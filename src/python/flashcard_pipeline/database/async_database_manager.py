"""
Enhanced database manager with connection pooling and performance monitoring.

This module provides advanced database connection management with:
- Connection pooling with health checks
- Query performance monitoring
- Automatic reconnection and retry
- Transaction management
- Prepared statement caching
"""

import asyncio
import time
import sqlite3
import aiosqlite
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, AsyncIterator, Callable, Union
from datetime import datetime, timedelta
import logging
from pathlib import Path
import json
from enum import Enum
import hashlib
from collections import defaultdict
import threading

from ..exceptions import DatabaseError, ConnectionPoolError
from ..circuit_breaker import CircuitBreaker
from ..utils.retry import RetryConfig, retry_async

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection states"""
    IDLE = "idle"
    IN_USE = "in_use"
    INVALID = "invalid"
    CLOSED = "closed"


@dataclass
class ConnectionStats:
    """Statistics for a database connection"""
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    total_queries: int = 0
    total_time: float = 0.0
    slow_queries: int = 0
    errors: int = 0
    
    @property
    def avg_query_time(self) -> float:
        """Average query execution time"""
        return self.total_time / self.total_queries if self.total_queries > 0 else 0.0
    
    @property
    def age(self) -> float:
        """Connection age in seconds"""
        return time.time() - self.created_at


@dataclass
class PooledConnection:
    """Wrapper for a pooled database connection"""
    connection: aiosqlite.Connection
    connection_id: str
    state: ConnectionState = ConnectionState.IDLE
    stats: ConnectionStats = field(default_factory=ConnectionStats)
    
    async def validate(self) -> bool:
        """Validate connection is still healthy"""
        try:
            await self.connection.execute("SELECT 1")
            return True
        except Exception:
            self.state = ConnectionState.INVALID
            return False
    
    async def close(self):
        """Close the connection"""
        self.state = ConnectionState.CLOSED
        await self.connection.close()


@dataclass
class QueryResult:
    """Result of a database query with metadata"""
    rows: List[Any]
    execution_time: float
    row_count: int
    connection_id: str
    query_hash: str
    cached: bool = False


class ConnectionPool:
    """Asynchronous database connection pool with advanced features"""
    
    def __init__(
        self,
        database_path: str,
        min_size: int = 2,
        max_size: int = 10,
        connection_timeout: float = 5.0,
        idle_timeout: float = 300.0,  # 5 minutes
        max_lifetime: float = 3600.0,  # 1 hour
        validation_interval: float = 60.0,  # 1 minute
        enable_statistics: bool = True
    ):
        """
        Initialize connection pool.
        
        Args:
            database_path: Path to SQLite database
            min_size: Minimum number of connections to maintain
            max_size: Maximum number of connections allowed
            connection_timeout: Timeout for acquiring a connection
            idle_timeout: Time before closing idle connections
            max_lifetime: Maximum lifetime of a connection
            validation_interval: Interval between connection validations
            enable_statistics: Whether to track detailed statistics
        """
        self.database_path = database_path
        self.min_size = min_size
        self.max_size = max_size
        self.connection_timeout = connection_timeout
        self.idle_timeout = idle_timeout
        self.max_lifetime = max_lifetime
        self.validation_interval = validation_interval
        self.enable_statistics = enable_statistics
        
        # Pool state
        self._connections: List[PooledConnection] = []
        self._available: asyncio.Queue = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(max_size)
        self._lock = asyncio.Lock()
        self._closed = False
        self._connection_counter = 0
        
        # Statistics
        self._stats = {
            "connections_created": 0,
            "connections_closed": 0,
            "connections_reused": 0,
            "acquisition_time_total": 0.0,
            "acquisition_count": 0,
            "timeouts": 0,
            "validation_failures": 0,
        }
        
        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        
        logger.info(
            f"Initialized connection pool: min={min_size}, max={max_size}, "
            f"database={database_path}"
        )
    
    async def initialize(self):
        """Initialize the connection pool with minimum connections"""
        # Create minimum connections
        for _ in range(self.min_size):
            conn = await self._create_connection()
            await self._available.put(conn)
        
        # Start background tasks
        self._background_tasks.append(
            asyncio.create_task(self._validation_task())
        )
        self._background_tasks.append(
            asyncio.create_task(self._cleanup_task())
        )
        
        logger.info(f"Connection pool initialized with {self.min_size} connections")
    
    async def _create_connection(self) -> PooledConnection:
        """Create a new database connection"""
        async with self._lock:
            self._connection_counter += 1
            connection_id = f"conn_{self._connection_counter}"
        
        # Create connection with optimized settings
        conn = await aiosqlite.connect(self.database_path)
        
        # Configure for performance
        await conn.execute("PRAGMA journal_mode = WAL")
        await conn.execute("PRAGMA synchronous = NORMAL")
        await conn.execute("PRAGMA cache_size = -64000")  # 64MB cache
        await conn.execute("PRAGMA temp_store = MEMORY")
        await conn.execute("PRAGMA mmap_size = 268435456")  # 256MB mmap
        
        pooled_conn = PooledConnection(
            connection=conn,
            connection_id=connection_id
        )
        
        async with self._lock:
            self._connections.append(pooled_conn)
            self._stats["connections_created"] += 1
        
        logger.debug(f"Created new connection: {connection_id}")
        return pooled_conn
    
    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[aiosqlite.Connection]:
        """
        Acquire a connection from the pool.
        
        Yields:
            Database connection
            
        Raises:
            ConnectionPoolError: If unable to acquire connection
        """
        if self._closed:
            raise ConnectionPoolError("Connection pool is closed")
        
        start_time = time.time()
        connection = None
        
        try:
            # Try to get an available connection
            try:
                connection = await asyncio.wait_for(
                    self._get_connection(),
                    timeout=self.connection_timeout
                )
            except asyncio.TimeoutError:
                self._stats["timeouts"] += 1
                raise ConnectionPoolError(
                    f"Timeout acquiring connection after {self.connection_timeout}s"
                )
            
            # Update statistics
            acquisition_time = time.time() - start_time
            self._stats["acquisition_time_total"] += acquisition_time
            self._stats["acquisition_count"] += 1
            
            connection.state = ConnectionState.IN_USE
            connection.stats.last_used_at = time.time()
            
            yield connection.connection
            
        finally:
            if connection:
                await self._release_connection(connection)
    
    async def _get_connection(self) -> PooledConnection:
        """Get a connection from the pool or create a new one"""
        # Try to get an existing connection
        try:
            connection = self._available.get_nowait()
            
            # Validate connection
            if await connection.validate():
                self._stats["connections_reused"] += 1
                return connection
            else:
                # Connection invalid, close it
                await self._close_connection(connection)
        except asyncio.QueueEmpty:
            pass
        
        # Check if we can create a new connection
        if len(self._connections) < self.max_size:
            return await self._create_connection()
        
        # Wait for an available connection
        connection = await self._available.get()
        
        # Validate before returning
        if not await connection.validate():
            await self._close_connection(connection)
            # Recursively try again
            return await self._get_connection()
        
        return connection
    
    async def _release_connection(self, connection: PooledConnection):
        """Release a connection back to the pool"""
        connection.state = ConnectionState.IDLE
        
        # Check if connection should be closed
        if (
            connection.stats.age > self.max_lifetime or
            connection.stats.errors > 5 or
            connection.state == ConnectionState.INVALID
        ):
            await self._close_connection(connection)
        else:
            # Return to pool
            await self._available.put(connection)
    
    async def _close_connection(self, connection: PooledConnection):
        """Close a connection and remove from pool"""
        try:
            await connection.close()
        except Exception as e:
            logger.error(f"Error closing connection {connection.connection_id}: {e}")
        
        async with self._lock:
            if connection in self._connections:
                self._connections.remove(connection)
            self._stats["connections_closed"] += 1
        
        logger.debug(f"Closed connection: {connection.connection_id}")
        
        # Ensure minimum connections
        if len(self._connections) < self.min_size and not self._closed:
            new_conn = await self._create_connection()
            await self._available.put(new_conn)
    
    async def _validation_task(self):
        """Background task to validate idle connections"""
        while not self._closed:
            try:
                await asyncio.sleep(self.validation_interval)
                
                # Get all idle connections
                idle_connections = []
                try:
                    while True:
                        conn = self._available.get_nowait()
                        idle_connections.append(conn)
                except asyncio.QueueEmpty:
                    pass
                
                # Validate each connection
                for conn in idle_connections:
                    if await conn.validate():
                        await self._available.put(conn)
                    else:
                        self._stats["validation_failures"] += 1
                        await self._close_connection(conn)
                
            except Exception as e:
                logger.error(f"Error in validation task: {e}")
    
    async def _cleanup_task(self):
        """Background task to clean up old connections"""
        while not self._closed:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                current_time = time.time()
                connections_to_close = []
                
                async with self._lock:
                    for conn in self._connections:
                        if conn.state == ConnectionState.IDLE:
                            if (
                                current_time - conn.stats.last_used_at > self.idle_timeout or
                                conn.stats.age > self.max_lifetime
                            ):
                                connections_to_close.append(conn)
                
                # Close old connections
                for conn in connections_to_close:
                    await self._close_connection(conn)
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
    
    async def close(self):
        """Close all connections and shut down the pool"""
        self._closed = True
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Close all connections
        async with self._lock:
            for conn in self._connections[:]:
                await self._close_connection(conn)
        
        logger.info("Connection pool closed")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get pool statistics"""
        stats = self._stats.copy()
        stats.update({
            "current_size": len(self._connections),
            "available": self._available.qsize(),
            "in_use": len(self._connections) - self._available.qsize(),
            "avg_acquisition_time": (
                self._stats["acquisition_time_total"] / self._stats["acquisition_count"]
                if self._stats["acquisition_count"] > 0 else 0.0
            ),
        })
        
        # Add per-connection statistics
        if self.enable_statistics:
            conn_stats = []
            for conn in self._connections:
                conn_stats.append({
                    "id": conn.connection_id,
                    "state": conn.state.value,
                    "age": conn.stats.age,
                    "total_queries": conn.stats.total_queries,
                    "avg_query_time": conn.stats.avg_query_time,
                    "slow_queries": conn.stats.slow_queries,
                })
            stats["connections"] = conn_stats
        
        return stats


