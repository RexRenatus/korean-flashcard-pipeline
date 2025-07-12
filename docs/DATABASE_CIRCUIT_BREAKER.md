# Database Circuit Breaker Documentation

**Last Updated**: 2025-01-09

## Overview

The DatabaseCircuitBreaker extends the basic circuit breaker pattern with persistent state storage, intelligent pattern analysis, and proactive alerting. It provides:

- **Persistent State**: Circuit state survives process restarts
- **Pattern Detection**: Identifies failure patterns (burst, steady, intermittent, escalating)
- **Intelligent Recommendations**: Suggests optimal thresholds based on historical data
- **Alert System**: Generates alerts for circuit state changes and anomalies
- **Multi-Service Support**: Manage circuit breakers for multiple services

## Key Features

### 1. Database Persistence

All circuit breaker states and events are stored in SQLite tables:

- `circuit_breaker_states`: Current state of each service's circuit
- `circuit_breaker_events`: History of all state changes and failures
- `circuit_breaker_failure_patterns`: Detected failure patterns
- `circuit_breaker_metrics`: Performance metrics over time
- `circuit_breaker_alerts`: Generated alerts requiring attention

### 2. Pattern Detection

The system automatically detects four types of failure patterns:

- **Burst**: Multiple failures in rapid succession (< 5 seconds apart)
- **Steady**: Consistent failure rate over time
- **Intermittent**: Sporadic failures with long gaps
- **Escalating**: Increasing failure rate over time

### 3. Intelligent Thresholds

Based on detected patterns, the system recommends optimal:
- **Failure Threshold**: Number of failures before opening circuit
- **Recovery Timeout**: Time to wait before attempting recovery

### 4. Alert System

Generates alerts for:
- Circuit opened (error severity)
- Circuit closed (info severity)
- High failure rate detected (warning severity)
- Threshold adjustment recommendations (warning severity)

## Usage

### Basic Usage

```python
from flashcard_pipeline.circuit_breaker import DatabaseCircuitBreaker

# Create a database-backed circuit breaker
breaker = DatabaseCircuitBreaker(
    db_path="pipeline.db",
    service_name="openrouter_api",
    failure_threshold=5,
    recovery_timeout=60,
    enable_alerts=True,
    alert_callback=my_alert_handler
)

# Use it to protect API calls
try:
    result = await breaker.call(api_client.generate, prompt, model)
except CircuitBreakerError:
    # Circuit is open, handle accordingly
    logger.error("Circuit breaker is open, service unavailable")
```

### Multi-Service Management

```python
from flashcard_pipeline.circuit_breaker import MultiServiceDatabaseCircuitBreaker

# Create multi-service manager
manager = MultiServiceDatabaseCircuitBreaker(
    db_path="pipeline.db",
    enable_alerts=True
)

# Get breaker for specific service
breaker = await manager.get_breaker("payment_api")
result = await breaker.call(payment_api.process, transaction)

# Or use directly
result = await manager.call("inventory_api", check_stock, item_id)

# Get services needing attention
attention_services = manager.get_services_needing_attention()
```

### Alert Handling

```python
def alert_handler(alert_data):
    """Handle circuit breaker alerts"""
    if alert_data['severity'] == 'critical':
        # Send to monitoring system
        monitoring.send_alert(alert_data)
    
    if alert_data['alert_type'] == 'threshold_recommendation':
        # Log recommendation for review
        logger.info(f"Threshold adjustment suggested: {alert_data['details']}")
```

## Database Schema

### circuit_breaker_states

| Column | Type | Description |
|--------|------|-------------|
| service_name | TEXT | Unique service identifier |
| current_state | TEXT | closed, open, or half_open |
| failure_count | INTEGER | Current failure count |
| failure_threshold | INTEGER | Threshold for opening circuit |
| recovery_timeout | INTEGER | Seconds before attempting recovery |
| last_failure_time | TIMESTAMP | Time of last failure |
| state_changed_at | TIMESTAMP | When state last changed |

### circuit_breaker_events

| Column | Type | Description |
|--------|------|-------------|
| service_name | TEXT | Service that generated event |
| event_type | TEXT | state_change, failure, success, etc. |
| from_state | TEXT | Previous state (for transitions) |
| to_state | TEXT | New state (for transitions) |
| error_type | TEXT | Exception class name |
| error_message | TEXT | Error details |
| additional_data | TEXT | JSON field for extra data |

