#!/bin/sh
# Removed set -e to prevent exit on errors

echo "Applying database migrations for image_service..."
python manage.py migrate --noinput || echo "Migration failed, continuing..."

echo "Collecting static files..."
python manage.py collectstatic --noinput || echo "Collectstatic failed, continuing..."

echo "Loading sample data..."
python manage.py import_data /service/sample_data.json --clear || echo "Sample data import failed, continuing..."

echo "Indexing images in Elasticsearch..."
# Skip indexing during startup - will be done manually if needed
echo "Indexing skipped during startup to avoid timeout issues" || echo "Indexing skipped"

echo "Starting image_service server..."
exec python manage.py runserver 0.0.0.0:8000