from django.db import models
from app.models.fields import LenientJSONField


class Mensaje(models.Model):
    """Mensajes entrantes y salientes (conversaciones)."""

    DIRECCIONES = (
        ("in", "entrante"),
        ("out", "saliente"),
        ("system", "sistema"),
    )

    QUEUE_STATUS = (
        ("pending", "pendiente"),
        ("processing", "procesando"),
        ("processed", "procesado"),
        ("queued", "en cola"),
        ("sent", "enviado"),
        ("failed", "fallido"),
    )

    phone_number = models.CharField(max_length=20, db_index=True)
    nombre = models.CharField(max_length=255, null=True, blank=True)
    direccion = models.CharField(max_length=10, choices=DIRECCIONES, db_index=True)
    tipo = models.CharField(max_length=50, default="text", db_index=True)
    contenido = models.CharField(max_length=4096, null=True, blank=True)
    wa_message_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    timestamp_ms = models.BigIntegerField(db_index=True)
    queue_status = models.CharField(
        max_length=20,
        choices=QUEUE_STATUS,
        default="processed",
        db_index=True,
    )
    delivery_status = models.CharField(max_length=30, null=True, blank=True, db_index=True)
    delivery_timestamp_ms = models.BigIntegerField(null=True, blank=True)
    process_after_ms = models.BigIntegerField(null=True, blank=True, db_index=True)
    locked_at_ms = models.BigIntegerField(null=True, blank=True)
    processed_at_ms = models.BigIntegerField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    error = models.TextField(null=True, blank=True)
    metadata_json = LenientJSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "mensajes"
        constraints = [
            models.UniqueConstraint(
                fields=["wa_message_id"],
                condition=models.Q(direccion="in") & models.Q(wa_message_id__isnull=False),
                name="uniq_inbound_wa_message_id",
            )
        ]
        indexes = [
            models.Index(fields=["direccion", "queue_status"], name="msg_queue_dir_status_idx"),
            models.Index(fields=["queue_status", "process_after_ms"], name="msg_queue_due_idx"),
        ]

    def __str__(self) -> str:
        return f"Mensaje {self.phone_number} {self.direccion}"
