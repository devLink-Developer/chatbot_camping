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
from app.services.interactive_builder import build_menu_interactive_payloads
from app.services.waba_config import get_whatsapp_bool

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


def _marcar_leido_y_typing(wa_message_id: str, simulate: bool = False) -> None:
    if simulate or not wa_message_id:
        return
    typing_enabled = (
        str(getattr(settings, "WHATSAPP_ENABLE_TYPING_INDICATOR", "False")).lower() == "true"
    )
    typing_type = getattr(settings, "WHATSAPP_TYPING_INDICATOR_TYPE", "text")
    ClienteWhatsApp.marcar_como_leido(
        wa_message_id,
        typing_indicator=typing_enabled,
        typing_type=typing_type,
    )


def _procesar_mensaje_inbound(mensaje_in: Mensaje, simulate: bool = False) -> None:
    datos = mensaje_in.metadata_json or {}
    phone_number = mensaje_in.phone_number
    mensaje_usuario = mensaje_in.contenido or ""
    nombre_usuario = mensaje_in.nombre or ""
    alias_waba = datos.get("alias_waba") or ""
    message_type = mensaje_in.tipo or "text"
    is_textual = message_type in ("text", "interactive")
    wa_message_id = mensaje_in.wa_message_id

    _marcar_leido_y_typing(wa_message_id, simulate=simulate)

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
    elif (not is_textual) or not mensaje_usuario:
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
    elif (not is_textual) or not mensaje_usuario:
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
    interactive_body = ""
    menu_id_for_interactive = None

    if cliente_nuevo:
        bienvenida = GestorContenido.obtener_config_mensaje("bienvenida") or ""
        contenido_menu = NavigadorBot.obtener_contenido("0", "menu")
        menu_texto = contenido_menu["contenido"] if contenido_menu else ""
        respuesta_texto = f"{bienvenida}\n\n{menu_texto}".strip()
        interactive_body = bienvenida or "Bienvenido"
        menu_id_for_interactive = "0"
    elif sesion_expirada:
        error_sesion = GestorContenido.obtener_config_mensaje("error_sesion") or ""
        contenido_menu = NavigadorBot.obtener_contenido("0", "menu")
        menu_texto = contenido_menu["contenido"] if contenido_menu else ""
        respuesta_texto = f"{error_sesion}\n\n{menu_texto}".strip()
        interactive_body = error_sesion or "Sesion expirada"
        menu_id_for_interactive = "0"
    elif (not is_textual) or not mensaje_usuario:
        contenido_menu = NavigadorBot.obtener_contenido("0", "menu")
        menu_texto = contenido_menu["contenido"] if contenido_menu else ""
        respuesta_texto = (
            "Solo puedo leer mensajes de texto.\n"
            "Escribi una opcion del menu o 'hola' para comenzar.\n\n"
            f"{menu_texto}"
        ).strip()
        interactive_body = "Solo puedo leer mensajes de texto."
        menu_id_for_interactive = "0"
    elif es_valido:
        contenido = NavigadorBot.obtener_contenido(target, tipo_contenido)
        if contenido:
            respuesta_texto = contenido["contenido"]
            if tipo_contenido == "menu":
                interactive_body = contenido.get("titulo") or "Selecciona una opcion"
                menu_id_for_interactive = target or "0"
        else:
            respuesta_texto = (
                "Error: No se encontro el contenido solicitado.\n"
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
            interactive_body = "Si queres otra informacion, elegi una opcion del menu."
            menu_id_for_interactive = "0"
        else:
            respuesta_texto = (
                "Opcion no valida.\n"
                "Por favor, selecciona un numero del 1 al 12 o una letra de la A a la Z.\n\n"
                "0 Volver al menu principal"
            )
            interactive_body = "Opcion no valida."
            menu_id_for_interactive = "0"

    GestorSesion.actualizar_estado(
        phone_number, estado_nuevo, historial_nuevo, mensaje_usuario
    )

    interactive_enabled = get_whatsapp_bool(
        "interactive_enabled",
        getattr(settings, "WHATSAPP_INTERACTIVE_ENABLED", False),
    )
    interactive_payloads = None
    interactive_fallback = None
    if interactive_enabled and menu_id_for_interactive:
        menu = GestorContenido.obtener_menu(menu_id_for_interactive) or GestorContenido.obtener_menu("0")
        if menu:
            if simulate and menu.flow_json:
                interactive_payloads = [
                    {
                        "type": "flow_preview",
                        "flow_id": menu.flow_id,
                        "flow_json": menu.flow_json,
                    }
                ]
            else:
                interactive_payloads = build_menu_interactive_payloads(
                    menu,
                    body_text=interactive_body or (menu.titulo or ""),
                )
            if interactive_payloads:
                interactive_fallback = respuesta_texto

    delay_ms = 0 if simulate else _calcular_delay_ms(respuesta_texto)
    outbound_meta = {
        "tipo_contenido": tipo_contenido,
        "accion": accion,
        "target": target,
        "estado_nuevo": estado_nuevo,
        "respuesta_a": wa_message_id,
        "respuesta_a_id": str(mensaje_in.id),
        "respuesta_a_ts_ms": mensaje_in.timestamp_ms,
        "delay_ms": delay_ms,
        "interactive_enabled": interactive_enabled,
        "simulated": simulate,
    }
    if simulate and menu_id_for_interactive:
        menu_ref = GestorContenido.obtener_menu(menu_id_for_interactive) or GestorContenido.obtener_menu("0")
        if menu_ref and menu_ref.flow_json:
            outbound_meta["flow_json"] = menu_ref.flow_json
            outbound_meta["flow_id"] = menu_ref.flow_id
    if interactive_payloads:
        outbound_meta["interactive_payloads"] = interactive_payloads
        outbound_meta["interactive_fallback"] = interactive_fallback
        outbound_tipo = "interactive"
    else:
        outbound_tipo = "text"

    outbound_status = "processed" if simulate else "queued"
    process_after = _now_ms() if simulate else (_now_ms() + delay_ms)
    GestorMensajes.registrar_salida(
        phone_number=phone_number,
        nombre=nombre_usuario,
        contenido=respuesta_texto,
        tipo=outbound_tipo,
        metadata=outbound_meta,
        queue_status=outbound_status,
        process_after_ms=process_after,
    )


def procesar_inbound_pendientes(limit: int = 10, simulate: bool = False) -> int:
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
            _procesar_mensaje_inbound(mensaje, simulate=simulate)
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
    max_age_seconds = int(getattr(settings, "OUTBOUND_MAX_AGE_SECONDS", 900))
    drop_if_newer = str(getattr(settings, "OUTBOUND_DROP_IF_NEWER_INBOUND", "True")).lower() == "true"
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
            if max_age_seconds > 0:
                age_ms = now_ms - int(mensaje.timestamp_ms or now_ms)
                if age_ms > (max_age_seconds * 1000):
                    Mensaje.objects.filter(id=mensaje.id).update(
                        queue_status="failed",
                        error="expired_outbound",
                        processed_at_ms=_now_ms(),
                    )
                    continue

            if drop_if_newer:
                meta = mensaje.metadata_json or {}
                respuesta_ts = meta.get("respuesta_a_ts_ms") or meta.get("respuesta_a_ts")
                if respuesta_ts:
                    newer_inbound = Mensaje.objects.filter(
                        phone_number=mensaje.phone_number,
                        direccion="in",
                        timestamp_ms__gt=int(respuesta_ts),
                    ).exists()
                    if newer_inbound:
                        Mensaje.objects.filter(id=mensaje.id).update(
                            queue_status="failed",
                            error="superseded_by_newer_inbound",
                            processed_at_ms=_now_ms(),
                        )
                        continue

            if mensaje.tipo == "interactive":
                meta = mensaje.metadata_json or {}
                payloads = meta.get("interactive_payloads")
                if not payloads:
                    single = meta.get("interactive_payload")
                    payloads = [single] if single else []
                fallback_text = meta.get("interactive_fallback") or mensaje.contenido or ""
                ok = True
                message_id = None
                sent_count = 0
                interactive_error = None
                for payload in payloads:
                    if not payload:
                        continue
                    resultado = ClienteWhatsApp.enviar_interactive_con_resultado(
                        mensaje.phone_number, payload
                    )
                    if not resultado.get("ok", False):
                        ok = False
                        interactive_error = resultado.get("error") or resultado.get("response")
                        break
                    sent_count += 1
                    message_id = resultado.get("message_id") or message_id
                update_fields = {
                    "processed_at_ms": _now_ms(),
                    "error": None,
                }
                if ok:
                    update_fields["queue_status"] = "sent"
                    update_fields["delivery_status"] = "sent"
                    update_fields["wa_message_id"] = message_id or mensaje.wa_message_id
                    meta["sent_via"] = "interactive"
                    meta["interactive_sent_count"] = sent_count
                    enviados += 1
                else:
                    fallback_result = ClienteWhatsApp.enviar_mensaje_con_resultado(
                        mensaje.phone_number, fallback_text
                    )
                    if fallback_result.get("ok", False):
                        update_fields["queue_status"] = "sent"
                        update_fields["delivery_status"] = "sent"
                        update_fields["wa_message_id"] = (
                            fallback_result.get("message_id") or mensaje.wa_message_id
                        )
                        meta["sent_via"] = "fallback_text"
                        meta["interactive_error"] = interactive_error
                        enviados += 1
                    else:
                        update_fields["queue_status"] = "failed"
                        update_fields["error"] = fallback_result.get("error") or fallback_result.get("response")
                        meta["interactive_error"] = interactive_error
                update_fields["metadata_json"] = meta
                Mensaje.objects.filter(id=mensaje.id).update(**update_fields)
            else:
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
    procesados_in = procesar_inbound_pendientes(limit=limit, simulate=False)
    procesados_out = procesar_outbound_pendientes(limit=limit)
    return {"inbound": procesados_in, "outbound": procesados_out}


def simular_mensaje(
    phone_number: str,
    nombre: str,
    contenido: str,
    message_type: str = "text",
) -> dict:
    """Simula un mensaje entrante sin enviar nada a WhatsApp."""
    ahora_ms = _now_ms()
    mensaje_in = GestorMensajes.registrar_entrada(
        phone_number=phone_number,
        nombre=nombre or "",
        contenido=contenido or "",
        tipo=message_type or "text",
        timestamp_ms=ahora_ms,
        metadata={"alias_waba": nombre or ""},
        queue_status="processing",
        process_after_ms=ahora_ms,
    )
    _procesar_mensaje_inbound(mensaje_in, simulate=True)
    Mensaje.objects.filter(id=mensaje_in.id).update(
        queue_status="processed",
        processed_at_ms=_now_ms(),
        error=None,
    )
    respuesta = (
        Mensaje.objects.filter(
            direccion="out",
            metadata_json__respuesta_a_id=str(mensaje_in.id),
        )
        .order_by("-id")
        .first()
    )
    historial = list(
        Mensaje.objects.filter(phone_number=phone_number)
        .order_by("timestamp_ms", "id")
        .values("direccion", "tipo", "contenido", "timestamp_ms")[:100]
    )
    if not respuesta:
        return {"ok": False, "error": "no_response", "historial": historial}
    meta = respuesta.metadata_json or {}
    return {
        "ok": True,
        "respuesta": respuesta.contenido or "",
        "respuesta_tipo": respuesta.tipo,
        "interactive_payloads": meta.get("interactive_payloads") or meta.get("interactive_payload") or [],
        "flow_json": meta.get("flow_json"),
        "flow_id": meta.get("flow_id"),
        "historial": historial,
    }
