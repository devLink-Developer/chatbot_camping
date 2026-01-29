import time
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from app.models.sesion import Sesion
from app.config import settings


class GestorSesion:
    """Gestiona sesiones de usuario"""

    @staticmethod
    def obtener_o_crear_sesion(
        db: Session, phone_number: str, nombre: str = ""
    ) -> Sesion:
        """Obtiene sesión existente o crea una nueva"""
        sesion = db.query(Sesion).filter(Sesion.phone_number == phone_number).first()
        
        tiempo_actual = int(time.time() * 1000)  # milliseconds

        if not sesion:
            # Nueva sesión
            sesion = Sesion(
                phone_number=phone_number,
                nombre=nombre,
                activa=True,
                estado_actual="0",
                historial_navegacion=["0"],
                inicio_sesion_ms=tiempo_actual,
                ultimo_acceso_ms=tiempo_actual,
                primer_acceso=True,
            )
            db.add(sesion)
            db.commit()
            db.refresh(sesion)
        else:
            # Actualizar sesión existente
            sesion.ultimo_acceso_ms = tiempo_actual
            sesion.activa = True
            
            # Verificar si la sesión ha expirado
            inactividad_ms = tiempo_actual - sesion.ultimo_acceso_ms
            if inactividad_ms > settings.inactive_timeout_seconds * 1000:
                # Resetear sesión si ha expirado
                sesion.estado_actual = "0"
                sesion.historial_navegacion = ["0"]
                sesion.intentos_fallidos = 0
            
            db.commit()
            db.refresh(sesion)

        return sesion

    @staticmethod
    def actualizar_estado(
        db: Session,
        phone_number: str,
        nuevo_estado: str,
        historial: List[str],
        mensaje: str = "",
    ) -> Sesion:
        """Actualiza el estado actual y el historial de navegación"""
        sesion = db.query(Sesion).filter(Sesion.phone_number == phone_number).first()
        
        if sesion:
            sesion.estado_actual = nuevo_estado
            sesion.historial_navegacion = historial
            sesion.ultimo_mensaje = mensaje
            sesion.timestamp_ultimo_mensaje = int(time.time() * 1000)
            db.commit()
            db.refresh(sesion)

        return sesion

    @staticmethod
    def incrementar_intentos_fallidos(db: Session, phone_number: str) -> int:
        """Incrementa contador de intentos fallidos"""
        sesion = db.query(Sesion).filter(Sesion.phone_number == phone_number).first()
        
        if sesion:
            sesion.intentos_fallidos += 1
            db.commit()
            db.refresh(sesion)
            return sesion.intentos_fallidos

        return 1

    @staticmethod
    def resetear_intentos_fallidos(db: Session, phone_number: str):
        """Resetea contador de intentos fallidos"""
        sesion = db.query(Sesion).filter(Sesion.phone_number == phone_number).first()
        
        if sesion:
            sesion.intentos_fallidos = 0
            db.commit()

    @staticmethod
    def es_sesion_valida(sesion: Sesion) -> bool:
        """Verifica si la sesión es válida y no ha expirado"""
        tiempo_actual = int(time.time() * 1000)
        inactividad_ms = tiempo_actual - sesion.ultimo_acceso_ms
        
        return sesion.activa and inactividad_ms <= settings.session_timeout_seconds * 1000
