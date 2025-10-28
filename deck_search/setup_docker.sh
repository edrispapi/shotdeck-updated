#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up Shotdeck Search Service${NC}"

# Create necessary directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p logs

# Check if docker and docker-compose are installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create docker network if it doesn't exist
echo -e "${YELLOW}Setting up docker network...${NC}"
docker network inspect shotdeck_platform_network >/dev/null 2>&1 || \
    docker network create shotdeck_platform_network

# Pull the latest changes if in a git repository
if [ -d .git ]; then
    echo -e "${YELLOW}Pulling latest changes...${NC}"
    git pull origin main
fi

# Stop any running containers
echo -e "${YELLOW}Stopping existing containers...${NC}"
docker compose down

# Start the services
echo -e "${YELLOW}Starting services...${NC}"
docker compose up -d

# Wait for services to be healthy
echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
attempt=1
max_attempts=30
until docker compose ps | grep deck_search_web | grep -q "healthy" || [ $attempt -eq $max_attempts ]; do
    echo "Waiting for services to be ready... (Attempt $attempt/$max_attempts)"
    sleep 10
    ((attempt++))
done

if [ $attempt -eq $max_attempts ]; then
    echo "Services did not become healthy within the expected time"
    docker compose logs
    exit 1
fi

# Final status check
echo -e "${GREEN}Checking final status:${NC}"
docker compose ps

# Print access URLs
echo -e "${GREEN}Setup complete!${NC}"
echo -e "Services are now available at:"
echo -e "${YELLOW}Elasticsearch:${NC} http://localhost:12002"
echo -e "${YELLOW}Search API Docs:${NC} http://localhost:12004/docs/"
echo -e "${YELLOW}Search API External:${NC} http://192.168.100.11:12004/docs/"

# Print logs command hint
echo -e "\n${YELLOW}To view logs, run:${NC}"
echo "docker compose logs -f"