"""Integration tests for database and cache optimizations"""

import asyncio
import pytest
import tempfile
import time
from pathlib import Path
from typing import List, Dict, Any
import random

from flashcard_pipeline.database.database_manager_v2 import DatabaseManager
from flashcard_pipeline.database.query_optimizer import QueryOptimizer
from flashcard_pipeline.cache.cache_manager_v2 import CacheManager, CacheStrategy
from flashcard_pipeline.circuit_breaker_v2 import EnhancedCircuitBreaker
from flashcard_pipeline.rate_limiter_v2 import ShardedRateLimiter
from flashcard_pipeline.utils.retry import RetryConfig, retry_async
from flashcard_pipeline.exceptions import DatabaseError


class TestDatabaseCacheIntegration:
    """Test database and cache working together"""
    
    @pytest.fixture
    async def integrated_system(self, tmp_path):
        """Create integrated database and cache system"""
        # Database manager
        db_manager = DatabaseManager(
            str(tmp_path / "test.db"),
            pool_config={
                "min_size": 2,
                "max_size": 5,
            },
            slow_query_threshold=0.1,
            enable_query_cache=True,
            enable_circuit_breaker=True
        )
        await db_manager.initialize()
        
        # Create schema
        await db_manager.execute("""
            CREATE TABLE flashcards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL UNIQUE,
                translation TEXT,
                difficulty INTEGER DEFAULT 3,
                stage1_result TEXT,
                stage2_result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db_manager.execute("""
            CREATE INDEX idx_flashcards_word ON flashcards(word)
        """)
        
        await db_manager.execute("""
            CREATE INDEX idx_flashcards_difficulty ON flashcards(difficulty)
        """)
        
        # Cache manager
        cache_manager = CacheManager(
            l1_config={"max_size": 100},
            l2_config={
                "backend": "disk",
                "disk_path": str(tmp_path / "cache")
            },
            enable_l2=True,
            strategy=CacheStrategy.CACHE_ASIDE
        )
        
        # Query optimizer
        query_optimizer = QueryOptimizer()
        
        yield {
            "db": db_manager,
            "cache": cache_manager,
            "optimizer": query_optimizer
        }
        
        # Cleanup
        await db_manager.close()
        await cache_manager.clear()
    
    @pytest.mark.asyncio
    async def test_cached_database_queries(self, integrated_system):
        """Test database queries with caching"""
        db = integrated_system["db"]
        cache = integrated_system["cache"]
        
        # Insert test data
        test_words = [
            ("안녕하세요", "Hello", 1),
            ("감사합니다", "Thank you", 2),
            ("사랑해요", "I love you", 3),
        ]
        
        for word, translation, difficulty in test_words:
            await db.execute(
                "INSERT INTO flashcards (word, translation, difficulty) VALUES (?, ?, ?)",
                (word, translation, difficulty)
            )
        
        # Define cached query function
        async def get_flashcard_by_word(word: str):
            result = await db.execute(
                "SELECT * FROM flashcards WHERE word = ?",
                (word,)
            )
            return result.rows[0] if result.rows else None
        
        # First query - cache miss
        start_time = time.time()
        flashcard = await cache.get(
            "flashcard:안녕하세요",
            lambda: get_flashcard_by_word("안녕하세요")
        )
        first_query_time = time.time() - start_time
        
        assert flashcard is not None
        assert flashcard[1] == "안녕하세요"
        
        # Second query - cache hit
        start_time = time.time()
        cached_flashcard = await cache.get(
            "flashcard:안녕하세요",
            lambda: get_flashcard_by_word("안녕하세요")
        )
        cached_query_time = time.time() - start_time
        
        assert cached_flashcard == flashcard
        assert cached_query_time < first_query_time * 0.1  # Much faster
        
        # Verify cache statistics
        stats = cache.get_statistics()
        assert stats["l1"]["hit_rate"] > 0
    
    @pytest.mark.asyncio
    async def test_batch_operations_with_cache(self, integrated_system):
        """Test batch database operations with cache warming"""
        db = integrated_system["db"]
        cache = integrated_system["cache"]
        
        # Insert batch data
        batch_data = [
            (f"word_{i}", f"translation_{i}", i % 5 + 1)
            for i in range(50)
        ]
        
        await db.execute_many(
            "INSERT INTO flashcards (word, translation, difficulty) VALUES (?, ?, ?)",
            batch_data
        )
        
        # Warm cache with frequently accessed items
        async def fetch_flashcard(word: str):
            result = await db.execute(
                "SELECT * FROM flashcards WHERE word = ?",
                (word,)
            )
            return result.rows[0] if result.rows else None
        
        # Warm cache with first 10 words
        popular_words = [f"word_{i}" for i in range(10)]
        await cache.warm_cache(
            popular_words,
            fetch_flashcard,
            ttl=300.0
        )
        
        # Access mixed cached and uncached items
        access_times = []
        for i in range(20):
            word = f"word_{i}"
            start_time = time.time()
            
            flashcard = await cache.get(
                f"flashcard:{word}",
                lambda w=word: fetch_flashcard(w)
            )
            
            access_time = time.time() - start_time
            access_times.append((word, access_time))
        
        # Cached items should be faster
        cached_times = [t for w, t in access_times if int(w.split('_')[1]) < 10]
        uncached_times = [t for w, t in access_times if int(w.split('_')[1]) >= 10]
        
        avg_cached = sum(cached_times) / len(cached_times)
        avg_uncached = sum(uncached_times) / len(uncached_times)
        
        assert avg_cached < avg_uncached * 0.5  # Cached much faster
    
    @pytest.mark.asyncio
    async def test_query_optimization_with_caching(self, integrated_system):
        """Test query optimization integrated with caching"""
        db = integrated_system["db"]
        cache = integrated_system["cache"]
        optimizer = integrated_system["optimizer"]
        
        # Insert more test data
        for i in range(100):
            await db.execute(
                "INSERT INTO flashcards (word, translation, difficulty) VALUES (?, ?, ?)",
                (f"test_word_{i}", f"translation_{i}", i % 5 + 1)
            )
        
        # Simulate N+1 query pattern
        async def get_flashcards_inefficient(difficulty: int):
            # First get IDs
            result = await db.execute(
                "SELECT id FROM flashcards WHERE difficulty = ?",
                (difficulty,)
            )
            
            flashcards = []
            for row in result.rows:
                # N+1 pattern - individual query for each
                card_result = await db.execute(
                    "SELECT * FROM flashcards WHERE id = ?",
                    (row[0],)
                )
                if card_result.rows:
                    flashcards.append(card_result.rows[0])
                
                # Track in optimizer
                optimizer.analyze_query(
                    f"SELECT * FROM flashcards WHERE id = {row[0]}",
                    0.01
                )
            
            return flashcards
        
        # Run inefficient query
        await get_flashcards_inefficient(3)
        
        # Check optimizer report
        report = optimizer.get_optimization_report()
        assert report["n1_patterns_detected"] > 0
        
        # Optimized version with caching
        async def get_flashcards_optimized(difficulty: int):
            cache_key = f"flashcards:difficulty:{difficulty}"
            
            async def fetch():
                result = await db.execute(
                    "SELECT * FROM flashcards WHERE difficulty = ?",
                    (difficulty,)
                )
                return result.rows
            
            return await cache.get(cache_key, fetch)
        
        # Compare performance
        start_time = time.time()
        inefficient_result = await get_flashcards_inefficient(4)
        inefficient_time = time.time() - start_time
        
        start_time = time.time()
        optimized_result = await get_flashcards_optimized(4)
        optimized_time = time.time() - start_time
        
        # Optimized should be faster
        assert optimized_time < inefficient_time
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_patterns(self, integrated_system):
        """Test cache invalidation strategies"""
        db = integrated_system["db"]
        cache = integrated_system["cache"]
        
        # Insert and cache data
        await db.execute(
            "INSERT INTO flashcards (word, translation) VALUES (?, ?)",
            ("test", "test translation")
        )
        
        # Cache the query result
        async def get_flashcard():
            result = await db.execute(
                "SELECT * FROM flashcards WHERE word = ?",
                ("test",)
            )
            return result.rows[0] if result.rows else None
        
        # Cache with tags
        flashcard = await cache.get(
            "flashcard:test",
            get_flashcard,
            tags=["flashcard", "word:test"]
        )
        
        assert flashcard[1] == "test"
        
        # Update database
        await db.execute(
            "UPDATE flashcards SET translation = ? WHERE word = ?",
            ("updated translation", "test")
        )
        
        # Cache still has old value
        cached = await cache.get("flashcard:test")
        assert cached[2] == "test translation"  # Old value
        
        # Invalidate by tag
        await cache.delete_by_tag("word:test")
        
        # Now should get updated value
        updated = await cache.get("flashcard:test", get_flashcard)
        assert updated[2] == "updated translation"  # New value
    
    @pytest.mark.asyncio
    async def test_connection_pool_under_load(self, integrated_system):
        """Test connection pool performance under concurrent load"""
        db = integrated_system["db"]
        
        # Insert test data
        for i in range(100):
            await db.execute(
                "INSERT INTO flashcards (word, translation) VALUES (?, ?)",
                (f"load_test_{i}", f"translation_{i}")
            )
        
        # Concurrent workers
        async def worker(worker_id: int, queries: int):
            results = []
            for i in range(queries):
                try:
                    # Random query
                    word_id = random.randint(0, 99)
                    result = await db.execute(
                        "SELECT * FROM flashcards WHERE word = ?",
                        (f"load_test_{word_id}",)
                    )
                    results.append(("success", len(result.rows)))
                except Exception as e:
                    results.append(("error", str(e)))
                
                # Small delay
                await asyncio.sleep(0.01)
            
            return results
        
        # Run concurrent workers
        workers = 10
        queries_per_worker = 20
        
        start_time = time.time()
        tasks = [
            worker(i, queries_per_worker)
            for i in range(workers)
        ]
        
        all_results = await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        # Analyze results
        total_queries = workers * queries_per_worker
        successful = sum(
            1 for worker_results in all_results
            for status, _ in worker_results
            if status == "success"
        )
        
        # Get pool statistics
        pool_stats = db.pool.get_statistics()
        
        print(f"\nConnection Pool Performance:")
        print(f"  Total queries: {total_queries}")
        print(f"  Successful: {successful}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Queries/sec: {total_queries/duration:.0f}")
        print(f"  Pool size: {pool_stats['current_size']}")
        print(f"  Connections reused: {pool_stats['connections_reused']}")
        print(f"  Avg acquisition time: {pool_stats['avg_acquisition_time']*1000:.1f}ms")
        
        # Should handle all queries successfully
        assert successful == total_queries
        assert pool_stats['timeouts'] == 0
        assert pool_stats['connections_reused'] > 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_with_cache_fallback(self, integrated_system):
        """Test circuit breaker with cache as fallback"""
        db = integrated_system["db"]
        cache = integrated_system["cache"]
        
        # Insert and cache some data
        await db.execute(
            "INSERT INTO flashcards (word, translation) VALUES (?, ?)",
            ("fallback_test", "cached translation")
        )
        
        async def get_flashcard_with_fallback(word: str):
            try:
                # Try database first
                result = await db.execute(
                    "SELECT * FROM flashcards WHERE word = ?",
                    (word,)
                )
                data = result.rows[0] if result.rows else None
                
                # Cache the result
                if data:
                    await cache.set(f"fallback:{word}", data)
                
                return data
            except DatabaseError:
                # Fallback to cache
                cached = await cache.get(f"fallback:{word}")
                if cached:
                    return cached
                raise
        
        # First call - populate cache
        flashcard = await get_flashcard_with_fallback("fallback_test")
        assert flashcard[2] == "cached translation"
        
        # Simulate database failure
        original_execute = db.execute
        db.execute = AsyncMock(side_effect=DatabaseError("Connection failed"))
        
        # Should fallback to cache
        cached_flashcard = await get_flashcard_with_fallback("fallback_test")
        assert cached_flashcard[2] == "cached translation"
        
        # Restore
        db.execute = original_execute


class TestPerformanceBenchmarks:
    """Performance benchmarks for database and cache optimizations"""
    
    @pytest.mark.asyncio
    async def test_query_performance_improvement(self, tmp_path):
        """Benchmark query performance improvements"""
        # Setup
        db_manager = DatabaseManager(
            str(tmp_path / "benchmark.db"),
            pool_config={"min_size": 3, "max_size": 10},
            enable_query_cache=True
        )
        await db_manager.initialize()
        
        # Create tables
        await db_manager.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                email TEXT NOT NULL,
                status INTEGER DEFAULT 1
            )
        """)
        
        # Insert test data
        for i in range(1000):
            await db_manager.execute(
                "INSERT INTO users (username, email, status) VALUES (?, ?, ?)",
                (f"user{i}", f"user{i}@example.com", i % 3)
            )
        
        # Benchmark without index
        start_time = time.time()
        for i in range(10):
            await db_manager.execute(
                "SELECT * FROM users WHERE email = ?",
                (f"user{random.randint(0, 999)}@example.com",),
                use_cache=False  # Disable cache for fair comparison
            )
        without_index_time = time.time() - start_time
        
        # Add index
        await db_manager.execute("CREATE INDEX idx_users_email ON users(email)")
        
        # Benchmark with index
        start_time = time.time()
        for i in range(10):
            await db_manager.execute(
                "SELECT * FROM users WHERE email = ?",
                (f"user{random.randint(0, 999)}@example.com",),
                use_cache=False
            )
        with_index_time = time.time() - start_time
        
        print(f"\nQuery Performance:")
        print(f"  Without index: {without_index_time:.3f}s")
        print(f"  With index: {with_index_time:.3f}s")
        print(f"  Improvement: {(without_index_time/with_index_time - 1)*100:.1f}%")
        
        # Index should provide significant improvement
        assert with_index_time < without_index_time * 0.5
        
        await db_manager.close()
    
    @pytest.mark.asyncio
    async def test_cache_hit_rate_optimization(self, tmp_path):
        """Benchmark cache hit rate improvements"""
        cache = CacheManager(
            l1_config={"max_size": 100, "eviction_policy": EvictionPolicy.LRU},
            l2_config={"backend": "disk", "disk_path": str(tmp_path / "cache")},
            enable_l2=True
        )
        
        # Simulate access patterns
        access_pattern = []
        # 80% of accesses to 20% of keys (Pareto principle)
        hot_keys = [f"hot_{i}" for i in range(20)]
        cold_keys = [f"cold_{i}" for i in range(80)]
        
        for _ in range(1000):
            if random.random() < 0.8:
                key = random.choice(hot_keys)
            else:
                key = random.choice(cold_keys)
            access_pattern.append(key)
        
        # Benchmark cache performance
        compute_count = 0
        
        async def compute_value(key: str):
            nonlocal compute_count
            compute_count += 1
            await asyncio.sleep(0.001)  # Simulate computation
            return f"value_for_{key}"
        
        start_time = time.time()
        for key in access_pattern:
            await cache.get(key, lambda k=key: compute_value(k))
        
        duration = time.time() - start_time
        
        stats = cache.get_statistics()
        
        print(f"\nCache Performance:")
        print(f"  Total accesses: {len(access_pattern)}")
        print(f"  Compute calls: {compute_count}")
        print(f"  Cache hit rate: {stats['overall_hit_rate']:.1%}")
        print(f"  L1 hit rate: {stats['l1']['hit_rate']:.1%}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Avg access time: {duration/len(access_pattern)*1000:.1f}ms")
        
        # Should achieve good hit rate with LRU
        assert stats['overall_hit_rate'] > 0.7
        
        await cache.clear()
    
    @pytest.mark.asyncio
    async def test_concurrent_performance_scaling(self, tmp_path):
        """Test performance scaling with concurrent access"""
        db = DatabaseManager(
            str(tmp_path / "concurrent.db"),
            pool_config={"min_size": 5, "max_size": 20}
        )
        await db.initialize()
        
        cache = CacheManager(
            l1_config={"max_size": 500},
            stampede_protection=True
        )
        
        # Create schema
        await db.execute("""
            CREATE TABLE data (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Insert data
        for i in range(100):
            await db.execute(
                "INSERT INTO data (id, value) VALUES (?, ?)",
                (i, f"value_{i}")
            )
        
        # Benchmark different concurrency levels
        async def benchmark_concurrency(concurrent_workers: int):
            async def worker():
                for _ in range(10):
                    data_id = random.randint(0, 99)
                    
                    async def fetch_data():
                        result = await db.execute(
                            "SELECT * FROM data WHERE id = ?",
                            (data_id,)
                        )
                        return result.rows[0] if result.rows else None
                    
                    await cache.get(f"data:{data_id}", fetch_data)
            
            start_time = time.time()
            tasks = [worker() for _ in range(concurrent_workers)]
            await asyncio.gather(*tasks)
            duration = time.time() - start_time
            
            total_operations = concurrent_workers * 10
            return {
                "workers": concurrent_workers,
                "duration": duration,
                "ops_per_sec": total_operations / duration
            }
        
        # Test different concurrency levels
        results = []
        for workers in [1, 5, 10, 20]:
            result = await benchmark_concurrency(workers)
            results.append(result)
            
            # Clear cache between runs
            await cache.clear()
        
        print(f"\nConcurrency Scaling:")
        for r in results:
            print(f"  {r['workers']} workers: {r['ops_per_sec']:.0f} ops/sec")
        
        # Should scale reasonably well
        single_threaded = results[0]['ops_per_sec']
        multi_threaded = results[-1]['ops_per_sec']
        assert multi_threaded > single_threaded * 2  # At least 2x improvement
        
        await db.close()


from unittest.mock import AsyncMock