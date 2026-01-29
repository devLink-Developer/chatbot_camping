# 📤 Instrucciones para Subir a GitHub

Tu repositorio GitHub está vacío y listo para recibir el código.

**Repositorio:** https://github.com/devLink-Developer/chatbot_camping.git

## 🚀 Opción 1: Automático (Recomendado para Windows)

1. Abre terminal en el directorio del proyecto:
```bash
cd "c:\Users\rortigoza\Documents\Aca Lujan Bot\chatbot-python"
```

2. Ejecuta el script:
```bash
upload_to_github.bat
```

El script creará el commit automáticamente y te dará instrucciones.

## 🔧 Opción 2: Manual (Paso a paso)

### Paso 1: Configurar Git

```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu@email.com"
```

### Paso 2: Inicializar repositorio local

```bash
cd "c:\Users\rortigoza\Documents\Aca Lujan Bot\chatbot-python"
git init
```

### Paso 3: Agregar todos los archivos

```bash
git add .
```

### Paso 4: Crear el commit

```bash
git commit -m "🚀 Initial commit: Complete Python chatbot solution

- FastAPI backend con webhook WhatsApp
- PostgreSQL database con 5 tablas
- Docker & docker-compose
- Documentación completa
- Migración automática de datos
- Arquitectura production-ready"
```

### Paso 5: Agregar remote

```bash
git remote add origin https://github.com/devLink-Developer/chatbot_camping.git
```

O si usas SSH (más seguro):
```bash
git remote add origin git@github.com:devLink-Developer/chatbot_camping.git
```

### Paso 6: Cambiar rama a main

```bash
git branch -M main
```

### Paso 7: Hacer push

```bash
git push -u origin main
```

## ✅ Verificación

Después de hacer push, verifica en GitHub:

```
https://github.com/devLink-Developer/chatbot_camping
```

Deberías ver:
- ✅ 30+ archivos
- ✅ Documentación
- ✅ Código Python
- ✅ Docker files
- ✅ Scripts

## 🔐 Credenciales (Importante)

Si GitHub pide autenticación:

### Opción A: Token Personal (Recomendado)

1. Ir a https://github.com/settings/tokens
2. Generar nuevo token (classic o fine-grained)
3. Usar como contraseña cuando Git pida

### Opción B: SSH (Más seguro)

1. Generar clave SSH:
```bash
ssh-keygen -t ed25519 -C "tu@email.com"
```

2. Agregar a GitHub:
   - Ir a https://github.com/settings/keys
   - Copiar contenido de `~/.ssh/id_ed25519.pub`

3. Usar SSH al hacer push:
```bash
git remote set-url origin git@github.com:devLink-Developer/chatbot_camping.git
```

## 🆘 Troubleshooting

### Error: "fatal: not a git repository"

```bash
git init
git add .
git commit -m "message"
```

### Error: "fatal: remote origin already exists"

```bash
git remote remove origin
git remote add origin https://github.com/devLink-Developer/chatbot_camping.git
```

### Error: "Permission denied (publickey)"

Problema de SSH. Solución:
```bash
git remote set-url origin https://github.com/devLink-Developer/chatbot_camping.git
```

### Error: "Authentication failed"

Necesitas token. Ir a https://github.com/settings/tokens

## 📊 Contenido que se va a subir

```
chatbot_camping/
├── 📖 Documentación (7 archivos)
├── 🐍 Código Python (30+ archivos)
├── 🐳 Docker (2 archivos)
├── 🔧 Scripts (4 scripts)
├── 🧪 Tests (2 archivos)
└── ⚙️ Configuración (5 archivos)
```

Total: **50+ archivos** listos para subir

## 📈 Futuro

Después de este primer push, puedes:

1. **Crear branches** para features:
```bash
git checkout -b feature/reservas
```

2. **Hacer más commits**:
```bash
git commit -m "mensaje"
git push
```

3. **Crear releases**:
```bash
git tag -a v1.0.0 -m "Version 1.0.0"
git push origin v1.0.0
```

4. **Agregar GitHub Actions** para CI/CD

## ✨ Resultado Final

Cuando termines de hacer push, tendrás:

✅ Código en la nube  
✅ Respaldo seguro  
✅ Fácil colaboración  
✅ Seguimiento de cambios  
✅ Historial completo  

---

**¡Listo!** Sigue estos pasos y tu código estará en GitHub. 🚀
