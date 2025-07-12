# Database Schema V2 Documentation

## Overview

This document describes the reorganized database schema for the Korean Flashcard Pipeline. The new schema addresses normalization issues, improves performance, and provides better data integrity.

## Schema Diagram

```mermaid
erDiagram
    vocabulary_master ||--o{ vocabulary_imports : "imported via"
    vocabulary_master ||--o{ processing_tasks : "has"
    vocabulary_master ||--o{ cache_entries : "cached"
    vocabulary_master ||--o{ flashcards : "generates"
    
    import_operations ||--o{ vocabulary_imports : "contains"
    
    processing_tasks ||--o{ processing_results : "produces"
    processing_tasks ||--o{ flashcards : "creates"
    
    cache_entries ||--|| cache_responses : "stores"
    
    vocabulary_master {
        int id PK
        text korean UK
        text english
        text romanization
        text hanja
        text type
        text category
        text subcategory
        int difficulty_level
        int frequency_rank
        text source_reference
        text notes
        bool is_active
        timestamp created_at
        timestamp updated_at
    }
    
    import_operations {
        int id PK
        text operation_id UK
        text source_file
        text source_type
        int total_items
        int imported_items
        int duplicate_items
        int failed_items
        text status
        text error_message
        timestamp started_at
        timestamp completed_at
        timestamp created_at
    }
    
    vocabulary_imports {
        int id PK
        int vocabulary_id FK
        int import_id FK
        int original_position
        text import_status
        text error_details
        timestamp created_at
    }
    
    processing_tasks {
        int id PK
        text task_id UK
        int vocabulary_id FK
        text task_type
        int priority
        text status
        int retry_count
        int max_retries
        timestamp scheduled_at
        timestamp started_at
        timestamp completed_at
        timestamp created_at
    }
    
    processing_results {
        int id PK
        int task_id FK
        int stage
        text result_type
        text result_key
        text result_value
        real confidence_score
        timestamp created_at
    }
    
    cache_entries {
        int id PK
        text cache_key UK
        int vocabulary_id FK
        int stage
        text prompt_hash
        text response_hash
        int token_count
        text model_version
        int hit_count
        timestamp last_accessed_at
        timestamp expires_at
        timestamp created_at
    }
    
    cache_responses {
        int cache_id PK FK
        text response_data
        bool compressed
    }
    
    flashcards {
        int id PK
        int vocabulary_id FK
        int task_id FK
        int card_number
        text deck_name
        text front_content
        text back_content
        text pronunciation_guide
        text example_sentence
        text example_translation
        text grammar_notes
        text cultural_notes
        text mnemonics
        int difficulty_rating
        text tags
        text honorific_level
        real quality_score
        bool is_published
        timestamp created_at
        timestamp updated_at
    }
```

## Table Descriptions

### Core Domain Tables

#### vocabulary_master
Central repository for all vocabulary items with comprehensive metadata.
- **Purpose**: Store unique vocabulary entries with linguistic and metadata information
- **Key Features**: 
  - Unique constraint on (korean, type) prevents duplicates
  - Supports multiple types: word, phrase, idiom, grammar, sentence
  - Includes difficulty and frequency ranking
  - Soft delete via is_active flag

#### import_operations
Tracks all data import operations with detailed statistics.
- **Purpose**: Audit trail and monitoring of CSV/API imports
- **Key Features**:
  - Unique operation_id for tracking
  - Detailed success/failure metrics
  - Support for multiple source types
  - Processing time tracking

#### vocabulary_imports
Links vocabulary items to their import operations.
- **Purpose**: Track origin and import status of each vocabulary item
- **Key Features**:
  - Maps vocabulary to import batches
  - Tracks individual item import status
  - Stores original position for reference

### Processing Pipeline Tables

#### processing_tasks
Central task queue for all processing operations.
- **Purpose**: Manage and track vocabulary processing through the pipeline
- **Key Features**:
  - Priority-based processing
  - Retry mechanism with configurable limits
  - Support for different task types (stage1, stage2, full_pipeline)
  - Comprehensive status tracking

#### processing_results
Stores structured results from processing stages.
- **Purpose**: Capture detailed output from each processing stage
- **Key Features**:
  - Key-value storage for flexible result types
  - Confidence scoring for quality tracking
  - Stage-specific results separation

### Cache Management Tables

#### cache_entries
Metadata for cached API responses with hit tracking.
- **Purpose**: Efficient cache lookup and management
- **Key Features**:
  - Unique cache keys for fast lookup
  - Hit counting for usage analytics
  - TTL support with automatic expiration
  - Model version tracking

#### cache_responses
Separate storage for large response data.
- **Purpose**: Optimize cache_entries table performance
- **Key Features**:
  - 1:1 relationship with cache_entries
  - Support for compressed storage
  - Separated to keep metadata table lean

### Output Tables

#### flashcards
Comprehensive flashcard storage with all learning fields.
- **Purpose**: Store generated flashcards ready for export
- **Key Features**:
  - Multiple cards per vocabulary item
  - Rich content fields (examples, notes, mnemonics)
  - Quality scoring and publishing workflow
  - Deck organization support

