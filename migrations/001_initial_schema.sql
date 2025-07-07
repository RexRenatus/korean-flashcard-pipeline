-- Initial schema for Korean Flashcard Pipeline
-- Version: 1
-- Description: Create all core tables with indexes

-- Vocabulary items table
CREATE TABLE IF NOT EXISTS vocabulary_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    korean TEXT NOT NULL,
    english TEXT NOT NULL,
    hanja TEXT,
    category TEXT NOT NULL,
    subcategory TEXT,
    difficulty_level TEXT NOT NULL CHECK (difficulty_level IN ('beginner', 'elementary', 'intermediate', 'advanced', 'native')),
    source TEXT NOT NULL DEFAULT 'manual',
    example_sentence TEXT,
    notes TEXT,
    metadata TEXT DEFAULT '{}', -- JSON
    tags TEXT DEFAULT '[]', -- JSON array
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(korean, english, category)
);

-- Stage 1 cache table
CREATE TABLE IF NOT EXISTS stage1_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vocabulary_id INTEGER NOT NULL,
    cache_key TEXT NOT NULL UNIQUE,
    request_hash TEXT NOT NULL,
    response_json TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0,
    model_used TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    accessed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary_items(id) ON DELETE CASCADE
);

-- Stage 2 cache table
CREATE TABLE IF NOT EXISTS stage2_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vocabulary_id INTEGER NOT NULL,
    stage1_cache_key TEXT NOT NULL,
    cache_key TEXT NOT NULL UNIQUE,
    request_hash TEXT NOT NULL,
    response_json TEXT NOT NULL,
    tsv_output TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0,
    model_used TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    accessed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary_items(id) ON DELETE CASCADE
);

-- Processing queue table
CREATE TABLE IF NOT EXISTS processing_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vocabulary_id INTEGER NOT NULL,
    batch_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'quarantined')),
    stage TEXT NOT NULL CHECK (stage IN ('stage1', 'stage2', 'complete')),
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary_items(id) ON DELETE CASCADE
);

-- Batch metadata table
CREATE TABLE IF NOT EXISTS batch_metadata (
    batch_id TEXT PRIMARY KEY,
    total_items INTEGER NOT NULL,
    completed_items INTEGER NOT NULL DEFAULT 0,
    failed_items INTEGER NOT NULL DEFAULT 0,
    quarantined_items INTEGER NOT NULL DEFAULT 0,
    start_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    status TEXT NOT NULL CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'partial')),
    metadata TEXT DEFAULT '{}' -- JSON
);

-- Processing checkpoints table
CREATE TABLE IF NOT EXISTS processing_checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    last_processed_id INTEGER NOT NULL,
    stage TEXT NOT NULL,
    checkpoint_data TEXT NOT NULL, -- JSON
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES batch_metadata(batch_id) ON DELETE CASCADE
);

-- API metrics table
CREATE TABLE IF NOT EXISTS api_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint TEXT NOT NULL,
    model TEXT NOT NULL,
    status_code INTEGER,
    response_time_ms INTEGER,
    token_count INTEGER,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Cache metrics table
CREATE TABLE IF NOT EXISTS cache_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_type TEXT NOT NULL CHECK (cache_type IN ('stage1', 'stage2')),
    hit_count INTEGER NOT NULL DEFAULT 0,
    miss_count INTEGER NOT NULL DEFAULT 0,
    total_tokens_saved INTEGER NOT NULL DEFAULT 0,
    date DATE NOT NULL DEFAULT (DATE('now')),
    UNIQUE(cache_type, date)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_vocabulary_korean ON vocabulary_items(korean);
CREATE INDEX IF NOT EXISTS idx_vocabulary_category ON vocabulary_items(category);
CREATE INDEX IF NOT EXISTS idx_vocabulary_difficulty ON vocabulary_items(difficulty_level);
CREATE INDEX IF NOT EXISTS idx_vocabulary_created ON vocabulary_items(created_at);

CREATE INDEX IF NOT EXISTS idx_stage1_cache_vocab_id ON stage1_cache(vocabulary_id);
CREATE INDEX IF NOT EXISTS idx_stage1_cache_key ON stage1_cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_stage1_cache_accessed ON stage1_cache(accessed_at);

CREATE INDEX IF NOT EXISTS idx_stage2_cache_vocab_id ON stage2_cache(vocabulary_id);
CREATE INDEX IF NOT EXISTS idx_stage2_cache_key ON stage2_cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_stage2_cache_stage1_key ON stage2_cache(stage1_cache_key);
CREATE INDEX IF NOT EXISTS idx_stage2_cache_accessed ON stage2_cache(accessed_at);

CREATE INDEX IF NOT EXISTS idx_queue_batch_id ON processing_queue(batch_id);
CREATE INDEX IF NOT EXISTS idx_queue_status ON processing_queue(status);
CREATE INDEX IF NOT EXISTS idx_queue_vocab_id ON processing_queue(vocabulary_id);
CREATE INDEX IF NOT EXISTS idx_queue_stage ON processing_queue(stage);

CREATE INDEX IF NOT EXISTS idx_checkpoints_batch_id ON processing_checkpoints(batch_id);

CREATE INDEX IF NOT EXISTS idx_api_metrics_created ON api_metrics(created_at);
CREATE INDEX IF NOT EXISTS idx_api_metrics_model ON api_metrics(model);

-- Create triggers for updated_at
CREATE TRIGGER IF NOT EXISTS update_vocabulary_timestamp 
AFTER UPDATE ON vocabulary_items
BEGIN
    UPDATE vocabulary_items SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_queue_timestamp 
AFTER UPDATE ON processing_queue
BEGIN
    UPDATE processing_queue SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_cache_access_stage1
AFTER UPDATE ON stage1_cache
BEGIN
    UPDATE stage1_cache SET accessed_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_cache_access_stage2
AFTER UPDATE ON stage2_cache
BEGIN
    UPDATE stage2_cache SET accessed_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;