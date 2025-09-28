#!/bin/sh
set -e

echo "Applying database migrations for search_service..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting search_service server..."
exec python manage.py runserver 0.0.0.0:8000