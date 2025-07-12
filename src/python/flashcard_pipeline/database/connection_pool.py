"""
Database connection pool implementation for SQLite.
Provides connection pooling with health checks and metrics.
"""

import sqlite3
import threading
import time
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from queue import Queue, Empty, Full
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


@dataclass
class PoolConfig:
    """Configuration for database connection pool"""
    min_connections: int = 2
    max_connections: int = 10
    connection_timeout: float = 30.0
    idle_timeout: float = 300.0  # 5 minutes
    health_check_interval: float = 60.0  # 1 minute
    retry_attempts: int = 3
    retry_delay: float = 0.1
    retry_backoff: float = 2.0
    enable_wal: bool = True
    enable_foreign_keys: bool = True


@dataclass
class ConnectionStats:
    """Statistics for a database connection"""
    created_at: datetime
    last_used: datetime
    total_queries: int = 0
    total_errors: int = 0
    total_time_ms: float = 0.0
    
    @property
    def age_seconds(self) -> float:
        """Get age of connection in seconds"""
        return (datetime.now() - self.created_at).total_seconds()
    
    @property
    def idle_seconds(self) -> float:
        """Get idle time in seconds"""
        return (datetime.now() - self.last_used).total_seconds()
    
    @property
    def avg_query_time_ms(self) -> float:
        """Get average query time in milliseconds"""
        if self.total_queries == 0:
            return 0.0
        return self.total_time_ms / self.total_queries


class PooledConnection:
    """Wrapper for a pooled database connection"""
    
    def __init__(self, conn: sqlite3.Connection, pool: 'ConnectionPool', conn_id: int):
        self.conn = conn
        self.pool = pool
        self.conn_id = conn_id
        self.stats = ConnectionStats(
            created_at=datetime.now(),
            last_used=datetime.now()
        )
        self.in_use = False
        self.lock = threading.Lock()
    
    def execute(self, query: str, params=None):
        """Execute a query with metrics tracking"""
        start_time = time.time()
        try:
            if params:
                result = self.conn.execute(query, params)
            else:
                result = self.conn.execute(query)
            
            # Update stats
            elapsed_ms = (time.time() - start_time) * 1000
            self.stats.total_queries += 1
            self.stats.total_time_ms += elapsed_ms
            self.stats.last_used = datetime.now()
            
            return result
            
        except Exception as e:
            self.stats.total_errors += 1
            raise
    
    def close(self):
        """Close the underlying connection"""
        try:
            self.conn.close()
        except:
            pass
    
    def is_healthy(self) -> bool:
        """Check if connection is healthy"""
        try:
            self.conn.execute("SELECT 1")
            return True
        except:
            return False


