from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.menu import Menu
from app.models.respuesta import Respuesta


class GestorContenido:
    """Gestiona menús y respuestas desde BD"""

    @staticmethod
    def obtener_menu(db: Session, menu_id: str) -> Optional[Menu]:
        """Obtiene un menú por ID"""
        return db.query(Menu).filter(Menu.id == menu_id, Menu.activo == True).first()

    @staticmethod
    def obtener_respuesta(db: Session, respuesta_id: str) -> Optional[Respuesta]:
        """Obtiene una respuesta por ID"""
        return (
            db.query(Respuesta)
            .filter(Respuesta.id == respuesta_id, Respuesta.activo == True)
            .first()
        )

    @staticmethod
    def obtener_config_mensaje(db: Session, clave: str) -> Optional[str]:
        """Obtiene mensaje de configuración"""
        from app.models.config import Config

        config = (
            db.query(Config)
            .filter(Config.id == f"mensaje_{clave}")
            .first()
        )
        return config.valor.get("contenido") if config else None

    @staticmethod
    def obtener_menu_principal(db: Session) -> Optional[Menu]:
        """Obtiene el menú principal (id=0)"""
        return GestorContenido.obtener_menu(db, "0")

    @staticmethod
    def listar_menus_activos(db: Session) -> List[Menu]:
        """Lista todos los menús activos"""
        return db.query(Menu).filter(Menu.activo == True).all()

    @staticmethod
    def listar_respuestas_activas(db: Session) -> List[Respuesta]:
        """Lista todas las respuestas activas"""
        return db.query(Respuesta).filter(Respuesta.activo == True).all()

    @staticmethod
    def formatear_respuesta(respuesta: Respuesta, incluir_navegacion: bool = True) -> str:
        """
        Formatea una respuesta para enviar a WhatsApp
        """
        contenido = respuesta.contenido

        if incluir_navegacion and respuesta.siguientes_pasos:
            # Agregar opciones de navegación
            for paso in respuesta.siguientes_pasos:
                if paso == "0":
                    contenido += "\n\n0️⃣ Volver al menú principal"
                elif paso == "#":
                    contenido += "\n#️⃣ Volver atrás"

        return contenido

    @staticmethod
    def formatear_menu(menu: Menu, incluir_navegacion: bool = True) -> str:
        """
        Formatea un menú para enviar a WhatsApp
        """
        contenido = f"{menu.titulo}\n\n{menu.contenido}"

        if incluir_navegacion:
            contenido += "\n\n0️⃣ Volver al menú principal"
            if menu.id != "0":
                contenido += "\n#️⃣ Volver atrás"

        return contenido
