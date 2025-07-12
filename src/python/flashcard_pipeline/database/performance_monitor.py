"""
Database performance monitoring and metrics collection.
Tracks query performance, identifies slow queries, and provides insights.
"""

import time
import threading
import logging
from collections import defaultdict, deque
from contextlib import contextmanager
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
import json
import sqlite3

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Metrics for a single query execution"""
    query_text: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    rows_affected: int = 0
    error: Optional[str] = None
    query_type: str = "SELECT"  # SELECT, INSERT, UPDATE, DELETE, OTHER
    table_name: Optional[str] = None
    
    def complete(self, rows_affected: int = 0, error: Optional[str] = None):
        """Mark query as complete"""
        self.end_time = datetime.now()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.rows_affected = rows_affected
        self.error = error


@dataclass
class PerformanceThresholds:
    """Configurable performance thresholds"""
    slow_query_ms: float = 100.0
    very_slow_query_ms: float = 1000.0
    max_query_history: int = 1000
    alert_on_slow_queries: bool = True
    track_query_plans: bool = True
    
    
class QueryAnalyzer:
    """Analyzes SQL queries to extract metadata"""
    
    @staticmethod
    def analyze_query(query: str) -> Tuple[str, Optional[str]]:
        """Extract query type and table name from SQL query"""
        query_upper = query.strip().upper()
        
        # Determine query type
        if query_upper.startswith("SELECT"):
            query_type = "SELECT"
        elif query_upper.startswith("INSERT"):
            query_type = "INSERT"
        elif query_upper.startswith("UPDATE"):
            query_type = "UPDATE"
        elif query_upper.startswith("DELETE"):
            query_type = "DELETE"
        elif query_upper.startswith("CREATE"):
            query_type = "CREATE"
        elif query_upper.startswith("DROP"):
            query_type = "DROP"
        else:
            query_type = "OTHER"
        
        # Extract table name (simplified)
        table_name = None
        
        if query_type == "SELECT":
            # Look for FROM clause
            from_idx = query_upper.find("FROM")
            if from_idx != -1:
                remaining = query[from_idx + 4:].strip()
                # Extract first word as table name
                table_name = remaining.split()[0].strip('`"[]')
                
        elif query_type in ["INSERT", "UPDATE", "DELETE"]:
            # These usually have table name early in query
            words = query.split()
            for i, word in enumerate(words):
                if word.upper() in ["INTO", "UPDATE", "FROM"]:
                    if i + 1 < len(words):
                        table_name = words[i + 1].strip('`"[](),')
                        break
        
        return query_type, table_name


class PerformanceMonitor:
    """Monitors database performance and collects metrics"""
    
    def __init__(self, thresholds: Optional[PerformanceThresholds] = None):
        self.thresholds = thresholds or PerformanceThresholds()
        self.analyzer = QueryAnalyzer()
        
        # Query history
        self._query_history = deque(maxlen=self.thresholds.max_query_history)
        self._slow_queries = deque(maxlen=100)
        
        # Aggregated metrics
        self._metrics_by_type = defaultdict(lambda: {
            'count': 0,
            'total_duration_ms': 0.0,
            'errors': 0,
            'rows_affected': 0
        })
        
        self._metrics_by_table = defaultdict(lambda: {
            'count': 0,
            'total_duration_ms': 0.0,
            'errors': 0
        })
        
        # Real-time metrics
        self._current_minute_metrics = defaultdict(int)
        self._metrics_lock = threading.RLock()
        
        # Alert callbacks
        self._alert_callbacks: List[Callable] = []
        
        # Start time
        self._start_time = datetime.now()
    
    @contextmanager
    def monitor_query(self, query: str, connection=None):
        """Context manager to monitor a query execution"""
        # Analyze query
        query_type, table_name = self.analyzer.analyze_query(query)
        
        # Create metrics
        metrics = QueryMetrics(
            query_text=query[:500],  # Truncate long queries
            start_time=datetime.now(),
            query_type=query_type,
            table_name=table_name
        )
        
        # Track query plan if enabled
        query_plan = None
        if self.thresholds.track_query_plans and connection and query_type == "SELECT":
            try:
                plan_query = f"EXPLAIN QUERY PLAN {query}"
                plan_result = connection.execute(plan_query).fetchall()
                query_plan = [dict(row) for row in plan_result]
            except:
                pass  # Ignore errors in plan extraction
        
        try:
            yield metrics
            
            # Query completed successfully
            metrics.complete()
            
        except Exception as e:
            # Query failed
            metrics.complete(error=str(e))
            raise
            
        finally:
            # Record metrics
            self._record_metrics(metrics, query_plan)
    
    def _record_metrics(self, metrics: QueryMetrics, query_plan: Optional[List[Dict]] = None):
        """Record query metrics"""
        with self._metrics_lock:
            # Add to history
            self._query_history.append(metrics)
            
            # Check for slow query
            if metrics.duration_ms >= self.thresholds.slow_query_ms:
                slow_query_info = {
                    'metrics': metrics,
                    'query_plan': query_plan,
                    'severity': 'very_slow' if metrics.duration_ms >= self.thresholds.very_slow_query_ms else 'slow'
                }
                self._slow_queries.append(slow_query_info)
                
                # Trigger alerts
                if self.thresholds.alert_on_slow_queries:
                    self._trigger_slow_query_alert(slow_query_info)
            
            # Update aggregated metrics by type
            type_metrics = self._metrics_by_type[metrics.query_type]
            type_metrics['count'] += 1
            type_metrics['total_duration_ms'] += metrics.duration_ms
            if metrics.error:
                type_metrics['errors'] += 1
            type_metrics['rows_affected'] += metrics.rows_affected
            
            # Update aggregated metrics by table
            if metrics.table_name:
                table_metrics = self._metrics_by_table[metrics.table_name]
                table_metrics['count'] += 1
                table_metrics['total_duration_ms'] += metrics.duration_ms
                if metrics.error:
                    table_metrics['errors'] += 1
            
            # Update real-time metrics
            minute_key = datetime.now().strftime("%Y-%m-%d %H:%M")
            self._current_minute_metrics[f"{minute_key}:queries"] += 1
            self._current_minute_metrics[f"{minute_key}:duration_ms"] += metrics.duration_ms
            if metrics.error:
                self._current_minute_metrics[f"{minute_key}:errors"] += 1
    
    def _trigger_slow_query_alert(self, slow_query_info: Dict):
        """Trigger alerts for slow queries"""
        for callback in self._alert_callbacks:
            try:
                callback(slow_query_info)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
    
    def add_alert_callback(self, callback: Callable):
        """Add a callback for slow query alerts"""
        self._alert_callbacks.append(callback)
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics"""
        with self._metrics_lock:
            total_queries = sum(m['count'] for m in self._metrics_by_type.values())
            total_duration = sum(m['total_duration_ms'] for m in self._metrics_by_type.values())
            total_errors = sum(m['errors'] for m in self._metrics_by_type.values())
            
            # Calculate percentiles from recent queries
            recent_durations = [q.duration_ms for q in self._query_history if not q.error]
            
            return {
                'uptime_seconds': (datetime.now() - self._start_time).total_seconds(),
                'total_queries': total_queries,
                'total_errors': total_errors,
                'error_rate': total_errors / total_queries if total_queries > 0 else 0,
                'avg_duration_ms': total_duration / total_queries if total_queries > 0 else 0,
                'queries_per_second': total_queries / (datetime.now() - self._start_time).total_seconds(),
                'slow_queries': len(self._slow_queries),
                'metrics_by_type': dict(self._metrics_by_type),
                'metrics_by_table': dict(self._metrics_by_table),
                'duration_percentiles': self._calculate_percentiles(recent_durations) if recent_durations else {}
            }
    
    def get_slow_queries(self, limit: int = 10) -> List[Dict]:
        """Get recent slow queries"""
        with self._metrics_lock:
            slow_queries = list(self._slow_queries)[-limit:]
            
        return [
            {
                'query': q['metrics'].query_text,
                'duration_ms': q['metrics'].duration_ms,
                'timestamp': q['metrics'].start_time.isoformat(),
                'query_type': q['metrics'].query_type,
                'table_name': q['metrics'].table_name,
                'severity': q['severity'],
                'query_plan': q.get('query_plan')
            }
            for q in reversed(slow_queries)
        ]
    
    def get_real_time_metrics(self, minutes: int = 10) -> Dict[str, Any]:
        """Get real-time metrics for the last N minutes"""
        with self._metrics_lock:
            current_time = datetime.now()
            metrics = {}
            
            for i in range(minutes):
                time_key = (current_time - timedelta(minutes=i)).strftime("%Y-%m-%d %H:%M")
                metrics[time_key] = {
                    'queries': self._current_minute_metrics.get(f"{time_key}:queries", 0),
                    'duration_ms': self._current_minute_metrics.get(f"{time_key}:duration_ms", 0),
                    'errors': self._current_minute_metrics.get(f"{time_key}:errors", 0)
                }
            
            return metrics
    
    def _calculate_percentiles(self, values: List[float]) -> Dict[str, float]:
        """Calculate percentiles for a list of values"""
        if not values:
            return {}
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        def percentile(p):
            k = (n - 1) * p / 100
            f = int(k)
            c = int(k) + 1
            if f == c:
                return sorted_values[f]
            d0 = sorted_values[f] * (c - k)
            d1 = sorted_values[c] * (k - f)
            return d0 + d1
        
        return {
            'p50': percentile(50),
            'p75': percentile(75),
            'p90': percentile(90),
            'p95': percentile(95),
            'p99': percentile(99),
            'min': sorted_values[0],
            'max': sorted_values[-1]
        }
    
    def generate_performance_report(self) -> str:
        """Generate a human-readable performance report"""
        stats = self.get_summary_stats()
        slow_queries = self.get_slow_queries(5)
        
        report = f"""
Database Performance Report
==========================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Uptime: {stats['uptime_seconds']:.1f} seconds

Summary Statistics
-----------------
Total Queries: {stats['total_queries']:,}
Total Errors: {stats['total_errors']:,}
Error Rate: {stats['error_rate']:.2%}
Average Duration: {stats['avg_duration_ms']:.2f} ms
Queries/Second: {stats['queries_per_second']:.2f}
Slow Queries: {stats['slow_queries']}

Query Type Distribution
----------------------"""
        
        for query_type, metrics in stats['metrics_by_type'].items():
            avg_duration = metrics['total_duration_ms'] / metrics['count'] if metrics['count'] > 0 else 0
            report += f"\n{query_type:10} Count: {metrics['count']:6,}  Avg: {avg_duration:6.2f} ms  Errors: {metrics['errors']}"
        
        report += "\n\nTop Tables by Query Count\n-------------------------"
        
        # Sort tables by query count
        sorted_tables = sorted(
            stats['metrics_by_table'].items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:5]
        
        for table, metrics in sorted_tables:
            avg_duration = metrics['total_duration_ms'] / metrics['count'] if metrics['count'] > 0 else 0
            report += f"\n{table:20} Count: {metrics['count']:6,}  Avg: {avg_duration:6.2f} ms"
        
        if stats.get('duration_percentiles'):
            report += "\n\nQuery Duration Percentiles\n--------------------------"
            for percentile, value in stats['duration_percentiles'].items():
                report += f"\n{percentile:3}: {value:6.2f} ms"
        
        if slow_queries:
            report += "\n\nRecent Slow Queries\n------------------"
            for i, query in enumerate(slow_queries, 1):
                report += f"\n{i}. [{query['severity'].upper()}] {query['duration_ms']:.2f} ms - {query['query_type']}"
                report += f"\n   {query['query'][:100]}{'...' if len(query['query']) > 100 else ''}"
                report += f"\n   Table: {query['table_name'] or 'N/A'}  Time: {query['timestamp']}"
        
        return report


