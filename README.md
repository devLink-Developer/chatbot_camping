# ACA Luján Chatbot - Python Edition

Versión mejorada del chatbot de ACA Luján usando **Python**, **FastAPI**, **PostgreSQL** y **Docker**.

## 🎯 Características

- ✅ **Webhook WhatsApp** - Recibe y procesa mensajes en tiempo real
- ✅ **Validación robusta** - Manejo de emojis, Unicode y caracteres especiales
- ✅ **Gestión de sesiones** - Control de estado de usuario con timeouts
- ✅ **Base de datos PostgreSQL** - Almacenamiento persistente
- ✅ **Dockerizado** - Docker y docker-compose para fácil deployment
- ✅ **API REST** - Endpoints adicionales para integración
- ✅ **Logging** - Auditoría completa de interacciones
- ✅ **Escalable** - Arquitectura modular y limpia

## 📋 Requisitos

- Docker y Docker Compose
- O Python 3.11+ con PostgreSQL

## 🚀 Inicio Rápido con Docker

### 1. Clonar y configurar

```bash
cd chatbot-python
cp .env.example .env
```

### 2. Editar `.env` con tus credenciales

```env
WHATSAPP_PHONE_ID=tu_phone_id
WHATSAPP_ACCESS_TOKEN=tu_token
WHATSAPP_VERIFY_TOKEN=tu_verify_token
SECRET_KEY=una_clave_secreta_fuerte
```

### 3. Iniciar servicios

```bash
docker-compose up -d
```

Esto levantará:
- **PostgreSQL** en puerto 5432
- **FastAPI** en puerto 8000

### 4. Importar datos

```bash
docker-compose exec chatbot python -m scripts.importar_datos
```

### 5. Verificar que funciona

```bash
curl http://localhost:8000/api/health
```

## 📚 Estructura del Proyecto

```
chatbot-python/
├── app/
│   ├── models/              # Modelos SQLAlchemy
│   │   ├── menu.py
│   │   ├── respuesta.py
│   │   ├── sesion.py
│   │   ├── registro.py
│   │   └── config.py
│   ├── services/            # Lógica de negocio
│   │   ├── validador.py     # Validación de entrada
│   │   ├── gestor_sesion.py # Gestión de sesiones
│   │   ├── gestor_contenido.py # Lectura de menús/respuestas
│   │   ├── navegador.py     # Lógica de navegación
│   │   └── cliente_whatsapp.py # Integración WhatsApp
│   ├── routes/              # Rutas FastAPI
│   │   └── webhook.py       # Endpoint del webhook
│   ├── config.py            # Configuración (Pydantic Settings)
│   ├── database.py          # Conexión BD
│   ├── schemas.py           # Modelos Pydantic
│   └── main.py              # Aplicación FastAPI
├── scripts/
│   └── importar_datos.py    # Script para migración de datos
├── Dockerfile               # Imagen Docker
├── docker-compose.yml       # Orquestación de servicios
├── requirements.txt         # Dependencias Python
├── .env.example             # Variables de entorno (template)
└── run.py                   # Punto de entrada
```

## 🔌 API Endpoints

### Webhook WhatsApp

```
POST /api/webhook
GET /api/webhook?hub_mode=subscribe&hub_challenge=...&hub_verify_token=...
```

Recibe mensajes de WhatsApp y retorna respuestas automáticas.

### Sesiones

```
GET /api/sesion/{phone_number}
POST /api/resetear-sesion/{phone_number}
```

Gestiona sesiones de usuario.

### Health Check

```
GET /api/health
```

Verifica estado del servicio.

### Documentación Interactiva

```
http://localhost:8000/docs          # Swagger UI
http://localhost:8000/redoc          # ReDoc
```

## 🛠️ Desarrollo Local

