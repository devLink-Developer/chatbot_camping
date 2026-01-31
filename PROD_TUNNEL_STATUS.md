# Proyecto: Chatbot Django (ACA Lujan) + Estado PROD (Cloudflare Tunnel)

Fecha: 2026-01-31

Este documento resume lo que sabemos del proyecto, la arquitectura, el problema en producción con el túnel de Cloudflare y los pasos realizados hasta ahora. **No incluye secretos/tokens** (deben completarse a mano).

---

## 1) Resumen del proyecto
- Backend: **Django** (última versión usada: Django 6.0.1) con DRF.
- DB: **PostgreSQL**.
- Integración: **WhatsApp Cloud API (Meta)**.
- Webhook: recibe eventos de WhatsApp y responde según el flujo de menús/respuestas.
- Admin Django: gestión de menús, respuestas, clientes, campañas, jobs.
- Cola y timing humano de respuestas (typing indicator, delays, etc).
- Importación inicial desde colecciones JSON (colecciones_v1).

Repositorio principal:
- `C:\Users\rortigoza\Documents\Aca Lujan Bot\chatbot-python`

---

## 2) Archivos clave
- `Dockerfile` (usa `python:3.12-slim`).
- `docker-compose.prod.yml` (prod).
- `.env.prod` / `.env.example` / `.env`.
- `entrypoint.sh` (migraciones, importaciones y colecta de staticfiles).
- `scripts/importar_datos.py` (importa colecciones si tablas vacias).
- `colecciones_v1/` dentro del repo (datos base).

---

## 3) Puertos / Servicios
- App Django: **8006** (interno).
- Traefik: **80/443** (expone hacia internet).
- DB: contenedor `devlink_db` en el server (Postgres 16, puerto interno 5455, externo 5456).

---

## 4) Variables de entorno (sin secretos)
Archivo ejemplo: `.env.prod`

```
SECRET_KEY=...
DEBUG=False
LOG_LEVEL=INFO
DATABASE_URL=postgresql://USUARIO:PASS@devlink_db:5455/devlink
WHATSAPP_PHONE_ID=...
WHATSAPP_ACCESS_TOKEN=...
WHATSAPP_VERIFY_TOKEN=...
SESSION_TIMEOUT_SECONDS=900
INACTIVE_TIMEOUT_SECONDS=1800
WHATSAPP_ENABLE_TYPING_INDICATOR=True
...
```

Notas:
- La clave de DB usa URL encoding si hay caracteres especiales.
- `ALLOWED_HOSTS` incluye `.devlink.com.ar`, `devlink.com.ar`, `localhost`, `127.0.0.1`, `aca_lujan_chatbot`.
- `CSRF_TRUSTED_ORIGINS` incluye `https://*.devlink.com.ar`.

---

## 5) Traefik / Routing (prod)
En `docker-compose.prod.yml`:
- Router con regla:
  - `Host(chatbot-api.devlink.com.ar)` **y** `HostRegexp({subdomain}.devlink.com.ar)` **y** `Host(devlink.com.ar)`
- EntryPoints: `web,websecure`
- TLS: true
- Servicio: `loadbalancer.server.port=8006`

Se eliminaron `certresolver` en labels (Traefik usa certificados **estaticos**).

---

## 6) Estado del webhook / salud local
Prueba OK (con SNI correcto):

```
curl -k --resolve chatbot-api.devlink.com.ar:443:127.0.0.1 \
  https://chatbot-api.devlink.com.ar/api/health
```

Respuesta:
```
{"status":"ok","service":"ACA Lujan Chatbot Bot"}
```

Esto confirma:
- Traefik + Django responden correctamente.
- El problema era **antes de entrar al origin** (Cloudflare/Tunnel/DNS).

---

## 7) Problema en PROD: 502 desde Cloudflare
Síntomas:
- `https://chatbot-api.devlink.com.ar` devuelve **502 Bad Gateway** en Cloudflare.
- `https://chatbot.devlink.com.ar` funciona (n8n).

Root cause probable:
1) `chatbot-api` estaba apuntando a **otro tunnel** distinto al que corre en el server.
2) El tunnel del server no tenia la ruta `chatbot-api`.

---

## 8) Cloudflare Tunnel en server (n8n-tunnel)
Archivo en server:
- `/etc/cloudflared/config.yml`

Estado esperado:
```
tunnel: 0e0e4e15-58fc-4417-bed7-76f166ce887d
credentials-file: /etc/cloudflared/0e0e4e15-58fc-4417-bed7-76f166ce887d.json
protocol: http2
edge-ip-version: "4"

ingress:
  - hostname: chatbot.devlink.com.ar
    service: http://127.0.0.1:5678   # n8n
  - hostname: chatbot-api.devlink.com.ar
    service: http://127.0.0.1:80     # traefik
  - service: http_status:404
```

**Importante**: cloudflared corre en host, no dentro de docker. Por eso `service` debe usar `127.0.0.1`.

Reiniciar:
```
sudo systemctl restart cloudflared
```

---

## 9) DNS correcto en Cloudflare
Para que `chatbot-api` funcione usando el mismo tunnel que `chatbot`:
- `chatbot` y `chatbot-api` deben tener **el mismo CNAME** (misma URL `*.cfargotunnel.com`).
- Proxy **ON** (nube naranja).

Si `chatbot` funciona y `chatbot-api` no, casi seguro el CNAME de `chatbot-api` apunta a otro tunnel.

---

## 10) Estado actual (segun lo verificado)
- App responde OK detrás de Traefik cuando se prueba con SNI correcto.
- `cloudflared` corre en el server (n8n-tunnel).
- `config.yml` tiene la ruta `chatbot-api` hacia `127.0.0.1:80`.
- `nslookup chatbot-api.devlink.com.ar` resuelve a IPs de Cloudflare (proxy).
- Falta confirmar que el **CNAME** de `chatbot-api` apunte al **mismo tunnel ID** que `chatbot`.

---

## 11) Checklist de verificacion (final)
1) Confirmar CNAME:
   - `chatbot` y `chatbot-api` -> mismo `*.cfargotunnel.com`.
2) Confirmar `config.yml` en server:
   - `chatbot-api` -> `http://127.0.0.1:80`.
3) Reiniciar cloudflared:
   - `sudo systemctl restart cloudflared`
4) Probar:
   - `curl -k https://chatbot-api.devlink.com.ar/api/health`

---

## 12) Comandos utiles
```
sudo systemctl status cloudflared --no-pager
sudo journalctl -u cloudflared -n 80 --no-pager
sudo sed -n '/^ingress:/,$p' /etc/cloudflared/config.yml

curl -k --resolve chatbot-api.devlink.com.ar:443:127.0.0.1 \
  https://chatbot-api.devlink.com.ar/api/health
```

---

## 13) Notas de seguridad
- Tokens y accesos reales no se incluyen en este documento.
- No subir secretos a git.

