-- Migration: Database Reorganization Phase 1 - Create New Schema
-- Purpose: Create optimized database structure with proper normalization
-- Date: 2025-01-08
-- WARNING: This is a major schema change. Backup your database before running!

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- ============================================
-- CORE DOMAIN TABLES
-- ============================================

-- Drop existing vocabulary_master if it exists (from previous attempts)
DROP TABLE IF EXISTS vocabulary_master;

-- Create new vocabulary master table
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

-- Create import operations table
CREATE TABLE IF NOT EXISTS import_operations (
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

-- Create vocabulary imports link table
CREATE TABLE IF NOT EXISTS vocabulary_imports (
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

-- ============================================
-- PROCESSING PIPELINE TABLES
-- ============================================

-- Create processing tasks table
CREATE TABLE IF NOT EXISTS processing_tasks (
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

-- Create processing results table
CREATE TABLE IF NOT EXISTS processing_results (
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

-- ============================================
-- CACHE MANAGEMENT TABLES
-- ============================================

-- Create cache entries table
CREATE TABLE IF NOT EXISTS cache_entries (
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

-- Create cache responses table
CREATE TABLE IF NOT EXISTS cache_responses (
    cache_id INTEGER PRIMARY KEY,
    response_data TEXT NOT NULL,
    compressed BOOLEAN DEFAULT 0,
    FOREIGN KEY (cache_id) REFERENCES cache_entries(id) ON DELETE CASCADE
);

-- ============================================
-- OUTPUT TABLES
-- ============================================

-- Create flashcards table
CREATE TABLE IF NOT EXISTS flashcards (
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

-- ============================================
-- ANALYTICS TABLES
-- ============================================

-- Create API usage metrics table
CREATE TABLE IF NOT EXISTS api_usage_metrics (
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

-- Create processing performance table
CREATE TABLE IF NOT EXISTS processing_performance (
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

-- ============================================
-- SYSTEM TABLES
-- ============================================

-- Create schema versions table
CREATE TABLE IF NOT EXISTS schema_versions (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create system configuration table
CREATE TABLE IF NOT EXISTS system_configuration (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    value_type TEXT CHECK (value_type IN ('string', 'integer', 'real', 'boolean', 'json')),
    description TEXT,
    is_sensitive BOOLEAN DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TRIGGERS
-- ============================================

-- Update timestamp trigger for vocabulary_master
CREATE TRIGGER update_vocabulary_master_timestamp 
AFTER UPDATE ON vocabulary_master
BEGIN
    UPDATE vocabulary_master SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Update timestamp trigger for flashcards
CREATE TRIGGER update_flashcards_timestamp 
AFTER UPDATE ON flashcards
BEGIN
    UPDATE flashcards SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Update last_accessed_at for cache hits
CREATE TRIGGER update_cache_last_accessed
AFTER UPDATE OF hit_count ON cache_entries
BEGIN
    UPDATE cache_entries SET last_accessed_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- ============================================
-- INITIAL DATA
-- ============================================

-- Insert schema version
INSERT INTO schema_versions (version, name, description) 
VALUES (3, 'database_reorganization_phase1', 'Complete database reorganization with normalized schema');

-- Insert default system configuration
INSERT OR IGNORE INTO system_configuration (key, value, value_type, description) VALUES
    ('cache_ttl_stage1', '2592000', 'integer', 'Stage 1 cache TTL in seconds (30 days)'),
    ('cache_ttl_stage2', '604800', 'integer', 'Stage 2 cache TTL in seconds (7 days)'),
    ('max_concurrent_tasks', '50', 'integer', 'Maximum concurrent processing tasks'),
    ('default_retry_count', '3', 'integer', 'Default retry count for failed tasks'),
    ('metrics_retention_days', '90', 'integer', 'Days to retain metrics data'),
    ('database_version', '3.0', 'string', 'Current database schema version');