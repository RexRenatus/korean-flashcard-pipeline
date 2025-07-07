#!/bin/bash
# Test Runner Script for Korean Flashcard Pipeline

set -e  # Exit on error

echo "🧪 Korean Flashcard Pipeline Test Runner"
echo "======================================="

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -q -r requirements.txt

# Run the test environment setup
echo "🔧 Setting up test environment..."
python scripts/setup_test_env.py

# Export test environment variables
echo "🌍 Loading test environment variables..."
export $(cat .env.test | grep -v '^#' | xargs)

# Run Python tests
echo ""
echo "🐍 Running Python tests..."
echo "------------------------"
python -m pytest tests/python -v --tb=short

# Run Rust tests
echo ""
echo "🦀 Running Rust tests..."
echo "----------------------"
cargo test --all

# Run integration tests
echo ""
echo "🔗 Running integration tests..."
echo "-----------------------------"
python -m pytest tests/integration -v --tb=short -m integration

# Generate coverage report
echo ""
echo "📊 Generating coverage report..."
echo "------------------------------"
python -m pytest tests/python --cov=flashcard_pipeline --cov-report=html --cov-report=term

echo ""
echo "✅ All tests completed!"
echo ""
echo "📈 Coverage report available at: htmlcov/index.html"
