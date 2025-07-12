# Monitoring Module

System health monitoring and performance tracking for the flashcard pipeline.

## Overview

This module provides comprehensive monitoring capabilities including health checks, performance metrics, error tracking, and system diagnostics. It ensures the pipeline operates reliably and helps identify issues before they impact users.

## Components

### Core Monitoring
- **`__init__.py`** - Module initialization and exports
- **`health_checker.py`** - System health verification
- **`metrics_collector.py`** - Performance metrics gathering
- **`alert_manager.py`** - Alert generation and routing
- **`dashboard.py`** - Real-time monitoring dashboard

### Specialized Monitors
- **`api_monitor.py`** - API availability and response times
- **`database_monitor.py`** - Database performance and connections
- **`cache_monitor.py`** - Cache hit rates and efficiency
- **`pipeline_monitor.py`** - End-to-end pipeline metrics

## Health Checks

The system performs regular health checks:

```python
from flashcard_pipeline.monitoring import HealthChecker

checker = HealthChecker()
status = await checker.check_all()

# Returns:
{
    "status": "healthy",  # healthy, degraded, unhealthy
    "timestamp": "2024-01-09T10:30:00Z",
    "checks": {
        "database": {"status": "healthy", "latency_ms": 5},
        "api": {"status": "healthy", "latency_ms": 250},
        "cache": {"status": "healthy", "hit_rate": 0.85},
        "disk": {"status": "healthy", "free_percent": 45}
    }
}
```

## Metrics Collection

### System Metrics
- CPU usage and load average
- Memory utilization
- Disk space and I/O
- Network latency

### Application Metrics
- API calls per minute
- Average response time
- Error rates by type
- Queue depths
- Cache performance

### Business Metrics
- Flashcards generated per hour
- User sessions active
- Import success rate
- Export completion time

## Usage Examples

```python
# Basic health check
from flashcard_pipeline.monitoring import health_check

@app.route("/health")
async def health():
    return await health_check()

# Metrics collection
from flashcard_pipeline.monitoring import MetricsCollector

collector = MetricsCollector()
collector.record_api_call(
    endpoint="generate_flashcard",
    duration_ms=320,
    status_code=200
)

# Alert configuration
from flashcard_pipeline.monitoring import AlertManager

alerts = AlertManager()
alerts.configure_alert(
    name="high_error_rate",
    condition=lambda metrics: metrics.error_rate > 0.05,
    action="email",
    recipients=["admin@example.com"]
)

# Dashboard
from flashcard_pipeline.monitoring import start_dashboard

# Starts web dashboard on http://localhost:8080
await start_dashboard(port=8080)
```

## Alert Conditions

Pre-configured alerts:
- API response time > 2 seconds
- Error rate > 5%
- Database connections exhausted
- Disk space < 10%
- Memory usage > 90%
- Cache hit rate < 50%

## Monitoring Dashboard

Web-based dashboard features:
- Real-time metrics graphs
- System health overview
- Recent errors log
- Performance trends
- Alert history

## Integration

### Prometheus Export
```python
from flashcard_pipeline.monitoring import PrometheusExporter

exporter = PrometheusExporter()
# Exposes metrics at /metrics endpoint
```

### Logging Integration
```python
from flashcard_pipeline.monitoring import StructuredLogger

logger = StructuredLogger()
logger.info("flashcard_generated", {
    "vocab_id": 123,
    "duration_ms": 450,
    "model": "claude-3-sonnet"
})
```

## Configuration

```yaml
monitoring:
  health_check:
    interval_seconds: 60
    timeout_seconds: 10
  
  metrics:
    retention_days: 30
    aggregation_interval: 300
  
  alerts:
    email:
      smtp_host: smtp.gmail.com
      from_address: alerts@system.com
    
    slack:
      webhook_url: https://hooks.slack.com/...
```

## Best Practices

1. **Don't Over-Monitor** - Focus on actionable metrics
2. **Set Reasonable Thresholds** - Avoid alert fatigue
3. **Use Structured Logging** - Makes analysis easier
4. **Monitor User Experience** - Not just system metrics
5. **Regular Reviews** - Adjust thresholds based on trends