### circuit_breaker_failure_patterns

| Column | Type | Description |
|--------|------|-------------|
| service_name | TEXT | Service with detected pattern |
| pattern_type | TEXT | burst, steady, intermittent, escalating |
| time_window_seconds | INTEGER | Analysis window size |
| failure_count | INTEGER | Failures in window |
| error_rate | REAL | Failures per second |
| suggested_threshold | INTEGER | Recommended threshold |
| suggested_timeout | INTEGER | Recommended timeout |
| confidence_score | REAL | 0.0 to 1.0 confidence |

## Monitoring and Analysis

### Get Statistics

```python
stats = breaker.get_stats()
# Returns:
# {
#     'state': 'closed',
#     'failure_count': 2,
#     'success_rate': 87.5,
#     'latest_pattern': {
#         'type': 'burst',
#         'confidence': 0.85,
#         'suggested_threshold': 3
#     },
#     'last_hour_metrics': {
#         'total_calls': 100,
#         'success_rate': 85.0,
#         'circuit_open_duration': 120
#     },
#     'unacknowledged_alerts': 2
# }
```

### Get Recommendations

```python
recommendations = breaker.get_recommendations()
# Returns:
# {
#     'has_recommendations': True,
#     'message': 'Based on 5 recent patterns, consider adjusting threshold to 3 and timeout to 90 seconds',
#     'current_threshold': 5,
#     'recommended_threshold': 3,
#     'current_timeout': 60,
#     'recommended_timeout': 90,
#     'confidence': 0.82,
#     'primary_pattern': 'burst'
# }
```

### Query Alerts

```python
# Direct SQL query for unacknowledged alerts
cursor.execute("""
    SELECT * FROM circuit_breaker_alerts
    WHERE service_name = ? AND acknowledged = FALSE
    ORDER BY created_at DESC
""", (service_name,))
```

## Migration

To add circuit breaker tables to existing database:

```bash
# Run the migration
sqlite3 pipeline.db < migrations/008_add_circuit_breaker_tracking.sql

# Or use the migration runner
python scripts/run_migrations.py
```

## Best Practices

1. **Set Appropriate Thresholds**: Start with conservative values (5 failures, 60s timeout) and adjust based on recommendations

2. **Monitor Alerts**: Regularly review unacknowledged alerts and pattern recommendations

3. **Use Alert Callbacks**: Integrate with your monitoring system for real-time notifications

4. **Regular Analysis**: Periodically review failure patterns to optimize thresholds

5. **Service Isolation**: Use separate circuit breakers for different services/endpoints

6. **Backup Strategies**: Have fallback mechanisms when circuits open (cached data, degraded functionality)

## Example Scenarios

### Handling API Rate Limits

```python
breaker = DatabaseCircuitBreaker(
    service_name="api_rate_limited",
    failure_threshold=3,  # Open quickly on rate limit errors
    recovery_timeout=300,  # Wait 5 minutes before retry
    expected_exception=RateLimitError
)
```

### Protecting Database Queries

```python
breaker = DatabaseCircuitBreaker(
    service_name="db_heavy_query",
    failure_threshold=10,  # Allow more failures for transient issues
    recovery_timeout=30,   # Quick recovery for database
    expected_exception=(OperationalError, TimeoutError)
)
```

### Multi-Region Failover

```python
manager = MultiServiceDatabaseCircuitBreaker()

regions = ['us-east', 'us-west', 'eu-central']
for region in regions:
    try:
        breaker = await manager.get_breaker(f"api_{region}")
        result = await breaker.call(api_call, region)
        break  # Success, exit loop
    except CircuitBreakerError:
        continue  # Try next region
```

## Troubleshooting

### Circuit Stuck Open

1. Check recent failure patterns
2. Review recommended thresholds
3. Manually reset if needed: `await breaker.reset()`

### High Alert Volume

1. Adjust alert thresholds
2. Implement alert aggregation
3. Review and acknowledge processed alerts

### Pattern Detection Issues

1. Ensure sufficient data (min 5 events)
2. Check time window settings
3. Verify event recording is working

## Future Enhancements

- Integration with distributed tracing
- Machine learning for pattern prediction
- Automatic threshold adjustment
- Dashboard for visualization
- Webhook support for alerts