from sqlalchemy import Column, String, JSON, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base


class Menu(Base):
    """Modelo para menús del chatbot"""

    __tablename__ = "menus"

    id = Column(String(50), primary_key=True, index=True)
    titulo = Column(String(255), nullable=False)
    submenu = Column(String(50), default="direct")  # "direct" o "nested"
    contenido = Column(String(4000), nullable=False)
    opciones = Column(JSON, nullable=True)  # Lista de opciones disponibles
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Menu {self.id}>"
