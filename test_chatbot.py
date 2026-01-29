"""
Tests unitarios para el chatbot
"""

import pytest
from app.services.validador import ValidadorEntrada, TipoEntrada
from app.services.gestor_sesion import GestorSesion


class TestValidadorEntrada:
    """Tests para ValidadorEntrada"""

    def test_normalizar_entrada_basico(self):
        """Prueba normalización básica"""
        resultado = ValidadorEntrada.normalizar_entrada("  HOLA  ")
        assert resultado == "HOLA"

    def test_normalizar_entrada_mayusculas(self):
        """Prueba conversión a mayúsculas"""
        resultado = ValidadorEntrada.normalizar_entrada("hola mundo")
        assert resultado == "HOLA MUNDO"

    def test_normalizar_entrada_vacia(self):
        """Prueba entrada vacía"""
        resultado = ValidadorEntrada.normalizar_entrada("")
        assert resultado == ""

    def test_validar_comando_menu(self):
        """Prueba validación de comando 0"""
        resultado = ValidadorEntrada.validar("0")
        assert resultado.es_valido
        assert resultado.tipo == TipoEntrada.COMANDO
        assert resultado.accion == "ir_menu_principal"

    def test_validar_menu_principal(self):
        """Prueba validación de menú principal (1-12)"""
        resultado = ValidadorEntrada.validar("5")
        assert resultado.es_valido
        assert resultado.tipo == TipoEntrada.MENU_PRINCIPAL
        assert resultado.target == "5"

    def test_validar_submenu(self):
        """Prueba validación de submenú (A-Z)"""
        resultado = ValidadorEntrada.validar("A")
        assert resultado.es_valido
        assert resultado.tipo == TipoEntrada.SUBMENU
        assert resultado.target == "A"

    def test_validar_entrada_invalida(self):
        """Prueba validación de entrada inválida"""
        resultado = ValidadorEntrada.validar("99")
        assert not resultado.es_valido
        assert resultado.tipo == TipoEntrada.INVALIDO

    def test_validar_comando_volver(self):
        """Prueba comando volver (#)"""
        resultado = ValidadorEntrada.validar("#")
        assert resultado.es_valido
        assert resultado.accion == "volver_anterior"

    def test_validar_comando_ayuda(self):
        """Prueba comando ayuda"""
        resultado = ValidadorEntrada.validar("HELP")
        assert resultado.es_valido
        assert resultado.accion == "mostrar_ayuda"

    def test_remover_emojis(self):
        """Prueba remoción de emojis"""
        entrada = "Hola 👋 mundo 🌍"
        resultado = ValidadorEntrada.normalizar_entrada(entrada)
        assert "👋" not in resultado
        assert "🌍" not in resultado
        assert "HOLA" in resultado
        assert "MUNDO" in resultado


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
