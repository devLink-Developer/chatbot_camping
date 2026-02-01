import time
from typing import List

from django.conf import settings

from app.models.sesion import Sesion


class GestorSesion:
    """Gestiona sesiones de usuario"""

    @staticmethod
    def obtener_o_crear_sesion(phone_number: str, nombre: str = "") -> tuple[Sesion, bool]:
        """Obtiene sesion existente o crea una nueva. Retorna (sesion, expirada)."""
        sesion = Sesion.objects.filter(phone_number=phone_number).first()

        tiempo_actual = int(time.time() * 1000)

        if not sesion:
            sesion = Sesion.objects.create(
                phone_number=phone_number,
                nombre=nombre,
                activa=True,
                estado_actual="0",
                historial_navegacion=["0"],
                inicio_sesion_ms=tiempo_actual,
                ultimo_acceso_ms=tiempo_actual,
                primer_acceso=True,
            )
            return sesion, False

        inactividad_ms = tiempo_actual - sesion.ultimo_acceso_ms
        expirada = inactividad_ms > settings.SESSION_TIMEOUT_SECONDS * 1000

        sesion.ultimo_acceso_ms = tiempo_actual
        sesion.primer_acceso = False

        if expirada:
            sesion.activa = False
            sesion.estado_actual = "0"
            sesion.historial_navegacion = ["0"]
            sesion.intentos_fallidos = 0
            extra = sesion.datos_extra or {}
            extra["last_closed_ms"] = tiempo_actual
            extra["last_close_reason"] = "timeout"
            sesion.datos_extra = extra
        else:
            sesion.activa = True

        sesion.save()
        return sesion, expirada

    @staticmethod
    def actualizar_estado(
        phone_number: str,
        nuevo_estado: str,
        historial: List[str],
        mensaje: str = "",
    ) -> Sesion:
        """Actualiza el estado actual y el historial de navegacion"""
        sesion = Sesion.objects.filter(phone_number=phone_number).first()

        if sesion:
            sesion.estado_actual = nuevo_estado
            sesion.historial_navegacion = historial
            sesion.ultimo_mensaje = mensaje
            sesion.timestamp_ultimo_mensaje = int(time.time() * 1000)
            sesion.save()

        return sesion

    @staticmethod
    def incrementar_intentos_fallidos(phone_number: str) -> int:
        """Incrementa contador de intentos fallidos"""
        sesion = Sesion.objects.filter(phone_number=phone_number).first()

        if sesion:
            sesion.intentos_fallidos += 1
            sesion.save()
            return sesion.intentos_fallidos

        return 1

    @staticmethod
    def resetear_intentos_fallidos(phone_number: str) -> None:
        """Resetea contador de intentos fallidos"""
        Sesion.objects.filter(phone_number=phone_number).update(intentos_fallidos=0)

    @staticmethod
    def es_sesion_valida(sesion: Sesion) -> bool:
        """Verifica si la sesion es valida y no ha expirado"""
        tiempo_actual = int(time.time() * 1000)
        inactividad_ms = tiempo_actual - sesion.ultimo_acceso_ms

        return sesion.activa and inactividad_ms <= settings.SESSION_TIMEOUT_SECONDS * 1000
