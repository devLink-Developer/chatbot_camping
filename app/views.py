import json
import logging
import time

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from app.models.sesion import Sesion
from app.models.mensaje import Mensaje
from app.services import GestorMensajes, GestorSesion
from app.services.queue_processor import procesar_cola
from app.services.waba_config import get_active_waba_config

logger = logging.getLogger(__name__)


def _extraer_eventos_whatsapp(data: dict) -> tuple[list[dict], list[dict]]:
    """Extrae mensajes y status updates del webhook de WhatsApp."""
    mensajes: list[dict] = []
    statuses: list[dict] = []
    try:
        for entry in data.get("entry", []) or []:
            for change in entry.get("changes", []) or []:
                value = change.get("value", {}) or {}
                metadata = value.get("metadata", {}) or {}
                contacts = value.get("contacts", []) or []
                contact = contacts[0] if contacts else {}
                alias_waba = contact.get("profile", {}).get("name", "")
                for message in value.get("messages", []) or []:
                    message_type = message.get("type", "text")
                    mensaje_texto = ""
                    if message_type == "text":
                        mensaje_texto = message.get("text", {}).get("body", "")

                    phone_raw = message.get("from", "")
                    if phone_raw.startswith("549"):
                        phone_number = "+54" + phone_raw[3:]
                    else:
                        phone_number = "+" + phone_raw

                    mensajes.append(
                        {
                            "phone_number": phone_number,
                            "nombre": alias_waba,
                            "alias_waba": alias_waba,
                            "mensaje": mensaje_texto,
                            "message_type": message_type,
                            "wa_message_id": message.get("id"),
                            "timestamp": int(message.get("timestamp", time.time())),
                            "raw_message": message,
                            "metadata": metadata,
                        }
                    )
                for status in value.get("statuses", []) or []:
                    statuses.append(status)
    except Exception as exc:
        logger.error("Error extrayendo eventos de WhatsApp: %s", exc)
    return mensajes, statuses


def _procesar_statuses(statuses: list[dict]) -> int:
    actualizados = 0
    for status in statuses:
        wa_message_id = status.get("id")
        status_value = status.get("status")
        timestamp = status.get("timestamp")
        if not wa_message_id or not status_value:
            continue
        update = {"delivery_status": status_value}
        if timestamp:
            update["delivery_timestamp_ms"] = int(timestamp) * 1000
        actualizados += Mensaje.objects.filter(
            direccion="out", wa_message_id=wa_message_id
        ).update(**update)
    return actualizados


def _encolar_mensajes(mensajes: list[dict]) -> int:
    encolados = 0
    mensajes_ordenados = sorted(
        mensajes,
        key=lambda m: (m.get("timestamp", 0), m.get("wa_message_id") or ""),
    )
    ahora_ms = int(time.time() * 1000)
    for datos in mensajes_ordenados:
        metadata = datos.get("metadata") or {}
        mensaje = GestorMensajes.registrar_entrada(
            phone_number=datos["phone_number"],
            nombre=datos.get("nombre") or "",
            contenido=datos.get("mensaje") or "",
            tipo=datos.get("message_type") or "text",
            timestamp_ms=datos.get("timestamp", int(time.time())) * 1000,
            wa_message_id=datos.get("wa_message_id"),
            metadata={
                "raw": datos.get("raw_message"),
                "alias_waba": datos.get("alias_waba"),
                "phone_number_id": metadata.get("phone_number_id"),
            },
            queue_status="pending",
            process_after_ms=ahora_ms,
        )
        if mensaje:
            encolados += 1
    return encolados


def _procesar_webhook(data: dict) -> dict:
    """Procesa un webhook entrante de WhatsApp (cola)."""
    mensajes, statuses = _extraer_eventos_whatsapp(data)
    encolados = _encolar_mensajes(mensajes) if mensajes else 0
    actualizados = _procesar_statuses(statuses) if statuses else 0

    if encolados and str(getattr(settings, "QUEUE_PROCESS_INLINE", "False")).lower() == "true":
        procesar_cola(limit=int(getattr(settings, "QUEUE_BATCH_SIZE", 10)))

    return {"status": "ok", "encolados": encolados, "statuses": actualizados}


def _verificar_webhook(
    hub_mode: str | None,
    hub_challenge: str | None,
    hub_verify_token: str | None,
) -> HttpResponse:
    """Verifica el webhook con WhatsApp."""
    if hub_mode != "subscribe" or not hub_challenge:
        return HttpResponse(status=400)

    active_config = get_active_waba_config()
    expected_token = (
        active_config.verify_token
        if active_config and active_config.verify_token
        else settings.WHATSAPP_VERIFY_TOKEN
    )
    if hub_verify_token != expected_token:
        logger.warning("Token de verificacion invalido: %s", hub_verify_token)
        return HttpResponse(status=403)

    logger.info("Webhook verificado correctamente")
    return HttpResponse(hub_challenge, content_type="text/plain", status=200)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def webhook(request):
    if request.method == "GET":
        params = request.GET
        hub_mode = params.get("hub.mode") or params.get("hub_mode")
        hub_challenge = params.get("hub.challenge") or params.get("hub_challenge")
        hub_verify_token = params.get("hub.verify_token") or params.get("hub_verify_token")
        return _verificar_webhook(hub_mode, hub_challenge, hub_verify_token)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"status": "error", "detalle": "invalid_json"}, status=400)

    logger.info("Webhook recibido: %s", json.dumps(data, indent=2))
    respuesta = _procesar_webhook(data)
    return JsonResponse(respuesta)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def webhook_mensajes(request):
    return webhook(request)


@require_http_methods(["GET"])
def obtener_sesion(request, phone_number: str):
    """Obtiene informacion de la sesion de un usuario"""
    sesion, _ = GestorSesion.obtener_o_crear_sesion(phone_number)
    return JsonResponse(
        {
            "phone_number": sesion.phone_number,
            "nombre": sesion.nombre,
            "estado_actual": sesion.estado_actual,
            "historial_navegacion": sesion.historial_navegacion,
            "activa": sesion.activa,
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def resetear_sesion(request, phone_number: str):
    """Resetea la sesion de un usuario"""
    sesion = Sesion.objects.filter(phone_number=phone_number).first()
    if sesion:
        sesion.estado_actual = "0"
        sesion.historial_navegacion = ["0"]
        sesion.intentos_fallidos = 0
        sesion.save()
        return JsonResponse({"status": "ok", "mensaje": "Sesion reseteada"})
    return JsonResponse({"status": "error", "mensaje": "Sesion no encontrada"}, status=404)


@require_http_methods(["GET"])
def health_check(request):
    return JsonResponse({"status": "ok", "servicio": "ACA Lujan Chatbot Bot"})


@require_http_methods(["GET"])
def root(request):
    return JsonResponse(
        {
            "nombre": settings.API_TITLE,
            "version": settings.API_VERSION,
            "estado": "activo",
        }
    )
