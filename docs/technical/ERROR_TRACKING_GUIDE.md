# Enhanced Error Tracking Guide

This guide explains how to use the enhanced error tracking system in the Flashcard Pipeline.

## Overview

The error tracking system provides:
- **Structured Errors**: Rich metadata and context for every error
- **Automatic Recovery**: Retry, fallback, and circuit breaker strategies
- **Error Analytics**: Trends, impact analysis, and reporting
- **OpenTelemetry Integration**: Full observability with distributed tracing

## Error Categories

### 1. Transient Errors (Recoverable)
Temporary failures that can be retried:
- `NetworkError`: Connection issues, timeouts
- `RateLimitError`: API rate limits
- `TimeoutError`: Operation timeouts
- `TemporaryUnavailableError`: Service temporarily down

### 2. Permanent Errors (Non-recoverable)
Failures that won't be fixed by retry:
- `ValidationError`: Invalid input data
- `AuthenticationError`: Auth failures
- `AuthorizationError`: Permission denied
- `NotFoundError`: Resource not found
- `ConflictError`: Resource conflicts

### 3. System Errors
Infrastructure and system-level issues:
- `DatabaseError`: Database failures
- `CacheError`: Cache service issues
- `ResourceExhaustedError`: Out of memory/disk
- `ConfigurationError`: Config problems

### 4. Business Errors
Domain-specific errors:
- `QuotaExceededError`: User limits reached
- `InvalidInputError`: Business rule violations
- `ProcessingError`: Pipeline failures

### 5. Degraded Errors
Partial failures with fallback:
- `FallbackUsedError`: Fallback service used
- `PartialSuccessError`: Some items failed

## Basic Usage

### Creating Structured Errors

```python
from flashcard_pipeline.errors import NetworkError, ValidationError

# Network error with context
raise NetworkError(
    "Failed to connect to API",
    status_code=503,
    url="https://api.example.com/translate"
)

# Validation error with field info
raise ValidationError(
    "Invalid email format",
    field="email",
    value=user_input,
    constraints={"format": "email", "required": True}
)

# Add context to any error
error = ProcessingError("Translation failed")
error.with_context(
    word="안녕하세요",
    stage="stage1",
    attempt=3
).with_user_context(
    user_id="user123",
    session_id="session456"
).with_tags("critical", "api_failure")
```

### Error Decorators

Automatically wrap exceptions in structured errors:

```python
from flashcard_pipeline.errors import with_error_handling, async_with_error_handling

@with_error_handling(
    category=ErrorCategory.BUSINESS,
    severity=ErrorSeverity.HIGH,
    recoverable=True
)
def process_flashcard(word: str) -> dict:
    # Any exception will be wrapped in FlashcardError
    validate_word(word)
    return translate_word(word)

@async_with_error_handling(
    category=ErrorCategory.SYSTEM,
    severity=ErrorSeverity.CRITICAL
)
async def fetch_from_database(query: str):
    # Async version for coroutines
    return await db.execute(query)
```

## Automatic Recovery

### Retry Strategy

Automatically retry transient errors:

```python
from flashcard_pipeline.errors import recover_with_retry, RetryPolicy

# Simple retry with defaults
result = await recover_with_retry(
    flaky_api_call,
    "parameter1", "parameter2"
)

# Custom retry policy
policy = RetryPolicy(
    max_attempts=5,
    initial_delay=0.5,      # Start with 0.5s delay
    max_delay=30.0,         # Cap at 30s
    exponential_base=2.0,   # Double each time
    jitter=True,            # Add randomness
    retry_on=[NetworkError, TimeoutError],
    retry_on_status_codes=[429, 502, 503, 504]
)

result = await recover_with_retry(
    api_call,
    retry_policy=policy
)
```

### Fallback Strategy

Use fallback values or services:

```python
from flashcard_pipeline.errors import recover_with_fallback

# Static fallback
result = await recover_with_fallback(
    unreliable_service,
    fallback_value={"status": "degraded", "data": "cached"}
)

# Dynamic fallback
result = await recover_with_fallback(
    primary_translation_api,
    fallback_function=lambda: basic_dictionary_lookup()
)

# Cache fallback
result = await recover_with_fallback(
    fetch_fresh_data,
    fallback_function=lambda: cache.get("stale_data")
)
```

