from typing import List, Optional, Dict, Any, Set
import unicodedata

from app.models.menu import Menu
from app.models.menu_option import MenuOption
from app.models.respuesta import Respuesta
from app.models.config import Config


class GestorContenido:
    """Gestiona menus y respuestas desde BD"""

    CLUB_SHORTCUT_KEY = "CLUB"
    NAV_CLUB_LINE = "🎁 CLUB Club de beneficios"
    NAV_MAIN_LINE = "0️⃣ 🏠 Volver al menu principal"
    NAV_BACK_LINE = "#️⃣ ↩️ Volver atras"
    MENU_CONTEXT_PREFIX = "📍 Estas en:"

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
        menu = Menu.objects.filter(is_main=True, activo=True).first()
        if menu:
            return menu
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
    def _es_opcion_club_beneficios(label: str) -> bool:
        label_norm = GestorContenido._normalizar_contenido(label or "")
        if "club" not in label_norm:
            return False
        return any(term in label_norm for term in ("beneficio", "promo", "descuento"))

    @staticmethod
    def obtener_opcion_club_beneficios() -> Optional[MenuOption]:
        """Busca en el menu principal la opcion que apunta al Club de Beneficios."""
        menu_principal = GestorContenido.obtener_menu_principal()
        if not menu_principal:
            return None
        opciones = (
            MenuOption.objects.filter(menu=menu_principal, activo=True)
            .select_related("target_menu", "target_respuesta")
            .order_by("orden")
        )
        for opcion in opciones:
            if GestorContenido._es_opcion_club_beneficios(opcion.label):
                return opcion
        return None

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
    def _menu_es_principal(menu: Optional[Menu]) -> bool:
        return bool(menu and (menu.is_main or str(menu.id) == "0"))

    @staticmethod
    def _titulo_menu(menu: Menu) -> str:
        if GestorContenido._menu_es_principal(menu):
            return "Menu principal"
        titulo = (menu.titulo or "").strip()
        if titulo:
            return titulo
        return f"Menu {menu.id}"

    @staticmethod
    def construir_ruta_menu(menu: Optional[Menu], max_depth: int = 15) -> str:
        if not menu:
            return ""
        ruta: List[str] = []
        visitados: Set[str] = set()
        actual = menu
        while actual and len(ruta) < max_depth:
            menu_id = str(actual.id)
            if menu_id in visitados:
                break
            visitados.add(menu_id)
            ruta.append(GestorContenido._titulo_menu(actual))
            actual = actual.parent

        if not ruta:
            return ""
        ruta.reverse()
        if ruta[0] != "Menu principal" and not GestorContenido._menu_es_principal(menu):
            ruta.insert(0, "Menu principal")
        return " > ".join(ruta)

    @staticmethod
    def obtener_contexto_menu(menu_contexto_id: Optional[str]) -> str:
        if not menu_contexto_id:
            return ""
        menu = GestorContenido.obtener_menu(str(menu_contexto_id))
        ruta = GestorContenido.construir_ruta_menu(menu)
        if not ruta:
            return ""
        return f"{GestorContenido.MENU_CONTEXT_PREFIX} {ruta}"

    @staticmethod
    def _agregar_navegacion(contenido: str, pasos: List[str]) -> str:
        if contenido:
            lineas = contenido.splitlines()
            lineas_limpias = []
            for linea in lineas:
                linea_norm = GestorContenido._normalizar_contenido(linea).strip()
                if (
                    (
                        "volver al menu principal" in linea_norm
                        or "volver atras" in linea_norm
                        or "club de beneficios" in linea_norm
                    )
                    and (
                        linea_norm.startswith("0")
                        or linea_norm.startswith("#")
                        or linea_norm.startswith("volver")
                        or GestorContenido.CLUB_SHORTCUT_KEY.lower() in linea_norm[:12]
                    )
                ):
                    continue
                lineas_limpias.append(linea)
            contenido = "\n".join(lineas_limpias).rstrip()

        nav_lines = []
        if GestorContenido.CLUB_SHORTCUT_KEY in pasos:
            nav_lines.append(GestorContenido.NAV_CLUB_LINE)
        if "0" in pasos:
            nav_lines.append(GestorContenido.NAV_MAIN_LINE)
        if "#" in pasos:
            nav_lines.append(GestorContenido.NAV_BACK_LINE)

        if nav_lines:
            if contenido:
                contenido += "\n\n" + "\n".join(nav_lines)
            else:
                contenido = "\n".join(nav_lines)

        return contenido

    @staticmethod
    def quitar_navegacion(contenido: str) -> str:
        """Elimina lineas de navegacion 0/# del texto."""
        return GestorContenido._agregar_navegacion(contenido, [])

    @staticmethod
    def formatear_respuesta(
        respuesta: Respuesta,
        incluir_navegacion: bool = True,
        menu_contexto_id: Optional[str] = None,
    ) -> str:
        """Formatea una respuesta para enviar a WhatsApp"""
        contenido = (respuesta.contenido or "").strip()

        contexto = GestorContenido.obtener_contexto_menu(menu_contexto_id)
        if contexto and contexto not in contenido:
            contenido = f"{contexto}\n\n{contenido}".strip()

        if incluir_navegacion and respuesta.siguientes_pasos:
            pasos = GestorContenido._coerce_pasos(respuesta.siguientes_pasos)
            contenido = GestorContenido._agregar_navegacion(contenido, pasos)

        return contenido

    @staticmethod
    def formatear_menu(
        menu: Menu,
        incluir_navegacion: bool = True,
        incluir_contexto: bool = True,
    ) -> str:
        """Formatea un menu para enviar a WhatsApp"""
        opciones = list(
            MenuOption.objects.filter(menu=menu, activo=True).order_by("orden")
        )
        if opciones:
            cuerpo = "\n".join([f"{opt.key} {opt.label}".strip() for opt in opciones])
        else:
            cuerpo = (menu.contenido or "").strip()

        contenido = f"{menu.titulo}\n\n{cuerpo}".strip()
        if incluir_contexto and not GestorContenido._menu_es_principal(menu):
            contexto = GestorContenido.obtener_contexto_menu(menu.id)
            if contexto:
                contenido = f"{contexto}\n\n{contenido}".strip()

        if incluir_navegacion:
            pasos = []
            if not menu.is_main and menu.id != "0":
                pasos = [GestorContenido.CLUB_SHORTCUT_KEY, "0", "#"]
            contenido = GestorContenido._agregar_navegacion(contenido, pasos)

        return contenido
