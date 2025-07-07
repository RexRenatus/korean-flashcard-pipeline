#!/usr/bin/env python3
"""
Test Environment Setup Script
Sets up test environment variables and configurations for running tests without real API keys.
"""

import os
import sys
from pathlib import Path
import shutil
import sqlite3
import json

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.absolute()


def create_test_env_file():
    """Create a .env.test file with mock values for testing."""
    test_env_content = """# Test Environment Configuration
# This file is used for running tests without real API credentials

# Mock OpenRouter API Configuration
OPENROUTER_API_KEY=test-api-key-12345
OPENROUTER_BASE_URL=http://localhost:8000/mock-api

# OpenRouter Preset Configuration (test values)
NUANCE_PRESET=@test/nuance-creator
FLASHCARD_PRESET=@test/flashcard-generator

# Test Database Configuration
DATABASE_PATH=./test_pipeline.db
CACHE_ENABLED=true
CACHE_TTL_STAGE1=3600  # 1 hour for tests
CACHE_TTL_STAGE2=1800  # 30 minutes for tests

# Test Processing Configuration
MAX_BATCH_SIZE=10
MAX_RETRIES=2
RETRY_DELAY=100  # milliseconds

# Test Rate Limiting
REQUESTS_PER_MINUTE=100
REQUESTS_PER_HOUR=1000

# Test Logging
LOG_LEVEL=debug
LOG_FILE=./logs/test_pipeline.log

# Test Input/Output Configuration
SOURCE_CSV_FILE=tests/data/test_vocabulary.csv
OUTPUT_FOLDER=tests/data/output

# Test Performance Settings
NUMBER_OF_PRODUCER_THREADS=2
API_RATE_LIMIT=10
DB_POOL_SIZE=5
DB_BUSY_TIMEOUT_MS=5000
TSV_BATCH_SIZE=10

# Test Advanced Settings
CONNECTION_POOL_MAXSIZE=5
BATCH_FETCH_SIZE=20
MIN_WORKERS=1
MAX_WORKERS=2
ENABLE_ADAPTIVE_CONCURRENCY=false
ENABLE_CONNECTION_POOLING=true
ENABLE_REQUEST_PIPELINING=false
ENABLE_RESPONSE_COMPRESSION=false

# Test Pipeline Settings
USE_RICH_PROGRESS=false
HTTP2_ENABLED=false
ENABLE_RATE_LIMITING=false

# Test Mode Flag
TEST_MODE=true
MOCK_API_RESPONSES=true
"""
    
    test_env_path = PROJECT_ROOT / ".env.test"
    with open(test_env_path, "w") as f:
        f.write(test_env_content)
    print(f"✅ Created test environment file: {test_env_path}")


def create_test_data_directories():
    """Create necessary test data directories."""
    test_dirs = [
        PROJECT_ROOT / "tests" / "data",
        PROJECT_ROOT / "tests" / "data" / "input",
        PROJECT_ROOT / "tests" / "data" / "output",
        PROJECT_ROOT / "logs",
    ]
    
    for test_dir in test_dirs:
        test_dir.mkdir(parents=True, exist_ok=True)
    
    print("✅ Created test data directories")


def create_test_vocabulary_csv():
    """Create a sample test vocabulary CSV file."""
    test_vocab_path = PROJECT_ROOT / "tests" / "data" / "test_vocabulary.csv"
    
    test_data = """position,term,type
1,안녕하세요,greeting
2,감사합니다,expression
3,학생,noun
4,공부하다,verb
5,책,noun
"""
    
    with open(test_vocab_path, "w", encoding="utf-8") as f:
        f.write(test_data)
    
    print(f"✅ Created test vocabulary file: {test_vocab_path}")


