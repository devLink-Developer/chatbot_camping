from typing import List, Optional, Dict, Tuple
from sqlalchemy.orm import Session
from app.services.validador import ValidadorEntrada, TipoEntrada
from app.services.gestor_contenido import GestorContenido


class NavigadorBot:
    """Gestiona la navegación del chatbot"""

    @staticmethod
    def procesar_entrada(
        db: Session,
        entrada: str,
        historial_actual: List[str],
        estado_actual: str,
    ) -> Tuple[str, List[str], str, str, bool]:
        """
        Procesa la entrada del usuario y retorna:
        - nuevo_estado (menu id o respuesta id)
        - nuevo_historial
        - tipo (menu o respuesta)
        - target (id del contenido)
        - es_valido
        """
        # Validar entrada
        validacion = ValidadorEntrada.validar(entrada)

        if not validacion.es_valido:
            return estado_actual, historial_actual, "error", "", False

        # Procesar según el tipo de entrada
        accion = validacion.accion
        target = validacion.target

        nuevo_historial = list(historial_actual)
        tipo_contenido = "menu"  # menu o respuesta

        if accion == "ir_menu_principal":
            # Volver al menú principal
            nuevo_historial = ["0"]
            nuevo_estado = "0"
            tipo_contenido = "menu"

        elif accion == "volver_anterior":
            # Volver al menú anterior
            if len(nuevo_historial) > 1:
                nuevo_historial.pop()
            nuevo_estado = nuevo_historial[-1] if nuevo_historial else "0"
            tipo_contenido = "menu"

        elif accion == "ir_menu":
            # Ir a un menú
            nuevo_estado = target
            if target not in nuevo_historial:
                nuevo_historial.append(target)
            tipo_contenido = "menu"

        elif accion == "ir_submenu":
            # Ir a un submenú (respuesta)
            # El target es la respuesta id (ej: "1A", "2B")
            nuevo_estado = target
            tipo_contenido = "respuesta"

        elif accion == "mostrar_ayuda":
            # Mostrar ayuda
            nuevo_estado = target
            tipo_contenido = "help"

        else:
            return estado_actual, historial_actual, "error", "", False

        return nuevo_estado, nuevo_historial, tipo_contenido, target, True

    @staticmethod
    def obtener_contenido(
        db: Session, target: str, tipo: str
    ) -> Optional[Dict]:
        """
        Obtiene el contenido a mostrar
        """
        if tipo == "menu":
            menu = GestorContenido.obtener_menu(db, target)
            if menu:
                return {
                    "id": menu.id,
                    "tipo": "menu",
                    "titulo": menu.titulo,
                    "contenido": GestorContenido.formatear_menu(menu),
                    "opciones": menu.opciones,
                }
        elif tipo == "respuesta":
            respuesta = GestorContenido.obtener_respuesta(db, target)
            if respuesta:
                return {
                    "id": respuesta.id,
                    "tipo": "respuesta",
                    "categoria": respuesta.categoria,
                    "contenido": GestorContenido.formatear_respuesta(respuesta),
                    "siguientes_pasos": respuesta.siguientes_pasos,
                }
        elif tipo == "help":
            # Retornar mensaje de ayuda
            return {
                "tipo": "help",
                "contenido": NavigadorBot._obtener_mensaje_ayuda(),
            }

        return None

    @staticmethod
    def _obtener_mensaje_ayuda() -> str:
        """Mensaje de ayuda del bot"""
        return (
            "ℹ️ *COMANDOS DISPONIBLES:*\n\n"
            "📌 *Números:* Selecciona un número del 1 al 12 para ver opciones\n"
            "📌 *Letras:* Selecciona A, B, C, etc. para más información\n"
            "📌 *0 o MENU:* Vuelve al menú principal\n"
            "📌 *# o VOLVER:* Vuelve al menú anterior\n"
            "📌 *HELP o AYUDA:* Muestra este mensaje\n\n"
            "💡 *Ejemplos:*\n"
            "• Escribe: 1\n"
            "• Luego: A\n"
            "• Escribí: 0 para volver"
        )
