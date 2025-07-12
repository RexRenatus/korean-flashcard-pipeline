# Comprehensive Error Handling System Guide

## Overview

The flashcard pipeline includes a comprehensive error handling system that provides:

1. **Error Taxonomy** - Categorizes all possible errors
2. **Error Recovery** - Automatic recovery strategies for different error types
3. **Error Reporting** - Database logging with full context
4. **Error Analysis** - Pattern detection and trend analysis
5. **Auto Resolution** - Automatic fixes for known issues

## Architecture

### Core Components

```python
from flashcard_pipeline.error_handler import (
    ErrorHandler,      # Main error handler
    ErrorCategory,     # Error categorization
    ErrorSeverity,     # Severity levels
    ErrorContext,      # Full error context
    handle_errors      # Decorator for automatic handling
)
```

### Error Categories

- **NETWORK** - Connection issues, timeouts
- **API** - API errors, rate limits, authentication
- **VALIDATION** - Data validation failures
- **DATABASE** - Database operation errors
- **PARSING** - Output parsing errors
- **CACHE** - Cache operation failures
- **CIRCUIT_BREAKER** - Circuit breaker trips
- **CONFIGURATION** - Config errors
- **RESOURCE** - Memory/disk exhaustion
- **TIMEOUT** - Operation timeouts
- **UNKNOWN** - Uncategorized errors

### Error Severity Levels

1. **CRITICAL** - System failure, immediate attention
2. **HIGH** - Major functionality impaired
3. **MEDIUM** - Degraded performance
4. **LOW** - Minor issue, system continues
5. **INFO** - Informational only

## Usage

### Basic Setup

```python
from flashcard_pipeline.error_handler import ErrorHandler

# Initialize error handler with database path
error_handler = ErrorHandler("pipeline.db")
```

### Method 1: Decorator Pattern

```python
from flashcard_pipeline.error_handler import handle_errors

class FlashcardService:
    def __init__(self, error_handler):
        self.error_handler = error_handler
    
    @handle_errors("FlashcardService")
    def generate_flashcard(self, word: str):
        # Errors are automatically captured and handled
        if not word:
            raise ValidationError("Word cannot be empty")
        
        # Process flashcard...
        return flashcard
```

### Method 2: Context Manager

```python
with error_handler.error_context(
    component="DataProcessor",
    operation="validate_input",
    user_id="user123",
    vocabulary_id=456
):
    # Any exceptions here are captured with context
    validate_korean_word(word)
    process_data(word)
```

### Method 3: Manual Capture

```python
try:
    result = api_client.call_model(prompt)
except ApiError as e:
    error_context = error_handler.capture_error(
        e,
        component="APIClient",
        operation="call_model",
        request_id="req_123",
        additional_info={
            "model": "claude-3-sonnet",
            "prompt_tokens": 1500
        }
    )
    error_handler.handle_error(error_context)
    raise
```

## Recovery Strategies

The system includes several automatic recovery strategies:

### 1. Retry Strategy
- Handles: Network, API, Database errors
- Action: Exponential backoff retry
- Config: Max 3 retries, base delay 1s

### 2. Rate Limit Recovery
- Handles: Rate limit errors
- Action: Wait for specified time
- Config: Uses retry_after header

### 3. Circuit Breaker Recovery
- Handles: Circuit breaker open
- Action: Wait for circuit reset
- Config: Default 5 minute wait

### 4. Cache Failover
- Handles: Cache errors
- Action: Bypass cache, use direct calls
- Config: Automatic fallback

### 5. Database Reconnect
- Handles: Connection errors
- Action: Attempt reconnection
- Config: 2s pause before retry

## Error Analysis

### Command Line Tool

```bash
# View recent errors
python scripts/analyze_errors.py recent --hours 24

# Analyze error patterns
python scripts/analyze_errors.py analyze --hours 48

# View error clusters
python scripts/analyze_errors.py clusters

# Get specific error details
python scripts/analyze_errors.py details --error-id "APIClient_123"

# Generate comprehensive report
python scripts/analyze_errors.py report --output errors.json
```

### Programmatic Analysis

```python
# Get error analysis
analysis = error_handler.get_error_analysis(hours=24)

print(f"Total errors: {analysis['total_errors']}")
print(f"Recovery rate: {analysis['recovery_success_rate']:.1%}")
print(f"Top errors: {analysis['top_errors']}")
print(f"Recommendations: {analysis['recommendations']}")

# Get error clusters
clusters = error_handler.get_error_clusters(hours=24)
for cluster in clusters:
    print(f"Cluster: {cluster['signature']}")
    print(f"Count: {cluster['count']}")
```

## Automatic Resolution

The AutoResolver can fix known issues:

```python
# Automatic resolutions include:
- API key validation and reloading
- Cache corruption cleanup
- Database lock clearing
- Memory cleanup and optimization
```

## Database Schema

Errors are stored with full context:

