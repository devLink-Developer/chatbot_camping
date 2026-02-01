from __future__ import annotations

import time
from typing import Optional, List, Dict, Any

from app.models.menu import Menu
from app.models.menu_option import MenuOption


MAX_BUTTONS = 3
MAX_BUTTON_TITLE = 20
MAX_LIST_ROW_TITLE = 24
MAX_LIST_ROW_DESC = 72
MAX_LIST_BUTTON_TEXT = 20
MAX_BODY_TEXT = 1024
MAX_LIST_ROWS = 10
MAX_FLOW_CTA = 20


def _trim(text: str, max_len: int) -> str:
    if not text:
        return ""
    text = " ".join(str(text).split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def _build_options(menu: Menu) -> List[Dict[str, str]]:
    opciones = list(
        MenuOption.objects.filter(menu=menu, activo=True).order_by("orden")
    )
    items = [
        {"key": (opt.key or "").strip(), "label": (opt.label or "").strip()}
        for opt in opciones
        if (opt.key or "").strip()
    ]

    if not menu.is_main and menu.id != "0":
        keys = {opt["key"] for opt in items}
        if "0" not in keys:
            items.append({"key": "0", "label": "Volver al menu principal"})
        if "#" not in keys:
            items.append({"key": "#", "label": "Volver atras"})

    return items


def _find_first_screen_id(flow_json: Any) -> Optional[str]:
    if not isinstance(flow_json, dict):
        return None
    screens = flow_json.get("screens") or []
    if isinstance(screens, list):
        for screen in screens:
            if isinstance(screen, dict):
                screen_id = screen.get("id")
                if screen_id:
                    return str(screen_id)
    return None


def build_flow_interactive_payload(
    menu: Menu,
    body_text: Optional[str] = None,
    cta_text: str = "Ver opciones",
    message_version: str = "3",
) -> Optional[Dict]:
    if not menu or not menu.flow_id:
        return None

    screen_id = _find_first_screen_id(menu.flow_json)
    body = _trim(body_text or menu.titulo or "Selecciona una opcion", MAX_BODY_TEXT)
    cta = _trim(cta_text, MAX_FLOW_CTA) or "Ver opciones"
    flow_token = f"menu_{menu.id}_{int(time.time())}"

    parameters: Dict[str, Any] = {
        "flow_message_version": str(message_version),
        "flow_id": str(menu.flow_id),
        "flow_cta": cta,
        "flow_token": flow_token,
    }

    if screen_id:
        parameters["flow_action"] = "navigate"
        parameters["flow_action_payload"] = {"screen": screen_id}

    return {
        "type": "flow",
        "body": {"text": body},
        "action": {"name": "flow", "parameters": parameters},
    }


def _build_list_payload(opciones: List[Dict[str, str]], body: str, section_title: str = "Opciones") -> Dict:
    rows = []
    for opt in opciones:
        title = _trim(opt["label"] or opt["key"], MAX_LIST_ROW_TITLE)
        desc = ""
        if opt["label"] and opt["label"] != title:
            desc = _trim(opt["label"], MAX_LIST_ROW_DESC)
        row = {"id": opt["key"], "title": title}
        if desc:
            row["description"] = desc
        rows.append(row)

    button_text = _trim("Ver opciones", MAX_LIST_BUTTON_TEXT)
    return {
        "type": "list",
        "body": {"text": body},
        "action": {
            "button": button_text,
            "sections": [{"title": section_title, "rows": rows}],
        },
    }


def build_menu_interactive_payloads(menu: Menu, body_text: Optional[str] = None) -> Optional[List[Dict]]:
    opciones = _build_options(menu)
    if not opciones:
        return None

    base_body = _trim(body_text or menu.titulo or "Selecciona una opcion", MAX_BODY_TEXT)

    if len(opciones) <= MAX_BUTTONS:
        buttons = []
        for opt in opciones:
            title = _trim(opt["label"] or opt["key"], MAX_BUTTON_TITLE)
            buttons.append(
                {
                    "type": "reply",
                    "reply": {"id": opt["key"], "title": title},
                }
            )
        return [
            {
                "type": "button",
                "body": {"text": base_body},
                "action": {"buttons": buttons},
            }
        ]

    if len(opciones) <= MAX_LIST_ROWS:
        return [_build_list_payload(opciones, base_body)]

    # Si supera el maximo de filas, no enviamos interactivo: el bot responde solo texto o flow.
    return None


def build_menu_interactive(menu: Menu, body_text: Optional[str] = None) -> Optional[Dict]:
    payloads = build_menu_interactive_payloads(menu, body_text=body_text)
    if not payloads:
        return None
    return payloads[0]
