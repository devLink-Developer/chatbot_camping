# 🚀 Ejemplos Avanzados de Uso

## Casos de Uso y Soluciones

### 1. Agregar un nuevo menú dinámicamente

```python
# SQL directo
INSERT INTO menus (id, titulo, contenido, activo)
VALUES ('13', '1️⃣3️⃣ Nuevo Menú', 'Contenido aquí', true);

# O en Python:
from app.database import SessionLocal
from app.models.menu import Menu

db = SessionLocal()
nuevo_menu = Menu(
    id="13",
    titulo="13️⃣ Nuevo Menú",
    contenido="Contenido del nuevo menú",
    activo=True
)
db.add(nuevo_menu)
db.commit()
```

### 2. Agregar respuesta nueva

```python
from app.models.respuesta import Respuesta

respuesta = Respuesta(
    id="13A",
    categoria="nueva_seccion",
    contenido="Texto de la respuesta aquí",
    siguientes_pasos=["0", "#"],
    activo=True
)
db.add(respuesta)
db.commit()
```

### 3. Consultar sesiones activas

```python
from app.models.sesion import Sesion
from sqlalchemy import func
import time

db = SessionLocal()

# Sesiones activas en últimas 24 horas
sesiones_activas = db.query(Sesion).filter(
    Sesion.activa == True,
    Sesion.ultimo_acceso_ms > int(time.time() * 1000) - 86400000
).all()

for sesion in sesiones_activas:
    print(f"{sesion.phone_number} - {sesion.nombre}")
```

### 4. Obtener estadísticas

```python
from app.models.registro import Registro
from sqlalchemy import func
from datetime import datetime, timedelta

db = SessionLocal()

# Mensajes en últimas 24 horas
hoy = datetime.now() - timedelta(hours=24)
stats = db.query(
    func.count().label("total"),
    func.count(func.distinct(Registro.phone_number)).label("usuarios")
).filter(Registro.created_at > hoy).first()

print(f"Mensajes: {stats.total}")
print(f"Usuarios: {stats.usuarios}")
```

### 5. Resetear sesión de usuario

```python
from app.models.sesion import Sesion

db = SessionLocal()
phone = "+5491234567890"

sesion = db.query(Sesion).filter(Sesion.phone_number == phone).first()
if sesion:
    sesion.estado_actual = "0"
    sesion.historial_navegacion = ["0"]
    sesion.intentos_fallidos = 0
    db.commit()
```

### 6. Exportar mensajes a CSV

```python
import csv
from app.models.registro import Registro

db = SessionLocal()
registros = db.query(Registro).all()

with open("registros.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Teléfono", "Mensaje", "Acción", "Fecha"])
    for r in registros:
        writer.writerow([r.phone_number, r.mensaje_usuario, r.accion, r.created_at])
```

### 7. Buscar usuarios por patrón

```python
from app.models.registro import Registro
from sqlalchemy import or_

db = SessionLocal()

# Buscar mensajes con palabra clave
resultados = db.query(Registro).filter(
    or_(
        Registro.mensaje_usuario.ilike("%precios%"),
        Registro.mensaje_usuario.ilike("%costo%")
    )
).limit(10).all()
```

### 8. Crear respuesta automática por horario

```python
from datetime import datetime, time
from app.services import ClienteWhatsApp
from app.models.sesion import Sesion

db = SessionLocal()
ahora = datetime.now().time()

# Mensaje especial en horario de atención
if time(9, 0) <= ahora <= time(18, 0):
    mensaje = "Atención disponible 9-18hs"
else:
    mensaje = "Fuera de horario. Responderemos mañana."

sesiones = db.query(Sesion).filter(Sesion.activa == True).all()
for sesion in sesiones:
    ClienteWhatsApp.enviar_mensaje(sesion.phone_number, mensaje)
```

### 9. Analizar patrones de navegación

```python
from app.models.registro import Registro
from sqlalchemy import func

db = SessionLocal()

# Rutas más comunes
rutas = db.query(
    Registro.accion,
    Registro.target,
    func.count().label("veces")
).group_by(
    Registro.accion,
    Registro.target
).order_by(
    func.count().desc()
).limit(10).all()

for accion, target, veces in rutas:
    print(f"{accion} → {target}: {veces} veces")
```

### 10. Backup de base de datos

```bash
# Automated backup a archivo
docker-compose exec postgres pg_dump -U chatbot aca_lujan_bot > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore desde backup
docker-compose exec postgres psql -U chatbot aca_lujan_bot < backup_20240129_120000.sql
```

---

## Customizaciones Comunes

### A. Cambiar timeouts de sesión

**Archivo: `.env`**
```env
SESSION_TIMEOUT_SECONDS=600         # 10 minutos
INACTIVE_TIMEOUT_SECONDS=1800       # 30 minutos
```

### B. Agregar campo personalizado a sesión

**Archivo: `app/models/sesion.py`**
```python
class Sesion(Base):
    # ... campos existentes ...
    
    # Nuevo campo
    ciudad = Column(String(100), nullable=True)
    ocupacion = Column(String(100), nullable=True)
```

### C. Cambiar mensaje de bienvenida

```python
# En database (SQL)
UPDATE config 
SET valor = jsonb_set(valor, '{contenido}', '"Tu nuevo mensaje aquí"')
WHERE id = 'mensaje_bienvenida';
```

### D. Agregar validación personalizada

**Archivo: `app/services/validador.py`**
```python
@staticmethod
def validar_extension(entrada: str) -> bool:
    """Valida extensiones personalizadas"""
    if entrada == "RESERVA":
        return True
    return ValidadorEntrada.validar(entrada).es_valido
```

### E. Logging personalizado

