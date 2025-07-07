# Database Design Documentation

**Last Updated**: 2025-07-07

## Purpose

This document provides a comprehensive database design for the Korean Language Flashcard Pipeline, following SOLID principles and ensuring maintainability, performance, and scalability.

## Usage

This design serves as the blueprint for implementing the SQLite database that will:
- Cache API responses to minimize costs
- Track processing state and failures
- Store generated flashcard data
- Maintain performance metrics

## Parameters

- **Database Engine**: SQLite 3.x with WAL mode
- **Access Pattern**: Memory-mapped files for performance
- **Connection Pool**: 5-20 connections
- **Cache Strategy**: Content-based keys with TTL support

## Database Schema Overview

### Core Tables

1. **vocabulary_items** - Source vocabulary tracking
2. **stage1_cache** - Semantic analysis results
3. **stage2_cache** - Generated flashcard data
4. **processing_queue** - Items pending processing
5. **failed_items** - Error tracking and retry logic
6. **api_requests** - Request/response logging
7. **performance_metrics** - System performance data
8. **cache_metadata** - Cache management information

## Detailed Schema Design

### 1. vocabulary_items

Tracks all vocabulary items processed by the system.

```sql
CREATE TABLE vocabulary_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    korean TEXT NOT NULL UNIQUE,
    english TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('word', 'phrase', 'idiom', 'grammar')),
    source_file TEXT,
    import_batch_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_vocab_korean ON vocabulary_items(korean);
CREATE INDEX idx_vocab_type ON vocabulary_items(type);
CREATE INDEX idx_vocab_batch ON vocabulary_items(import_batch_id);
```

### 2. stage1_cache

Stores semantic analysis results with intelligent caching.

```sql
CREATE TABLE stage1_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vocabulary_id INTEGER NOT NULL,
    cache_key TEXT NOT NULL UNIQUE,
    request_hash TEXT NOT NULL,
    response_json TEXT NOT NULL,
    nuanced_meanings TEXT,
    contexts TEXT,
    usage_notes TEXT,
    model_version TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    hit_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary_items(id)
);

CREATE INDEX idx_stage1_cache_key ON stage1_cache(cache_key);
CREATE INDEX idx_stage1_vocab ON stage1_cache(vocabulary_id);
CREATE INDEX idx_stage1_expires ON stage1_cache(expires_at);
CREATE INDEX idx_stage1_accessed ON stage1_cache(last_accessed);
```

### 3. stage2_cache

Stores generated flashcard data with version tracking.

```sql
CREATE TABLE stage2_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vocabulary_id INTEGER NOT NULL,
    stage1_cache_id INTEGER NOT NULL,
    cache_key TEXT NOT NULL UNIQUE,
    recognition_card_json TEXT NOT NULL,
    production_card_json TEXT NOT NULL,
    example_sentences_json TEXT,
    image_prompts_json TEXT,
    model_version TEXT NOT NULL,
    generation_params TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    quality_score REAL,
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary_items(id),
    FOREIGN KEY (stage1_cache_id) REFERENCES stage1_cache(id)
);

CREATE INDEX idx_stage2_cache_key ON stage2_cache(cache_key);
CREATE INDEX idx_stage2_vocab ON stage2_cache(vocabulary_id);
CREATE INDEX idx_stage2_stage1 ON stage2_cache(stage1_cache_id);
CREATE INDEX idx_stage2_quality ON stage2_cache(quality_score);
```

### 4. processing_queue

Manages items awaiting processing with priority support.

```sql
CREATE TABLE processing_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vocabulary_id INTEGER NOT NULL,
    stage INTEGER NOT NULL CHECK (stage IN (1, 2)),
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    assigned_worker TEXT,
    queued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary_items(id)
);

CREATE INDEX idx_queue_status_priority ON processing_queue(status, priority DESC);
CREATE INDEX idx_queue_vocab ON processing_queue(vocabulary_id);
CREATE INDEX idx_queue_worker ON processing_queue(assigned_worker);
```

### 5. failed_items

Comprehensive error tracking with retry management.

```sql
CREATE TABLE failed_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vocabulary_id INTEGER NOT NULL,
    stage INTEGER NOT NULL,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    error_details TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    retry_after TIMESTAMP,
    first_failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolution_notes TEXT,
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary_items(id)
);

CREATE INDEX idx_failed_vocab ON failed_items(vocabulary_id);
CREATE INDEX idx_failed_retry ON failed_items(retry_after, retry_count);
CREATE INDEX idx_failed_type ON failed_items(error_type);
CREATE INDEX idx_failed_unresolved ON failed_items(resolved_at) WHERE resolved_at IS NULL;
```

### 6. api_requests

Detailed API request/response logging for debugging and analytics.

```sql
CREATE TABLE api_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL UNIQUE,
    vocabulary_id INTEGER,
    stage INTEGER,
    endpoint TEXT NOT NULL,
    request_body TEXT NOT NULL,
    request_headers TEXT,
    response_status INTEGER,
    response_body TEXT,
    response_headers TEXT,
    latency_ms INTEGER,
    tokens_used INTEGER,
    cost_usd REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary_items(id)
);

CREATE INDEX idx_api_request_id ON api_requests(request_id);
CREATE INDEX idx_api_vocab ON api_requests(vocabulary_id);
CREATE INDEX idx_api_created ON api_requests(created_at);
CREATE INDEX idx_api_status ON api_requests(response_status);
```

### 7. performance_metrics

System performance tracking for optimization.

```sql
CREATE TABLE performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_type TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    dimensions TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_metrics_type_time ON performance_metrics(metric_type, timestamp DESC);
CREATE INDEX idx_metrics_name_time ON performance_metrics(metric_name, timestamp DESC);
```

