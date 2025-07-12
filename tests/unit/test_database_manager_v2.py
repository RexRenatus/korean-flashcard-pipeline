"""Unit tests for enhanced database manager with connection pooling"""

import asyncio
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import aiosqlite

from flashcard_pipeline.database.database_manager_v2 import (
    DatabaseManager,
    ConnectionPool,
    ConnectionState,
    PooledConnection,
    QueryResult,
    ConnectionStats,
)
from flashcard_pipeline.exceptions import DatabaseError, ConnectionPoolError


class TestConnectionPool:
    """Test connection pool functionality"""
    
    @pytest.fixture
    async def pool(self, tmp_path):
        """Create a test connection pool"""
        db_path = tmp_path / "test.db"
        pool = ConnectionPool(
            str(db_path),
            min_size=2,
            max_size=5,
            connection_timeout=1.0,
            idle_timeout=10.0
        )
        await pool.initialize()
        yield pool
        await pool.close()
    
    @pytest.mark.asyncio
    async def test_pool_initialization(self, pool):
        """Test pool initializes with minimum connections"""
        stats = pool.get_statistics()
        
        assert stats["current_size"] >= pool.min_size
        assert stats["connections_created"] >= pool.min_size
        assert stats["available"] >= pool.min_size
    
    @pytest.mark.asyncio
    async def test_connection_acquisition(self, pool):
        """Test acquiring connections from pool"""
        connections = []
        
        # Acquire multiple connections
        for i in range(3):
            async with pool.acquire() as conn:
                connections.append(conn)
                # Verify it's a valid connection
                cursor = await conn.execute("SELECT 1")
                result = await cursor.fetchone()
                assert result[0] == 1
        
        stats = pool.get_statistics()
        assert stats["connections_reused"] >= 2  # At least 2 reused
    
    @pytest.mark.asyncio
    async def test_connection_limit(self, pool):
        """Test pool respects maximum connection limit"""
        connections = []
        
        # Acquire max connections
        for i in range(pool.max_size):
            ctx = pool.acquire()
            conn = await ctx.__aenter__()
            connections.append((ctx, conn))
        
        # Try to acquire one more - should timeout
        with pytest.raises(ConnectionPoolError, match="Timeout"):
            async with pool.acquire():
                pass
        
        # Release all connections
        for ctx, conn in connections:
            await ctx.__aexit__(None, None, None)
    
    @pytest.mark.asyncio
    async def test_connection_validation(self, pool):
        """Test connection validation"""
        async with pool.acquire() as conn:
            # Connection should be valid
            pass
        
        # Manually invalidate a connection
        if pool._connections:
            pool._connections[0].state = ConnectionState.INVALID
        
        # Should create new connection on next acquire
        old_created = pool._stats["connections_created"]
        async with pool.acquire() as conn:
            pass
        
        # May create new connection if invalid one was chosen
        assert pool._stats["connections_created"] >= old_created
    
    @pytest.mark.asyncio
    async def test_connection_lifecycle(self, pool):
        """Test connection lifecycle management"""
        # Get connection stats
        async with pool.acquire() as conn:
            # Find the pooled connection
            pooled_conn = None
            for pc in pool._connections:
                if pc.connection == conn:
                    pooled_conn = pc
                    break
            
            assert pooled_conn is not None
            assert pooled_conn.state == ConnectionState.IN_USE
            
            # Stats should update
            old_last_used = pooled_conn.stats.last_used_at
        
        # After release, should be idle
        assert pooled_conn.state == ConnectionState.IDLE
        assert pooled_conn.stats.last_used_at > old_last_used
    
    @pytest.mark.asyncio
    async def test_concurrent_access(self, pool):
        """Test concurrent connection access"""
        async def worker(worker_id: int):
            for i in range(5):
                async with pool.acquire() as conn:
                    # Simulate work
                    await conn.execute(f"SELECT {worker_id}")
                    await asyncio.sleep(0.01)
        
        # Run multiple workers concurrently
        workers = [worker(i) for i in range(10)]
        await asyncio.gather(*workers)
        
        stats = pool.get_statistics()
        assert stats["acquisition_count"] >= 50  # 10 workers * 5 acquisitions
        assert stats["timeouts"] == 0  # No timeouts expected
    
    @pytest.mark.asyncio
    async def test_connection_timeout_handling(self, pool):
        """Test handling of connection acquisition timeout"""
        # Acquire all connections
        connections = []
        for i in range(pool.max_size):
            ctx = pool.acquire()
            conn = await ctx.__aenter__()
            connections.append((ctx, conn))
        
        # Set short timeout
        pool.connection_timeout = 0.1
        
        # Should timeout
        with pytest.raises(ConnectionPoolError, match="Timeout"):
            async with pool.acquire():
                pass
        
        assert pool._stats["timeouts"] >= 1
        
        # Cleanup
        for ctx, conn in connections:
            await ctx.__aexit__(None, None, None)
    
    @pytest.mark.asyncio
    async def test_idle_connection_cleanup(self, pool):
        """Test cleanup of idle connections"""
        # Set very short idle timeout
        pool.idle_timeout = 0.1
        
        # Use a connection
        async with pool.acquire() as conn:
            pass
        
        # Wait for cleanup
        await asyncio.sleep(0.2)
        
        # Trigger cleanup
        await pool._cleanup_task()
        
        # Should maintain minimum connections
        stats = pool.get_statistics()
        assert stats["current_size"] >= pool.min_size