### Analytics Tables

#### api_usage_metrics
Hourly API usage tracking for cost management.
- **Purpose**: Monitor API usage and costs
- **Key Features**:
  - Hourly granularity
  - Model and stage-specific tracking
  - Token and cost calculation
  - Latency monitoring

#### processing_performance
Daily processing performance metrics.
- **Purpose**: Track system performance and optimization opportunities
- **Key Features**:
  - Cache hit rate tracking
  - Processing time percentiles
  - Concurrency metrics
  - Error rate monitoring

### System Tables

#### schema_versions
Database migration tracking.
- **Purpose**: Version control for database schema
- **Key Features**:
  - Sequential version numbering
  - Migration history
  - Applied timestamp tracking

#### system_configuration
Key-value configuration storage.
- **Purpose**: Runtime configuration without code changes
- **Key Features**:
  - Typed values (string, integer, real, boolean, json)
  - Sensitive value flagging
  - Description documentation

## Indexes

### Performance Indexes
- `idx_vocabulary_korean`: Fast Korean term lookup
- `idx_vocabulary_type`: Filter by vocabulary type
- `idx_vocabulary_active`: Active items only
- `idx_tasks_status_priority`: Priority queue processing
- `idx_cache_lookup`: Efficient cache hit detection
- `idx_flashcards_published`: Export-ready flashcards

### Foreign Key Indexes
Automatically created for all foreign key relationships

## Views

### Operational Views

#### v_pending_tasks
Shows all pending processing tasks with vocabulary details.
```sql
SELECT task info + vocabulary details
WHERE status IN ('pending', 'queued')
ORDER BY priority DESC, created_at
```

#### v_import_summary
Import operations with calculated statistics.
```sql
SELECT import details + success rate + processing time
ORDER BY created_at DESC
```

#### v_cache_statistics
Cache performance metrics by date and stage.
```sql
SELECT cache metrics GROUP BY date, stage
Including hit rates, token savings, usage patterns
```

#### v_flashcard_export
Export-ready flashcards with full vocabulary context.
```sql
SELECT flashcard + vocabulary details
WHERE is_published = 1
ORDER BY deck_name, korean, card_number
```

## Migration Path

### From Old Schema
1. Run migration scripts in order:
   - `003_database_reorganization_phase1.sql` - Create new schema
   - `004_database_reorganization_phase2.sql` - Add indexes and views
   - `005_database_reorganization_phase3_data_migration.sql` - Migrate data

2. Update application code to use:
   - `DatabaseManager` instead of direct SQL
   - `IngressServiceV2` for imports
   - New model classes (VocabularyRecord, ProcessingTask, etc.)

3. Verify migration with:
   ```sql
   SELECT * FROM system_configuration 
   WHERE key = 'migration_stats';
   ```

## Performance Considerations

### Query Optimization
- All common queries have supporting indexes
- Views pre-calculate complex joins
- Separate tables for hot (cache_entries) and cold (cache_responses) data

### Data Growth Management
- Metrics tables designed for time-based partitioning
- Expired cache entries can be automatically cleaned
- Processing history can be archived

### Concurrency
- Row-level locking for task processing
- Optimistic locking via updated_at timestamps
- Connection pooling support in DatabaseManager

## Best Practices

### Data Integrity
1. Always use foreign key constraints
2. Validate data types with CHECK constraints
3. Use transactions for multi-table operations
4. Implement soft deletes where appropriate

### Performance
1. Keep frequently accessed data normalized
2. Denormalize only for specific performance needs
3. Use indexes for all foreign keys and common filters
4. Monitor and vacuum database regularly

### Maintenance
1. Regular backups before migrations
2. Monitor table sizes and growth patterns
3. Clean up expired cache entries periodically
4. Archive old metrics data

## Future Enhancements

### Planned Improvements
1. **Full-text search** on vocabulary content
2. **Partitioned tables** for metrics data
3. **Materialized views** for complex analytics
4. **Audit logging** for all data changes
5. **Replication support** for scalability

### Extension Points
- Additional vocabulary metadata fields
- Custom flashcard templates
- Multi-language support
- User-specific customization

## Troubleshooting

### Common Issues

1. **Foreign Key Violations**
   - Ensure parent records exist before inserting
   - Check cascade rules for deletions

2. **Unique Constraint Errors**
   - Vocabulary: Check (korean, type) combination
   - Cache: Verify cache_key generation

3. **Performance Degradation**
   - Run ANALYZE to update statistics
   - Check for missing indexes
   - Monitor cache hit rates

### Diagnostic Queries

```sql
-- Check database stats
SELECT * FROM v_daily_metrics WHERE metric_date = date('now');

-- Find processing bottlenecks
SELECT * FROM v_processing_queue;

-- Cache effectiveness
SELECT * FROM v_cache_statistics WHERE cache_date >= date('now', '-7 days');

-- Recent errors
SELECT * FROM processing_tasks 
WHERE status = 'failed' 
AND created_at >= datetime('now', '-1 day');
```