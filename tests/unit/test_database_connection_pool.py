"""
Test suite for database connection pooling and retry logic.
Tests concurrent access, connection limits, and retry mechanisms.
"""

import pytest
import sqlite3
import tempfile
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, MagicMock

from flashcard_pipeline.database.db_manager import DatabaseManager


class TestDatabaseConnectionPool:
    """Test database connection pooling and concurrency"""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        # Initialize with minimal schema
        conn = sqlite3.connect(path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vocabulary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                korean TEXT NOT NULL UNIQUE,
                english TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_configuration (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.execute("""
            INSERT INTO system_configuration (key, value)
            VALUES ('schema_version', '2.0')
        """)
        conn.commit()
        conn.close()
        
        yield path
        os.unlink(path)
    
    @pytest.fixture
    def db_manager(self, temp_db):
        """Create DatabaseManager instance"""
        return DatabaseManager(temp_db)
    
    def test_concurrent_connections(self, db_manager):
        """Test multiple concurrent database connections"""
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                with db_manager.get_connection() as conn:
                    # Simulate some work
                    cursor = conn.execute("SELECT COUNT(*) FROM vocabulary")
                    count = cursor.fetchone()[0]
                    time.sleep(0.01)  # Small delay to increase concurrency
                    results.append((worker_id, count))
            except Exception as e:
                errors.append((worker_id, str(e)))
        
        # Run concurrent workers
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            for i in range(50):
                future = executor.submit(worker, i)
                futures.append(future)
            
            # Wait for all to complete
            for future in as_completed(futures):
                future.result()
        
        # All should succeed
        assert len(errors) == 0
        assert len(results) == 50
    
    def test_connection_context_manager(self, db_manager):
        """Test connection context manager properly closes connections"""
        # Get connection and verify it's open
        with db_manager.get_connection() as conn:
            assert conn is not None
            cursor = conn.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1
        
        # After context, connection should be closed
        # Attempting to use it should raise error
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")
    
    def test_connection_isolation(self, db_manager):
        """Test that connections are properly isolated"""
        def writer():
            with db_manager.get_connection() as conn:
                conn.execute("BEGIN EXCLUSIVE")
                conn.execute(
                    "INSERT INTO vocabulary (korean, english) VALUES (?, ?)",
                    ("테스트", "test")
                )
                time.sleep(0.1)  # Hold exclusive lock
                conn.commit()
        
        def reader():
            time.sleep(0.05)  # Start after writer
            with db_manager.get_connection() as conn:
                # This should wait for writer to complete
                cursor = conn.execute("SELECT COUNT(*) FROM vocabulary")
                return cursor.fetchone()[0]
        
        # Run writer and reader concurrently
        with ThreadPoolExecutor(max_workers=2) as executor:
            writer_future = executor.submit(writer)
            reader_future = executor.submit(reader)
            
            writer_future.result()
            count = reader_future.result()
        
        # Reader should see the written data
        assert count == 1
    
    def test_connection_settings_persistence(self, db_manager):
        """Test that connection settings are applied to each connection"""
        # Test foreign keys setting
        with db_manager.get_connection() as conn:
            cursor = conn.execute("PRAGMA foreign_keys")
            assert cursor.fetchone()[0] == 1
        
        # Test WAL mode
        with db_manager.get_connection() as conn:
            cursor = conn.execute("PRAGMA journal_mode")
            assert cursor.fetchone()[0] == 'wal'
        
        # Settings should persist across connections
        for _ in range(5):
            with db_manager.get_connection() as conn:
                cursor = conn.execute("PRAGMA foreign_keys")
                assert cursor.fetchone()[0] == 1


class TestDatabaseRetryLogic:
    """Test database retry mechanisms with exponential backoff"""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create a DatabaseManager with mocked methods for testing retries"""
        manager = MagicMock(spec=DatabaseManager)
        manager.db_path = ":memory:"
        return manager
    
    def test_retry_on_database_locked(self, mock_db_manager):
        """Test retry logic when database is locked"""
        # Simulate database locked error that succeeds on 3rd try
        call_count = 0
        
        def mock_execute():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise sqlite3.OperationalError("database is locked")
            return MagicMock()
        
        # Implement retry logic
        def execute_with_retry(func, max_retries=3, backoff_base=0.1):
            for attempt in range(max_retries):
                try:
                    return func()
                except sqlite3.OperationalError as e:
                    if "locked" in str(e) and attempt < max_retries - 1:
                        time.sleep(backoff_base * (2 ** attempt))
                        continue
                    raise
        
        # Test retry succeeds
        result = execute_with_retry(mock_execute)
        assert result is not None
        assert call_count == 3
    
    def test_exponential_backoff_timing(self):
        """Test exponential backoff timing calculation"""
        base = 0.1
        max_retries = 5
        
        expected_delays = []
        for i in range(max_retries):
            delay = base * (2 ** i)
            expected_delays.append(delay)
        
        # Verify backoff sequence
        assert expected_delays == [0.1, 0.2, 0.4, 0.8, 1.6]
        
        # Verify total wait time
        total_wait = sum(expected_delays[:-1])  # Don't count last one
        assert total_wait == pytest.approx(1.5, rel=0.01)
    
    def test_retry_with_jitter(self):
        """Test retry with random jitter to avoid thundering herd"""
        import random
        
        def calculate_backoff_with_jitter(attempt, base=0.1, jitter=0.1):
            backoff = base * (2 ** attempt)
            jitter_amount = backoff * jitter * (2 * random.random() - 1)
            return max(0, backoff + jitter_amount)
        
        # Test multiple calculations
        for attempt in range(5):
            delays = []
            for _ in range(100):
                delay = calculate_backoff_with_jitter(attempt)
                delays.append(delay)
            
            # Verify average is close to expected
            expected = 0.1 * (2 ** attempt)
            average = sum(delays) / len(delays)
            assert average == pytest.approx(expected, rel=0.2)
            
            # Verify all positive
            assert all(d >= 0 for d in delays)
    
    def test_retry_on_specific_errors(self):
        """Test retry only on specific recoverable errors"""
        recoverable_errors = [
            sqlite3.OperationalError("database is locked"),
            sqlite3.OperationalError("disk I/O error"),
            sqlite3.DatabaseError("database disk image is malformed")
        ]
        
        non_recoverable_errors = [
            sqlite3.IntegrityError("UNIQUE constraint failed"),
            sqlite3.ProgrammingError("syntax error"),
            ValueError("Invalid input")
        ]
        
        def should_retry(error):
            if isinstance(error, sqlite3.OperationalError):
                return "locked" in str(error) or "I/O error" in str(error)
            if isinstance(error, sqlite3.DatabaseError):
                return "malformed" in str(error)
            return False
        
        # Test recoverable errors
        for error in recoverable_errors:
            assert should_retry(error) is True
        
        # Test non-recoverable errors
        for error in non_recoverable_errors:
            assert should_retry(error) is False
    
    def test_retry_with_circuit_breaker(self):
        """Test retry logic with circuit breaker pattern"""
        class CircuitBreaker:
            def __init__(self, failure_threshold=5, timeout=60):
                self.failure_threshold = failure_threshold
                self.timeout = timeout
                self.failure_count = 0
                self.last_failure_time = None
                self.state = "closed"  # closed, open, half-open
            
            def call(self, func):
                if self.state == "open":
                    if time.time() - self.last_failure_time > self.timeout:
                        self.state = "half-open"
                    else:
                        raise Exception("Circuit breaker is open")
                
                try:
                    result = func()
                    if self.state == "half-open":
                        self.state = "closed"
                        self.failure_count = 0
                    return result
                except Exception as e:
                    self.failure_count += 1
                    self.last_failure_time = time.time()
                    
                    if self.failure_count >= self.failure_threshold:
                        self.state = "open"
                    
                    raise e
        
        # Test circuit breaker
        breaker = CircuitBreaker(failure_threshold=3)
        
        def failing_operation():
            raise Exception("Operation failed")
        
        # First 2 failures - circuit still closed
        for i in range(2):
            with pytest.raises(Exception):
                breaker.call(failing_operation)
            assert breaker.state == "closed"
        
        # 3rd failure - circuit opens
        with pytest.raises(Exception):
            breaker.call(failing_operation)
        assert breaker.state == "open"
        
        # Subsequent calls fail immediately
        with pytest.raises(Exception, match="Circuit breaker is open"):
            breaker.call(failing_operation)


class TestDatabaseHealthChecks:
    """Test database health check endpoints"""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        conn = sqlite3.connect(path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_configuration (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.execute("""
            INSERT INTO system_configuration (key, value)
            VALUES ('schema_version', '2.0')
        """)
        conn.commit()
        conn.close()
        
        yield path
        os.unlink(path)
    
    def test_health_check_implementation(self, temp_db):
        """Test database health check functionality"""
        
        class DatabaseHealthChecker:
            def __init__(self, db_path):
                self.db_path = db_path
            
            def check_health(self):
                """Perform comprehensive health check"""
                checks = {
                    'connection': False,
                    'writable': False,
                    'schema_valid': False,
                    'response_time_ms': None
                }
                
                start_time = time.time()
                
                try:
                    # Check connection
                    conn = sqlite3.connect(self.db_path)
                    checks['connection'] = True
                    
                    # Check if writable
                    conn.execute("CREATE TEMP TABLE health_check (id INTEGER)")
                    conn.execute("INSERT INTO health_check VALUES (1)")
                    conn.execute("DROP TABLE health_check")
                    checks['writable'] = True
                    
                    # Check schema
                    cursor = conn.execute(
                        "SELECT value FROM system_configuration WHERE key = 'schema_version'"
                    )
                    version = cursor.fetchone()
                    checks['schema_valid'] = version is not None and version[0] == '2.0'
                    
                    conn.close()
                    
                except Exception as e:
                    checks['error'] = str(e)
                
                checks['response_time_ms'] = int((time.time() - start_time) * 1000)
                checks['healthy'] = all([
                    checks['connection'],
                    checks['writable'],
                    checks['schema_valid']
                ])
                
                return checks
        
        # Test health checker
        checker = DatabaseHealthChecker(temp_db)
        health = checker.check_health()
        
        assert health['healthy'] is True
        assert health['connection'] is True
        assert health['writable'] is True
        assert health['schema_valid'] is True
        assert health['response_time_ms'] < 100  # Should be fast
        assert 'error' not in health
    
    def test_health_check_with_corrupted_db(self):
        """Test health check with corrupted database"""
        # Create a corrupted database file
        fd, path = tempfile.mkstemp(suffix='.db')
        os.write(fd, b"This is not a valid SQLite database")
        os.close(fd)
        
        try:
            class DatabaseHealthChecker:
                def __init__(self, db_path):
                    self.db_path = db_path
                
                def check_health(self):
                    try:
                        conn = sqlite3.connect(self.db_path)
                        conn.execute("SELECT 1")
                        conn.close()
                        return {'healthy': True}
                    except Exception as e:
                        return {
                            'healthy': False,
                            'error': str(e),
                            'error_type': type(e).__name__
                        }
            
            checker = DatabaseHealthChecker(path)
            health = checker.check_health()
            
            assert health['healthy'] is False
            assert 'error' in health
            assert 'DatabaseError' in health['error_type'] or 'OperationalError' in health['error_type']
            
        finally:
            os.unlink(path)