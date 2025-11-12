#!/bin/sh

set -e

DB_HOST=${DB_HOST:-image-db}
DB_PORT=${DB_PORT:-5432}
ELASTICSEARCH_HOST=${ELASTICSEARCH_HOST:-deck_elasticsearch}
ELASTICSEARCH_PORT=${ELASTICSEARCH_PORT:-9200}

echo "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."
while ! nc -z "${DB_HOST}" "${DB_PORT}"; do
  sleep 1
done
echo "PostgreSQL is ready."

echo "Waiting for Elasticsearch at ${ELASTICSEARCH_HOST}:${ELASTICSEARCH_PORT}..."
while ! nc -z "${ELASTICSEARCH_HOST}" "${ELASTICSEARCH_PORT}"; do
  sleep 1
done
echo "Elasticsearch is ready."

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting deck_search server..."
exec python manage.py runserver 0.0.0.0:8000

