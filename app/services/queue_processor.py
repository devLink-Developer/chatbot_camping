import logging
import random
import time
from datetime import date

from django.conf import settings
from django.db import transaction, close_old_connections, models
from django.db.utils import NotSupportedError

from app.models.mensaje import Mensaje
from app.models.cliente import Cliente
from app.services import (
    GestorCliente,
    GestorContenido,
    GestorMensajes,
    GestorSesion,
    NavigadorBot,
    ValidadorEntrada,
)
from app.services.cliente_whatsapp import ClienteWhatsApp
from app.services.interactive_builder import (
    build_menu_interactive_payloads,
    build_flow_interactive_payload,
    build_navigation_interactive_payload,
)
from app.services.waba_config import get_whatsapp_bool, get_whatsapp_setting

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


def _parse_flow_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    valor = str(value).strip()
    if not valor:
        return None
    if len(valor) >= 10:
        valor = valor[:10]
    try:
        return date.fromisoformat(valor)
    except ValueError:
        return None


def _coerce_optin(value) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    valor = str(value).strip().lower()
    if valor in {"true", "1", "si", "sí", "yes", "y"}:
        return True
    if valor in {"false", "0", "no", "n"}:
        return False
    return None


def _actualizar_cliente_desde_flow(phone_number: str, metadata: dict) -> list[str]:
    flow_data = metadata.get("flow_client_data") or {}
    if not isinstance(flow_data, dict) or not flow_data:
        return []

    cliente = Cliente.objects.filter(phone_number=phone_number).first()
    if not cliente:
        return []

    updated_fields: list[str] = []

    nombre_completo = flow_data.get("nombre_completo")
    if isinstance(nombre_completo, str):
        nombre_limpio = " ".join(nombre_completo.split())
        if nombre_limpio and cliente.nombre != nombre_limpio:
            cliente.nombre = nombre_limpio
            updated_fields.append("nombre")

    fecha_raw = flow_data.get("fecha_nacimiento")
    fecha_nacimiento = _parse_flow_date(fecha_raw)
    if fecha_raw and not fecha_nacimiento:
        logger.warning(
            "No se pudo parsear fecha_nacimiento del flow para %s: %r",
            phone_number,
            fecha_raw,
        )
    if fecha_nacimiento and cliente.fecha_nacimiento != fecha_nacimiento:
        cliente.fecha_nacimiento = fecha_nacimiento
        updated_fields.append("fecha_nacimiento")

    tos_optin_raw = flow_data.get("tos_optin")
    marketing_opt_in = _coerce_optin(tos_optin_raw)
    if tos_optin_raw is not None and marketing_opt_in is None:
        logger.warning(
            "No se pudo parsear tos_optin del flow para %s: %r",
            phone_number,
            tos_optin_raw,
        )
    if marketing_opt_in is not None and cliente.marketing_opt_in != marketing_opt_in:
        cliente.marketing_opt_in = marketing_opt_in
        updated_fields.append("marketing_opt_in")

    if updated_fields:
        cliente.save(update_fields=updated_fields + ["updated_at"])
    return updated_fields


def _mensaje_confirmacion_club_beneficios() -> str:
    configured = GestorContenido.obtener_config_mensaje("club_beneficios_confirmacion")
    if configured:
        return configured
    return (
        "🎉 ¡Listo! Ya sos parte del Club de Beneficios del Camping ACA.\n\n"
        "A partir de ahora podrás recibir:\n"
        "🔥 Cupones de descuento\n"
        "💰 Promociones exclusivas\n"
        "🎟 Beneficios especiales por cantidad\n"
        "🎂 Descuentos por cumpleaños\n"
        "🎉 Promos sorpresa durante el año\n\n"
        "Cuando haya novedades, te las enviaremos por este medio.\n\n"
        "Si en algún momento querés dejar de recibirlas, escribí BAJA."
    )


