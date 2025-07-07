-- migrations/002_concurrent_processing.sql
-- Add support for concurrent processing

-- Add position column to vocabulary_items for ordered processing
ALTER TABLE vocabulary_items ADD COLUMN position INTEGER;

-- Create index on the new position column
CREATE INDEX IF NOT EXISTS idx_vocabulary_position 
    ON vocabulary_items(position);

-- Add processing order tracking to batch_metadata
ALTER TABLE batch_metadata ADD COLUMN max_concurrent INTEGER DEFAULT 1;
ALTER TABLE batch_metadata ADD COLUMN actual_concurrent INTEGER;
ALTER TABLE batch_metadata ADD COLUMN processing_order TEXT DEFAULT 'position';

-- Create table for concurrent processing metrics
CREATE TABLE IF NOT EXISTS concurrent_processing_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    concurrent_count INTEGER,
    total_duration_ms INTEGER,
    average_item_duration_ms REAL,
    rate_limit_hits INTEGER DEFAULT 0,
    circuit_breaker_trips INTEGER DEFAULT 0,
    cache_hit_rate REAL,
    FOREIGN KEY (batch_id) REFERENCES processing_batches(batch_id)
);

-- Create table for processing errors
CREATE TABLE IF NOT EXISTS processing_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    term TEXT NOT NULL,
    error_message TEXT,
    error_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES processing_batches(batch_id)
);

-- Note: Schema migration version is tracked automatically by the migration runner