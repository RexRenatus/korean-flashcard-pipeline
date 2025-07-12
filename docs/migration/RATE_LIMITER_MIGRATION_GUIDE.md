# Rate Limiter Migration Guide

This guide helps you migrate from the existing rate limiter to the new sharded rate limiter with enhanced features.

## Overview

The new rate limiter provides:
- **Sharding** for better performance at scale
- **Token reservation** system for fair queuing
- **Power-of-two shard selection** for optimal distribution
- **Adaptive rebalancing** for handling hot keys
- **Distributed support** with namespace isolation

## Migration Strategies

### Strategy 1: Drop-in Replacement (Basic)

For simple use cases, you can replace the existing rate limiter with minimal changes:

```python
# Old
from flashcard_pipeline.rate_limiter import RateLimiter

limiter = RateLimiter(
    requests_per_minute=600,
    requests_per_hour=36000,
    burst_size=20
)

# New - Basic compatibility
from flashcard_pipeline.rate_limiter_v2 import ShardedRateLimiter

limiter = ShardedRateLimiter(
    rate=600,
    period=60.0,
    shards=1,  # Single shard = similar to old behavior
    burst_size=20
)
```

### Strategy 2: Gradual Enhancement

Start with basic replacement, then add features:

```python
# Step 1: Basic replacement
limiter = ShardedRateLimiter(rate=600, period=60.0)

# Step 2: Add sharding for performance
limiter = ShardedRateLimiter(
    rate=600,
    period=60.0,
    shards=4  # Automatic optimal calculation
)

# Step 3: Add reservations for fairness
reservation = await limiter.reserve("user_123", max_wait=5.0)
# ... wait until ready ...
result = await limiter.execute_reservation(reservation.id)
```

### Strategy 3: Full Migration

Complete migration with all features:

```python
# Old implementation
class APIClient:
    def __init__(self):
        self.rate_limiter = RateLimiter(
            requests_per_minute=600,
            burst_size=20
        )
    
    async def make_request(self, user_id: str):
        await self.rate_limiter.acquire()
        return await self._call_api()

# New implementation with full features
class APIClient:
    def __init__(self):
        self.rate_limiter = ShardedRateLimiter(
            rate=600,
            period=60.0,
            shards=8,  # Better performance
            algorithm="token_bucket"
        )
    
    async def make_request(self, user_id: str):
        # Use sharding with user_id as key
        result = await self.rate_limiter.acquire(user_id)
        if not result.allowed:
            raise RateLimitError(
                f"Rate limited",
                retry_after=result.retry_after
            )
        return await self._call_api()
    
    async def make_batch_request(self, user_ids: List[str]):
        # Use reservations for batch processing
        reservations = []
        for user_id in user_ids:
            reservation = await self.rate_limiter.reserve(
                user_id,
                max_wait=30.0
            )
            reservations.append(reservation)
        
        # Process when ready
        results = []
        for reservation in sorted(reservations, key=lambda r: r.execute_at):
            wait_time = reservation.execute_at - time.time()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            
            result = await self.rate_limiter.execute_reservation(reservation.id)
            if result.allowed:
                results.append(await self._call_api())
        
        return results
```

## API Compatibility

### Changed Methods

| Old Method | New Method | Notes |
|------------|------------|-------|
| `acquire(tokens=1)` | `acquire(key="default", count=1)` | Now returns `RateLimitResult` |
| `try_acquire(tokens=1)` | `try_acquire(key="default", count=1)` | Returns result object instead of bool |
| `wait_if_needed(tokens=1)` | Built into retry logic | Use with retry decorator |

### New Methods

| Method | Purpose |
|--------|---------|
| `reserve(key, count, max_wait)` | Reserve tokens for future use |
| `execute_reservation(reservation_id)` | Execute a reservation |
| `cancel_reservation(reservation_id)` | Cancel a reservation |
| `get_shard_balance()` | Check shard distribution |

### Return Value Changes

Old `try_acquire` returned bool:
```python
if limiter.try_acquire():
    # proceed
else:
    # rate limited
```

New `try_acquire` returns `RateLimitResult`:
```python
result = await limiter.try_acquire("user_123")
if result.allowed:
    # proceed
    print(f"Tokens remaining: {result.tokens_remaining}")
else:
    # rate limited
    print(f"Retry after: {result.retry_after}s")
```

## Configuration Mapping

### Basic Configuration

| Old Parameter | New Parameter | Default | Notes |
|---------------|---------------|---------|-------|
| `requests_per_minute` | `rate` | Required | Same meaning |
| N/A | `period` | 60.0 | Time window in seconds |
| `burst_size` | `burst_size` | Same as rate | Optional burst capacity |
| N/A | `shards` | Auto-calculated | Number of shards |

### Environment Variables

Old:
```bash
REQUESTS_PER_MINUTE=600
REQUESTS_PER_HOUR=36000
BURST_SIZE=20
```

New (if using compatibility mode):
```bash
# Same variables work with ShardedRateLimiter(shards=1)
REQUESTS_PER_MINUTE=600
REQUESTS_PER_HOUR=36000
BURST_SIZE=20

# Or use new explicit configuration
RATE_LIMIT_RATE=600
RATE_LIMIT_PERIOD=60
RATE_LIMIT_SHARDS=4
```

## Feature Comparison

| Feature | Old Rate Limiter | New Sharded Rate Limiter |
|---------|------------------|--------------------------|
| Basic rate limiting | ✓ | ✓ |
| Token bucket | ✓ | ✓ |
| Sliding window | ✓ | ✓ |
| Burst capacity | ✓ | ✓ |
| Async support | ✓ | ✓ |
| **Sharding** | ✗ | ✓ |
| **Reservations** | ✗ | ✓ |
| **Key-based distribution** | ✗ | ✓ |
| **Adaptive rebalancing** | ✗ | ✓ |
| **Distributed support** | ✗ | ✓ |
| **Detailed result info** | ✗ | ✓ |

