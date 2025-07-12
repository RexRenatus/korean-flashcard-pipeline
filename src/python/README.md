# Python Source Code

This directory contains the Python implementation of the Korean Language Flashcard Pipeline.

## Structure

```
python/
├── flashcard_pipeline/      # Main package
│   ├── __init__.py         # Package initialization
│   ├── api_client.py       # OpenRouter API client
│   ├── models.py           # Data models and validation
│   ├── pipeline.py         # Pipeline orchestration
│   ├── cache.py            # Caching implementation
│   ├── rate_limiter.py     # Rate limiting
│   ├── circuit_breaker.py  # Circuit breaker pattern
│   ├── exceptions.py       # Custom exceptions
│   ├── cli/                # Command-line interface
│   ├── concurrent/         # Concurrent processing
│   ├── database/           # Database management
│   ├── exporters/          # Export functionality
│   ├── intelligent_assistant/  # AI assistant features
│   └── monitoring/         # Health monitoring
├── tests/                  # Unit tests (legacy location)
└── venv/                   # Virtual environment (git-ignored)
```

## Key Components

### Core Modules
- **api_client.py**: Handles all OpenRouter API communications
- **models.py**: Pydantic models for data validation
- **pipeline.py**: Orchestrates the two-stage processing pipeline
- **cache.py**: LRU cache with compression and persistence

### Subsystems
- **database/**: Database connection management, migrations, validation
- **concurrent/**: Distributed processing, rate limiting, worker pools
- **cli/**: Command-line interface and user interactions
- **monitoring/**: Health checks, metrics, performance monitoring

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .
```

## Usage

```python
# Import the package
from flashcard_pipeline import OpenRouterClient, Pipeline

# Or use the CLI
python -m flashcard_pipeline.cli --help
```

## Development Guidelines

1. **Code Style**:
   - Follow PEP 8
   - Use type hints for all functions
   - Add docstrings to all public methods

2. **Testing**:
   - Write tests for new features
   - Maintain >85% code coverage
   - Run tests before committing

3. **Error Handling**:
   - Use custom exceptions from exceptions.py
   - Always provide meaningful error messages
   - Log errors appropriately

4. **Performance**:
   - Use async/await for I/O operations
   - Implement caching where appropriate
   - Profile before optimizing

## Current Status

- ✅ Phase 2: Core API client implementation
- ✅ Phase 3: Database and models
- ✅ Phase 4: Pipeline orchestration
- 🚧 Phase 5: Testing and validation

## Dependencies

Key dependencies:
- `httpx`: Async HTTP client
- `pydantic`: Data validation
- `aiosqlite`: Async SQLite
- `click`: CLI framework
- `rich`: Terminal formatting

See `requirements.txt` for complete list.