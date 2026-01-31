#!/bin/bash
# Script para configurar el túnel de Cloudflare completamente

TUNNEL_ID="0e0e4e15-58fc-4417-bed7-76f166ce887d"
CLOUDFLARE_EMAIL="${CLOUDFLARE_EMAIL}"
CLOUDFLARE_API_KEY="${CLOUDFLARE_API_KEY}"

echo "=== Configuración del Túnel de Cloudflare ==="
echo ""

# 1. Crear la red de Traefik si no existe
echo "1. Creando red traefik_proxy..."
docker network create traefik_proxy 2>/dev/null || echo "   La red ya existe"
echo ""

# 2. Verificar que el archivo de credenciales existe
echo "2. Verificando archivo de credenciales..."
if [ ! -f "/etc/cloudflared/${TUNNEL_ID}.json" ]; then
    echo "   ❌ ERROR: No se encuentra /etc/cloudflared/${TUNNEL_ID}.json"
    echo "   Necesitas crear este archivo con las credenciales del túnel"
    exit 1
fi
echo "   ✓ Archivo de credenciales encontrado"
echo ""

# 3. Configurar DNS en Cloudflare (requiere API)
echo "3. Configurando DNS en Cloudflare..."
if [ -z "$CLOUDFLARE_EMAIL" ] || [ -z "$CLOUDFLARE_API_KEY" ]; then
    echo "   ⚠️  Variables CLOUDFLARE_EMAIL y CLOUDFLARE_API_KEY no configuradas"
    echo "   Debes configurar manualmente en Cloudflare:"
    echo "   - chatbot.devlink.com.ar -> CNAME ${TUNNEL_ID}.cfargotunnel.com"
    echo "   - chatbot-api.devlink.com.ar -> CNAME ${TUNNEL_ID}.cfargotunnel.com"
else
    python3 add_tunnel_route.py
fi
echo ""

# 4. Iniciar servicios
echo "4. Iniciando servicios..."
echo "   Iniciando Traefik y Cloudflared..."
docker-compose -f docker-compose.tunnel.yml up -d
echo ""

echo "   Iniciando Chatbot..."
cd chatbot-python
docker-compose -f docker-compose.prod.yml up -d
cd ..
echo ""

# 5. Verificar estado
echo "5. Verificando estado de los contenedores..."
docker ps --filter "name=traefik" --filter "name=cloudflared" --filter "name=aca_lujan_chatbot" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "=== Configuración completada ==="
echo ""
echo "URLs del servicio:"
echo "  - https://chatbot-api.devlink.com.ar (Django API)"
echo "  - https://chatbot.devlink.com.ar (n8n - puerto 5678)"
echo ""
echo "Para verificar logs:"
echo "  docker logs -f cloudflared-tunnel"
echo "  docker logs -f traefik"
echo "  docker logs -f aca_lujan_chatbot"
