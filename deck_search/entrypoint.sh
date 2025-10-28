#!/bin/bash
set -e

cd /app

echo "Applying database migrations for deck_search..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting deck_search server with Gunicorn..."
gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120 --access-logfile - --error-logfile -