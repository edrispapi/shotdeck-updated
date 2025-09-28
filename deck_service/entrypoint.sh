#!/bin/sh
# Path: deck_service/entrypoint.sh
set -e

# Wait for this service's dedicated database to be ready
echo "Waiting for deck_db to be ready..."
while ! nc -z deck_db 5432; do
  sleep 1
done
echo "deck_db is ready."

# انتظار برای آماده شدن Kafka
echo "Waiting for Kafka to be ready..."
while ! nc -z kafka 9092; do
  sleep 1
done
echo "Kafka is ready."

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting deck_service server..."
exec python manage.py runserver 0.0.0.0:8000