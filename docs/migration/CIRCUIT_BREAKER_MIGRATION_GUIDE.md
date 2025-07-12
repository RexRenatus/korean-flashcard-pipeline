# Circuit Breaker Migration Guide

## Overview

This guide helps you migrate from the existing circuit breaker implementation to the enhanced version with state monitoring, manual control, and dynamic break duration.

## Key Improvements

1. **State Monitoring**: Real-time visibility into circuit breaker state and metrics
2. **Manual Control**: Ability to isolate, reset, or force state changes
3. **Dynamic Break Duration**: Adaptive recovery times based on failure patterns
4. **Integration with Retry System**: Seamless coordination with Week 1's retry enhancements

## Migration Steps

### 1. Update Imports

**Old:**
```python
from flashcard_pipeline.circuit_breaker import CircuitBreaker
```

**New:**
```python
from flashcard_pipeline.circuit_breaker_v2 import (
    EnhancedCircuitBreaker,
    CircuitState,
    exponential_break_duration,
    linear_break_duration,
    adaptive_break_duration,
)
```

### 2. Update Circuit Breaker Initialization

**Old:**
```python
breaker = CircuitBreaker(
    failure_threshold=5,       # Number of failures
    recovery_timeout=60,       # Fixed timeout
    expected_exception=Exception,
    name="my_service"
)
```

**New:**
```python
breaker = EnhancedCircuitBreaker(
    failure_threshold=0.5,     # Now a ratio (50%)
    min_throughput=10,         # Minimum calls before evaluation
    sampling_duration=10.0,    # Time window for sampling
    break_duration=60.0,       # Base break duration
    # Optional: Use dynamic break duration
    break_duration_generator=exponential_break_duration,
    expected_exception=Exception,
    name="my_service",
    enable_monitoring=True,    # Enable state monitoring
    enable_manual_control=True # Enable manual control
)
```

### 3. Key Parameter Changes

| Old Parameter | New Parameter | Description |
|--------------|---------------|-------------|
| `failure_threshold` (count) | `failure_threshold` (ratio) | Changed from absolute count to failure ratio (0.0-1.0) |
| N/A | `min_throughput` | Minimum calls before evaluating failure ratio |
| N/A | `sampling_duration` | Time window for calculating failure ratio |
| `recovery_timeout` | `break_duration` | Base duration for circuit break |
| N/A | `break_duration_generator` | Function for dynamic break duration |

### 4. Using State Monitoring

**Access monitoring data:**
```python
# Get state provider
provider = breaker.state_provider

# Get current stats
stats = provider.stats
print(f"State: {stats['state']}")
print(f"Success rate: {stats['success_rate']}")
print(f"Time in state: {stats['time_in_state']}s")

# Get state change history
timeline = provider.get_state_timeline(hours=1)
for event in timeline:
    print(f"{event['timestamp']}: {event['from_state']} → {event['to_state']}")
```

### 5. Using Manual Control

**Manual control operations:**
```python
# Get manual control interface
control = breaker.manual_control

# Isolate service (e.g., for maintenance)
await control.isolate("Scheduled maintenance")

# Check if isolated
if control.is_isolated:
    info = control.isolation_info
    print(f"Isolated: {info['reason']}")

# Reset circuit
await control.reset()

# Force to half-open (from open state)
await control.force_half_open()
```

### 6. Dynamic Break Duration

**Built-in generators:**
```python
# Exponential backoff (recommended)
breaker = EnhancedCircuitBreaker(
    break_duration_generator=exponential_break_duration,
    # Base: 30s, Factor: 1.5
)

# Linear increase
breaker = EnhancedCircuitBreaker(
    break_duration_generator=linear_break_duration,
    # Base: 30s, Increment: 15s
)

# Adaptive (based on failure count)
breaker = EnhancedCircuitBreaker(
    break_duration_generator=adaptive_break_duration,
    # 30s for 1-2 failures, 60s for 3-5, 120s for 6+
)
```

**Custom generator:**
```python
def custom_break_duration(consecutive_failures: int) -> float:
    """Custom logic for break duration"""
    if consecutive_failures <= 2:
        return 10.0  # Quick retry
    elif consecutive_failures <= 5:
        return 30.0 * consecutive_failures
    else:
        return 300.0  # Max 5 minutes
        
breaker = EnhancedCircuitBreaker(
    break_duration_generator=custom_break_duration
)
```

### 7. Integration with Retry System

**Combined circuit breaker + retry:**
```python
from flashcard_pipeline.utils.retry import retry_async, RetryConfig

# Configure retry to handle circuit breaker errors
retry_config = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    jitter=True,
    retry_on=(NetworkError, TimeoutError)  # Don't retry CircuitBreakerError
)

@retry_async(retry_config)
async def protected_api_call():
    # Circuit breaker protects the actual call
    return await breaker.call(make_api_request)
```

