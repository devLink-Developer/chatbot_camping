from sqlalchemy import Column, String, JSON, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base


class Respuesta(Base):
    """Modelo para respuestas del chatbot"""

    __tablename__ = "respuestas"

    id = Column(String(50), primary_key=True, index=True)
    categoria = Column(String(100), nullable=False, index=True)
    contenido = Column(String(4096), nullable=False)
    siguientes_pasos = Column(JSON, default=["0", "#"])  # Botones de navegación
    metadata = Column(JSON, nullable=True)  # Información adicional
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Respuesta {self.id}>"
