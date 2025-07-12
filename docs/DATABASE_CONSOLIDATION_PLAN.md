# Database Manager Consolidation Plan

## Overview
This document outlines the plan to consolidate 6 database manager implementations into 2 clean versions.

## Current State
1. **db_manager.py** - Basic implementation (July 8)
2. **db_manager_v2.py** - Enhanced with pooling (July 9) 
3. **validated_db_manager.py** - Adds validation (July 9)
4. **manager.py** - Unified attempt (July 11) - Currently exported as default
5. **database_manager_v2.py** - Async version (July 11)
6. **database_manager_instrumented.py** - With telemetry (July 11)

## Target State
### 1. Synchronous Database Manager (`database_manager.py`)
- Consolidate features from db_manager.py, db_manager_v2.py, validated_db_manager.py, and manager.py
- Features available via configuration:
  - Connection pooling (optional)
  - Performance monitoring (optional)
  - Data validation (optional)
  - Instrumentation/telemetry (optional)

### 2. Asynchronous Database Manager (`async_database_manager.py`)
- Based on current database_manager_v2.py
- Features:
  - All sync features but async
  - Circuit breaker integration
  - Prepared statements
  - Query caching
  
## Migration Steps
1. Create new consolidated `database_manager.py` with all sync features
2. Rename `database_manager_v2.py` to `async_database_manager.py`
3. Update imports across codebase
4. Remove old implementations
5. Update documentation

## Backward Compatibility
- Keep same class names and method signatures
- Use factory functions for feature configuration
- Provide migration guide for existing code