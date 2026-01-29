"""
Script para importar datos de MongoDB (archivos JSON) a PostgreSQL
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models.menu import Menu
from app.models.respuesta import Respuesta
from app.models.config import Config


def crear_tablas():
    """Crea todas las tablas"""
    print("📋 Creando tablas...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas creadas")


def importar_menus(archivo_json: str):
    """Importa menús desde archivo JSON"""
    print(f"\n📂 Importando menús desde {archivo_json}...")

    with open(archivo_json, "r", encoding="utf-8") as f:
        datos = json.load(f)

    db = SessionLocal()
    try:
        for item in datos:
            menu_id = item.get("id", "")
            if not menu_id:
                print(f"⚠️ Menú sin ID, saltando...")
                continue

            # Verificar si ya existe
            existente = db.query(Menu).filter(Menu.id == menu_id).first()
            if existente:
                print(f"ℹ️ Menú {menu_id} ya existe, actualizando...")
                existente.titulo = item.get("menu", "")
                existente.contenido = item.get("submenu", "")
            else:
                menu = Menu(
                    id=menu_id,
                    titulo=item.get("menu", ""),
                    contenido=item.get("submenu", ""),
                    submenu=item.get("submenu_type", "direct"),
                    opciones=item.get("opciones"),
                    activo=True,
                )
                db.add(menu)
                print(f"✅ Menú {menu_id} importado")

        db.commit()
        print(f"✅ Total de menús importados/actualizados")

    except Exception as e:
        db.rollback()
        print(f"❌ Error importando menús: {e}")
        raise
    finally:
        db.close()


def importar_respuestas(archivo_json: str):
    """Importa respuestas desde archivo JSON"""
    print(f"\n📂 Importando respuestas desde {archivo_json}...")

    with open(archivo_json, "r", encoding="utf-8") as f:
        datos = json.load(f)

    db = SessionLocal()
    try:
        for item in datos:
            respuesta_id = item.get("id", "")
            if not respuesta_id:
                print(f"⚠️ Respuesta sin ID, saltando...")
                continue

            # Verificar si ya existe
            existente = db.query(Respuesta).filter(Respuesta.id == respuesta_id).first()
            if existente:
                print(f"ℹ️ Respuesta {respuesta_id} ya existe, actualizando...")
                existente.contenido = item.get("respuesta", "")
            else:
                respuesta = Respuesta(
                    id=respuesta_id,
                    categoria="general",
                    contenido=item.get("respuesta", ""),
                    siguientes_pasos=["0", "#"],
                    activo=True,
                )
                db.add(respuesta)
                print(f"✅ Respuesta {respuesta_id} importada")

        db.commit()
        print(f"✅ Total de respuestas importadas/actualizadas")

    except Exception as e:
        db.rollback()
        print(f"❌ Error importando respuestas: {e}")
        raise
    finally:
        db.close()


def crear_config_inicial():
    """Crea configuración inicial del bot"""
    print(f"\n⚙️ Creando configuración inicial...")

    db = SessionLocal()
    try:
        # Mensajes
        mensajes = {
            "bienvenida": "👋 ¡Hola! Bienvenido al Centro Recreativo y Camping ACA de Luján.",
            "error_opcion": "❌ Opción no válida. Por favor, selecciona un número del 1 al 12 o una letra de la A a la Z.",
            "error_sesion": "⚠️ Tu sesión ha expirado. Por favor, inicia nuevamente.",
            "ayuda": "ℹ️ Usa números (1-12) para menús principales y letras (A-Z) para opciones específicas.",
        }

        for clave, valor in mensajes.items():
            existente = db.query(Config).filter(Config.id == f"mensaje_{clave}").first()
            if not existente:
                config = Config(
                    id=f"mensaje_{clave}",
                    seccion="mensajes",
                    valor={"contenido": valor},
                    descripcion=f"Mensaje: {clave}",
                )
                db.add(config)
                print(f"✅ Mensaje '{clave}' creado")

        db.commit()
        print(f"✅ Configuración inicial creada")

    except Exception as e:
        db.rollback()
        print(f"❌ Error creando configuración: {e}")
        raise
    finally:
        db.close()


def main():
    """Función principal"""
    print("=" * 60)
    print("🚀 IMPORTADOR DE DATOS: MongoDB → PostgreSQL")
    print("=" * 60)

    # Rutas a archivos JSON
    scripts_dir = Path(__file__).parent.parent
    menus_archivo = scripts_dir.parent / "colecciones_v1" / "chatbot.menus.json"
    respuestas_archivo = scripts_dir.parent / "colecciones_v1" / "chatbot.respuestas.json"

    # Crear tablas
    crear_tablas()

    # Importar datos
    if menus_archivo.exists():
        importar_menus(str(menus_archivo))
    else:
        print(f"⚠️ Archivo de menús no encontrado: {menus_archivo}")

    if respuestas_archivo.exists():
        importar_respuestas(str(respuestas_archivo))
    else:
        print(f"⚠️ Archivo de respuestas no encontrado: {respuestas_archivo}")

    # Configuración inicial
    crear_config_inicial()

    print("\n" + "=" * 60)
    print("✅ IMPORTACIÓN COMPLETADA")
    print("=" * 60)


if __name__ == "__main__":
    main()
