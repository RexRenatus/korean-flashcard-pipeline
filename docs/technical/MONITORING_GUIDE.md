# Monitoring & Analytics Guide

## Overview

The flashcard pipeline includes a comprehensive monitoring and analytics system that provides:

1. **Real-time Metrics** - Live performance and usage tracking
2. **Cost Management** - Budget tracking with alerts
3. **Performance Analysis** - Latency, throughput, and success rates
4. **Anomaly Detection** - Statistical outlier identification
5. **Automated Reporting** - Scheduled reports with multiple formats

## Architecture

### Core Components

```python
from flashcard_pipeline.monitoring.metrics_collector import (
    MetricsCollector,   # Metrics collection and storage
    MetricType,         # Counter, Gauge, Histogram, Timer
    MetricCategory      # API, Processing, Cache, Database, Cost, System
)

from flashcard_pipeline.monitoring.analytics_service import (
    AnalyticsService,   # Analysis and insights
    TrendDirection      # Trend detection
)

from flashcard_pipeline.monitoring.dashboard import (
    Dashboard,          # CLI dashboard interface
    DashboardView       # View types
)

from flashcard_pipeline.monitoring.reporter import (
    Reporter,           # Report generation
    ReportType,         # Report categories
    ReportFormat        # Output formats
)
```

## Metrics Collection

### Available Metrics

#### API Metrics
- `api.calls.total` - Total API calls
- `api.calls.success` - Successful calls
- `api.calls.failed` - Failed calls
- `api.latency.ms` - Response latency
- `api.tokens.used` - Tokens consumed
- `api.cost.total` - Total cost
- `api.cost.by_model.*` - Cost per model

#### Processing Metrics
- `processing.tasks.total` - Total tasks
- `processing.tasks.completed` - Completed tasks
- `processing.tasks.failed` - Failed tasks
- `processing.duration.ms` - Task duration
- `processing.throughput.per_minute` - Processing rate
- `processing.queue.size` - Queue depth

#### Cache Metrics
- `cache.hits.total` - Cache hits
- `cache.misses.total` - Cache misses
- `cache.hit_rate` - Hit rate percentage
- `cache.size.mb` - Cache size
- `cache.operations.save` - Save operations
- `cache.operations.evict` - Evictions

#### Database Metrics
- `db.queries.total` - Total queries
- `db.queries.duration.ms` - Query duration
- `db.connections.active` - Active connections
- `db.size.mb` - Database size

#### System Metrics
- `system.memory.used.mb` - Memory usage
- `system.cpu.percent` - CPU usage
- `system.uptime.hours` - System uptime

### Recording Metrics

```python
from flashcard_pipeline.monitoring.metrics_collector import MetricsCollector

# Initialize collector
collector = MetricsCollector()

# Record counter
collector.record("api.calls.total", 1, MetricCategory.API)

# Record gauge
collector.record("cache.size.mb", 150.5, MetricCategory.CACHE)

# Track API call with automatic metrics
collector.track_api_call(
    model="claude-3-sonnet",
    tokens_used=1500,
    cost=0.023,
    latency_ms=450,
    success=True
)

# Track processing task
collector.track_processing_task(
    task_type="full_pipeline",
    duration_ms=2500,
    success=True
)
```

### Using Metric Types

```python
# Counter - incremental values
api_calls = collector.get_metric("api.calls.total", MetricType.COUNTER)
api_calls.increment()
api_calls.increment(5)

# Gauge - point-in-time values
cache_size = collector.get_metric("cache.size.mb", MetricType.GAUGE)
cache_size.set(150.5)

# Histogram - distribution of values
latency = collector.get_metric("api.latency.ms", MetricType.HISTOGRAM)
latency.observe(245)
print(f"P95 latency: {latency.percentile(95)}ms")

# Timer - duration tracking
timer = collector.get_metric("processing.duration", MetricType.TIMER)
with timer:
    # Process task
    process_vocabulary_item()
```

## CLI Dashboard

### Running the Dashboard

```bash
# Start live dashboard
python scripts/monitoring_dashboard.py dashboard

# View specific dashboard
python scripts/monitoring_dashboard.py dashboard --view overview
python scripts/monitoring_dashboard.py dashboard --view processing
python scripts/monitoring_dashboard.py dashboard --view cost
python scripts/monitoring_dashboard.py dashboard --view performance
python scripts/monitoring_dashboard.py dashboard --view alerts
```

### Dashboard Views

