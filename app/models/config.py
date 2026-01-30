from django.db import models
from app.models.fields import LenientJSONField


class Config(models.Model):
    """Modelo para configuracion del bot"""

    id = models.CharField(max_length=100, primary_key=True)
    seccion = models.CharField(max_length=100, db_index=True)
    valor = LenientJSONField()
    descripcion = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "config"

    def __str__(self) -> str:
        return f"Config {self.id}"
