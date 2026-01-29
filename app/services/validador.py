import re
import unicodedata
from typing import Dict, Tuple
from enum import Enum


class TipoEntrada(str, Enum):
    COMANDO = "comando"
    MENU_PRINCIPAL = "menu_principal"
    SUBMENU = "submenu"
    INVALIDO = "invalido"


class ResultadoValidacion:
    def __init__(
        self,
        es_valido: bool,
        tipo: TipoEntrada,
        accion: str,
        target: str,
        entrada_limpia: str,
        error_msg: str = "",
    ):
        self.es_valido = es_valido
        self.tipo = tipo
        self.accion = accion
        self.target = target
        self.entrada_limpia = entrada_limpia
        self.error_msg = error_msg


class ValidadorEntrada:
    """Valida y normaliza entrada del usuario"""

    # Comandos especiales universales
    COMANDOS_ESPECIALES = {
        "0": {"accion": "ir_menu_principal", "target": "0"},
        "MENU": {"accion": "ir_menu_principal", "target": "0"},
        "#": {"accion": "volver_anterior", "target": "auto"},
        "BACK": {"accion": "volver_anterior", "target": "auto"},
        "VOLVER": {"accion": "volver_anterior", "target": "auto"},
        "ATRAS": {"accion": "volver_anterior", "target": "auto"},
        "*": {"accion": "mostrar_ayuda", "target": "help"},
        "HELP": {"accion": "mostrar_ayuda", "target": "help"},
        "AYUDA": {"accion": "mostrar_ayuda", "target": "help"},
        "INFO": {"accion": "mostrar_ayuda", "target": "help"},
    }

    @staticmethod
    def normalizar_entrada(texto: str) -> str:
        """
        Normaliza entrada del usuario:
        - Convierte a mayúsculas
        - Elimina espacios extra
        - Maneja Unicode y emojis
        """
        if not texto:
            return ""

        # Remover emojis y caracteres especiales manteniendo números y letras
        texto = ValidadorEntrada._remover_emojis(texto)

        # Normalizar espacios
        texto = re.sub(r"\s+", " ", texto).strip()

        # A mayúsculas
        texto = texto.upper()

        return texto

    @staticmethod
    def _remover_emojis(texto: str) -> str:
        """Remueve emojis pero mantiene números y letras"""
        # Patrón para detectar emojis y caracteres especiales
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "\U0001f926-\U0001f937"
            "\U00010000-\U0010ffff"
            "\u2640-\u2642"
            "\u2600-\u2B55"
            "\u200d"
            "\u23cf"
            "\u23e9"
            "\u231a"
            "\ufe0f"  # dingbats
            "\u3030"
            "]+",
            flags=re.UNICODE,
        )
        # Reemplaza emojis con espacio
        texto = emoji_pattern.sub(r" ", texto)
        return texto

    @staticmethod
    def validar(entrada: str) -> ResultadoValidacion:
        """
        Valida entrada del usuario y retorna un objeto ResultadoValidacion
        """
        entrada_limpia = ValidadorEntrada.normalizar_entrada(entrada)

        if not entrada_limpia:
            return ResultadoValidacion(
                es_valido=False,
                tipo=TipoEntrada.INVALIDO,
                accion="error",
                target="",
                entrada_limpia="",
                error_msg="Entrada vacía",
            )

        # Verificar comandos especiales primero
        if entrada_limpia in ValidadorEntrada.COMANDOS_ESPECIALES:
            comando = ValidadorEntrada.COMANDOS_ESPECIALES[entrada_limpia]
            return ResultadoValidacion(
                es_valido=True,
                tipo=TipoEntrada.COMANDO,
                accion=comando["accion"],
                target=comando["target"],
                entrada_limpia=entrada_limpia,
            )

        # Validar menús principales (números 1-12)
        if re.match(r"^(?:[1-9]|1[0-2])$", entrada_limpia):
            return ResultadoValidacion(
                es_valido=True,
                tipo=TipoEntrada.MENU_PRINCIPAL,
                accion="ir_menu",
                target=entrada_limpia,
                entrada_limpia=entrada_limpia,
            )

        # Validar submenús (letras A-Z)
        if re.match(r"^[A-Z]$", entrada_limpia):
            return ResultadoValidacion(
                es_valido=True,
                tipo=TipoEntrada.SUBMENU,
                accion="ir_submenu",
                target=entrada_limpia,
                entrada_limpia=entrada_limpia,
            )

        # Entrada inválida
        return ResultadoValidacion(
            es_valido=False,
            tipo=TipoEntrada.INVALIDO,
            accion="error",
            target="",
            entrada_limpia=entrada_limpia,
            error_msg="Opción no válida. Selecciona un número (1-12) o una letra (A-Z)",
        )
