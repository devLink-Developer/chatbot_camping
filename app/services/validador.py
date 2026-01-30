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
    SALUDOS = {
        "HOLA",
        "HOLA BOT",
        "BUEN DIA",
        "BUENOS DIAS",
        "BUENAS",
        "BUENAS TARDES",
        "BUENAS NOCHES",
        "SALUDOS",
        "HI",
        "HELLO",
        "QUE TAL",
    }

    @staticmethod
    def normalizar_entrada(texto: str) -> str:
        """
        Normaliza entrada del usuario:
        - Convierte a mayÃºsculas
        - Elimina espacios extra
        - Maneja Unicode y emojis
        """
        if not texto:
            return ""

        # Remover emojis y caracteres especiales manteniendo nÃºmeros y letras
        texto = ValidadorEntrada._remover_emojis(texto)

        # Normalizar espacios
        texto = re.sub(r"\s+", " ", texto).strip()

        # A mayÃºsculas
        texto = texto.upper()

        return texto

    @staticmethod
    def _remover_emojis(texto: str) -> str:
        """Remueve emojis pero mantiene nÃºmeros y letras"""
        # PatrÃ³n para detectar emojis y caracteres especiales
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
                error_msg="Entrada vacÃ­a",
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

        # Saludos: responder con menu principal
        entrada_saludo = re.sub(r"[^A-Z0-9 ]+", "", entrada_limpia).strip()
        if (
            entrada_saludo in ValidadorEntrada.SALUDOS
            or re.match(
                r"^(HOLA|BUEN DIA|BUENOS DIAS|BUENAS|BUENAS TARDES|BUENAS NOCHES|HI|HELLO)\b",
                entrada_saludo,
            )
        ):
            return ResultadoValidacion(
                es_valido=True,
                tipo=TipoEntrada.COMANDO,
                accion="ir_menu_principal",
                target="0",
                entrada_limpia=entrada_limpia,
            )

        # Validar opciones numericas (1-99)
        if re.match(r"^[0-9]{1,2}$", entrada_limpia):
            return ResultadoValidacion(
                es_valido=True,
                tipo=TipoEntrada.MENU_PRINCIPAL,
                accion="seleccionar_opcion",
                target=entrada_limpia,
                entrada_limpia=entrada_limpia,
            )

        # Validar opciones alfabeticas (A-Z)
        if re.match(r"^[A-Z]$", entrada_limpia):
            return ResultadoValidacion(
                es_valido=True,
                tipo=TipoEntrada.SUBMENU,
                accion="seleccionar_opcion",
                target=entrada_limpia,
                entrada_limpia=entrada_limpia,
            )

        # Entrada invÃ¡lida
        return ResultadoValidacion(
            es_valido=False,
            tipo=TipoEntrada.INVALIDO,
            accion="error",
            target="",
            entrada_limpia=entrada_limpia,
            error_msg="OpciÃ³n no vÃ¡lida. Selecciona un nÃºmero o una letra (A-Z)",
        )

