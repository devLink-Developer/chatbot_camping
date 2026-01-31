from __future__ import annotations

from typing import Optional, List, Dict

from app.models.menu import Menu
from app.models.menu_option import MenuOption


MAX_BUTTONS = 3
MAX_BUTTON_TITLE = 20
MAX_LIST_ROW_TITLE = 24
MAX_LIST_ROW_DESC = 72
MAX_LIST_BUTTON_TEXT = 20
MAX_BODY_TEXT = 1024
MAX_LIST_ROWS = 10


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

    if menu.id != "0":
        keys = {opt["key"] for opt in items}
        if "0" not in keys:
            items.append({"key": "0", "label": "Volver al menu principal"})
        if "#" not in keys:
            items.append({"key": "#", "label": "Volver atras"})

    return items


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

    if menu.id == "0":
        grupo_1_keys = {str(i) for i in range(1, 7)}
        grupo_2_keys = {str(i) for i in range(7, 13)}
        grupo_1 = [opt for opt in opciones if opt["key"] in grupo_1_keys]
        grupo_2 = [opt for opt in opciones if opt["key"] in grupo_2_keys]
        if grupo_1 and grupo_2:
            body_1 = _trim(f"{base_body}\nOpciones 1-6", MAX_BODY_TEXT)
            body_2 = _trim(f"{base_body}\nOpciones 7-12", MAX_BODY_TEXT)
            return [
                _build_list_payload(grupo_1, body_1, section_title="Opciones 1-6"),
                _build_list_payload(grupo_2, body_2, section_title="Opciones 7-12"),
            ]

    payloads = []
    total_chunks = (len(opciones) + MAX_LIST_ROWS - 1) // MAX_LIST_ROWS
    for idx in range(total_chunks):
        chunk = opciones[idx * MAX_LIST_ROWS : (idx + 1) * MAX_LIST_ROWS]
        suffix = f" ({idx + 1}/{total_chunks})" if total_chunks > 1 else ""
        body = _trim(f"{base_body}{suffix}", MAX_BODY_TEXT)
        payloads.append(_build_list_payload(chunk, body))
    return payloads


def build_menu_interactive(menu: Menu, body_text: Optional[str] = None) -> Optional[Dict]:
    payloads = build_menu_interactive_payloads(menu, body_text=body_text)
    if not payloads:
        return None
    return payloads[0]