#### Overview Dashboard
```
┌─ System Overview ────────────────────────────────┐
│ Status: ● Healthy     Uptime: 5d 14h 23m         │
│                                                   │
│ API Calls:     12,456  ↑ 15% (24h)              │
│ Success Rate:  98.5%   → stable                  │
│ Avg Latency:   245ms   ↓ 10ms                   │
│ Total Cost:    $45.23  Budget: $100/day         │
└───────────────────────────────────────────────────┘

┌─ Current Activity ───────────────────────────────┐
│ Processing: 15 tasks  Queue: 45                  │
│ Cache Hit:  78%       Size: 245MB/1GB           │
│ API Rate:   25/min    Limit: 100/min            │
└───────────────────────────────────────────────────┘
```

#### Cost Analysis View
```
┌─ Cost Breakdown ─────────────────────────────────┐
│ Today:     $12.45    ████████░░ 80% of budget   │
│ Week:      $78.90    ██████░░░░ 60% of budget   │
│ Month:     $234.56   ████░░░░░░ 40% of budget   │
│                                                   │
│ By Model:                                         │
│   claude-3-sonnet:  $180.45 (77%)               │
│   claude-3-haiku:   $54.11  (23%)               │
│                                                   │
│ Trend: ↑ 15% vs last week                       │
└───────────────────────────────────────────────────┘
```

### Dashboard Commands

```bash
# View specific metric
python scripts/monitoring_dashboard.py metric api.calls.total --hours 24

# Get metric statistics
python scripts/monitoring_dashboard.py stats --metric api.latency.ms

# Analyze trends
python scripts/monitoring_dashboard.py analyze --period 7
```

## Budget Management

### Setting Budgets

```bash
# Set budget limits
python scripts/monitoring_dashboard.py budget set \
    --daily 50 \
    --weekly 300 \
    --monthly 1000

# View current budget status
python scripts/monitoring_dashboard.py budget status

# Set budget alerts
python scripts/monitoring_dashboard.py budget alert \
    --warning 80 \
    --critical 95
```

### Budget Tracking

```python
# In code
collector.set_budget(
    daily=50.0,
    weekly=300.0,
    monthly=1000.0
)

# Check budget status
status = collector.get_budget_status()
if status["daily"]["percentage"] > 80:
    logger.warning(f"Daily budget at {status['daily']['percentage']}%")
```

## Alert Configuration

### Creating Alerts

```bash
# High API latency alert
python scripts/monitoring_dashboard.py alerts add \
    --name "High Latency" \
    --metric api.latency.ms \
    --threshold 500 \
    --comparison gt \
    --severity high

# Low cache hit rate
python scripts/monitoring_dashboard.py alerts add \
    --name "Low Cache Hits" \
    --metric cache.hit_rate \
    --threshold 50 \
    --comparison lt \
    --severity medium

# Cost threshold
python scripts/monitoring_dashboard.py alerts add \
    --name "Daily Cost Limit" \
    --metric api.cost.total \
    --threshold 45 \
    --comparison gt \
    --severity critical \
    --cooldown 60
```

### Alert Actions

```python
# Configure alert actions
collector.add_alert_rule(
    name="High Error Rate",
    metric_name="processing.tasks.failed",
    threshold=10,
    comparison="gt",
    action="email",  # or "webhook", "log"
    action_config={
        "to": "admin@example.com",
        "subject": "High Error Rate Alert"
    },
    cooldown_minutes=30
)
```

## Analytics

### Trend Analysis

```python
from flashcard_pipeline.monitoring.analytics_service import AnalyticsService

analytics = AnalyticsService(collector)

# Analyze trends
trends = analytics.analyze_trends(
    metrics=["api.calls.total", "api.cost.total"],
    hours=168  # 1 week
)

for metric, trend in trends.items():
    print(f"{metric}: {trend['direction']} (slope: {trend['slope']:.2f})")
```

### Usage Patterns

```python
# Detect usage patterns
patterns = analytics.detect_usage_patterns(
    metric="api.calls.total",
    days=7
)

print(f"Peak hours: {patterns['peak_hours']}")
print(f"Low usage: {patterns['low_hours']}")
```

### Anomaly Detection

```python
# Find anomalies
anomalies = analytics.detect_anomalies(hours=24)

for anomaly in anomalies:
    print(f"Anomaly in {anomaly['metric']}: "
          f"{anomaly['value']} (expected: {anomaly['expected']}) "
          f"Severity: {anomaly['severity']}")
```

### Performance Analysis

```python
# Analyze performance
perf = analytics.analyze_performance(hours=24)

print(f"Latency P50: {perf['latency_p50']}ms")
print(f"Latency P95: {perf['latency_p95']}ms")
print(f"Latency P99: {perf['latency_p99']}ms")
print(f"Success Rate: {perf['success_rate']:.1%}")
```

