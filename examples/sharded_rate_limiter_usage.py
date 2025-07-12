"""Examples of using the sharded rate limiter system"""

import asyncio
import time
import random
from datetime import datetime

from flashcard_pipeline.rate_limiter_v2 import (
    ShardedRateLimiter,
    AdaptiveShardedRateLimiter,
    DistributedRateLimiter,
    TokenReservation,
)
from flashcard_pipeline.exceptions import RateLimitError


async def basic_sharded_example():
    """Basic usage of sharded rate limiter"""
    print("\n=== Basic Sharded Rate Limiter Example ===")
    
    # Create limiter with 4 shards
    limiter = ShardedRateLimiter(
        rate=60,        # 60 requests per minute
        period=60.0,    # 60 second period
        shards=4        # 4 shards for distribution
    )
    
    # Simulate requests from different users
    users = ["alice", "bob", "charlie", "david", "eve"]
    
    for i in range(10):
        user = users[i % len(users)]
        result = await limiter.try_acquire(user)
        
        if result.allowed:
            print(f"✓ Request {i+1} from {user}: Allowed (shard {result.shard_id})")
        else:
            print(f"✗ Request {i+1} from {user}: Rate limited (retry in {result.retry_after:.1f}s)")
        
        await asyncio.sleep(0.1)
    
    # Show status
    status = limiter.get_status()
    print(f"\nRate Limiter Status:")
    print(f"  Total Rate: {status['total_rate']} requests per {status['period']}s")
    print(f"  Shards: {status['shards']}")
    print(f"  Success Rate: {status['statistics']['success_rate']:.1%}")
    
    # Show shard balance
    balance = limiter.get_shard_balance()
    print(f"\nShard Balance:")
    print(f"  Balanced: {balance['balanced']}")
    print(f"  Distribution: {balance['distribution']}")
    print(f"  Imbalance Ratio: {balance['imbalance_ratio']:.2f}")


async def reservation_system_example():
    """Example of token reservation system"""
    print("\n\n=== Token Reservation System Example ===")
    
    # Create limiter with low rate to demonstrate reservations
    limiter = ShardedRateLimiter(
        rate=30,        # 0.5 requests per second
        period=60.0,
        shards=2
    )
    
    # Reserve tokens for future use
    print("Creating reservations for batch processing...")
    
    reservations = []
    for i in range(5):
        user = f"batch_user_{i}"
        try:
            reservation = await limiter.reserve(
                user,
                count=1,
                max_wait=10.0  # Wait up to 10 seconds
            )
            
            wait_time = reservation.execute_at - time.time()
            print(f"Reserved for {user}: executable in {wait_time:.1f}s")
            reservations.append(reservation)
            
        except ValueError as e:
            print(f"Failed to reserve for {user}: {e}")
    
    print("\nExecuting reservations as they become ready...")
    
    # Sort by execution time
    reservations.sort(key=lambda r: r.execute_at)
    
    for reservation in reservations:
        # Wait until ready
        wait_time = reservation.execute_at - time.time()
        if wait_time > 0:
            print(f"Waiting {wait_time:.1f}s for {reservation.key}...")
            await asyncio.sleep(wait_time)
        
        # Execute
        try:
            result = await limiter.execute_reservation(reservation.id)
            if result.allowed:
                print(f"✓ Executed reservation for {reservation.key}")
        except Exception as e:
            print(f"✗ Failed to execute reservation: {e}")
    
    print("\nReservation system allows fair queuing of requests!")


async def adaptive_rate_limiting_example():
    """Example of adaptive rate limiter with rebalancing"""
    print("\n\n=== Adaptive Rate Limiter Example ===")
    
    # Create adaptive limiter
    limiter = AdaptiveShardedRateLimiter(
        rate=100,
        initial_shards=4,
        rebalance_threshold=0.3,    # Rebalance if >30% imbalanced
        rebalance_interval=2.0      # Check every 2 seconds
    )
    
    print("Simulating uneven load distribution...")
    
    # Simulate hot and cold keys
    hot_keys = ["popular_user_1", "popular_user_2"]
    cold_keys = [f"regular_user_{i}" for i in range(10)]
    
    # Generate biased traffic
    for i in range(50):
        # 80% of traffic goes to hot keys
        if random.random() < 0.8:
            key = random.choice(hot_keys)
        else:
            key = random.choice(cold_keys)
        
        result = await limiter.try_acquire(key)
        
        if i % 10 == 0:  # Print every 10th request
            balance = limiter.get_shard_balance()
            print(f"Request {i}: Imbalance ratio: {balance['imbalance_ratio']:.2f}")
    
    # Wait for potential rebalancing
    await asyncio.sleep(2.5)
    
    # Check final balance
    final_balance = limiter.get_shard_balance()
    print(f"\nFinal shard distribution: {final_balance['distribution']}")
    print(f"Rebalancing helps distribute load more evenly!")


async def distributed_rate_limiting_example():
    """Example of distributed rate limiting with namespaces"""
    print("\n\n=== Distributed Rate Limiter Example ===")
    
    # Create limiters for different services
    api_limiter = DistributedRateLimiter(
        rate=1000,
        namespace="api_service",
        backend="memory"  # Would use Redis in production
    )
    
    worker_limiter = DistributedRateLimiter(
        rate=500,
        namespace="background_worker",
        backend="memory"
    )
    
    print("Different services have isolated rate limits...")
    
    # Make requests from both services
    user = "shared_user_123"
    
    # API service requests
    api_success = 0
    for _ in range(10):
        result = await api_limiter.acquire(user)
        if result.allowed:
            api_success += 1
    
    # Worker service requests
    worker_success = 0
    for _ in range(10):
        result = await worker_limiter.acquire(user)
        if result.allowed:
            worker_success += 1
    
    print(f"\nSame user '{user}' in different namespaces:")
    print(f"  API Service: {api_success}/10 requests allowed")
    print(f"  Worker Service: {worker_success}/10 requests allowed")
    print("Namespaces provide isolation between services!")