### Instalación

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar .env
cp .env.example .env
```

### Ejecutar localmente

```bash
# Asegurate que PostgreSQL esté ejecutándose
python run.py
```

### Ejecutar tests

```bash
# pytest (cuando esté implementado)
pytest
```

## 🗄️ Base de Datos

### Tablas principales

- **menus** - Menús del chatbot
- **respuestas** - Respuestas automáticas
- **sesiones** - Estado de sesiones de usuario
- **registros** - Auditoría de mensajes
- **config** - Configuración del bot

### Ejemplo de consultas

```sql
-- Ver última interacción por usuario
SELECT phone_number, mensaje_usuario, respuesta_enviada 
FROM registros 
ORDER BY created_at DESC 
LIMIT 10;

-- Sesiones activas
SELECT phone_number, estado_actual, ultimo_acceso_ms 
FROM sesiones 
WHERE activa = true;

-- Menús disponibles
SELECT id, titulo FROM menus WHERE activo = true;
```

## 📝 Importar Datos de MongoDB

El script `scripts/importar_datos.py` convierte datos de los archivos JSON de MongoDB:

```bash
python scripts/importar_datos.py
```

Importa:
- ✅ Menús desde `../colecciones_v1/chatbot.menus.json`
- ✅ Respuestas desde `../colecciones_v1/chatbot.respuestas.json`
- ✅ Configuración inicial

## 🔒 Variables de Entorno

```env
# Database
DATABASE_URL=postgresql://chatbot:password@postgres:5432/aca_lujan_bot

# WhatsApp
WHATSAPP_PHONE_ID=tu_phone_id
WHATSAPP_ACCESS_TOKEN=tu_access_token
WHATSAPP_VERIFY_TOKEN=tu_verify_token

# App
DEBUG=False
LOG_LEVEL=INFO
SECRET_KEY=clave_super_secreta

# Timeouts (en segundos)
SESSION_TIMEOUT_SECONDS=900
INACTIVE_TIMEOUT_SECONDS=1800
```

## 🐛 Troubleshooting

### Error de conexión a PostgreSQL

```bash
# Verificar que el contenedor está corriendo
docker-compose ps

# Ver logs de PostgreSQL
docker-compose logs postgres

# Reiniciar servicios
docker-compose down
docker-compose up -d
```

### Webhook no recibe mensajes

1. Verificar que el URL público es correcto en WhatsApp Console
2. Verificar el token de verificación en `.env`
3. Ver logs: `docker-compose logs -f chatbot`

### Error al importar datos

```bash
# Verificar rutas a archivos JSON
docker-compose exec chatbot ls -la ../colecciones_v1/

# Ejecutar con output detallado
docker-compose exec chatbot python -m scripts.importar_datos
```

## 📦 Deployment

### Production ready

```bash
# Compilar imagen
docker build -t aca-lujan-chatbot:1.0 .

# Ejecutar con variables de entorno
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e WHATSAPP_PHONE_ID=... \
  -e WHATSAPP_ACCESS_TOKEN=... \
  -e WHATSAPP_VERIFY_TOKEN=... \
  aca-lujan-chatbot:1.0
```

### Con Nginx (proxy reverso)

```nginx
server {
    listen 80;
    server_name tu-dominio.com;

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🚦 Monitoreo

### Ver logs en tiempo real

```bash
docker-compose logs -f chatbot
```

### Acceder a PostgreSQL

```bash
docker-compose exec postgres psql -U chatbot -d aca_lujan_bot
```

### Estadísticas de uso

```sql
-- Mensajes por día
SELECT DATE(created_at) as fecha, COUNT(*) as total 
FROM registros 
GROUP BY fecha 
ORDER BY fecha DESC;

-- Usuarios activos
SELECT COUNT(DISTINCT phone_number) FROM sesiones WHERE activa = true;
```

## 🤝 Contribuir

Sugerencias de mejoras:

- [ ] Sistema de reservas
- [ ] Notificaciones proactivas
- [ ] IA para respuestas automáticas (NLP)
- [ ] Admin panel
- [ ] Integración con Google Calendar
- [ ] Pago online

## 📞 Soporte

Para problemas o sugerencias:
- Revisar logs: `docker-compose logs chatbot`
- Documentación FastAPI: http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

## 📄 Licencia

Copyright © 2024 ACA Luján
