# Retry System Migration Guide

## Overview

This guide helps you migrate from the existing tenacity-based retry system to the new enhanced retry system with structured error handling.

## Key Improvements

1. **Exponential Backoff with Jitter**: Prevents thundering herd problems
2. **Structured Error Handling**: Better error categorization and recovery information
3. **Integration with Circuit Breaker**: Coordinated failure handling
4. **Health Metrics**: Built-in success/failure tracking

## Migration Steps

### 1. Update Imports

**Old (tenacity-based):**
```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
    before_sleep_log,
)
```

**New:**
```python
from flashcard_pipeline.utils.retry import RetryConfig, retry_async, retry_sync
from flashcard_pipeline.exceptions import (
    StructuredAPIError,
    StructuredRateLimitError,
    NetworkError,
    RetryExhausted,
)
```

### 2. Update Retry Decorators

**Old:**
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=10),
    retry=retry_if_exception_type((httpx.HTTPError, APIError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
async def make_api_call():
    # API call logic
```

**New:**
```python
@retry_async(RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=10.0,
    exponential_base=2.0,
    jitter=True,
    retry_on=(httpx.HTTPError, NetworkError, StructuredAPIError)
))
async def make_api_call():
    # API call logic
```

### 3. Update Error Handling

**Old:**
```python
try:
    response = await client.post(url, json=data)
    response.raise_for_status()
except httpx.HTTPStatusError as e:
    if e.response.status_code == 429:
        raise RateLimitError(f"Rate limit exceeded: {e}")
    raise APIError(f"API request failed: {e}")
```

**New:**
```python
try:
    response = await client.post(url, json=data)
    
    if response.status_code == 429:
        retry_after = response.headers.get("retry-after")
        raise StructuredRateLimitError(
            message="Rate limit exceeded",
            retry_after=float(retry_after) if retry_after else None,
        )
    
    response.raise_for_status()
    
except httpx.HTTPStatusError as e:
    raise StructuredAPIError(
        status_code=e.response.status_code,
        message=f"API request failed: {e}",
        response=e.response.json() if e.response.text else None,
    )
```

### 4. Update API Client Usage

**Old:**
```python
from flashcard_pipeline.api.client import OpenRouterClient

client = OpenRouterClient(
    api_key=api_key,
    max_retries=3,
)
```

**New:**
```python
from flashcard_pipeline.api.enhanced_client import EnhancedOpenRouterClient
from flashcard_pipeline.utils.retry import RetryConfig

client = EnhancedOpenRouterClient(
    api_key=api_key,
    retry_config=RetryConfig(
        max_attempts=3,
        initial_delay=1.0,
        jitter=True,
    )
)
```

### 5. Handle Retry Exhaustion

**Old:**
```python
try:
    result = await make_api_call()
except Exception as e:
    logger.error(f"API call failed: {e}")
    raise
```

**New:**
```python
try:
    result = await make_api_call()
except RetryExhausted as e:
    # Access the last exception for details
    if isinstance(e.last_exception, StructuredRateLimitError):
        logger.error(f"Rate limited. Retry after: {e.last_exception.retry_after}s")
    else:
        logger.error(f"All retries failed: {e.last_exception}")
    raise
```

## Configuration Examples

### Basic Configuration
```python
# Simple retry with defaults
@retry_async()
async def simple_call():
    return await api.get("/endpoint")
```

### Custom Configuration
```python
# Custom retry for specific use case
config = RetryConfig(
    max_attempts=5,
    initial_delay=2.0,
    max_delay=60.0,
    exponential_base=1.5,  # Slower backoff
    jitter=True,
    retry_on=(NetworkError, StructuredAPIError)  # Specific errors
)

@retry_async(config)
async def resilient_call():
    return await api.post("/critical-endpoint", json=data)
```

### No Jitter (Testing)
```python
# Predictable delays for testing
test_config = RetryConfig(
    max_attempts=3,
    initial_delay=0.1,
    jitter=False  # Predictable timing
)
```

## Health Monitoring

The enhanced client provides built-in health metrics:

```python
# Get health status
status = client.get_health_status()

print(f"Success rate: {status['health']['success_rate']:.2%}")
print(f"Average latency: {status['health']['avg_latency_ms']:.1f}ms")
print(f"Consecutive failures: {status['health']['consecutive_failures']}")
```

## Testing Your Migration

### Unit Tests
```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_retry_on_network_error():
    # Mock that fails twice then succeeds
    mock_api = AsyncMock()
    mock_api.side_effect = [
        NetworkError("Failed"),
        NetworkError("Failed"),
        {"success": True}
    ]
    
    @retry_async(RetryConfig(max_attempts=3, initial_delay=0.01))
    async def call_api():
        return await mock_api()
    
    result = await call_api()
    assert result == {"success": True}
    assert mock_api.call_count == 3
```

### Integration Tests
```python
# Test with real delays
@pytest.mark.asyncio
async def test_exponential_backoff_timing():
    start_times = []
    
    @retry_async(RetryConfig(
        max_attempts=3,
        initial_delay=0.1,
        jitter=False
    ))
    async def timed_call():
        start_times.append(time.time())
        if len(start_times) < 3:
            raise NetworkError("Test")
        return "success"
    
    await timed_call()
    
    # Verify delays
    assert 0.09 < start_times[1] - start_times[0] < 0.11  # ~0.1s
    assert 0.19 < start_times[2] - start_times[1] < 0.21  # ~0.2s
```

## Common Patterns

### 1. Fast Retry for Transient Errors
```python
fast_retry = RetryConfig(
    max_attempts=3,
    initial_delay=0.5,
    max_delay=2.0,
    retry_on=(NetworkError,)  # Only network errors
)
```

### 2. Slow Retry for Rate Limits
```python
rate_limit_retry = RetryConfig(
    max_attempts=5,
    initial_delay=5.0,
    max_delay=300.0,  # 5 minutes max
    exponential_base=2.0,
    retry_on=(StructuredRateLimitError,)
)
```

### 3. No Retry for Client Errors
```python
@retry_async(RetryConfig(
    retry_on=(NetworkError, StructuredAPIError),
    # Exclude 4xx errors except 429
))
async def api_call():
    try:
        response = await make_request()
    except StructuredAPIError as e:
        if 400 <= e.status_code < 500 and e.status_code != 429:
            raise  # Don't retry client errors
        raise  # Retry server errors
```

## Rollback Plan

If you need to rollback to the old system:

1. Keep the old `api_client.py` as `api_client_legacy.py`
2. Use feature flags to toggle between implementations:

```python
if os.getenv("USE_ENHANCED_RETRY", "true").lower() == "true":
    from flashcard_pipeline.api.enhanced_client import EnhancedOpenRouterClient as APIClient
else:
    from flashcard_pipeline.api.client import OpenRouterClient as APIClient
```

## Performance Considerations

1. **Jitter Impact**: Jitter adds 0-50% random delay, preventing synchronized retries
2. **Memory Usage**: Structured errors store more context but improve debugging
3. **Circuit Breaker**: Combine with circuit breaker to fail fast when services are down

## Next Steps

1. Update your API clients to use `EnhancedOpenRouterClient`
2. Replace tenacity decorators with `@retry_async` or `@retry_sync`
3. Update error handling to use structured exceptions
4. Add health monitoring to your dashboards
5. Test retry behavior in your staging environment

For questions or issues, see the [examples/retry_demo.py](../examples/retry_demo.py) for working examples.