async def real_world_api_client_example():
    """Real-world example: API client with rate limiting"""
    print("\n\n=== Real-World API Client Example ===")
    
    class APIClient:
        def __init__(self):
            # Different rate limits for different endpoints
            self.endpoint_limiters = {
                "/api/search": ShardedRateLimiter(
                    rate=100,   # 100 searches per minute
                    period=60.0,
                    shards=4
                ),
                "/api/create": ShardedRateLimiter(
                    rate=20,    # 20 creates per minute
                    period=60.0,
                    shards=2
                ),
                "/api/bulk": ShardedRateLimiter(
                    rate=5,     # 5 bulk operations per minute
                    period=60.0,
                    shards=1
                )
            }
            
            # Per-user rate limiter
            self.user_limiter = ShardedRateLimiter(
                rate=200,   # 200 total requests per user per minute
                period=60.0,
                shards=8
            )
        
        async def call_api(self, user_id: str, endpoint: str, data: dict):
            # Check user rate limit first
            user_result = await self.user_limiter.try_acquire(user_id)
            if not user_result.allowed:
                return {
                    "error": "user_rate_limit",
                    "retry_after": user_result.retry_after
                }
            
            # Check endpoint rate limit
            endpoint_limiter = self.endpoint_limiters.get(
                endpoint,
                self.endpoint_limiters["/api/search"]  # Default
            )
            
            endpoint_result = await endpoint_limiter.try_acquire(f"{user_id}:{endpoint}")
            if not endpoint_result.allowed:
                return {
                    "error": "endpoint_rate_limit",
                    "retry_after": endpoint_result.retry_after
                }
            
            # Simulate API call
            await asyncio.sleep(0.05)  # Simulate network delay
            
            return {
                "success": True,
                "endpoint": endpoint,
                "user": user_id,
                "timestamp": datetime.now().isoformat()
            }
    
    client = APIClient()
    
    # Simulate different usage patterns
    print("Simulating API usage patterns...")
    
    # Normal user - mixed endpoints
    print("\nNormal user pattern:")
    for endpoint in ["/api/search", "/api/search", "/api/create", "/api/search"]:
        result = await client.call_api("user_normal", endpoint, {})
        status = "✓ Success" if result.get("success") else f"✗ Limited: {result.get('error')}"
        print(f"  {endpoint}: {status}")
    
    # Heavy search user
    print("\nHeavy search user pattern:")
    for i in range(6):
        result = await client.call_api("user_searcher", "/api/search", {})
        if not result.get("success"):
            print(f"  Search {i+1}: Rate limited after {i} requests")
            break
        else:
            print(f"  Search {i+1}: Success")
    
    # Bulk operation user
    print("\nBulk operation pattern:")
    for i in range(3):
        result = await client.call_api("user_bulk", "/api/bulk", {})
        status = "✓ Success" if result.get("success") else f"✗ Limited"
        print(f"  Bulk operation {i+1}: {status}")
        await asyncio.sleep(0.5)


async def performance_comparison_example():
    """Compare performance of sharded vs non-sharded rate limiters"""
    print("\n\n=== Performance Comparison Example ===")
    
    from flashcard_pipeline.rate_limiter import RateLimiter  # Original non-sharded
    
    # Create limiters
    regular_limiter = RateLimiter(
        requests_per_minute=10000,
        burst_size=100
    )
    
    sharded_limiter = ShardedRateLimiter(
        rate=10000,
        period=60.0,
        shards=16,  # 16 shards for high throughput
        burst_size=100
    )
    
    # Test function
    async def benchmark_limiter(limiter, name: str, requests: int):
        start_time = time.time()
        success_count = 0
        
        # Use different keys to simulate real usage
        keys = [f"user_{i % 100}" for i in range(requests)]
        
        for key in keys:
            try:
                if hasattr(limiter, 'try_acquire'):
                    # Sharded limiter
                    result = await limiter.try_acquire(key)
                    if result.allowed:
                        success_count += 1
                else:
                    # Regular limiter
                    if limiter.try_acquire():
                        success_count += 1
            except:
                pass
        
        duration = time.time() - start_time
        
        print(f"\n{name}:")
        print(f"  Processed: {requests} requests")
        print(f"  Successful: {success_count}")
        print(f"  Duration: {duration:.3f}s")
        print(f"  Throughput: {requests / duration:.0f} req/s")
    
    # Run benchmarks
    print("Running performance comparison...")
    
    requests = 5000
    
    # Regular limiter
    await benchmark_limiter(regular_limiter, "Regular Rate Limiter", requests)
    
    # Sharded limiter
    await benchmark_limiter(sharded_limiter, "Sharded Rate Limiter (16 shards)", requests)
    
    print("\nSharding improves performance by reducing lock contention!")


async def main():
    """Run all examples"""
    examples = [
        basic_sharded_example,
        reservation_system_example,
        adaptive_rate_limiting_example,
        distributed_rate_limiting_example,
        real_world_api_client_example,
        performance_comparison_example,
    ]
    
    for example in examples:
        await example()
        print("\n" + "="*60)
    
    print("\nAll examples completed!")
    print("\nKey takeaways:")
    print("1. Sharding improves performance by distributing load")
    print("2. Reservations enable fair queuing and batch processing")
    print("3. Adaptive limiters can rebalance based on traffic patterns")
    print("4. Distributed limiters provide namespace isolation")
    print("5. Different strategies suit different use cases")


if __name__ == "__main__":
    asyncio.run(main())