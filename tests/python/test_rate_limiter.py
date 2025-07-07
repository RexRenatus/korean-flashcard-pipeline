import pytest
import asyncio
import time
from datetime import datetime, timedelta

from flashcard_pipeline.rate_limiter import RateLimiter


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_basic_rate_limiting(self):
        # 10 requests per minute with burst of 10
        limiter = RateLimiter(requests_per_minute=10, burst_size=10)
        
        # Should allow initial burst
        for _ in range(5):
            await limiter.acquire()
        
        # Should still have tokens left
        assert limiter.minute_tokens > 0
    
    @pytest.mark.asyncio
    async def test_token_refill(self):
        # 60 requests per minute = 1 per second
        limiter = RateLimiter(requests_per_minute=60, burst_size=10)
        
        # Consume burst tokens
        for _ in range(10):
            await limiter.acquire()
        
        # Wait for refill
        await asyncio.sleep(1.1)
        
        # Should have refilled ~1 token
        await limiter.acquire()  # This should succeed
    
    @pytest.mark.asyncio
    async def test_burst_capacity(self):
        limiter = RateLimiter(
            requests_per_minute=60,
            burst_size=20
        )
        
        # Should allow burst capacity
        consumed = 0
        for _ in range(20):
            await limiter.acquire()
            consumed += 1
        
        assert consumed == 20
    
    @pytest.mark.asyncio
    async def test_hour_window_tracking(self):
        limiter = RateLimiter(
            requests_per_minute=60,
            requests_per_hour=100,
            burst_size=10
        )
        
        # Make some requests
        for _ in range(5):
            await limiter.acquire()
        
        # Check hour window has entries
        assert len(limiter.hour_window) == 5
    
    @pytest.mark.asyncio
    async def test_reset_functionality(self):
        limiter = RateLimiter(requests_per_minute=10, burst_size=10)
        
        # Consume some tokens
        for _ in range(5):
            await limiter.acquire()
        
        initial_tokens = limiter.minute_tokens
        
        # Reset
        await limiter.reset()
        assert limiter.minute_tokens == 10.0
        assert len(limiter.hour_window) == 0


class TestRateLimiterIntegration:
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        limiter = RateLimiter(requests_per_minute=60, burst_size=10)
        
        async def make_request():
            try:
                await limiter.acquire()
                return True
            except:
                return False
        
        # Launch concurrent requests
        tasks = [make_request() for _ in range(15)]
        results = await asyncio.gather(*tasks)
        
        # Should allow up to burst size
        assert sum(results) >= 10
    
    @pytest.mark.asyncio
    async def test_rate_limiter_with_wait(self):
        limiter = RateLimiter(requests_per_minute=120, burst_size=5)  # 2 per second
        
        start_time = time.time()
        requests_made = 0
        
        # Make requests for 2 seconds
        while time.time() - start_time < 2:
            try:
                await limiter.acquire()
                requests_made += 1
            except:
                await asyncio.sleep(0.1)
        
        # Should make approximately 5 (burst) + 4 (2 per second * 2 seconds)
        assert 5 <= requests_made <= 10  # Allow for timing variations
    
    @pytest.mark.asyncio
    async def test_stats_collection(self):
        limiter = RateLimiter(requests_per_minute=60, burst_size=10)
        
        # Make some requests
        for _ in range(5):
            await limiter.acquire()
        
        stats = await limiter.get_stats()
        assert stats["requests_per_minute"] == 60
        assert stats["requests_per_hour"] == 3000
        assert stats["hour_window_count"] == 5
        assert stats["minute_tokens_remaining"] < 10.0


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_zero_tokens_handling(self):
        limiter = RateLimiter(requests_per_minute=60, burst_size=10)
        
        # Consume all burst tokens
        for _ in range(10):
            await limiter.acquire()
        
        # Should have very few tokens left
        assert limiter.minute_tokens < 1.0
    
    @pytest.mark.asyncio
    async def test_hour_window_cleanup(self):
        limiter = RateLimiter(
            requests_per_minute=60,
            requests_per_hour=100,
            burst_size=10
        )
        
        # Make a request
        await limiter.acquire()
        
        # Manually add old timestamp
        old_time = time.monotonic() - 3700  # Over an hour ago
        limiter.hour_window.append(old_time)
        
        # Make another request to trigger cleanup
        await limiter.acquire()
        
        # Old timestamp should be removed
        assert all(ts > old_time for ts in limiter.hour_window)
    
    def test_very_high_rate(self):
        # Test with very high rate (10k requests per minute)
        limiter = RateLimiter(requests_per_minute=10000, burst_size=100)
        
        # Should handle large numbers correctly
        assert limiter.minute_rate == pytest.approx(166.67, rel=0.01)  # per second
    
    def test_very_low_rate(self):
        # Test with very low rate (1 request per minute)
        limiter = RateLimiter(requests_per_minute=1, burst_size=1)
        
        # Should handle small numbers correctly
        assert limiter.minute_rate == pytest.approx(0.0167, rel=0.01)  # per second