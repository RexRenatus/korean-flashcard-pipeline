# Developer Guide - Korean Language Flashcard Pipeline

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [API Reference](#api-reference)
5. [Database Schema](#database-schema)
6. [Testing](#testing)
7. [Contributing](#contributing)
8. [Development Setup](#development-setup)

## Architecture Overview

The Korean Language Flashcard Pipeline follows a modular, layered architecture designed for scalability and maintainability.

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Interface                         │
├─────────────────────────────────────────────────────────────┤
│                    Pipeline Orchestrator                     │
├──────────────┬──────────────┬──────────────┬───────────────┤
│   API Client │ Rate Limiter │ Cache Service│ Circuit Break │
├──────────────┴──────────────┴──────────────┴───────────────┤
│                    Database Manager                          │
├─────────────────────────────────────────────────────────────┤
│                    SQLite Database                          │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Input Processing**: Word/CSV → Validation → Queue
2. **API Integration**: Queue → Rate Limiter → API Client → OpenRouter
3. **Two-Stage Processing**: 
   - Stage 1: Flashcard Creation
   - Stage 2: Nuance Enhancement
4. **Storage**: Results → Database → Cache
5. **Export**: Database → Formatter → Output Files

## Project Structure

```
korean-flashcard-pipeline/
├── src/
│   └── python/
│       └── flashcard_pipeline/
│           ├── __init__.py
│           ├── api_client.py          # API integration
│           ├── cache.py               # Caching layer
│           ├── circuit_breaker.py     # Fault tolerance
│           ├── cli.py                 # CLI interface
│           ├── models.py              # Data models
│           ├── pipeline.py            # Core pipeline
│           ├── rate_limiter.py        # Rate limiting
│           └── database/
│               ├── __init__.py
│               ├── manager.py         # DB operations
│               └── schema.sql         # Schema definition
├── tests/
│   ├── unit/                         # Unit tests
│   ├── integration/                  # Integration tests
│   └── fixtures/                     # Test data
├── migrations/                       # Database migrations
├── prompts/                         # AI prompt templates
├── examples/                        # Example files
└── docs/                           # Documentation
```

## Core Components

### 1. API Client (`api_client.py`)

Handles communication with OpenRouter API.

```python
from flashcard_pipeline.api_client import APIClient

class APIClient:
    """OpenRouter API client with retry logic and error handling."""
    
    def __init__(self, api_key: str, base_url: str = None):
        """Initialize API client."""
        
    async def create_flashcard(self, word: str, context: dict = None) -> dict:
        """Create initial flashcard for a Korean word."""
        
    async def enhance_with_nuance(self, flashcard: dict) -> dict:
        """Enhance flashcard with cultural nuances."""
```

#### Usage Example:
```python
client = APIClient(api_key="your-key")
flashcard = await client.create_flashcard("안녕하세요")
enhanced = await client.enhance_with_nuance(flashcard)
```

### 2. Cache Service (`cache.py`)

LRU cache with TTL support for API responses.

```python
from flashcard_pipeline.cache import CacheService

class CacheService:
    """Thread-safe caching with TTL and size limits."""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """Initialize cache with size and TTL limits."""
        
    def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache if valid."""
        
    def set(self, key: str, value: Any) -> None:
        """Store value in cache with TTL."""
```

### 3. Rate Limiter (`rate_limiter.py`)

Token bucket algorithm for API rate limiting.

```python
from flashcard_pipeline.rate_limiter import RateLimiter

class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, rate: int, burst: int):
        """Initialize with rate (per second) and burst capacity."""
        
    async def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens, blocking if necessary."""
```

### 4. Circuit Breaker (`circuit_breaker.py`)

Fault tolerance for API failures.

```python
from flashcard_pipeline.circuit_breaker import CircuitBreaker

class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        """Initialize with failure threshold and recovery timeout."""
        
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
```

### 5. Database Manager (`database/manager.py`)

SQLite database operations with connection pooling.

```python
from flashcard_pipeline.database import DatabaseManager

class DatabaseManager:
    """Database operations with connection pooling."""
    
    def __init__(self, db_path: str, pool_size: int = 5):
        """Initialize database with connection pool."""
        
    async def save_flashcard(self, flashcard: Flashcard) -> int:
        """Save flashcard to database."""
        
    async def get_flashcard(self, word: str) -> Optional[Flashcard]:
        """Retrieve flashcard by word."""
```

### 6. Pipeline Orchestrator (`pipeline.py`)

Main pipeline coordinating all components.

```python
from flashcard_pipeline import Pipeline

class Pipeline:
    """Main pipeline orchestrator."""
    
    def __init__(self, config: dict):
        """Initialize pipeline with configuration."""
        
    async def process_word(self, word: str, options: dict = None) -> Flashcard:
        """Process single word through pipeline."""
        
    async def process_batch(self, words: List[str], options: dict = None) -> List[Flashcard]:
        """Process batch of words concurrently."""
```

## API Reference

### Public API

#### Pipeline Class

```python
# Initialize pipeline
pipeline = Pipeline(config={
    "api_key": "your-key",
    "cache_enabled": True,
    "rate_limit": 60,
    "database_path": "./pipeline.db"
})

# Process single word
flashcard = await pipeline.process_word("안녕하세요")

# Process batch
flashcards = await pipeline.process_batch(["안녕", "감사", "사랑"])

# Process with options
flashcard = await pipeline.process_word(
    "김치",
    options={
        "skip_cache": True,
        "include_etymology": True,
        "difficulty_level": "intermediate"
    }
)
```

#### Models

```python
from flashcard_pipeline.models import Flashcard, WordMetadata

# Flashcard model
flashcard = Flashcard(
    word="안녕하세요",
    romanization="annyeonghaseyo",
    definition="Hello (formal)",
    examples=[
        {"korean": "안녕하세요, 만나서 반갑습니다.", 
         "english": "Hello, nice to meet you."}
    ],
    cultural_notes=["Used in formal situations", "Morning greeting"],
    difficulty="beginner"
)

# Metadata model
metadata = WordMetadata(
    category="greeting",
    tags=["formal", "common"],
    frequency_rank=10,
    hanja="安寧"
)
```

#### Export Functions

```python
from flashcard_pipeline.exporters import export_anki, export_csv, export_json

# Export to Anki
deck = export_anki(
    flashcards,
    deck_name="Korean Vocabulary",
    note_type="Korean Advanced"
)

# Export to CSV
csv_data = export_csv(
    flashcards,
    columns=["word", "definition", "romanization", "examples"]
)

# Export to JSON
json_data = export_json(
    flashcards,
    pretty=True,
    include_metadata=True
)
```

### Error Handling

```python
from flashcard_pipeline.exceptions import (
    APIError,
    RateLimitError,
    ValidationError,
    DatabaseError
)

try:
    flashcard = await pipeline.process_word("안녕")
except RateLimitError as e:
    print(f"Rate limit hit: {e.retry_after} seconds")
except APIError as e:
    print(f"API error: {e.status_code} - {e.message}")
except ValidationError as e:
    print(f"Invalid input: {e.field} - {e.message}")
except DatabaseError as e:
    print(f"Database error: {e.operation} - {e.message}")
```

## Database Schema

### Tables

#### flashcards
```sql
CREATE TABLE flashcards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL UNIQUE,
    romanization TEXT,
    definition TEXT NOT NULL,
    part_of_speech TEXT,
    difficulty TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### examples
```sql
CREATE TABLE examples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flashcard_id INTEGER NOT NULL,
    korean_text TEXT NOT NULL,
    english_text TEXT NOT NULL,
    romanization TEXT,
    example_type TEXT,
    FOREIGN KEY (flashcard_id) REFERENCES flashcards(id)
);
```

#### cultural_notes
```sql
CREATE TABLE cultural_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flashcard_id INTEGER NOT NULL,
    note TEXT NOT NULL,
    category TEXT,
    FOREIGN KEY (flashcard_id) REFERENCES flashcards(id)
);
```

#### cache_entries
```sql
CREATE TABLE cache_entries (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);
```

### Indexes
```sql
CREATE INDEX idx_flashcards_word ON flashcards(word);
CREATE INDEX idx_flashcards_difficulty ON flashcards(difficulty);
CREATE INDEX idx_examples_flashcard ON examples(flashcard_id);
CREATE INDEX idx_cultural_notes_flashcard ON cultural_notes(flashcard_id);
CREATE INDEX idx_cache_expires ON cache_entries(expires_at);
```

## Testing

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# With coverage
pytest --cov=flashcard_pipeline --cov-report=html

# Specific test file
pytest tests/unit/test_api_client.py

# Verbose output
pytest -v

# Parallel execution
pytest -n 4
```

### Writing Tests

#### Unit Test Example
```python
# tests/unit/test_cache.py
import pytest
from flashcard_pipeline.cache import CacheService

class TestCacheService:
    @pytest.fixture
    def cache(self):
        return CacheService(max_size=10, ttl=60)
    
    def test_set_and_get(self, cache):
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
    
    def test_expiration(self, cache, freezer):
        cache.set("key1", "value1")
        freezer.move_to("+61 seconds")
        assert cache.get("key1") is None
```

#### Integration Test Example
```python
# tests/integration/test_pipeline.py
import pytest
from flashcard_pipeline import Pipeline

@pytest.mark.integration
class TestPipeline:
    @pytest.fixture
    async def pipeline(self):
        return Pipeline(config={
            "api_key": "test-key",
            "database_path": ":memory:"
        })
    
    @pytest.mark.asyncio
    async def test_process_word(self, pipeline, mock_api):
        mock_api.return_value = {"definition": "Hello"}
        result = await pipeline.process_word("안녕")
        assert result.word == "안녕"
        assert result.definition == "Hello"
```

### Test Fixtures

```python
# tests/conftest.py
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_api_client():
    """Mock API client for testing."""
    client = Mock()
    client.create_flashcard.return_value = {
        "word": "test",
        "definition": "test definition"
    }
    return client

@pytest.fixture
def sample_flashcard():
    """Sample flashcard for testing."""
    return {
        "word": "안녕",
        "romanization": "annyeong",
        "definition": "Hello (informal)",
        "examples": [
            {"korean": "안녕!", "english": "Hi!"}
        ]
    }
```

## Contributing

### Development Setup

1. **Fork and Clone**
   ```bash
   git fork https://github.com/original/korean-flashcard-pipeline
   git clone https://github.com/yourusername/korean-flashcard-pipeline
   cd korean-flashcard-pipeline
   ```

2. **Create Development Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements-dev.txt
   ```

3. **Install Pre-commit Hooks**
   ```bash
   pre-commit install
   ```

### Code Style

- Follow PEP 8
- Use type hints
- Maximum line length: 88 (Black default)
- Docstrings for all public functions

### Making Changes

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Write code
   - Add tests
   - Update documentation

3. **Run Tests**
   ```bash
   pytest
   black .
   flake8
   mypy .
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Format

Follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `style:` Code style
- `refactor:` Refactoring
- `test:` Tests
- `chore:` Maintenance

### Pull Request Guidelines

1. **Title**: Clear, descriptive title
2. **Description**: What, why, and how
3. **Tests**: All tests must pass
4. **Documentation**: Update if needed
5. **Review**: Address feedback promptly

### Code Review Checklist

- [ ] Tests pass
- [ ] Code follows style guide
- [ ] Documentation updated
- [ ] No hardcoded values
- [ ] Error handling implemented
- [ ] Performance considered
- [ ] Security reviewed

## Advanced Topics

### Performance Optimization

1. **Database Optimization**
   ```python
   # Use connection pooling
   db = DatabaseManager(pool_size=10)
   
   # Batch operations
   await db.save_flashcards_batch(flashcards)
   
   # Prepared statements
   await db.execute_prepared(query, params)
   ```

2. **Concurrent Processing**
   ```python
   # Process words concurrently
   async with asyncio.TaskGroup() as tg:
       tasks = [tg.create_task(process_word(w)) for w in words]
   results = [t.result() for t in tasks]
   ```

3. **Memory Management**
   ```python
   # Stream large files
   async for chunk in read_csv_chunks("large.csv", chunk_size=1000):
       await process_chunk(chunk)
   ```

### Extending the Pipeline

1. **Custom Processors**
   ```python
   from flashcard_pipeline.processors import BaseProcessor
   
   class HanjaProcessor(BaseProcessor):
       async def process(self, flashcard: dict) -> dict:
           flashcard["hanja"] = await self.get_hanja(flashcard["word"])
           return flashcard
   ```

2. **Custom Exporters**
   ```python
   from flashcard_pipeline.exporters import BaseExporter
   
   class MemriseExporter(BaseExporter):
       def export(self, flashcards: List[Flashcard]) -> str:
           # Custom export logic
           pass
   ```

### Debugging

1. **Enable Debug Logging**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **API Request Debugging**
   ```python
   # Enable request/response logging
   client = APIClient(api_key="key", debug=True)
   ```

3. **Database Query Logging**
   ```python
   # Log all SQL queries
   db = DatabaseManager(db_path="pipeline.db", log_queries=True)
   ```

## Resources

- [Project Repository](https://github.com/yourusername/korean-flashcard-pipeline)
- [API Documentation](API_REFERENCE.md)
- [User Guide](USER_GUIDE.md)
- [OpenRouter API Docs](https://openrouter.ai/docs)
- [SQLite Documentation](https://www.sqlite.org/docs.html)