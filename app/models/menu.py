from django.db import models
from app.models.fields import LenientJSONField


class Menu(models.Model):
    """Modelo para menus del chatbot"""

    id = models.CharField(max_length=50, primary_key=True)
    titulo = models.CharField(max_length=255)
    submenu = models.CharField(max_length=50, default="direct")
    contenido = models.TextField()
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="hijos"
    )
    orden = models.IntegerField(default=0, db_index=True)
    opciones = LenientJSONField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "menus"

    def __str__(self) -> str:
        return f"Menu {self.id}"
