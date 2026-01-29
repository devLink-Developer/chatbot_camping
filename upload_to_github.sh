#!/bin/bash
# Script para subir el proyecto a GitHub

echo "🚀 Preparando para subir a GitHub..."
echo ""

# Navegar al directorio
cd "$(dirname "$0")"

# Configurar git si no está configurado
git config user.name "ACA Lujan Bot" 2>/dev/null || git config --global user.name "ACA Lujan Bot"
git config user.email "bot@aca-lujan.com" 2>/dev/null || git config --global user.email "bot@aca-lujan.com"

echo "📍 Inicializando repositorio..."
git init

echo "📋 Agregando archivos..."
git add .

echo "💾 Creando commit..."
git commit -m "🚀 Initial commit: Complete Python chatbot solution

- FastAPI backend with WhatsApp webhook
- PostgreSQL database with 5 tables
- Docker & docker-compose ready
- Complete documentation
- Automatic data migration from MongoDB
- Production-ready architecture"

echo ""
echo "✅ Commit creado exitosamente"
echo ""
echo "⚠️  PRÓXIMOS PASOS (ejecutar en terminal):"
echo ""
echo "1. Agregar remote:"
echo "   git remote add origin https://github.com/devLink-Developer/chatbot_camping.git"
echo ""
echo "2. Cambiar rama a main (si es necesario):"
echo "   git branch -M main"
echo ""
echo "3. Hacer push:"
echo "   git push -u origin main"
echo ""
echo "💡 Si tienes SSH configurado, usa:"
echo "   git remote add origin git@github.com:devLink-Developer/chatbot_camping.git"
echo ""
echo "📚 Proyecto listo para GitHub!"
