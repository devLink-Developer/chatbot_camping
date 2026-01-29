#!/bin/bash
set -e

echo "🚀 Iniciando servicios con Docker Compose..."
docker-compose up -d

echo "⏳ Esperando que PostgreSQL esté listo..."
sleep 5

echo "✅ Servicios iniciados correctamente!"
echo ""
echo "📋 Información:"
echo "  - API Chatbot: http://localhost:8000"
echo "  - Docs: http://localhost:8000/docs"
echo "  - PostgreSQL: localhost:5432"
echo ""
echo "Para ver logs: docker-compose logs -f chatbot"
echo "Para detener: docker-compose down"
