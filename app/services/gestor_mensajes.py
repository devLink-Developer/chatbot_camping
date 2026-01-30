import time
from typing import Optional

from django.db import IntegrityError

from app.models.mensaje import Mensaje


class GestorMensajes:
    """Registra mensajes entrantes y salientes."""

    @staticmethod
    def registrar_entrada(
        phone_number: str,
        nombre: str,
        contenido: str,
        tipo: str,
        timestamp_ms: Optional[int] = None,
        wa_message_id: str | None = None,
        metadata: Optional[dict] = None,
        queue_status: str = "pending",
        process_after_ms: Optional[int] = None,
    ) -> Mensaje:
        defaults = dict(
            phone_number=phone_number,
            nombre=nombre or None,
            direccion="in",
            tipo=tipo or "text",
            contenido=contenido,
            wa_message_id=wa_message_id,
            timestamp_ms=timestamp_ms or int(time.time() * 1000),
            metadata_json=metadata or None,
            queue_status=queue_status,
            process_after_ms=process_after_ms,
        )
        if wa_message_id:
            existing = Mensaje.objects.filter(
                direccion="in", wa_message_id=wa_message_id
            ).first()
            if existing:
                return existing
        try:
            return Mensaje.objects.create(**defaults)
        except IntegrityError:
            if wa_message_id:
                existing = Mensaje.objects.filter(
                    direccion="in", wa_message_id=wa_message_id
                ).first()
                if existing:
                    return existing
            raise

    @staticmethod
    def registrar_salida(
        phone_number: str,
        nombre: str,
        contenido: str,
        tipo: str = "text",
        timestamp_ms: Optional[int] = None,
        metadata: Optional[dict] = None,
        queue_status: str = "queued",
        process_after_ms: Optional[int] = None,
    ) -> Mensaje:
        return Mensaje.objects.create(
            phone_number=phone_number,
            nombre=nombre or None,
            direccion="out",
            tipo=tipo or "text",
            contenido=contenido,
            timestamp_ms=timestamp_ms or int(time.time() * 1000),
            metadata_json=metadata or None,
            queue_status=queue_status,
            process_after_ms=process_after_ms,
        )