def _es_comando_baja_promociones(mensaje_usuario: str, validacion) -> bool:
    if not mensaje_usuario:
        return False
    entrada_limpia = getattr(validacion, "entrada_limpia", "") or ""
    return entrada_limpia == "BAJA"


def _registrar_baja_promociones(phone_number: str) -> bool:
    cliente = Cliente.objects.filter(phone_number=phone_number).first()
    if not cliente:
        return False
    if cliente.marketing_opt_in is False:
        return False
    cliente.marketing_opt_in = False
    cliente.save(update_fields=["marketing_opt_in", "updated_at"])
    return True


def _mensaje_baja_club_beneficios() -> str:
    configured = (
        GestorContenido.obtener_config_mensaje("club_beneficios_baja_confirmacion")
        or GestorContenido.obtener_config_mensaje("club_beneficios_baja")
    )
    if configured:
        return configured
    return (
        "✅ Registramos tu BAJA del Club de Beneficios del Camping ACA.\n\n"
        "A partir de ahora no te enviaremos promociones por este medio."
    )


def _procesar_mensaje_inbound(mensaje_in: Mensaje, simulate: bool = False) -> None:
    datos = mensaje_in.metadata_json or {}
    inbound_phone_id = datos.get("phone_number_id")
    expected_phone_id = get_whatsapp_setting(
        "phone_id", getattr(settings, "WHATSAPP_PHONE_ID", "")
    )
    if expected_phone_id and inbound_phone_id and str(inbound_phone_id) != str(expected_phone_id):
        logger.warning(
            "Inbound ignorado: phone_number_id %s != activo %s",
            inbound_phone_id,
            expected_phone_id,
        )
        datos.update(
            {
                "ignored_reason": "phone_id_mismatch",
                "expected_phone_id": expected_phone_id,
                "actual_phone_id": inbound_phone_id,
            }
        )
        mensaje_in.metadata_json = datos
        mensaje_in.save(update_fields=["metadata_json"])
        return
    phone_number = mensaje_in.phone_number
    mensaje_usuario = mensaje_in.contenido or ""
    nombre_usuario = mensaje_in.nombre or ""
    alias_waba = datos.get("alias_waba") or ""
    message_type = mensaje_in.tipo or "text"
    is_textual = message_type in ("text", "interactive")
    wa_message_id = mensaje_in.wa_message_id

    _marcar_leido_y_typing(wa_message_id, simulate=simulate)

    now_ms = _now_ms()
    cliente_prev = Cliente.objects.filter(phone_number=phone_number).first()
    prev_contact_ms = cliente_prev.ultimo_contacto_ms if cliente_prev else None

    sesion, sesion_expirada = GestorSesion.obtener_o_crear_sesion(
        phone_number, nombre_usuario
    )
    _, cliente_nuevo = GestorCliente.registrar_contacto(
        phone_number, nombre_usuario, mensaje_usuario, alias_waba=alias_waba
    )
    flow_updated_fields = _actualizar_cliente_desde_flow(phone_number, datos)
    flow_client_data_received = bool(datos.get("flow_client_data"))

    validacion = ValidadorEntrada.validar(mensaje_usuario)
    baja_promociones = _es_comando_baja_promociones(mensaje_usuario, validacion)
    baja_promociones_actualizada = False
    if baja_promociones:
        baja_promociones_actualizada = _registrar_baja_promociones(phone_number)

    if flow_client_data_received:
        estado_nuevo = "0"
        historial_nuevo = ["0"]
        tipo_contenido = "menu"
        target = "0"
        es_valido = True
    elif baja_promociones:
        estado_nuevo = "0"
        historial_nuevo = ["0"]
        tipo_contenido = "menu"
        target = "0"
        es_valido = True
    elif cliente_nuevo:
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
        last_content_type = (sesion.datos_extra or {}).get("last_content_type")
        estado_nuevo, historial_nuevo, tipo_contenido, target, es_valido = (
            NavigadorBot.procesar_entrada(
                mensaje_usuario,
                sesion.historial_navegacion,
                sesion.estado_actual,
                last_content_type,
            )
        )

    if flow_client_data_received:
        tipo_entrada = "flow_cliente_actualizado"
        accion = "flow_cliente_actualizado"
    elif baja_promociones:
        tipo_entrada = "baja_promociones"
        accion = "baja_promociones"
    elif cliente_nuevo:
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
            "prev_contact_ms": prev_contact_ms,
            "message_type": message_type,
            "tipo_entrada": tipo_entrada,
            "accion": accion,
            "target": target,
            "flow_client_data_received": bool(datos.get("flow_client_data")),
            "flow_client_data_updated_fields": flow_updated_fields,
            "baja_promociones": baja_promociones,
            "marketing_opt_in_updated": baja_promociones_actualizada,
        }
    )
    mensaje_in.metadata_json = inbound_meta
    mensaje_in.save(update_fields=["metadata_json"])

    respuesta_texto = ""
    interactive_body = ""
    menu_id_for_interactive = None
    interactive_navigation_only = False
    pre_menu_text_message = ""
    menu_texto_principal = ""

    if flow_client_data_received:
        confirmacion = _mensaje_confirmacion_club_beneficios()
        contenido_menu = NavigadorBot.obtener_contenido("0", "menu")
        menu_texto = contenido_menu["contenido"] if contenido_menu else ""
        pre_menu_text_message = confirmacion
        menu_texto_principal = menu_texto
        respuesta_texto = f"{confirmacion}\n\n{menu_texto}".strip()
        interactive_body = "Ya sos parte del Club de Beneficios."
        menu_id_for_interactive = "0"
    elif baja_promociones:
        confirmacion = _mensaje_baja_club_beneficios()
        contenido_menu = NavigadorBot.obtener_contenido("0", "menu")
        menu_texto = contenido_menu["contenido"] if contenido_menu else ""
        pre_menu_text_message = confirmacion
        menu_texto_principal = menu_texto
        respuesta_texto = f"{confirmacion}\n\n{menu_texto}".strip()
        interactive_body = "Preferencias de promociones actualizadas."
        menu_id_for_interactive = "0"
    elif cliente_nuevo:
        bienvenida = GestorContenido.obtener_config_mensaje("bienvenida") or ""
        contenido_menu = NavigadorBot.obtener_contenido("0", "menu")
        menu_texto = contenido_menu["contenido"] if contenido_menu else ""
        respuesta_texto = f"{bienvenida}\n\n{menu_texto}".strip()
        interactive_body = bienvenida or "Bienvenido"
        menu_id_for_interactive = "0"
    elif sesion_expirada:
        retorno_threshold_ms = 24 * 60 * 60 * 1000
        saludo_retorno = (
            GestorContenido.obtener_config_mensaje("bienvenida_retorno")
            or "¡Hola de nuevo! Qué gusto verte por acá. ¿En qué puedo ayudarte hoy?"
        )
        error_default = (
            GestorContenido.obtener_config_mensaje("error_sesion")
            or "Tu sesión ha expirado. Por favor, inicia nuevamente."
        )
        use_return_greeting = (
            (not cliente_nuevo)
            and prev_contact_ms
            and (now_ms - int(prev_contact_ms)) >= retorno_threshold_ms
        )
        error_sesion = saludo_retorno if use_return_greeting else error_default
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
        contenido = NavigadorBot.obtener_contenido(
            target, tipo_contenido, menu_contexto_id=estado_nuevo
        )
        if contenido:
            respuesta_texto = contenido["contenido"]
            if tipo_contenido == "menu":
                interactive_body = contenido.get("titulo") or "Selecciona una opcion"
                menu_id_for_interactive = target or "0"
            elif tipo_contenido == "respuesta":
                interactive_body = respuesta_texto
                menu_id_for_interactive = estado_nuevo or "0"
                interactive_navigation_only = True
        else:
            respuesta_texto = (
                "Error: No se encontro el contenido solicitado.\n"
                f"{GestorContenido.NAV_MAIN_LINE}"
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
                f"{GestorContenido.NAV_MAIN_LINE}"
            )
            interactive_body = "Opcion no valida."
            menu_id_for_interactive = "0"

    GestorSesion.actualizar_estado(
        phone_number,
        estado_nuevo,
        historial_nuevo,
        mensaje_usuario,
        tipo_contenido=tipo_contenido,
    )

    interactive_enabled = get_whatsapp_bool(
        "interactive_enabled",
        getattr(settings, "WHATSAPP_INTERACTIVE_ENABLED", False),
    )
    flow_enabled = get_whatsapp_bool(
        "flow_enabled",
        getattr(settings, "WHATSAPP_FLOW_ENABLED", False),
    )
    flow_cta = getattr(settings, "WHATSAPP_FLOW_CTA_TEXT", "Ver opciones")
    flow_version = getattr(settings, "WHATSAPP_FLOW_MESSAGE_VERSION", "3")
    interactive_payloads = None
    interactive_fallback = None
    if interactive_enabled and interactive_navigation_only:
        respuesta_texto = GestorContenido.quitar_navegacion(respuesta_texto).strip()
        interactive_body = respuesta_texto or interactive_body

    if interactive_enabled and menu_id_for_interactive:
        menu = GestorContenido.obtener_menu(menu_id_for_interactive) or GestorContenido.obtener_menu("0")
        if menu:
            if (not interactive_navigation_only) and flow_enabled and menu.flow_id:
                flow_payload = build_flow_interactive_payload(
                    menu,
                    body_text=interactive_body or (menu.titulo or ""),
                    cta_text=flow_cta,
                    message_version=flow_version,
                )
                if flow_payload:
                    interactive_payloads = [flow_payload]
            if not interactive_payloads:
                if interactive_navigation_only:
                    interactive_payloads = [
                        build_navigation_interactive_payload(
                            body_text=interactive_body or "Elegi una opcion de navegacion",
                            include_back=True,
                        )
                    ]
                else:
                    interactive_payloads = build_menu_interactive_payloads(
                        menu,
                        body_text=interactive_body or (menu.titulo or ""),
                    )
            if interactive_payloads:
                if pre_menu_text_message and menu_texto_principal:
                    interactive_fallback = menu_texto_principal
                else:
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
        "flow_enabled": flow_enabled,
        "simulated": simulate,
    }
    if menu_id_for_interactive:
        menu_ref = GestorContenido.obtener_menu(menu_id_for_interactive) or GestorContenido.obtener_menu("0")
        if menu_ref and menu_ref.flow_id:
            outbound_meta["flow_id"] = menu_ref.flow_id
        if menu_ref and menu_ref.flow_json and simulate:
            outbound_meta["flow_json"] = menu_ref.flow_json
    if interactive_payloads:
        outbound_meta["interactive_payloads"] = interactive_payloads
        outbound_meta["interactive_fallback"] = interactive_fallback
        outbound_tipo = "interactive"
    else:
        outbound_tipo = "text"

    outbound_status = "processed" if simulate else "queued"
    process_after = _now_ms() if simulate else (_now_ms() + delay_ms)
    if pre_menu_text_message and interactive_payloads:
        confirmacion_meta = dict(outbound_meta)
        confirmacion_meta["tipo_contenido"] = "confirmacion_pre_menu"
        confirmacion_meta["flow_followup"] = "menu_interactive"
        GestorMensajes.registrar_salida(
            phone_number=phone_number,
            nombre=nombre_usuario,
            contenido=pre_menu_text_message,
            tipo="text",
            metadata=confirmacion_meta,
            queue_status=outbound_status,
            process_after_ms=process_after,
        )
        respuesta_texto = menu_texto_principal or respuesta_texto

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
