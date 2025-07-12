-- Migration: Add Ingress Tables
-- Purpose: Create vocabulary_items and import_batches tables for database-driven word loading
-- Date: 2025-01-08

-- Create vocabulary_items table for storing imported words
CREATE TABLE IF NOT EXISTS vocabulary_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    korean TEXT NOT NULL UNIQUE,
    english TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('word', 'phrase', 'idiom', 'grammar')),
    source_file TEXT,
    import_batch_id TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_vocabulary_status ON vocabulary_items(status);
CREATE INDEX IF NOT EXISTS idx_vocabulary_batch ON vocabulary_items(import_batch_id);
CREATE INDEX IF NOT EXISTS idx_vocabulary_korean ON vocabulary_items(korean);

-- Create import_batches table for tracking import operations
CREATE TABLE IF NOT EXISTS import_batches (
    id TEXT PRIMARY KEY,
    source_file TEXT NOT NULL,
    total_items INTEGER NOT NULL,
    processed_items INTEGER DEFAULT 0,
    failed_items INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'partial')),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Create index for batch status queries
CREATE INDEX IF NOT EXISTS idx_import_batch_status ON import_batches(status);
CREATE INDEX IF NOT EXISTS idx_import_batch_created ON import_batches(created_at);

-- Create a trigger to update the updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_vocabulary_items_timestamp 
AFTER UPDATE ON vocabulary_items
BEGIN
    UPDATE vocabulary_items SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Add migration record
INSERT INTO schema_migrations (version, name, applied_at)
VALUES (2, 'add_ingress_tables', CURRENT_TIMESTAMP);