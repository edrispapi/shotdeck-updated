#!/bin/sh
set -e

echo "Waiting for image_db to be ready..."
while ! nc -z image_db 5432; do
  sleep 1
done
echo "image_db is ready."

echo "Waiting for Kafka to be ready..."
while ! nc -z kafka 9092; do
  sleep 1
done
echo "Kafka is ready."

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting image_service server..."
exec python manage.py runserver 0.0.0.0:8000