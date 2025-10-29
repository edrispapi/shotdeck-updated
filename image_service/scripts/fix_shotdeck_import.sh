#!/bin/bash
# Fixed script addressing both issues

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}=== ShotDeck Dataset Import Fix (CORRECTED) ===${NC}"
echo ""

# Configuration
COMPOSE_DIR="$HOME/shotdeck-main/image_service"
CONTAINER_NAME="image_service"  # ← FIXED: underscore, not hyphen

cd "$COMPOSE_DIR"

# Determine docker compose command
if command -v docker-compose &> /dev/null; then
    DC="docker-compose"
else
    DC="docker compose"
fi

echo "Using: $DC"
echo "Container name: $CONTAINER_NAME"

# Check if containers are actually running
echo ""
echo "Checking container status..."
$DC ps

# Wait a bit more for service to fully start
echo ""
echo "Waiting 30s for image_service to fully start..."
sleep 30

# Verify container is running
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${RED}❌ Container $CONTAINER_NAME is not running!${NC}"
    echo ""
    echo "Checking logs:"
    $DC logs --tail=50 image_service
    exit 1
fi

echo -e "${GREEN}✅ Container is running${NC}"

# Check the actual structure inside container
echo ""
echo -e "${YELLOW}Checking mount structure inside container...${NC}"

echo "Contents of /host_data:"
docker exec "$CONTAINER_NAME" ls -la /host_data/ 2>/dev/null || echo -e "${RED}❌ /host_data not accessible${NC}"

echo ""
echo "Looking for shot_images and shot_json_data..."

# Check if dataset is at /host_data/dataset/ or directly at /host_data/
if docker exec "$CONTAINER_NAME" test -d /host_data/dataset/shot_images 2>/dev/null; then
    CONTAINER_IMG_PATH="/host_data/dataset/shot_images"
    CONTAINER_JSON_PATH="/host_data/dataset/shot_json_data"
    echo -e "${GREEN}✅ Dataset found at: /host_data/dataset/${NC}"
elif docker exec "$CONTAINER_NAME" test -d /host_data/shot_images 2>/dev/null; then
    CONTAINER_IMG_PATH="/host_data/shot_images"
    CONTAINER_JSON_PATH="/host_data/shot_json_data"
    echo -e "${GREEN}✅ Dataset found at: /host_data/${NC}"
else
    echo -e "${RED}❌ Cannot find shot_images in container!${NC}"
    echo ""
    echo "Full /host_data structure:"
    docker exec "$CONTAINER_NAME" find /host_data -maxdepth 3 -type d 2>/dev/null || echo "Cannot list"
    exit 1
fi

# Count files in container
echo ""
echo "Counting files in container..."
CNT_IMG=$(docker exec "$CONTAINER_NAME" sh -c "find $CONTAINER_IMG_PATH -name '*.jpg' 2>/dev/null | wc -l" || echo "0")
CNT_JSON=$(docker exec "$CONTAINER_NAME" sh -c "find $CONTAINER_JSON_PATH -name '*.json' 2>/dev/null | wc -l" || echo "0")

echo "  📊 Images in container: $CNT_IMG"
echo "  📊 JSON files in container: $CNT_JSON"

if [ "$CNT_IMG" -lt 1000 ] || [ "$CNT_JSON" -lt 1000 ]; then
    echo -e "${RED}❌ File counts too low!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Dataset properly mounted!${NC}"

# Run migrations first
echo ""
echo -e "${BLUE}Running database migrations...${NC}"
docker exec "$CONTAINER_NAME" python manage.py migrate

# Run import using the correct paths
echo ""
echo -e "${BLUE}Running import with correct paths...${NC}"

docker exec "$CONTAINER_NAME" python manage.py consolidated_commands import_complete \
    --json-dir "$CONTAINER_JSON_PATH" \
    --image-dir "$CONTAINER_IMG_PATH" \
    --batch-size 100

# Check database
echo ""
echo -e "${YELLOW}Checking database...${NC}"
$DC exec -T image-db psql -U postgres -d image_db -c "
SELECT 
    'Images' as type, COUNT(*) as count 
FROM images_image
UNION ALL
SELECT 
    'Movies' as type, COUNT(*) as count 
FROM images_movie
UNION ALL
SELECT 
    'Tags' as type, COUNT(*) as count 
FROM images_tag
ORDER BY type;
"

echo ""
echo -e "${GREEN}✅ Import Complete!${NC}"
echo ""
echo "Access points:"
echo "  API: http://localhost:51009/api/"
echo "  Admin: http://localhost:51009/admin/ (admin/admin123)"
echo "  Swagger: http://localhost:51009/api/schema/swagger-ui/"
echo ""
echo "Test API:"
echo "  curl 'http://localhost:51009/api/images/?limit=5'"