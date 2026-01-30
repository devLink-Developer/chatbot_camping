import logging
from typing import Optional

import requests
from django.conf import settings

from app.services.waba_config import get_active_waba_config, get_whatsapp_setting

logger = logging.getLogger(__name__)


class ClienteWhatsApp:
    """Cliente para enviar mensajes a traves de WhatsApp Cloud API"""

    TIMEOUT = 10

    @staticmethod
    def _build_base_url() -> str:
        base = get_whatsapp_setting("api_base", settings.WHATSAPP_API_BASE).rstrip("/")
        version = get_whatsapp_setting("api_version", settings.WHATSAPP_API_VERSION)
        if version and not version.startswith("v"):
            version = f"v{version}"
        phone_id = get_whatsapp_setting("phone_id", settings.WHATSAPP_PHONE_ID)
        return f"{base}/{version}/{phone_id}/messages"

    @staticmethod
    def _build_headers() -> dict:
        token = get_whatsapp_setting("access_token", settings.WHATSAPP_ACCESS_TOKEN)
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def enviar_mensaje(phone_number: str, mensaje: str) -> bool:
        """
        Envia un mensaje a traves de WhatsApp API

        Args:
            phone_number: Numero de telefono en formato +54...
            mensaje: Contenido del mensaje

        Returns:
            True si se envio exitosamente, False en caso contrario
        """
        resultado = ClienteWhatsApp.enviar_mensaje_con_resultado(phone_number, mensaje)
        return resultado.get("ok", False)

    @staticmethod
    def enviar_mensajes_batch(mensajes: list[dict]) -> dict:
        """Envia multiples mensajes"""
        resultados = {}
        for msg in mensajes:
            resultados[msg["phone_number"]] = ClienteWhatsApp.enviar_mensaje(
                msg["phone_number"], msg["mensaje"]
            )
        return resultados

    @staticmethod
    def enviar_mensaje_con_resultado(phone_number: str, mensaje: str) -> dict:
        """Envia mensaje y retorna resultado con message_id si existe."""
        try:
            phone_clean = phone_number.replace("+", "").replace(" ", "")
            url = ClienteWhatsApp._build_base_url()
            headers = ClienteWhatsApp._build_headers()
            payload = {
                "messaging_product": "whatsapp",
                "to": phone_clean,
                "type": "text",
                "text": {"body": mensaje},
            }

            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=ClienteWhatsApp.TIMEOUT,
            )

            if response.status_code == 200:
                message_id = None
                try:
                    body = response.json()
                    messages = body.get("messages") or []
                    if messages:
                        message_id = messages[0].get("id")
                except Exception:
                    message_id = None
                logger.info("Mensaje enviado a %s", phone_number)
                return {"ok": True, "message_id": message_id, "response": response.text}

            logger.error(
                "Error enviando mensaje a %s: %s - %s",
                phone_number,
                response.status_code,
                response.text,
            )
            return {"ok": False, "message_id": None, "response": response.text}

        except requests.exceptions.RequestException as exc:
            logger.error("Error de conexion enviando mensaje a %s: %s", phone_number, exc)
            return {"ok": False, "message_id": None, "error": str(exc)}
        except Exception as exc:
            logger.error("Error inesperado enviando mensaje a %s: %s", phone_number, exc)
            return {"ok": False, "message_id": None, "error": str(exc)}

    @staticmethod
    def marcar_como_leido(message_id: str, typing_indicator: bool = False, typing_type: str = "text") -> bool:
        """Marca un mensaje como leido y opcionalmente envia typing indicator."""
        if not message_id:
            return False
        try:
            url = ClienteWhatsApp._build_base_url()
            headers = ClienteWhatsApp._build_headers()
            payload = {
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id,
            }
            if typing_indicator:
                payload["typing_indicator"] = {"type": typing_type}

            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=ClienteWhatsApp.TIMEOUT,
            )
            if response.status_code == 200:
                return True
            logger.error(
                "Error marcando como leido %s: %s - %s",
                message_id,
                response.status_code,
                response.text,
            )
            return False
        except Exception as exc:
            logger.error("Error marcando como leido %s: %s", message_id, exc)
            return False
