#!/usr/bin/env python
"""
Script para crear archivo .env con valores por defecto
"""

import os
from pathlib import Path

def crear_env():
    env_file = Path(__file__).parent.parent / ".env"
    
    if env_file.exists():
        print(f"⚠️  {env_file} ya existe")
        return
    
    env_template = """# Database
DATABASE_URL=postgresql://chatbot:password@postgres:5432/aca_lujan_bot

# WhatsApp - Reemplaza con tus valores reales
WHATSAPP_PHONE_ID=877312245455597
WHATSAPP_ACCESS_TOKEN=tu_token_de_acceso_aqui
WHATSAPP_VERIFY_TOKEN=tu_verify_token_aqui

# App
DEBUG=False
LOG_LEVEL=INFO
SECRET_KEY=tu_clave_secreta_super_segura_aqui_min_32_caracteres

# Timeouts (segundos)
SESSION_TIMEOUT_SECONDS=900
INACTIVE_TIMEOUT_SECONDS=1800
"""
    
    with open(env_file, "w") as f:
        f.write(env_template)
    
    print(f"✅ Archivo {env_file} creado")
    print("📝 Por favor, actualiza los valores de WHATSAPP_* con tus credenciales")

if __name__ == "__main__":
    crear_env()
