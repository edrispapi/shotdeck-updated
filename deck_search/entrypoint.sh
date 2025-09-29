#!/bin/sh
set -e

echo "Applying database migrations for deck_search..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting deck_search server..."
exec python manage.py runserver 0.0.0.0:8000