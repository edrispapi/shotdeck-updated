# (Paste the setup.sh content from above)
#!/bin/bash

###############################################################################
# Shotdeck Search Service - Enhanced Setup Script
# Version: 2.0
# Last Updated: 2025-11-01
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/home/a/shotdeck-main/deck_search"
DOCKER_NETWORK="shotdeck_platform_network"
ES_WAIT_TIMEOUT=300  # 5 minutes
HEALTH_CHECK_RETRIES=10

# Helper Functions
print_header() {
    echo -e "\n${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}\n"
}

print_step() {
    echo -e "${YELLOW}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check Prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        echo "Please install Docker first: https://docs.docker.com/get-docker/"
        exit 1
    fi
    print_success "Docker is installed: $(docker --version)"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
        echo "Please install Docker Compose first"
        exit 1
    fi
    print_success "Docker Compose is installed: $(docker-compose --version)"
    
    # Check if running as root
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root"
        exit 1
    fi
    
    # Check .env file
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        print_error ".env file not found"
        print_info "Creating .env from .env.example..."
        if [ -f "$PROJECT_DIR/.env.example" ]; then
            cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
            print_success ".env file created"
            print_info "Please edit .env file with your configuration"
        else
            print_error ".env.example not found"
            exit 1
        fi
    else
        print_success ".env file exists"
    fi
}

# Create Docker Network
setup_network() {
    print_header "Setting up Docker Network"
    
    if docker network inspect $DOCKER_NETWORK >/dev/null 2>&1; then
        print_success "Network '$DOCKER_NETWORK' already exists"
    else
        print_step "Creating network '$DOCKER_NETWORK'..."
        docker network create $DOCKER_NETWORK
        print_success "Network created successfully"
    fi
}

# Stop Existing Containers
stop_containers() {
    print_header "Stopping Existing Containers"
    
    cd "$PROJECT_DIR"
    
    if docker-compose ps -q | grep -q .; then
        print_step "Stopping containers..."
        docker-compose down
        print_success "Containers stopped"
    else
        print_info "No running containers found"
    fi
}

# Clean Old Data (Optional)
clean_old_data() {
    print_header "Cleaning Old Elasticsearch Data"
    
    read -p "Do you want to remove old Elasticsearch data? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_step "Removing old Elasticsearch volume..."
        docker volume rm deck_search_deck_es_data 2>/dev/null || true
        print_success "Old data removed"
    else
        print_info "Keeping existing data"
    fi
}

# Build Images
build_images() {
    print_header "Building Docker Images"
    
    cd "$PROJECT_DIR"
    
    print_step "Building deck_search_web image..."
    docker-compose build deck_search_web
    print_success "Images built successfully"
}

# Start Services
start_services() {
    print_header "Starting Services"
    
    cd "$PROJECT_DIR"
    
    print_step "Starting all services..."
    docker-compose up -d
    
    sleep 3
    
    # Check if containers are running
    if docker-compose ps | grep -q "Up"; then
        print_success "Services started successfully"
    else
        print_error "Some services failed to start"
        docker-compose ps
        exit 1
    fi
}

# Wait for Elasticsearch
wait_for_elasticsearch() {
    print_header "Waiting for Elasticsearch"
    
    local elapsed=0
    local interval=5
    
    print_step "Checking Elasticsearch health (timeout: ${ES_WAIT_TIMEOUT}s)..."
    
    while [ $elapsed -lt $ES_WAIT_TIMEOUT ]; do
        if curl -s "http://localhost:12002/_cluster/health" | grep -q '"status":"green\|yellow"'; then
            print_success "Elasticsearch is ready!"
            return 0
        fi
        
        echo -ne "${YELLOW}⏳ Waiting... ${elapsed}s${NC}\r"
        sleep $interval
        elapsed=$((elapsed + interval))
    done
    
    print_error "Elasticsearch failed to start within timeout"
    print_info "Checking logs..."
    docker-compose logs --tail=50 deck_elasticsearch
    exit 1
}

