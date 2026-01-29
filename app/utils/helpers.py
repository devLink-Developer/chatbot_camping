"""
Utilidades para el chatbot
"""

import uuid
import time
from typing import List
from datetime import datetime, timezone


def generar_uuid() -> str:
    """Genera un UUID v4"""
    return str(uuid.uuid4())


def obtener_timestamp_ms() -> int:
    """Obtiene timestamp actual en milisegundos"""
    return int(time.time() * 1000)


def obtener_timestamp_iso() -> str:
    """Obtiene timestamp en formato ISO 8601"""
    return datetime.now(timezone.utc).isoformat()


def formatear_numero_telefono(phone: str) -> str:
    """
    Formatea número de teléfono a formato estándar
    
    Args:
        phone: Número de teléfono
        
    Returns:
        Número formateado (+54...)
    """
    phone_clean = phone.replace("+", "").replace(" ", "").replace("-", "")

    if phone_clean.startswith("549"):
        # Argentina sin +
        return "+54" + phone_clean[3:]
    elif phone_clean.startswith("54"):
        # Argentina con +54
        return "+" + phone_clean
    else:
        # Asumir que lleva código de país
        return "+" + phone_clean if not phone_clean.startswith("+") else phone_clean


def truncar_texto(texto: str, longitud: int = 500, sufijo: str = "...") -> str:
    """
    Trunca texto a longitud máxima
    
    Args:
        texto: Texto a truncar
        longitud: Longitud máxima
        sufijo: Sufijo a agregar si se trunca
        
    Returns:
        Texto truncado
    """
    if len(texto) <= longitud:
        return texto
    return texto[: longitud - len(sufijo)] + sufijo


def paginar_lista(items: List, pagina: int = 1, por_pagina: int = 10) -> tuple:
    """
    Pagina una lista
    
    Args:
        items: Lista a paginar
        pagina: Número de página (1-indexed)
        por_pagina: Elementos por página
        
    Returns:
        (items_pagina, total_paginas, total_elementos)
    """
    total = len(items)
    total_paginas = (total + por_pagina - 1) // por_pagina
    
    inicio = (pagina - 1) * por_pagina
    fin = inicio + por_pagina
    
    items_pagina = items[inicio:fin]
    
    return items_pagina, total_paginas, total


def parsear_json_seguro(texto: str, default=None):
    """
    Parsea JSON de forma segura
    
    Args:
        texto: String JSON
        default: Valor por defecto si falla
        
    Returns:
        Objeto parseado o default
    """
    import json
    try:
        return json.loads(texto)
    except (json.JSONDecodeError, TypeError):
        return default


def validar_email(email: str) -> bool:
    """Valida formato de email básico"""
    import re
    patron = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(patron, email) is not None
