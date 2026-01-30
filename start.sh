#!/bin/bash
set -e

echo "Iniciando servicios con Docker Compose..."
docker-compose up -d --build

echo "Esperando que PostgreSQL este listo..."
sleep 5

echo "Servicios iniciados correctamente."
echo ""
echo "Informacion:"
echo "  - API Chatbot: http://localhost:8006"
echo "  - Health: http://localhost:8006/api/health"
echo "  - PostgreSQL: localhost:5456"
echo ""
echo "Nota: migraciones y staticfiles se ejecutan automaticamente al iniciar el contenedor."
echo "Para ver logs: docker-compose logs -f chatbot"
echo "Para detener: docker-compose down"
