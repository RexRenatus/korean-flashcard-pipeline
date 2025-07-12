#!/bin/bash
#
# Process vocabulary files using Docker container
#

set -e  # Exit on error

echo "=========================================="
echo "Flashcard Pipeline - Vocabulary Processor"
echo "=========================================="

# Default values
INPUT_FILE="${1:-docs/10K_HSK_List.csv}"
OUTPUT_DIR="data/output"
CACHE_DIR="data/cache"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose not found. Please install Docker Compose."
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found. Please create it with your OPENROUTER_API_KEY"
    echo "Example:"
    echo "  echo 'OPENROUTER_API_KEY=your-key-here' > .env"
    exit 1
fi

# Create necessary directories
echo "Creating data directories..."
mkdir -p "$OUTPUT_DIR" "$CACHE_DIR"

# Build the image if needed
echo "Building Docker image..."
docker-compose build

# Check if we need to run migrations first
if [ ! -f "data/flashcards.db" ]; then
    echo ""
    echo "Database not found. Running migrations first..."
    ./docker-migrate.sh
fi

echo ""
echo "Processing vocabulary file: $INPUT_FILE"
echo "Output will be saved to: $OUTPUT_DIR"
echo ""

# Run the vocabulary processor
if [ "$1" == "" ]; then
    # No arguments - process first 100 from default file
    echo "Processing first 100 words from default vocabulary list..."
    docker-compose run --rm \
        -e DOCKER_CONTAINER=1 \
        flashcard-pipeline \
        python /app/process_vocab_docker.py
else
    # Custom file provided
    echo "Processing vocabulary from: $1"
    docker-compose run --rm \
        -e DOCKER_CONTAINER=1 \
        -v "$(pwd)/$1:/app/input_vocab.csv" \
        flashcard-pipeline \
        python -c "
import sys
sys.path.insert(0, '/app')
# Modify the process_vocab_docker.py to use custom input
import process_vocab_docker
process_vocab_docker.vocab_file = '/app/input_vocab.csv'
process_vocab_docker.main()
"
fi

echo ""
echo "✅ Processing completed!"
echo ""

# Show output files
echo "Output files:"
ls -la "$OUTPUT_DIR"/*.tsv 2>/dev/null || echo "  No output files found"

# Optional: Preview the results
if [ -f "$OUTPUT_DIR/hsk_100_processed.tsv" ]; then
    echo ""
    read -p "Would you like to preview the first 5 processed flashcards? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "First 5 flashcards:"
        head -n 6 "$OUTPUT_DIR/hsk_100_processed.tsv" | column -t -s $'\t'
    fi
fi