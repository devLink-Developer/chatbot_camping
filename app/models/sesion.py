from sqlalchemy import Column, String, JSON, DateTime, Boolean, BigInteger
from sqlalchemy.sql import func
from app.database import Base


class Sesion(Base):
    """Modelo para gestión de sesiones de usuario"""

    __tablename__ = "sesiones"

    phone_number = Column(String(20), primary_key=True, index=True)
    nombre = Column(String(255), nullable=True)
    activa = Column(Boolean, default=True)
    
    # Estado de navegación
    estado_actual = Column(String(50), default="0")
    historial_navegacion = Column(JSON, default=["0"])
    
    # Temporal
    ultimo_mensaje = Column(String(500), nullable=True)
    timestamp_ultimo_mensaje = Column(BigInteger, nullable=True)
    
    # Control de sesión
    inicio_sesion_ms = Column(BigInteger, nullable=False)
    ultimo_acceso_ms = Column(BigInteger, nullable=False)
    
    # Metadata
    primer_acceso = Column(Boolean, default=True)
    intentos_fallidos = Column(BigInteger, default=0)
    datos_extra = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Sesion {self.phone_number}>"
