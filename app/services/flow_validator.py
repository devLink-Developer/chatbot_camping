import json
import logging
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings
from django.utils import timezone

from app.models.menu import Menu
from app.models.menu_option import MenuOption
from app.services.waba_config import get_whatsapp_setting

logger = logging.getLogger(__name__)

DEFAULT_FIELDS = "id,name,status,validation_errors,updated_time,flow_json"


def _graph_base() -> str:
    base = get_whatsapp_setting("api_base", settings.WHATSAPP_API_BASE).rstrip("/")
    version = get_whatsapp_setting("api_version", settings.WHATSAPP_API_VERSION)
    if version and not version.startswith("v"):
        version = f"v{version}"
    return f"{base}/{version}"


def _headers() -> Dict[str, str]:
    token = get_whatsapp_setting("access_token", settings.WHATSAPP_ACCESS_TOKEN)
    return {"Authorization": f"Bearer {token}"}


def _request_json(url: str, params: Optional[dict] = None) -> Dict[str, Any]:
    try:
        response = requests.get(url, params=params, headers=_headers(), timeout=15)
        if response.status_code == 200:
            return {"ok": True, "data": response.json()}
        return {"ok": False, "status_code": response.status_code, "error": response.text}
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)}


def _parse_flow_json(raw: Any) -> Optional[dict]:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    return None


def _collect_option_ids(flow_json: dict) -> List[str]:
    ids: List[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key in ("data-source", "data_source", "dataSource"):
                if key in node and isinstance(node[key], list):
                    for item in node[key]:
                        if isinstance(item, dict) and "id" in item:
                            ids.append(str(item["id"]))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(flow_json)
    return sorted(set(ids))


def _fetch_flow_details(flow_id: str) -> Dict[str, Any]:
    url = f"{_graph_base()}/{flow_id}"
    result = _request_json(url, params={"fields": DEFAULT_FIELDS})
    if result.get("ok"):
        return result

    fallback_fields = "id,name,status,validation_errors,updated_time"
    fallback = _request_json(url, params={"fields": fallback_fields})
    return fallback


def validate_flow_for_menu(menu: Menu) -> Dict[str, Any]:
    if not menu.flow_id:
        menu.flow_valid = False
        menu.flow_status = None
        menu.flow_last_checked_at = timezone.now()
        menu.flow_validation = {"ok": False, "error": "flow_id_missing"}
        menu.save(
            update_fields=[
                "flow_valid",
                "flow_status",
                "flow_last_checked_at",
                "flow_validation",
            ]
        )
        return menu.flow_validation

    flow_id = menu.flow_id
    result = _fetch_flow_details(flow_id)
    validation: Dict[str, Any] = {
        "flow_id": flow_id,
        "checked_at": timezone.now().isoformat(),
    }

    if not result.get("ok"):
        validation.update(
            {
                "ok": False,
                "error": result.get("error"),
                "status_code": result.get("status_code"),
            }
        )
        menu.flow_valid = False
        menu.flow_last_checked_at = timezone.now()
        menu.flow_validation = validation
        menu.save(update_fields=["flow_valid", "flow_last_checked_at", "flow_validation"])
        return validation

    data = result.get("data") or {}
    flow_json = _parse_flow_json(data.get("flow_json"))
    option_ids_flow = _collect_option_ids(flow_json) if flow_json else []
    option_ids_menu = sorted(
        {str(opt.key) for opt in MenuOption.objects.filter(menu=menu, activo=True)}
    )

    missing_ids = sorted(set(option_ids_menu) - set(option_ids_flow)) if option_ids_flow else []
    extra_ids = sorted(set(option_ids_flow) - set(option_ids_menu)) if option_ids_flow else []

    validation_errors = data.get("validation_errors") or []
    flow_status = data.get("status") or ""
    flow_name = data.get("name") or None

    options_match = None
    if option_ids_flow:
        options_match = not missing_ids and not extra_ids

    ok = (not validation_errors) and (options_match is not False)

    validation.update(
        {
            "ok": ok,
            "flow_name": flow_name,
            "flow_status": flow_status,
            "validation_errors": validation_errors,
            "option_ids_flow": option_ids_flow,
            "option_ids_menu": option_ids_menu,
            "missing_option_ids": missing_ids,
            "extra_option_ids": extra_ids,
            "options_match": options_match,
        }
    )

    menu.flow_name = flow_name
    menu.flow_status = flow_status or None
    menu.flow_valid = ok
    menu.flow_last_checked_at = timezone.now()
    menu.flow_validation = validation
    menu.save(
        update_fields=[
            "flow_name",
            "flow_status",
            "flow_valid",
            "flow_last_checked_at",
            "flow_validation",
        ]
    )

    return validation
