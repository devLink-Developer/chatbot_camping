# README LOCAL / PROD (Comandos + Troubleshooting)

Fecha: 2026-02-01

Este documento reúne los comandos exactos para levantar el proyecto en **local** y **prod**, y cómo resolver errores comunes.

---
## 1) Local (Windows)

### 1.1. Requisitos
- Docker Desktop (Compose v2)
- Puertos libres: 8006 (app), 5456 (Postgres local si lo usás)

### 1.2. Levantar stack local
```powershell
cd C:\Users\rortigoza\Documents\Aca Lujan Bot\chatbot-python

# (opcional) bajar lo que esté corriendo
docker compose down

# build sin caché
docker compose build --no-cache

# levantar
docker compose up -d --force-recreate
```

### 1.3. Crear superusuario (local)
```powershell
cd C:\Users\rortigoza\Documents\Aca Lujan Bot\chatbot-python
docker compose exec chatbot python manage.py createsuperuser --username rortigoza
```

### 1.4. Cambiar contraseña de superusuario (local)
```powershell
cd C:\Users\rortigoza\Documents\Aca Lujan Bot\chatbot-python
docker compose exec chatbot python manage.py changepassword rortigoza
```

### 1.5. Admin y simulador
- Admin: http://127.0.0.1:8006/admin/
- Simulador: http://127.0.0.1:8006/simulador

---
## 2) Prod (VPS / Linux)

### 2.1. Requisitos
- Docker + Compose v2
- Red externa `traefik_proxy` ya creada en el server
- DB Postgres externa ya corriendo (ej: `devlink_db`)

### 2.2. Comandos de despliegue
```bash
cd /opt/chatbot

# si hay cambios locales que querés descartar
git reset --hard HEAD
git clean -fd

git pull origin main

# build + up
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

### 2.3. Crear superusuario (prod)
```bash
cd /opt/chatbot
docker compose -f docker-compose.prod.yml exec chatbot python manage.py createsuperuser --username rortigoza
```

### 2.4. Cambiar contraseña de superusuario (prod)
```bash
cd /opt/chatbot
docker compose -f docker-compose.prod.yml exec chatbot python manage.py changepassword rortigoza
```

---
## 3) Variables importantes (.env / .env.prod)

Variables mínimas:
```
SECRET_KEY=...
DEBUG=False
DATABASE_URL=postgresql://devlink:@Inf124578..@devlink_db:5455/devlink

WHATSAPP_PHONE_ID=...
WHATSAPP_ACCESS_TOKEN=...
WHATSAPP_VERIFY_TOKEN=...
```

Extras relevantes:
```
OUTBOUND_MAX_AGE_SECONDS=900
OUTBOUND_DROP_IF_NEWER_INBOUND=True
```

---
## 4) Troubleshooting común

### 4.1. "unknown flag: --force-recreatedocker"
Te faltó un espacio entre comandos:
```powershell
docker compose up -d --force-recreate
```

### 4.2. "network traefik_proxy declared as external, but could not be found"
En **local** no existe esa red. Usá `docker compose` sin `-f docker-compose.prod.yml`.

En **prod** asegurate de tener la red:
```bash
docker network ls | grep traefik_proxy
```

Si no existe:
```bash
docker network create traefik_proxy
```

### 4.3. "WHATSAPP_VERIFY_TOKEN variable is not set"
Setealo en `.env` (local) o `.env.prod` (prod).

### 4.4. "Docker permission denied" (en VPS)
Usar sudo:
```bash
sudo docker compose -f docker-compose.prod.yml up -d --build --force-recreate
```
o agregar tu usuario al grupo `docker`.

### 4.5. 502 Bad Gateway (Cloudflare)
Verifica:
- Traefik está up y en `traefik_proxy`
- `chatbot` en red `traefik_proxy`
- host rule en Traefik y Cloudflare tunnel apuntando a traefik

Comandos útiles:
```bash
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}"
docker network inspect traefik_proxy | grep aca_lujan_chatbot
docker logs traefik --tail 200
```

### 4.6. Admin 500 / migraciones pendientes
```bash
docker compose exec chatbot python manage.py migrate
```

---
## 5) Verificación rápida

### 5.1. Health local
```powershell
curl http://127.0.0.1:8006/api/health
```

### 5.2. Health prod
```bash
curl -k -H "Host: chatbot-api.devlink.com.ar" https://127.0.0.1/api/health
```

---
## 6) Notas de Cloudflare Tunnel

Si usás el túnel del server:
- El hostname `chatbot-api.devlink.com.ar` debe apuntar al mismo tunnel ID que el `chatbot.devlink.com.ar` (si comparten túnel).
- Revisar `/etc/cloudflared/config.yml` en el server.

Comando:
```bash
sudo cat /etc/cloudflared/config.yml
sudo systemctl restart cloudflared
```

---
## 7) FAQ rápido

**¿En local puedo usar la misma URL de webhook que en prod?**  
No. En local usá tu túnel local (Cloudflare/ngrok). En Meta debes registrar el webhook con esa URL local pública.

**¿Cómo cambio el webhook en Meta?**  
En Meta Developers → Webhooks → WhatsApp Business Account → cambiar URL + token.

