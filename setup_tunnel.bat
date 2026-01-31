@echo off
REM Script para configurar el túnel de Cloudflare en Windows

set TUNNEL_ID=0e0e4e15-58fc-4417-bed7-76f166ce887d

echo === Configuracion del Tunel de Cloudflare ===
echo.

REM 1. Crear la red de Traefik si no existe
echo 1. Creando red traefik_proxy...
docker network create traefik_proxy 2>nul
if %errorlevel% neq 0 (
    echo    La red ya existe o hubo un error
)
echo.

REM 2. Verificar configuracion
echo 2. Verificando configuracion...
if not exist "cloudflared_config.yml" (
    echo    ERROR: No se encuentra cloudflared_config.yml
    exit /b 1
)
echo    OK: Archivo de configuracion encontrado
echo.

REM 3. Recordatorio de DNS
echo 3. Configuracion DNS en Cloudflare:
echo    Asegurate de tener estos registros CNAME:
echo    - chatbot.devlink.com.ar -^> %TUNNEL_ID%.cfargotunnel.com
echo    - chatbot-api.devlink.com.ar -^> %TUNNEL_ID%.cfargotunnel.com
echo.

REM 4. Iniciar servicios
echo 4. Iniciando servicios...
echo    Iniciando Traefik y Cloudflared...
docker-compose -f docker-compose.tunnel.yml up -d
echo.

echo    Iniciando Chatbot...
cd chatbot-python
docker-compose -f docker-compose.prod.yml up -d
cd ..
echo.

REM 5. Verificar estado
echo 5. Verificando estado de los contenedores...
docker ps --filter "name=traefik" --filter "name=cloudflared" --filter "name=aca_lujan_chatbot"
echo.

echo === Configuracion completada ===
echo.
echo URLs del servicio:
echo   - https://chatbot-api.devlink.com.ar (Django API)
echo   - https://chatbot.devlink.com.ar (n8n - puerto 5678)
echo.
echo Para verificar logs:
echo   docker logs -f cloudflared-tunnel
echo   docker logs -f traefik
echo   docker logs -f aca_lujan_chatbot
echo.
pause
