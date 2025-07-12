# Database Module

Comprehensive database management for the flashcard pipeline system.

## Overview

This module handles all database operations including connection management, query execution, migrations, validation, and performance monitoring. It provides both synchronous and asynchronous interfaces for SQLite operations.

## Components

### Core Files
- **`__init__.py`** - Module initialization and exports
- **`manager.py`** - Main database manager class
- **`connection_pool.py`** - Connection pooling for concurrent access
- **`models.py`** - SQLAlchemy-style model definitions
- **`validation.py`** - Data validation rules and constraints

### Advanced Features
- **`migrations.py`** - Database schema migration system
- **`performance_monitoring.py`** - Query performance tracking
- **`enhanced_manager.py`** - Extended features with validation
- **`query_builder.py`** - Dynamic query construction

## Database Schema

The system uses SQLite with the following main tables:
- `vocabulary_master` - Core vocabulary items
- `flashcards` - Generated flashcard content
- `stage_outputs` - Processing stage results
- `import_operations` - Import tracking
- `processing_cache` - API response cache

See `/DATABASE_SCHEMA.md` for complete schema documentation.

## Usage Examples

```python
# Basic usage
from flashcard_pipeline.database import DatabaseManager

db = DatabaseManager("pipeline.db")
vocab_id = await db.create_vocabulary({
    "korean": "안녕하세요",
    "english": "Hello",
    "type": "phrase"
})

# With validation
from flashcard_pipeline.database import ValidatedDatabaseManager

db = ValidatedDatabaseManager("pipeline.db")
# Automatically validates data before insertion

# Connection pool
from flashcard_pipeline.database import ConnectionPool

pool = ConnectionPool("pipeline.db", max_connections=10)
async with pool.acquire() as conn:
    await conn.execute("SELECT * FROM vocabulary_master")
```

## Key Features

### 1. Connection Management
- Connection pooling for concurrent access
- Automatic connection recycling
- Transaction support with rollback
- Context managers for safety

### 2. Data Validation
- Pydantic model validation
- Business rule enforcement
- Data sanitization
- Constraint checking

### 3. Migration System
- Version-controlled schema changes
- Automatic migration execution
- Rollback support
- Migration history tracking

### 4. Performance Monitoring
- Query execution time tracking
- Slow query logging
- Index usage analysis
- Connection pool metrics

## Best Practices

1. **Always use transactions for multi-statement operations**
   ```python
   async with db.transaction() as tx:
       await tx.execute(query1)
       await tx.execute(query2)
       # Automatically commits or rolls back
   ```

2. **Use parameterized queries to prevent SQL injection**
   ```python
   await db.execute(
       "SELECT * FROM vocabulary WHERE korean = ?",
       (search_term,)
   )
   ```

3. **Index frequently queried columns**
   - Korean terms for lookups
   - Import IDs for batch operations
   - Created dates for time-based queries

4. **Monitor connection pool usage**
   ```python
   stats = pool.get_stats()
   if stats['waiting'] > 0:
       # Consider increasing pool size
   ```

## Configuration

Environment variables:
- `DATABASE_URL` - SQLite file path
- `DB_POOL_SIZE` - Max connections (default: 10)
- `DB_TIMEOUT` - Query timeout in seconds (default: 30)
- `DB_ECHO` - Log all SQL queries (default: false)

## Error Handling

Common exceptions:
- `DatabaseError` - General database errors
- `ValidationError` - Data validation failures
- `IntegrityError` - Constraint violations
- `TimeoutError` - Query timeout
- `PoolExhaustedError` - No available connections

## Performance Tips

1. Use bulk inserts for large datasets
2. Create appropriate indexes
3. Vacuum database periodically
4. Monitor slow queries
5. Use connection pooling
6. Batch related queries in transactions