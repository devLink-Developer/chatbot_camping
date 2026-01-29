from sqlalchemy import Column, String, DateTime, JSON, BigInteger
from sqlalchemy.sql import func
from app.database import Base


class Registro(Base):
    """Modelo para auditoría y registro de interacciones"""

    __tablename__ = "registros"

    id = Column(String(50), primary_key=True, index=True)
    phone_number = Column(String(20), nullable=False, index=True)
    nombre = Column(String(255), nullable=True)
    
    # Mensaje del usuario
    mensaje_usuario = Column(String(1000), nullable=False)
    
    # Clasificación de entrada
    tipo_entrada = Column(String(50), nullable=False)  # comando, menu, submenu, error
    accion = Column(String(100), nullable=False)  # ir_menu, ir_submenu, mostrar_respuesta, etc.
    target = Column(String(50), nullable=False)
    
    # Respuesta del bot
    respuesta_enviada = Column(String(4096), nullable=True)
    
    # Timestamps
    timestamp_usuario = Column(BigInteger, nullable=False)
    timestamp_ms = Column(BigInteger, nullable=False)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now(), index=True)

    def __repr__(self):
        return f"<Registro {self.id}>"
