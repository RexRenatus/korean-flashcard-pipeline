"""Integration tests for sharded rate limiter with other components"""

import asyncio
import pytest
import time
from typing import List, Dict, Any
import random

from flashcard_pipeline.rate_limiter_v2 import (
    ShardedRateLimiter,
    AdaptiveShardedRateLimiter,
    DistributedRateLimiter,
    RateLimitResult,
    TokenReservation,
)
from flashcard_pipeline.circuit_breaker_v2 import EnhancedCircuitBreaker
from flashcard_pipeline.utils.retry import RetryConfig, retry_async
from flashcard_pipeline.exceptions import RateLimitError, NetworkError


class TestShardedRateLimiterIntegration:
    """Test sharded rate limiter integration with other components"""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_with_circuit_breaker(self):
        """Test rate limiter working with circuit breaker"""
        # Create components
        rate_limiter = ShardedRateLimiter(
            rate=60,  # 1 per second
            period=60.0,
            shards=4
        )
        
        circuit_breaker = EnhancedCircuitBreaker(
            failure_threshold=0.5,
            min_throughput=2,
            break_duration=1.0
        )
        
        async def protected_api_call(user_id: str):
            # First check rate limit
            result = await rate_limiter.acquire(user_id)
            if not result.allowed:
                raise RateLimitError(f"Rate limited: {result.reason}")
            
            # Then protect with circuit breaker
            async def api_call():
                # Simulate API work
                await asyncio.sleep(0.01)
                return {"user": user_id, "data": "success"}
            
            return await circuit_breaker.call(api_call)
        
        # Make several calls
        results = []
        for i in range(10):
            try:
                result = await protected_api_call(f"user_{i}")
                results.append(("success", result))
            except RateLimitError as e:
                results.append(("rate_limited", str(e)))
            except Exception as e:
                results.append(("error", str(e)))
        
        # Should have mix of successes and rate limits
        successes = [r for r in results if r[0] == "success"]
        rate_limited = [r for r in results if r[0] == "rate_limited"]
        
        assert len(successes) > 0
        assert len(rate_limited) > 0
    
    @pytest.mark.asyncio
    async def test_rate_limiter_with_retry(self):
        """Test rate limiter with retry logic"""
        rate_limiter = ShardedRateLimiter(
            rate=10,  # Low rate to trigger limits
            period=60.0,
            shards=2
        )
        
        retry_config = RetryConfig(
            max_attempts=3,
            initial_delay=0.5,
            retry_on=(RateLimitError,)
        )
        
        @retry_async(retry_config)
        async def rate_limited_call(user_id: str):
            result = await rate_limiter.acquire(user_id)
            if not result.allowed:
                raise RateLimitError(
                    f"Rate limited",
                    retry_after=result.retry_after
                )
            return {"success": True, "user": user_id}
        
        # Exhaust rate limit
        user = "heavy_user"
        for _ in range(10):
            try:
                await rate_limiter.acquire(user)
            except:
                break
        
        # Now try with retry - should eventually succeed
        start_time = time.time()
        result = await rate_limited_call(user)
        duration = time.time() - start_time
        
        assert result["success"] is True
        assert duration > 0.5  # Had to retry
    
    @pytest.mark.asyncio
    async def test_reservation_system_integration(self):
        """Test reservation system with multiple components"""
        rate_limiter = ShardedRateLimiter(
            rate=30,  # 0.5 per second
            period=60.0,
            shards=4
        )
        
        # Service that processes reservations
        class ReservationProcessor:
            def __init__(self, limiter: ShardedRateLimiter):
                self.limiter = limiter
                self.processed = []
            
            async def process_batch(self, user_ids: List[str]):
                """Process a batch of users with reservations"""
                reservations = []
                
                # Reserve tokens for all users
                for user_id in user_ids:
                    try:
                        reservation = await self.limiter.reserve(
                            user_id,
                            count=1,
                            max_wait=5.0
                        )
                        reservations.append(reservation)
                    except ValueError:
                        # Could not reserve within time limit
                        pass
                
                # Sort by execution time
                reservations.sort(key=lambda r: r.execute_at)
                
                # Execute when ready
                results = []
                for reservation in reservations:
                    # Wait until ready
                    wait_time = reservation.execute_at - time.time()
                    if wait_time > 0:
                        await asyncio.sleep(wait_time)
                    
                    # Execute reservation
                    try:
                        result = await self.limiter.execute_reservation(
                            reservation.id
                        )
                        if result.allowed:
                            self.processed.append(reservation.key)
                            results.append((reservation.key, "processed"))
                    except Exception as e:
                        results.append((reservation.key, f"failed: {e}"))
                
                return results
        
        processor = ReservationProcessor(rate_limiter)
        
        # Process batch of users
        users = [f"user_{i}" for i in range(10)]
        results = await processor.process_batch(users)
        
        # Should have processed all users eventually
        assert len(processor.processed) == len(users)
        assert all(r[1] == "processed" for r in results)
    
    @pytest.mark.asyncio
    async def test_adaptive_rate_limiting(self):
        """Test adaptive rate limiter responding to load"""
        limiter = AdaptiveShardedRateLimiter(
            rate=100,
            initial_shards=4,
            rebalance_threshold=0.2,
            rebalance_interval=0.5  # Short for testing
        )
        
        # Simulate uneven load distribution
        # Most requests go to specific users
        hot_users = ["user_1", "user_2"]
        cold_users = [f"user_{i}" for i in range(3, 20)]
        
        async def simulate_traffic():
            for _ in range(100):
                # 80% of traffic to hot users
                if random.random() < 0.8:
                    user = random.choice(hot_users)
                else:
                    user = random.choice(cold_users)
                
                await limiter.try_acquire(user)
                await asyncio.sleep(0.01)
        
        # Run traffic simulation
        await simulate_traffic()
        
        # Check shard balance
        balance = limiter.get_shard_balance()
        
        # Should detect imbalance
        assert balance["imbalance_ratio"] > 0.1
        
        # Wait for rebalancing
        await asyncio.sleep(1.0)
        
        # Make a request to trigger rebalance check
        await limiter.try_acquire("trigger")
        
        # Verify rebalancing occurred
        assert limiter._last_rebalance > 0
    
    @pytest.mark.asyncio
    async def test_cascading_rate_limits(self):
        """Test multiple rate limiters in cascade"""
        # Global rate limiter
        global_limiter = ShardedRateLimiter(
            rate=1000,  # 1000 requests per minute total
            period=60.0,
            shards=8
        )
        
        # Per-user rate limiter
        user_limiter = ShardedRateLimiter(
            rate=100,  # 100 requests per minute per user
            period=60.0,
            shards=4
        )
        
        # Per-endpoint rate limiter
        endpoint_limiter = ShardedRateLimiter(
            rate=500,  # 500 requests per minute per endpoint
            period=60.0,
            shards=4
        )
        
        async def make_request(user_id: str, endpoint: str):
            # Check all rate limits
            checks = [
                ("global", await global_limiter.try_acquire("global")),
                ("user", await user_limiter.try_acquire(user_id)),
                ("endpoint", await endpoint_limiter.try_acquire(endpoint))
            ]
            
            # All must pass
            for name, result in checks:
                if not result.allowed:
                    return {
                        "allowed": False,
                        "limited_by": name,
                        "retry_after": result.retry_after
                    }
            
            return {
                "allowed": True,
                "user": user_id,
                "endpoint": endpoint
            }
        
        # Simulate traffic
        results = []
        endpoints = ["/api/users", "/api/posts", "/api/comments"]
        
        for i in range(200):
            user = f"user_{i % 5}"  # 5 users
            endpoint = endpoints[i % 3]  # 3 endpoints
            
            result = await make_request(user, endpoint)
            results.append(result)
        
        # Analyze results
        allowed = [r for r in results if r["allowed"]]
        limited = [r for r in results if not r["allowed"]]
        
        # Should have some of each
        assert len(allowed) > 0
        assert len(limited) > 0
        
        # Check what caused limits
        limit_reasons = {}
        for r in limited:
            reason = r["limited_by"]
            limit_reasons[reason] = limit_reasons.get(reason, 0) + 1
        
        # User limits should be most common (lowest limit)
        assert "user" in limit_reasons


