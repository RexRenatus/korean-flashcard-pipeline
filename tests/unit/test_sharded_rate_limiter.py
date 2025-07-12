"""Unit tests for sharded rate limiter implementation"""

import asyncio
import pytest
import time
from datetime import datetime
import hashlib

from flashcard_pipeline.rate_limiter_v2 import (
    ShardedRateLimiter,
    AdaptiveShardedRateLimiter,
    DistributedRateLimiter,
    RateLimitResult,
    TokenReservation,
)
from flashcard_pipeline.exceptions import RateLimitError


class TestShardedRateLimiter:
    """Test sharded rate limiter functionality"""
    
    @pytest.fixture
    def limiter(self):
        """Create a test rate limiter with 4 shards"""
        return ShardedRateLimiter(
            rate=100,      # 100 requests per minute
            period=60.0,
            shards=4,
            algorithm="token_bucket"
        )
    
    def test_initialization(self):
        """Test rate limiter initialization"""
        limiter = ShardedRateLimiter(rate=100, period=60.0, shards=4)
        
        assert limiter.total_rate == 100
        assert limiter.period == 60.0
        assert limiter.shards == 4
        assert len(limiter.limiters) == 4
        
        # Check rate distribution
        total_rate = sum(l.requests_per_minute for l in limiter.limiters)
        assert total_rate == 100
    
    def test_optimal_shard_calculation(self):
        """Test optimal shard count calculation"""
        # Low rate should use 1 shard
        limiter = ShardedRateLimiter(rate=10, shards=8)
        assert limiter.shards == 1
        
        # Medium rate
        limiter = ShardedRateLimiter(rate=100, shards=8)
        assert limiter.shards in [4, 8]  # Power of 2
        
        # High rate
        limiter = ShardedRateLimiter(rate=1000, shards=32)
        assert limiter.shards >= 8
    
    @pytest.mark.asyncio
    async def test_basic_acquire(self, limiter):
        """Test basic token acquisition"""
        # Should succeed
        result = await limiter.acquire("user1")
        assert result.allowed is True
        assert result.retry_after is None
        assert result.shard_id is not None
        assert result.tokens_remaining is not None
    
    @pytest.mark.asyncio
    async def test_shard_distribution(self, limiter):
        """Test that requests are distributed across shards"""
        keys = [f"user{i}" for i in range(100)]
        shard_hits = [0] * limiter.shards
        
        for key in keys:
            result = await limiter.acquire(key)
            if result.allowed and result.shard_id is not None:
                shard_hits[result.shard_id] += 1
        
        # All shards should have been used
        assert all(hits > 0 for hits in shard_hits)
        
        # Distribution should be relatively balanced
        avg_hits = sum(shard_hits) / len(shard_hits)
        for hits in shard_hits:
            assert abs(hits - avg_hits) < avg_hits * 0.5  # Within 50% of average
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, limiter):
        """Test that rate limits are enforced"""
        # Exhaust tokens on all shards for a key
        key = "heavy_user"
        success_count = 0
        
        # Try many requests
        for _ in range(200):
            result = await limiter.acquire(key)
            if result.allowed:
                success_count += 1
            else:
                break
        
        # Should have been rate limited
        assert success_count < 200
        
        # Further requests should fail
        result = await limiter.acquire(key)
        assert result.allowed is False
        assert result.retry_after is not None
        assert result.retry_after > 0
    
    @pytest.mark.asyncio
    async def test_secondary_shard_fallback(self, limiter):
        """Test fallback to secondary shard"""
        # This test is probabilistic due to hash distribution
        # We'll use keys that we know hash to different shards
        
        # Find a key that uses different primary/secondary shards
        test_key = None
        for i in range(100):
            key = f"test_key_{i}"
            shard1, shard2 = limiter._get_shards(key)
            if shard1 != shard2:
                test_key = key
                break
        
        assert test_key is not None, "Could not find suitable test key"
        
        # Exhaust primary shard
        primary, secondary = limiter._get_shards(test_key)
        
        # Directly exhaust the primary shard's tokens
        limiter.limiters[primary].minute_tokens = 0
        
        # Should still succeed using secondary shard
        result = await limiter.acquire(test_key)
        assert result.allowed is True
        assert result.shard_id == secondary
    
    @pytest.mark.asyncio
    async def test_try_acquire_non_blocking(self, limiter):
        """Test non-blocking acquire"""
        # Exhaust rate limit
        key = "test_user"
        while True:
            result = await limiter.try_acquire(key)
            if not result.allowed:
                break
        
        # Should return failure result without raising
        result = await limiter.try_acquire(key)
        assert result.allowed is False
        assert result.retry_after is not None
    
    def test_get_status(self, limiter):
        """Test status reporting"""
        status = limiter.get_status()
        
        assert status["total_rate"] == 100
        assert status["period"] == 60.0
        assert status["shards"] == 4
        assert "statistics" in status
        assert "shard_details" in status
        assert len(status["shard_details"]) == 4
    
    @pytest.mark.asyncio
    async def test_reset(self, limiter):
        """Test rate limiter reset"""
        # Use some tokens
        for i in range(10):
            await limiter.acquire(f"user{i}")
        
        # Reset
        await limiter.reset()
        
        # Check status
        status = limiter.get_status()
        assert status["statistics"]["total_requests"] == 0
        assert status["statistics"]["allowed_requests"] == 0


