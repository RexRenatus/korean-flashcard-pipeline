# Concurrent Processing Module

Handles parallel and distributed processing for the flashcard pipeline.

## Overview

This module provides concurrent processing capabilities to maximize throughput when dealing with large vocabulary datasets. It includes worker pools, distributed rate limiting, and batch processing utilities.

## Components

### Core Files
- **`__init__.py`** - Module exports and initialization
- **`worker_pool.py`** - Async worker pool implementation
- **`batch_processor.py`** - Batch processing logic
- **`distributed_rate_limiter.py`** - Distributed rate limiting across workers

### Key Features

1. **Worker Pool**
   - Configurable number of workers
   - Automatic task distribution
   - Error isolation per worker
   - Graceful shutdown

2. **Batch Processing**
   - Dynamic batch sizing
   - Memory-efficient processing
   - Progress tracking
   - Retry failed batches

3. **Rate Limiting**
   - Distributed token bucket
   - Redis-backed for multi-process
   - Configurable limits per API
   - Burst handling

## Usage Examples

```python
# Worker pool
from flashcard_pipeline.concurrent import WorkerPool

async with WorkerPool(workers=4) as pool:
    results = await pool.map(process_item, items)

# Batch processor
from flashcard_pipeline.concurrent import BatchProcessor

processor = BatchProcessor(batch_size=100)
async for batch_result in processor.process(items):
    handle_results(batch_result)

# Distributed rate limiter
from flashcard_pipeline.concurrent import DistributedRateLimiter

limiter = DistributedRateLimiter(rate=60, interval=60)  # 60/min
async with limiter.acquire():
    await make_api_call()
```

## Configuration

- `WORKER_COUNT` - Number of concurrent workers (default: CPU count)
- `BATCH_SIZE` - Items per batch (default: 100)
- `RATE_LIMIT` - API calls per minute (default: 60)
- `REDIS_URL` - Redis connection for distributed limiting

## Performance Considerations

1. **Worker Count**: Start with CPU count, adjust based on I/O vs CPU work
2. **Batch Size**: Balance between memory and efficiency
3. **Rate Limits**: Leave headroom for burst traffic
4. **Error Handling**: Isolate failures to prevent cascade

## Monitoring

The module provides metrics for:
- Tasks processed per second
- Worker utilization
- Rate limit usage
- Error rates
- Queue depths

## Best Practices

1. Use appropriate worker count for workload type
2. Monitor memory usage with large batches
3. Implement proper cleanup in workers
4. Handle partial batch failures
5. Use circuit breakers for external services