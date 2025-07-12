-- Migration: Database Reorganization Phase 2 - Indexes and Views
-- Purpose: Add performance indexes and operational views
-- Date: 2025-01-08
-- Prerequisites: Run migration 003 first

-- ============================================
-- PERFORMANCE INDEXES
-- ============================================

-- Vocabulary lookups
CREATE INDEX IF NOT EXISTS idx_vocabulary_korean ON vocabulary_master(korean);
CREATE INDEX IF NOT EXISTS idx_vocabulary_type ON vocabulary_master(type);
CREATE INDEX IF NOT EXISTS idx_vocabulary_active ON vocabulary_master(is_active);
CREATE INDEX IF NOT EXISTS idx_vocabulary_category ON vocabulary_master(category, subcategory);

-- Import tracking
CREATE INDEX IF NOT EXISTS idx_imports_status ON import_operations(status, created_at);
CREATE INDEX IF NOT EXISTS idx_imports_operation_id ON import_operations(operation_id);
CREATE INDEX IF NOT EXISTS idx_vocabulary_imports_status ON vocabulary_imports(import_status);
CREATE INDEX IF NOT EXISTS idx_vocabulary_imports_vocab ON vocabulary_imports(vocabulary_id);

-- Processing pipeline
CREATE INDEX IF NOT EXISTS idx_tasks_status_priority ON processing_tasks(status, priority DESC, scheduled_at);
CREATE INDEX IF NOT EXISTS idx_tasks_vocabulary ON processing_tasks(vocabulary_id, task_type);
CREATE INDEX IF NOT EXISTS idx_tasks_task_id ON processing_tasks(task_id);
CREATE INDEX IF NOT EXISTS idx_results_task ON processing_results(task_id, stage);