class TestTokenReservation:
    """Test token reservation functionality"""
    
    @pytest.fixture
    def limiter(self):
        """Create a test rate limiter"""
        return ShardedRateLimiter(
            rate=60,  # 1 per second
            period=60.0,
            shards=2
        )
    
    @pytest.mark.asyncio
    async def test_immediate_reservation(self, limiter):
        """Test reservation when tokens are available"""
        reservation = await limiter.reserve("user1", count=1)
        
        assert reservation.key == "user1"
        assert reservation.count == 1
        assert reservation.is_ready()
        assert not reservation.is_expired()
        assert reservation.execute_at <= time.time()
    
    @pytest.mark.asyncio
    async def test_delayed_reservation(self, limiter):
        """Test reservation when tokens are not immediately available"""
        # Exhaust tokens
        key = "user1"
        while (await limiter.try_acquire(key)).allowed:
            pass
        
        # Reserve tokens
        start_time = time.time()
        reservation = await limiter.reserve(key, count=1)
        
        assert not reservation.is_ready()
        assert reservation.execute_at > start_time
        assert reservation.execute_at - start_time <= 2.0  # Should be ready soon
    
    @pytest.mark.asyncio
    async def test_reservation_expiration(self, limiter):
        """Test reservation expiration"""
        reservation = TokenReservation(
            key="user1",
            count=1,
            expires_at=time.time() - 1  # Already expired
        )
        
        assert reservation.is_expired()
    
    @pytest.mark.asyncio
    async def test_execute_reservation(self, limiter):
        """Test executing a reservation"""
        # Create and execute immediate reservation
        reservation = await limiter.reserve("user1", count=1)
        result = await limiter.execute_reservation(reservation.id)
        
        assert result.allowed is True
        
        # Reservation should be removed after execution
        with pytest.raises(KeyError):
            await limiter.execute_reservation(reservation.id)
    
    @pytest.mark.asyncio
    async def test_execute_expired_reservation(self, limiter):
        """Test executing an expired reservation"""
        # Create reservation with short expiration
        reservation = await limiter.reserve("user1", count=1)
        reservation.expires_at = time.time() - 1
        limiter._reservations[reservation.id] = reservation
        
        # Should fail
        with pytest.raises(ValueError, match="expired"):
            await limiter.execute_reservation(reservation.id)
    
    @pytest.mark.asyncio
    async def test_execute_not_ready_reservation(self, limiter):
        """Test executing a reservation that's not ready"""
        # Create future reservation
        reservation = await limiter.reserve("user1", count=1)
        reservation.execute_at = time.time() + 10
        limiter._reservations[reservation.id] = reservation
        
        # Should fail
        with pytest.raises(ValueError, match="not ready"):
            await limiter.execute_reservation(reservation.id)
    
    @pytest.mark.asyncio
    async def test_cancel_reservation(self, limiter):
        """Test cancelling a reservation"""
        reservation = await limiter.reserve("user1", count=1)
        
        # Cancel should succeed
        assert await limiter.cancel_reservation(reservation.id) is True
        
        # Second cancel should fail
        assert await limiter.cancel_reservation(reservation.id) is False
    
    @pytest.mark.asyncio
    async def test_max_wait_exceeded(self, limiter):
        """Test reservation with max_wait exceeded"""
        # Exhaust tokens
        key = "user1"
        while (await limiter.try_acquire(key)).allowed:
            pass
        
        # Try to reserve with short max_wait
        with pytest.raises(ValueError, match="exceeds max_wait"):
            await limiter.reserve(key, count=50, max_wait=0.1)
    
    @pytest.mark.asyncio
    async def test_reservation_cleanup(self, limiter):
        """Test automatic cleanup of expired reservations"""
        # Create expired reservation
        reservation = TokenReservation(
            key="user1",
            count=1,
            expires_at=time.time() - 1
        )
        limiter._reservations[reservation.id] = reservation
        
        # Create new reservation to trigger cleanup
        await limiter.reserve("user2", count=1)
        
        # Expired reservation should be cleaned up
        assert reservation.id not in limiter._reservations
        assert limiter._stats["reservations_expired"] == 1


