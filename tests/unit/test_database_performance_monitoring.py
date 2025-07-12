"""
Test suite for database performance monitoring and metrics collection.
Tests query performance tracking, slow query detection, and metrics aggregation.
"""

import pytest
import sqlite3
import tempfile
import os
import time
import json
from datetime import datetime, timedelta
from contextlib import contextmanager
from unittest.mock import patch, MagicMock

from flashcard_pipeline.database.db_manager import DatabaseManager


class PerformanceMonitor:
    """Database performance monitoring implementation"""
    
    def __init__(self, slow_query_threshold_ms=100):
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self.metrics = []
    
    @contextmanager
    def monitor_query(self, query_type, query_text):
        """Monitor a database query execution"""
        start_time = time.time()
        
        try:
            yield
            status = 'success'
            error = None
        except Exception as e:
            status = 'error'
            error = str(e)
            raise
        finally:
            duration_ms = int((time.time() - start_time) * 1000)
            
            metric = {
                'timestamp': datetime.now().isoformat(),
                'query_type': query_type,
                'query_text': query_text[:200],  # Truncate long queries
                'duration_ms': duration_ms,
                'status': status,
                'error': error,
                'is_slow': duration_ms > self.slow_query_threshold_ms
            }
            
            self.metrics.append(metric)
    
    def get_slow_queries(self, limit=10):
        """Get the slowest queries"""
        slow_queries = [m for m in self.metrics if m['is_slow']]
        return sorted(slow_queries, key=lambda x: x['duration_ms'], reverse=True)[:limit]
    
    def get_query_stats(self):
        """Get aggregate query statistics"""
        if not self.metrics:
            return {}
        
        durations = [m['duration_ms'] for m in self.metrics]
        errors = [m for m in self.metrics if m['status'] == 'error']
        
        return {
            'total_queries': len(self.metrics),
            'total_errors': len(errors),
            'avg_duration_ms': sum(durations) / len(durations),
            'min_duration_ms': min(durations),
            'max_duration_ms': max(durations),
            'slow_query_count': len([m for m in self.metrics if m['is_slow']]),
            'error_rate': len(errors) / len(self.metrics) if self.metrics else 0
        }


