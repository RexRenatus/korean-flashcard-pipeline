-- Migration: Database Reorganization Phase 3 - Data Migration
-- Purpose: Migrate data from old schema to new reorganized schema
-- Date: 2025-01-08
-- WARNING: This migration transforms existing data. Ensure backup is available!

-- ============================================
-- STEP 1: MIGRATE VOCABULARY DATA
-- ============================================

-- Migrate vocabulary_items to vocabulary_master
-- Handle potential duplicates from multiple vocabulary_items definitions
INSERT OR IGNORE INTO vocabulary_master (
    korean,
    english,
    type,
    category,
    subcategory,
    difficulty_level,
    source_reference,
    created_at,
    updated_at
)
SELECT DISTINCT
    korean,
    english,
    COALESCE(type, 'word'),
    NULL, -- category not in old schema
    NULL, -- subcategory not in old schema
    NULL, -- difficulty_level not in old schema
    source_file,
    created_at,
    COALESCE(updated_at, created_at)
FROM vocabulary_items
WHERE korean IS NOT NULL;

-- ============================================
-- STEP 2: MIGRATE IMPORT OPERATIONS
-- ============================================

-- Migrate import_batches to import_operations
INSERT OR IGNORE INTO import_operations (
    operation_id,
    source_file,
    source_type,
    total_items,
    imported_items,
    failed_items,
    status,
    error_message,
    started_at,
    completed_at,
    created_at
)
SELECT 
    id as operation_id,
    source_file,
    'csv' as source_type,
    total_items,
    processed_items as imported_items,
    failed_items,
    status,
    error_message,
    started_at,
    completed_at,
    created_at
FROM import_batches;

-- Create vocabulary_imports links
INSERT OR IGNORE INTO vocabulary_imports (
    vocabulary_id,
    import_id,
    import_status,
    created_at
)
SELECT DISTINCT
    vm.id as vocabulary_id,
    io.id as import_id,
    CASE 
        WHEN vi.status = 'completed' THEN 'imported'
        WHEN vi.status = 'failed' THEN 'failed'
        ELSE 'pending'
    END as import_status,
    vi.created_at
FROM vocabulary_items vi
JOIN vocabulary_master vm ON vi.korean = vm.korean
JOIN import_operations io ON vi.import_batch_id = io.operation_id
WHERE vi.import_batch_id IS NOT NULL;

-- ============================================
-- STEP 3: MIGRATE PROCESSING DATA
-- ============================================

-- Migrate processing_queue to processing_tasks
INSERT OR IGNORE INTO processing_tasks (
    task_id,
    vocabulary_id,
    task_type,
    priority,
    status,
    retry_count,
    created_at
)
SELECT 
    'task_' || pq.id || '_' || COALESCE(pq.batch_id, 'none') as task_id,
    vm.id as vocabulary_id,
    CASE 
        WHEN pq.stage = 'stage1' THEN 'stage1'
        WHEN pq.stage = 'stage2' THEN 'stage2'
        ELSE 'full_pipeline'
    END as task_type,
    COALESCE(pq.priority, 5) as priority,
    pq.status,
    COALESCE(pq.retry_count, 0) as retry_count,
    pq.created_at
FROM processing_queue pq
JOIN vocabulary_master vm ON pq.korean = vm.korean;

-- ============================================
-- STEP 4: MIGRATE CACHE DATA
-- ============================================

-- Migrate stage1_cache to cache_entries and cache_responses
INSERT OR IGNORE INTO cache_entries (
    cache_key,
    vocabulary_id,
    stage,
    prompt_hash,
    response_hash,
    token_count,
    model_version,
    hit_count,
    expires_at,
    created_at
)
SELECT 
    'stage1_' || s1c.korean || '_' || substr(s1c.prompt_hash, 1, 8) as cache_key,
    vm.id as vocabulary_id,
    1 as stage,
    s1c.prompt_hash,
    s1c.response_hash,
    COALESCE(s1c.token_count, 0) as token_count,
    s1c.model_version,
    0 as hit_count, -- Reset hit counts
    datetime(s1c.created_at, '+30 days') as expires_at,
    s1c.created_at
FROM stage1_cache s1c
JOIN vocabulary_master vm ON s1c.korean = vm.korean
WHERE s1c.response IS NOT NULL;

-- Insert stage1 cache responses
INSERT OR IGNORE INTO cache_responses (cache_id, response_data, compressed)
SELECT 
    ce.id,
    s1c.response,
    0
FROM stage1_cache s1c
JOIN vocabulary_master vm ON s1c.korean = vm.korean
JOIN cache_entries ce ON ce.vocabulary_id = vm.id AND ce.stage = 1 AND ce.prompt_hash = s1c.prompt_hash
WHERE s1c.response IS NOT NULL;

-- Migrate stage2_cache to cache_entries and cache_responses
INSERT OR IGNORE INTO cache_entries (
    cache_key,
    vocabulary_id,
    stage,
    prompt_hash,
    response_hash,
    token_count,
    model_version,
    hit_count,
    expires_at,
    created_at
)
SELECT 
    'stage2_' || s2c.korean || '_' || substr(s2c.prompt_hash, 1, 8) as cache_key,
    vm.id as vocabulary_id,
    2 as stage,
    s2c.prompt_hash,
    s2c.response_hash,
    COALESCE(s2c.token_count, 0) as token_count,
    s2c.model_version,
    0 as hit_count,
    datetime(s2c.created_at, '+7 days') as expires_at,
    s2c.created_at