### 8. cache_metadata

Cache management and statistics.

```sql
CREATE TABLE cache_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_type TEXT NOT NULL CHECK (cache_type IN ('stage1', 'stage2')),
    total_entries INTEGER DEFAULT 0,
    total_hits INTEGER DEFAULT 0,
    total_misses INTEGER DEFAULT 0,
    hit_rate REAL GENERATED ALWAYS AS (
        CASE 
            WHEN (total_hits + total_misses) > 0 
            THEN CAST(total_hits AS REAL) / (total_hits + total_misses) 
            ELSE 0 
        END
    ) STORED,
    last_cleanup TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Views for Common Queries

### Processing Status View

```sql
CREATE VIEW v_processing_status AS
SELECT 
    vi.korean,
    vi.english,
    vi.type,
    COALESCE(pq.status, 'not_queued') as queue_status,
    s1.id IS NOT NULL as has_stage1_cache,
    s2.id IS NOT NULL as has_stage2_cache,
    fi.retry_count,
    fi.error_type
FROM vocabulary_items vi
LEFT JOIN processing_queue pq ON vi.id = pq.vocabulary_id
LEFT JOIN stage1_cache s1 ON vi.id = s1.vocabulary_id
LEFT JOIN stage2_cache s2 ON vi.id = s2.vocabulary_id
LEFT JOIN failed_items fi ON vi.id = fi.vocabulary_id AND fi.resolved_at IS NULL;
```

### Cache Performance View

```sql
CREATE VIEW v_cache_performance AS
SELECT 
    'stage1' as cache_type,
    COUNT(*) as total_entries,
    SUM(hit_count) as total_hits,
    AVG(hit_count) as avg_hits_per_entry,
    COUNT(CASE WHEN expires_at < CURRENT_TIMESTAMP THEN 1 END) as expired_entries
FROM stage1_cache
UNION ALL
SELECT 
    'stage2' as cache_type,
    COUNT(*) as total_entries,
    0 as total_hits,
    0 as avg_hits_per_entry,
    COUNT(CASE WHEN expires_at < CURRENT_TIMESTAMP THEN 1 END) as expired_entries
FROM stage2_cache;
```

## Database Initialization

### Configuration

```sql
-- Enable WAL mode for better concurrency
PRAGMA journal_mode = WAL;

-- Set synchronous mode for performance
PRAGMA synchronous = NORMAL;

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Set cache size (negative = KB)
PRAGMA cache_size = -64000;

-- Memory-mapped I/O
PRAGMA mmap_size = 268435456;
```

### Initial Data

```sql
-- Initialize cache metadata
INSERT INTO cache_metadata (cache_type) VALUES ('stage1'), ('stage2');

-- Create schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO schema_version (version, description) 
VALUES (1, 'Initial schema creation');
```

## Migration Strategy

### Version Control

All schema changes tracked in `/migrations/` with naming convention:
- `V{version}_{timestamp}_{description}.sql`
- Example: `V2_20250108_add_quality_scoring.sql`

### Rollback Support

Each migration must include:
1. Forward migration (`up.sql`)
2. Rollback migration (`down.sql`)
3. Validation queries (`validate.sql`)

## Performance Optimizations

### Index Strategy

1. **Primary Keys**: Automatic B-tree indexes
2. **Foreign Keys**: Indexed for JOIN performance
3. **Cache Lookups**: Covering indexes on cache_key
4. **Time-based Queries**: Compound indexes with timestamp
5. **Queue Processing**: Composite index on status + priority

### Query Optimization

1. Use prepared statements for repeated queries
2. Batch INSERT operations in transactions
3. Regular ANALYZE for query planner statistics
4. Periodic VACUUM for space reclamation

## Security Considerations

### Data Protection

1. No credentials stored in database
2. API keys managed via environment variables
3. Request/response bodies sanitized before storage
4. Personal data anonymization support

### Access Control

1. Read-only connection pool for queries
2. Write connections limited and monitored
3. Audit logging for all modifications
4. Row-level security via application layer

## Monitoring Queries

### Health Check

```sql
-- Database health check
SELECT 
    (SELECT COUNT(*) FROM vocabulary_items) as total_vocabulary,
    (SELECT COUNT(*) FROM processing_queue WHERE status = 'pending') as pending_items,
    (SELECT COUNT(*) FROM failed_items WHERE resolved_at IS NULL) as unresolved_failures,
    (SELECT hit_rate FROM cache_metadata WHERE cache_type = 'stage1') as stage1_hit_rate,
    (SELECT hit_rate FROM cache_metadata WHERE cache_type = 'stage2') as stage2_hit_rate;
```

### Performance Monitoring

```sql
-- Recent API performance
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_requests,
    AVG(latency_ms) as avg_latency,
    SUM(tokens_used) as total_tokens,
    SUM(cost_usd) as total_cost
FROM api_requests
WHERE created_at > datetime('now', '-7 days')
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

## Examples

### Insert Vocabulary Item

```sql
INSERT INTO vocabulary_items (korean, english, type, source_file, import_batch_id)
VALUES ('안녕하세요', 'Hello (formal)', 'phrase', 'lesson1.csv', 'batch_20250107_001');
```

### Check Cache Before API Call

```sql
SELECT 
    id, 
    response_json,
    hit_count
FROM stage1_cache
WHERE cache_key = ? 
  AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP);
```

### Queue Processing

```sql
-- Get next item to process
UPDATE processing_queue
SET status = 'processing', 
    started_at = CURRENT_TIMESTAMP,
    assigned_worker = ?
WHERE id = (
    SELECT id FROM processing_queue
    WHERE status = 'pending'
    ORDER BY priority DESC, queued_at ASC
    LIMIT 1
)
RETURNING *;
```