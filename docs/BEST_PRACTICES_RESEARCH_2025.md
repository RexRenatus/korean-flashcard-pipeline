# Best Practices Research for Flashcard Pipeline Modules (2025)

Generated on: 2025-01-11
Research conducted using .ref search for current best practices

## Table of Contents

1. [API & Network Communication](#api--network-communication)
2. [Circuit Breaker Pattern](#circuit-breaker-pattern)
3. [Rate Limiting](#rate-limiting)
4. [Database & Connection Pooling](#database--connection-pooling)
5. [Error Handling & Logging](#error-handling--logging)
6. [Monitoring & Observability](#monitoring--observability)
7. [CLI Design](#cli-design)
8. [Concurrency & Async Programming](#concurrency--async-programming)
9. [Recommendations by Module](#recommendations-by-module)

## API & Network Communication

### Key Best Practices (2025)

1. **Retry Logic with Exponential Backoff**
   - Use `RetryConfig` with configurable backoff strategies
   - Implement jitter to avoid thundering herd
   - Set reasonable retry limits (3-5 attempts typical)

2. **Error Handling**
   - Use typed exceptions (e.g., `HTTPValidationError`, `SDKError`)
   - Implement proper error context with status codes and raw responses
   - Handle specific error types before generic ones

3. **Timeout Configuration**
   - Always set request timeouts
   - Use different timeouts for connection vs read operations
   - Consider circuit breaker integration for timeout scenarios

### Implementation Example
```python
from mistralai import Mistral
from mistralai.utils import BackoffStrategy, RetryConfig

retry_config = RetryConfig(
    "backoff", 
    BackoffStrategy(
        initial_interval=1,
        max_interval=50,
        exponent=1.1,
        max_elapsed_time=100
    ),
    False
)
```

## Circuit Breaker Pattern

### Key Best Practices (2025)

1. **State Management**
   - Closed → Open → Half-Open → Closed cycle
   - Use failure ratio (e.g., 50%) with minimum throughput
   - Implement proper break duration (5-30 seconds typical)

2. **Configuration Guidelines**
   - `FailureRatio`: 0.1-0.5 (10-50% failure rate)
   - `MinimumThroughput`: 10-100 requests
   - `SamplingDuration`: 10-30 seconds
   - `BreakDuration`: 5-30 seconds (or use dynamic generator)

3. **Advanced Features**
   - Use `StateProvider` for monitoring circuit state
   - Implement `ManualControl` for emergency isolation
   - Consider `BreakDurationGenerator` for dynamic recovery

### Anti-Patterns to Avoid
- Don't use state provider to branch retry logic
- Don't create circuit breaker per endpoint (use sharding instead)
- Don't suppress exceptions to avoid breaking the circuit

## Rate Limiting

### Key Best Practices (2025)

1. **Algorithm Selection**
   - **Token Bucket**: Best for allowing bursts (recommended)
   - **Fixed Window**: Simple but prone to boundary issues
   - **Sliding Window**: More accurate but memory intensive

2. **Sharding for Scale**
   - Use power-of-two selection for shard distribution
   - Aim for 10+ capacity per shard
   - Formula: `shards = max_qps / 2`

3. **Implementation Tips**
   - Reserve capacity for fairness
   - Add jitter to retry times
   - Implement proper error responses with retry-after headers

## Database & Connection Pooling

### SQLAlchemy Best Practices (2025)

1. **Pool Configuration**
   - `QueuePool` is default and recommended
   - Key parameters: `pool_size=5`, `max_overflow=10`
   - Use `pool_recycle` for stale connections
   - Set `pool_timeout` to avoid indefinite waits

2. **SQLite Specific**
   - File DBs now use `QueuePool` by default (change in v2.0)
   - Memory DBs use `SingletonThreadPool`
   - Set `check_same_thread=False` for file DBs

3. **Connection Management**
   - Never rely on garbage collection for cleanup
   - Use `engine.dispose()` when needed
   - Implement proper error handling for connection failures

### Common Issues & Solutions
- **"QueuePool limit reached"**: Increase pool size or fix connection leaks
- **Threading issues**: Use appropriate pool class for your use case
- **Async compatibility**: Use `AsyncAdaptedQueuePool` for asyncio

## Error Handling & Logging

### Structured Error Handling (2025)

1. **Exception Hierarchy**
   - Create domain-specific exceptions
   - Use exception chaining for context
   - Include actionable information

2. **Logging Best Practices**
   - Use structured logging (JSON format)
   - Include trace IDs for correlation
   - Log at appropriate levels (ERROR for exceptions only)
   - Use `logging.exception()` in exception handlers

3. **Google Cloud Logging Structure**
   ```json
   {
     "severity": "ERROR",
     "message": "Error description",
     "httpRequest": {...},
     "sourceLocation": {...},
     "trace": "projects/[PROJECT-ID]/traces/[TRACE-ID]"
   }
   ```

## Monitoring & Observability

### OpenTelemetry Integration (2025)

1. **Instrumentation Strategy**
   - Auto-instrument where possible
   - Manual instrumentation for business metrics
   - Use semantic conventions

2. **Metrics Collection**
   - System metrics: CPU, memory, GC
   - Business metrics: Request count, latency, errors
   - Use appropriate metric types (Counter, Gauge, Histogram)

3. **Export Configuration**
   - Prefer OTLP exporters for compatibility
   - Configure batching for efficiency
   - Set up proper resource attributes

### Recommended Setup
```python
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint="localhost:4317"),
    export_interval_millis=60000
)
meter_provider = MeterProvider(metric_readers=[reader])
metrics.set_meter_provider(meter_provider)
```

## CLI Design

### Typer Best Practices (2025)

1. **Use Annotated Types**
   ```python
   from typing import Annotated
   import typer
   
   def main(name: Annotated[str, typer.Argument(help="User name")]):
       print(f"Hello {name}")
   ```

2. **Callback Validation**
   - Handle completion scenarios with `ctx.resilient_parsing`
   - Use `typer.BadParameter` for validation errors
   - Implement `is_eager` for priority parameters

3. **Help Text Guidelines**
   - Add help for all arguments and options
   - Use `rich_help_panel` for grouping
   - Show defaults with `show_default=True`

## Concurrency & Async Programming

### Best Practices (2025)

1. **Connection Pool Async Compatibility**
   - Use `AsyncAdaptedQueuePool` for async SQLAlchemy
   - Avoid mixing sync/async patterns
   - Implement proper async context managers

2. **Rate Limiting in Async**
   - Use async-safe implementations
   - Consider distributed rate limiting for scale
   - Implement proper backpressure

3. **Error Handling in Async**
   - Use `asyncio.gather` with `return_exceptions=True`
   - Implement proper cancellation handling
   - Add timeouts to all async operations

## Recommendations by Module

### api_client.py & Related
- Implement retry with exponential backoff
- Add circuit breaker integration
- Use structured error responses
- Implement request/response logging

### circuit_breaker.py
- Use failure ratio with minimum throughput
- Implement state monitoring
- Add manual control for emergencies
- Log state transitions

### rate_limiter.py
- Use token bucket algorithm
- Implement sharding for scale
- Add reservation mechanism
- Return proper retry-after headers

### database/connection_pool.py
- Configure appropriate pool sizes
- Implement connection recycling
- Add health checks
- Monitor pool metrics

### error_handler.py
- Create exception hierarchy
- Add context to exceptions
- Implement fallback chains
- Log with appropriate severity

### monitoring/
- Use OpenTelemetry standards
- Export to OTLP endpoints
- Implement custom business metrics
- Add distributed tracing

### cli/
- Use Typer with Annotated
- Implement proper validation
- Add comprehensive help
- Handle completion properly

### concurrent/
- Use appropriate async patterns
- Implement proper cancellation
- Add timeout handling
- Monitor concurrent operations

## Tooling Recommendations

1. **Testing**
   - pytest with async support
   - hypothesis for property testing
   - pytest-benchmark for performance

2. **Code Quality**
   - ruff for linting
   - mypy for type checking
   - black for formatting

3. **Monitoring**
   - OpenTelemetry Collector
   - Prometheus + Grafana
   - Distributed tracing (Jaeger/Tempo)

## Migration Considerations

When updating existing code:
1. Start with critical path components
2. Add monitoring before refactoring
3. Implement gradual rollout
4. Keep backward compatibility
5. Document breaking changes

## References

- [Mistral AI Python Client](https://github.com/mistralai/client-python)
- [Polly Circuit Breaker](https://www.pollydocs.org/strategies/circuit-breaker)
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)
- [SQLAlchemy Connection Pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html)
- [Typer Documentation](https://typer.tiangolo.com/)
- [Google Cloud Structured Logging](https://cloud.google.com/logging/docs/structured-logging)