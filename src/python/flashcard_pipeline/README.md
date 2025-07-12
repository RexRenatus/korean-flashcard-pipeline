# Flashcard Pipeline Package

Main Python package for the Korean Language Flashcard Pipeline system.

## Overview

This package implements the complete pipeline for generating Korean language flashcards using AI, including:
- API client for OpenRouter/Claude
- Two-stage processing pipeline
- Database management
- Import/export functionality
- Monitoring and health checks

## Module Organization

### Core Modules
- **`__init__.py`** - Package initialization and exports
- **`api_client.py`** - OpenRouter API client with retry logic
- **`models.py`** - Pydantic models for data validation
- **`pipeline.py`** - Main pipeline orchestration
- **`exceptions.py`** - Custom exception hierarchy

### Infrastructure Modules
- **`cache.py`** - LRU cache with compression
- **`rate_limiter.py`** - Token bucket rate limiting
- **`circuit_breaker.py`** - Circuit breaker for fault tolerance
- **`utils.py`** - Utility functions and helpers

### Feature Modules
- **`cli/`** - Command-line interface
- **`concurrent/`** - Concurrent processing utilities
- **`database/`** - Database operations and management
- **`exporters/`** - Export to various formats
- **`intelligent_assistant/`** - AI-powered assistance
- **`monitoring/`** - Health checks and metrics

## Usage Examples

```python
# Basic API usage
from flashcard_pipeline import OpenRouterClient

client = OpenRouterClient(api_key="your-key")
response = await client.generate_flashcard(vocab_item)

# Pipeline usage
from flashcard_pipeline import Pipeline

pipeline = Pipeline(config)
results = await pipeline.process_vocabulary(items)

# CLI usage
python -m flashcard_pipeline.cli process input.csv
```

## Key Features

1. **Resilient API Client**
   - Automatic retries with exponential backoff
   - Circuit breaker for fault tolerance
   - Rate limiting to respect API limits

2. **Efficient Processing**
   - Concurrent processing with worker pools
   - Intelligent caching to reduce API calls
   - Batch processing for large datasets

3. **Data Management**
   - SQLite database with migrations
   - Data validation and sanitization
   - Import/export in multiple formats

4. **Monitoring**
   - Health check endpoints
   - Performance metrics
   - Detailed logging

## Configuration

The package uses environment variables for configuration:
- `OPENROUTER_API_KEY` - API key for OpenRouter
- `DATABASE_URL` - Database connection string
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `CACHE_SIZE` - Maximum cache entries
- `RATE_LIMIT` - API calls per minute

## Development

### Adding New Features
1. Create module in appropriate subdirectory
2. Add to `__init__.py` if it's a public API
3. Write comprehensive tests
4. Update documentation

### Code Style
- Follow PEP 8
- Use type hints
- Write descriptive docstrings
- Handle errors gracefully

## Dependencies

Core dependencies:
- `httpx` - Async HTTP client
- `pydantic` - Data validation
- `aiosqlite` - Async SQLite
- `rich` - Terminal UI
- `click` - CLI framework