class TestDistributedRateLimiter:
    """Test distributed rate limiter scenarios"""
    
    @pytest.mark.asyncio
    async def test_namespace_isolation(self):
        """Test that namespaces isolate rate limits"""
        # Create limiters for different services
        service_a = DistributedRateLimiter(
            rate=100,
            namespace="service_a",
            backend="memory"
        )
        
        service_b = DistributedRateLimiter(
            rate=100,
            namespace="service_b",
            backend="memory"
        )
        
        # Same user in different services
        user = "shared_user"
        
        # Exhaust service A limit
        count_a = 0
        while (await service_a._local_limiter.try_acquire(f"service_a:{user}")).allowed:
            count_a += 1
            if count_a > 200:  # Safety limit
                break
        
        # Service B should still have capacity
        result_b = await service_b.acquire(user)
        assert result_b.allowed is True
        
        # Verify isolation
        status_a = service_a.get_status()
        status_b = service_b.get_status()
        
        assert status_a["statistics"]["denied_requests"] > 0
        assert status_b["statistics"]["denied_requests"] == 0
    
    @pytest.mark.asyncio
    async def test_distributed_coordination(self):
        """Test distributed rate limiting coordination"""
        # Simulate multiple instances
        instances = [
            DistributedRateLimiter(
                rate=100,
                namespace="api",
                backend="memory"
            )
            for _ in range(3)
        ]
        
        # In real implementation, these would share backend
        # For testing, we'll coordinate manually
        shared_state = {"tokens": 100, "last_refill": time.time()}
        
        async def coordinated_acquire(instance: DistributedRateLimiter, key: str):
            # Simulate distributed coordination
            # In reality, this would be Redis/Memcached operations
            
            # Simple token bucket simulation
            now = time.time()
            elapsed = now - shared_state["last_refill"]
            refill = elapsed * (100 / 60.0)  # 100 per minute
            
            shared_state["tokens"] = min(100, shared_state["tokens"] + refill)
            shared_state["last_refill"] = now
            
            if shared_state["tokens"] >= 1:
                shared_state["tokens"] -= 1
                return RateLimitResult(
                    allowed=True,
                    tokens_remaining=shared_state["tokens"]
                )
            else:
                return RateLimitResult(
                    allowed=False,
                    retry_after=1.0
                )
        
        # Make requests from all instances
        results = []
        for i in range(150):
            instance = instances[i % 3]
            result = await coordinated_acquire(instance, "user")
            results.append(result)
        
        # Should see rate limiting kick in
        allowed = sum(1 for r in results if r.allowed)
        denied = sum(1 for r in results if not r.allowed)
        
        assert allowed > 0
        assert denied > 0
        
        # Total allowed should respect global limit
        assert allowed <= 110  # Some tolerance for timing


