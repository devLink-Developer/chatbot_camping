import json

from app.views import _extraer_eventos_whatsapp, _extraer_opcion_flow


def test_extraer_opcion_flow_simple():
    assert _extraer_opcion_flow({"menu_option": "5"}) == "5"


def test_extraer_opcion_flow_nested():
    assert _extraer_opcion_flow({"data": {"menu_option": "12"}}) == "12"


def test_extraer_evento_nfm_reply():
    response_json = json.dumps({"menu_option": "3"})
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "123"},
                            "contacts": [{"profile": {"name": "Test"}}],
                            "messages": [
                                {
                                    "from": "5491111111111",
                                    "id": "wamid.test",
                                    "timestamp": "1700000000",
                                    "type": "interactive",
                                    "interactive": {
                                        "type": "nfm_reply",
                                        "nfm_reply": {
                                            "response_json": response_json,
                                            "name": "menu_principal",
                                        },
                                    },
                                }
                            ],
                        }
                    }
                ]
            }
        ]
    }
    mensajes, statuses = _extraer_eventos_whatsapp(payload)
    assert statuses == []
    assert len(mensajes) == 1
    assert mensajes[0]["mensaje"] == "3"
