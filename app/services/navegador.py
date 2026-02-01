from typing import List, Optional, Dict, Tuple

from app.services.validador import ValidadorEntrada
from app.services.gestor_contenido import GestorContenido


class NavigadorBot:
    """Gestiona la navegacion del chatbot"""

    @staticmethod
    def procesar_entrada(
        entrada: str,
        historial_actual: List[str],
        estado_actual: str,
        ultimo_tipo: Optional[str] = None,
    ) -> Tuple[str, List[str], str, str, bool]:
        """
        Procesa la entrada del usuario y retorna:
        - nuevo_estado (menu id o respuesta id)
        - nuevo_historial
        - tipo (menu o respuesta)
        - target (id del contenido)
        - es_valido
        """
        validacion = ValidadorEntrada.validar(entrada)

        if not validacion.es_valido:
            return estado_actual, historial_actual, "error", "", False

        accion = validacion.accion
        target = validacion.target

        nuevo_historial = list(historial_actual)
        tipo_contenido = "menu"

        if accion == "ir_menu_principal":
            nuevo_historial = ["0"]
            nuevo_estado = "0"
            tipo_contenido = "menu"
            target = "0"
        elif accion == "volver_anterior":
            if ultimo_tipo == "respuesta":
                nuevo_estado = estado_actual
            else:
                if len(nuevo_historial) > 1:
                    nuevo_historial.pop()
                nuevo_estado = nuevo_historial[-1] if nuevo_historial else "0"
            tipo_contenido = "menu"
            target = nuevo_estado
        elif accion == "seleccionar_opcion":
            opcion = GestorContenido.obtener_opcion(estado_actual, target)
            if not opcion:
                return estado_actual, historial_actual, "error", "", False

            if opcion.target_menu_id:
                nuevo_estado = opcion.target_menu_id
                if nuevo_estado not in nuevo_historial:
                    nuevo_historial.append(nuevo_estado)
                tipo_contenido = "menu"
                target = opcion.target_menu_id
            elif opcion.target_respuesta_id:
                nuevo_estado = estado_actual
                tipo_contenido = "respuesta"
                target = opcion.target_respuesta_id
            else:
                return estado_actual, historial_actual, "error", "", False
        elif accion == "mostrar_ayuda":
            nuevo_estado = estado_actual
            tipo_contenido = "help"
        else:
            return estado_actual, historial_actual, "error", "", False

        return nuevo_estado, nuevo_historial, tipo_contenido, target, True

    @staticmethod
    def obtener_contenido(target: str, tipo: str) -> Optional[Dict]:
        """Obtiene el contenido a mostrar"""
        if tipo == "menu":
            menu = GestorContenido.obtener_menu(target)
            if menu:
                return {
                    "id": menu.id,
                    "tipo": "menu",
                    "titulo": menu.titulo,
                    "contenido": GestorContenido.formatear_menu(menu),
                    "opciones": menu.opciones,
                }
        elif tipo == "respuesta":
            respuesta = GestorContenido.obtener_respuesta(target)
            if respuesta:
                return {
                    "id": respuesta.id,
                    "tipo": "respuesta",
                    "categoria": respuesta.categoria,
                    "contenido": GestorContenido.formatear_respuesta(respuesta),
                    "siguientes_pasos": respuesta.siguientes_pasos,
                }
        elif tipo == "help":
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
            "📌 *Numeros:* Selecciona un numero del 1 al 12 para ver opciones\n"
            "📌 *Letras:* Selecciona A, B, C, etc. para mas informacion\n"
            "📌 *0 o MENU:* Vuelve al menu principal\n"
            "📌 *# o VOLVER:* Vuelve al menu anterior\n"
            "📌 *HELP o AYUDA:* Muestra este mensaje\n\n"
            "💡 *Ejemplos:*\n"
            "• Escribe: 1\n"
            "• Luego: A\n"
            "• Escribi: 0 para volver"
        )
