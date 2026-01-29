# 🤖 ACA Luján Chatbot - Python Edition

> Solución profesional de chatbot para WhatsApp usando **Python**, **FastAPI**, **PostgreSQL** y **Docker**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 🎯 Descripción

Chatbot inteligente para el Centro Recreativo y Camping ACA de Luján. Reemplaza la solución anterior en n8n con una implementación **profesional, escalable y de bajo costo**.

### Principales Características

- ✅ **Webhook WhatsApp** - Recibe y procesa mensajes en tiempo real
- ✅ **Validación Robusta** - Manejo perfecto de emojis, Unicode y caracteres especiales
- ✅ **Gestión de Sesiones** - Control automático de estado con timeouts configurables
- ✅ **Base de Datos PostgreSQL** - Almacenamiento persistente y auditoría completa
- ✅ **Dockerizado** - Deployment reproducible en cualquier lugar
- ✅ **API REST** - Endpoints adicionales para integración
- ✅ **Logging Completo** - Auditoría de cada interacción
- ✅ **100% Escalable** - Arquitectura modular y limpia

## 📊 Comparativa: n8n vs Python

| Aspecto | n8n | Python |
|---------|-----|--------|
| **Costo** | $$$ pagado | Gratis ✓ |
| **Performance** | Media | ⭐⭐⭐⭐⭐ |
| **Escalabilidad** | Media | ⭐⭐⭐⭐⭐ |
| **Mantenibilidad** | Difícil | ⭐⭐⭐⭐⭐ |
| **Control** | Limitado | Total ✓ |
| **Deployment** | Cloud | Anywhere ✓ |

## 🚀 Quick Start

### Requisitos
- Docker & Docker Compose
- Python 3.11+ (opcional, para desarrollo local)

### 1. Clonar y configurar

```bash
git clone https://github.com/devLink-Developer/chatbot_camping.git
cd chatbot_camping
cp .env.example .env
```

### 2. Editar `.env` con credenciales

```env
WHATSAPP_PHONE_ID=tu_phone_id
WHATSAPP_ACCESS_TOKEN=tu_token
WHATSAPP_VERIFY_TOKEN=tu_verify_token
```

### 3. Iniciar con Docker

```bash
docker-compose up -d
```

### 4. Importar datos (opcional)

```bash
docker-compose exec chatbot python -m scripts.importar_datos
```

### 5. Verificar

```
http://localhost:8000/docs
```

## 📁 Estructura

```
chatbot_camping/
├── app/
│   ├── models/          # Modelos SQLAlchemy (5 tablas)
│   ├── services/        # Lógica core (5 servicios)
│   ├── routes/          # Endpoints FastAPI
│   ├── utils/           # Funciones auxiliares
│   ├── main.py          # Aplicación FastAPI
│   ├── config.py        # Configuración
│   ├── database.py      # PostgreSQL
│   └── schemas.py       # Validación Pydantic
│
├── scripts/
│   ├── importar_datos.py    # MongoDB → PostgreSQL
│   └── crear_env.py         # Generar .env
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── README.md
└── ...
```

## 🔌 API Endpoints

```
POST   /api/webhook                          Webhook WhatsApp (main)
GET    /api/webhook                          Verificar webhook
GET    /api/sesion/{phone_number}           Obtener sesión
POST   /api/resetear-sesion/{phone_number}   Reset sesión
GET    /api/health                           Health check
GET    /docs                                 Swagger UI
GET    /redoc                                ReDoc
```

## 🗄️ Base de Datos

- **menus** - Menús del chatbot (13 registros)
- **respuestas** - Respuestas automáticas (30+ registros)
- **sesiones** - Estado de usuarios activos
- **registros** - Auditoría completa de interacciones
- **config** - Configuración del bot

## 🔧 Servicios Principales

### ValidadorEntrada
Valida y normaliza entrada del usuario
- Convierte a mayúsculas
- Remueve emojis manteniendo texto
- Valida números (1-12) y letras (A-Z)
- Soporta comandos especiales (#, 0, help)

### GestorSesion
Gestiona sesiones de usuario
- Obtiene o crea automáticamente
- Control de timeouts
- Historial de navegación persistente

### NavigadorBot
Lógica de navegación entre menús
- Procesa entrada del usuario
- Mantiene historial
- Retorna contenido apropiado

### GestorContenido
Lee contenido desde BD
- Menús y respuestas dinámicos
- Formateo para WhatsApp
- Navegación automática

### ClienteWhatsApp
Envía mensajes a través de WhatsApp API
- Integración con Meta
- Logging de entregas
- Manejo de errores

## 📚 Documentación

- [INSTALACION.md](INSTALACION.md) - Guía paso a paso
- [EJEMPLOS_AVANZADOS.md](EJEMPLOS_AVANZADOS.md) - Casos de uso
- [COMPLETADO.md](COMPLETADO.md) - Resumen técnico
- [CHANGELOG.md](CHANGELOG.md) - Historial

## 🔐 Seguridad

- `.env` en `.gitignore` (no se sube a git)
- Tokens en variables de entorno
- SECRET_KEY configurable
- Validación de entrada
- CORS configurable

## 🧪 Testing

```bash
# Swagger interactivo
http://localhost:8000/docs

# Health check
curl http://localhost:8000/api/health

# Tests script
./test_webhook.sh

# Logs en vivo
docker-compose logs -f chatbot
```

## 📦 Deployment

### Con Docker Compose
```bash
docker-compose up -d
```

### Con Docker solo
```bash
docker build -t aca-chatbot:1.0 .
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e WHATSAPP_ACCESS_TOKEN=... \
  aca-chatbot:1.0
```

## 🆘 Troubleshooting

### PostgreSQL no conecta
```bash
docker-compose down
docker-compose up -d
```

### Puerto 8000 en uso
Cambiar en `docker-compose.yml`: `ports: ["8001:8000"]`

### Webhook no recibe mensajes
1. Verificar token en `.env`
2. Verificar URL en Meta Developers Console
3. Ver logs: `docker-compose logs chatbot`

## 🤝 Contribución

Sugerencias de mejoras:
- [ ] Sistema de reservas
- [ ] IA/NLP para respuestas inteligentes
- [ ] Admin panel web
- [ ] Notificaciones proactivas
- [ ] Integración con Google Calendar
- [ ] Pago online

## 📄 Licencia

MIT License - Libre para usar y modificar

## 📞 Soporte

- 📖 Lee la documentación en `/docs`
- 🐛 Revisa logs: `docker-compose logs -f`
- 🔍 Accede a Swagger: `http://localhost:8000/docs`

---

**Versión:** 1.0.0  
**Última actualización:** 2024-01-29  
**Estado:** ✅ Production Ready

Hecho con ❤️ para ACA Luján
