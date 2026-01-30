import time
from typing import Tuple

from app.models.cliente import Cliente


class GestorCliente:
    """Gestiona clientes por numero de telefono."""

    @staticmethod
    def registrar_contacto(
        phone_number: str,
        nombre: str,
        mensaje: str,
        alias_waba: str | None = None,
    ) -> Tuple[Cliente, bool]:
        """Crea o actualiza un cliente. Retorna (cliente, es_nuevo)."""
        ahora_ms = int(time.time() * 1000)
        cliente = Cliente.objects.filter(phone_number=phone_number).first()

        if not cliente:
            cliente = Cliente.objects.create(
                phone_number=phone_number,
                nombre=nombre or None,
                alias_waba=alias_waba or None,
                primer_contacto_ms=ahora_ms,
                ultimo_contacto_ms=ahora_ms,
                mensajes_totales=1,
                ultimo_mensaje=mensaje,
                activo=True,
            )
            return cliente, True

        if nombre and not cliente.nombre:
            cliente.nombre = nombre
        if alias_waba and not cliente.alias_waba:
            cliente.alias_waba = alias_waba
        cliente.ultimo_contacto_ms = ahora_ms
        cliente.mensajes_totales += 1
        cliente.ultimo_mensaje = mensaje
        cliente.activo = True
        cliente.save()
        return cliente, False
