from sqlalchemy import Column, String, JSON, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Config(Base):
    """Modelo para configuración del bot"""

    __tablename__ = "config"

    id = Column(String(100), primary_key=True, index=True)
    seccion = Column(String(100), nullable=False, index=True)
    valor = Column(JSON, nullable=False)
    descripcion = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Config {self.id}>"
