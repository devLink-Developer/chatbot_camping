"""
Script para importar datos de MongoDB (archivos JSON) a PostgreSQL usando Django.
"""

import json
import os
import sys
import time
from pathlib import Path

import django
from django.core.management import call_command

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aca_lujan.settings")
django.setup()

import re

from app.models.menu import Menu
from app.models.menu_option import MenuOption
from app.models.respuesta import Respuesta
from app.models.config import Config
from app.models.cliente import Cliente
from app.models.campana import Campana, CampanaTemplate
from app.models.campana_envio import CampanaEnvio
from app.services.validador import ValidadorEntrada


def crear_tablas():
    """Crea tablas mediante migrate --run-syncdb."""
    print("📋 Creando tablas...")
    call_command("migrate", run_syncdb=True, verbosity=0)
    print("✅ Tablas creadas")


def _extraer_opcion(linea: str):
    linea = linea.strip()
    if not linea:
        return None
    normalizada = ValidadorEntrada.normalizar_entrada(linea)

    if "🔟" in linea:
        key = "10"
    else:
        key = ""

    if not key:
        match_num = re.match(r"^\D*([0-9])\D*([0-9])?", linea)
        if match_num and match_num.group(1):
            key = match_num.group(1)
            if match_num.group(2):
                key += match_num.group(2)
        else:
            match = re.match(r"^([A-Z])", normalizada)
            if not match:
                return None
            key = match.group(1)
    if key in {"0"}:
        return None

    # Intentar limpiar el label quitando el key inicial
    label = linea
    label = re.sub(r"^[^A-Za-z0-9]*", "", label)
    label = re.sub(rf"^{re.escape(key)}\s*[-.:)]*\s*", "", label, flags=re.IGNORECASE)
    label = label.replace("\uFE0F", "").replace("\u20E3", "").replace("🔟", "")
    label = re.sub(rf"^{re.escape(key)}\s*[-.:)]*\s*", "", label, flags=re.IGNORECASE)
    label = label.strip()
    return key, label or linea


def _orden_por_key(key: str) -> int:
    if key.isdigit():
        return int(key)
    if key.isalpha():
        return 100 + (ord(key.upper()) - ord("A"))
    return 0


def importar_menus(archivo_json: str):
    """Importa menus desde archivo JSON"""
    print(f"\n📂 Importando menus desde {archivo_json}...")

    with open(archivo_json, "r", encoding="utf-8") as f:
        datos = json.load(f)

    menus_info = {}
    for item in datos:
        menu_id = item.get("id", "")
        if not menu_id:
            print("⚠️ Menu sin ID, saltando...")
            continue

        submenu = item.get("submenu", "")
        titulo = item.get("menu", "")
        contenido = submenu if submenu and submenu != "direct" else ""

        existente = Menu.objects.filter(id=menu_id).first()
        if existente:
            print(f"ℹ️ Menu {menu_id} ya existe, actualizando...")
            existente.titulo = titulo
            existente.contenido = contenido
            existente.orden = int(menu_id) if menu_id.isdigit() else 0
            existente.parent_id = "0" if menu_id != "0" and menu_id.isdigit() else None
            existente.save()
            menu_obj = existente
        else:
            menu_obj = Menu.objects.create(
                id=menu_id,
                titulo=titulo,
                contenido=contenido,
                parent_id="0" if menu_id != "0" and menu_id.isdigit() else None,
                orden=int(menu_id) if menu_id.isdigit() else 0,
                opciones=item.get("opciones"),
                activo=True,
            )
            print(f"✅ Menu {menu_id} importado")

        menus_info[menu_id] = {
            "submenu": submenu,
            "menu": menu_obj,
        }

    print("✅ Total de menus importados/actualizados")
    return menus_info


