# Diagnóstico del Túnel Cloudflared - 31/01/2026

## Estado Actual
✅ **Cloudflared está funcionando correctamente** en el servidor
- Servicio: `systemctl status cloudflared`
- Conexiones activas: 4
- Tunnel ID: `0e0e4e15-58fc-4417-bed7-76f166ce887d`

## Archivo de Configuración
✅ **Archivo `/etc/cloudflared/config.yml` contiene todas las rutas:**
```
tunnel: 0e0e4e15-58fc-4417-bed7-76f166ce887d
credentials-file: /etc/cloudflared/0e0e4e15-58fc-4417-bed7-76f166ce887d.json
protocol: http2

ingress:
  - hostname: chatbot.devlink.com.ar
    service: http://127.0.0.1:5678
  - hostname: chatbot-api.devlink.com.ar
    service: http://127.0.0.1:80
  - service: http_status:404
```

Verificado con: `grep -n . /etc/cloudflared/config.yml` ✓

## ✅ Problema Root Cause Identificado

**Cloudflare Dashboard controla qué rutas se envían al túnel**, no el archivo local `config.yml`.

Aunque creamos el DNS record `chatbot-api.devlink.com.ar`, Cloudflare no lo reconoce como ruta válida del túnel.

Los logs de cloudflared muestran que Cloudflare está enviando:
```
"ingress":[{"hostname":"chatbot.devlink.com.ar",...},{"service":"http_status:404"}]
```

**Falta `chatbot-api` porque Cloudflare no lo ha registrado en el túnel.**

## ✅ Próximos Pasos - QUÉ HACER AHORA

### Opción 1: Cloudflare Dashboard (RECOMENDADO - 2 minutos)
1. Ve a **Cloudflare Dashboard** → **Tunnels**
2. Selecciona tu túnel: `0e0e4e15-58fc-4417-bed7-76f166ce887d`
3. Haz clic en **"Public Hostname"**
4. Haz clic en **"Add a public hostname"**
5. Completa el formulario:
   - **Subdomain**: `chatbot-api`
   - **Domain**: `devlink.com.ar`
   - **Type**: `HTTP` 
   - **URL**: `http://127.0.0.1:80`
6. Haz clic en **Save**
7. **Espera 30-60 segundos** a que se sincronice

### Verificar que Funcionó
Una vez completado:
```bash
# Desde tu máquina local
curl https://chatbot-api.devlink.com.ar/api/health

# O desde el servidor
curl https://chatbot-api.devlink.com.ar/api/health
```

## 📝 Lo que Ya Hemos Completado

## Comandos para Verificar en el Servidor

```bash
# Ver estado del túnel
sudo systemctl status cloudflared --no-pager

# Ver logs en tiempo real
sudo journalctl -u cloudflared -f

# Ver últimas 50 líneas de logs
sudo journalctl -u cloudflared -n 50 --no-pager

# Verificar el archivo de config
cat /etc/cloudflared/config.yml

# Probar conectividad directa a Traefik (sin Cloudflare)
curl -k --resolve chatbot-api.devlink.com.ar:443:127.0.0.1 https://chatbot-api.devlink.com.ar/api/health
```

## Variables de Conexión SSH

```
Host: 200.58.107.187
Puerto: 5344
Usuario: rortigoza
Contraseña: <SSH_PASSWORD>
```

---

**Próximo paso recomendado:** Verifica el dashboard de Cloudflare para asegurar que ambos hostnames están configurados correctamente.
