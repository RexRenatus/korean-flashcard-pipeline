# Architecture Migration Guide

## Overview
This guide helps developers migrate to the new consolidated architecture implemented in January 2025.

## Key Changes

### 1. Database Manager Consolidation
**Before**: 6 different database manager implementations
**After**: 2 clean implementations

#### Migration Steps:
```python
# Old imports (any of these):
from flashcard_pipeline.database import LegacyDatabaseManager
from flashcard_pipeline.database import EnhancedDatabaseManager
from flashcard_pipeline.database import ValidatedDatabaseManager
from flashcard_pipeline.database.db_manager import DatabaseManager
from flashcard_pipeline.database.db_manager_v2 import EnhancedDatabaseManager

# New import (synchronous):
from flashcard_pipeline.database import DatabaseManager

# New import (asynchronous):
from flashcard_pipeline.database import AsyncDatabaseManager
```

#### Feature Configuration:
```python
# Old way (separate classes):
db = EnhancedDatabaseManager(db_path)  # For pooling
db = ValidatedDatabaseManager(db_path)  # For validation

# New way (configuration options):
db = DatabaseManager(
    db_path="flashcard_pipeline.db",
    use_connection_pool=True,      # Enable pooling
    enable_monitoring=True,         # Enable monitoring
    enable_validation=True,         # Enable validation
    pool_size=5
)
```

### 2. Rate Limiter Consolidation
**Before**: Duplicate in api/ directory, separate v2 with sharding
**After**: Single implementation location

#### Migration Steps:
```python
# Old imports:
from flashcard_pipeline.api.rate_limiter import RateLimiter
from flashcard_pipeline.rate_limiter_v2 import ShardedRateLimiter

# New import:
from flashcard_pipeline.rate_limiter import RateLimiter
```

### 3. Circuit Breaker Consolidation
**Before**: Duplicate in api/, separate v2 with enhanced features
**After**: Single implementation with all features

#### Migration Steps:
```python
# Old imports:
from flashcard_pipeline.api.circuit_breaker import CircuitBreaker
from flashcard_pipeline.circuit_breaker_v2 import EnhancedCircuitBreaker

# New import:
from flashcard_pipeline.circuit_breaker import CircuitBreaker
```

#### New Features Available:
- `CircuitState.ISOLATED` - Manual circuit control
- `CircuitBreakerStats` - Enhanced monitoring
- Failure ratio thresholds (not just count)

### 4. Documentation Organization
**Before**: 30+ documentation files at root level
**After**: Organized into subdirectories

#### New Structure:
```
docs/
├── refactoring/          # Refactoring documentation
├── hooks/                # Hooks system documentation
├── deployment/           # Docker, production guides
├── testing/              # Test plans and reports
├── project-management/   # Phase plans, improvements
└── *.md                  # Core technical docs
```

### 5. Import Path Updates

#### API Package
```python
# Rate limiter and circuit breaker now imported from parent:
from flashcard_pipeline.api import OpenRouterClient  # No change
from flashcard_pipeline.api import RateLimiter      # Now from parent
from flashcard_pipeline.api import CircuitBreaker   # Now from parent
```

#### Database Package
```python
# Backward compatibility maintained:
from flashcard_pipeline.database import DatabaseManager
# Legacy names still work but point to new implementation
```

## Testing Your Migration

1. **Run Tests**: Ensure all tests pass after migration
   ```bash
   python -m pytest tests/
   ```

2. **Check Imports**: Update any failing imports
   ```bash
   # Find old imports
   grep -r "circuit_breaker_v2" src/
   grep -r "rate_limiter_v2" src/
   ```

3. **Verify Features**: Test that optional features work
   ```python
   # Test database features
   db = DatabaseManager(enable_monitoring=True)
   assert db.monitor is not None
   ```

## Rollback Plan

If issues arise:
1. The old class names are aliased for compatibility
2. Core functionality unchanged - only organization improved
3. Git history preserved for reverting specific changes

## Need Help?

- Check the consolidated implementations in:
  - `/src/python/flashcard_pipeline/database/database_manager.py`
  - `/src/python/flashcard_pipeline/circuit_breaker.py`
  - `/src/python/flashcard_pipeline/rate_limiter.py`
- Review test files for usage examples
- Check git history for specific changes