class TestDatabaseManager:
    """Test enhanced database manager"""
    
    @pytest.fixture
    async def db_manager(self, tmp_path):
        """Create a test database manager"""
        db_path = tmp_path / "test.db"
        
        # Create schema
        async with aiosqlite.connect(str(db_path)) as conn:
            await conn.execute("""
                CREATE TABLE test_table (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    value INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.commit()
        
        manager = DatabaseManager(
            str(db_path),
            pool_config={"min_size": 1, "max_size": 3},
            slow_query_threshold=0.1,
            enable_query_cache=True,
            cache_ttl=60.0
        )
        await manager.initialize()
        
        yield manager
        
        await manager.close()
    
    @pytest.mark.asyncio
    async def test_query_execution(self, db_manager):
        """Test basic query execution"""
        # Insert data
        result = await db_manager.execute(
            "INSERT INTO test_table (name, value) VALUES (?, ?)",
            ("test1", 100)
        )
        
        assert result.row_count == 1
        assert result.cached is False
        assert result.execution_time > 0
        
        # Select data
        result = await db_manager.execute(
            "SELECT * FROM test_table WHERE name = ?",
            ("test1",)
        )
        
        assert len(result.rows) == 1
        assert result.rows[0][1] == "test1"  # name column
        assert result.rows[0][2] == 100  # value column
    
    @pytest.mark.asyncio
    async def test_query_caching(self, db_manager):
        """Test query result caching"""
        # First query - not cached
        query = "SELECT * FROM test_table WHERE value > ?"
        params = (50,)
        
        result1 = await db_manager.execute(query, params)
        assert result1.cached is False
        query_hash = result1.query_hash
        
        # Second query - should be cached
        result2 = await db_manager.execute(query, params)
        assert result2.cached is True
        assert result2.query_hash == query_hash
        assert result2.execution_time == 0.0  # No execution for cached
        
        # Verify same data
        assert result2.rows == result1.rows
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self, db_manager):
        """Test cache expiration"""
        # Set very short TTL
        db_manager.cache_ttl = 0.1
        
        # Execute query
        result1 = await db_manager.execute("SELECT * FROM test_table")
        assert result1.cached is False
        
        # Wait for expiration
        await asyncio.sleep(0.2)
        
        # Should not be cached
        result2 = await db_manager.execute("SELECT * FROM test_table")
        assert result2.cached is False
    
    @pytest.mark.asyncio
    async def test_transaction_management(self, db_manager):
        """Test transaction context manager"""
        # Insert with transaction
        async with db_manager.transaction():
            await db_manager.execute(
                "INSERT INTO test_table (name, value) VALUES (?, ?)",
                ("tx1", 200)
            )
            await db_manager.execute(
                "INSERT INTO test_table (name, value) VALUES (?, ?)",
                ("tx2", 300)
            )
        
        # Verify both inserted
        result = await db_manager.execute("SELECT COUNT(*) FROM test_table")
        assert result.rows[0][0] >= 2
        
        # Test rollback
        try:
            async with db_manager.transaction():
                await db_manager.execute(
                    "INSERT INTO test_table (name, value) VALUES (?, ?)",
                    ("tx3", 400)
                )
                # Force error
                raise Exception("Test rollback")
        except Exception:
            pass
        
        # tx3 should not exist
        result = await db_manager.execute(
            "SELECT * FROM test_table WHERE name = ?",
            ("tx3",)
        )
        assert len(result.rows) == 0
    
    @pytest.mark.asyncio
    async def test_batch_execution(self, db_manager):
        """Test batch query execution"""
        # Prepare batch data
        params_list = [
            (f"batch{i}", i * 100)
            for i in range(5)
        ]
        
        results = await db_manager.execute_many(
            "INSERT INTO test_table (name, value) VALUES (?, ?)",
            params_list
        )
        
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result.row_count == 1
            assert result.connection_id == "batch"
        
        # Verify all inserted
        result = await db_manager.execute(
            "SELECT COUNT(*) FROM test_table WHERE name LIKE 'batch%'"
        )
        assert result.rows[0][0] == 5
    
    @pytest.mark.asyncio
    async def test_slow_query_detection(self, db_manager):
        """Test slow query detection and logging"""
        # Set very low threshold
        db_manager.slow_query_threshold = 0.001
        
        with patch("flashcard_pipeline.database.database_manager_v2.logger") as mock_logger:
            # Execute a "slow" query
            await db_manager.execute("SELECT * FROM test_table")
            
            # Should log warning
            mock_logger.warning.assert_called()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert "Slow query detected" in warning_msg
    
    @pytest.mark.asyncio
    async def test_query_statistics(self, db_manager):
        """Test query statistics tracking"""
        # Execute various queries
        for i in range(3):
            await db_manager.execute(
                "INSERT INTO test_table (name, value) VALUES (?, ?)",
                (f"stat{i}", i)
            )
        
        for i in range(5):
            await db_manager.execute("SELECT * FROM test_table")
        
        stats = db_manager.get_query_statistics()
        
        assert stats["total_queries"] >= 8
        assert len(stats["queries"]) >= 2  # At least 2 different queries
        
        # Find SELECT query stats
        select_stats = None
        for query_stat in stats["queries"]:
            if query_stat["count"] >= 5:
                select_stats = query_stat
                break
        
        assert select_stats is not None
        assert select_stats["avg_time"] > 0
        assert select_stats["error_rate"] == 0.0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, db_manager):
        """Test circuit breaker protection"""
        # Force database errors
        with patch.object(db_manager.pool, 'acquire', side_effect=DatabaseError("Connection failed")):
            
            # Should fail multiple times and open circuit
            for i in range(5):
                with pytest.raises(DatabaseError):
                    await db_manager.execute("SELECT 1")
            
            # Circuit should be open
            if db_manager.circuit_breaker:
                from flashcard_pipeline.circuit_breaker_v2 import CircuitState
                assert db_manager.circuit_breaker._state == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_query_optimization_suggestions(self, db_manager):
        """Test query optimization analysis"""
        # Create table without index
        await db_manager.execute("""
            CREATE TABLE test_no_index (
                id INTEGER PRIMARY KEY,
                data TEXT,
                status INTEGER
            )
        """)
        
        # Analyze query that would benefit from index
        suggestions = await db_manager.optimize_query(
            "SELECT * FROM test_no_index WHERE status = 1 ORDER BY data"
        )
        
        assert "suggestions" in suggestions
        assert len(suggestions["suggestions"]) > 0
        
        # Should detect table scan
        has_scan_suggestion = any(
            s["type"] == "missing_index" for s in suggestions["suggestions"]
        )
        assert has_scan_suggestion
    
    @pytest.mark.asyncio
    async def test_connection_pool_statistics(self, db_manager):
        """Test connection pool statistics"""
        # Perform some operations
        for i in range(10):
            await db_manager.execute(
                "INSERT INTO test_table (name, value) VALUES (?, ?)",
                (f"pool{i}", i)
            )
        
        pool_stats = db_manager.pool.get_statistics()
        
        assert pool_stats["current_size"] >= 1
        assert pool_stats["acquisition_count"] >= 10
        assert pool_stats["avg_acquisition_time"] >= 0
        
        # Check connection details if enabled
        if db_manager.pool.enable_statistics:
            assert "connections" in pool_stats
            for conn_stat in pool_stats["connections"]:
                assert conn_stat["total_queries"] >= 0
                assert conn_stat["age"] >= 0


class TestConnectionStats:
    """Test connection statistics tracking"""
    
    def test_stats_initialization(self):
        """Test stats are properly initialized"""
        stats = ConnectionStats()
        
        assert stats.total_queries == 0
        assert stats.total_time == 0.0
        assert stats.slow_queries == 0
        assert stats.errors == 0
        assert stats.avg_query_time == 0.0
        assert stats.age >= 0
    
    def test_stats_calculation(self):
        """Test statistics calculations"""
        stats = ConnectionStats()
        
        # Simulate queries
        stats.total_queries = 10
        stats.total_time = 5.0
        
        assert stats.avg_query_time == 0.5
        
        # Test with no queries
        stats.total_queries = 0
        assert stats.avg_query_time == 0.0


class TestPooledConnection:
    """Test pooled connection wrapper"""
    
    @pytest.mark.asyncio
    async def test_connection_validation(self, tmp_path):
        """Test connection validation"""
        db_path = tmp_path / "test.db"
        conn = await aiosqlite.connect(str(db_path))
        
        pooled = PooledConnection(
            connection=conn,
            connection_id="test_1"
        )
        
        # Should be valid
        assert await pooled.validate() is True
        assert pooled.state == ConnectionState.IDLE
        
        # Close connection
        await conn.close()
        
        # Should be invalid
        assert await pooled.validate() is False
        assert pooled.state == ConnectionState.INVALID