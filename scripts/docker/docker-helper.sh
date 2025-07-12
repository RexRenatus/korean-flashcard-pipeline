#!/bin/bash
# Docker Helper Script for Korean Flashcard Pipeline
# Simplifies common Docker operations for personal use

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker compose.personal.yml"
DOCKER_FILE="Dockerfile.production"
IMAGE_NAME="korean-flashcard-pipeline:production"

# Helper functions
print_header() {
    echo -e "${BLUE}===========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    print_success "Docker is installed"
    
    if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi
    print_success "Docker Compose is installed"
    
    if [ ! -f ".env.production" ]; then
        print_info "Creating .env.production from template..."
        cp .env.production.template .env.production
        print_error "Please edit .env.production with your API key"
        exit 1
    fi
    print_success "Environment file exists"
}

# Build production image
build() {
    print_header "Building Production Image"
    docker build -f "$DOCKER_FILE" -t "$IMAGE_NAME" .
    print_success "Image built successfully"
}

# Start all services
start() {
    print_header "Starting Services"
    docker compose -f "$COMPOSE_FILE" up -d
    print_success "Services started"
    sleep 3
    status
}

# Stop all services
stop() {
    print_header "Stopping Services"
    docker compose -f "$COMPOSE_FILE" down
    print_success "Services stopped"
}

# Restart services
restart() {
    stop
    start
}

# Show service status
status() {
    print_header "Service Status"
    docker compose -f "$COMPOSE_FILE" ps
}

# View logs
logs() {
    local service="${1:-flashcard-pipeline}"
    print_header "Logs for $service"
    docker compose -f "$COMPOSE_FILE" logs -f "$service"
}

# Process vocabulary file
process() {
    local input_file="$1"
    if [ -z "$input_file" ]; then
        print_error "Usage: $0 process <input_file>"
        exit 1
    fi
    
    print_header "Processing Vocabulary File"
    docker compose -f "$COMPOSE_FILE" run --rm flashcard-pipeline \
        python -m flashcard_pipeline process "/app/data/input/$(basename "$input_file")" \
        --concurrent 20 --output "/app/data/output/$(basename "$input_file" .csv)_processed.tsv"
}

# Run tests
test() {
    print_header "Running Tests"
    docker compose -f "$COMPOSE_FILE" run --rm flashcard-pipeline \
        python -m flashcard_pipeline test all --verbose
}

# Backup database
backup() {
    print_header "Creating Backup"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    docker compose -f "$COMPOSE_FILE" run --rm flashcard-pipeline \
        python -m flashcard_pipeline db backup "/app/backup/manual_backup_$timestamp.db"
    print_success "Backup created: manual_backup_$timestamp.db"
}

# Clean up resources
cleanup() {
    print_header "Cleaning Up Resources"
    print_info "This will remove stopped containers and unused images"
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker compose -f "$COMPOSE_FILE" down -v
        docker image prune -f
        print_success "Cleanup completed"
    else
        print_info "Cleanup cancelled"
    fi
}

# Interactive shell
shell() {
    print_header "Starting Interactive Shell"
    docker compose -f "$COMPOSE_FILE" run --rm flashcard-pipeline bash
}

# Show help
show_help() {
    cat << EOF
Korean Flashcard Pipeline - Docker Helper

Usage: $0 [command] [options]

Commands:
  build       Build the production Docker image
  start       Start all services
  stop        Stop all services
  restart     Restart all services
  status      Show service status
  logs        View logs (optionally specify service)
  process     Process a vocabulary file
  test        Run all tests
  backup      Create a manual backup
  cleanup     Clean up Docker resources
  shell       Start an interactive shell
  help        Show this help message

Examples:
  $0 start                    # Start all services
  $0 process vocab.csv        # Process a vocabulary file
  $0 logs monitor            # View monitor service logs
  $0 backup                  # Create a manual backup

EOF
}

# Main script logic
case "$1" in
    build)
        check_prerequisites
        build
        ;;
    start)
        check_prerequisites
        start
        ;;
    stop)
        stop
        ;;
    restart)
        check_prerequisites
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs "$2"
        ;;
    process)
        process "$2"
        ;;
    test)
        test
        ;;
    backup)
        backup
        ;;
    cleanup)
        cleanup
        ;;
    shell)
        shell
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac