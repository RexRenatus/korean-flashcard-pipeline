-- Migration: Update Schema for Stage Output Storage
-- Purpose: Better handle structured outputs from Nuance Creator and Flashcard Generator
-- Date: 2025-01-08

-- ============================================
-- STAGE 1: NUANCE CREATOR OUTPUT STORAGE
-- ============================================

-- Create table for structured nuance data
CREATE TABLE IF NOT EXISTS nuance_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vocabulary_id INTEGER NOT NULL,
    task_id INTEGER NOT NULL,
    -- Core fields
    term TEXT NOT NULL,
    term_with_pronunciation TEXT NOT NULL,
    ipa TEXT NOT NULL,
    pos TEXT NOT NULL,
    primary_meaning TEXT NOT NULL,
    other_meanings TEXT,
    -- Memory palace fields
    metaphor TEXT NOT NULL,
    metaphor_noun TEXT NOT NULL,
    metaphor_action TEXT NOT NULL,
    suggested_location TEXT NOT NULL,
    anchor_object TEXT NOT NULL,
    anchor_sensory TEXT NOT NULL,
    explanation TEXT NOT NULL,
    -- Context fields
    usage_context TEXT,
    -- Comparison data (stored as JSON)
    comparison_data TEXT,
    -- Homonyms data (stored as JSON array)
    homonyms_data TEXT,
    -- Keywords (stored as JSON array)
    korean_keywords TEXT NOT NULL,
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary_master(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES processing_tasks(id) ON DELETE CASCADE,
    UNIQUE(vocabulary_id, task_id)
);

-- Create indexes for nuance data
CREATE INDEX IF NOT EXISTS idx_nuance_vocabulary ON nuance_data(vocabulary_id);
CREATE INDEX IF NOT EXISTS idx_nuance_task ON nuance_data(task_id);
CREATE INDEX IF NOT EXISTS idx_nuance_pos ON nuance_data(pos);

-- ============================================
-- STAGE 2: FLASHCARD ENHANCEMENT
-- ============================================

-- Add primer column to flashcards table if not exists
ALTER TABLE flashcards ADD COLUMN primer TEXT;

-- Add position column for TSV output ordering
ALTER TABLE flashcards ADD COLUMN position INTEGER;

-- Add tab_name column (alias for deck_name)
ALTER TABLE flashcards ADD COLUMN tab_name TEXT;

-- Create index for flashcard ordering
CREATE INDEX IF NOT EXISTS idx_flashcards_position ON flashcards(vocabulary_id, position);

-- ============================================
-- VIEWS FOR EASY ACCESS
-- ============================================

-- View: Complete nuance data with vocabulary info
CREATE VIEW IF NOT EXISTS v_nuance_complete AS
SELECT 
    nd.*,
    vm.korean,
    vm.english,
    vm.category,
    vm.difficulty_level,
    pt.status as task_status,
    pt.created_at as task_created
FROM nuance_data nd
JOIN vocabulary_master vm ON nd.vocabulary_id = vm.id
JOIN processing_tasks pt ON nd.task_id = pt.id
ORDER BY nd.created_at DESC;

-- View: Flashcard TSV export format
CREATE VIEW IF NOT EXISTS v_flashcard_tsv_export AS
SELECT 
    f.position,
    nd.term_with_pronunciation as term,
    ROW_NUMBER() OVER (PARTITION BY f.vocabulary_id ORDER BY f.position) as term_number,
    COALESCE(f.tab_name, f.deck_name) as tab_name,
    f.primer,
    f.front_content as front,
    f.back_content as back,
    f.tags,
    f.honorific_level
FROM flashcards f
JOIN vocabulary_master vm ON f.vocabulary_id = vm.id
LEFT JOIN nuance_data nd ON f.vocabulary_id = nd.vocabulary_id
WHERE f.is_published = 1
ORDER BY f.position;

-- ============================================
-- STORED PROCEDURES (AS TRIGGERS)
-- ============================================

-- Trigger to parse and store nuance creator output
CREATE TRIGGER IF NOT EXISTS process_nuance_output
AFTER INSERT ON processing_results
WHEN NEW.stage = 1 AND NEW.result_type = 'nuance_complete'
BEGIN
    -- This would ideally parse the JSON and insert into nuance_data
    -- SQLite doesn't support complex JSON parsing in triggers
    -- This is handled in application code
    SELECT 1; -- Placeholder
END;

-- Trigger to update flashcard position
CREATE TRIGGER IF NOT EXISTS update_flashcard_position
AFTER INSERT ON flashcards
BEGIN
    UPDATE flashcards 
    SET position = (
        SELECT COALESCE(MAX(position), 0) + 1 
        FROM flashcards 
        WHERE vocabulary_id != NEW.vocabulary_id
    )
    WHERE id = NEW.id AND position IS NULL;
END;

-- ============================================
-- HELPER FUNCTIONS (AS VIEWS)
-- ============================================

-- View: Get next position for flashcard
CREATE VIEW IF NOT EXISTS v_next_flashcard_position AS
SELECT 
    COALESCE(MAX(position), 0) + 1 as next_position
FROM flashcards;

-- View: Vocabulary items ready for flashcard generation
CREATE VIEW IF NOT EXISTS v_ready_for_flashcards AS
SELECT DISTINCT
    vm.id as vocabulary_id,
    vm.korean,
    nd.term_with_pronunciation,
    nd.pos,
    pt.id as task_id
FROM vocabulary_master vm
JOIN nuance_data nd ON vm.id = nd.vocabulary_id
JOIN processing_tasks pt ON nd.task_id = pt.id
LEFT JOIN flashcards f ON vm.id = f.vocabulary_id
WHERE pt.status = 'completed'
AND f.id IS NULL
ORDER BY vm.id;

-- ============================================
-- DATA TYPE ENHANCEMENTS
-- ============================================

-- Add check constraints for better data integrity
-- Note: SQLite doesn't support adding constraints to existing tables
-- These would be included in table recreation

-- Suggested constraint for nuance_data.pos:
-- CHECK (pos IN ('noun', 'verb', 'adjective', 'adverb', 'particle', 
--                'determiner', 'numeral', 'pronoun', 'interjection'))

-- Suggested constraint for flashcards.tab_name:
-- CHECK (tab_name IN ('Scene', 'Usage-Comparison', 'Hanja', 'Grammar', 
--                     'Formal-Casual', 'Example', 'Cultural'))

-- ============================================
-- MIGRATION COMPLETION
-- ============================================

-- Update schema version
INSERT INTO schema_versions (version, name, description) 
VALUES (6, 'stage_output_schema_update', 'Enhanced schema for structured stage outputs');

-- Add system configuration for output formats
INSERT OR REPLACE INTO system_configuration (key, value, value_type, description) 
VALUES 
    ('nuance_output_version', '1.0', 'string', 'Version of nuance creator output format'),
    ('flashcard_output_version', '1.0', 'string', 'Version of flashcard generator output format'),
    ('flashcard_cards_per_term', '3', 'integer', 'Default number of flashcards per term'),
    ('flashcard_default_tabs', '["Scene", "Usage-Comparison", "Hanja"]', 'json', 'Default flashcard types to generate');