FROM stage2_cache s2c
JOIN vocabulary_master vm ON s2c.korean = vm.korean
WHERE s2c.response IS NOT NULL;

-- Insert stage2 cache responses
INSERT OR IGNORE INTO cache_responses (cache_id, response_data, compressed)
SELECT 
    ce.id,
    s2c.response,
    0
FROM stage2_cache s2c
JOIN vocabulary_master vm ON s2c.korean = vm.korean
JOIN cache_entries ce ON ce.vocabulary_id = vm.id AND ce.stage = 2 AND ce.prompt_hash = s2c.prompt_hash
WHERE s2c.response IS NOT NULL;

-- ============================================
-- STEP 5: MIGRATE FLASHCARD DATA
-- ============================================

-- Migrate existing flashcards if table exists
-- Note: Old schema may not have flashcards table, so we check first
INSERT OR IGNORE INTO flashcards (
    vocabulary_id,
    task_id,
    card_number,
    deck_name,
    front_content,
    back_content,
    pronunciation_guide,
    example_sentence,
    example_translation,
    tags,
    created_at
)
SELECT 
    vm.id as vocabulary_id,
    pt.id as task_id,
    COALESCE(f.term_number, 1) as card_number,
    COALESCE(f.tab_name, 'General') as deck_name,
    f.front as front_content,
    f.back as back_content,
    f.primer as pronunciation_guide,
    NULL as example_sentence,
    NULL as example_translation,
    f.tags,
    f.created_at
FROM flashcards_old f
JOIN vocabulary_master vm ON f.term = vm.korean
JOIN processing_tasks pt ON pt.vocabulary_id = vm.id AND pt.status = 'completed'
WHERE EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='flashcards_old');

-- ============================================
-- STEP 6: MIGRATE METRICS DATA
-- ============================================

-- Migrate API metrics if they exist
INSERT OR IGNORE INTO api_usage_metrics (
    metric_date,
    hour,
    model_name,
    stage,
    request_count,
    success_count,
    failure_count,
    total_tokens,
    prompt_tokens,
    completion_tokens,
    estimated_cost,
    created_at
)
SELECT 
    DATE(created_at) as metric_date,
    CAST(strftime('%H', created_at) AS INTEGER) as hour,
    COALESCE(model_name, 'anthropic/claude-3-sonnet') as model_name,
    CASE 
        WHEN endpoint LIKE '%stage1%' THEN 1
        WHEN endpoint LIKE '%stage2%' THEN 2
        ELSE NULL
    END as stage,
    COUNT(*) as request_count,
    SUM(CASE WHEN status_code = 200 THEN 1 ELSE 0 END) as success_count,
    SUM(CASE WHEN status_code != 200 THEN 1 ELSE 0 END) as failure_count,
    SUM(total_tokens) as total_tokens,
    SUM(prompt_tokens) as prompt_tokens,
    SUM(completion_tokens) as completion_tokens,
    SUM(estimated_cost) as estimated_cost,
    MIN(created_at) as created_at
FROM api_metrics
WHERE EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='api_metrics')
GROUP BY DATE(created_at), CAST(strftime('%H', created_at) AS INTEGER), model_name, 
    CASE 
        WHEN endpoint LIKE '%stage1%' THEN 1
        WHEN endpoint LIKE '%stage2%' THEN 2
        ELSE NULL
    END;

-- ============================================
-- STEP 7: UPDATE CACHE METRICS
-- ============================================

-- Update cache hit counts based on cache_metrics if available
UPDATE cache_entries
SET hit_count = (
    SELECT COUNT(*) 
    FROM cache_metrics cm 
    WHERE cm.cache_key = cache_entries.cache_key 
    AND cm.hit = 1
)
WHERE EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='cache_metrics');

-- ============================================
-- STEP 8: CREATE SUMMARY STATISTICS
-- ============================================

-- Create initial processing performance entry for today
INSERT OR IGNORE INTO processing_performance (
    metric_date,
    task_type,
    total_processed,
    cache_hits,
    cache_misses,
    avg_processing_time_ms,
    error_count,
    created_at
)
SELECT 
    DATE('now') as metric_date,
    'full_pipeline' as task_type,
    COUNT(DISTINCT vocabulary_id) as total_processed,
    (SELECT COUNT(*) FROM cache_entries WHERE hit_count > 0) as cache_hits,
    (SELECT COUNT(*) FROM cache_entries WHERE hit_count = 0) as cache_misses,
    0 as avg_processing_time_ms,
    (SELECT COUNT(*) FROM processing_tasks WHERE status = 'failed') as error_count,
    CURRENT_TIMESTAMP
FROM processing_tasks
WHERE status = 'completed';

-- ============================================
-- STEP 9: CLEANUP AND VERIFICATION
-- ============================================

-- Log migration statistics
INSERT INTO system_configuration (key, value, value_type, description) 
VALUES ('migration_stats', json_object(
    'vocabulary_migrated', (SELECT COUNT(*) FROM vocabulary_master),
    'imports_migrated', (SELECT COUNT(*) FROM import_operations),
    'tasks_migrated', (SELECT COUNT(*) FROM processing_tasks),
    'cache_entries_migrated', (SELECT COUNT(*) FROM cache_entries),
    'flashcards_migrated', (SELECT COUNT(*) FROM flashcards),
    'migration_date', datetime('now')
), 'json', 'Data migration statistics from reorganization');

-- Update schema version
INSERT INTO schema_versions (version, name, description) 
VALUES (5, 'database_reorganization_phase3', 'Data migration from old schema to new reorganized schema completed');