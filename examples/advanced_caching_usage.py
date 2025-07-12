"""Examples of using the advanced cache manager"""

import asyncio
import time
import random
from pathlib import Path
import tempfile

from flashcard_pipeline.cache.cache_manager_v2 import (
    CacheManager,
    L1Cache,
    L2Cache,
    CacheStrategy,
    EvictionPolicy,
)


async def basic_caching_example():
    """Basic multi-tier caching example"""
    print("\n=== Basic Multi-Tier Caching Example ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create cache manager with L1 and L2
        cache = CacheManager(
            l1_config={
                "max_size": 100,
                "max_memory_mb": 10,
                "default_ttl": 300.0  # 5 minutes
            },
            l2_config={
                "backend": "disk",
                "disk_path": str(Path(tmpdir) / "l2_cache"),
                "max_size_mb": 100,
                "compression": True
            },
            enable_l2=True
        )
        
        # Simple set/get
        await cache.set("user:123", {"name": "John", "score": 100})
        user_data = await cache.get("user:123")
        print(f"Retrieved user data: {user_data}")
        
        # Cache miss with compute function
        async def fetch_user(user_id: str):
            print(f"Fetching user {user_id} from database...")
            await asyncio.sleep(0.1)  # Simulate DB query
            return {"name": f"User {user_id}", "score": random.randint(50, 150)}
        
        # First call computes
        user_456 = await cache.get("user:456", lambda: fetch_user("456"))
        print(f"User 456 (computed): {user_456}")
        
        # Second call uses cache
        user_456_cached = await cache.get("user:456", lambda: fetch_user("456"))
        print(f"User 456 (cached): {user_456_cached}")
        
        # Check statistics
        stats = cache.get_statistics()
        print(f"\nCache statistics:")
        print(f"  L1 hit rate: {stats['l1']['hit_rate']:.1%}")
        print(f"  Overall hit rate: {stats['overall_hit_rate']:.1%}")


async def eviction_policies_example():
    """Demonstrate different eviction policies"""
    print("\n\n=== Eviction Policies Example ===")
    
    # LRU Example
    print("\n1. LRU (Least Recently Used):")
    lru_cache = L1Cache(max_size=3, eviction_policy=EvictionPolicy.LRU)
    
    # Fill cache
    for i in range(3):
        await lru_cache.set(f"lru_{i}", f"value_{i}")
    
    # Access first item to make it recently used
    await lru_cache.get("lru_0")
    
    # Add new item - should evict lru_1 (least recently used)
    await lru_cache.set("lru_3", "value_3")
    
    print("  After eviction:")
    for i in range(4):
        value = await lru_cache.get(f"lru_{i}")
        print(f"    lru_{i}: {value}")
    
    # LFU Example
    print("\n2. LFU (Least Frequently Used):")
    lfu_cache = L1Cache(max_size=3, eviction_policy=EvictionPolicy.LFU)
    
    # Fill cache and access with different frequencies
    await lfu_cache.set("popular", "data")
    await lfu_cache.set("moderate", "data")
    await lfu_cache.set("rare", "data")
    
    # Access patterns
    for _ in range(5):
        await lfu_cache.get("popular")
    for _ in range(2):
        await lfu_cache.get("moderate")
    # "rare" accessed 0 times
    
    # Add new item - should evict "rare"
    await lfu_cache.set("new", "data")
    
    print("  After eviction:")
    for key in ["popular", "moderate", "rare", "new"]:
        value = await lfu_cache.get(key)
        print(f"    {key}: {'cached' if value else 'evicted'}")


async def cache_stampede_example():
    """Demonstrate cache stampede protection"""
    print("\n\n=== Cache Stampede Protection Example ===")
    
    cache = CacheManager(stampede_protection=True)
    
    compute_count = 0
    
    async def expensive_computation():
        nonlocal compute_count
        compute_count += 1
        print(f"  Starting expensive computation #{compute_count}...")
        await asyncio.sleep(1.0)  # Simulate expensive operation
        result = f"expensive_result_{compute_count}"
        print(f"  Completed computation #{compute_count}")
        return result
    
    print("Launching 5 concurrent requests for the same uncached key:")
    
    # Launch multiple concurrent requests
    tasks = []
    for i in range(5):
        task = cache.get("expensive_key", expensive_computation)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    
    print(f"\nResults: {results}")
    print(f"Computation was called {compute_count} time(s)")
    print("All requests got the same result without duplicate computation!")


async def cache_warming_example():
    """Demonstrate cache warming strategies"""
    print("\n\n=== Cache Warming Example ===")
    
    cache = CacheManager()
    
    # Simulate database with product data
    products_db = {
        "prod_1": {"name": "Widget", "price": 9.99, "stock": 100},
        "prod_2": {"name": "Gadget", "price": 19.99, "stock": 50},
        "prod_3": {"name": "Doohickey", "price": 14.99, "stock": 75},
        "prod_4": {"name": "Thingamajig", "price": 24.99, "stock": 30},
        "prod_5": {"name": "Whatsit", "price": 4.99, "stock": 200},
    }
    
    async def fetch_product(product_id: str):
        print(f"  Fetching {product_id} from database...")
        await asyncio.sleep(0.1)  # Simulate DB query
        return products_db.get(product_id)
    
    print("Warming cache with popular products...")
    
    # Warm cache with popular products
    popular_products = ["prod_1", "prod_2", "prod_3"]
    await cache.warm_cache(
        popular_products,
        fetch_product,
        ttl=3600.0,  # 1 hour
        batch_size=2
    )
    
    print("\nCache warmed! Now accessing products:")
    
    # Access products - popular ones should be instant
    for prod_id in ["prod_1", "prod_2", "prod_3", "prod_4"]:
        start = time.time()
        product = await cache.get(prod_id, lambda: fetch_product(prod_id))
        elapsed = time.time() - start
        print(f"  {prod_id}: {product['name']} - {elapsed*1000:.1f}ms")


async def refresh_ahead_example():
    """Demonstrate refresh-ahead caching strategy"""
    print("\n\n=== Refresh-Ahead Strategy Example ===")
    
    cache = CacheManager(strategy=CacheStrategy.REFRESH_AHEAD)
    
    version = 0
    
    async def get_config():
        nonlocal version
        version += 1
        print(f"  Fetching config version {version}")
        return {
            "version": version,
            "feature_flags": {
                "new_ui": version >= 2,
                "advanced_mode": version >= 3
            }
        }
    
    print("Starting refresh-ahead for configuration:")
    
    # Start refresh-ahead with short TTL for demo
    await cache.start_refresh_ahead(
        "app_config",
        get_config,
        ttl=2.0,  # 2 seconds TTL
        refresh_before=0.5  # Refresh 0.5s before expiry
    )
    
    # Access config multiple times
    for i in range(5):
        config = await cache.get("app_config")
        print(f"  Time {i}: Config version {config['version']}")
        await asyncio.sleep(0.8)
    
    # Clean up background task
    if "app_config" in cache._warm_tasks:
        cache._warm_tasks["app_config"].cancel()
    
    print("\nConfiguration was automatically refreshed in the background!")


async def tagged_caching_example():
    """Demonstrate tag-based cache management"""
    print("\n\n=== Tagged Caching Example ===")
    
    cache = CacheManager()
    
    # Cache different types of data with tags
    print("Caching data with tags:")
    
    # User session data
    await cache.set("session:user123", {"user_id": 123, "role": "admin"}, 
                   tags=["session", "user:123"])
    await cache.set("session:user456", {"user_id": 456, "role": "user"}, 
                   tags=["session", "user:456"])
    
    # User profile data
    await cache.set("profile:user123", {"name": "Alice", "email": "alice@example.com"}, 
                   tags=["profile", "user:123"])
    await cache.set("profile:user456", {"name": "Bob", "email": "bob@example.com"}, 
                   tags=["profile", "user:456"])
    
    # API responses
    await cache.set("api:users", ["user123", "user456"], 
                   tags=["api", "users"])
    
    print("\nCurrent cache contents:")
    for key in ["session:user123", "session:user456", "profile:user123", 
                "profile:user456", "api:users"]:
        value = await cache.get(key)
        print(f"  {key}: {'cached' if value else 'not found'}")
    
    # Invalidate all session data
    print("\nInvalidating all session data (by tag):")
    await cache.delete_by_tag("session")
    
    print("\nCache contents after session invalidation:")
    for key in ["session:user123", "session:user456", "profile:user123", 
                "profile:user456", "api:users"]:
        value = await cache.get(key)
        print(f"  {key}: {'cached' if value else 'not found'}")


async def performance_monitoring_example():
    """Demonstrate cache performance monitoring"""
    print("\n\n=== Performance Monitoring Example ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = CacheManager(
            l1_config={"max_size": 50},
            l2_config={
                "backend": "disk",
                "disk_path": str(Path(tmpdir) / "l2_cache")
            }
        )
        
        print("Simulating mixed cache access patterns...")
        
        # Simulate various access patterns
        for i in range(100):
            key = f"item_{i % 20}"  # 20 unique keys
            
            if random.random() < 0.7:  # 70% reads
                value = await cache.get(
                    key,
                    lambda k=key: f"value_for_{k}"
                )
            else:  # 30% writes
                await cache.set(key, f"updated_{i}")
        
        # Get detailed statistics
        stats = cache.get_statistics()
        
        print("\n=== Cache Performance Report ===")
        print(f"\nL1 Cache (In-Memory):")
        print(f"  Hit Rate: {stats['l1']['hit_rate']:.1%}")
        print(f"  Entries: {stats['l1']['entries']}")
        print(f"  Size: {stats['l1']['size_bytes'] / 1024:.1f} KB")
        print(f"  Evictions: {stats['l1']['evictions']}")
        
        print(f"\nL2 Cache (Disk):")
        print(f"  Hit Rate: {stats['l2']['hit_rate']:.1%}")
        print(f"  Hits: {stats['l2']['hits']}")
        print(f"  Misses: {stats['l2']['misses']}")
        print(f"  Errors: {stats['l2']['errors']}")
        
        print(f"\nOverall Performance:")
        print(f"  Combined Hit Rate: {stats['overall_hit_rate']:.1%}")
        
        # Analyze cache efficiency
        l1_stats = cache.l1_cache.stats
        total_requests = l1_stats.hits + l1_stats.misses
        
        if total_requests > 0:
            print(f"\nCache Efficiency Analysis:")
            print(f"  Total Requests: {total_requests}")
            print(f"  L1 Hits: {l1_stats.hits} ({l1_stats.hits/total_requests:.1%})")
            print(f"  L1 Misses: {l1_stats.misses} ({l1_stats.misses/total_requests:.1%})")
            
            if l1_stats.evictions > 0:
                print(f"\n  ⚠️  High eviction rate detected!")
                print(f"     Consider increasing L1 cache size")


async def real_world_flashcard_example():
    """Real-world example: Caching in flashcard pipeline"""
    print("\n\n=== Real-World: Flashcard Pipeline Caching ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = CacheManager(
            l1_config={
                "max_size": 1000,
                "default_ttl": 3600.0  # 1 hour
            },
            l2_config={
                "backend": "disk",
                "disk_path": str(Path(tmpdir) / "flashcard_cache"),
                "compression": True
            }
        )
        
        # Simulate flashcard processing
        async def process_flashcard_stage1(word: str):
            print(f"  Processing stage 1 for '{word}'...")
            await asyncio.sleep(0.5)  # Simulate API call
            return {
                "word": word,
                "base_translation": f"Translation of {word}",
                "difficulty": random.randint(1, 5)
            }
        
        async def process_flashcard_stage2(stage1_data: dict):
            print(f"  Processing stage 2 for '{stage1_data['word']}'...")
            await asyncio.sleep(0.5)  # Simulate API call
            return {
                **stage1_data,
                "nuances": ["Nuance 1", "Nuance 2"],
                "examples": ["Example 1", "Example 2"]
            }
        
        # Process flashcards with caching
        words = ["안녕하세요", "감사합니다", "사랑해요"]
        
        print("First processing run (cache miss):")
        start_time = time.time()
        
        for word in words:
            # Stage 1 with caching
            stage1_result = await cache.get(
                f"stage1:{word}",
                lambda w=word: process_flashcard_stage1(w),
                ttl=3600.0,
                tags=["stage1", f"word:{word}"]
            )
            
            # Stage 2 with caching
            stage2_result = await cache.get(
                f"stage2:{word}",
                lambda s1=stage1_result: process_flashcard_stage2(s1),
                ttl=3600.0,
                tags=["stage2", f"word:{word}"]
            )
        
        first_run_time = time.time() - start_time
        print(f"First run completed in {first_run_time:.2f}s")
        
        print("\nSecond processing run (cache hit):")
        start_time = time.time()
        
        for word in words:
            stage1_result = await cache.get(
                f"stage1:{word}",
                lambda w=word: process_flashcard_stage1(w)
            )
            stage2_result = await cache.get(
                f"stage2:{word}",
                lambda s1=stage1_result: process_flashcard_stage2(s1)
            )
        
        second_run_time = time.time() - start_time
        print(f"Second run completed in {second_run_time:.2f}s")
        print(f"Speed improvement: {first_run_time/second_run_time:.1f}x faster!")
        
        # Show cache stats
        stats = cache.get_statistics()
        print(f"\nCache performance:")
        print(f"  Hit rate: {stats['overall_hit_rate']:.1%}")
        print(f"  Time saved: {first_run_time - second_run_time:.2f}s")


async def main():
    """Run all examples"""
    examples = [
        basic_caching_example,
        eviction_policies_example,
        cache_stampede_example,
        cache_warming_example,
        refresh_ahead_example,
        tagged_caching_example,
        performance_monitoring_example,
        real_world_flashcard_example,
    ]
    
    for example in examples:
        await example()
        print("\n" + "="*60)
    
    print("\nAll examples completed!")
    print("\nKey takeaways:")
    print("1. Multi-tier caching (L1/L2) provides speed and capacity")
    print("2. Eviction policies (LRU/LFU) optimize cache efficiency")
    print("3. Stampede protection prevents redundant computations")
    print("4. Cache warming improves initial performance")
    print("5. Refresh-ahead keeps frequently accessed data fresh")
    print("6. Tag-based invalidation simplifies cache management")
    print("7. Performance monitoring helps optimize cache configuration")


if __name__ == "__main__":
    asyncio.run(main())