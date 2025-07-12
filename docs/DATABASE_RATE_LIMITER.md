# Database Rate Limiter Documentation

## Overview

The `DatabaseRateLimiter` class extends the basic rate limiting functionality to provide:
- **Persistent API usage tracking** in SQLite database
- **Cost calculation** based on token usage and model pricing
- **Quota management** with daily token limits and monthly budget caps
- **Usage alerts** with configurable thresholds
- **State persistence** across application restarts
- **Comprehensive usage analytics**

## Features

### 1. Usage Tracking
- Records every API request with tokens, costs, and status
- Tracks both successful and failed requests
- Supports retry tracking for duplicate request IDs
- Calculates costs based on current OpenRouter pricing

### 2. Quota Management
- **Daily Token Quota**: Limit total tokens used per day
- **Monthly Budget**: Cap spending with USD budget limits
- Automatically enforces quotas with appropriate retry delays
- Configurable quotas that can be updated at runtime

### 3. Usage Alerts
- Default alerts at 50%, 80%, and 90% usage
- Custom alerts with callbacks for automation
- Alert spam prevention (once per day per threshold)
- Different severity levels: info, warning, critical

### 4. State Persistence
- Saves rate limiter state to database
- Restores token buckets and sliding windows on restart
- Maintains continuity across application restarts

## Usage

### Basic Setup

```python
from flashcard_pipeline.rate_limiter import DatabaseRateLimiter

# Initialize with database and quotas
limiter = DatabaseRateLimiter(
    db_path="pipeline.db",
    requests_per_minute=60,
    requests_per_hour=3000,
    burst_size=10,
    daily_token_quota=100000,      # 100k tokens per day
    monthly_budget_usd=50.00,      # $50 monthly budget
    model_name="claude-3-5-sonnet"
)
```

### Tracking API Usage

```python
# After making an API request
cost = await limiter.track_usage(
    request_id="unique-request-id",
    input_tokens=1000,
    output_tokens=500,
    endpoint="/v1/messages",
    status="success"
)
print(f"Request cost: ${cost:.4f}")
```

### Custom Alerts

```python
async def slack_notification(percent, usage, quota_type):
    """Send Slack notification when threshold reached"""
    await send_slack_message(
        f"API Usage Alert: {quota_type} at {percent:.1f}%"
    )

# Add custom alert with callback
limiter.add_alert(
    threshold_percent=75.0,
    message="75% of quota used - consider scaling",
    alert_type="warning",
    callback=slack_notification
)
```

### Viewing Statistics

```python
# Get usage statistics
stats = limiter.get_usage_stats("today")  # or "week", "month", "all"
print(f"Requests today: {stats['total_requests']}")
print(f"Tokens used: {stats['total_tokens']:,}")
print(f"Cost: ${stats['total_cost_usd']:.2f}")

# Get usage by model
model_usage = limiter.get_usage_by_model()
for model, data in model_usage.items():
    print(f"{model}: {data['request_count']} requests, ${data['total_cost']:.2f}")
```

### Updating Quotas

```python
# Update daily token limit
limiter.set_quota("daily_tokens", 200000)

# Update monthly budget
limiter.set_quota("monthly_budget", 100.00)
```

## Database Schema

### Tables

1. **api_usage_tracking**
   - Stores all API requests with token counts and costs
   - Indexed by creation date and model name

2. **api_quota_config**
   - Stores quota configurations with effective dates
   - Supports historical quota tracking

3. **rate_limiter_state**
   - Persists rate limiter state for recovery
   - Stores token counts and sliding windows

4. **usage_alerts**
   - Logs all triggered alerts
   - Useful for monitoring and auditing

### Views

1. **v_daily_usage_summary**
   - Aggregated daily usage statistics
   - Useful for dashboards and reporting

2. **v_current_quota_status**
   - Real-time quota usage and percentages
   - Shows both token and budget status

## Integration with Existing Code

The `DatabaseRateLimiter` is fully backward compatible with the base `RateLimiter` class:

```python
# Can be used as a drop-in replacement
if use_database_tracking:
    limiter = DatabaseRateLimiter(db_path="pipeline.db", **config)
else:
    limiter = RateLimiter(**config)

# Same interface for rate limiting
await limiter.acquire()
```

## Cost Calculation

Costs are calculated based on Claude 3.5 Sonnet pricing:
- **Input tokens**: $3.00 per million tokens
- **Output tokens**: $15.00 per million tokens

Example calculation:
```
1,000 input tokens = 1,000 / 1,000,000 * $3.00 = $0.003
500 output tokens = 500 / 1,000,000 * $15.00 = $0.0075
Total cost = $0.0105
```

## Best Practices

1. **Set Reasonable Quotas**
   - Start with conservative limits
   - Monitor usage patterns
   - Adjust based on actual needs

2. **Handle Quota Errors**
   ```python
   try:
       await limiter.acquire()
       # Make API request
   except RateLimitError as e:
       if "quota exceeded" in str(e):
           # Handle quota exhaustion
           logger.error(f"Quota exceeded: {e}")
   ```

3. **Monitor Alerts**
   - Set up logging for critical alerts
   - Use callbacks for automated responses
   - Review alert history regularly

4. **Regular Backups**
   - The SQLite database contains valuable usage data
   - Include in regular backup procedures
   - Consider exporting statistics periodically

## Migration

To add usage tracking to an existing database:

```bash
# Run the migration
sqlite3 pipeline.db < migrations/007_add_api_usage_tracking.sql
```

## Performance Considerations

- Database operations are lightweight and async
- Indexes optimize common queries
- State saving is periodic, not on every request
- Views pre-calculate common aggregations

## Troubleshooting

### Common Issues

1. **"Daily token quota exceeded"**
   - Check current usage: `limiter.get_usage_stats("today")`
   - Increase quota: `limiter.set_quota("daily_tokens", new_limit)`

2. **Alerts not triggering**
   - Verify alert configuration
   - Check that usage exceeds threshold
   - Ensure callbacks are async functions

3. **State not persisting**
   - Verify database write permissions
   - Check that `_save_state()` is called
   - Look for errors in logs

### Debug Queries

```sql
-- Check today's usage
SELECT * FROM v_current_quota_status;

-- View recent requests
SELECT * FROM api_usage_tracking 
ORDER BY created_at DESC LIMIT 10;

-- Check alert history
SELECT * FROM usage_alerts 
ORDER BY created_at DESC LIMIT 20;
```