class ConnectionPool:
    """Thread-safe connection pool for SQLite database"""
    
    def __init__(self, db_path: str, config: Optional[PoolConfig] = None):
        self.db_path = db_path
        self.config = config or PoolConfig()
        
        # Connection management
        self._connections: Dict[int, PooledConnection] = {}
        self._available = Queue(maxsize=self.config.max_connections)
        self._conn_counter = 0
        self._lock = threading.RLock()
        
        # Health check thread
        self._health_check_thread = None
        self._shutdown = threading.Event()
        
        # Metrics
        self.metrics = {
            'connections_created': 0,
            'connections_destroyed': 0,
            'connections_reused': 0,
            'connection_errors': 0,
            'health_checks_passed': 0,
            'health_checks_failed': 0,
            'total_wait_time_ms': 0.0
        }
        
        # Initialize pool
        self._initialize_pool()
        self._start_health_check()
    
    def _initialize_pool(self):
        """Initialize the connection pool with minimum connections"""
        for _ in range(self.config.min_connections):
            try:
                conn = self._create_connection()
                self._available.put(conn, block=False)
            except Exception as e:
                logger.error(f"Failed to create initial connection: {e}")
    
    def _create_connection(self) -> PooledConnection:
        """Create a new database connection"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        
        # Configure connection
        conn.row_factory = sqlite3.Row
        
        if self.config.enable_foreign_keys:
            conn.execute("PRAGMA foreign_keys = ON")
        
        if self.config.enable_wal:
            conn.execute("PRAGMA journal_mode = WAL")
        
        # Set busy timeout
        conn.execute(f"PRAGMA busy_timeout = {int(self.config.connection_timeout * 1000)}")
        
        # Create pooled connection
        with self._lock:
            self._conn_counter += 1
            conn_id = self._conn_counter
            pooled = PooledConnection(conn, self, conn_id)
            self._connections[conn_id] = pooled
            self.metrics['connections_created'] += 1
            
        logger.debug(f"Created new connection {conn_id}")
        return pooled
    
    def _destroy_connection(self, pooled: PooledConnection):
        """Destroy a database connection"""
        try:
            pooled.close()
        except Exception as e:
            logger.error(f"Error closing connection {pooled.conn_id}: {e}")
        
        with self._lock:
            if pooled.conn_id in self._connections:
                del self._connections[pooled.conn_id]
                self.metrics['connections_destroyed'] += 1
                
        logger.debug(f"Destroyed connection {pooled.conn_id}")
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool with retry logic"""
        pooled = None
        start_time = time.time()
        
        for attempt in range(self.config.retry_attempts):
            try:
                # Try to get an available connection
                timeout = self.config.connection_timeout
                pooled = self._available.get(timeout=timeout)
                
                # Check if connection is healthy
                if not pooled.is_healthy():
                    logger.warning(f"Unhealthy connection {pooled.conn_id}, creating new one")
                    self._destroy_connection(pooled)
                    pooled = self._create_connection()
                
                # Mark as in use
                with pooled.lock:
                    pooled.in_use = True
                    self.metrics['connections_reused'] += 1
                
                # Track wait time
                wait_time_ms = (time.time() - start_time) * 1000
                self.metrics['total_wait_time_ms'] += wait_time_ms
                
                break
                
            except Empty:
                # No available connections, try to create new one
                with self._lock:
                    total_conns = len(self._connections)
                    
                if total_conns < self.config.max_connections:
                    try:
                        pooled = self._create_connection()
                        with pooled.lock:
                            pooled.in_use = True
                        break
                    except Exception as e:
                        logger.error(f"Failed to create new connection: {e}")
                        self.metrics['connection_errors'] += 1
                
                # Retry with exponential backoff
                if attempt < self.config.retry_attempts - 1:
                    delay = self.config.retry_delay * (self.config.retry_backoff ** attempt)
                    time.sleep(delay)
                else:
                    raise TimeoutError(f"Could not acquire connection after {self.config.retry_attempts} attempts")
        
        if not pooled:
            raise RuntimeError("Failed to acquire database connection")
        
        try:
            yield pooled.conn
        finally:
            # Return connection to pool
            with pooled.lock:
                pooled.in_use = False
                pooled.stats.last_used = datetime.now()
            
            try:
                self._available.put(pooled, block=False)
            except Full:
                # Pool is full, destroy this connection
                logger.warning(f"Pool full, destroying connection {pooled.conn_id}")
                self._destroy_connection(pooled)
    
    def _start_health_check(self):
        """Start the health check thread"""
        def health_check_loop():
            while not self._shutdown.is_set():
                try:
                    self._perform_health_check()
                except Exception as e:
                    logger.error(f"Health check error: {e}")
                
                self._shutdown.wait(self.config.health_check_interval)
        
        self._health_check_thread = threading.Thread(
            target=health_check_loop,
            daemon=True,
            name="ConnectionPool-HealthCheck"
        )
        self._health_check_thread.start()
    
    def _perform_health_check(self):
        """Perform health check on all connections"""
        with self._lock:
            connections_to_check = list(self._connections.values())
        
        for pooled in connections_to_check:
            # Skip connections in use
            if pooled.in_use:
                continue
            
            # Check if connection is idle too long
            if pooled.stats.idle_seconds > self.config.idle_timeout:
                logger.info(f"Connection {pooled.conn_id} idle for {pooled.stats.idle_seconds:.1f}s, destroying")
                self._destroy_connection(pooled)
                continue
            
            # Health check
            if pooled.is_healthy():
                self.metrics['health_checks_passed'] += 1
            else:
                logger.warning(f"Connection {pooled.conn_id} failed health check")
                self.metrics['health_checks_failed'] += 1
                self._destroy_connection(pooled)
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get current pool statistics"""
        with self._lock:
            active_connections = [c for c in self._connections.values() if c.in_use]
            idle_connections = [c for c in self._connections.values() if not c.in_use]
            
            return {
                'total_connections': len(self._connections),
                'active_connections': len(active_connections),
                'idle_connections': len(idle_connections),
                'available_connections': self._available.qsize(),
                'metrics': self.metrics.copy(),
                'connection_stats': [
                    {
                        'id': c.conn_id,
                        'in_use': c.in_use,
                        'age_seconds': c.stats.age_seconds,
                        'idle_seconds': c.stats.idle_seconds,
                        'total_queries': c.stats.total_queries,
                        'total_errors': c.stats.total_errors,
                        'avg_query_time_ms': c.stats.avg_query_time_ms
                    }
                    for c in self._connections.values()
                ]
            }
    
    def close(self):
        """Close the connection pool"""
        logger.info("Closing connection pool")
        
        # Signal shutdown
        self._shutdown.set()
        
        # Wait for health check thread
        if self._health_check_thread:
            self._health_check_thread.join(timeout=5.0)
        
        # Close all connections
        with self._lock:
            for pooled in list(self._connections.values()):
                self._destroy_connection(pooled)
        
        logger.info("Connection pool closed")


class RetryableDatabase:
    """Database wrapper with automatic retry logic"""
    
    def __init__(self, pool: ConnectionPool):
        self.pool = pool
    
    def execute_with_retry(self, query: str, params=None, max_retries: int = 3):
        """Execute a query with automatic retry on failure"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                with self.pool.get_connection() as conn:
                    if params:
                        return conn.execute(query, params).fetchall()
                    else:
                        return conn.execute(query).fetchall()
                        
            except sqlite3.OperationalError as e:
                last_error = e
                if "database is locked" in str(e):
                    # Exponential backoff for lock errors
                    delay = 0.1 * (2 ** attempt)
                    logger.warning(f"Database locked, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    raise
            except Exception as e:
                # Don't retry on other errors
                raise
        
        # Max retries exceeded
        raise last_error or RuntimeError(f"Failed after {max_retries} attempts")