# API Documentation

Complete API reference for the Korean Language Flashcard Pipeline system.

## Overview

This directory contains documentation for all APIs used in the flashcard pipeline:
- External API integrations (OpenRouter)
- Internal REST APIs
- Plugin development APIs
- Database APIs

## API Categories

### External APIs

#### OpenRouter Integration
- **Purpose**: Access to Claude Sonnet 4 for AI-powered flashcard generation
- **Documentation**: [OPENROUTER.md](./OPENROUTER.md)
- **Authentication**: API key required
- **Rate Limits**: 60 requests/minute default

### Internal APIs

#### REST API
- **Purpose**: Internal service communication
- **Documentation**: [REST_API.md](./REST_API.md)
- **Format**: JSON
- **Authentication**: Internal token

#### Plugin API
- **Purpose**: Extend pipeline functionality
- **Documentation**: [PLUGIN_API.md](./PLUGIN_API.md)
- **Interface**: Python/Rust plugins
- **Registration**: Dynamic loading

### Database APIs

#### Query Interface
- **Purpose**: Database operations
- **Technology**: SQLite/SQLAlchemy
- **Async Support**: Yes (aiosqlite)

## Quick Reference

### OpenRouter API Call
```python
from flashcard_pipeline import OpenRouterClient

client = OpenRouterClient(api_key="your-key")
response = await client.generate_flashcard(
    vocabulary_item={
        "korean": "안녕하세요",
        "english": "Hello"
    }
)
```

### Internal REST API
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/process",
        json={"items": vocabulary_list}
    )
```

### Plugin Development
```python
from flashcard_pipeline.plugins import BasePlugin

class MyPlugin(BasePlugin):
    def process(self, item):
        # Custom processing logic
        return enhanced_item
```

## API Standards

### Request Format
- **Content-Type**: application/json
- **Encoding**: UTF-8
- **Method**: RESTful conventions

### Response Format
```json
{
    "status": "success|error",
    "data": {},
    "error": {
        "code": "ERROR_CODE",
        "message": "Human readable message",
        "details": {}
    },
    "metadata": {
        "timestamp": "2024-01-09T10:30:00Z",
        "request_id": "uuid"
    }
}
```

### Error Codes
- `400` - Bad Request (validation error)
- `401` - Unauthorized (auth required)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `429` - Too Many Requests (rate limit)
- `500` - Internal Server Error
- `503` - Service Unavailable

## Best Practices

### API Design
1. Use consistent naming conventions
2. Version your APIs (/v1/, /v2/)
3. Provide clear error messages
4. Include request IDs for tracking
5. Document all parameters

### Security
1. Always use HTTPS in production
2. Implement rate limiting
3. Validate all inputs
4. Sanitize outputs
5. Log security events

### Performance
1. Implement caching where appropriate
2. Use pagination for large results
3. Support batch operations
4. Minimize response payload
5. Enable compression

## Integration Examples

### Basic Integration
```python
# Simple vocabulary processing
result = await api.process_vocabulary([
    {"korean": "책", "english": "book"},
    {"korean": "학교", "english": "school"}
])
```

### Advanced Integration
```python
# With options and error handling
try:
    result = await api.process_vocabulary(
        items=vocabulary_list,
        options={
            "difficulty_level": 3,
            "include_examples": True,
            "cache": True
        },
        callback=progress_handler
    )
except RateLimitError:
    # Handle rate limiting
    await asyncio.sleep(60)
except APIError as e:
    # Handle API errors
    logger.error(f"API error: {e}")
```

## API Documentation Standards

Each API should document:
1. **Endpoint** - URL and method
2. **Purpose** - What it does
3. **Parameters** - All inputs with types
4. **Response** - Format and fields
5. **Examples** - Working code samples
6. **Errors** - Possible error responses
7. **Rate Limits** - Any restrictions

## Testing APIs

Use the provided test clients:
```bash
# Test OpenRouter integration
python -m flashcard_pipeline.test_api --api openrouter

# Test internal APIs
python -m flashcard_pipeline.test_api --api internal

# Load test
python -m flashcard_pipeline.test_api --load-test --concurrent 10
```