class TestDatabasePerformanceMonitoring:
    """Test database performance monitoring functionality"""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database with test data"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vocabulary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                korean TEXT NOT NULL,
                english TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processing_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                stage_name TEXT,
                duration_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert test data
        for i in range(1000):
            cursor.execute(
                "INSERT INTO vocabulary (korean, english) VALUES (?, ?)",
                (f"단어{i}", f"Word{i}")
            )
        
        conn.commit()
        conn.close()
        
        yield path
        os.unlink(path)
    
    def test_query_monitoring(self, temp_db):
        """Test basic query monitoring"""
        monitor = PerformanceMonitor()
        
        conn = sqlite3.connect(temp_db)
        
        # Monitor a fast query
        with monitor.monitor_query("SELECT", "SELECT COUNT(*) FROM vocabulary"):
            cursor = conn.execute("SELECT COUNT(*) FROM vocabulary")
            count = cursor.fetchone()[0]
        
        # Monitor a slower query
        with monitor.monitor_query("SELECT", "SELECT * FROM vocabulary WHERE korean LIKE '%5%'"):
            cursor = conn.execute("SELECT * FROM vocabulary WHERE korean LIKE '%5%'")
            results = cursor.fetchall()
        
        conn.close()
        
        # Check metrics
        assert len(monitor.metrics) == 2
        assert monitor.metrics[0]['status'] == 'success'
        assert monitor.metrics[0]['duration_ms'] >= 0
        assert monitor.metrics[0]['error'] is None
    
    def test_slow_query_detection(self, temp_db):
        """Test detection of slow queries"""
        monitor = PerformanceMonitor(slow_query_threshold_ms=1)  # Very low threshold
        
        conn = sqlite3.connect(temp_db)
        
        # This should be marked as slow
        with monitor.monitor_query("SELECT", "Complex query"):
            cursor = conn.execute("""
                SELECT v1.korean, v2.english
                FROM vocabulary v1
                CROSS JOIN vocabulary v2
                LIMIT 100
            """)
            results = cursor.fetchall()
        
        conn.close()
        
        slow_queries = monitor.get_slow_queries()
        assert len(slow_queries) == 1
        assert slow_queries[0]['is_slow'] is True
        assert slow_queries[0]['query_type'] == "SELECT"
    
    def test_query_error_tracking(self, temp_db):
        """Test tracking of query errors"""
        monitor = PerformanceMonitor()
        
        conn = sqlite3.connect(temp_db)
        
        # Monitor a query that will fail
        with pytest.raises(sqlite3.OperationalError):
            with monitor.monitor_query("SELECT", "Invalid query"):
                conn.execute("SELECT * FROM non_existent_table")
        
        conn.close()
        
        # Check error was recorded
        assert len(monitor.metrics) == 1
        assert monitor.metrics[0]['status'] == 'error'
        assert monitor.metrics[0]['error'] is not None
        assert 'no such table' in monitor.metrics[0]['error']
    
    def test_query_statistics(self, temp_db):
        """Test aggregate query statistics"""
        monitor = PerformanceMonitor()
        
        conn = sqlite3.connect(temp_db)
        
        # Run various queries
        queries = [
            "SELECT COUNT(*) FROM vocabulary",
            "SELECT * FROM vocabulary LIMIT 10",
            "SELECT korean FROM vocabulary WHERE id = 1",
            "SELECT * FROM vocabulary WHERE english LIKE '%test%'"
        ]
        
        for query in queries:
            with monitor.monitor_query("SELECT", query):
                conn.execute(query)
        
        # Add an error
        try:
            with monitor.monitor_query("SELECT", "Bad query"):
                conn.execute("SELECT * FROM invalid_table")
        except:
            pass
        
        conn.close()
        
        # Get statistics
        stats = monitor.get_query_stats()
        
        assert stats['total_queries'] == 5
        assert stats['total_errors'] == 1
        assert stats['error_rate'] == 0.2
        assert stats['avg_duration_ms'] > 0
        assert stats['min_duration_ms'] <= stats['avg_duration_ms']
        assert stats['max_duration_ms'] >= stats['avg_duration_ms']
    
    def test_performance_degradation_detection(self, temp_db):
        """Test detection of performance degradation"""
        
        class PerformanceTrendAnalyzer:
            def __init__(self, window_size=10):
                self.window_size = window_size
                self.query_times = []
            
            def add_measurement(self, duration_ms):
                self.query_times.append(duration_ms)
                if len(self.query_times) > self.window_size * 2:
                    self.query_times.pop(0)
            
            def detect_degradation(self, threshold=1.5):
                """Detect if recent queries are slower than historical average"""
                if len(self.query_times) < self.window_size * 2:
                    return False, None
                
                mid = len(self.query_times) // 2
                historical = self.query_times[:mid]
                recent = self.query_times[mid:]
                
                historical_avg = sum(historical) / len(historical)
                recent_avg = sum(recent) / len(recent)
                
                ratio = recent_avg / historical_avg if historical_avg > 0 else 1
                
                return ratio > threshold, {
                    'historical_avg_ms': historical_avg,
                    'recent_avg_ms': recent_avg,
                    'degradation_ratio': ratio
                }
        
        analyzer = PerformanceTrendAnalyzer(window_size=5)
        
        # Simulate normal performance
        for i in range(5):
            analyzer.add_measurement(10 + i % 3)  # 10-12ms
        
        # Simulate degraded performance
        for i in range(5):
            analyzer.add_measurement(20 + i % 3)  # 20-22ms
        
        is_degraded, details = analyzer.detect_degradation()
        
        assert is_degraded is True
        assert details['degradation_ratio'] > 1.5
        assert details['recent_avg_ms'] > details['historical_avg_ms']
    
    def test_query_plan_analysis(self, temp_db):
        """Test analysis of query execution plans"""
        
        class QueryPlanAnalyzer:
            def __init__(self, db_path):
                self.db_path = db_path
            
            def analyze_query(self, query):
                """Analyze query execution plan"""
                conn = sqlite3.connect(self.db_path)
                
                # Get query plan
                cursor = conn.execute(f"EXPLAIN QUERY PLAN {query}")
                plan = cursor.fetchall()
                
                analysis = {
                    'query': query,
                    'plan': plan,
                    'uses_index': False,
                    'full_table_scan': False,
                    'recommendations': []
                }
                
                # Analyze plan
                plan_text = ' '.join(str(row) for row in plan)
                
                if 'SCAN' in plan_text:
                    analysis['full_table_scan'] = True
                    analysis['recommendations'].append(
                        "Consider adding an index to avoid full table scan"
                    )
                
                if 'USING INDEX' in plan_text:
                    analysis['uses_index'] = True
                
                conn.close()
                return analysis
        
        analyzer = QueryPlanAnalyzer(temp_db)
        
        # Analyze a query without index
        analysis = analyzer.analyze_query(
            "SELECT * FROM vocabulary WHERE english = 'Test'"
        )
        
        assert analysis['full_table_scan'] is True
        assert analysis['uses_index'] is False
        assert len(analysis['recommendations']) > 0
        
        # Create index and re-analyze
        conn = sqlite3.connect(temp_db)
        conn.execute("CREATE INDEX idx_english ON vocabulary(english)")
        conn.close()
        
        analysis = analyzer.analyze_query(
            "SELECT * FROM vocabulary WHERE english = 'Test'"
        )
        
        assert analysis['uses_index'] is True
    
    def test_concurrent_query_monitoring(self, temp_db):
        """Test monitoring of concurrent queries"""
        import threading
        
        monitor = PerformanceMonitor()
        errors = []
        
        def run_query(query_id):
            try:
                conn = sqlite3.connect(temp_db)
                
                with monitor.monitor_query("SELECT", f"Query {query_id}"):
                    cursor = conn.execute(
                        "SELECT COUNT(*) FROM vocabulary WHERE korean LIKE ?",
                        (f"%{query_id}%",)
                    )
                    cursor.fetchone()
                
                conn.close()
            except Exception as e:
                errors.append((query_id, str(e)))
        
        # Run concurrent queries
        threads = []
        for i in range(10):
            thread = threading.Thread(target=run_query, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0
        assert len(monitor.metrics) == 10
        assert all(m['status'] == 'success' for m in monitor.metrics)
    
    def test_metrics_persistence(self, temp_db):
        """Test saving performance metrics to database"""
        
        class MetricsPersistence:
            def __init__(self, db_path):
                self.db_path = db_path
            
            def save_metrics(self, metrics):
                """Save metrics to database"""
                conn = sqlite3.connect(self.db_path)
                
                for metric in metrics:
                    conn.execute("""
                        INSERT INTO processing_metrics 
                        (task_id, stage_name, duration_ms, created_at)
                        VALUES (?, ?, ?, ?)
                    """, (
                        metric.get('task_id', 0),
                        metric['query_type'],
                        metric['duration_ms'],
                        metric['timestamp']
                    ))
                
                conn.commit()
                conn.close()
            
            def get_metrics_summary(self, hours=24):
                """Get metrics summary for the last N hours"""
                conn = sqlite3.connect(self.db_path)
                
                cutoff = datetime.now() - timedelta(hours=hours)
                
                cursor = conn.execute("""
                    SELECT 
                        stage_name,
                        COUNT(*) as count,
                        AVG(duration_ms) as avg_duration,
                        MIN(duration_ms) as min_duration,
                        MAX(duration_ms) as max_duration
                    FROM processing_metrics
                    WHERE created_at > ?
                    GROUP BY stage_name
                """, (cutoff.isoformat(),))
                
                summary = {}
                for row in cursor:
                    summary[row[0]] = {
                        'count': row[1],
                        'avg_duration_ms': row[2],
                        'min_duration_ms': row[3],
                        'max_duration_ms': row[4]
                    }
                
                conn.close()
                return summary
        
        # Create and save metrics
        monitor = PerformanceMonitor()
        persistence = MetricsPersistence(temp_db)
        
        # Generate some metrics
        conn = sqlite3.connect(temp_db)
        for i in range(5):
            with monitor.monitor_query("SELECT", f"Query {i}"):
                conn.execute("SELECT COUNT(*) FROM vocabulary")
                time.sleep(0.01 * i)  # Varying durations
        conn.close()
        
        # Save metrics
        persistence.save_metrics(monitor.metrics)
        
        # Get summary
        summary = persistence.get_metrics_summary()
        
        assert 'SELECT' in summary
        assert summary['SELECT']['count'] == 5
        assert summary['SELECT']['avg_duration_ms'] > 0
        assert summary['SELECT']['min_duration_ms'] <= summary['SELECT']['avg_duration_ms']
        assert summary['SELECT']['max_duration_ms'] >= summary['SELECT']['avg_duration_ms']