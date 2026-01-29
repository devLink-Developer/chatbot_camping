import logging
import json
import uuid
import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ChatbotResponse, ContenidoResponse, SesionResponse
from app.config import settings
from app.services import (
    ValidadorEntrada,
    GestorSesion,
    NavigadorBot,
    GestorContenido,
    ClienteWhatsApp,
)
from app.models.registro import Registro

router = APIRouter(prefix="/api", tags=["chatbot"])
logger = logging.getLogger(__name__)


def _extraer_datos_whatsapp(data: dict) -> Optional[dict]:
    """Extrae datos relevantes del webhook de WhatsApp"""
    try:
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return None

        message = messages[0]
        contacts = value.get("contacts", [])
        contact = contacts[0] if contacts else {}

        # Extraer número de teléfono
        phone_raw = message.get("from", "")
        if phone_raw.startswith("549"):
            phone_number = "+54" + phone_raw[3:]
        else:
            phone_number = "+" + phone_raw

        return {
            "phone_number": phone_number,
            "nombre": contact.get("profile", {}).get("name", ""),
            "mensaje": message.get("text", {}).get("body", ""),
            "timestamp": int(message.get("timestamp", time.time())),
        }
    except Exception as e:
        logger.error(f"Error extrayendo datos de WhatsApp: {e}")
        return None


@router.post("/webhook")
async def webhook_whatsapp(request: Request, db: Session = Depends(get_db)):
    """
    Endpoint webhook para recibir mensajes de WhatsApp
    """
    try:
        data = await request.json()
        logger.info(f"Webhook recibido: {json.dumps(data, indent=2)}")

        # Extraer datos del mensaje
        datos_msg = _extraer_datos_whatsapp(data)
        if not datos_msg:
            return {"status": "ok"}

        phone_number = datos_msg["phone_number"]
        mensaje_usuario = datos_msg["mensaje"]
        nombre_usuario = datos_msg["nombre"]

        # Obtener o crear sesión
        sesion = GestorSesion.obtener_o_crear_sesion(
            db, phone_number, nombre_usuario
        )

        # Procesar entrada
        estado_nuevo, historial_nuevo, tipo_contenido, target, es_valido = (
            NavigadorBot.procesar_entrada(
                db, mensaje_usuario, sesion.historial_navegacion, sesion.estado_actual
            )
        )

        # Registrar interacción
        registro_id = str(uuid.uuid4())
        registro = Registro(
            id=registro_id,
            phone_number=phone_number,
            nombre=nombre_usuario,
            mensaje_usuario=mensaje_usuario,
            tipo_entrada="valido" if es_valido else "invalido",
            accion=ValidadorEntrada.validar(mensaje_usuario).accion,
            target=target,
            timestamp_usuario=datos_msg["timestamp"],
            timestamp_ms=int(time.time() * 1000),
        )

        # Obtener contenido a mostrar
        contenido = None
        respuesta_texto = ""

        if es_valido:
            contenido = NavigadorBot.obtener_contenido(db, target, tipo_contenido)
            if contenido:
                respuesta_texto = contenido["contenido"]
            else:
                respuesta_texto = (
                    "❌ Error: No se encontró el contenido solicitado.\n"
                    "0️⃣ Volver al menú principal"
                )
        else:
            respuesta_texto = (
                f"❌ Opción no válida.\n"
                f"Por favor, selecciona un número del 1 al 12 o una letra de la A a la Z.\n\n"
                f"0️⃣ Volver al menú principal"
            )

        # Actualizar sesión y guardar registro
        GestorSesion.actualizar_estado(
            db, phone_number, estado_nuevo, historial_nuevo, mensaje_usuario
        )
        registro.respuesta_enviada = respuesta_texto
        db.add(registro)
        db.commit()

        # Enviar respuesta por WhatsApp
        enviado = ClienteWhatsApp.enviar_mensaje(phone_number, respuesta_texto)

        logger.info(
            f"Mensaje procesado para {phone_number}: "
            f"estado={estado_nuevo}, "
            f"enviado={enviado}"
        )

        return {"status": "ok", "enviado": enviado}

    except Exception as e:
        logger.error(f"Error procesando webhook: {e}")
        return {"status": "error", "detalle": str(e)}


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = None,
    hub_challenge: str = None,
    hub_verify_token: str = None,
):
    """
    Verifica el webhook con WhatsApp
    """
    if hub_mode != "subscribe":
        return {"status": "error"}

    if hub_verify_token != settings.whatsapp_verify_token:
        logger.warning(f"Token de verificación inválido: {hub_verify_token}")
        return {"status": "error"}

    logger.info("Webhook verificado correctamente")
    return hub_challenge


@router.get("/sesion/{phone_number}", response_model=SesionResponse)
async def obtener_sesion(phone_number: str, db: Session = Depends(get_db)):
    """Obtiene información de la sesión de un usuario"""
    sesion = GestorSesion.obtener_o_crear_sesion(db, phone_number)
    return SesionResponse(
        phone_number=sesion.phone_number,
        nombre=sesion.nombre,
        estado_actual=sesion.estado_actual,
        historial_navegacion=sesion.historial_navegacion,
        activa=sesion.activa,
    )


@router.post("/resetear-sesion/{phone_number}")
async def resetear_sesion(phone_number: str, db: Session = Depends(get_db)):
    """Resetea la sesión de un usuario"""
    sesion = db.query(Session).filter(Sesion.phone_number == phone_number).first()
    if sesion:
        sesion.estado_actual = "0"
        sesion.historial_navegacion = ["0"]
        sesion.intentos_fallidos = 0
        db.commit()
        return {"status": "ok", "mensaje": "Sesión reseteada"}
    return {"status": "error", "mensaje": "Sesión no encontrada"}


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "servicio": "ACA Lujan Chatbot Bot"}
