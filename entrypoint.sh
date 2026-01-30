#!/bin/sh
set -e

echo "Ejecutando migraciones..."
python manage.py migrate --noinput

echo "Importando datos iniciales si es necesario..."
python scripts/importar_datos.py

echo "Recolectando staticfiles..."
python manage.py collectstatic --noinput

exec "$@"
