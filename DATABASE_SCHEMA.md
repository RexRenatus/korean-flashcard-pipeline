# Database Schema Documentation

**Last Updated**: 2025-07-06

## Overview

The Korean Language Flashcard Pipeline uses SQLite as its primary database for caching API responses and tracking processing state. The database is designed for high performance with memory-mapped file access and optimized indexing.

## Database Architecture

```
┌─────────────────────────────────────────────────┐
│                  pipeline.db                     │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────────────┐  ┌──────────────────────┐ │
│  │ stage1_results  │  │  stage2_results      │ │
│  │                 │  │                      │ │
│  │ • korean (PK)   │  │ • korean (PK)        │ │
│  │ • english       │  │ • english            │ │
│  │ • type          │  │ • type               │ │
│  │ • result_json   │  │ • recognition_card   │ │
│  │ • created_at    │  │ • production_card    │ │
│  │ • updated_at    │  │ • korean_example     │ │
│  └─────────────────┘  │ • english_example    │ │
│                       │ • image_prompt       │ │
│  ┌─────────────────┐  │ • created_at         │ │
│  │  failed_items   │  │ • updated_at         │ │
│  │                 │  └──────────────────────┘ │
│  │ • id (PK)       │                           │
│  │ • korean        │  ┌──────────────────────┐ │
│  │ • english       │  │  processing_stats    │ │
│  │ • type          │  │                      │ │
│  │ • stage         │  │ • id (PK)            │ │
│  │ • error_message │  │ • timestamp          │ │
│  │ • retry_count   │  │ • items_processed    │ │
│  │ • created_at    │  │ • api_calls_made     │ │
│  │ • updated_at    │  │ • cache_hits         │ │
│  └─────────────────┘  │ • processing_time_ms │ │
│                       └──────────────────────┘ │
└─────────────────────────────────────────────────┘
```

## Table Schemas

### 1. stage1_results

Stores semantic analysis results from Stage 1 processing.

```sql
CREATE TABLE stage1_results (
    korean TEXT PRIMARY KEY,
    english TEXT NOT NULL,
    type TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_stage1_type ON stage1_results(type);
CREATE INDEX idx_stage1_created ON stage1_results(created_at);
```

**Columns**:
- `korean`: The Korean word/phrase (Primary Key)
- `english`: English translation
- `type`: Vocabulary type (word, phrase, idiom, etc.)
- `result_json`: JSON containing nuanced meanings, contexts, usage notes
- `created_at`: Record creation timestamp
- `updated_at`: Last update timestamp

**JSON Structure** (result_json):
```json
{
  "nuanced_meanings": ["formal greeting", "hello (polite)"],
  "contexts": ["meeting someone", "formal situations"],
  "usage_notes": "Used in formal settings",
  "register": "formal",
  "frequency": "high"
}
```

### 2. stage2_results

Stores generated flashcard data from Stage 2 processing.

```sql
CREATE TABLE stage2_results (
    korean TEXT PRIMARY KEY,
    english TEXT NOT NULL,
    type TEXT NOT NULL,
    recognition_card TEXT NOT NULL,
    production_card TEXT NOT NULL,
    korean_example TEXT,
    english_example TEXT,
    image_prompt TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_stage2_type ON stage2_results(type);
CREATE INDEX idx_stage2_created ON stage2_results(created_at);
```

**Columns**:
- `korean`: The Korean word/phrase (Primary Key)
- `english`: English translation
- `type`: Vocabulary type
- `recognition_card`: Front of recognition flashcard
- `production_card`: Front of production flashcard
- `korean_example`: Example sentence in Korean
- `english_example`: Example sentence translation
- `image_prompt`: AI-generated image description
- `created_at`: Record creation timestamp
- `updated_at`: Last update timestamp

### 3. failed_items

Tracks items that failed processing for retry logic.

```sql
CREATE TABLE failed_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    korean TEXT NOT NULL,
    english TEXT NOT NULL,
    type TEXT NOT NULL,
    stage INTEGER NOT NULL,
    error_message TEXT NOT NULL,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_failed_korean ON failed_items(korean);
CREATE INDEX idx_failed_stage ON failed_items(stage);
CREATE INDEX idx_failed_retry ON failed_items(retry_count);
```