# Initialize Elasticsearch Index
initialize_index() {
    print_header "Initializing Elasticsearch Index"
    
    cd "$PROJECT_DIR"
    
    print_step "Checking if reset_elasticsearch.py exists..."
    if docker-compose exec -T deck_search_web test -f reset_elasticsearch.py; then
        print_step "Resetting Elasticsearch indices..."
        docker-compose exec -T deck_search_web python reset_elasticsearch.py
        print_success "Indices initialized"
    else
        print_info "reset_elasticsearch.py not found, skipping index reset"
    fi
}

# Index Sample Data
index_sample_data() {
    print_header "Indexing Sample Data"
    
    read -p "Do you want to index sample data now? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter number of images to index (default: 100, 'all' for everything): " limit
        limit=${limit:-100}
        
        if [ "$limit" = "all" ]; then
            print_step "Indexing all images..."
            docker-compose exec deck_search_web python manage.py reindex_from_db --batch-size 100
        else
            print_step "Indexing $limit images..."
            docker-compose exec deck_search_web python manage.py reindex_from_db --limit "$limit" --batch-size 50
        fi
        
        print_success "Indexing completed"
    else
        print_info "You can index data later using:"
        print_info "  docker-compose exec deck_search_web python manage.py reindex_from_db"
    fi
}

# Health Check
health_check() {
    print_header "Health Check"
    
    local all_healthy=true
    
    # Check Elasticsearch
    print_step "Checking Elasticsearch..."
    if curl -s "http://localhost:12002/_cluster/health" | grep -q '"status":"green\|yellow"'; then
        print_success "Elasticsearch: Healthy"
    else
        print_error "Elasticsearch: Unhealthy"
        all_healthy=false
    fi
    
    # Check deck_search API
    print_step "Checking deck_search API..."
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:12004/" | grep -q "200"; then
        print_success "API: Healthy"
    else
        print_error "API: Unhealthy"
        all_healthy=false
    fi
    
    # Check database connection
    print_step "Checking database connection..."
    if docker-compose exec -T deck_search_web python manage.py check --database default &>/dev/null; then
        print_success "Database: Connected"
    else
        print_error "Database: Connection failed"
        all_healthy=false
    fi
    
    if [ "$all_healthy" = true ]; then
        print_success "All services are healthy!"
    else
        print_error "Some services are unhealthy. Check logs for details."
    fi
}

# Show Access URLs
show_access_info() {
    print_header "Setup Complete! 🎉"
    
    echo -e "${GREEN}Services are now available at:${NC}\n"
    
    echo -e "${CYAN}📊 Elasticsearch:${NC}"
    echo -e "   Local:   http://localhost:12002"
    echo -e "   Network: http://$(hostname -I | awk '{print $1}'):12002"
    
    echo -e "\n${CYAN}🔍 Search API:${NC}"
    echo -e "   Local:   http://localhost:12004/"
    echo -e "   Network: http://$(hostname -I | awk '{print $1}'):12004/"
    
    echo -e "\n${CYAN}📚 API Documentation:${NC}"
    echo -e "   Swagger: http://localhost:12004/docs/"
    echo -e "   Network: http://$(hostname -I | awk '{print $1}'):12004/docs/"
    
    echo -e "\n${YELLOW}Useful Commands:${NC}"
    echo -e "  View logs:     ${CYAN}docker-compose logs -f${NC}"
    echo -e "  Stop services: ${CYAN}docker-compose down${NC}"
    echo -e "  Restart:       ${CYAN}docker-compose restart${NC}"
    echo -e "  Index data:    ${CYAN}docker-compose exec deck_search_web python manage.py reindex_from_db${NC}"
    echo -e "  Shell access:  ${CYAN}docker-compose exec deck_search_web bash${NC}"
    
    echo -e "\n${GREEN}For more information, see README.md${NC}\n"
}

# Error Handler
trap 'print_error "Setup failed! Check the error messages above."; exit 1' ERR

# Main Execution
main() {
    print_header "🔍 Shotdeck Search Service - Setup"
    
    check_prerequisites
    setup_network
    stop_containers
    clean_old_data
    build_images
    start_services
    wait_for_elasticsearch
    initialize_index
    index_sample_data
    health_check
    show_access_info
}

# Run main function
main "$@"