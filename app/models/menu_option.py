from django.db import models

from app.models.menu import Menu
from app.models.respuesta import Respuesta


class MenuOption(models.Model):
    """Opciones de un menu y su destino (menu o respuesta)."""

    menu = models.ForeignKey(
        Menu, on_delete=models.CASCADE, related_name="opciones_items"
    )
    key = models.CharField(max_length=10)
    label = models.CharField(max_length=255)
    target_menu = models.ForeignKey(
        Menu,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opciones_padre",
    )
    target_respuesta = models.ForeignKey(
        Respuesta,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opciones_respuesta",
    )
    orden = models.IntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "menu_opciones"
        constraints = [
            models.UniqueConstraint(fields=["menu", "key"], name="uniq_menu_key")
        ]
        indexes = [
            models.Index(fields=["menu", "orden"]),
            models.Index(fields=["menu", "key"]),
        ]

    def __str__(self) -> str:
        return f"{self.menu_id}:{self.key}"
