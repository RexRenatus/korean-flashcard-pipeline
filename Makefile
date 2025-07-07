# Makefile for Korean Flashcard Pipeline

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
	@export $$(cat .env.test | grep -v '^#' | xargs) && \
		python -m pytest tests/python -v && \
		cargo test --all && \
		python -m pytest tests/integration -v -m integration

test-python: setup
	@echo "Running Python tests..."
	@export $$(cat .env.test | grep -v '^#' | xargs) && \
		python -m pytest tests/python -v --cov=flashcard_pipeline --cov-report=term-missing

test-rust:
	@echo "Running Rust tests..."
	cargo test --all

test-integration: setup
	@echo "Running integration tests..."
	@export $$(cat .env.test | grep -v '^#' | xargs) && \
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
