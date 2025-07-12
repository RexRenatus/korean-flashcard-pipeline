# Database Reorganization Plan

## Overview

This document outlines a comprehensive reorganization of the Korean Flashcard Pipeline database to address normalization issues, improve performance, and ensure data integrity.

## Design Principles

1. **Single Source of Truth**: Each piece of data stored in exactly one place
2. **Referential Integrity**: Proper foreign key constraints with cascading actions
3. **Performance Optimization**: Strategic indexing and denormalization where needed
4. **Scalability**: Design for growth with partitioning and archival strategies
5. **Clear Separation**: Distinct boundaries between operational and analytical data

## New Database Schema

### Core Domain Tables

#### 1. vocabulary_master
Primary vocabulary storage with full metadata
```sql
CREATE TABLE vocabulary_master (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    korean TEXT NOT NULL,
    english TEXT,
    romanization TEXT,
    hanja TEXT,
    type TEXT NOT NULL CHECK (type IN ('word', 'phrase', 'idiom', 'grammar', 'sentence')),
    category TEXT,
    subcategory TEXT,
    difficulty_level INTEGER CHECK (difficulty_level BETWEEN 1 AND 10),
    frequency_rank INTEGER,
    source_reference TEXT,
    notes TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(korean, type)
);
```

#### 2. import_operations
Track all import operations with metadata
```sql
CREATE TABLE import_operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id TEXT UNIQUE NOT NULL,
    source_file TEXT NOT NULL,
    source_type TEXT CHECK (source_type IN ('csv', 'json', 'api', 'manual')),
    total_items INTEGER NOT NULL DEFAULT 0,
    imported_items INTEGER NOT NULL DEFAULT 0,
    duplicate_items INTEGER NOT NULL DEFAULT 0,
    failed_items INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending' 
        CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'partial')),
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3. vocabulary_imports
Link vocabulary items to their import operations
```sql
CREATE TABLE vocabulary_imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vocabulary_id INTEGER NOT NULL,
    import_id INTEGER NOT NULL,
    original_position INTEGER,
    import_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (import_status IN ('pending', 'imported', 'duplicate', 'failed')),
    error_details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary_master(id) ON DELETE CASCADE,
    FOREIGN KEY (import_id) REFERENCES import_operations(id) ON DELETE CASCADE,
    UNIQUE(vocabulary_id, import_id)
);
```

### Processing Pipeline Tables

#### 4. processing_tasks
Central task management for all processing operations
```sql
CREATE TABLE processing_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT UNIQUE NOT NULL,
    vocabulary_id INTEGER NOT NULL,
    task_type TEXT NOT NULL CHECK (task_type IN ('stage1', 'stage2', 'full_pipeline')),
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'queued', 'processing', 'completed', 'failed', 'cancelled')),
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    scheduled_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary_master(id) ON DELETE CASCADE
);
```

#### 5. processing_results
Store structured processing results
```sql
CREATE TABLE processing_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    stage INTEGER NOT NULL CHECK (stage IN (1, 2)),
    result_type TEXT NOT NULL,
    result_key TEXT NOT NULL,
    result_value TEXT NOT NULL,
    confidence_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES processing_tasks(id) ON DELETE CASCADE,
    UNIQUE(task_id, stage, result_type, result_key)
);
```

### Cache Management Tables

#### 6. cache_entries
Normalized cache storage with metadata
```sql
CREATE TABLE cache_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT UNIQUE NOT NULL,
    vocabulary_id INTEGER NOT NULL,
    stage INTEGER NOT NULL CHECK (stage IN (1, 2)),
    prompt_hash TEXT NOT NULL,
    response_hash TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    model_version TEXT,
    hit_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary_master(id) ON DELETE CASCADE
);
```

#### 7. cache_responses
Separate storage for large response data
```sql
CREATE TABLE cache_responses (
    cache_id INTEGER PRIMARY KEY,
    response_data TEXT NOT NULL,
    compressed BOOLEAN DEFAULT 0,
    FOREIGN KEY (cache_id) REFERENCES cache_entries(id) ON DELETE CASCADE
);
```

### Output Tables

#### 8. flashcards
Final flashcard output with all fields
```sql
CREATE TABLE flashcards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vocabulary_id INTEGER NOT NULL,
    task_id INTEGER NOT NULL,
    card_number INTEGER NOT NULL DEFAULT 1,
    deck_name TEXT,
    front_content TEXT NOT NULL,
    back_content TEXT NOT NULL,
    pronunciation_guide TEXT,
    example_sentence TEXT,
    example_translation TEXT,
    grammar_notes TEXT,
    cultural_notes TEXT,
    mnemonics TEXT,
    difficulty_rating INTEGER CHECK (difficulty_rating BETWEEN 1 AND 5),
    tags TEXT,  -- JSON array
    honorific_level TEXT,
    quality_score REAL,
    is_published BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary_master(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES processing_tasks(id) ON DELETE CASCADE,
    UNIQUE(vocabulary_id, card_number)
);
```

### Analytics Tables

#### 9. api_usage_metrics
Track API usage for cost management
```sql
CREATE TABLE api_usage_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_date DATE NOT NULL,
    hour INTEGER NOT NULL CHECK (hour BETWEEN 0 AND 23),
    model_name TEXT NOT NULL,
    stage INTEGER CHECK (stage IN (1, 2)),
    request_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    estimated_cost REAL DEFAULT 0,
    avg_latency_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(metric_date, hour, model_name, stage)
);
```

#### 10. processing_performance
Track processing performance metrics
```sql
CREATE TABLE processing_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_date DATE NOT NULL,
    task_type TEXT NOT NULL,
    total_processed INTEGER DEFAULT 0,
    cache_hits INTEGER DEFAULT 0,
    cache_misses INTEGER DEFAULT 0,
    avg_processing_time_ms INTEGER,
    p95_processing_time_ms INTEGER,
    p99_processing_time_ms INTEGER,
    concurrent_tasks_avg REAL,
    concurrent_tasks_peak INTEGER,
    error_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(metric_date, task_type)
);
```

### System Tables

#### 11. schema_versions
Track database schema versions
```sql
CREATE TABLE schema_versions (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 12. system_configuration
Store system configuration
```sql
CREATE TABLE system_configuration (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    value_type TEXT CHECK (value_type IN ('string', 'integer', 'real', 'boolean', 'json')),
    description TEXT,
    is_sensitive BOOLEAN DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Indexes

### Performance Indexes
```sql
-- Vocabulary lookups
CREATE INDEX idx_vocabulary_korean ON vocabulary_master(korean);
CREATE INDEX idx_vocabulary_type ON vocabulary_master(type);
CREATE INDEX idx_vocabulary_active ON vocabulary_master(is_active);

-- Import tracking
CREATE INDEX idx_imports_status ON import_operations(status, created_at);
CREATE INDEX idx_vocabulary_imports_status ON vocabulary_imports(import_status);

-- Processing pipeline
CREATE INDEX idx_tasks_status_priority ON processing_tasks(status, priority DESC, scheduled_at);
CREATE INDEX idx_tasks_vocabulary ON processing_tasks(vocabulary_id, task_type);

-- Cache management
CREATE INDEX idx_cache_lookup ON cache_entries(vocabulary_id, stage, prompt_hash);
CREATE INDEX idx_cache_expiry ON cache_entries(expires_at) WHERE expires_at IS NOT NULL;

-- Flashcard queries
CREATE INDEX idx_flashcards_vocabulary ON flashcards(vocabulary_id);
CREATE INDEX idx_flashcards_published ON flashcards(is_published, created_at);

-- Analytics
CREATE INDEX idx_api_metrics_date ON api_usage_metrics(metric_date, model_name);
CREATE INDEX idx_performance_date ON processing_performance(metric_date, task_type);
```

## Views

### Operational Views

#### v_pending_tasks
```sql
CREATE VIEW v_pending_tasks AS
SELECT 
    pt.id,
    pt.task_id,
    vm.korean,
    vm.type,
    pt.task_type,
    pt.priority,
    pt.retry_count,
    pt.created_at
FROM processing_tasks pt
JOIN vocabulary_master vm ON pt.vocabulary_id = vm.id
WHERE pt.status = 'pending'
ORDER BY pt.priority DESC, pt.created_at;
```

#### v_import_summary
```sql
CREATE VIEW v_import_summary AS
SELECT 
    io.operation_id,
    io.source_file,
    io.total_items,
    io.imported_items,
    io.duplicate_items,
    io.failed_items,
    io.status,
    io.created_at,
    io.completed_at,
    CASE 
        WHEN io.total_items > 0 
        THEN ROUND(100.0 * io.imported_items / io.total_items, 2)
        ELSE 0 
    END as success_rate
FROM import_operations io
ORDER BY io.created_at DESC;
```

#### v_cache_statistics
```sql
CREATE VIEW v_cache_statistics AS
SELECT 
    DATE(ce.created_at) as cache_date,
    ce.stage,
    COUNT(*) as total_entries,
    SUM(ce.hit_count) as total_hits,
    AVG(ce.hit_count) as avg_hits_per_entry,
    SUM(ce.token_count) as total_tokens_saved,
    COUNT(CASE WHEN ce.expires_at < CURRENT_TIMESTAMP THEN 1 END) as expired_entries
FROM cache_entries ce
GROUP BY DATE(ce.created_at), ce.stage;
```

## Migration Strategy

### Phase 1: Schema Creation
1. Create new tables with proper constraints
2. Add all indexes and views
3. Populate system tables

### Phase 2: Data Migration
1. Migrate vocabulary_items to vocabulary_master
2. Consolidate import_batches into import_operations
3. Transform cache tables to new structure
4. Migrate processing data

### Phase 3: Cleanup
1. Drop old tables
2. Vacuum database
3. Update application code

## Benefits

1. **Improved Performance**
   - Optimized indexes for common queries
   - Separated hot and cold data
   - Efficient cache lookups

2. **Better Data Integrity**
   - Proper foreign key constraints
   - Unique constraints prevent duplicates
   - Check constraints validate data

3. **Enhanced Maintainability**
   - Clear table purposes
   - Normalized structure
   - Comprehensive documentation

4. **Scalability**
   - Partitioning-ready design
   - Efficient metrics aggregation
   - Archive-friendly structure