## Reporting

### Report Types

#### Daily Summary
```bash
python scripts/generate_reports.py daily --format html --email admin@example.com
```

Includes:
- Key metrics summary
- Performance highlights
- Cost tracking
- Anomalies detected
- System health

#### Weekly Performance
```bash
python scripts/generate_reports.py weekly --format markdown
```

Includes:
- Trend analysis
- Performance comparisons
- Usage patterns
- Optimization recommendations

#### Monthly Cost Report
```bash
python scripts/generate_reports.py monthly --year 2025 --month 1 --format pdf
```

Includes:
- Total costs
- Cost breakdown by model
- Budget analysis
- Cost projections
- Optimization suggestions

### Custom Reports

```bash
# Custom report with specific metrics
python scripts/generate_reports.py custom \
    --name "API Performance Analysis" \
    --start 2025-01-01 \
    --end 2025-01-31 \
    --metrics api.calls.total api.latency.ms api.cost.total \
    --include-trends \
    --include-anomalies \
    --format html
```

### Report Scheduling

```bash
# Schedule daily report
python scripts/generate_reports.py schedule add \
    --name "Daily Summary" \
    --type daily_summary \
    --cron "0 8 * * *" \
    --format html \
    --email admin@example.com

# Schedule weekly report
python scripts/generate_reports.py schedule add \
    --name "Weekly Performance" \
    --type weekly_performance \
    --cron "0 9 * * 1" \
    --webhook https://example.com/reports

# List schedules
python scripts/generate_reports.py schedule list

# Remove schedule
python scripts/generate_reports.py schedule remove --id 1
```

## Data Export

### Export Metrics

```bash
# Export raw metrics data
python scripts/generate_reports.py export \
    --output ./metrics_export \
    --days 30 \
    --format csv

# Export specific metrics
python scripts/generate_reports.py export \
    --metrics api.calls.total api.cost.total \
    --start 2025-01-01 \
    --format json \
    --compress
```

## Integration

### Webhook Integration

```python
# Configure webhook for alerts
reporter.add_webhook(
    url="https://example.com/monitoring/webhook",
    events=["alert", "daily_report"],
    headers={"Authorization": "Bearer token"}
)
```

### Email Configuration

```python
# Configure email settings
reporter.configure_email(
    smtp_host="smtp.gmail.com",
    smtp_port=587,
    username="your-email@gmail.com",
    password="app-password",
    from_email="monitoring@example.com"
)
```

## Best Practices

### 1. Metric Naming
- Use hierarchical naming: `category.subcategory.metric`
- Be consistent with units: `_ms`, `_mb`, `_total`
- Use descriptive names

### 2. Alert Configuration
- Set appropriate thresholds based on baselines
- Use cooldown periods to prevent alert fatigue
- Start with fewer, high-value alerts

### 3. Performance
- Flush metrics periodically, not on every record
- Use appropriate metric types (Counter vs Gauge)
- Aggregate data for long-term storage

### 4. Cost Management
- Set realistic budgets with some buffer
- Monitor cost trends, not just totals
- Review model usage regularly

### 5. Reporting
- Schedule reports for consistent times
- Include actionable insights, not just data
- Keep reports concise and focused

## Troubleshooting

### Common Issues

1. **Missing Metrics**
   - Check metric name spelling
   - Ensure metrics are being recorded
   - Verify flush interval

2. **Alert Not Firing**
   - Check threshold values
   - Verify comparison operator
   - Check cooldown period

3. **High Memory Usage**
   - Reduce metric retention period
   - Increase flush frequency
   - Use sampling for high-volume metrics

4. **Report Generation Fails**
   - Check date ranges
   - Verify metric names exist
   - Check email/webhook configuration

### Debug Mode

```bash
# Enable debug logging
export MONITORING_DEBUG=1

# Test alert rules
python scripts/monitoring_dashboard.py alerts test --name "High Latency"

# Validate report configuration
python scripts/generate_reports.py validate --config report_config.json
```

## Performance Optimization

### Metric Collection
```python
# Batch metric updates
with collector.batch():
    for item in items:
        collector.record("metric", value)
```

### Data Retention
```python
# Configure retention
collector.set_retention(
    detailed_days=7,    # Keep detailed data for 7 days
    hourly_days=30,     # Keep hourly aggregates for 30 days
    daily_days=365      # Keep daily aggregates for 1 year
)
```

### Query Optimization
```python
# Use appropriate aggregation
data = collector.get_metric_data(
    "api.calls.total",
    hours=24,
    aggregate="sum",
    interval="hour"  # Hourly aggregation for 24h view
)
```