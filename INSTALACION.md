# 📖 Guía de Instalación y Configuración - Chatbot Python

## 🎯 Objetivo

Convertir tu chatbot de n8n a una solución **100% Python** con:
- **Backend FastAPI** con webhook integrado
- **PostgreSQL** como base de datos principal
- **Docker** para deployment reproducible
- **Validación robusta** de entradas
- **Gestión de sesiones** mejorada

## 📋 Requisitos Previos

- **Docker Desktop** (https://www.docker.com/products/docker-desktop)
- **Git** (opcional, para clonar)
- **Python 3.11+** (si quieres ejecutar localmente sin Docker)

## 🚀 Instalación Rápida (Docker)

### Paso 1: Preparar el directorio

```bash
cd "c:\Users\rortigoza\Documents\Aca Lujan Bot\chatbot-python"
```

### Paso 2: Configurar variables de entorno

```bash
copy .env.example .env
```

Editar `.env` con tus valores reales:

```env
DATABASE_URL=postgresql://chatbot:password@postgres:5432/aca_lujan_bot

# Obtener en https://developers.facebook.com/apps/
WHATSAPP_PHONE_ID=877312245455597
WHATSAPP_ACCESS_TOKEN=tu_token_aqui
WHATSAPP_VERIFY_TOKEN=tu_verify_token_aqui

DEBUG=False
LOG_LEVEL=INFO
SECRET_KEY=clave_super_secreta_muy_larga_min_32_caracteres

SESSION_TIMEOUT_SECONDS=900
INACTIVE_TIMEOUT_SECONDS=1800
```

### Paso 3: Iniciar servicios

```bash
docker-compose up -d
```

Esto levanta:
- 🐘 **PostgreSQL** en `localhost:5432`
- 🚀 **FastAPI** en `http://localhost:8000`

### Paso 4: Importar datos

```bash
docker-compose exec chatbot python -m scripts.importar_datos
```

Esto carga:
- ✅ Menús desde `chatbot.menus.json`
- ✅ Respuestas desde `chatbot.respuestas.json`
- ✅ Configuración inicial

### Paso 5: Verificar que funciona

```bash
# Health check
curl http://localhost:8000/api/health

# Docs interactivos
start http://localhost:8000/docs
```

## ⚙️ Obtener Credenciales de WhatsApp

### 1. Crear app en Facebook Developers

1. Ir a https://developers.facebook.com/apps
2. Click "Create App"
3. Seleccionar "Business" → "Next"
4. Llenar detalles
5. En Dashboard, ir a "WhatsApp Business Platform"

### 2. Obtener valores

```
WHATSAPP_PHONE_ID    → En "Phone Number ID"
WHATSAPP_ACCESS_TOKEN → Generate Token
WHATSAPP_VERIFY_TOKEN → Crear token seguro (ej: `python -c "import secrets; print(secrets.token_hex(16))"`)
```

### 3. Configurar webhook

En Meta App Dashboard → WhatsApp → Configuration:

```
Callback URL: https://tu-dominio.com/api/webhook
Verify Token:  (el que generaste)
```

## 🔌 Integrar con WhatsApp

### Para que reciba mensajes reales, configura en Facebook:

1. **Webhook URL**
   - Si está en local: usa ngrok → `ngrok http 8000`
   - Si es producción: tu dominio público

2. **Suscribirse a eventos**
   ```
   messages
   message_status
   message_template_status_update
   ```

3. **Testar webhook localmente**

```bash
# Terminal 1: Iniciar app
docker-compose up -d

# Terminal 2: Exponer con ngrok
ngrok http 8000

# Terminal 3: Simular mensaje WhatsApp
curl -X POST https://tu-ngrok-url/api/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "5491234567890",
            "text": {"body": "1"},
            "timestamp": 1234567890
          }],
          "contacts": [{
            "profile": {"name": "Juan"},
            "wa_id": "5491234567890"
          }]
        }
      }]
    }]
  }'
```

## 🗄️ Base de Datos

### Conectar a PostgreSQL

```bash
# Acceso directo a BD
docker-compose exec postgres psql -U chatbot -d aca_lujan_bot

# Dentro de psql:
\dt                    -- Ver tablas
SELECT * FROM menus;   -- Ver menús
SELECT * FROM sesiones;  -- Ver sesiones activas
\q                     -- Salir
```

### Tablas principales

```sql
-- Menús disponibles
SELECT id, titulo, submenu FROM menus WHERE activo = true;

-- Últimos mensajes
SELECT phone_number, mensaje_usuario, accion, created_at 
FROM registros 
ORDER BY created_at DESC 
LIMIT 20;

-- Sesiones activas
SELECT phone_number, nombre, estado_actual, ultimo_acceso_ms 
FROM sesiones 
WHERE activa = true;

-- Estadísticas
SELECT COUNT(DISTINCT phone_number) as usuarios_unicos
FROM registros
WHERE created_at > NOW() - INTERVAL '1 day';
```

## 📝 Estructura de Archivos

```
chatbot-python/
├── app/
│   ├── models/              # Modelos SQLAlchemy (BD)
│   │   ├── __init__.py
│   │   ├── menu.py          # Tabla menus
│   │   ├── respuesta.py     # Tabla respuestas
│   │   ├── sesion.py        # Tabla sesiones
│   │   ├── registro.py      # Tabla registros
│   │   └── config.py        # Tabla config
│   │
│   ├── services/            # Lógica de negocio
│   │   ├── __init__.py
│   │   ├── validador.py     # ⭐ Valida entrada del usuario
│   │   ├── gestor_sesion.py # Maneja sesiones
│   │   ├── gestor_contenido.py # Lee menus/respuestas
│   │   ├── navegador.py     # Lógica de navegación
│   │   └── cliente_whatsapp.py # Envía mensajes
│   │
│   ├── routes/              # Endpoints FastAPI
│   │   ├── __init__.py
│   │   └── webhook.py       # POST /api/webhook
│   │
│   ├── utils/               # Funciones auxiliares
│   │   ├── __init__.py
│   │   └── helpers.py       # UUID, timestamps, etc
│   │
│   ├── __init__.py
│   ├── config.py            # Configuración (env vars)
│   ├── database.py          # Conexión a PostgreSQL
│   ├── schemas.py           # Modelos Pydantic (validación)
│   └── main.py              # Aplicación FastAPI
│
├── scripts/                 # Scripts de utilidad
│   ├── __init__.py
│   ├── importar_datos.py    # Migrar MongoDB → PostgreSQL
│   └── crear_env.py         # Crear archivo .env
│
├── migrations/              # Migraciones Alembic (opcional)
├── Dockerfile               # Imagen Docker
├── docker-compose.yml       # Orquestación servicios
├── requirements.txt         # Dependencias Python
├── .env.example             # Template variables entorno
├── .gitignore               # Archivos ignorar en git
├── run.py                   # Punto entrada (python run.py)
├── test_chatbot.py          # Tests unitarios
├── README.md                # Documentación
└── CHANGELOG.md             # Historia de cambios
```

## 🛠️ Desarrollo Local (sin Docker)

### Instalación

```bash
# Crear entorno virtual
python -m venv venv

# Activar (Windows)
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Crear .env
copy .env.example .env
```

### Ejecutar PostgreSQL

```bash
# Opción 1: Docker solo para BD
docker run -d \
  --name pg_chatbot \
  -e POSTGRES_USER=chatbot \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=aca_lujan_bot \
  -p 5432:5432 \
  postgres:15-alpine

# Opción 2: PostgreSQL instalado localmente
# (asegurate que esté corriendo)
```

### Ejecutar app

```bash
python run.py
# O con auto-reload:
uvicorn app.main:app --reload
```

## 🐛 Troubleshooting

### Error: "conexión rechazada" a PostgreSQL

```bash
# Verificar que contenedor está corriendo
docker-compose ps

# Si no:
docker-compose up -d postgres

# Esperar 10 segundos y reintentar
```

### Error: "Token de verificación inválido"

```bash
# Verificar que .env tiene el token correcto
cat .env | grep WHATSAPP_VERIFY_TOKEN

# Ver logs
docker-compose logs -f chatbot | grep -i token
```

### Error: "No se encuentran archivos JSON"

```bash
# Verificar que existen archivos
ls -la ../colecciones_v1/

# Si no, copiar desde ubicación original
cp "c:\Users\rortigoza\Documents\Aca Lujan Bot\colecciones_v1\*" \
   "chatbot-python\colecciones_v1\"
```

### Port 8000 ya en uso

```bash
# Cambiar en docker-compose.yml:
# De:   ports: ["8000:8000"]
# A:    ports: ["8001:8000"]

# Luego:
docker-compose up -d
```

## 📊 Monitoreo

### Ver logs en tiempo real

```bash
docker-compose logs -f chatbot
```

### Ver solo errores

```bash
docker-compose logs chatbot | grep ERROR
```

### Estadísticas de uso

```bash
# Conectar a BD
docker-compose exec postgres psql -U chatbot -d aca_lujan_bot

# Ver top 10 usuarios más activos
SELECT 
  phone_number, 
  nombre, 
  COUNT(*) as mensajes 
FROM registros 
GROUP BY phone_number, nombre 
ORDER BY mensajes DESC 
LIMIT 10;

# Mensajes por hora
SELECT 
  DATE_TRUNC('hour', created_at) as hora,
  COUNT(*) as total
FROM registros
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY hora
ORDER BY hora DESC;
```

## 🚀 Deploy a Producción

### Opción 1: En tu servidor

```bash
# 1. Clonar repo
git clone tu-repo
cd chatbot-python

# 2. Crear .env con valores producción
nano .env

# 3. Iniciar
docker-compose -f docker-compose.prod.yml up -d
```

### Opción 2: Heroku / Railway / Render

```bash
# Cada plataforma tiene sus pasos, pero básicamente:
# 1. Push a GitHub
# 2. Conectar repo
# 3. Configurar variables de entorno
# 4. Deploy automático
```

### Opción 3: AWS / GCP / Azure

```bash
# Usar ECR/Container Registry
docker build -t aca-lujan-chatbot:1.0 .
docker tag aca-lujan-chatbot:1.0 tu-registry/aca-lujan:latest
docker push tu-registry/aca-lujan:latest

# Luego desplegar en ECS/Cloud Run/Container Instances
```

## 📞 API Endpoints

```
GET  /                                  # Root
GET  /api/health                        # Health check
POST /api/webhook                       # Webhook WhatsApp (main)
GET  /api/webhook                       # Verificar webhook
GET  /api/sesion/{phone_number}         # Obtener sesión
POST /api/resetear-sesion/{phone_number} # Reset sesión
GET  /docs                              # Swagger UI
GET  /redoc                             # ReDoc
```

## 🔐 Seguridad

### Production checklist

- [ ] `DEBUG=False` en .env
- [ ] `SECRET_KEY` con valor criptográficamente seguro
- [ ] HTTPS/SSL configurado
- [ ] Token de WhatsApp en variable de entorno (no hardcodeado)
- [ ] CORS restringido a dominios permitidos
- [ ] Logs monitoreados
- [ ] Backup automático de BD
- [ ] Rate limiting en endpoints

## 📚 Recursos Adicionales

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://docs.sqlalchemy.org/)
- [PostgreSQL](https://www.postgresql.org/docs/)
- [WhatsApp API](https://developers.facebook.com/docs/whatsapp)
- [Docker](https://docs.docker.com/)

## 💬 Soporte

Para problemas:

1. Revisar logs: `docker-compose logs chatbot`
2. Health check: `curl http://localhost:8000/api/health`
3. Docs: `http://localhost:8000/docs`
4. Revisar esta guía

---

**¡Listo para empezar!** 🎉