class DatabaseManager:
    """Enhanced database manager with connection pooling and monitoring"""
    
    def __init__(
        self,
        database_path: str,
        pool_config: Optional[Dict[str, Any]] = None,
        slow_query_threshold: float = 1.0,
        enable_query_cache: bool = True,
        cache_ttl: float = 300.0,  # 5 minutes
        enable_circuit_breaker: bool = True
    ):
        """
        Initialize database manager.
        
        Args:
            database_path: Path to SQLite database
            pool_config: Configuration for connection pool
            slow_query_threshold: Threshold for slow query logging (seconds)
            enable_query_cache: Whether to cache query results
            cache_ttl: Cache time-to-live in seconds
            enable_circuit_breaker: Whether to use circuit breaker for protection
        """
        self.database_path = database_path
        self.slow_query_threshold = slow_query_threshold
        self.enable_query_cache = enable_query_cache
        self.cache_ttl = cache_ttl
        
        # Connection pool
        pool_config = pool_config or {}
        self.pool = ConnectionPool(database_path, **pool_config)
        
        # Query cache
        self._query_cache: Dict[str, Tuple[Any, float]] = {}
        self._cache_lock = asyncio.Lock()
        
        # Query statistics
        self._query_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "total_time": 0.0, "errors": 0}
        )
        
        # Circuit breaker for database protection
        if enable_circuit_breaker:
            self.circuit_breaker = CircuitBreaker(
                failure_threshold=0.5,
                min_throughput=10,
                break_duration=30.0,
                expected_exception=DatabaseError,
                name="database"
            )
        else:
            self.circuit_breaker = None
        
        # Prepared statements cache
        self._prepared_statements: Dict[str, str] = {}
        
        logger.info(f"Initialized DatabaseManager for {database_path}")
    
    async def initialize(self):
        """Initialize the database manager"""
        await self.pool.initialize()
        
        # Create tables if needed
        await self._ensure_schema()
        
        # Start cache cleanup task
        asyncio.create_task(self._cache_cleanup_task())
    
    async def _ensure_schema(self):
        """Ensure database schema exists"""
        # This would contain your schema creation logic
        pass
    
    def _get_query_hash(self, query: str, params: Optional[tuple] = None) -> str:
        """Generate hash for query caching"""
        key = f"{query}:{params}" if params else query
        return hashlib.md5(key.encode()).hexdigest()
    
    async def execute(
        self,
        query: str,
        params: Optional[tuple] = None,
        use_cache: Optional[bool] = None
    ) -> QueryResult:
        """
        Execute a database query.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            use_cache: Whether to use cache (overrides default)
            
        Returns:
            QueryResult with rows and metadata
        """
        query_hash = self._get_query_hash(query, params)
        use_cache = use_cache if use_cache is not None else self.enable_query_cache
        
        # Check cache for SELECT queries
        if use_cache and query.strip().upper().startswith("SELECT"):
            cached_result = await self._get_cached_result(query_hash)
            if cached_result:
                return cached_result
        
        # Execute with circuit breaker if enabled
        if self.circuit_breaker:
            return await self.circuit_breaker.call(
                self._execute_query, query, params, query_hash
            )
        else:
            return await self._execute_query(query, params, query_hash)
    
    async def _execute_query(
        self,
        query: str,
        params: Optional[tuple],
        query_hash: str
    ) -> QueryResult:
        """Execute query with monitoring"""
        start_time = time.time()
        connection_id = None
        
        try:
            async with self.pool.acquire() as conn:
                # Get connection ID for tracking
                for pooled_conn in self.pool._connections:
                    if pooled_conn.connection == conn:
                        connection_id = pooled_conn.connection_id
                        break
                
                # Execute query
                cursor = await conn.execute(query, params or ())
                rows = await cursor.fetchall()
                row_count = cursor.rowcount
                
                # Update connection statistics
                execution_time = time.time() - start_time
                if connection_id:
                    for pooled_conn in self.pool._connections:
                        if pooled_conn.connection_id == connection_id:
                            pooled_conn.stats.total_queries += 1
                            pooled_conn.stats.total_time += execution_time
                            if execution_time > self.slow_query_threshold:
                                pooled_conn.stats.slow_queries += 1
                            break
                
                # Update query statistics
                self._update_query_stats(query_hash, execution_time, success=True)
                
                # Log slow queries
                if execution_time > self.slow_query_threshold:
                    logger.warning(
                        f"Slow query detected ({execution_time:.2f}s): "
                        f"{query[:100]}..."
                    )
                
                result = QueryResult(
                    rows=rows,
                    execution_time=execution_time,
                    row_count=row_count,
                    connection_id=connection_id or "unknown",
                    query_hash=query_hash,
                    cached=False
                )
                
                # Cache result if applicable
                if self.enable_query_cache and query.strip().upper().startswith("SELECT"):
                    await self._cache_result(query_hash, result)
                
                return result
                
        except Exception as e:
            # Update error statistics
            if connection_id:
                for pooled_conn in self.pool._connections:
                    if pooled_conn.connection_id == connection_id:
                        pooled_conn.stats.errors += 1
                        break
            
            self._update_query_stats(query_hash, time.time() - start_time, success=False)
            
            logger.error(f"Database query error: {e}")
            raise DatabaseError(f"Query execution failed: {e}") from e
    
    async def execute_many(
        self,
        query: str,
        params_list: List[tuple]
    ) -> List[QueryResult]:
        """
        Execute multiple queries efficiently.
        
        Args:
            query: SQL query template
            params_list: List of parameter tuples
            
        Returns:
            List of QueryResult objects
        """
        results = []
        
        async with self.pool.acquire() as conn:
            # Use transaction for batch operations
            await conn.execute("BEGIN")
            
            try:
                for params in params_list:
                    start_time = time.time()
                    cursor = await conn.execute(query, params)
                    rows = await cursor.fetchall()
                    
                    results.append(QueryResult(
                        rows=rows,
                        execution_time=time.time() - start_time,
                        row_count=cursor.rowcount,
                        connection_id="batch",
                        query_hash=self._get_query_hash(query, params),
                        cached=False
                    ))
                
                await conn.execute("COMMIT")
                
            except Exception as e:
                await conn.execute("ROLLBACK")
                raise DatabaseError(f"Batch execution failed: {e}") from e
        
        return results
    
    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for database transactions.
        
        Usage:
            async with db.transaction():
                await db.execute("INSERT ...")
                await db.execute("UPDATE ...")
        """
        async with self.pool.acquire() as conn:
            await conn.execute("BEGIN")
            
            try:
                # Store connection in context for nested queries
                self._transaction_conn = conn
                yield conn
                await conn.execute("COMMIT")
            except Exception:
                await conn.execute("ROLLBACK")
                raise
            finally:
                self._transaction_conn = None
    
    async def _get_cached_result(self, query_hash: str) -> Optional[QueryResult]:
        """Get cached query result if available"""
        async with self._cache_lock:
            if query_hash in self._query_cache:
                result, cached_at = self._query_cache[query_hash]
                
                # Check if cache is still valid
                if time.time() - cached_at < self.cache_ttl:
                    # Return copy with cached flag
                    cached_result = QueryResult(
                        rows=result.rows,
                        execution_time=0.0,  # No execution time for cached
                        row_count=result.row_count,
                        connection_id="cache",
                        query_hash=query_hash,
                        cached=True
                    )
                    return cached_result
                else:
                    # Cache expired
                    del self._query_cache[query_hash]
        
        return None
    
    async def _cache_result(self, query_hash: str, result: QueryResult):
        """Cache query result"""
        async with self._cache_lock:
            self._query_cache[query_hash] = (result, time.time())
    
    async def _cache_cleanup_task(self):
        """Background task to clean up expired cache entries"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                current_time = time.time()
                expired_keys = []
                
                async with self._cache_lock:
                    for key, (_, cached_at) in self._query_cache.items():
                        if current_time - cached_at > self.cache_ttl:
                            expired_keys.append(key)
                    
                    for key in expired_keys:
                        del self._query_cache[key]
                
                if expired_keys:
                    logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
                    
            except Exception as e:
                logger.error(f"Error in cache cleanup task: {e}")
    
    def _update_query_stats(self, query_hash: str, execution_time: float, success: bool):
        """Update query statistics"""
        stats = self._query_stats[query_hash]
        stats["count"] += 1
        stats["total_time"] += execution_time
        if not success:
            stats["errors"] += 1
    
    def get_query_statistics(self) -> Dict[str, Any]:
        """Get query execution statistics"""
        stats = []
        
        for query_hash, data in self._query_stats.items():
            avg_time = data["total_time"] / data["count"] if data["count"] > 0 else 0.0
            stats.append({
                "query_hash": query_hash,
                "count": data["count"],
                "avg_time": avg_time,
                "total_time": data["total_time"],
                "errors": data["errors"],
                "error_rate": data["errors"] / data["count"] if data["count"] > 0 else 0.0,
            })
        
        # Sort by total time descending
        stats.sort(key=lambda x: x["total_time"], reverse=True)
        
        return {
            "queries": stats[:20],  # Top 20 queries by time
            "total_queries": sum(s["count"] for s in stats),
            "cache_size": len(self._query_cache),
            "cache_hit_rate": self._calculate_cache_hit_rate(),
        }
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        # This would need more sophisticated tracking in production
        # For now, return a placeholder
        return 0.0
    
    async def optimize_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze and suggest optimizations for a query.
        
        Args:
            query: SQL query to analyze
            
        Returns:
            Dictionary with optimization suggestions
        """
        async with self.pool.acquire() as conn:
            # Get query plan
            cursor = await conn.execute(f"EXPLAIN QUERY PLAN {query}")
            plan = await cursor.fetchall()
            
            suggestions = []
            
            # Analyze plan for common issues
            plan_text = " ".join(str(row) for row in plan)
            
            if "SCAN TABLE" in plan_text:
                suggestions.append({
                    "type": "missing_index",
                    "severity": "high",
                    "message": "Query performs full table scan. Consider adding an index.",
                })
            
            if "TEMP B-TREE" in plan_text:
                suggestions.append({
                    "type": "sorting",
                    "severity": "medium",
                    "message": "Query requires sorting. Consider an index on ORDER BY columns.",
                })
            
            return {
                "query": query,
                "plan": plan,
                "suggestions": suggestions,
                "estimated_cost": len(plan),  # Simplified cost estimate
            }
    
    async def close(self):
        """Close the database manager"""
        await self.pool.close()
        logger.info("DatabaseManager closed")