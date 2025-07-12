#!/bin/bash
#
# Run database migrations in Docker container
#

set -e  # Exit on error

echo "=========================================="
echo "Running Database Migrations"
echo "=========================================="

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose not found. Please install Docker Compose."
    exit 1
fi

# Build the image if needed
echo "Building Docker image..."
docker-compose build

# Run migrations
echo "Running database migrations..."
docker-compose run --rm \
    -e DOCKER_CONTAINER=1 \
    flashcard-pipeline \
    python /app/scripts/run_migrations.py

echo ""
echo "✅ Migrations completed successfully!"
echo ""

# Optional: Show database status
read -p "Would you like to see the database status? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose run --rm flashcard-pipeline \
        sqlite3 /app/data/flashcards.db \
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
fi