**Archivo: `app/main.py`**
```python
import logging

logger = logging.getLogger(__name__)
logger.info(f"Usuario {phone} seleccionó opción {target}")
logger.warning(f"Intento fallido para {phone}")
logger.error(f"Error en webhook: {error}")
```

---

## Queries SQL Útiles

### Top 10 usuarios más activos
```sql
SELECT 
    phone_number, 
    nombre,
    COUNT(*) as total_mensajes,
    MAX(created_at) as ultimo_acceso
FROM registros
GROUP BY phone_number, nombre
ORDER BY total_mensajes DESC
LIMIT 10;
```

### Mensajes por hora del día
```sql
SELECT 
    EXTRACT(HOUR FROM created_at) as hora,
    COUNT(*) as total
FROM registros
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY hora
ORDER BY hora;
```

### Menús menos visitados
```sql
SELECT 
    target,
    COUNT(*) as veces
FROM registros
WHERE accion = 'ir_menu'
GROUP BY target
ORDER BY veces ASC
LIMIT 5;
```

### Usuarios sin completar
```sql
SELECT 
    phone_number,
    nombre,
    estado_actual,
    COUNT(*) as intentos_fallidos
FROM registros
WHERE accion = 'error'
GROUP BY phone_number, nombre, estado_actual
ORDER BY intentos_fallidos DESC;
```

### Performance - Respuesta más lenta
```sql
SELECT 
    phone_number,
    mensaje_usuario,
    respuesta_enviada,
    created_at
FROM registros
WHERE LENGTH(respuesta_enviada) > 500
ORDER BY created_at DESC
LIMIT 10;
```

---

## Integración con Sistemas Externos

### Enviar confirmación a email

```python
import smtplib
from email.mime.text import MIMEText

def enviar_confirmacion(email: str, mensaje: str):
    msg = MIMEText(mensaje)
    msg['Subject'] = "Confirmación de reserva"
    
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login('tu@email.com', 'tu_contraseña')
        server.send_message(msg)
```

### Integrar con Webhook externo

```python
import requests
from app.services import ClienteWhatsApp

def procesar_reserva(datos: dict):
    # Enviar a sistema externo
    response = requests.post(
        "https://api-reservas.com/crear",
        json=datos,
        timeout=5
    )
    
    if response.status_code == 200:
        ClienteWhatsApp.enviar_mensaje(
            datos["phone"],
            "✅ Reserva confirmada!"
        )
```

### Consultar datos en tiempo real

```python
from sqlalchemy import text

db = SessionLocal()
result = db.execute(text("""
    SELECT COUNT(*) as usuarios_en_linea
    FROM sesiones
    WHERE ultimo_acceso_ms > :cutoff
"""), {"cutoff": time.time() * 1000 - 300000})

print(result.fetchone()[0])
```

---

## Performance Optimization

### 1. Agregar índices

```sql
CREATE INDEX idx_phone_number ON registros(phone_number);
CREATE INDEX idx_created_at ON registros(created_at);
CREATE INDEX idx_sesion_activa ON sesiones(activa);
```

### 2. Cachear respuestas

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def obtener_respuesta_cacheada(respuesta_id: str):
    return GestorContenido.obtener_respuesta(db, respuesta_id)
```

### 3. Conexión pool

```python
# Ya implementado en database.py
# SQLAlchemy usa connection pooling automáticamente
```

---

## Seguridad

### 1. Validar webhook de WhatsApp

```python
import hashlib
import hmac

def verificar_firma_whatsapp(payload: str, token: str, header_sig: str) -> bool:
    """Verifica que el webhook viene de Meta"""
    hash_calc = hmac.new(
        token.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={hash_calc}" == header_sig
```

### 2. Rate limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/webhook")
@limiter.limit("100/minute")
async def webhook_whatsapp(request: Request):
    # ...
```

### 3. CORS restringido

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://mi-dominio.com"],  # Específico
    allow_methods=["POST"],                      # Solo POST
    allow_headers=["Content-Type"],              # Específico
)
```

---

## Deployment

### Para producción

1. **Variables en secrets (no .env)**
2. **HTTPS obligatorio**
3. **Rate limiting habilitado**
4. **Logs persistentes**
5. **Backup automático**
6. **Monitoreo activo**

```bash
# Build para prod
docker build -t aca-chatbot:prod --build-arg ENV=production .

# Push a registry
docker tag aca-chatbot:prod registry.com/aca-chatbot:latest
docker push registry.com/aca-chatbot:latest

# Deploy
docker run -d \
  --name chatbot-prod \
  --restart always \
  -e DATABASE_URL=$DB_URL \
  -e WHATSAPP_ACCESS_TOKEN=$WHATSAPP_TOKEN \
  registry.com/aca-chatbot:latest
```

---

## 🆘 Debugging

### Ver logs detallados

```bash
# Todos los logs
docker-compose logs chatbot

# Últimas 100 líneas
docker-compose logs --tail=100 chatbot

# En tiempo real (follow)
docker-compose logs -f chatbot

# Solo errores
docker-compose logs chatbot | grep ERROR
```

### Acceso a base de datos

```bash
# Conectar psql
docker-compose exec postgres psql -U chatbot -d aca_lujan_bot

# En psql:
\d                          # Ver tablas
SELECT * FROM sesiones;     # Ver datos
\q                          # Salir
```

### Test de endpoint

```bash
# Verificar que API responde
curl -i http://localhost:8000/api/health

# Con JSON
curl -s http://localhost:8000/api/health | jq .

# POST con data
curl -X POST http://localhost:8000/api/webhook \
  -H "Content-Type: application/json" \
  -d @payload.json
```

---

¡Que disfrutes tu chatbot! 🚀
