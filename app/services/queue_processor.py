import logging
import random
import time

from django.conf import settings
from django.db import transaction, close_old_connections, models
from django.db.utils import NotSupportedError

from app.models.mensaje import Mensaje
from app.services import (
    GestorCliente,
    GestorContenido,
    GestorMensajes,
    GestorSesion,
    NavigadorBot,
    ValidadorEntrada,
)
from app.services.cliente_whatsapp import ClienteWhatsApp

logger = logging.getLogger(__name__)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _calcular_delay_ms(respuesta_texto: str) -> int:
    min_delay = int(getattr(settings, "RESPONSE_MIN_DELAY_MS", 800))
    max_delay = int(getattr(settings, "RESPONSE_MAX_DELAY_MS", 2000))
    chars_per_sec = float(getattr(settings, "RESPONSE_CHARS_PER_SEC", 18))
    jitter_ms = int(getattr(settings, "RESPONSE_JITTER_MS", 250))

    texto_len = max(0, len(respuesta_texto or ""))
    typing_ms = int((texto_len / max(chars_per_sec, 1)) * 1000)
    delay_ms = max(min_delay, typing_ms)
    delay_ms = min(delay_ms, max_delay)
    if jitter_ms > 0:
        delay_ms += random.randint(0, jitter_ms)
    return delay_ms


def _marcar_leido_y_typing(wa_message_id: str) -> None:
    if not wa_message_id:
        return
    typing_enabled = str(getattr(settings, "WHATSAPP_ENABLE_TYPING_INDICATOR", "False")).lower() == "true"
    typing_type = getattr(settings, "WHATSAPP_TYPING_INDICATOR_TYPE", "text")
    ClienteWhatsApp.marcar_como_leido(
        wa_message_id,
        typing_indicator=typing_enabled,
        typing_type=typing_type,
    )


def _procesar_mensaje_inbound(mensaje_in: Mensaje) -> None:
    datos = mensaje_in.metadata_json or {}
    phone_number = mensaje_in.phone_number
    mensaje_usuario = mensaje_in.contenido or ""
    nombre_usuario = mensaje_in.nombre or ""
    alias_waba = datos.get("alias_waba") or ""
    message_type = mensaje_in.tipo or "text"
    wa_message_id = mensaje_in.wa_message_id

    _marcar_leido_y_typing(wa_message_id)

    sesion, sesion_expirada = GestorSesion.obtener_o_crear_sesion(
        phone_number, nombre_usuario
    )
    _, cliente_nuevo = GestorCliente.registrar_contacto(
        phone_number, nombre_usuario, mensaje_usuario, alias_waba=alias_waba
    )

    validacion = ValidadorEntrada.validar(mensaje_usuario)

    if cliente_nuevo:
        estado_nuevo = "0"
        historial_nuevo = ["0"]
        tipo_contenido = "menu"
        target = "0"
        es_valido = True
    elif sesion_expirada:
        estado_nuevo = "0"
        historial_nuevo = ["0"]
        tipo_contenido = "menu"
        target = "0"
        es_valido = True
    elif message_type != "text" or not mensaje_usuario:
        estado_nuevo = sesion.estado_actual
        historial_nuevo = sesion.historial_navegacion
        tipo_contenido = "menu"
        target = "0"
        es_valido = False
    else:
        estado_nuevo, historial_nuevo, tipo_contenido, target, es_valido = (
            NavigadorBot.procesar_entrada(
                mensaje_usuario, sesion.historial_navegacion, sesion.estado_actual
            )
        )

    if cliente_nuevo:
        tipo_entrada = "cliente_nuevo"
        accion = "cliente_nuevo"
    elif sesion_expirada:
        tipo_entrada = "sesion_expirada"
        accion = "sesion_expirada"
    elif message_type != "text" or not mensaje_usuario:
        tipo_entrada = "no_texto"
        accion = "no_texto"
    else:
        tipo_entrada = "valido" if es_valido else "invalido"
        accion = validacion.accion

    inbound_meta = mensaje_in.metadata_json or {}
    inbound_meta.update(
        {
            "cliente_nuevo": cliente_nuevo,
            "sesion_expirada": sesion_expirada,
            "message_type": message_type,
            "tipo_entrada": tipo_entrada,
            "accion": accion,
            "target": target,
        }
    )
    mensaje_in.metadata_json = inbound_meta
    mensaje_in.save(update_fields=["metadata_json"])

    respuesta_texto = ""

    if cliente_nuevo:
        bienvenida = GestorContenido.obtener_config_mensaje("bienvenida") or ""
        contenido_menu = NavigadorBot.obtener_contenido("0", "menu")
        menu_texto = contenido_menu["contenido"] if contenido_menu else ""
        respuesta_texto = f"{bienvenida}\n\n{menu_texto}".strip()
    elif sesion_expirada:
        error_sesion = GestorContenido.obtener_config_mensaje("error_sesion") or ""
        contenido_menu = NavigadorBot.obtener_contenido("0", "menu")
        menu_texto = contenido_menu["contenido"] if contenido_menu else ""
        respuesta_texto = f"{error_sesion}\n\n{menu_texto}".strip()
    elif message_type != "text" or not mensaje_usuario:
        contenido_menu = NavigadorBot.obtener_contenido("0", "menu")
        menu_texto = contenido_menu["contenido"] if contenido_menu else ""
        respuesta_texto = (
            "⚠️ Solo puedo leer mensajes de texto.\n"
            "Escribí una opción del menú o 'hola' para comenzar.\n\n"
            f"{menu_texto}"
        ).strip()
    elif es_valido:
        contenido = NavigadorBot.obtener_contenido(target, tipo_contenido)
        if contenido:
            respuesta_texto = contenido["contenido"]
        else:
            respuesta_texto = (
                "❌ Error: No se encontró el contenido solicitado.\n"
                "0 Volver al menu principal"
            )
    else:
        entrada_limpia = validacion.entrada_limpia if validacion else ""
        es_texto_libre = bool(entrada_limpia) and not entrada_limpia.isdigit() and len(entrada_limpia) > 1
        if es_texto_libre:
            contenido_menu = NavigadorBot.obtener_contenido("0", "menu")
            menu_texto = contenido_menu["contenido"] if contenido_menu else ""
            respuesta_texto = (
                "Si queres otra informacion, elegi una opcion del menu.\n\n"
                f"{menu_texto}"
            ).strip()
        else:
            respuesta_texto = (
                "Opcion no valida.\n"
                "Por favor, selecciona un numero del 1 al 12 o una letra de la A a la Z.\n\n"
                "0 Volver al menu principal"
            )

    GestorSesion.actualizar_estado(
        phone_number, estado_nuevo, historial_nuevo, mensaje_usuario
    )

    delay_ms = _calcular_delay_ms(respuesta_texto)
    outbound_meta = {
        "tipo_contenido": tipo_contenido,
        "accion": accion,
        "target": target,
        "estado_nuevo": estado_nuevo,
        "respuesta_a": wa_message_id,
        "respuesta_a_id": str(mensaje_in.id),
        "delay_ms": delay_ms,
    }
    GestorMensajes.registrar_salida(
        phone_number=phone_number,
        nombre=nombre_usuario,
        contenido=respuesta_texto,
        tipo="text",
        metadata=outbound_meta,
        queue_status="queued",
        process_after_ms=_now_ms() + delay_ms,
    )


