# 📊 Colecciones MongoDB v1

## 🔧 Instrucciones de Importación

### MongoDB Compass
1. **Conectar a tu base de datos MongoDB**
2. **Crear nueva base de datos** (ej: `aca_lujan_bot`)
3. **Para cada archivo JSON:**
   - Crear nueva colección
   - Nombre: `menus_v1`, `respuestas_v1`, `registros_v1`
   - Click "ADD DATA" → "Import JSON or CSV file"
   - Seleccionar archivo correspondiente
   - Click "Import"

### MongoDB CLI
```bash
# Importar menus
mongoimport --db aca_lujan_bot --collection menus_v1 --file menus_v1.json --jsonArray

# Importar respuestas  
mongoimport --db aca_lujan_bot --collection respuestas_v1 --file respuestas_v1.json --jsonArray

# Importar registros
mongoimport --db aca_lujan_bot --collection registros_v1 --file registros_v1.json --jsonArray
```

## 📋 Descripción de Colecciones

### `menus_v1.json`
**Estructura de menús con navegación QWERTY**
- **id**: Identificador único del menú
- **titulo**: Título del menú
- **tipo**: Tipo (menu_principal, submenu)
- **parent_id**: ID del menú padre (para navegación)
- **breadcrumb**: Ruta de navegación para mostrar al usuario
- **opciones**: Array de opciones disponibles
- **mensaje**: Texto completo del menú a enviar

### `respuestas_v1.json`
**Respuestas del chatbot**
- **id**: Identificador único de la respuesta
- **titulo**: Título descriptivo
- **categoria**: Categoría temática
- **mensaje**: Texto de la respuesta a enviar
- **opciones_navegacion**: Opciones de navegación disponibles

### `registros_v1.json`
**Registros de usuarios (ejemplos)**
- **telefono**: Número de teléfono del usuario
- **nombre**: Nombre del usuario
- **estado**: Estado actual en el flujo
- **subestado**: Subestado específico
- **ultimo_menu**: Último menú visitado
- **fecha_inicio**: Timestamp de inicio de sesión
- **ultima_actividad**: Timestamp de última actividad
- **historial_navegacion**: Array con historial de navegación
- **interacciones**: Historial de mensajes intercambiados

## ✅ Verificación Post-Importación

Después de importar, verifica que:

1. **Colecciones creadas correctamente:**
   ```javascript
   // En MongoDB shell
   show collections
   // Debería mostrar: menus_v1, respuestas_v1, registros_v1
   ```

2. **Datos importados:**
   ```javascript
   db.menus_v1.count()      // Debería ser > 0
   db.respuestas_v1.count() // Debería ser > 0  
   db.registros_v1.count()  // Debería ser > 0
   ```

3. **Estructura correcta:**
   ```javascript
   db.menus_v1.findOne()      // Verificar estructura
   db.respuestas_v1.findOne() // Verificar estructura
   db.registros_v1.findOne()  // Verificar estructura
   ```

## 🔄 Actualización desde Versiones Anteriores

Si tienes colecciones antiguas (`menus`, `respuestas`, `registros`):

1. **Respaldar colecciones existentes:**
   ```javascript
   db.menus.find().forEach(function(doc) { 
       db.menus_backup.insert(doc) 
   });
   ```

2. **Importar nuevas colecciones v1**

3. **Actualizar referencias en n8n** (usar flujo actualizado en `/flujos_n8n/`)

## 🚨 Importante

- **NO elimines** las colecciones originales hasta verificar que todo funciona
- **Las colecciones v1** son independientes de las originales
- **El flujo de n8n** debe usar las referencias actualizadas a `_v1`