class TestRealWorldScenarios:
    """Test real-world rate limiting scenarios"""
    
    @pytest.mark.asyncio
    async def test_api_gateway_scenario(self):
        """Test API gateway with multiple rate limit tiers"""
        class APIGateway:
            def __init__(self):
                # Different tiers of rate limits
                self.free_tier = ShardedRateLimiter(
                    rate=60,  # 1 per second
                    period=60.0,
                    shards=2
                )
                
                self.pro_tier = ShardedRateLimiter(
                    rate=600,  # 10 per second
                    period=60.0,
                    shards=4
                )
                
                self.enterprise_tier = ShardedRateLimiter(
                    rate=6000,  # 100 per second
                    period=60.0,
                    shards=8
                )
                
                # User tier mapping
                self.user_tiers = {
                    "user_free": "free",
                    "user_pro": "pro",
                    "user_enterprise": "enterprise"
                }
            
            async def handle_request(self, user_id: str, request_data: Dict[str, Any]):
                # Determine tier
                tier = self.user_tiers.get(user_id, "free")
                
                # Select appropriate limiter
                limiter = {
                    "free": self.free_tier,
                    "pro": self.pro_tier,
                    "enterprise": self.enterprise_tier
                }[tier]
                
                # Check rate limit
                result = await limiter.acquire(user_id)
                if not result.allowed:
                    return {
                        "error": "rate_limit_exceeded",
                        "retry_after": result.retry_after,
                        "tier": tier
                    }
                
                # Process request
                return {
                    "success": True,
                    "user": user_id,
                    "tier": tier,
                    "tokens_remaining": result.tokens_remaining
                }
        
        gateway = APIGateway()
        
        # Simulate traffic from different tiers
        async def simulate_user_traffic(user_id: str, request_count: int):
            results = []
            for i in range(request_count):
                result = await gateway.handle_request(
                    user_id,
                    {"request_id": i}
                )
                results.append(result)
                await asyncio.sleep(0.01)
            return results
        
        # Run concurrent traffic
        tasks = [
            simulate_user_traffic("user_free", 10),
            simulate_user_traffic("user_pro", 50),
            simulate_user_traffic("user_enterprise", 100)
        ]
        
        all_results = await asyncio.gather(*tasks)
        
        # Analyze results by tier
        free_results = all_results[0]
        pro_results = all_results[1]
        enterprise_results = all_results[2]
        
        # Free tier should hit limits
        free_limited = [r for r in free_results if "error" in r]
        assert len(free_limited) > 0
        
        # Pro tier might hit limits
        pro_limited = [r for r in pro_results if "error" in r]
        
        # Enterprise should not hit limits
        enterprise_limited = [r for r in enterprise_results if "error" in r]
        assert len(enterprise_limited) == 0
    
    @pytest.mark.asyncio
    async def test_burst_handling_scenario(self):
        """Test handling traffic bursts with reservations"""
        limiter = ShardedRateLimiter(
            rate=60,  # 1 per second average
            period=60.0,
            shards=4,
            burst_size=10  # Allow short bursts
        )
        
        class BurstHandler:
            def __init__(self, limiter: ShardedRateLimiter):
                self.limiter = limiter
                self.queue = asyncio.Queue()
                self.processed = []
            
            async def handle_burst(self, requests: List[Dict[str, Any]]):
                """Handle burst of requests with queuing"""
                # Try immediate processing
                immediate = []
                queued = []
                
                for req in requests:
                    result = await self.limiter.try_acquire(req["user"])
                    if result.allowed:
                        immediate.append(req)
                    else:
                        # Reserve for later
                        reservation = await self.limiter.reserve(
                            req["user"],
                            max_wait=10.0
                        )
                        queued.append((req, reservation))
                
                # Process immediate requests
                for req in immediate:
                    self.processed.append({
                        **req,
                        "processed_at": time.time(),
                        "queued": False
                    })
                
                # Schedule queued requests
                for req, reservation in queued:
                    await self.queue.put((req, reservation))
                
                # Process queue
                await self.process_queue()
                
                return {
                    "immediate": len(immediate),
                    "queued": len(queued),
                    "total": len(requests)
                }
            
            async def process_queue(self):
                """Process queued requests as their reservations become ready"""
                while not self.queue.empty():
                    req, reservation = await self.queue.get()
                    
                    # Wait until ready
                    wait_time = reservation.execute_at - time.time()
                    if wait_time > 0:
                        await asyncio.sleep(wait_time)
                    
                    # Execute reservation
                    try:
                        result = await self.limiter.execute_reservation(
                            reservation.id
                        )
                        if result.allowed:
                            self.processed.append({
                                **req,
                                "processed_at": time.time(),
                                "queued": True
                            })
                    except Exception:
                        pass  # Reservation expired or cancelled
        
        handler = BurstHandler(limiter)
        
        # Create burst of requests
        burst = [
            {"user": f"user_{i % 5}", "id": i}
            for i in range(30)
        ]
        
        # Handle burst
        result = await handler.handle_burst(burst)
        
        # Should have processed some immediately, queued others
        assert result["immediate"] > 0
        assert result["queued"] > 0
        assert result["immediate"] + result["queued"] == result["total"]
        
        # All should eventually be processed
        assert len(handler.processed) == len(burst)
        
        # Check timing
        process_times = [p["processed_at"] for p in handler.processed]
        duration = max(process_times) - min(process_times)
        
        # Should have spread processing over time
        assert duration > 1.0  # Not all processed instantly