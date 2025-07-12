# OpenTelemetry Migration Guide

This guide helps you migrate the Flashcard Pipeline from existing monitoring to OpenTelemetry.

## Overview

OpenTelemetry provides a unified approach to observability with:
- **Distributed Tracing**: Track requests across all components
- **Metrics**: Collect performance and business metrics
- **Logs**: Correlate logs with traces
- **Vendor Agnostic**: Works with any observability backend

## Migration Benefits

### Before (Current State)
- Manual logging for debugging
- Basic timing measurements
- No distributed tracing
- Limited metrics collection
- No correlation between components

### After (With OpenTelemetry)
- Automatic distributed tracing
- Rich metrics with labels
- Log-trace correlation
- Performance insights
- Error tracking with context
- SLA monitoring

## Migration Steps

### Step 1: Install Dependencies

```bash
pip install opentelemetry-api
pip install opentelemetry-sdk
pip install opentelemetry-instrumentation
pip install opentelemetry-exporter-otlp
pip install opentelemetry-exporter-jaeger
pip install opentelemetry-exporter-prometheus
```

Or add to `requirements.txt`:
```txt
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-instrumentation>=0.41b0
opentelemetry-exporter-otlp>=1.20.0
opentelemetry-exporter-jaeger>=1.20.0
opentelemetry-exporter-prometheus>=0.41b0
```

### Step 2: Initialize Telemetry

Replace existing initialization with:

```python
from flashcard_pipeline.telemetry import init_telemetry

# For development
init_telemetry(
    service_name="flashcard-pipeline",
    service_version="1.0.0",
    environment="development",
    enable_console_export=True  # For debugging
)

# For production
init_telemetry(
    service_name="flashcard-pipeline",
    service_version="1.0.0",
    environment="production",
    custom_resource_attributes={
        "deployment.region": "us-east-1",
        "team": "language-learning"
    }
)
```

### Step 3: Configure Exporters

#### Development Setup

```python
from flashcard_pipeline.telemetry.exporters import (
    ExporterConfig,
    ExporterType,
    configure_exporters
)

# Jaeger for traces (local development)
configs = [
    ExporterConfig(
        exporter_type=ExporterType.JAEGER,
        endpoint="localhost:6831"
    ),
    ExporterConfig(
        exporter_type=ExporterType.CONSOLE  # For debugging
    )
]
```

Run Jaeger locally:
```bash
docker run -d --name jaeger \
  -p 6831:6831/udp \
  -p 16686:16686 \
  jaegertracing/all-in-one:latest
```

#### Production Setup

```python
# OTLP for production (works with many backends)
configs = [
    ExporterConfig(
        exporter_type=ExporterType.OTLP,
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
        headers={"api-key": os.getenv("OTEL_API_KEY")},
        insecure=False
    ),
    ExporterConfig(
        exporter_type=ExporterType.PROMETHEUS,
        prometheus_port=9090
    )
]
```

### Step 4: Replace Components

#### Database Manager

Before:
```python
from flashcard_pipeline.database.database_manager_v2 import DatabaseManager

db = DatabaseManager("flashcards.db")
```

After:
```python
from flashcard_pipeline.database.database_manager_instrumented import (
    create_instrumented_database_manager
)

db = create_instrumented_database_manager("flashcards.db")
```

#### Cache Manager

Before:
```python
from flashcard_pipeline.cache.cache_manager_v2 import CacheManager

cache = CacheManager()
```

After:
```python
from flashcard_pipeline.cache.cache_manager_instrumented import (
    create_instrumented_cache_manager
)

cache = create_instrumented_cache_manager()
```

#### API Client

Before:
```python
from flashcard_pipeline.api_client import OpenRouterClient

client = OpenRouterClient(api_key)
```

After:
```python
from flashcard_pipeline.api_client_instrumented import (
    create_instrumented_api_client
)

client = create_instrumented_api_client(api_key)
```

### Step 5: Update Custom Code

#### Add Manual Instrumentation

For custom business logic:

```python
from flashcard_pipeline.telemetry import create_span, record_metric

# Before
def process_flashcard(word):
    start = time.time()
    result = expensive_operation(word)
    duration = time.time() - start
    logger.info(f"Processed {word} in {duration}s")
    return result

# After
def process_flashcard(word):
    with create_span(
        "flashcard.process",
        attributes={"word": word}
    ) as span:
        result = expensive_operation(word)
        
        # Record business metrics
        record_metric(
            "flashcard.processed",
            1,
            metric_type="counter",
            attributes={"difficulty": result.difficulty}
        )
        
        return result
```

#### Add Context Propagation

For async operations:

