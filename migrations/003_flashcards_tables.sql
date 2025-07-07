-- Migration: Create flashcards and processing_batches tables
-- Purpose: Add missing tables required for storing processed flashcards
-- Date: 2025-01-07

-- Create processing_batches table first (referenced by flashcards)
CREATE TABLE IF NOT EXISTS processing_batches (
    batch_id TEXT PRIMARY KEY,
    total_items INTEGER NOT NULL,
    completed_items INTEGER DEFAULT 0,
    status TEXT NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    max_concurrent INTEGER DEFAULT 1,
    processing_order TEXT DEFAULT 'position',
    error_message TEXT,
    started_at DATETIME,
    completed_at DATETIME
);

-- Create flashcards table for storing final processed flashcards
CREATE TABLE IF NOT EXISTS flashcards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    term TEXT NOT NULL,
    term_number INTEGER NOT NULL,
    tab_name TEXT NOT NULL,
    primer TEXT NOT NULL,
    front TEXT NOT NULL,
    back TEXT NOT NULL,
    tags TEXT NOT NULL,
    honorific_level TEXT,
    processing_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    processing_order INTEGER,
    processing_time_ms REAL,
    FOREIGN KEY (batch_id) REFERENCES processing_batches(batch_id),
    UNIQUE(batch_id, position)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_flashcards_batch_id ON flashcards(batch_id);
CREATE INDEX IF NOT EXISTS idx_flashcards_position ON flashcards(position);
CREATE INDEX IF NOT EXISTS idx_flashcards_term ON flashcards(term);
CREATE INDEX IF NOT EXISTS idx_processing_batches_status ON processing_batches(status);
CREATE INDEX IF NOT EXISTS idx_processing_batches_created ON processing_batches(created_at);

-- Add trigger to update processing_batches.updated_at
CREATE TRIGGER IF NOT EXISTS update_processing_batches_timestamp 
    AFTER UPDATE ON processing_batches
    BEGIN
        UPDATE processing_batches 
        SET updated_at = CURRENT_TIMESTAMP 
        WHERE batch_id = NEW.batch_id;
    END;