def create_test_database():
    """Create a test SQLite database with schema."""
    test_db_path = PROJECT_ROOT / "test_pipeline.db"
    
    # Remove existing test database if it exists
    if test_db_path.exists():
        test_db_path.unlink()
    
    # Create database and tables
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    
    # Create schema based on DATABASE_SCHEMA.md
    schema_sql = """
    -- Vocabulary Items Table
    CREATE TABLE IF NOT EXISTS vocabulary_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        position INTEGER NOT NULL,
        term TEXT NOT NULL,
        type TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(position, term)
    );

    -- Stage 1 Results Table
    CREATE TABLE IF NOT EXISTS stage1_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vocabulary_item_id INTEGER NOT NULL,
        term_number INTEGER NOT NULL,
        term TEXT NOT NULL,
        ipa TEXT,
        pos TEXT,
        primary_meaning TEXT,
        other_meanings TEXT,
        metaphor TEXT,
        metaphor_noun TEXT,
        metaphor_action TEXT,
        suggested_location TEXT,
        anchor_object TEXT,
        anchor_sensory TEXT,
        explanation TEXT,
        usage_context TEXT,
        comparison_similar_to TEXT,
        comparison_different_from TEXT,
        comparison_commonly_confused_with TEXT,
        homonyms TEXT,
        korean_keywords TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (vocabulary_item_id) REFERENCES vocabulary_items(id)
    );

    -- Stage 2 Results Table
    CREATE TABLE IF NOT EXISTS stage2_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vocabulary_item_id INTEGER NOT NULL,
        stage1_result_id INTEGER NOT NULL,
        flashcard_row TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (vocabulary_item_id) REFERENCES vocabulary_items(id),
        FOREIGN KEY (stage1_result_id) REFERENCES stage1_results(id)
    );

    -- Cache Table
    CREATE TABLE IF NOT EXISTS cache_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cache_key TEXT UNIQUE NOT NULL,
        cache_value TEXT NOT NULL,
        stage INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL
    );

    -- API Usage Table
    CREATE TABLE IF NOT EXISTS api_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stage INTEGER NOT NULL,
        prompt_tokens INTEGER NOT NULL,
        completion_tokens INTEGER NOT NULL,
        total_tokens INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Create Indexes
    CREATE INDEX IF NOT EXISTS idx_vocabulary_items_position ON vocabulary_items(position);
    CREATE INDEX IF NOT EXISTS idx_vocabulary_items_term ON vocabulary_items(term);
    CREATE INDEX IF NOT EXISTS idx_stage1_vocabulary_id ON stage1_results(vocabulary_item_id);
    CREATE INDEX IF NOT EXISTS idx_stage2_vocabulary_id ON stage2_results(vocabulary_item_id);
    CREATE INDEX IF NOT EXISTS idx_stage2_stage1_id ON stage2_results(stage1_result_id);
    CREATE INDEX IF NOT EXISTS idx_cache_key ON cache_entries(cache_key);
    CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache_entries(expires_at);
    """
    
    cursor.executescript(schema_sql)
    conn.commit()
    conn.close()
    
    print(f"✅ Created test database: {test_db_path}")


