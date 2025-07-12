"""
Comprehensive test suite for DatabaseManager class.
Tests all database operations including vocabulary, tasks, cache, flashcards, and metrics.
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path
import json

from flashcard_pipeline.database.db_manager import (
    DatabaseManager,
    VocabularyRecord,
    ProcessingTask,
    FlashcardRecord
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Initialize database with schema
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    
    # Create tables matching the reorganized schema
    cursor.executescript("""
        -- Vocabulary table
        CREATE TABLE IF NOT EXISTS vocabulary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            korean TEXT NOT NULL UNIQUE,
            english TEXT,
            romanization TEXT,
            hanja TEXT,
            type TEXT DEFAULT 'word',
            category TEXT,
            subcategory TEXT,
            difficulty_level INTEGER,
            frequency_rank INTEGER,
            source_reference TEXT,
            notes TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Processing tasks table
        CREATE TABLE IF NOT EXISTS processing_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            vocabulary_id INTEGER NOT NULL,
            task_type TEXT DEFAULT 'full_pipeline',
            priority INTEGER DEFAULT 5,
            status TEXT DEFAULT 'pending',
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            scheduled_at TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vocabulary_id) REFERENCES vocabulary(id)
        );

        -- Stage outputs table
        CREATE TABLE IF NOT EXISTS stage_outputs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            stage_name TEXT NOT NULL,
            stage_number INTEGER,
            output_data TEXT,
            metadata TEXT,
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            processing_time_ms INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES processing_tasks(id)
        );

        -- Flashcards table
        CREATE TABLE IF NOT EXISTS flashcards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vocabulary_id INTEGER NOT NULL,
            task_id INTEGER NOT NULL,
            card_number INTEGER DEFAULT 1,
            deck_name TEXT,
            front_content TEXT NOT NULL,
            back_content TEXT NOT NULL,
            pronunciation_guide TEXT,
            example_sentence TEXT,
            example_translation TEXT,
            grammar_notes TEXT,
            cultural_notes TEXT,
            mnemonics TEXT,
            difficulty_rating INTEGER,
            tags TEXT,
            honorific_level TEXT,
            quality_score REAL,
            is_published BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vocabulary_id) REFERENCES vocabulary(id),
            FOREIGN KEY (task_id) REFERENCES processing_tasks(id)
        );

        -- Processing metrics table
        CREATE TABLE IF NOT EXISTS processing_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            stage_name TEXT NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            duration_ms INTEGER,
            status TEXT,
            error_count INTEGER DEFAULT 0,
            retry_count INTEGER DEFAULT 0,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES processing_tasks(id)
        );

        -- API usage table
        CREATE TABLE IF NOT EXISTS api_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            api_name TEXT NOT NULL,
            endpoint TEXT,
            request_timestamp TIMESTAMP NOT NULL,
            response_time_ms INTEGER,
            status_code INTEGER,
            tokens_used INTEGER,
            cost_estimate REAL,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES processing_tasks(id)
        );

        -- Cache entries table
        CREATE TABLE IF NOT EXISTS cache_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cache_key TEXT UNIQUE NOT NULL,
            cache_value TEXT NOT NULL,
            cache_type TEXT DEFAULT 'api_response',
            ttl_seconds INTEGER,
            expires_at TIMESTAMP,
            hit_count INTEGER DEFAULT 0,
            last_accessed TIMESTAMP,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- System configuration table
        CREATE TABLE IF NOT EXISTS system_configuration (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Insert schema version
        INSERT INTO system_configuration (key, value, description)
        VALUES ('schema_version', '2.0', 'Database schema version');
    """)
    
    conn.commit()
    conn.close()
    
    yield path
    
    # Cleanup
    os.unlink(path)


@pytest.fixture
def db_manager(temp_db):
    """Create a DatabaseManager instance with temporary database"""
    return DatabaseManager(temp_db)


class TestDatabaseManager:
    """Test suite for DatabaseManager class"""
    
    def test_initialization(self, db_manager):
        """Test DatabaseManager initialization"""
        assert db_manager.db_path is not None
        assert os.path.exists(db_manager.db_path)
    
    def test_get_connection(self, db_manager):
        """Test database connection context manager"""
        with db_manager.get_connection() as conn:
            assert conn is not None
            # Check foreign keys are enabled
            cursor = conn.execute("PRAGMA foreign_keys")
            assert cursor.fetchone()[0] == 1
            # Check WAL mode
            cursor = conn.execute("PRAGMA journal_mode")
            assert cursor.fetchone()[0] == 'wal'
    
    # Vocabulary Operations Tests
    
    def test_create_vocabulary(self, db_manager):
        """Test creating a vocabulary record"""
        vocab = VocabularyRecord(
            korean="안녕하세요",
            english="Hello",
            romanization="annyeonghaseyo",
            type="phrase",
            category="greeting",
            difficulty_level=1
        )
        
        vocab_id = db_manager.create_vocabulary(vocab)
        assert vocab_id > 0
        
        # Verify it was created
        retrieved = db_manager.get_vocabulary_by_id(vocab_id)
        assert retrieved is not None
        assert retrieved.korean == "안녕하세요"
        assert retrieved.english == "Hello"
    
    def test_get_vocabulary_by_korean(self, db_manager):
        """Test retrieving vocabulary by Korean text"""
        vocab = VocabularyRecord(korean="감사합니다", english="Thank you")
        vocab_id = db_manager.create_vocabulary(vocab)
        
        retrieved = db_manager.get_vocabulary_by_korean("감사합니다")
        assert retrieved is not None
        assert retrieved.id == vocab_id
        assert retrieved.english == "Thank you"
    
    def test_get_pending_vocabulary(self, db_manager):
        """Test retrieving pending vocabulary items"""
        # Create some vocabulary items
        vocabs = [
            VocabularyRecord(korean="하나", english="One"),
            VocabularyRecord(korean="둘", english="Two"),
            VocabularyRecord(korean="셋", english="Three")
        ]
        
        vocab_ids = []
        for vocab in vocabs:
            vocab_ids.append(db_manager.create_vocabulary(vocab))
        
        # Create tasks for some items
        db_manager.create_task(vocab_ids[0], task_type="full_pipeline")
        
        # Get pending (no tasks)
        pending = db_manager.get_pending_vocabulary(limit=10)
        assert len(pending) == 2
        korean_texts = [v.korean for v in pending]
        assert "둘" in korean_texts
        assert "셋" in korean_texts
        assert "하나" not in korean_texts
    
    # Task Management Tests
    
    def test_create_task(self, db_manager):
        """Test creating a processing task"""
        vocab = VocabularyRecord(korean="테스트", english="Test")
        vocab_id = db_manager.create_vocabulary(vocab)
        
        task_id = db_manager.create_task(
            vocabulary_id=vocab_id,
            task_type="full_pipeline",
            priority=10
        )
        
        assert task_id is not None
        
        # Verify task was created
        with db_manager.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM processing_tasks WHERE task_id = ?",
                (task_id,)
            )
            task = cursor.fetchone()
            assert task is not None
            assert task['vocabulary_id'] == vocab_id
            assert task['priority'] == 10
            assert task['status'] == 'pending'
    
    def test_update_task_status(self, db_manager):
        """Test updating task status"""
        vocab = VocabularyRecord(korean="상태", english="Status")
        vocab_id = db_manager.create_vocabulary(vocab)
        task_id = db_manager.create_task(vocab_id)
        
        # Update to processing
        db_manager.update_task_status(task_id, "processing")
        
        with db_manager.get_connection() as conn:
            cursor = conn.execute(
                "SELECT status, started_at FROM processing_tasks WHERE task_id = ?",
                (task_id,)
            )
            task = cursor.fetchone()
            assert task['status'] == 'processing'
            assert task['started_at'] is not None
        
        # Update to completed
        db_manager.update_task_status(task_id, "completed")
        
        with db_manager.get_connection() as conn:
            cursor = conn.execute(
                "SELECT status, completed_at FROM processing_tasks WHERE task_id = ?",
                (task_id,)
            )
            task = cursor.fetchone()
            assert task['status'] == 'completed'
            assert task['completed_at'] is not None
    
    def test_get_pending_tasks(self, db_manager):
        """Test retrieving pending tasks"""
        # Create vocabulary and tasks
        for i in range(5):
            vocab = VocabularyRecord(korean=f"단어{i}", english=f"Word{i}")
            vocab_id = db_manager.create_vocabulary(vocab)
            task_id = db_manager.create_task(vocab_id, priority=i)
            
            # Complete some tasks
            if i % 2 == 0:
                db_manager.update_task_status(task_id, "completed")
        
        pending = db_manager.get_pending_tasks(limit=10)
        assert len(pending) == 2  # Only odd numbered tasks are pending
        
        # Check priority ordering (highest priority first)
        assert pending[0].priority > pending[1].priority
    
    def test_retry_task(self, db_manager):
        """Test task retry mechanism"""
        vocab = VocabularyRecord(korean="재시도", english="Retry")
        vocab_id = db_manager.create_vocabulary(vocab)
        task_id = db_manager.create_task(vocab_id)
        
        # Fail the task
        db_manager.update_task_status(task_id, "failed")
        
        # Retry
        success = db_manager.retry_task(task_id)
        assert success is True
        
        with db_manager.get_connection() as conn:
            cursor = conn.execute(
                "SELECT status, retry_count FROM processing_tasks WHERE task_id = ?",
                (task_id,)
            )
            task = cursor.fetchone()
            assert task['status'] == 'pending'
            assert task['retry_count'] == 1
        
        # Test max retries
        for _ in range(3):
            db_manager.update_task_status(task_id, "failed")
            db_manager.retry_task(task_id)
        
        # Should fail after max retries
        success = db_manager.retry_task(task_id)
        assert success is False
    
    # Cache Operations Tests
    
    def test_cache_operations(self, db_manager):
        """Test cache get/save operations"""
        # Save cache entry
        db_manager.save_cache_entry(
            cache_key="test_key",
            cache_value='{"data": "test"}',
            ttl_seconds=3600
        )
        
        # Get cache entry
        value = db_manager.get_cache_entry("test_key")
        assert value is not None
        assert json.loads(value)["data"] == "test"
        
        # Test cache miss
        value = db_manager.get_cache_entry("non_existent")
        assert value is None
    
    def test_cache_expiration(self, db_manager):
        """Test cache expiration logic"""
        # Save with short TTL
        db_manager.save_cache_entry(
            cache_key="expire_test",
            cache_value="data",
            ttl_seconds=1
        )
        
        # Should exist immediately
        assert db_manager.get_cache_entry("expire_test") is not None
        
        # Manually expire it
        with db_manager.get_connection() as conn:
            conn.execute(
                "UPDATE cache_entries SET expires_at = ? WHERE cache_key = ?",
                (datetime.now() - timedelta(seconds=1), "expire_test")
            )
            conn.commit()
        
        # Should be expired
        assert db_manager.get_cache_entry("expire_test") is None
    
    def test_cleanup_expired_cache(self, db_manager):
        """Test cleanup of expired cache entries"""
        # Create expired and non-expired entries
        db_manager.save_cache_entry("keep1", "data", ttl_seconds=3600)
        db_manager.save_cache_entry("keep2", "data", ttl_seconds=3600)
        db_manager.save_cache_entry("expire1", "data", ttl_seconds=1)
        db_manager.save_cache_entry("expire2", "data", ttl_seconds=1)
        
        # Manually expire some entries
        with db_manager.get_connection() as conn:
            conn.execute(
                """UPDATE cache_entries 
                SET expires_at = ? 
                WHERE cache_key IN (?, ?)""",
                (datetime.now() - timedelta(seconds=1), "expire1", "expire2")
            )
            conn.commit()
        
        # Cleanup
        deleted = db_manager.cleanup_expired_cache()
        assert deleted == 2
        
        # Verify correct entries remain
        assert db_manager.get_cache_entry("keep1") is not None
        assert db_manager.get_cache_entry("keep2") is not None
        assert db_manager.get_cache_entry("expire1") is None
        assert db_manager.get_cache_entry("expire2") is None
    
    # Flashcard Operations Tests
    
    def test_create_flashcard(self, db_manager):
        """Test creating flashcards"""
        vocab = VocabularyRecord(korean="공부", english="Study")
        vocab_id = db_manager.create_vocabulary(vocab)
        task_id = db_manager.create_task(vocab_id)
        
        flashcard = FlashcardRecord(
            vocabulary_id=vocab_id,
            task_id=1,  # We'll use numeric ID
            card_number=1,
            deck_name="Korean Basics",
            front_content="공부",
            back_content="Study (noun/verb)",
            example_sentence="저는 한국어를 공부합니다",
            example_translation="I study Korean",
            difficulty_rating=2,
            tags='["education", "verb", "noun"]'
        )
        
        # Get numeric task ID
        with db_manager.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id FROM processing_tasks WHERE task_id = ?",
                (task_id,)
            )
            numeric_task_id = cursor.fetchone()['id']
        
        flashcard.task_id = numeric_task_id
        flashcard_id = db_manager.create_flashcard(flashcard)
        assert flashcard_id > 0
        
        # Verify creation
        with db_manager.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM flashcards WHERE id = ?",
                (flashcard_id,)
            )
            card = cursor.fetchone()
            assert card is not None
            assert card['front_content'] == "공부"
            assert card['deck_name'] == "Korean Basics"
    
    def test_export_flashcards(self, db_manager):
        """Test exporting flashcards"""
        # Create test data
        vocab1 = VocabularyRecord(korean="하나", english="One")
        vocab2 = VocabularyRecord(korean="둘", english="Two")
        vocab_id1 = db_manager.create_vocabulary(vocab1)
        vocab_id2 = db_manager.create_vocabulary(vocab2)
        
        task_id1 = db_manager.create_task(vocab_id1)
        task_id2 = db_manager.create_task(vocab_id2)
        
        # Get numeric IDs
        with db_manager.get_connection() as conn:
            cursor = conn.execute("SELECT id FROM processing_tasks WHERE task_id = ?", (task_id1,))
            num_task_id1 = cursor.fetchone()['id']
            cursor = conn.execute("SELECT id FROM processing_tasks WHERE task_id = ?", (task_id2,))
            num_task_id2 = cursor.fetchone()['id']
        
        # Create flashcards
        flashcards = [
            FlashcardRecord(
                vocabulary_id=vocab_id1,
                task_id=num_task_id1,
                front_content="하나",
                back_content="One",
                is_published=True
            ),
            FlashcardRecord(
                vocabulary_id=vocab_id2,
                task_id=num_task_id2,
                front_content="둘",
                back_content="Two",
                is_published=False  # Not published
            )
        ]
        
        for card in flashcards:
            db_manager.create_flashcard(card)
        
        # Export only published
        exported = db_manager.export_flashcards(published_only=True)
        assert len(exported) == 1
        assert exported[0].front_content == "하나"
        
        # Export all
        exported = db_manager.export_flashcards(published_only=False)
        assert len(exported) == 2
    
    def test_publish_flashcards(self, db_manager):
        """Test publishing flashcards"""
        vocab = VocabularyRecord(korean="출판", english="Publish")
        vocab_id = db_manager.create_vocabulary(vocab)
        task_id = db_manager.create_task(vocab_id)
        
        # Get numeric task ID
        with db_manager.get_connection() as conn:
            cursor = conn.execute("SELECT id FROM processing_tasks WHERE task_id = ?", (task_id,))
            num_task_id = cursor.fetchone()['id']
        
        # Create unpublished flashcards
        card_ids = []
        for i in range(3):
            card = FlashcardRecord(
                vocabulary_id=vocab_id,
                task_id=num_task_id,
                card_number=i+1,
                front_content=f"Card {i+1}",
                back_content=f"Back {i+1}"
            )
            card_ids.append(db_manager.create_flashcard(card))
        
        # Publish them
        count = db_manager.publish_flashcards(card_ids)
        assert count == 3
        
        # Verify they're published
        with db_manager.get_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM flashcards WHERE id IN ({}) AND is_published = 1".format(
                    ','.join('?' * len(card_ids))
                ),
                card_ids
            )
            assert cursor.fetchone()[0] == 3
    
    # Metrics Operations Tests
    
    def test_record_api_usage(self, db_manager):
        """Test recording API usage metrics"""
        vocab = VocabularyRecord(korean="API", english="API")
        vocab_id = db_manager.create_vocabulary(vocab)
        task_id = db_manager.create_task(vocab_id)
        
        # Get numeric task ID
        with db_manager.get_connection() as conn:
            cursor = conn.execute("SELECT id FROM processing_tasks WHERE task_id = ?", (task_id,))
            num_task_id = cursor.fetchone()['id']
        
        # Record API usage
        db_manager.record_api_usage(
            task_id=num_task_id,
            api_name="openrouter",
            endpoint="/chat/completions",
            response_time_ms=250,
            status_code=200,
            tokens_used=150,
            cost_estimate=0.0025
        )
        
        # Verify recording
        with db_manager.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM api_usage WHERE task_id = ?",
                (num_task_id,)
            )
            usage = cursor.fetchone()
            assert usage is not None
            assert usage['api_name'] == "openrouter"
            assert usage['tokens_used'] == 150
            assert usage['cost_estimate'] == 0.0025
    
    def test_record_processing_performance(self, db_manager):
        """Test recording processing performance metrics"""
        vocab = VocabularyRecord(korean="성능", english="Performance")
        vocab_id = db_manager.create_vocabulary(vocab)
        task_id = db_manager.create_task(vocab_id)
        
        # Get numeric task ID
        with db_manager.get_connection() as conn:
            cursor = conn.execute("SELECT id FROM processing_tasks WHERE task_id = ?", (task_id,))
            num_task_id = cursor.fetchone()['id']
        
        # Record performance
        db_manager.record_processing_performance(
            task_id=num_task_id,
            stage_name="nuance_creator",
            duration_ms=1500,
            status="success"
        )
        
        # Verify recording
        with db_manager.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM processing_metrics WHERE task_id = ?",
                (num_task_id,)
            )
            metric = cursor.fetchone()
            assert metric is not None
            assert metric['stage_name'] == "nuance_creator"
            assert metric['duration_ms'] == 1500
            assert metric['status'] == "success"
    
    def test_get_daily_metrics(self, db_manager):
        """Test retrieving daily metrics"""
        # Create test data for today
        vocab = VocabularyRecord(korean="오늘", english="Today")
        vocab_id = db_manager.create_vocabulary(vocab)
        
        # Create multiple tasks
        for i in range(3):
            task_id = db_manager.create_task(vocab_id)
            with db_manager.get_connection() as conn:
                cursor = conn.execute("SELECT id FROM processing_tasks WHERE task_id = ?", (task_id,))
                num_task_id = cursor.fetchone()['id']
                
                # Record API usage
                db_manager.record_api_usage(
                    task_id=num_task_id,
                    api_name="openrouter",
                    endpoint="/chat/completions",
                    response_time_ms=200 + i * 50,
                    status_code=200,
                    tokens_used=100 + i * 50,
                    cost_estimate=0.002 + i * 0.001
                )
        
        # Get today's metrics
        metrics = db_manager.get_daily_metrics(datetime.now().date())
        
        assert metrics['total_api_calls'] == 3
        assert metrics['total_tokens_used'] == 450  # 100 + 150 + 200
        assert metrics['total_cost'] == pytest.approx(0.009, rel=0.01)  # 0.002 + 0.003 + 0.004
        assert metrics['average_response_time'] == pytest.approx(250.0, rel=0.01)  # (200 + 250 + 300) / 3
    
    # System Operations Tests
    
    def test_get_configuration(self, db_manager):
        """Test configuration management"""
        # Set a configuration value
        db_manager.set_configuration("test_key", "test_value", "Test description")
        
        # Get configuration
        value = db_manager.get_configuration("test_key")
        assert value == "test_value"
        
        # Get non-existent key with default
        value = db_manager.get_configuration("missing_key", default="default")
        assert value == "default"
    
    def test_set_configuration(self, db_manager):
        """Test setting configuration values"""
        # Set new value
        db_manager.set_configuration("api_timeout", "30", "API timeout in seconds")
        
        # Update existing value
        db_manager.set_configuration("api_timeout", "60", "Updated API timeout")
        
        # Verify update
        value = db_manager.get_configuration("api_timeout")
        assert value == "60"
        
        # Check description was updated
        with db_manager.get_connection() as conn:
            cursor = conn.execute(
                "SELECT description FROM system_configuration WHERE key = ?",
                ("api_timeout",)
            )
            desc = cursor.fetchone()['description']
            assert desc == "Updated API timeout"
    
    def test_get_database_stats(self, db_manager):
        """Test database statistics retrieval"""
        # Create test data
        for i in range(5):
            vocab = VocabularyRecord(korean=f"단어{i}", english=f"Word{i}")
            vocab_id = db_manager.create_vocabulary(vocab)
            
            if i < 3:  # Create tasks for first 3
                task_id = db_manager.create_task(vocab_id)
                
                if i < 2:  # Create flashcards for first 2
                    with db_manager.get_connection() as conn:
                        cursor = conn.execute("SELECT id FROM processing_tasks WHERE task_id = ?", (task_id,))
                        num_task_id = cursor.fetchone()['id']
                    
                    card = FlashcardRecord(
                        vocabulary_id=vocab_id,
                        task_id=num_task_id,
                        front_content=f"Front {i}",
                        back_content=f"Back {i}"
                    )
                    db_manager.create_flashcard(card)
        
        # Get stats
        stats = db_manager.get_database_stats()
        
        assert stats['total_vocabulary'] == 5
        assert stats['total_tasks'] == 3
        assert stats['pending_tasks'] == 3
        assert stats['completed_tasks'] == 0
        assert stats['total_flashcards'] == 2
        assert stats['published_flashcards'] == 0
        assert stats['cache_entries'] == 0
        assert 'database_size_mb' in stats
    
    # Error Handling Tests
    
    def test_duplicate_vocabulary(self, db_manager):
        """Test handling duplicate vocabulary entries"""
        vocab = VocabularyRecord(korean="중복", english="Duplicate")
        db_manager.create_vocabulary(vocab)
        
        # Try to create duplicate
        with pytest.raises(sqlite3.IntegrityError):
            db_manager.create_vocabulary(vocab)
    
    def test_invalid_task_vocabulary(self, db_manager):
        """Test creating task with invalid vocabulary ID"""
        with pytest.raises(sqlite3.IntegrityError):
            db_manager.create_task(vocabulary_id=99999)  # Non-existent ID
    
    def test_transaction_rollback(self, db_manager):
        """Test transaction rollback on error"""
        vocab = VocabularyRecord(korean="트랜잭션", english="Transaction")
        vocab_id = db_manager.create_vocabulary(vocab)
        
        # Try to create flashcard with invalid task_id
        card = FlashcardRecord(
            vocabulary_id=vocab_id,
            task_id=99999,  # Invalid
            front_content="Front",
            back_content="Back"
        )
        
        with pytest.raises(sqlite3.IntegrityError):
            db_manager.create_flashcard(card)
        
        # Verify no partial data was saved
        with db_manager.get_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM flashcards WHERE vocabulary_id = ?",
                (vocab_id,)
            )
            assert cursor.fetchone()[0] == 0


class TestDatabaseManagerIntegration:
    """Integration tests for DatabaseManager"""
    
    def test_full_pipeline_flow(self, db_manager):
        """Test complete pipeline flow from vocabulary to flashcard"""
        # 1. Create vocabulary
        vocab = VocabularyRecord(
            korean="통합테스트",
            english="Integration Test",
            type="noun",
            category="technology",
            difficulty_level=3
        )
        vocab_id = db_manager.create_vocabulary(vocab)
        
        # 2. Create processing task
        task_id = db_manager.create_task(
            vocabulary_id=vocab_id,
            task_type="full_pipeline",
            priority=10
        )
        
        # 3. Get pending task
        pending = db_manager.get_pending_tasks(limit=1)
        assert len(pending) == 1
        assert pending[0].vocabulary_id == vocab_id
        
        # 4. Update task status
        db_manager.update_task_status(task_id, "processing")
        
        # 5. Record API usage
        with db_manager.get_connection() as conn:
            cursor = conn.execute("SELECT id FROM processing_tasks WHERE task_id = ?", (task_id,))
            num_task_id = cursor.fetchone()['id']
        
        db_manager.record_api_usage(
            task_id=num_task_id,
            api_name="openrouter",
            endpoint="/chat/completions",
            response_time_ms=350,
            status_code=200,
            tokens_used=250,
            cost_estimate=0.005
        )
        
        # 6. Create flashcards
        flashcards = []
        for i in range(3):
            card = FlashcardRecord(
                vocabulary_id=vocab_id,
                task_id=num_task_id,
                card_number=i+1,
                deck_name="Integration Test Deck",
                front_content=f"통합테스트 - Card {i+1}",
                back_content=f"Integration Test - Definition {i+1}",
                example_sentence="이것은 통합테스트입니다.",
                example_translation="This is an integration test.",
                difficulty_rating=3,
                tags='["technology", "testing", "noun"]'
            )
            card_id = db_manager.create_flashcard(card)
            flashcards.append(card_id)
        
        # 7. Record performance
        db_manager.record_processing_performance(
            task_id=num_task_id,
            stage_name="full_pipeline",
            duration_ms=2500,
            status="success"
        )
        
        # 8. Complete task
        db_manager.update_task_status(task_id, "completed")
        
        # 9. Publish flashcards
        published = db_manager.publish_flashcards(flashcards)
        assert published == 3
        
        # 10. Export flashcards
        exported = db_manager.export_flashcards(published_only=True)
        assert len(exported) == 3
        assert all(card.is_published for card in exported)
        
        # 11. Get metrics
        metrics = db_manager.get_daily_metrics(datetime.now().date())
        assert metrics['total_api_calls'] >= 1
        assert metrics['total_tokens_used'] >= 250
        assert metrics['total_cost'] >= 0.005
    
    def test_concurrent_task_processing(self, db_manager):
        """Test handling concurrent task processing"""
        # Create multiple vocabulary items
        vocab_items = []
        for i in range(5):
            vocab = VocabularyRecord(korean=f"동시처리{i}", english=f"Concurrent{i}")
            vocab_id = db_manager.create_vocabulary(vocab)
            vocab_items.append(vocab_id)
        
        # Create tasks for all items
        task_ids = []
        for vocab_id in vocab_items:
            task_id = db_manager.create_task(vocab_id, priority=5)
            task_ids.append(task_id)
        
        # Simulate concurrent processing
        for i, task_id in enumerate(task_ids):
            if i % 2 == 0:
                db_manager.update_task_status(task_id, "processing")
        
        # Get pending tasks (should be odd numbered ones)
        pending = db_manager.get_pending_tasks(limit=10)
        assert len(pending) == 2
        
        # Complete all tasks
        for task_id in task_ids:
            db_manager.update_task_status(task_id, "completed")
        
        # Verify all completed
        pending = db_manager.get_pending_tasks(limit=10)
        assert len(pending) == 0
    
    def test_cache_performance(self, db_manager):
        """Test cache performance with multiple entries"""
        # Create many cache entries
        for i in range(100):
            db_manager.save_cache_entry(
                cache_key=f"perf_test_{i}",
                cache_value=f'{{"data": "value_{i}"}}',
                ttl_seconds=3600 if i % 2 == 0 else 1
            )
        
        # Test retrieval performance
        import time
        start = time.time()
        for i in range(100):
            value = db_manager.get_cache_entry(f"perf_test_{i}")
            assert value is not None
        end = time.time()
        
        # Should be fast (< 1ms per retrieval on average)
        assert (end - start) / 100 < 0.001
        
        # Expire half the entries
        with db_manager.get_connection() as conn:
            conn.execute(
                """UPDATE cache_entries 
                SET expires_at = ? 
                WHERE cache_key LIKE 'perf_test_%' 
                AND ttl_seconds = 1""",
                (datetime.now() - timedelta(seconds=1),)
            )
            conn.commit()
        
        # Cleanup
        deleted = db_manager.cleanup_expired_cache()
        assert deleted == 50
        
        # Verify correct entries remain
        for i in range(100):
            value = db_manager.get_cache_entry(f"perf_test_{i}")
            if i % 2 == 0:
                assert value is not None
            else:
                assert value is None