class TestAdaptiveShardedRateLimiter:
    """Test adaptive sharded rate limiter"""
    
    @pytest.mark.asyncio
    async def test_adaptive_initialization(self):
        """Test adaptive rate limiter initialization"""
        limiter = AdaptiveShardedRateLimiter(
            rate=100,
            initial_shards=4,
            rebalance_threshold=0.3,
            rebalance_interval=1.0  # Short for testing
        )
        
        assert limiter.rebalance_threshold == 0.3
        assert limiter.rebalance_interval == 1.0
    
    @pytest.mark.asyncio
    async def test_rebalancing_check(self):
        """Test that rebalancing is checked periodically"""
        limiter = AdaptiveShardedRateLimiter(
            rate=100,
            initial_shards=4,
            rebalance_interval=0.1  # Very short for testing
        )
        
        # Make requests
        for i in range(10):
            await limiter.acquire(f"user{i}")
        
        # Wait for rebalancing interval
        await asyncio.sleep(0.2)
        
        # Make another request to trigger check
        await limiter.acquire("trigger")
        
        # Last rebalance time should be updated
        assert time.time() - limiter._last_rebalance < 1.0


class TestDistributedRateLimiter:
    """Test distributed rate limiter interface"""
    
    @pytest.mark.asyncio
    async def test_distributed_initialization(self):
        """Test distributed rate limiter initialization"""
        limiter = DistributedRateLimiter(
            rate=100,
            period=60.0,
            namespace="test_app",
            backend="memory"
        )
        
        assert limiter.rate == 100
        assert limiter.namespace == "test_app"
        assert limiter.backend == "memory"
    
    @pytest.mark.asyncio
    async def test_namespaced_keys(self):
        """Test that keys are properly namespaced"""
        limiter = DistributedRateLimiter(
            rate=100,
            namespace="app1",
            backend="memory"
        )
        
        # Acquire tokens
        result = await limiter.acquire("user1")
        assert result.allowed is True
        
        # Status should show namespace
        status = limiter.get_status()
        assert status["backend"]["namespace"] == "app1"
    
    @pytest.mark.asyncio
    async def test_distributed_reserve(self):
        """Test reservation in distributed limiter"""
        limiter = DistributedRateLimiter(
            rate=60,
            namespace="test",
            backend="memory"
        )
        
        reservation = await limiter.reserve("user1", count=1)
        assert reservation.key == "test:user1"  # Should include namespace


class TestShardBalance:
    """Test shard load balancing"""
    
    @pytest.mark.asyncio
    async def test_balanced_distribution(self):
        """Test that load is balanced across shards"""
        limiter = ShardedRateLimiter(rate=400, shards=4)
        
        # Make many requests with different keys
        for i in range(400):
            await limiter.try_acquire(f"user{i}")
        
        balance = limiter.get_shard_balance()
        
        # Should be reasonably balanced
        assert balance["balanced"] is True
        assert balance["imbalance_ratio"] < 0.2
    
    @pytest.mark.asyncio
    async def test_imbalanced_detection(self):
        """Test detection of imbalanced shards"""
        limiter = ShardedRateLimiter(rate=100, shards=4)
        
        # Force imbalance by using keys that hash to same shard
        # This is a bit artificial but demonstrates the concept
        for i in range(100):
            # These keys might hash to similar shards
            await limiter.try_acquire(f"user_000{i}")
        
        balance = limiter.get_shard_balance()
        
        # Check that imbalance is detected
        assert "distribution" in balance
        assert "most_loaded_shard" in balance
        assert "least_loaded_shard" in balance


class TestPerformance:
    """Performance tests for sharded rate limiter"""
    
    @pytest.mark.asyncio
    async def test_high_concurrency(self):
        """Test performance under high concurrency"""
        limiter = ShardedRateLimiter(rate=10000, shards=16)
        
        async def make_requests(user_id: str, count: int):
            successes = 0
            for _ in range(count):
                result = await limiter.try_acquire(user_id)
                if result.allowed:
                    successes += 1
            return successes
        
        # Simulate 100 concurrent users
        start_time = time.time()
        tasks = [
            make_requests(f"user{i}", 100)
            for i in range(100)
        ]
        
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        total_success = sum(results)
        total_requests = 100 * 100
        
        print(f"\nPerformance test:")
        print(f"  Total requests: {total_requests}")
        print(f"  Successful: {total_success}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Requests/sec: {total_requests / duration:.0f}")
        
        # Should complete reasonably quickly
        assert duration < 5.0  # 5 seconds for 10k requests
    
    @pytest.mark.asyncio
    async def test_reservation_performance(self):
        """Test reservation system performance"""
        limiter = ShardedRateLimiter(rate=1000, shards=8)
        
        # Create many reservations
        start_time = time.time()
        reservations = []
        
        for i in range(100):
            reservation = await limiter.reserve(f"user{i}", count=1)
            reservations.append(reservation)
        
        creation_time = time.time() - start_time
        
        # Execute all reservations
        start_time = time.time()
        results = []
        for reservation in reservations:
            if reservation.is_ready():
                try:
                    result = await limiter.execute_reservation(reservation.id)
                    results.append(result)
                except:
                    pass
        
        execution_time = time.time() - start_time
        
        print(f"\nReservation performance:")
        print(f"  Creation time: {creation_time:.3f}s")
        print(f"  Execution time: {execution_time:.3f}s")
        print(f"  Successful executions: {len(results)}")
        
        # Should be fast
        assert creation_time < 1.0
        assert execution_time < 1.0