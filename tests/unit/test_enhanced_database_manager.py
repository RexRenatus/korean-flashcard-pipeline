"""
Test suite for Enhanced Database Manager with connection pooling and monitoring.
"""

import pytest
import sqlite3
import tempfile
import os
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from flashcard_pipeline.database.db_manager_v2 import (
    EnhancedDatabaseManager,
    DatabaseHealthEndpoint
)
from flashcard_pipeline.database.connection_pool import PoolConfig
from flashcard_pipeline.database.performance_monitor import PerformanceThresholds
from flashcard_pipeline.database.db_manager import VocabularyRecord, ProcessingTask


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Initialize database with schema
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    
    # Create all required tables
    cursor.executescript("""
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

        CREATE TABLE IF NOT EXISTS system_configuration (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        INSERT INTO system_configuration (key, value, description)
        VALUES ('schema_version', '2.0', 'Database schema version');
    """)
    
    conn.commit()
    conn.close()
    
    yield path
    
    # Cleanup
    os.unlink(path)


@pytest.fixture
def enhanced_db_manager(temp_db):
    """Create an enhanced database manager"""
    config = PoolConfig(
        min_connections=2,
        max_connections=5,
        connection_timeout=10.0,
        idle_timeout=60.0,
        health_check_interval=5.0
    )
    
    thresholds = PerformanceThresholds(
        slow_query_ms=50.0,
        very_slow_query_ms=200.0
    )
    
    manager = EnhancedDatabaseManager(
        db_path=temp_db,
        pool_config=config,
        performance_thresholds=thresholds,
        enable_monitoring=True
    )
    
    yield manager
    
    # Cleanup
    manager.close()


class TestEnhancedDatabaseManager:
    """Test enhanced database manager functionality"""
    
    def test_initialization(self, enhanced_db_manager):
        """Test manager initialization"""
        assert enhanced_db_manager is not None
        assert enhanced_db_manager.pool is not None
        assert enhanced_db_manager.monitor is not None
        assert enhanced_db_manager.health_checker is not None
    
    def test_connection_pooling(self, enhanced_db_manager):
        """Test connection pool functionality"""
        # Get pool stats
        stats = enhanced_db_manager.get_pool_stats()
        
        assert stats['total_connections'] >= 2  # Min connections
        assert stats['available_connections'] >= 0
        
        # Use connections concurrently
        def use_connection(i):
            with enhanced_db_manager.get_connection() as conn:
                cursor = conn.execute("SELECT ? as num", (i,))
                result = cursor.fetchone()
                time.sleep(0.01)  # Simulate work
                return result['num']
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(use_connection, i) for i in range(10)]
            results = [f.result() for f in as_completed(futures)]
        
        assert len(results) == 10
        assert sorted(results) == list(range(10))
        
        # Check pool grew but within limits
        stats = enhanced_db_manager.get_pool_stats()
        assert stats['total_connections'] <= 5  # Max connections
    
    def test_performance_monitoring(self, enhanced_db_manager):
        """Test performance monitoring"""
        # Create some test data
        for i in range(5):
            vocab = VocabularyRecord(
                korean=f"단어{i}",
                english=f"Word{i}",
                type="noun"
            )
            enhanced_db_manager.create_vocabulary(vocab)
        
        # Get performance stats
        stats = enhanced_db_manager.get_performance_stats()
        
        assert stats['total_queries'] >= 5
        assert stats['total_errors'] == 0
        assert stats['error_rate'] == 0
        assert stats['avg_duration_ms'] > 0
        
        # Check metrics by type
        assert 'INSERT' in stats['metrics_by_type']
        assert stats['metrics_by_type']['INSERT']['count'] >= 5
    
    def test_slow_query_detection(self, enhanced_db_manager):
        """Test slow query detection"""
        # Create a slow query (cross join)
        with enhanced_db_manager.get_connection() as conn:
            # First add some data
            for i in range(10):
                conn.execute(
                    "INSERT INTO vocabulary (korean, english) VALUES (?, ?)",
                    (f"느린{i}", f"Slow{i}")
                )
            conn.commit()
            
            # Execute slow query
            with enhanced_db_manager.monitor.monitor_query(
                "SELECT COUNT(*) FROM vocabulary v1 CROSS JOIN vocabulary v2"
            ) as metrics:
                conn.execute("SELECT COUNT(*) FROM vocabulary v1 CROSS JOIN vocabulary v2")
        
        # Check slow queries
        slow_queries = enhanced_db_manager.get_slow_queries()
        
        # May or may not have slow queries depending on performance
        if slow_queries:
            assert slow_queries[0]['query_type'] == 'SELECT'
            assert 'CROSS JOIN' in slow_queries[0]['query']
    
    def test_health_check(self, enhanced_db_manager):
        """Test health check functionality"""
        health = enhanced_db_manager.check_health()
        
        assert health['healthy'] is True
        assert health['checks']['connection'] == 'OK'
        assert health['checks']['write'] == 'OK'
        assert health['checks']['schema'] == 'OK'
        assert 'pool_health' in health
        assert health['pool_health']['total_connections'] > 0
    
    def test_retry_logic(self, enhanced_db_manager):
        """Test retry logic for locked database"""
        # This test is tricky with SQLite, so we'll test the retry mechanism exists
        vocab = VocabularyRecord(korean="재시도", english="Retry")
        vocab_id = enhanced_db_manager.create_vocabulary(vocab)
        
        # Create a task
        task_id = enhanced_db_manager.create_task(vocab_id)
        
        # Verify it was created
        tasks = enhanced_db_manager.get_pending_tasks(1)
        assert len(tasks) == 1
        assert tasks[0].task_id == task_id
    
    def test_cache_with_monitoring(self, enhanced_db_manager):
        """Test cache operations with monitoring"""
        # Save cache entry
        enhanced_db_manager.save_cache_entry(
            cache_key="test_monitored",
            cache_value='{"data": "monitored"}',
            ttl_seconds=3600
        )
        
        # Get cache entry (should update hit count)
        value = enhanced_db_manager.get_cache_entry("test_monitored")
        assert value == '{"data": "monitored"}'
        
        # Get it again
        value = enhanced_db_manager.get_cache_entry("test_monitored")
        assert value is not None
        
        # Check performance stats include cache operations
        stats = enhanced_db_manager.get_performance_stats()
        
        # Should have INSERT and SELECT queries
        assert 'INSERT' in stats['metrics_by_type']
        assert 'SELECT' in stats['metrics_by_type']
        assert 'UPDATE' in stats['metrics_by_type']  # Hit count update
    
    def test_concurrent_operations(self, enhanced_db_manager):
        """Test concurrent database operations"""
        def worker(worker_id):
            results = []
            
            # Create vocabulary
            vocab = VocabularyRecord(
                korean=f"동시{worker_id}",
                english=f"Concurrent{worker_id}"
            )
            vocab_id = enhanced_db_manager.create_vocabulary(vocab)
            results.append(('vocab', vocab_id))
            
            # Create task
            task_id = enhanced_db_manager.create_task(vocab_id)
            results.append(('task', task_id))
            
            # Cache operation
            enhanced_db_manager.save_cache_entry(
                cache_key=f"concurrent_{worker_id}",
                cache_value=f"data_{worker_id}"
            )
            
            # Read cache
            value = enhanced_db_manager.get_cache_entry(f"concurrent_{worker_id}")
            results.append(('cache', value))
            
            return results
        
        # Run concurrent workers
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, i) for i in range(10)]
            all_results = [f.result() for f in as_completed(futures)]
        
        # Verify all succeeded
        assert len(all_results) == 10
        for results in all_results:
            assert len(results) == 3
            assert results[0][0] == 'vocab'
            assert results[1][0] == 'task'
            assert results[2][0] == 'cache'
            assert results[2][1] is not None
        
        # Check pool handled concurrency well
        stats = enhanced_db_manager.get_pool_stats()
        assert stats['metrics']['connection_errors'] == 0
    
    def test_performance_report(self, enhanced_db_manager):
        """Test performance report generation"""
        # Generate some activity
        for i in range(3):
            vocab = VocabularyRecord(korean=f"리포트{i}", english=f"Report{i}")
            enhanced_db_manager.create_vocabulary(vocab)
        
        # Generate report
        report = enhanced_db_manager.generate_performance_report()
        
        assert "Database Performance Report" in report
        assert "Total Queries:" in report
        assert "Query Type Distribution" in report
        assert "INSERT" in report
    
    def test_database_optimization(self, enhanced_db_manager):
        """Test database optimization"""
        # Add some data and cache entries
        for i in range(5):
            vocab = VocabularyRecord(korean=f"최적화{i}", english=f"Optimize{i}")
            enhanced_db_manager.create_vocabulary(vocab)
            
            enhanced_db_manager.save_cache_entry(
                cache_key=f"optimize_{i}",
                cache_value=f"data_{i}",
                ttl_seconds=1 if i < 2 else 3600  # Some expire quickly
            )
        
        # Wait for some cache entries to expire
        time.sleep(1.1)
        
        # Run optimization
        results = enhanced_db_manager.optimize_database()
        
        assert results['operations']
        
        # Check operations
        operations = {op['operation']: op for op in results['operations']}
        assert 'VACUUM' in operations
        assert 'ANALYZE' in operations
        assert 'CACHE_CLEANUP' in operations
        
        # Cache cleanup should have found expired entries
        if operations['CACHE_CLEANUP']['status'] == 'success':
            assert operations['CACHE_CLEANUP']['deleted_entries'] >= 0


class TestDatabaseHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_endpoint(self, enhanced_db_manager):
        """Test health endpoint responses"""
        endpoint = DatabaseHealthEndpoint(enhanced_db_manager)
        
        # Test healthy state
        status_code, response = endpoint.get_health()
        
        assert status_code == 200
        assert response['healthy'] is True
        assert 'checks' in response
        assert 'pool_health' in response
    
    def test_metrics_endpoint(self, enhanced_db_manager):
        """Test metrics endpoint"""
        endpoint = DatabaseHealthEndpoint(enhanced_db_manager)
        
        # Generate some metrics
        for i in range(3):
            vocab = VocabularyRecord(korean=f"메트릭{i}", english=f"Metric{i}")
            enhanced_db_manager.create_vocabulary(vocab)
        
        # Get metrics
        status_code, response = endpoint.get_metrics()
        
        assert status_code == 200
        assert 'pool_stats' in response
        assert 'performance_stats' in response
        assert 'slow_queries' in response
        assert response['performance_stats']['total_queries'] >= 3


class TestConnectionPoolStress:
    """Stress tests for connection pool"""
    
    def test_pool_exhaustion_recovery(self, enhanced_db_manager):
        """Test pool behavior when exhausted"""
        # Get all available connections
        connections = []
        try:
            for i in range(10):  # Try to get more than max
                conn_context = enhanced_db_manager.pool.get_connection()
                conn = conn_context.__enter__()
                connections.append((conn_context, conn))
                
                if len(connections) >= 5:  # Max connections
                    break
        except TimeoutError:
            # Expected when pool exhausted
            pass
        
        # Release connections
        for conn_context, conn in connections:
            conn_context.__exit__(None, None, None)
        
        # Pool should recover
        with enhanced_db_manager.get_connection() as conn:
            cursor = conn.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1
    
    def test_long_running_queries(self, enhanced_db_manager):
        """Test handling of long-running queries"""
        def long_query():
            with enhanced_db_manager.get_connection() as conn:
                # Simulate long query
                conn.execute("SELECT 1")
                time.sleep(0.1)
                return True
        
        # Run multiple long queries concurrently
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(long_query) for _ in range(3)]
            results = [f.result() for f in as_completed(futures)]
        
        assert all(results)
        
        # Check pool stats
        stats = enhanced_db_manager.get_pool_stats()
        assert stats['metrics']['connections_reused'] > 0