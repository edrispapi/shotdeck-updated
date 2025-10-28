#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up Shotdeck Search Service${NC}"

# Check if docker and docker-compose are installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

# Create docker network if it doesn't exist
echo -e "${YELLOW}Setting up docker network...${NC}"
docker network inspect shotdeck_platform_network >/dev/null 2>&1 || \
    docker network create shotdeck_platform_network

# Stop any running containers
echo -e "${YELLOW}Stopping existing containers...${NC}"
docker compose down

# Remove old elasticsearch data
echo -e "${YELLOW}Removing old Elasticsearch data...${NC}"
docker volume rm deck_search_deck_es_data || true

# Start the services
echo -e "${YELLOW}Starting services...${NC}"
docker compose up -d

# Wait for Elasticsearch to be ready
echo -e "${YELLOW}Waiting for Elasticsearch to be ready...${NC}"
until curl -s "http://localhost:12002/_cluster/health" | grep -q '"status":"green"'; do
    echo "Waiting for Elasticsearch..."
    sleep 5
done

# Reset Elasticsearch indices
echo -e "${YELLOW}Resetting Elasticsearch indices...${NC}"
docker compose exec deck_search_web python reset_elasticsearch.py

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