```python
from flashcard_pipeline.telemetry.context import propagate_context_async

# Ensure context is propagated across async boundaries
@propagate_context_async
async def background_task(word):
    # Trace context is automatically preserved
    await process_word(word)
```

### Step 6: Correlate Logs

Update logging configuration:

```python
import logging
from flashcard_pipeline.telemetry import get_trace_id, get_span_id

class TraceFormatter(logging.Formatter):
    def format(self, record):
        # Add trace context to logs
        record.trace_id = get_trace_id() or "no-trace"
        record.span_id = get_span_id() or "no-span"
        return super().format(record)

# Configure logging
formatter = TraceFormatter(
    '%(asctime)s - %(name)s - %(levelname)s - '
    '[trace_id=%(trace_id)s span_id=%(span_id)s] - %(message)s'
)
```

### Step 7: Add Business Metrics

Define custom metrics for your use case:

```python
from flashcard_pipeline.telemetry import record_metric

class FlashcardMetrics:
    @staticmethod
    def record_processing_time(stage: str, duration_ms: float):
        record_metric(
            "flashcard.processing_time",
            duration_ms,
            metric_type="histogram",
            attributes={"stage": stage},
            unit="ms"
        )
    
    @staticmethod
    def record_api_usage(model: str, tokens: int):
        record_metric(
            "flashcard.api_tokens",
            tokens,
            metric_type="counter",
            attributes={"model": model}
        )
    
    @staticmethod
    def record_cache_efficiency(hit_rate: float):
        record_metric(
            "flashcard.cache_hit_rate",
            hit_rate,
            metric_type="gauge"
        )
```

## Migration Checklist

- [ ] Install OpenTelemetry dependencies
- [ ] Initialize telemetry at application startup
- [ ] Configure exporters for your environment
- [ ] Replace database manager with instrumented version
- [ ] Replace cache manager with instrumented version
- [ ] Replace API client with instrumented version
- [ ] Add manual instrumentation to custom code
- [ ] Update logging to include trace context
- [ ] Define and record business metrics
- [ ] Test in development with Jaeger
- [ ] Configure production exporters
- [ ] Set up dashboards and alerts

## Environment Variables

Configure these environment variables:

```bash
# Service identification
OTEL_SERVICE_NAME=flashcard-pipeline
OTEL_SERVICE_VERSION=1.0.0

# OTLP exporter (production)
OTEL_EXPORTER_OTLP_ENDPOINT=https://your-collector.com:4317
OTEL_EXPORTER_OTLP_HEADERS=api-key=your-key

# Jaeger exporter (development)
JAEGER_AGENT_HOST=localhost
JAEGER_AGENT_PORT=6831

# Sampling (optional)
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1  # Sample 10% of traces
```

## Gradual Migration

You can migrate gradually:

1. **Phase 1**: Add telemetry initialization alongside existing monitoring
2. **Phase 2**: Instrument one component at a time
3. **Phase 3**: Add custom instrumentation
4. **Phase 4**: Correlate logs with traces
5. **Phase 5**: Remove old monitoring code

## Testing the Migration

### Verify Traces

1. Start Jaeger:
   ```bash
   docker run -p 16686:16686 -p 6831:6831/udp jaegertracing/all-in-one
   ```

2. Run your application

3. View traces at http://localhost:16686

### Verify Metrics

1. Start Prometheus:
   ```bash
   docker run -p 9090:9090 prom/prometheus
   ```

2. Check metrics endpoint: http://localhost:9090/metrics

### Performance Impact

Expected overhead:
- CPU: < 1% for typical workloads
- Memory: ~10-20MB for SDK and exporters
- Latency: < 1ms per span creation

## Troubleshooting

### No Traces Appearing

1. Check telemetry initialization
2. Verify exporter configuration
3. Check network connectivity to collectors
4. Enable debug logging:
   ```python
   logging.getLogger("opentelemetry").setLevel(logging.DEBUG)
   ```

### High Memory Usage

1. Reduce batch size in exporter config
2. Implement sampling for high-volume endpoints
3. Limit span attributes and events

### Missing Correlations

1. Ensure context propagation in async code
2. Check that all components use the same trace
3. Verify baggage propagation settings

## Next Steps

After migration:

1. **Set up dashboards** in your observability platform
2. **Create alerts** based on metrics and error rates
3. **Implement SLOs** using the collected data
4. **Optimize performance** using trace insights
5. **Share runbooks** with trace deep-links

## Resources

- [OpenTelemetry Python Documentation](https://opentelemetry.io/docs/instrumentation/python/)
- [Jaeger UI Guide](https://www.jaegertracing.io/docs/latest/frontend-ui/)
- [Prometheus Query Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)
- [OTLP Specification](https://opentelemetry.io/docs/reference/specification/protocol/otlp/)