**Columns**:
- `id`: Auto-incrementing primary key
- `korean`: The Korean word/phrase
- `english`: English translation
- `type`: Vocabulary type
- `stage`: Processing stage where failure occurred (1 or 2)
- `error_message`: Detailed error information
- `retry_count`: Number of retry attempts
- `created_at`: Failure timestamp
- `updated_at`: Last retry timestamp

### 4. processing_stats

Tracks pipeline performance metrics.

```sql
CREATE TABLE processing_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    items_processed INTEGER NOT NULL,
    api_calls_made INTEGER NOT NULL,
    cache_hits INTEGER NOT NULL,
    processing_time_ms INTEGER NOT NULL
);

CREATE INDEX idx_stats_timestamp ON processing_stats(timestamp);
```

**Columns**:
- `id`: Auto-incrementing primary key
- `timestamp`: Statistics collection time
- `items_processed`: Number of items processed in batch
- `api_calls_made`: Number of API calls made
- `cache_hits`: Number of cache hits
- `processing_time_ms`: Total processing time in milliseconds

## Memory-Mapped Cache Tables

For ultra-high performance, frequently accessed data is stored in memory-mapped tables:

### tsv_cache

Stores pre-formatted TSV data for instant export.

```sql
CREATE TABLE tsv_cache (
    id INTEGER PRIMARY KEY,
    tsv_data BLOB NOT NULL,
    row_count INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Indexes

Optimized indexes for common query patterns:

1. **Primary Key Indexes**: Automatic on all primary keys
2. **Type Indexes**: For filtering by vocabulary type
3. **Timestamp Indexes**: For time-based queries
4. **Composite Indexes**: For complex queries

```sql
-- Composite indexes for common queries
CREATE INDEX idx_stage1_type_created 
    ON stage1_results(type, created_at DESC);

CREATE INDEX idx_stage2_type_created 
    ON stage2_results(type, created_at DESC);

CREATE INDEX idx_failed_stage_retry 
    ON failed_items(stage, retry_count);
```

## Database Operations

### Connection Pooling

```python
# Connection pool configuration
POOL_CONFIG = {
    "min_size": 5,
    "max_size": 20,
    "max_idle": 300,  # seconds
    "max_lifetime": 3600  # seconds
}
```

### Transaction Management

All write operations use transactions for consistency:

```python
async with db.transaction():
    await db.save_stage1_result(item, result)
    await db.update_stats(stats)
```

### Vacuum and Optimization

Regular maintenance operations:

```sql
-- Run weekly
VACUUM;
ANALYZE;

-- Rebuild indexes monthly
REINDEX;
```

## Performance Considerations

### 1. Write Performance
- Batch inserts using transactions
- Write-ahead logging (WAL) mode enabled
- Synchronous mode set to NORMAL

### 2. Read Performance
- Memory-mapped file access for cache tables
- Covering indexes for common queries
- Query result caching in application layer

### 3. Storage Optimization
- ZSTD compression for large JSON fields
- Automatic cleanup of old failed items
- Periodic VACUUM to reclaim space

## Migration Strategy

### Version Control

Database schema versions tracked in:
```sql
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Migration Scripts

Located in `/migrations/` directory:
- `001_initial_schema.sql`
- `002_add_indexes.sql`
- `003_add_stats_table.sql`

## Backup Strategy

### Automated Backups
- Daily backups to `backups/` directory
- 7-day retention policy
- Compressed with zstd

### Backup Command
```bash
sqlite3 pipeline.db ".backup 'backups/pipeline_$(date +%Y%m%d).db'"
```

## Monitoring Queries

### Cache Hit Rate
```sql
SELECT 
    SUM(cache_hits) * 100.0 / SUM(items_processed) as cache_hit_rate
FROM processing_stats
WHERE timestamp > datetime('now', '-1 day');
```

### Processing Performance
```sql
SELECT 
    AVG(processing_time_ms / items_processed) as avg_time_per_item,
    MAX(processing_time_ms) as max_batch_time
FROM processing_stats
WHERE timestamp > datetime('now', '-1 hour');
```

### Failed Items Summary
```sql
SELECT 
    stage, 
    COUNT(*) as failed_count,
    AVG(retry_count) as avg_retries
FROM failed_items
GROUP BY stage;
```