from django.db import models
from app.models.fields import LenientJSONField


def default_historial():
    return ["0"]


class Sesion(models.Model):
    """Modelo para gestion de sesiones de usuario"""

    phone_number = models.CharField(max_length=20, primary_key=True)
    nombre = models.CharField(max_length=255, null=True, blank=True)
    activa = models.BooleanField(default=True)

    estado_actual = models.CharField(max_length=50, default="0")
    historial_navegacion = LenientJSONField(default=default_historial)

    ultimo_mensaje = models.CharField(max_length=500, null=True, blank=True)
    timestamp_ultimo_mensaje = models.BigIntegerField(null=True, blank=True)

    inicio_sesion_ms = models.BigIntegerField()
    ultimo_acceso_ms = models.BigIntegerField()

    primer_acceso = models.BooleanField(default=True)
    intentos_fallidos = models.BigIntegerField(default=0)
    datos_extra = LenientJSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sesiones"

    def __str__(self) -> str:
        return f"Sesion {self.phone_number}"