def procesar_inbound_pendientes(limit: int = 10) -> int:
    """Procesa mensajes entrantes pendientes."""
    close_old_connections()
    now_ms = _now_ms()
    with transaction.atomic():
        base_qs = (
            Mensaje.objects.filter(
                direccion="in",
                queue_status="pending",
            )
            .filter(models.Q(process_after_ms__lte=now_ms) | models.Q(process_after_ms__isnull=True))
            .order_by("timestamp_ms", "id")
        )
        try:
            mensajes = list(base_qs.select_for_update(skip_locked=True)[:limit])
        except NotSupportedError:
            mensajes = list(base_qs[:limit])
        if mensajes:
            Mensaje.objects.filter(id__in=[m.id for m in mensajes]).update(
                queue_status="processing",
                locked_at_ms=now_ms,
                attempts=models.F("attempts") + 1,
            )

    procesados = 0
    for mensaje in mensajes:
        try:
            _procesar_mensaje_inbound(mensaje)
            Mensaje.objects.filter(id=mensaje.id).update(
                queue_status="processed",
                processed_at_ms=_now_ms(),
                error=None,
            )
            procesados += 1
        except Exception as exc:
            logger.exception("Error procesando mensaje inbound %s", mensaje.id)
            Mensaje.objects.filter(id=mensaje.id).update(
                queue_status="failed",
                error=str(exc),
                processed_at_ms=_now_ms(),
            )
    return procesados


def procesar_outbound_pendientes(limit: int = 10) -> int:
    """Envia mensajes salientes en cola."""
    close_old_connections()
    now_ms = _now_ms()
    with transaction.atomic():
        base_qs = (
            Mensaje.objects.filter(
                direccion="out",
                queue_status="queued",
            )
            .filter(models.Q(process_after_ms__lte=now_ms) | models.Q(process_after_ms__isnull=True))
            .order_by("process_after_ms", "id")
        )
        try:
            mensajes = list(base_qs.select_for_update(skip_locked=True)[:limit])
        except NotSupportedError:
            mensajes = list(base_qs[:limit])
        if mensajes:
            Mensaje.objects.filter(id__in=[m.id for m in mensajes]).update(
                queue_status="processing",
                locked_at_ms=now_ms,
                attempts=models.F("attempts") + 1,
            )

    enviados = 0
    for mensaje in mensajes:
        try:
            resultado = ClienteWhatsApp.enviar_mensaje_con_resultado(
                mensaje.phone_number, mensaje.contenido or ""
            )
            ok = resultado.get("ok", False)
            message_id = resultado.get("message_id")
            update_fields = {
                "processed_at_ms": _now_ms(),
                "error": None,
            }
            if ok:
                update_fields["queue_status"] = "sent"
                update_fields["delivery_status"] = "sent"
                update_fields["wa_message_id"] = message_id or mensaje.wa_message_id
                enviados += 1
            else:
                update_fields["queue_status"] = "failed"
                update_fields["error"] = resultado.get("error") or resultado.get("response")
            Mensaje.objects.filter(id=mensaje.id).update(**update_fields)
        except Exception as exc:
            logger.exception("Error enviando mensaje outbound %s", mensaje.id)
            Mensaje.objects.filter(id=mensaje.id).update(
                queue_status="failed",
                error=str(exc),
                processed_at_ms=_now_ms(),
            )
    return enviados


def procesar_cola(limit: int = 10) -> dict:
    """Procesa colas inbound y outbound."""
    procesados_in = procesar_inbound_pendientes(limit=limit)
    procesados_out = procesar_outbound_pendientes(limit=limit)
    return {"inbound": procesados_in, "outbound": procesados_out}
