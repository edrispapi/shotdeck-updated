#!/bin/bash

echo "Stopping services..."
docker compose down

echo "Cleaning up volumes..."
docker compose down -v

echo "Removing all unused containers, networks, and volumes..."
docker system prune -f
