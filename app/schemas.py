from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


# Schemas de entrada
class MessageEntry(BaseModel):
    """Estructura de entrada de WhatsApp webhook"""

    object: str
    entry: List[Dict[str, Any]]


class SesionResponse(BaseModel):
    """Respuesta con info de sesión"""

    phone_number: str
    nombre: Optional[str]
    estado_actual: str
    historial_navegacion: List[str]
    activa: bool


class ContenidoResponse(BaseModel):
    """Respuesta con contenido (menú o respuesta)"""

    tipo: str  # menu, respuesta, help
    id: str
    contenido: str
    titulo: Optional[str] = None
    categoria: Optional[str] = None


class RegistroResponse(BaseModel):
    """Registro de interacción"""

    id: str
    phone_number: str
    mensaje_usuario: str
    tipo_entrada: str
    accion: str
    target: str
    respuesta_enviada: Optional[str]


class ChatbotResponse(BaseModel):
    """Respuesta completa del chatbot"""

    success: bool
    sesion: SesionResponse
    contenido: Optional[ContenidoResponse]
    mensaje: Optional[str]
    error: Optional[str]