class DatabaseHealthChecker:
    """Performs health checks on database connections and operations"""
    
    def __init__(self, db_path: str, monitor: Optional[PerformanceMonitor] = None):
        self.db_path = db_path
        self.monitor = monitor
    
    def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'healthy': True,
            'checks': {},
            'warnings': [],
            'errors': []
        }
        
        # Connection check
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("SELECT 1")
            conn.close()
            health_status['checks']['connection'] = 'OK'
        except Exception as e:
            health_status['healthy'] = False
            health_status['checks']['connection'] = 'FAILED'
            health_status['errors'].append(f"Connection failed: {str(e)}")
        
        # Write check
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("CREATE TEMP TABLE health_check_temp (id INTEGER)")
            conn.execute("INSERT INTO health_check_temp VALUES (1)")
            conn.execute("DROP TABLE health_check_temp")
            conn.close()
            health_status['checks']['write'] = 'OK'
        except Exception as e:
            health_status['healthy'] = False
            health_status['checks']['write'] = 'FAILED'
            health_status['errors'].append(f"Write check failed: {str(e)}")
        
        # Schema check
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                ORDER BY name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = [
                'vocabulary', 'processing_tasks', 'stage_outputs',
                'flashcards', 'cache_entries', 'api_usage',
                'processing_metrics', 'system_configuration'
            ]
            
            missing_tables = set(expected_tables) - set(tables)
            if missing_tables:
                health_status['warnings'].append(f"Missing tables: {', '.join(missing_tables)}")
            
            health_status['checks']['schema'] = 'OK' if not missing_tables else 'WARNING'
            conn.close()
            
        except Exception as e:
            health_status['checks']['schema'] = 'ERROR'
            health_status['errors'].append(f"Schema check failed: {str(e)}")
        
        # Performance check
        if self.monitor:
            stats = self.monitor.get_summary_stats()
            
            # Check error rate
            if stats['error_rate'] > 0.05:  # 5% error rate
                health_status['warnings'].append(f"High error rate: {stats['error_rate']:.2%}")
            
            # Check average query time
            if stats['avg_duration_ms'] > 100:
                health_status['warnings'].append(f"High average query time: {stats['avg_duration_ms']:.2f} ms")
            
            # Check for many slow queries
            if stats['slow_queries'] > 50:
                health_status['warnings'].append(f"Many slow queries: {stats['slow_queries']}")
            
            health_status['checks']['performance'] = 'OK' if not health_status['warnings'] else 'WARNING'
            health_status['performance_summary'] = {
                'total_queries': stats['total_queries'],
                'error_rate': stats['error_rate'],
                'avg_duration_ms': stats['avg_duration_ms'],
                'slow_queries': stats['slow_queries']
            }
        
        # File system check
        try:
            db_stat = Path(self.db_path).stat()
            health_status['checks']['filesystem'] = 'OK'
            health_status['database_info'] = {
                'size_mb': db_stat.st_size / (1024 * 1024),
                'modified': datetime.fromtimestamp(db_stat.st_mtime).isoformat()
            }
        except Exception as e:
            health_status['checks']['filesystem'] = 'ERROR'
            health_status['errors'].append(f"Filesystem check failed: {str(e)}")
        
        # Update overall health status
        if health_status['errors']:
            health_status['healthy'] = False
        elif health_status['warnings']:
            health_status['healthy'] = True  # Warnings don't make it unhealthy
            
        return health_status