@echo off
REM Script para subir el proyecto a GitHub (Windows)

echo.
echo 🚀 Preparando para subir a GitHub...
echo.

REM Cambiar a directorio actual
cd /d "%~dp0"

echo 📍 Inicializando repositorio...
git init

echo 📋 Agregando archivos...
git add .

echo 💾 Creando commit...
git commit -m "🚀 Initial commit: Complete Python chatbot solution - FastAPI backend with WhatsApp webhook - PostgreSQL database with 5 tables - Docker ready - Production architecture"

echo.
echo ✅ Commit creado exitosamente
echo.
echo ⚠️  PRÓXIMOS PASOS:
echo.
echo 1. Agregar remote:
echo    git remote add origin https://github.com/devLink-Developer/chatbot_camping.git
echo.
echo 2. Cambiar rama a main:
echo    git branch -M main
echo.
echo 3. Hacer push:
echo    git push -u origin main
echo.
echo 📚 Proyecto listo para GitHub!
echo.
pause