def importar_respuestas(archivo_json: str):
    """Importa respuestas desde archivo JSON"""
    print(f"\n📂 Importando respuestas desde {archivo_json}...")

    with open(archivo_json, "r", encoding="utf-8") as f:
        datos = json.load(f)

    respuestas = {}
    for item in datos:
        respuesta_id = item.get("id", "")
        if not respuesta_id:
            print("⚠️ Respuesta sin ID, saltando...")
            continue

        existente = Respuesta.objects.filter(id=respuesta_id).first()
        if existente:
            print(f"ℹ️ Respuesta {respuesta_id} ya existe, actualizando...")
            existente.contenido = item.get("respuesta", "")
            existente.save()
            respuestas[respuesta_id] = existente
        else:
            respuesta = Respuesta.objects.create(
                id=respuesta_id,
                categoria="general",
                contenido=item.get("respuesta", ""),
                siguientes_pasos=["0", "#"],
                activo=True,
            )
            print(f"✅ Respuesta {respuesta_id} importada")
            respuestas[respuesta_id] = respuesta

    print("✅ Total de respuestas importadas/actualizadas")
    return respuestas


def crear_opciones_menu(menus_info: dict, respuestas: dict):
    """Crea opciones de menu basadas en los submenus."""
    print("\n🧩 Creando opciones de menu...")
    MenuOption.objects.all().delete()

    for menu_id, info in menus_info.items():
        submenu = info.get("submenu", "")
        if not submenu or submenu == "direct":
            continue

        lineas = [l for l in submenu.splitlines() if l.strip()]
        for linea in lineas:
            extraido = _extraer_opcion(linea)
            if not extraido:
                continue
            key, label = extraido

            target_menu = None
            target_respuesta = None

            if menu_id == "0":
                # Opciones del menu principal
                if key in menus_info and menus_info[key]["submenu"] != "direct":
                    target_menu = menus_info[key]["menu"]
                elif key in respuestas:
                    target_respuesta = respuestas[key]
                elif key in menus_info:
                    target_respuesta = respuestas.get(key)
            else:
                # Submenus por letra/numero: respuesta id = menu_id + key
                if key.isalpha():
                    target_respuesta = respuestas.get(f"{menu_id}{key}")
                else:
                    target_respuesta = respuestas.get(key)

            if not target_menu and not target_respuesta:
                continue

            MenuOption.objects.create(
                menu=menus_info[menu_id]["menu"],
                key=key,
                label=label,
                target_menu=target_menu,
                target_respuesta=target_respuesta,
                orden=_orden_por_key(key),
                activo=True,
            )

    print("✅ Opciones creadas")


def crear_config_inicial():
    """Crea configuracion inicial del bot"""
    print("\n⚙️ Creando configuracion inicial...")

    mensajes = {
        "bienvenida": (
            "👋 ¡Hola! Bienvenido al Centro Recreativo y Camping ACA de Luján.\n"
            "Soy *Boti* 🤖💬, tu asistente virtual. Estoy para ayudarte con toda la info del predio.\n"
            "\n"
            "📌 A continuación te dejo el menú para que elijas lo que necesitas:"
        ),
        "bienvenida_retorno": "¡Hola de nuevo! Qué gusto verte por acá. ¿En qué puedo ayudarte hoy?",
        "error_opcion": "❌ Opción no válida. Por favor, selecciona un número del 1 al 12 o una letra de la A a la Z.",
        "error_sesion": "⚠️ Tu sesión ha expirado. Por favor, inicia nuevamente.",
        "ayuda": "ℹ️ Usa números (1-12) para menús principales y letras (A-Z) para opciones específicas.",
    }

    for clave, valor in mensajes.items():
        existente = Config.objects.filter(id=f"mensaje_{clave}").first()
        if not existente:
            Config.objects.create(
                id=f"mensaje_{clave}",
                seccion="mensajes",
                valor={"contenido": valor},
                descripcion=f"Mensaje: {clave}",
            )
            print(f"✅ Mensaje '{clave}' creado")

    print("✅ Configuracion inicial creada")


