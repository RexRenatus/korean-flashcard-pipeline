# API Architecture

**Last Updated**: 2025-07-06

## Overview

The Korean Language Flashcard Pipeline uses a modular API architecture designed for scalability, reliability, and maintainability. The system integrates with OpenRouter's API to leverage Claude Sonnet 4 for AI-powered flashcard generation.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │     CLI     │  │   Pipeline   │  │    Database     │  │
│  │  Interface  │  │   Manager    │  │    Manager      │  │
│  └──────┬──────┘  └──────┬───────┘  └────────┬────────┘  │
│         │                 │                    │           │
├─────────┴─────────────────┴────────────────────┴───────────┤
│                      Service Layer                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ OpenRouter   │  │    Rate      │  │     Cache       │  │
│  │   Client     │  │   Limiter    │  │    Service      │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬────────┘  │
│         │                  │                    │           │
├─────────┴──────────────────┴────────────────────┴──────────┤
│                    Infrastructure Layer                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │    HTTP/2    │  │   SQLite     │  │  Memory Map     │  │
│  │   (httpx)    │  │  Database    │  │    Cache        │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. OpenRouter Client

**Purpose**: Manages all communication with the OpenRouter API.

**Key Features**:
- Async HTTP/2 client using httpx
- Automatic retry with exponential backoff
- Request/response validation
- Preset management for consistent AI behavior

**Implementation**:
```python
class OpenRouterClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.client = httpx.AsyncClient(http2=True)
        self.rate_limiter = RateLimiter()
```

### 2. Rate Limiter

**Purpose**: Prevents API rate limit violations and ensures sustainable usage.

**Key Features**:
- Token bucket algorithm
- Configurable limits per time window
- Automatic request queuing
- Burst handling

**Configuration**:
```python
RATE_LIMITS = {
    "requests_per_minute": 60,
    "requests_per_hour": 1000,
    "tokens_per_minute": 150000
}
```

### 3. Cache Service

**Purpose**: Minimizes API calls and costs through intelligent caching.

**Key Features**:
- SQLite-based persistent cache
- Memory-mapped file access for speed
- Content-based cache keys
- TTL support for cache invalidation

**Cache Strategy**:
- Stage 1 results: Cached indefinitely (semantic analysis rarely changes)
- Stage 2 results: Cached with 30-day TTL (may want regeneration)
- Failed requests: Cached for 1 hour (temporary failures)

## API Flow

### 1. Two-Stage Generation Process

```
Input CSV → Stage 1 (Semantic Analysis) → Stage 2 (Card Generation) → Output TSV
```

#### Stage 1: Semantic Analysis
- **Preset**: `@preset/nuance-creator`
- **Purpose**: Extract nuanced meanings, contexts, and usage notes
- **Input**: Vocabulary item (Korean, English, type)
- **Output**: Structured semantic data

#### Stage 2: Card Generation
- **Preset**: `@preset/nuance-flashcard-generator`
- **Purpose**: Generate Recognition and Production flashcards
- **Input**: Vocabulary item + Stage 1 results
- **Output**: TSV-formatted flashcard data

### 2. Request Lifecycle

```python
async def process_vocabulary_item(item: VocabularyItem):
    # 1. Check cache
    cached_result = await cache.get(item)
    if cached_result:
        return cached_result
    
    # 2. Rate limit check
    await rate_limiter.acquire()
    
    # 3. Make API request
    try:
        result = await openrouter_client.request(item)
    except RateLimitError:
        await asyncio.sleep(backoff_time)
        return await process_vocabulary_item(item)  # Retry
    
    # 4. Cache result
    await cache.set(item, result)
    
    return result
```

## Error Handling

### 1. Retry Strategy

**Exponential Backoff**:
```python
backoff_time = min(
    initial_delay * (2 ** attempt),
    max_delay
) + random.uniform(0, jitter)
```

**Retry Conditions**:
- Rate limit errors (429)
- Temporary network failures
- Server errors (5xx)

**Non-Retry Conditions**:
- Authentication errors (401)
- Invalid request errors (400)
- Not found errors (404)

### 2. Circuit Breaker

**Purpose**: Prevent cascading failures when API is unavailable.

**States**:
- **Closed**: Normal operation
- **Open**: All requests fail immediately
- **Half-Open**: Limited requests to test recovery

**Configuration**:
```python
CIRCUIT_BREAKER = {
    "failure_threshold": 5,
    "recovery_timeout": 60,
    "expected_exception": APIError
}
```

## Security Considerations

### 1. API Key Management
- Stored in environment variables
- Never logged or exposed in errors
- Validated on startup

### 2. Request Validation
- Input sanitization
- Size limits on requests
- Content type validation

### 3. Response Validation
- JSON schema validation
- Content security checks
- Error message sanitization

## Performance Optimizations

### 1. Connection Pooling
- Persistent HTTP/2 connections
- Connection reuse across requests
- Automatic connection health checks

### 2. Async Processing
- Concurrent request handling
- Non-blocking I/O operations
- Efficient resource utilization

### 3. Batch Processing
- Group requests for efficiency
- Parallel processing within rate limits
- Progress tracking and resumability

## Monitoring and Observability

### 1. Metrics
- Request rate and latency
- Cache hit/miss ratio
- Error rates by type
- Token usage tracking

### 2. Logging
- Structured JSON logging
- Request/response correlation IDs
- Performance timing logs
- Error context capture

### 3. Health Checks
- API connectivity test
- Database connection check
- Cache service status
- Rate limiter state

## Future Enhancements

### 1. Webhook Support
- Async processing notifications
- Progress updates via webhooks
- Error notifications

### 2. GraphQL Integration
- Flexible data queries
- Reduced over-fetching
- Better client control

### 3. Multi-Model Support
- A/B testing different models
- Model performance comparison
- Automatic model selection

### 4. Advanced Caching
- Redis integration for distributed cache
- Edge caching with CDN
- Predictive cache warming