-- Cache management
CREATE INDEX IF NOT EXISTS idx_cache_lookup ON cache_entries(vocabulary_id, stage, prompt_hash);
CREATE INDEX IF NOT EXISTS idx_cache_expiry ON cache_entries(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cache_key ON cache_entries(cache_key);

-- Flashcard queries
CREATE INDEX IF NOT EXISTS idx_flashcards_vocabulary ON flashcards(vocabulary_id);
CREATE INDEX IF NOT EXISTS idx_flashcards_published ON flashcards(is_published, created_at);
CREATE INDEX IF NOT EXISTS idx_flashcards_deck ON flashcards(deck_name, is_published);

-- Analytics
CREATE INDEX IF NOT EXISTS idx_api_metrics_date ON api_usage_metrics(metric_date, model_name);
CREATE INDEX IF NOT EXISTS idx_api_metrics_hourly ON api_usage_metrics(metric_date, hour);
CREATE INDEX IF NOT EXISTS idx_performance_date ON processing_performance(metric_date, task_type);

-- ============================================
-- OPERATIONAL VIEWS
-- ============================================

-- Drop existing views if they exist
DROP VIEW IF EXISTS v_pending_tasks;
DROP VIEW IF EXISTS v_import_summary;
DROP VIEW IF EXISTS v_cache_statistics;
DROP VIEW IF EXISTS v_processing_queue;
DROP VIEW IF EXISTS v_daily_metrics;
DROP VIEW IF EXISTS v_vocabulary_status;
DROP VIEW IF EXISTS v_flashcard_export;

-- View: Pending tasks with vocabulary details
CREATE VIEW v_pending_tasks AS
SELECT 
    pt.id,
    pt.task_id,
    pt.vocabulary_id,
    vm.korean,
    vm.english,
    vm.type,
    pt.task_type,
    pt.priority,
    pt.retry_count,
    pt.max_retries,
    pt.created_at,
    pt.scheduled_at
FROM processing_tasks pt
JOIN vocabulary_master vm ON pt.vocabulary_id = vm.id
WHERE pt.status IN ('pending', 'queued')
ORDER BY pt.priority DESC, pt.created_at;

-- View: Import operation summary
CREATE VIEW v_import_summary AS
SELECT 
    io.id,
    io.operation_id,
    io.source_file,
    io.source_type,
    io.total_items,
    io.imported_items,
    io.duplicate_items,
    io.failed_items,
    io.status,
    io.created_at,
    io.started_at,
    io.completed_at,
    CASE 
        WHEN io.started_at IS NOT NULL AND io.completed_at IS NOT NULL
        THEN ROUND((julianday(io.completed_at) - julianday(io.started_at)) * 86400, 2)
        ELSE NULL
    END as processing_time_seconds,
    CASE 
        WHEN io.total_items > 0 
        THEN ROUND(100.0 * io.imported_items / io.total_items, 2)
        ELSE 0 
    END as success_rate
FROM import_operations io
ORDER BY io.created_at DESC;

-- View: Cache statistics by date and stage
CREATE VIEW v_cache_statistics AS
SELECT 
    DATE(ce.created_at) as cache_date,
    ce.stage,
    COUNT(*) as total_entries,
    SUM(ce.hit_count) as total_hits,
    AVG(ce.hit_count) as avg_hits_per_entry,
    SUM(ce.token_count * ce.hit_count) as total_tokens_saved,
    COUNT(CASE WHEN ce.expires_at < CURRENT_TIMESTAMP THEN 1 END) as expired_entries,
    COUNT(CASE WHEN ce.hit_count > 0 THEN 1 END) as used_entries,
    ROUND(100.0 * COUNT(CASE WHEN ce.hit_count > 0 THEN 1 END) / COUNT(*), 2) as usage_rate
FROM cache_entries ce
GROUP BY DATE(ce.created_at), ce.stage
ORDER BY cache_date DESC;

-- View: Current processing queue status
CREATE VIEW v_processing_queue AS
SELECT 
    status,
    task_type,
    COUNT(*) as count,
    AVG(retry_count) as avg_retries,
    MIN(created_at) as oldest_task,
    MAX(created_at) as newest_task
FROM processing_tasks
GROUP BY status, task_type
ORDER BY 
    CASE status 
        WHEN 'processing' THEN 1
        WHEN 'queued' THEN 2
        WHEN 'pending' THEN 3
        WHEN 'failed' THEN 4
        WHEN 'completed' THEN 5
        ELSE 6
    END,
    task_type;

-- View: Daily processing metrics
CREATE VIEW v_daily_metrics AS
SELECT 
    pp.metric_date,
    pp.total_processed,
    pp.cache_hits,
    pp.cache_misses,
    ROUND(100.0 * pp.cache_hits / NULLIF(pp.cache_hits + pp.cache_misses, 0), 2) as cache_hit_rate,
    pp.avg_processing_time_ms,
    pp.concurrent_tasks_peak,
    pp.error_count,
    COALESCE(am.total_requests, 0) as api_requests,
    COALESCE(am.total_tokens, 0) as api_tokens,
    COALESCE(am.estimated_cost, 0) as api_cost
FROM processing_performance pp
LEFT JOIN (
    SELECT 
        metric_date,
        SUM(request_count) as total_requests,
        SUM(total_tokens) as total_tokens,
        SUM(estimated_cost) as estimated_cost
    FROM api_usage_metrics
    GROUP BY metric_date
) am ON pp.metric_date = am.metric_date
ORDER BY pp.metric_date DESC;

-- View: Vocabulary processing status overview
CREATE VIEW v_vocabulary_status AS
SELECT 
    vm.id,
    vm.korean,
    vm.english,
    vm.type,
    vm.category,
    vm.is_active,
    COALESCE(pt.total_tasks, 0) as total_tasks,
    COALESCE(pt.completed_tasks, 0) as completed_tasks,
    COALESCE(pt.failed_tasks, 0) as failed_tasks,
    COALESCE(fc.flashcard_count, 0) as flashcard_count,
    COALESCE(fc.published_count, 0) as published_flashcards,
    vm.created_at,
    vm.updated_at
FROM vocabulary_master vm
LEFT JOIN (
    SELECT 
        vocabulary_id,
        COUNT(*) as total_tasks,
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_tasks
    FROM processing_tasks
    GROUP BY vocabulary_id
) pt ON vm.id = pt.vocabulary_id
LEFT JOIN (
    SELECT 
        vocabulary_id,
        COUNT(*) as flashcard_count,
        SUM(CASE WHEN is_published = 1 THEN 1 ELSE 0 END) as published_count
    FROM flashcards
    GROUP BY vocabulary_id
) fc ON vm.id = fc.vocabulary_id
WHERE vm.is_active = 1;

-- View: Flashcard export view
CREATE VIEW v_flashcard_export AS
SELECT 
    f.id,
    vm.korean,
    vm.english,
    vm.type,
    vm.category,
    f.card_number,
    f.deck_name,
    f.front_content,
    f.back_content,
    f.pronunciation_guide,
    f.example_sentence,
    f.example_translation,
    f.grammar_notes,
    f.cultural_notes,
    f.mnemonics,
    f.difficulty_rating,
    f.tags,
    f.honorific_level,
    f.quality_score,
    f.created_at
FROM flashcards f
JOIN vocabulary_master vm ON f.vocabulary_id = vm.id
WHERE f.is_published = 1
ORDER BY f.deck_name, vm.korean, f.card_number;

-- ============================================
-- ADDITIONAL PERFORMANCE OPTIMIZATIONS
-- ============================================

-- Analyze tables to update statistics
ANALYZE vocabulary_master;
ANALYZE import_operations;
ANALYZE processing_tasks;
ANALYZE cache_entries;
ANALYZE flashcards;

-- Update schema version
INSERT INTO schema_versions (version, name, description) 
VALUES (4, 'database_reorganization_phase2', 'Added performance indexes and operational views');