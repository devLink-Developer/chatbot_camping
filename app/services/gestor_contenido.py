from typing import List, Optional, Dict, Any
import unicodedata

from app.models.menu import Menu
from app.models.menu_option import MenuOption
from app.models.respuesta import Respuesta
from app.models.config import Config


class GestorContenido:
    """Gestiona menus y respuestas desde BD"""

    @staticmethod
    def obtener_menu(menu_id: str) -> Optional[Menu]:
        """Obtiene un menu por ID"""
        return Menu.objects.filter(id=menu_id, activo=True).first()

    @staticmethod
    def obtener_respuesta(respuesta_id: str) -> Optional[Respuesta]:
        """Obtiene una respuesta por ID"""
        return Respuesta.objects.filter(id=respuesta_id, activo=True).first()

    @staticmethod
    def obtener_config_mensaje(clave: str) -> Optional[str]:
        """Obtiene mensaje de configuracion"""
        config = Config.objects.filter(id=f"mensaje_{clave}").first()
        if not config or not isinstance(config.valor, dict):
            return None
        return config.valor.get("contenido")

    @staticmethod
    def obtener_menu_principal() -> Optional[Menu]:
        """Obtiene el menu principal (id=0)"""
        return GestorContenido.obtener_menu("0")

    @staticmethod
    def listar_menus_activos() -> List[Menu]:
        """Lista todos los menus activos"""
        return list(Menu.objects.filter(activo=True))

    @staticmethod
    def listar_respuestas_activas() -> List[Respuesta]:
        """Lista todas las respuestas activas"""
        return list(Respuesta.objects.filter(activo=True))

    @staticmethod
    def obtener_opcion(menu_id: str, key: str) -> Optional[MenuOption]:
        """Obtiene una opcion activa de un menu por key."""
        return (
            MenuOption.objects.filter(menu_id=menu_id, key=key, activo=True)
            .select_related("target_menu", "target_respuesta")
            .first()
        )

    @staticmethod
    def _normalizar_contenido(texto: str) -> str:
        if not texto:
            return ""
        normalizado = unicodedata.normalize("NFD", texto.lower())
        return "".join(c for c in normalizado if unicodedata.category(c) != "Mn")

    @staticmethod
    def _coerce_pasos(pasos: Any) -> List[str]:
        if not pasos:
            return []
        if isinstance(pasos, (list, tuple, set)):
            return [str(p).strip() for p in pasos if str(p).strip()]
        return [str(pasos).strip()]

    @staticmethod
    def _agregar_navegacion(contenido: str, pasos: List[str]) -> str:
        if contenido:
            lineas = contenido.splitlines()
            lineas_limpias = []
            for linea in lineas:
                linea_norm = GestorContenido._normalizar_contenido(linea).strip()
                if (
                    ("volver al menu principal" in linea_norm or "volver atras" in linea_norm)
                    and (linea_norm.startswith("0") or linea_norm.startswith("#") or linea_norm.startswith("volver"))
                ):
                    continue
                lineas_limpias.append(linea)
            contenido = "\n".join(lineas_limpias).rstrip()

        nav_lines = []
        if "0" in pasos:
            nav_lines.append("0 Volver al menu principal")
        if "#" in pasos:
            nav_lines.append("# Volver atras")

        if nav_lines:
            if contenido:
                contenido += "\n\n" + "\n".join(nav_lines)
            else:
                contenido = "\n".join(nav_lines)

        return contenido

    @staticmethod
    def formatear_respuesta(respuesta: Respuesta, incluir_navegacion: bool = True) -> str:
        """Formatea una respuesta para enviar a WhatsApp"""
        contenido = respuesta.contenido or ""

        if incluir_navegacion and respuesta.siguientes_pasos:
            pasos = GestorContenido._coerce_pasos(respuesta.siguientes_pasos)
            contenido = GestorContenido._agregar_navegacion(contenido, pasos)

        return contenido

    @staticmethod
    def formatear_menu(menu: Menu, incluir_navegacion: bool = True) -> str:
        """Formatea un menu para enviar a WhatsApp"""
        opciones = list(
            MenuOption.objects.filter(menu=menu, activo=True).order_by("orden")
        )
        if opciones:
            cuerpo = "\n".join([f"{opt.key} {opt.label}".strip() for opt in opciones])
        else:
            cuerpo = (menu.contenido or "").strip()

        contenido = f"{menu.titulo}\n\n{cuerpo}".strip()

        if incluir_navegacion:
            pasos = []
            if menu.id != "0":
                pasos = ["0", "#"]
            contenido = GestorContenido._agregar_navegacion(contenido, pasos)

        return contenido