## Common Patterns

### 1. Service Health Monitoring
```python
async def health_check():
    """Regular health check with circuit breaker stats"""
    stats = breaker.get_stats()
    
    health = {
        "service": stats["name"],
        "status": "healthy" if stats["state"] == "closed" else "degraded",
        "circuit_state": stats["state"],
        "success_rate": stats.get("success_rate", "N/A"),
        "recent_errors": stats.get("error_breakdown", {}),
    }
    
    # Alert if circuit is open for too long
    if stats["state"] == "open" and stats["time_in_state"] > 300:
        await send_alert("Circuit breaker open for >5 minutes", health)
    
    return health
```

### 2. Graceful Degradation
```python
async def get_user_data(user_id: str):
    """Get user data with fallback"""
    try:
        # Primary service with circuit breaker
        return await primary_breaker.call(
            fetch_from_primary_service,
            user_id
        )
    except CircuitBreakerError:
        # Fallback to cache or secondary service
        logger.warning(f"Primary service circuit open, using fallback")
        return await get_cached_user_data(user_id)
```

### 3. Maintenance Mode
```python
async def enter_maintenance_mode(services: List[str], duration: int):
    """Put services into maintenance mode"""
    for service in services:
        breaker = get_circuit_breaker(service)
        await breaker.manual_control.isolate(
            f"Maintenance mode - estimated {duration} minutes"
        )
    
    # Schedule automatic reset
    asyncio.create_task(reset_after_delay(services, duration * 60))
```

### 4. Cascading Failure Prevention
```python
async def handle_dependency_failure(dependency: str):
    """Prevent cascading failures when dependency fails"""
    # Check dependency health
    dep_breaker = get_circuit_breaker(dependency)
    if dep_breaker._state != CircuitState.CLOSED:
        # Proactively isolate dependent services
        for service in get_dependent_services(dependency):
            service_breaker = get_circuit_breaker(service)
            await service_breaker.manual_control.isolate(
                f"Dependency {dependency} is unavailable"
            )
```

## Testing Your Migration

### Unit Tests
```python
@pytest.mark.asyncio
async def test_circuit_breaker_with_monitoring():
    breaker = EnhancedCircuitBreaker(
        failure_threshold=0.5,
        min_throughput=2,
        break_duration=0.5,  # Short for testing
        enable_monitoring=True
    )
    
    # Cause failures
    for _ in range(2):
        with pytest.raises(ValueError):
            await breaker.call(failing_func)
    
    # Check monitoring captured state change
    stats = breaker.state_provider.stats
    assert stats["state"] == "open"
    assert stats["consecutive_failures"] == 2
```

### Integration Tests
```python
@pytest.mark.asyncio
async def test_manual_control_integration():
    breaker = EnhancedCircuitBreaker(enable_manual_control=True)
    
    # Simulate maintenance
    await breaker.manual_control.isolate("Testing")
    
    # Verify calls are rejected
    with pytest.raises(CircuitBreakerError):
        await breaker.call(api_call)
    
    # Reset and verify recovery
    await breaker.manual_control.reset()
    result = await breaker.call(api_call)
    assert result is not None
```

## Performance Considerations

1. **Sampling Window**: The enhanced breaker maintains a time-based sampling window. Adjust `sampling_duration` based on your traffic patterns.

2. **Memory Usage**: State monitoring keeps history. The default limit is 100 events, configurable via `provider._max_history`.

3. **Lock Contention**: The circuit breaker uses async locks. For very high throughput, consider sharding circuit breakers.

## Rollback Plan

If you need to rollback:

1. Keep the old circuit breaker as `circuit_breaker_legacy.py`
2. Use feature flags:

```python
if os.getenv("USE_ENHANCED_CIRCUIT_BREAKER", "true").lower() == "true":
    from flashcard_pipeline.circuit_breaker_v2 import EnhancedCircuitBreaker as CircuitBreaker
else:
    from flashcard_pipeline.circuit_breaker import CircuitBreaker
```

## Migration Checklist

- [ ] Update all circuit breaker imports
- [ ] Convert failure thresholds from counts to ratios
- [ ] Add min_throughput and sampling_duration parameters
- [ ] Enable monitoring for production services
- [ ] Enable manual control for critical services
- [ ] Choose appropriate break duration strategy
- [ ] Update health check endpoints to use stats
- [ ] Add monitoring dashboards for circuit state
- [ ] Test manual isolation procedures
- [ ] Document operational procedures

## Next Steps

1. Start with non-critical services
2. Monitor the new metrics for a week
3. Adjust thresholds based on observed patterns
4. Roll out to critical services
5. Implement alerting based on circuit breaker states

For examples, see [circuit_breaker_retry_integration.py](../examples/circuit_breaker_retry_integration.py).