### Recovery Manager

Automatic strategy selection based on error type:

```python
from flashcard_pipeline.errors import get_recovery_manager

recovery_manager = get_recovery_manager()

try:
    result = await recovery_manager.recover(
        error,
        function=failed_function,
        args=(arg1, arg2),
        context={
            "cache": cache_instance,
            "cache_key": "result_key"
        }
    )
except Exception as e:
    # Recovery failed
    logger.error(f"Unrecoverable error: {e}")
```

## Error Collection

### Initialize Collector

```python
from flashcard_pipeline.errors import initialize_error_collector

# With database persistence
collector = initialize_error_collector(
    database=db_manager,
    max_buffer_size=10000,
    flush_interval=60.0,  # Flush every minute
    enable_persistence=True
)

await collector.start()

# Without persistence (in-memory only)
collector = initialize_error_collector(
    enable_persistence=False
)
```

### Manual Collection

Errors are automatically collected when raised, but you can manually collect:

```python
from flashcard_pipeline.errors import get_error_collector

collector = get_error_collector()

try:
    risky_operation()
except Exception as e:
    # Manually collect without re-raising
    record = collector.collect(e)
    logger.warning(f"Collected error: {record.error_id}")
```

### Error Handlers

Add callbacks for error events:

```python
def critical_error_handler(record: ErrorRecord):
    if record.metadata.severity == ErrorSeverity.CRITICAL:
        # Send alert
        alert_service.send_critical_error(record)

collector.add_handler(critical_error_handler)
```

## Error Analytics

### Get Metrics

```python
from flashcard_pipeline.errors import ErrorAnalytics

analytics = ErrorAnalytics(collector, database)

# Get metrics for last hour
metrics = await analytics.get_error_metrics(
    time_window=timedelta(hours=1),
    category_filter=ErrorCategory.TRANSIENT,
    severity_filter=ErrorSeverity.HIGH
)

print(f"Total errors: {metrics.total_errors}")
print(f"Error rate: {metrics.error_rate:.2f} per minute")
print(f"Affected users: {metrics.affected_users}")
```

### Analyze Trends

```python
# Get hourly trends for last 24 hours
trends = await analytics.get_error_trends(
    time_window=timedelta(hours=24),
    granularity="hour"  # or "day"
)

for trend in trends:
    print(f"{trend.timestamp}: {trend.count} errors")
```

### Impact Analysis

```python
# Get top impact errors
impacts = await analytics.get_error_impact_analysis(
    limit=10,
    time_window=timedelta(hours=6)
)

for impact in impacts:
    print(f"Error: {impact.error_fingerprint[:8]}...")
    print(f"  Occurrences: {impact.total_occurrences}")
    print(f"  Affected users: {impact.affected_users}")
    print(f"  Impact score: {impact.estimated_impact_score:.2f}")
```

### Generate Reports

```python
# Generate comprehensive error report
report = await analytics.generate_error_report(
    time_window=timedelta(hours=24)
)

print(f"Report generated at: {report['generated_at']}")
print(f"Summary: {report['summary']}")
print(f"Top errors: {report['top_impact_errors']}")

if report.get('alerts'):
    for alert in report['alerts']:
        print(f"ALERT: {alert['level']} - {alert['message']}")
```

## Integration Examples

### With Circuit Breaker

```python
from flashcard_pipeline.circuit_breaker_v2 import EnhancedCircuitBreaker

circuit_breaker = EnhancedCircuitBreaker(
    name="translation_api",
    failure_threshold=5,
    recovery_timeout=30.0,
    expected_exception_types=[NetworkError, TimeoutError]
)

@with_error_handling(category=ErrorCategory.TRANSIENT)
async def call_translation_api(word: str):
    return await circuit_breaker.call_async(
        api_client.translate,
        word
    )
```

### With OpenTelemetry

Errors are automatically traced:

```python
from flashcard_pipeline.telemetry import create_span

with create_span("process_batch") as span:
    try:
        process_flashcards(batch)
    except FlashcardError as e:
        # Error automatically recorded in span
        # Includes error ID, fingerprint, and metadata
        span.set_attribute("batch.failed", True)
        raise
```

### With Rate Limiter