def create_mock_responses_file():
    """Create a file with mock API responses for testing."""
    mock_responses = {
        "stage1_responses": [
            {
                "term": "안녕하세요",
                "response": {
                    "term_number": 1,
                    "term": "안녕하세요",
                    "ipa": "[annjʌŋhasejo]",
                    "pos": "greeting",
                    "primary_meaning": "hello",
                    "other_meanings": "good day, greetings",
                    "metaphor": "like opening a door to conversation",
                    "metaphor_noun": "door",
                    "metaphor_action": "opening",
                    "suggested_location": "entrance",
                    "anchor_object": "door handle",
                    "anchor_sensory": "smooth metal",
                    "explanation": "formal greeting used when meeting someone",
                    "usage_context": "formal situations",
                    "comparison": {
                        "similar_to": ["안녕"],
                        "different_from": ["잘가"],
                        "commonly_confused_with": []
                    },
                    "homonyms": [],
                    "korean_keywords": ["인사", "만남"]
                }
            }
        ],
        "stage2_responses": [
            {
                "term": "안녕하세요",
                "response": "1\t안녕하세요\t[annjʌŋhasejo]\tgreeting\tHello\tFormal greeting\t안녕하세요, 만나서 반갑습니다.\tannyeonghaseyo\tannyeonghaseyo, mannaseo bangapseumnida.\tHello, nice to meet you.\tOpening a door\tbeginner\tvery common\tformal,polite\tEssential greeting"
            }
        ]
    }
    
    mock_file_path = PROJECT_ROOT / "tests" / "data" / "mock_api_responses.json"
    with open(mock_file_path, "w", encoding="utf-8") as f:
        json.dump(mock_responses, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Created mock responses file: {mock_file_path}")


def create_pytest_ini():
    """Create pytest.ini configuration file if it doesn't exist."""
    pytest_ini_path = PROJECT_ROOT / "pytest.ini"
    
    if not pytest_ini_path.exists():
        pytest_ini_content = """[pytest]
minversion = 7.0
addopts = -ra -q --strict-markers --cov=flashcard_pipeline --cov=src/rust --cov-report=term-missing --cov-report=html
testpaths = tests
pythonpath = src/python
env_files = .env.test
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    asyncio: marks tests as async
"""
        
        with open(pytest_ini_path, "w") as f:
            f.write(pytest_ini_content)
        
        print(f"✅ Created pytest configuration: {pytest_ini_path}")
    else:
        print(f"ℹ️  pytest.ini already exists at: {pytest_ini_path}")


def create_test_runner_script():
    """Create a test runner shell script."""
    test_runner_path = PROJECT_ROOT / "run_tests.sh"
    
    test_runner_content = """#!/bin/bash
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
"""
    
    with open(test_runner_path, "w") as f:
        f.write(test_runner_content)
    
    # Make script executable
    os.chmod(test_runner_path, 0o755)
    
    print(f"✅ Created test runner script: {test_runner_path}")


def create_makefile():
    """Create a Makefile for common development tasks."""
    makefile_path = PROJECT_ROOT / "Makefile"
    
    makefile_content = """# Makefile for Korean Flashcard Pipeline

.PHONY: help test test-python test-rust test-integration clean setup lint format install

help:
	@echo "Available commands:"
	@echo "  make install        - Install all dependencies"
	@echo "  make setup          - Set up test environment"
	@echo "  make test           - Run all tests"
	@echo "  make test-python    - Run Python tests only"
	@echo "  make test-rust      - Run Rust tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make lint           - Run linters"
	@echo "  make format         - Format code"
	@echo "  make clean          - Clean up generated files"

install:
	pip install -r requirements.txt
	cargo build --all

setup:
	python scripts/setup_test_env.py

test: setup
	@echo "Running all tests with test environment..."
	@export $$(cat .env.test | grep -v '^#' | xargs) && \\
		python -m pytest tests/python -v && \\
		cargo test --all && \\
		python -m pytest tests/integration -v -m integration

test-python: setup
	@echo "Running Python tests..."
	@export $$(cat .env.test | grep -v '^#' | xargs) && \\
		python -m pytest tests/python -v --cov=flashcard_pipeline --cov-report=term-missing

test-rust:
	@echo "Running Rust tests..."
	cargo test --all

test-integration: setup
	@echo "Running integration tests..."
	@export $$(cat .env.test | grep -v '^#' | xargs) && \\
		python -m pytest tests/integration -v -m integration

lint:
	@echo "Running Python linters..."
	ruff check src/python tests/python
	mypy src/python
	@echo "Running Rust linters..."
	cargo clippy --all -- -D warnings

format:
	@echo "Formatting Python code..."
	black src/python tests/python
	ruff check --fix src/python tests/python
	@echo "Formatting Rust code..."
	cargo fmt --all

clean:
	@echo "Cleaning up..."
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	rm -rf tests/data/output/*
	rm -f test_pipeline.db
	rm -f logs/test_pipeline.log
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	cargo clean
"""
    
    with open(makefile_path, "w") as f:
        f.write(makefile_content)
    
    print(f"✅ Created Makefile: {makefile_path}")


def main():
    """Main function to set up the test environment."""
    print("🚀 Setting up test environment for Korean Flashcard Pipeline")
    print("=" * 60)
    
    # Create all necessary files and directories
    create_test_env_file()
    create_test_data_directories()
    create_test_vocabulary_csv()
    create_test_database()
    create_mock_responses_file()
    create_pytest_ini()
    create_test_runner_script()
    create_makefile()
    
    print("\n" + "=" * 60)
    print("✅ Test environment setup complete!")
    print("\n📝 Quick Start:")
    print("  1. Run all tests:           make test")
    print("  2. Run Python tests only:   make test-python")
    print("  3. Run Rust tests only:     make test-rust")
    print("  4. Run integration tests:   make test-integration")
    print("\n💡 Or use the test runner script: ./run_tests.sh")
    print("\n🔍 Test environment variables are in: .env.test")
    print("📊 Mock API responses are in: tests/data/mock_api_responses.json")


if __name__ == "__main__":
    main()