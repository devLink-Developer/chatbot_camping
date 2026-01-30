from django.db import models
from app.models.fields import LenientJSONField


class CampanaTemplate(models.Model):
    """Templates de campaña (WhatsApp)."""

    nombre = models.CharField(max_length=255, db_index=True)
    idioma = models.CharField(max_length=20, default="es_AR")
    cuerpo = models.TextField(blank=True)
    variables_json = LenientJSONField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "campana_templates"
        indexes = [models.Index(fields=["nombre", "idioma"])]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.idioma})"


class Campana(models.Model):
    """Configuración de campañas de marketing."""

    CANALES = (("whatsapp", "whatsapp"),)
    TIPOS = (
        ("cumpleanos", "cumpleanos"),
        ("manual", "manual"),
        ("segmento", "segmento"),
    )
    DIRECCIONES = (
        ("antes", "antes"),
        ("despues", "despues"),
        ("mismo_dia", "mismo_dia"),
    )

    nombre = models.CharField(max_length=255, db_index=True)
    descripcion = models.CharField(max_length=255, null=True, blank=True)
    activo = models.BooleanField(default=True)
    canal = models.CharField(max_length=50, choices=CANALES, default="whatsapp")
    tipo = models.CharField(max_length=50, choices=TIPOS, default="cumpleanos")
    direccion_offset = models.CharField(
        max_length=20, choices=DIRECCIONES, default="mismo_dia"
    )
    dias_offset = models.IntegerField(default=0)
    hora_envio = models.TimeField(null=True, blank=True)
    template = models.ForeignKey(
        CampanaTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campanas",
    )
    template_nombre = models.CharField(max_length=255, null=True, blank=True)
    template_idioma = models.CharField(max_length=20, null=True, blank=True)
    texto_estatico = models.TextField(blank=True)
    variables_json = LenientJSONField(null=True, blank=True)
    segmento_json = LenientJSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "campanas"

    def __str__(self) -> str:
        return self.nombre
