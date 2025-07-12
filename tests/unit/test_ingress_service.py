"""
Unit tests for enhanced ingress service.
"""

import pytest
import tempfile
import csv
from pathlib import Path
from datetime import datetime
import json

from flashcard_pipeline.ingress_service_enhanced import (
    IngressServiceEnhanced,
    CSVValidator,
    DuplicateDetector,
    ImportProgress,
    ImportBatch
)
from flashcard_pipeline.database import EnhancedDatabaseManager, ValidatedDatabaseManager, PoolConfig
from flashcard_pipeline.exceptions import IngressError, ValidationError


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    fd, path = tempfile.mkstemp(suffix='.db')
    
    # Initialize with schema
    db_manager = EnhancedDatabaseManager(
        db_path=path,
        pool_config=PoolConfig(min_connections=1, max_connections=2)
    )
    
    # Run migrations to create schema
    with db_manager.get_connection() as conn:
        # Create minimal schema for testing
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vocabulary_master (
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
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS import_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_id TEXT UNIQUE NOT NULL,
                source_file TEXT NOT NULL,
                source_type TEXT DEFAULT 'csv',
                total_items INTEGER DEFAULT 0,
                imported_items INTEGER DEFAULT 0,
                duplicate_items INTEGER DEFAULT 0,
                failed_items INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vocabulary_imports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vocabulary_id INTEGER NOT NULL,
                import_id INTEGER NOT NULL,
                original_position INTEGER,
                import_status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vocabulary_id) REFERENCES vocabulary_master(id),
                FOREIGN KEY (import_id) REFERENCES import_operations(id)
            )
        """)
        
        conn.commit()
    
    yield path
    
    # Cleanup
    db_manager.close()
    import os
    os.unlink(path)


@pytest.fixture
def ingress_service(temp_db):
    """Create ingress service with test database"""
    db_manager = EnhancedDatabaseManager(
        db_path=temp_db,
        pool_config=PoolConfig(min_connections=1, max_connections=2)
    )
    validated_db = ValidatedDatabaseManager(db_manager)
    service = IngressServiceEnhanced(validated_db)
    
    yield service
    
    # Cleanup
    service.close()
    db_manager.close()


@pytest.fixture
def sample_csv():
    """Create sample CSV file for testing"""
    fd, path = tempfile.mkstemp(suffix='.csv')
    
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['term', 'meaning', 'type', 'level'])
        writer.writeheader()
        writer.writerows([
            {'term': '안녕하세요', 'meaning': 'Hello', 'type': 'phrase', 'level': '1'},
            {'term': '감사합니다', 'meaning': 'Thank you', 'type': 'phrase', 'level': '1'},
            {'term': '사랑', 'meaning': 'Love', 'type': 'noun', 'level': '2'},
            {'term': '공부하다', 'meaning': 'To study', 'type': 'verb', 'level': '2'},
            {'term': '한국어', 'meaning': 'Korean language', 'type': 'noun', 'level': '1'},
        ])
    
    yield path
    
    # Cleanup
    import os
    os.unlink(path)


class TestCSVValidator:
    """Test CSV validation functionality"""
    
    def test_detect_encoding(self, tmp_path):
        """Test encoding detection"""
        # Create UTF-8 file
        utf8_file = tmp_path / "utf8.csv"
        utf8_file.write_text("term,meaning\n안녕,hello", encoding='utf-8')
        
        validator = CSVValidator()
        encoding = validator.detect_encoding(utf8_file)
        assert encoding in ['utf-8', 'UTF-8', 'ascii']
    
    def test_normalize_headers(self):
        """Test header normalization"""
        validator = CSVValidator()
        
        # Test various header formats
        headers = ['Term', 'English', 'POS', 'difficulty']
        mapping = validator.normalize_headers(headers)
        
        assert mapping['Term'] == 'term'
        assert mapping['English'] == 'meaning'
        assert mapping['POS'] == 'pos'
        assert mapping['difficulty'] == 'level'
    
    def test_validate_headers(self):
        """Test header validation"""
        validator = CSVValidator()
        
        # Valid headers
        valid, msg = validator.validate_headers(['term', 'meaning', 'type'])
        assert valid is True
        assert msg is None
        
        # Missing required column
        valid, msg = validator.validate_headers(['meaning', 'type'])
        assert valid is False
        assert 'Missing required columns: term' in msg
    
    def test_validate_row(self):
        """Test row validation"""
        validator = CSVValidator()
        validator.normalize_headers(['term', 'meaning', 'level'])
        
        # Valid row
        valid, error, data = validator.validate_row({
            'term': '안녕',
            'meaning': 'Hello',
            'level': '1'
        }, 1)
        
        assert valid is True
        assert error is None
        assert data['korean'] == '안녕'
        assert data['english'] == 'Hello'
        assert data['difficulty_level'] == 1
        
        # Invalid level
        valid, error, data = validator.validate_row({
            'term': '안녕',
            'meaning': 'Hello',
            'level': '15'
        }, 2)
        
        assert valid is False
        assert 'Difficulty level must be 1-10' in error
        
        # Missing term
        valid, error, data = validator.validate_row({
            'meaning': 'Hello',
            'level': '1'
        }, 3)
        
        assert valid is False
        assert "Missing required field 'term'" in error


class TestDuplicateDetector:
    """Test duplicate detection functionality"""
    
    def test_term_normalization(self):
        """Test Korean term normalization"""
        detector = DuplicateDetector()
        
        # Korean with spaces
        normalized = detector._normalize_korean("안녕 하세요")
        assert normalized == "안녕하세요"
        
        # Mixed case
        normalized = detector._normalize_korean("HELLO")
        assert normalized == "hello"
    
    def test_duplicate_detection(self):
        """Test duplicate detection"""
        detector = DuplicateDetector()
        
        # First item - not duplicate
        is_dup, reason, id = detector.check_duplicate({
            'korean': '안녕하세요',
            'english': 'Hello',
            'type': 'phrase'
        })
        assert is_dup is False
        
        # Add to index
        detector.add_item(1, {
            'korean': '안녕하세요',
            'english': 'Hello',
            'type': 'phrase'
        })
        
        # Exact duplicate
        is_dup, reason, id = detector.check_duplicate({
            'korean': '안녕하세요',
            'english': 'Hello',
            'type': 'phrase'
        })
        assert is_dup is True
        assert 'Exact duplicate' in reason
        
        # Same term, different meaning
        is_dup, reason, id = detector.check_duplicate({
            'korean': '안녕하세요',
            'english': 'Goodbye',
            'type': 'phrase'
        })
        assert is_dup is True
        assert 'already exists with different meaning' in reason
    
    def test_load_existing_vocabulary(self, ingress_service):
        """Test loading existing vocabulary"""
        # Add some vocabulary
        with ingress_service.db_manager.db_manager.get_connection() as conn:
            conn.execute("""
                INSERT INTO vocabulary_master (korean, english, type)
                VALUES (?, ?, ?)
            """, ('테스트', 'Test', 'noun'))
            conn.commit()
        
        # Load existing
        detector = DuplicateDetector()
        detector.load_existing_vocabulary(ingress_service.db_manager)
        
        # Check if loaded
        is_dup, reason, id = detector.check_duplicate({
            'korean': '테스트',
            'english': 'Test',
            'type': 'noun'
        })
        assert is_dup is True


class TestImportProgress:
    """Test import progress tracking"""
    
    def test_progress_calculation(self):
        """Test progress calculations"""
        progress = ImportProgress(total_rows=100)
        progress.processed_rows = 50
        progress.successful_rows = 45
        progress.failed_rows = 5
        
        assert progress.progress_percentage == 50.0
        
        # Test rate calculation
        import time
        time.sleep(0.1)
        assert progress.rows_per_second > 0
        assert progress.estimated_remaining_seconds > 0
    
    def test_progress_serialization(self):
        """Test progress serialization"""
        progress = ImportProgress(total_rows=100)
        progress.processed_rows = 50
        
        data = progress.to_dict()
        assert data['total_rows'] == 100
        assert data['processed_rows'] == 50
        assert 'elapsed_seconds' in data
        assert 'progress_percentage' in data


class TestIngressService:
    """Test main ingress service functionality"""
    
    def test_create_import_batch(self, ingress_service):
        """Test batch creation"""
        batch_id = ingress_service.create_import_batch("test.csv", {"test": "metadata"})
        
        assert batch_id.startswith("import_")
        assert batch_id in ingress_service.active_batches
        
        # Check database
        batch = ingress_service.get_batch_status(batch_id)
        assert batch is not None
        assert batch.source_file == "test.csv"
        assert batch.metadata["test"] == "metadata"
    
    def test_import_csv_success(self, ingress_service, sample_csv):
        """Test successful CSV import"""
        batch = ingress_service.import_csv(sample_csv, batch_size=2)
        
        assert batch.status == "completed"
        assert batch.progress.total_rows == 5
        assert batch.progress.successful_rows == 5
        assert batch.progress.failed_rows == 0
        
        # Check vocabulary was created
        with ingress_service.db_manager.db_manager.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM vocabulary_master")
            count = cursor.fetchone()[0]
            assert count == 5
    
    def test_import_csv_with_duplicates(self, ingress_service, sample_csv):
        """Test import with duplicate detection"""
        # First import
        batch1 = ingress_service.import_csv(sample_csv)
        assert batch1.progress.successful_rows == 5
        
        # Second import - all should be duplicates
        batch2 = ingress_service.import_csv(sample_csv, skip_duplicates=True)
        assert batch2.progress.successful_rows == 0
        assert batch2.progress.duplicate_rows == 5
    
    def test_import_csv_validation_only(self, ingress_service, sample_csv):
        """Test validation-only mode"""
        batch = ingress_service.import_csv(sample_csv, validate_only=True)
        
        assert batch.status == "completed"
        assert batch.progress.successful_rows == 5
        
        # Check no vocabulary was created
        with ingress_service.db_manager.db_manager.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM vocabulary_master")
            count = cursor.fetchone()[0]
            assert count == 0
    
    def test_import_csv_with_errors(self, ingress_service, tmp_path):
        """Test import with validation errors"""
        # Create CSV with errors
        error_csv = tmp_path / "errors.csv"
        with open(error_csv, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['term', 'meaning', 'level'])
            writer.writeheader()
            writer.writerows([
                {'term': '안녕', 'meaning': 'Hello', 'level': '1'},
                {'term': '', 'meaning': 'Empty term', 'level': '1'},  # Error
                {'term': '테스트', 'meaning': 'Test', 'level': '20'},  # Error - invalid level
                {'term': '좋아', 'meaning': 'Good', 'level': '2'},
            ])
        
        batch = ingress_service.import_csv(str(error_csv))
        
        assert batch.status == "partial"
        assert batch.progress.successful_rows == 2
        assert batch.progress.failed_rows == 2
        assert len(batch.progress.validation_errors) == 2
    
    def test_progress_callback(self, ingress_service, sample_csv):
        """Test progress callback"""
        progress_updates = []
        
        def callback(progress):
            progress_updates.append({
                'processed': progress.processed_rows,
                'successful': progress.successful_rows
            })
        
        batch = ingress_service.import_csv(sample_csv, progress_callback=callback)
        
        assert len(progress_updates) > 0
        assert progress_updates[-1]['processed'] == 5
        assert progress_updates[-1]['successful'] == 5
    
    def test_cancel_batch(self, ingress_service):
        """Test batch cancellation"""
        batch_id = ingress_service.create_import_batch("test.csv")
        batch = ingress_service.active_batches[batch_id]
        batch.status = "processing"
        
        # Cancel
        result = ingress_service.cancel_batch(batch_id)
        assert result is True
        assert batch.status == "cancelled"
        
        # Can't cancel completed batch
        batch.status = "completed"
        result = ingress_service.cancel_batch(batch_id)
        assert result is False
    
    def test_list_batches(self, ingress_service, sample_csv):
        """Test listing batches"""
        # Import some batches
        batch1 = ingress_service.import_csv(sample_csv)
        batch2 = ingress_service.import_csv(sample_csv)
        
        # List all
        batches = ingress_service.list_batches()
        assert len(batches) >= 2
        
        # List by status
        completed = ingress_service.list_batches(status="completed")
        assert all(b.status == "completed" for b in completed)
    
    def test_retry_failed_items(self, ingress_service, tmp_path):
        """Test retrying failed items"""
        # Create CSV with errors
        error_csv = tmp_path / "retry_test.csv"
        with open(error_csv, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['term', 'meaning'])
            writer.writeheader()
            writer.writerows([
                {'term': '안녕', 'meaning': 'Hello'},
                {'term': '', 'meaning': 'Empty term'},  # Will fail
                {'term': '테스트', 'meaning': 'Test'},
            ])
        
        # First import
        batch1 = ingress_service.import_csv(str(error_csv))
        assert batch1.progress.failed_rows == 1
        
        # Fix the data in memory (simulated)
        # In real scenario, user would fix the CSV
        
        # Retry - should fail again since data not actually fixed
        retry_batch = ingress_service.retry_failed_items(batch1.batch_id)
        assert retry_batch.progress.total_rows == 1
        assert retry_batch.progress.failed_rows == 1
    
    def test_export_batch_report(self, ingress_service, sample_csv, tmp_path):
        """Test batch report export"""
        batch = ingress_service.import_csv(sample_csv)
        
        report_path = ingress_service.export_batch_report(
            batch.batch_id,
            str(tmp_path / "report.json")
        )
        
        assert Path(report_path).exists()
        
        # Load and verify report
        with open(report_path, 'r') as f:
            report = json.load(f)
        
        assert report['batch']['batch_id'] == batch.batch_id
        assert report['summary']['total_items'] == 5
        assert report['summary']['successful'] == 5
    
    def test_cleanup_old_batches(self, ingress_service, sample_csv):
        """Test cleanup of old batches"""
        # Import a batch
        batch = ingress_service.import_csv(sample_csv)
        
        # Cleanup with 0 days (should delete all completed)
        deleted = ingress_service.cleanup_old_batches(days=0)
        assert deleted >= 1
        
        # Batch should be gone
        batch_status = ingress_service.get_batch_status(batch.batch_id)
        assert batch_status is None


class TestImportBatch:
    """Test ImportBatch dataclass"""
    
    def test_batch_serialization(self):
        """Test batch serialization"""
        batch = ImportBatch(
            batch_id="test_123",
            source_file="test.csv",
            total_items=100
        )
        batch.progress.processed_rows = 50
        
        data = batch.to_dict()
        assert data['batch_id'] == "test_123"
        assert data['source_file'] == "test.csv"
        assert data['progress']['processed_rows'] == 50


# Integration test
@pytest.mark.integration
class TestIngressIntegration:
    """Integration tests for ingress service"""
    
    async def test_concurrent_import(self, ingress_service, sample_csv):
        """Test concurrent import functionality"""
        # This would test the async import method
        batch = await ingress_service.import_csv_async(sample_csv)
        assert batch.status == "completed"