```sql
CREATE TABLE error_logs (
    error_id TEXT UNIQUE,
    timestamp DATETIME,
    category TEXT,
    severity TEXT,
    error_type TEXT,
    error_message TEXT,
    stack_trace TEXT,
    component TEXT,
    operation TEXT,
    input_data TEXT,
    system_state TEXT,
    user_id TEXT,
    session_id TEXT,
    request_id TEXT,
    vocabulary_id INTEGER,
    task_id TEXT,
    retry_count INTEGER,
    recovery_attempted BOOLEAN,
    recovery_successful BOOLEAN,
    recovery_strategy TEXT,
    additional_info TEXT
);
```

## Best Practices

### 1. Always Provide Context

```python
@handle_errors("YourComponent")
def your_method(self, word_id: int, user_id: str):
    # Good: Include relevant IDs in kwargs
    with self.error_handler.error_context(
        component="YourComponent",
        operation="your_method",
        vocabulary_id=word_id,
        user_id=user_id
    ):
        # Your code here
```

### 2. Use Appropriate Error Types

```python
# Good: Use specific exception types
if not data.get('korean'):
    raise ValidationError("Korean word required", field='korean')

if response.status_code == 429:
    raise RateLimitError("Rate limited", retry_after=60)

# Bad: Generic exceptions
raise Exception("Something went wrong")
```

### 3. Include Recovery Information

```python
# Good: Include recovery hints
raise CircuitBreakerError(
    "Circuit open for OpenRouter",
    service="openrouter",
    failure_count=failures,
    threshold=threshold
)
```

### 4. Monitor Error Trends

```python
# Set up regular monitoring
async def monitor_errors():
    while True:
        analysis = error_handler.get_error_analysis(hours=1)
        
        if analysis['total_errors'] > 100:
            send_alert("High error rate detected")
        
        await asyncio.sleep(300)  # Check every 5 minutes
```

## Integration Example

```python
class EnhancedAPIClient:
    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler
        self.session = httpx.AsyncClient()
    
    @handle_errors("APIClient")
    async def generate_flashcard(self, word: str, user_id: str):
        """Generate flashcard with comprehensive error handling"""
        
        # Validate input
        if not word or not word.strip():
            raise ValidationError(
                "Word cannot be empty",
                field="word",
                value=word
            )
        
        # Make API call with error context
        with self.error_handler.error_context(
            component="APIClient",
            operation="generate_flashcard",
            user_id=user_id,
            input_data={"word": word}
        ):
            try:
                response = await self.session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=self._build_request(word)
                )
                response.raise_for_status()
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Rate limit with retry info
                    retry_after = int(
                        e.response.headers.get('Retry-After', 60)
                    )
                    raise RateLimitError(
                        "API rate limit exceeded",
                        retry_after=retry_after
                    )
                elif e.response.status_code == 401:
                    raise AuthenticationError("Invalid API key")
                else:
                    raise ApiError(
                        f"API error: {e.response.text}",
                        status_code=e.response.status_code
                    )
            
            except httpx.ConnectError as e:
                raise NetworkError(
                    "Failed to connect to API",
                    original_error=e
                )
            
            # Parse response
            try:
                result = response.json()
                return self._parse_flashcard(result)
            except (json.JSONDecodeError, KeyError) as e:
                raise ParsingError(
                    f"Failed to parse API response: {e}"
                )
```

## Monitoring Dashboard

Create a simple monitoring script:

```python
# scripts/error_monitor.py
import asyncio
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.live import Live

async def monitor_dashboard(error_handler):
    console = Console()
    
    with Live(console=console, refresh_per_second=1) as live:
        while True:
            # Get current analysis
            analysis = error_handler.get_error_analysis(hours=1)
            
            # Create table
            table = Table(title=f"Error Monitor - {datetime.now()}")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Total Errors", str(analysis['total_errors']))
            table.add_row(
                "Recovery Rate",
                f"{analysis['recovery_success_rate']:.1%}"
            )
            
            # Add category breakdown
            for cat, count in analysis['by_category'].items():
                table.add_row(f"  {cat}", str(count))
            
            live.update(table)
            await asyncio.sleep(5)
```

## Troubleshooting

### Common Issues

1. **Database Lock Errors**
   - Check for long-running transactions
   - Use WAL mode for SQLite
   - Implement connection pooling

2. **High Memory Usage**
   - Enable automatic memory cleanup
   - Reduce batch sizes
   - Clear caches periodically

3. **Recovery Failures**
   - Check recovery strategy configuration
   - Verify network connectivity
   - Review error patterns

### Debug Mode

Enable detailed logging:

```python
import logging

# Enable debug logging
logging.getLogger('flashcard_pipeline.error_handler').setLevel(logging.DEBUG)

# Track recovery attempts
error_handler.debug_mode = True
```

## Performance Considerations

1. **Async Recovery** - Recovery strategies run asynchronously
2. **Database Indexes** - Optimized for time-based queries
3. **Memory Efficient** - Old errors are automatically pruned
4. **Batch Operations** - Analysis aggregates data efficiently

## Future Enhancements

Planned improvements:
- Machine learning for error prediction
- Automated error report generation
- Integration with monitoring services
- Real-time error dashboards
- Predictive failure detection