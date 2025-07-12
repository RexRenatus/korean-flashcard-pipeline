-- Performance optimization indexes for the flashcard pipeline
-- These indexes are designed to improve query performance based on common access patterns

-- ============================================
-- FLASHCARDS TABLE INDEXES
-- ============================================

-- Index for looking up flashcards by word (common search)
CREATE INDEX IF NOT EXISTS idx_flashcards_word 
ON flashcards(word);

-- Index for difficulty-based queries and sorting
CREATE INDEX IF NOT EXISTS idx_flashcards_difficulty 
ON flashcards(difficulty);

-- Composite index for filtering by processed status and ordering by created date
CREATE INDEX IF NOT EXISTS idx_flashcards_processed_created 
ON flashcards(is_processed, created_at);

-- Index for stage processing queries
CREATE INDEX IF NOT EXISTS idx_flashcards_stage1_processed 
ON flashcards(stage1_processed, created_at)
WHERE stage1_processed = 0;

CREATE INDEX IF NOT EXISTS idx_flashcards_stage2_processed 
ON flashcards(stage2_processed, created_at)
WHERE stage2_processed = 0;

-- ============================================
-- STAGE OUTPUTS TABLE INDEXES
-- ============================================

-- Index for retrieving outputs by flashcard
CREATE INDEX IF NOT EXISTS idx_stage_outputs_flashcard_stage 
ON stage_outputs(flashcard_id, stage);

-- Index for finding latest outputs
CREATE INDEX IF NOT EXISTS idx_stage_outputs_created 
ON stage_outputs(created_at DESC);

-- Composite index for status filtering
CREATE INDEX IF NOT EXISTS idx_stage_outputs_status_stage 
ON stage_outputs(status, stage);

-- ============================================
-- PROCESSING HISTORY TABLE INDEXES
-- ============================================

-- Index for history lookups by flashcard
CREATE INDEX IF NOT EXISTS idx_processing_history_flashcard 
ON processing_history(flashcard_id, started_at DESC);

-- Index for finding failed processings
CREATE INDEX IF NOT EXISTS idx_processing_history_status 
ON processing_history(status)
WHERE status IN ('failed', 'error');

-- Index for duration analysis
CREATE INDEX IF NOT EXISTS idx_processing_history_duration 
ON processing_history(duration_seconds)
WHERE duration_seconds IS NOT NULL;

-- ============================================
-- API USAGE TRACKING TABLE INDEXES
-- ============================================

-- Index for usage queries by date
CREATE INDEX IF NOT EXISTS idx_api_usage_created 
ON api_usage_tracking(created_at DESC);

-- Index for model-specific queries
CREATE INDEX IF NOT EXISTS idx_api_usage_model 
ON api_usage_tracking(model_name, created_at);

-- Index for cost analysis
CREATE INDEX IF NOT EXISTS idx_api_usage_cost 
ON api_usage_tracking(estimated_cost_usd)
WHERE status = 'success';

-- ============================================
-- CACHE ENTRIES TABLE INDEXES
-- ============================================

-- Index for cache lookups
CREATE INDEX IF NOT EXISTS idx_cache_entries_key_expires 
ON cache_entries(cache_key, expires_at)
WHERE expires_at > datetime('now');

-- Index for cache cleanup
CREATE INDEX IF NOT EXISTS idx_cache_entries_expires 
ON cache_entries(expires_at)
WHERE expires_at <= datetime('now');

-- ============================================
-- INGRESS QUEUE TABLE INDEXES
-- ============================================

-- Index for queue processing
CREATE INDEX IF NOT EXISTS idx_ingress_queue_status_priority 
ON ingress_queue(status, priority DESC, created_at)
WHERE status IN ('pending', 'processing');

-- Index for finding stalled items
CREATE INDEX IF NOT EXISTS idx_ingress_queue_processing_time 
ON ingress_queue(status, updated_at)
WHERE status = 'processing';

-- ============================================
-- COVERING INDEXES FOR COMMON QUERIES
-- ============================================

-- Covering index for flashcard listing queries
CREATE INDEX IF NOT EXISTS idx_flashcards_listing 
ON flashcards(created_at DESC, word, difficulty, is_processed);

-- Covering index for stage output retrieval
CREATE INDEX IF NOT EXISTS idx_stage_outputs_full 
ON stage_outputs(flashcard_id, stage, status, model_response);

-- Covering index for processing status checks
CREATE INDEX IF NOT EXISTS idx_flashcards_processing_status 
ON flashcards(id, stage1_processed, stage2_processed, is_processed)
WHERE is_processed = 0;

-- ============================================
-- STATISTICS UPDATE
-- ============================================

-- Update SQLite statistics for query planner
ANALYZE;

-- ============================================
-- PERFORMANCE NOTES
-- ============================================

-- These indexes are designed based on the following access patterns:
-- 1. Looking up flashcards by word (exact match and prefix search)
-- 2. Filtering flashcards by difficulty level
-- 3. Finding unprocessed flashcards for batch processing
-- 4. Retrieving stage outputs for specific flashcards
-- 5. Analyzing API usage and costs over time
-- 6. Efficient cache lookups and cleanup
-- 7. Queue processing in priority order

-- Total index size overhead is estimated at ~10-15% of data size
-- Query performance improvements are expected to be 50-90% for indexed queries

-- To verify index usage, run:
-- EXPLAIN QUERY PLAN <your query>

-- To check index statistics:
-- SELECT name, tbl_name FROM sqlite_master WHERE type = 'index' ORDER BY tbl_name;