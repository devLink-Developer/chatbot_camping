from django.db import models


class Cliente(models.Model):
    """Clientes registrados por telefono."""

    phone_number = models.CharField(max_length=20, primary_key=True)
    nombre = models.CharField(max_length=255, null=True, blank=True)
    alias_waba = models.CharField(max_length=255, null=True, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    direccion = models.CharField(max_length=255, null=True, blank=True)
    correo = models.EmailField(null=True, blank=True)
    marketing_opt_in = models.BooleanField(default=True)
    primer_contacto_ms = models.BigIntegerField()
    ultimo_contacto_ms = models.BigIntegerField()
    mensajes_totales = models.BigIntegerField(default=0)
    ultimo_mensaje = models.CharField(max_length=1000, null=True, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clientes"

    def __str__(self) -> str:
        return f"Cliente {self.phone_number}"
