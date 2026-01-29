import requests
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


class ClienteWhatsApp:
    """Cliente para enviar mensajes a través de WhatsApp API"""

    BASE_URL = "https://graph.instagram.com/v18.0"
    TIMEOUT = 10

    @staticmethod
    def enviar_mensaje(phone_number: str, mensaje: str) -> bool:
        """
        Envía un mensaje a través de WhatsApp API
        
        Args:
            phone_number: Número de teléfono en formato +54...
            mensaje: Contenido del mensaje
            
        Returns:
            True si se envió exitosamente, False en caso contrario
        """
        try:
            # Limpiar número de teléfono
            phone_clean = phone_number.replace("+", "").replace(" ", "")

            url = f"{ClienteWhatsApp.BASE_URL}/{settings.whatsapp_phone_id}/messages"

            headers = {
                "Authorization": f"Bearer {settings.whatsapp_access_token}",
                "Content-Type": "application/json",
            }

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
                logger.info(f"Mensaje enviado a {phone_number}")
                return True
            else:
                logger.error(
                    f"Error enviando mensaje a {phone_number}: "
                    f"{response.status_code} - {response.text}"
                )
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión enviando mensaje a {phone_number}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado enviando mensaje a {phone_number}: {e}")
            return False

    @staticmethod
    def enviar_mensajes_batch(
        mensajes: list[dict],
    ) -> dict:
        """
        Envía múltiples mensajes
        
        Args:
            mensajes: Lista de dict con {phone_number, mensaje}
            
        Returns:
            Dict con resultado de cada envío
        """
        resultados = {}
        for msg in mensajes:
            resultados[msg["phone_number"]] = ClienteWhatsApp.enviar_mensaje(
                msg["phone_number"], msg["mensaje"]
            )
        return resultados
