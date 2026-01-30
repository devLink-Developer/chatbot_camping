from django.db import models
from app.models.fields import LenientJSONField
from app.models.campana import Campana
from app.models.cliente import Cliente


class CampanaEnvio(models.Model):
    """Registro de envíos de campañas."""

    ESTADOS = (
        ("programado", "programado"),
        ("enviado", "enviado"),
        ("fallido", "fallido"),
        ("omitido", "omitido"),
    )

    campana = models.ForeignKey(Campana, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="programado")
    programado_para = models.DateTimeField(null=True, blank=True)
    enviado_en = models.DateTimeField(null=True, blank=True)
    error = models.CharField(max_length=500, null=True, blank=True)
    payload_json = LenientJSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "campana_envios"
        indexes = [
            models.Index(fields=["campana", "estado"]),
            models.Index(fields=["cliente", "estado"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["campana", "cliente", "programado_para"],
                name="uniq_campana_cliente_programado",
            )
        ]

    def __str__(self) -> str:
        return f"{self.campana_id} -> {self.cliente_id} ({self.estado})"
