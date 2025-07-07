"""Phase 2: Rate Limiter Tests

Tests for rate limiting functionality including token bucket algorithm,
distributed rate limiting, and thread-safe operations.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor

from flashcard_pipeline.rate_limiter import RateLimiter
from flashcard_pipeline.concurrent.distributed_rate_limiter import DistributedRateLimiter
from flashcard_pipeline.exceptions import RateLimitError


class TestTokenBucket:
    """Test token bucket algorithm implementation"""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter with 60 requests per minute"""
        return RateLimiter(requests_per_minute=60)
    
    @pytest.fixture
    def distributed_limiter(self):
        """Create distributed rate limiter"""
        return DistributedRateLimiter(requests_per_minute=60, buffer_factor=0.8)
    
    def test_token_consumption(self, rate_limiter):
        """Test basic token consumption"""
        # Initial state - should have full capacity
        assert rate_limiter.tokens == rate_limiter.capacity
        
        # Consume one token
        allowed = rate_limiter.try_acquire()
        assert allowed is True
        assert rate_limiter.tokens == rate_limiter.capacity - 1
        
        # Consume remaining tokens
        for _ in range(rate_limiter.capacity - 1):
            assert rate_limiter.try_acquire() is True
        
        # No tokens left
        assert rate_limiter.tokens == 0
        assert rate_limiter.try_acquire() is False
    
    def test_token_refill_rate(self, rate_limiter):
        """Test token refill rate matches configuration"""
        # Consume all tokens
        for _ in range(rate_limiter.capacity):
            rate_limiter.try_acquire()
        
        assert rate_limiter.tokens == 0
        
        # Wait for refill (1 token per second for 60 rpm)
        time.sleep(1.1)
        
        # Should have refilled ~1 token
        assert rate_limiter.tokens >= 0.9
        assert rate_limiter.tokens <= 1.1
    
    def test_burst_capacity(self):
        """Test burst capacity handling"""
        # Create limiter with 600 rpm (10 per second)
        limiter = RateLimiter(requests_per_minute=600)
        
        # Should allow burst up to capacity
        burst_count = 0
        start_time = time.time()
        
        while limiter.try_acquire() and (time.time() - start_time) < 0.1:
            burst_count += 1
        
        # Should allow at least capacity tokens in burst
        assert burst_count >= limiter.capacity
    
    @pytest.mark.asyncio
    async def test_async_acquire(self):
        """Test async token acquisition with waiting"""
        limiter = RateLimiter(requests_per_minute=60)
        
        # Consume all tokens
        for _ in range(limiter.capacity):
            limiter.try_acquire()
        
        # Async acquire should wait for token
        start = time.time()
        acquired = await limiter.acquire_async(timeout=2.0)
        duration = time.time() - start
        
        assert acquired is True
        assert duration >= 0.9  # Should wait ~1 second for refill
        assert duration < 2.0  # Should not timeout
    
    @pytest.mark.asyncio
    async def test_acquire_timeout(self):
        """Test timeout when waiting for tokens"""
        limiter = RateLimiter(requests_per_minute=60)
        
        # Consume all tokens
        for _ in range(limiter.capacity):
            limiter.try_acquire()
        
        # Should timeout
        with pytest.raises(RateLimitError) as exc_info:
            await limiter.acquire_async(timeout=0.1)
        
        assert "timeout" in str(exc_info.value).lower()
    
    def test_rate_limit_adjustment(self, rate_limiter):
        """Test dynamic rate limit adjustment"""
        initial_rate = rate_limiter.rate
        
        # Increase rate limit
        rate_limiter.set_rate(120)  # 120 rpm
        assert rate_limiter.rate == 2.0  # 2 per second
        assert rate_limiter.capacity == 2  # Capacity adjusts
        
        # Decrease rate limit
        rate_limiter.set_rate(30)  # 30 rpm
        assert rate_limiter.rate == 0.5  # 0.5 per second
        assert rate_limiter.capacity == 1  # Minimum capacity