## Migration Examples

### Example 1: Simple Rate Limiting

```python
# Old
limiter = RateLimiter(requests_per_minute=60)

async def process_request():
    await limiter.acquire()
    return process()

# New - Minimal changes
limiter = ShardedRateLimiter(rate=60, shards=1)

async def process_request():
    await limiter.acquire()  # Still works!
    return process()

# New - With improvements
limiter = ShardedRateLimiter(rate=60, shards=4)

async def process_request(user_id: str):
    result = await limiter.acquire(user_id)  # Sharded by user
    if not result.allowed:
        raise RateLimitError(retry_after=result.retry_after)
    return process()
```

### Example 2: Adaptive Rate Limiting

```python
# Old
limiter = AdaptiveRateLimiter(
    initial_requests_per_minute=600,
    burst_size=20
)

# New - With adaptive sharding
limiter = AdaptiveShardedRateLimiter(
    rate=600,
    initial_shards=4,
    rebalance_threshold=0.3,
    rebalance_interval=300.0
)

# Automatically rebalances shards based on traffic patterns
```

### Example 3: Composite Limiting

```python
# Old
composite = CompositeLimiter()
await composite.acquire_for_stage(1, estimated_tokens=350)

# New - With better isolation
class EnhancedCompositeLimiter:
    def __init__(self):
        self.api_limiter = ShardedRateLimiter(rate=600, shards=8)
        self.cost_limiter = ShardedRateLimiter(rate=300, shards=4)
        self.stage_limiters = {
            1: ShardedRateLimiter(rate=300, shards=4),
            2: ShardedRateLimiter(rate=300, shards=4)
        }
    
    async def acquire_for_stage(self, stage: int, user_id: str):
        # Check all limits with proper keys
        await self.api_limiter.acquire(f"api:{user_id}")
        await self.cost_limiter.acquire(f"cost:{user_id}")
        await self.stage_limiters[stage].acquire(f"stage{stage}:{user_id}")
```

## Performance Considerations

### When to Use Sharding

1. **High request rate** (>1000 req/min): Use 4-16 shards
2. **Many concurrent users**: Shards = sqrt(concurrent_users)
3. **Hot key problem**: Use adaptive sharding
4. **Distributed system**: Use DistributedRateLimiter

### Shard Count Guidelines

| Request Rate | Recommended Shards | Notes |
|--------------|-------------------|-------|
| < 100/min | 1 | No sharding needed |
| 100-1000/min | 2-4 | Light sharding |
| 1000-10k/min | 4-8 | Moderate sharding |
| > 10k/min | 8-16 | Heavy sharding |

### Memory Usage

- Base overhead: ~1KB per rate limiter
- Per shard: ~200 bytes
- Per reservation: ~100 bytes
- Total: `base + (shards * 200) + (active_reservations * 100)`

## Troubleshooting

### Issue: Different rate limiting behavior

**Cause**: Sharding distributes tokens across shards.

**Solution**: Use `shards=1` for identical behavior to old limiter.

### Issue: Uneven distribution

**Cause**: Poor key distribution or hot keys.

**Solution**: Use `AdaptiveShardedRateLimiter` or better key design.

### Issue: Memory usage increased

**Cause**: Multiple shards and reservation tracking.

**Solution**: Reduce shard count or implement reservation cleanup.

## Best Practices

1. **Choose meaningful keys**: Use user IDs, API keys, or IP addresses
2. **Let shards auto-calculate**: The system optimizes based on rate
3. **Use reservations for batches**: Ensures fair processing order
4. **Monitor shard balance**: Check `get_shard_balance()` periodically
5. **Start conservative**: Begin with fewer shards, increase as needed

## Testing Your Migration

```python
import pytest
from flashcard_pipeline.rate_limiter import RateLimiter
from flashcard_pipeline.rate_limiter_v2 import ShardedRateLimiter

@pytest.mark.asyncio
async def test_migration_compatibility():
    """Verify similar behavior between old and new"""
    old_limiter = RateLimiter(requests_per_minute=60)
    new_limiter = ShardedRateLimiter(rate=60, shards=1)
    
    # Both should allow similar request patterns
    old_results = []
    new_results = []
    
    for i in range(10):
        old_allowed = old_limiter.try_acquire()
        new_result = await new_limiter.try_acquire()
        
        old_results.append(old_allowed)
        new_results.append(new_result.allowed)
    
    # Should have similar patterns
    assert old_results == new_results
```

## Rollback Plan

If you need to rollback:

1. **Keep old imports**: Don't delete old rate limiter immediately
2. **Feature flag**: Use environment variable to switch
3. **Gradual rollout**: Migrate service by service

```python
import os

if os.getenv("USE_NEW_RATE_LIMITER", "false").lower() == "true":
    from flashcard_pipeline.rate_limiter_v2 import ShardedRateLimiter as RateLimiter
else:
    from flashcard_pipeline.rate_limiter import RateLimiter

# Rest of code remains the same
```

## Support

For questions or issues during migration:

1. Check the examples in `examples/sharded_rate_limiter_usage.py`
2. Run tests with `pytest tests/unit/test_sharded_rate_limiter.py`
3. Review integration tests for real-world patterns
4. Enable debug logging: `logging.getLogger("flashcard_pipeline.rate_limiter_v2").setLevel(logging.DEBUG)`

## Summary

The new sharded rate limiter is designed to be backward compatible while providing significant improvements for high-scale scenarios. Start with minimal changes and gradually adopt advanced features as needed.