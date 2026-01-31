# Guía de Deploy en Producción

## Estructura de archivos de deployment

- **`docker-compose.prod.yml`**: Para actualizar SOLO el chatbot (uso normal)
- **`docker-compose.prod.full.yml`**: Para deploy completo incluyendo Traefik y Cloudflared (primera vez)

## 📦 Primer Deploy (con Traefik y Cloudflared)

Usar cuando:
- Es la primera vez que se despliega
- Se necesita recrear Traefik o Cloudflared
- El servidor no tiene Traefik corriendo

```bash
# 1. Crear la red de Traefik
docker network create traefik_proxy

# 2. Desplegar todo
docker-compose -f docker-compose.prod.full.yml up -d

# 3. Verificar
docker ps
docker logs -f aca_lujan_chatbot
```

## 🔄 Updates del Chatbot (uso normal)

Usar cuando:
- Solo se actualiza código del chatbot
- Traefik y Cloudflared ya están corriendo
- Despliegues regulares

```bash
# 1. Pull del código más reciente
git pull origin main

# 2. Rebuild y redeploy del chatbot
docker-compose -f docker-compose.prod.yml up -d --build

# 3. Ver logs
docker logs -f aca_lujan_chatbot
```

## 🔍 Verificación

```bash
# Ver todos los contenedores
docker ps

# Logs del chatbot
docker logs -f aca_lujan_chatbot

# Logs de Traefik
docker logs -f traefik

# Logs del túnel Cloudflare
docker logs -f cloudflared-tunnel

# Estado de salud
docker ps --format "table {{.Names}}\t{{.Status}}"
```

## 🌐 URLs

- **API del Chatbot**: https://chatbot-api.devlink.com.ar
- **n8n**: https://chatbot.devlink.com.ar

## 🛑 Detener servicios

```bash
# Solo el chatbot
docker-compose -f docker-compose.prod.yml down

# Todo (incluyendo Traefik y Cloudflared)
docker-compose -f docker-compose.prod.full.yml down
```

## ⚠️ Importante

- **NO usar `docker-compose.prod.full.yml`** si Traefik ya está corriendo (conflicto de puertos)
- **Siempre usar `docker-compose.prod.yml`** para updates normales
- Verificar que la red `traefik_proxy` exista antes del primer deploy