class TestDistributedRateLimiting:
    """Test thread-safe distributed rate limiting"""
    
    @pytest.mark.asyncio
    async def test_concurrent_token_access(self, distributed_limiter):
        """Test concurrent access to tokens"""
        # Track successful acquisitions
        success_count = 0
        
        async def try_acquire():
            nonlocal success_count
            try:
                await distributed_limiter.acquire(timeout=0.1)
                success_count += 1
                return True
            except RateLimitError:
                return False
        
        # Run concurrent requests
        tasks = [try_acquire() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        
        # Should respect rate limit
        assert success_count <= distributed_limiter.effective_capacity
        assert sum(results) == success_count
    
    def test_thread_safe_operations(self):
        """Test thread safety with multiple threads"""
        limiter = DistributedRateLimiter(requests_per_minute=600)  # 10 per second
        success_count = 0
        lock = threading.Lock()
        
        def worker():
            nonlocal success_count
            for _ in range(10):
                if asyncio.run(limiter.acquire_nowait()):
                    with lock:
                        success_count += 1
                time.sleep(0.01)
        
        # Run multiple threads
        import threading
        threads = []
        for _ in range(5):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Should not exceed capacity
        assert success_count <= limiter.effective_capacity * 2  # Allow some refill
    
    @pytest.mark.asyncio
    async def test_fair_token_distribution(self, distributed_limiter):
        """Test fair distribution among concurrent requests"""
        worker_counts = {}
        
        async def worker(worker_id):
            count = 0
            for _ in range(20):
                try:
                    await distributed_limiter.acquire(timeout=0.01)
                    count += 1
                except RateLimitError:
                    pass
                await asyncio.sleep(0.01)
            worker_counts[worker_id] = count
            return count
        
        # Run 5 workers
        tasks = [worker(i) for i in range(5)]
        await asyncio.gather(*tasks)
        
        # Check fairness - no worker should dominate
        counts = list(worker_counts.values())
        if len(counts) > 0 and max(counts) > 0:
            fairness_ratio = min(counts) / max(counts)
            assert fairness_ratio > 0.2  # Reasonable fairness
    
    @pytest.mark.asyncio
    async def test_buffer_factor(self):
        """Test buffer factor reduces effective rate"""
        # Create limiter with 80% buffer
        limiter = DistributedRateLimiter(
            requests_per_minute=100,
            buffer_factor=0.8
        )
        
        # Effective rate should be 80 rpm
        assert limiter.effective_rate == pytest.approx(80 / 60, rel=0.01)
        assert limiter.effective_capacity < limiter.base_capacity
    
    @pytest.mark.asyncio
    async def test_adaptive_throttling(self):
        """Test adaptive throttling based on availability"""
        limiter = DistributedRateLimiter(
            requests_per_minute=60,
            buffer_factor=0.8
        )
        
        # Track wait times
        wait_times = []
        
        async def measure_wait():
            start = time.time()
            await limiter.acquire()
            return time.time() - start
        
        # First batch - should be fast
        for _ in range(5):
            wait_time = await measure_wait()
            wait_times.append(wait_time)
        
        avg_initial_wait = sum(wait_times[:5]) / 5
        
        # Consume more tokens to create scarcity
        for _ in range(40):
            await limiter.acquire_nowait()
        
        # Next batch - should wait longer
        wait_times.clear()
        for _ in range(5):
            wait_time = await measure_wait()
            wait_times.append(wait_time)
        
        avg_scarce_wait = sum(wait_times) / 5
        
        # Wait time should increase under load
        assert avg_scarce_wait > avg_initial_wait


class TestRateLimiterStatistics:
    """Test rate limiter statistics and monitoring"""
    
    def test_request_tracking(self, rate_limiter):
        """Test tracking of allowed/denied requests"""
        stats = rate_limiter.get_stats()
        initial_allowed = stats["requests_allowed"]
        initial_denied = stats["requests_denied"]
        
        # Make some allowed requests
        for _ in range(5):
            rate_limiter.try_acquire()
        
        # Exhaust tokens
        while rate_limiter.try_acquire():
            pass
        
        # Make some denied requests
        for _ in range(3):
            rate_limiter.try_acquire()
        
        stats = rate_limiter.get_stats()
        assert stats["requests_allowed"] > initial_allowed + 5
        assert stats["requests_denied"] == initial_denied + 3
    
    def test_rate_calculation(self, rate_limiter):
        """Test actual rate calculation"""
        # Reset stats
        rate_limiter.reset_stats()
        
        # Make requests over time
        start_time = time.time()
        request_count = 0
        
        while time.time() - start_time < 2.0:
            if rate_limiter.try_acquire():
                request_count += 1
            time.sleep(0.1)
        
        stats = rate_limiter.get_stats()
        duration = time.time() - start_time
        actual_rate = request_count / duration
        
        # Should be close to configured rate (1 per second for 60 rpm)
        assert actual_rate >= 0.8
        assert actual_rate <= 1.2
    
    @pytest.mark.asyncio
    async def test_wait_time_tracking(self, distributed_limiter):
        """Test tracking of wait times"""
        # Consume most tokens
        for _ in range(int(distributed_limiter.effective_capacity * 0.9)):
            await distributed_limiter.acquire_nowait()
        
        # Track wait time
        start = time.time()
        await distributed_limiter.acquire()
        wait_time = time.time() - start
        
        stats = distributed_limiter.get_stats()
        assert stats["average_wait_time"] > 0
        assert stats["max_wait_time"] >= wait_time
    
    def test_capacity_utilization(self, rate_limiter):
        """Test capacity utilization metrics"""
        stats = rate_limiter.get_stats()
        
        # Full capacity initially
        assert stats["capacity_utilization"] == 0.0
        
        # Use half capacity
        for _ in range(rate_limiter.capacity // 2):
            rate_limiter.try_acquire()
        
        stats = rate_limiter.get_stats()
        assert stats["capacity_utilization"] == pytest.approx(0.5, rel=0.1)
        
        # Use all capacity
        while rate_limiter.try_acquire():
            pass
        
        stats = rate_limiter.get_stats()
        assert stats["capacity_utilization"] == 1.0


class TestRateLimiterErrorHandling:
    """Test error conditions and edge cases"""
    
    def test_invalid_rate_configuration(self):
        """Test handling of invalid rate configurations"""
        # Zero rate
        with pytest.raises(ValueError):
            RateLimiter(requests_per_minute=0)
        
        # Negative rate
        with pytest.raises(ValueError):
            RateLimiter(requests_per_minute=-10)
        
        # Very high rate (should cap)
        limiter = RateLimiter(requests_per_minute=1_000_000)
        assert limiter.capacity <= 10_000  # Should have reasonable cap
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test proper timeout handling"""
        limiter = RateLimiter(requests_per_minute=60)
        
        # Exhaust tokens
        for _ in range(limiter.capacity):
            limiter.try_acquire()
        
        # Test various timeout scenarios
        with pytest.raises(RateLimitError) as exc_info:
            await limiter.acquire_async(timeout=0)
        assert "timeout" in str(exc_info.value)
        
        # Negative timeout
        with pytest.raises(ValueError):
            await limiter.acquire_async(timeout=-1)
    
    def test_concurrent_reset(self, rate_limiter):
        """Test resetting limiter during concurrent access"""
        results = []
        
        def worker():
            for _ in range(10):
                try:
                    result = rate_limiter.try_acquire()
                    results.append(result)
                except Exception as e:
                    results.append(f"error: {e}")
                time.sleep(0.01)
        
        # Start workers
        import threading
        threads = []
        for _ in range(3):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()
        
        # Reset during operation
        time.sleep(0.05)
        rate_limiter.reset()
        
        for t in threads:
            t.join()
        
        # Should handle reset gracefully
        assert all(isinstance(r, bool) or "error" not in str(r) for r in results)
    
    @pytest.mark.asyncio
    async def test_release_tokens(self, distributed_limiter):
        """Test releasing tokens back to pool"""
        # Acquire some tokens
        for _ in range(5):
            await distributed_limiter.acquire()
        
        initial_tokens = distributed_limiter.current_tokens
        
        # Release tokens
        for _ in range(3):
            distributed_limiter.release()
        
        # Should have more tokens
        assert distributed_limiter.current_tokens > initial_tokens
        assert distributed_limiter.current_tokens <= distributed_limiter.effective_capacity


class TestRateLimiterIntegration:
    """Test rate limiter integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_api_rate_limiting_simulation(self):
        """Simulate API rate limiting scenario"""
        limiter = DistributedRateLimiter(
            requests_per_minute=600,  # Typical API limit
            buffer_factor=0.8
        )
        
        # Simulate API calls
        successful_calls = 0
        rate_limited_calls = 0
        
        async def api_call():
            nonlocal successful_calls, rate_limited_calls
            try:
                await limiter.acquire(timeout=0.1)
                # Simulate API work
                await asyncio.sleep(0.01)
                successful_calls += 1
                return {"status": "success"}
            except RateLimitError:
                rate_limited_calls += 1
                return {"status": "rate_limited"}
        
        # Run burst of API calls
        tasks = [api_call() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        
        # Check results
        assert successful_calls > 0
        assert successful_calls <= limiter.effective_capacity + 10  # Some refill
        assert rate_limited_calls == 100 - successful_calls
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """Test graceful degradation under load"""
        limiter = DistributedRateLimiter(
            requests_per_minute=120,
            buffer_factor=0.9
        )
        
        # Track performance over time
        windows = []
        
        for window in range(3):
            window_start = time.time()
            window_success = 0
            
            # Try to make 50 requests per window
            for _ in range(50):
                if await limiter.acquire_nowait():
                    window_success += 1
                await asyncio.sleep(0.02)
            
            window_duration = time.time() - window_start
            window_rate = window_success / window_duration
            windows.append({
                "success": window_success,
                "rate": window_rate,
                "duration": window_duration
            })
        
        # Rate should degrade gracefully, not cliff
        rates = [w["rate"] for w in windows]
        assert all(r <= limiter.effective_rate * 1.1 for r in rates)
    
    @pytest.mark.asyncio  
    async def test_multi_tenant_rate_limiting(self):
        """Test rate limiting for multiple tenants"""
        # Simulate per-tenant rate limiters
        tenant_limiters = {
            "tenant_a": DistributedRateLimiter(requests_per_minute=300),
            "tenant_b": DistributedRateLimiter(requests_per_minute=600),
            "tenant_c": DistributedRateLimiter(requests_per_minute=150),
        }
        
        results = {"tenant_a": 0, "tenant_b": 0, "tenant_c": 0}
        
        async def tenant_request(tenant_id):
            limiter = tenant_limiters[tenant_id]
            if await limiter.acquire_nowait():
                results[tenant_id] += 1
        
        # Simulate mixed tenant requests
        tasks = []
        for _ in range(100):
            for tenant in ["tenant_a", "tenant_b", "tenant_c"]:
                tasks.append(tenant_request(tenant))
        
        await asyncio.gather(*tasks)
        
        # Each tenant should respect their own limits
        assert results["tenant_a"] <= tenant_limiters["tenant_a"].effective_capacity + 5
        assert results["tenant_b"] <= tenant_limiters["tenant_b"].effective_capacity + 5
        assert results["tenant_c"] <= tenant_limiters["tenant_c"].effective_capacity + 5