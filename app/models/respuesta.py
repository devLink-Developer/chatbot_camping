from django.db import models
from app.models.fields import LenientJSONField


def default_siguientes_pasos():
    return ["0", "#"]


class Respuesta(models.Model):
    """Modelo para respuestas del chatbot"""

    id = models.CharField(max_length=50, primary_key=True)
    categoria = models.CharField(max_length=100, db_index=True)
    contenido = models.CharField(max_length=4096)
    siguientes_pasos = LenientJSONField(default=default_siguientes_pasos)
    metadata_json = LenientJSONField(db_column="metadata", null=True, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "respuestas"

    def __str__(self) -> str:
        return f"Respuesta {self.id}"
