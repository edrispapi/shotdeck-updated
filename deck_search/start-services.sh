#!/bin/bash

echo "Starting services..."
docker compose up -d

echo "Waiting for services to be ready..."
sleep 5

echo "Collecting static files..."
docker compose exec deck_search_web python manage.py collectstatic --noinput

echo "Services started successfully!"