```python
from flashcard_pipeline.rate_limiter_v2 import ShardedRateLimiter

rate_limiter = ShardedRateLimiter(
    capacity=100,
    refill_rate=10,
    shards=16
)

async def rate_limited_api_call(word: str):
    result = await rate_limiter.acquire("api_calls")
    
    if not result.allowed:
        raise RateLimitError(
            "API rate limit exceeded",
            retry_after=result.retry_after,
            limit=rate_limiter.capacity
        )
    
    return await api_client.call(word)
```

## Best Practices

### 1. Use Specific Error Types
```python
# Good: Specific error with context
raise ValidationError(
    "Email format invalid",
    field="email",
    value=email
)

# Bad: Generic error
raise Exception("Invalid email")
```

### 2. Add Context Early
```python
try:
    result = await process_word(word)
except Exception as e:
    # Convert and add context
    raise ProcessingError(
        f"Failed to process word: {word}",
        cause=e
    ).with_context(
        stage="translation",
        model="claude-3-haiku",
        word_length=len(word)
    )
```

### 3. Use Recovery Strategies
```python
# Define recovery for different scenarios
async def robust_api_call(params):
    # Try primary with retry
    try:
        return await recover_with_retry(
            primary_api.call,
            params,
            retry_policy=RetryPolicy(max_attempts=3)
        )
    except NetworkError:
        # Fallback to secondary
        return await recover_with_fallback(
            secondary_api.call,
            params,
            fallback_value=get_cached_result(params)
        )
```

### 4. Monitor Error Patterns
```python
# Regular error analysis
async def monitor_errors():
    analytics = ErrorAnalytics(collector, db)
    
    # Check every hour
    while True:
        metrics = await analytics.get_error_metrics(timedelta(hours=1))
        
        if metrics.critical_error_rate > 0.1:
            await alert_team("High critical error rate")
        
        if metrics.error_rate > 10:
            await scale_up_resources()
        
        await asyncio.sleep(3600)  # 1 hour
```

### 5. Test Error Scenarios
```python
@pytest.mark.asyncio
async def test_api_error_handling():
    # Mock API to fail
    api_client.translate = AsyncMock(
        side_effect=NetworkError("Connection timeout")
    )
    
    # Should use fallback
    result = await translate_with_fallback("test")
    assert result.get("degraded") is True
    
    # Verify error was collected
    collector = get_error_collector()
    stats = collector.get_statistics()
    assert stats["errors_by_category"]["transient"] > 0
```

## Configuration

### Environment Variables
```bash
# Error tracking
ERROR_FLUSH_INTERVAL=60          # Seconds between flushes
ERROR_BUFFER_SIZE=10000          # Max errors in memory
ERROR_PERSISTENCE_ENABLED=true   # Save to database

# Recovery policies
RETRY_MAX_ATTEMPTS=3
RETRY_INITIAL_DELAY=1.0
RETRY_MAX_DELAY=60.0
RETRY_JITTER=true

# Analytics
ERROR_REPORT_INTERVAL=3600       # Generate reports hourly
ERROR_ALERT_THRESHOLD=0.1        # Alert on >0.1 critical/min
```

### Programmatic Configuration
```python
# Configure recovery strategies
recovery_manager = get_recovery_manager()

# Change strategy for category
recovery_manager.set_strategy(
    ErrorCategory.SYSTEM,
    RecoveryStrategy.FALLBACK  # Use fallback instead of circuit breaker
)

# Custom retry policy for specific errors
custom_retry = RetryPolicy(
    max_attempts=10,
    initial_delay=0.1,
    retry_on=[TemporaryUnavailableError]
)

recovery_manager.handlers[RecoveryStrategy.RETRY] = RetryHandler(custom_retry)
```

## Troubleshooting

### Errors Not Being Collected
1. Ensure collector is initialized and started
2. Check that errors inherit from FlashcardError
3. Verify telemetry is initialized

### Recovery Not Working
1. Check error category and recoverability
2. Verify recovery strategy is configured
3. Check retry policy conditions

### High Memory Usage
1. Reduce buffer size
2. Decrease flush interval
3. Enable database persistence

### Missing Error Context
1. Use error decorators
2. Add context with `.with_context()`
3. Ensure trace propagation