def crear_datos_ejemplo():
    """Crea datos de ejemplo para campañas y clientes."""
    print("\n🧪 Creando datos de ejemplo...")

    if not Cliente.objects.filter(phone_number="+5491111111111").exists():
        Cliente.objects.create(
            phone_number="+5491111111111",
            nombre="Juan Perez",
            alias_waba="Juan",
            correo="juan@example.com",
            direccion="Calle Falsa 123",
            marketing_opt_in=True,
            primer_contacto_ms=int(time.time() * 1000),
            ultimo_contacto_ms=int(time.time() * 1000),
            mensajes_totales=3,
            ultimo_mensaje="Hola",
        )

    if not Cliente.objects.filter(phone_number="+5492222222222").exists():
        Cliente.objects.create(
            phone_number="+5492222222222",
            nombre="Maria Gomez",
            alias_waba="Maria",
            correo="maria@example.com",
            marketing_opt_in=True,
            primer_contacto_ms=int(time.time() * 1000),
            ultimo_contacto_ms=int(time.time() * 1000),
            mensajes_totales=1,
            ultimo_mensaje="Buenas",
        )

    template, _ = CampanaTemplate.objects.get_or_create(
        nombre="cumple_felicitacion_v1",
        idioma="es_AR",
        defaults={
            "cuerpo": "Hola {{nombre}} 🎉\n¡Feliz cumpleaños! Tenemos un beneficio especial para vos.",
            "variables_json": {"nombre": "cliente.nombre"},
            "activo": True,
        },
    )

    campana, _ = Campana.objects.get_or_create(
        nombre="Cumpleaños - mismo día",
        defaults={
            "tipo": "cumpleanos",
            "canal": "whatsapp",
            "direccion_offset": "mismo_dia",
            "dias_offset": 0,
            "hora_envio": "09:00:00",
            "template": template,
            "template_nombre": template.nombre,
            "template_idioma": template.idioma,
            "texto_estatico": "",
            "variables_json": {"nombre": "cliente.nombre"},
            "segmento_json": {"marketing_opt_in": True},
            "activo": True,
        },
    )

    cliente = Cliente.objects.filter(phone_number="+5491111111111").first()
    if cliente and not CampanaEnvio.objects.filter(campana=campana, cliente=cliente).exists():
        CampanaEnvio.objects.create(
            campana=campana,
            cliente=cliente,
            estado="programado",
            payload_json={
                "to": cliente.phone_number,
                "template": template.nombre,
                "vars": {"nombre": cliente.nombre},
            },
        )

    print("✅ Datos de ejemplo creados")

def main():
    """Funcion principal"""
    print("=" * 60)
    print("🚀 IMPORTADOR DE DATOS: MongoDB → PostgreSQL")
    print("=" * 60)

    menus_archivo = BASE_DIR / "colecciones_v1" / "chatbot.menus.json"
    respuestas_archivo = BASE_DIR / "colecciones_v1" / "chatbot.respuestas.json"

    crear_tablas()
    crear_config_inicial()

    if Menu.objects.exists() or Respuesta.objects.exists() or MenuOption.objects.exists():
        print("ℹ️ Ya existen datos en la base. Importación omitida.")
        return

    menus_info = {}
    respuestas = {}

    if menus_archivo.exists():
        menus_info = importar_menus(str(menus_archivo))
    else:
        print(f"⚠️ Archivo de menus no encontrado: {menus_archivo}")

    if respuestas_archivo.exists():
        respuestas = importar_respuestas(str(respuestas_archivo))
    else:
        print(f"⚠️ Archivo de respuestas no encontrado: {respuestas_archivo}")

    if menus_info and respuestas:
        crear_opciones_menu(menus_info, respuestas)

    crear_datos_ejemplo()

    print("\n" + "=" * 60)
    print("✅ IMPORTACION COMPLETADA")
    print("=" * 60)


if __name__ == "__main__":
    main()
