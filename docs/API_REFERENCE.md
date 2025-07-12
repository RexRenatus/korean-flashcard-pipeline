# API Reference - Korean Language Flashcard Pipeline

## Table of Contents
1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Core APIs](#core-apis)
4. [REST API Endpoints](#rest-api-endpoints)
5. [Python SDK](#python-sdk)
6. [Response Formats](#response-formats)
7. [Error Handling](#error-handling)
8. [Rate Limits](#rate-limits)
9. [Webhooks](#webhooks)
10. [Examples](#examples)

## Overview

The Korean Language Flashcard Pipeline provides both REST API endpoints and a Python SDK for integrating flashcard generation into your applications.

### Base URL
```
https://api.flashcardpipeline.com/v1
```

### API Versioning
- Current version: `v1`
- Version specified in URL path
- Backward compatibility maintained for 12 months

### Content Types
- Request: `application/json`
- Response: `application/json`
- File uploads: `multipart/form-data`

## Authentication

### API Key Authentication

Include your API key in the `Authorization` header:
```http
Authorization: Bearer YOUR_API_KEY
```

### Getting an API Key
```bash
curl -X POST https://api.flashcardpipeline.com/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "organization": "My Company"
  }'
```

### API Key Management

#### List API Keys
```http
GET /v1/auth/keys
Authorization: Bearer YOUR_MASTER_KEY
```

#### Create New API Key
```http
POST /v1/auth/keys
Authorization: Bearer YOUR_MASTER_KEY
Content-Type: application/json

{
  "name": "Production Key",
  "permissions": ["read", "write"],
  "rate_limit": 1000
}
```

#### Revoke API Key
```http
DELETE /v1/auth/keys/{key_id}
Authorization: Bearer YOUR_MASTER_KEY
```

## Core APIs

### Process Word

Generate a flashcard for a single Korean word.

```http
POST /v1/flashcards/process
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "word": "안녕하세요",
  "options": {
    "include_nuance": true,
    "difficulty_level": "beginner",
    "include_etymology": false,
    "skip_cache": false
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "flashcard_id": "fc_123456",
    "word": "안녕하세요",
    "romanization": "annyeonghaseyo",
    "definition": "Hello (formal greeting)",
    "part_of_speech": "interjection",
    "difficulty": "beginner",
    "examples": [
      {
        "korean": "안녕하세요, 만나서 반갑습니다.",
        "english": "Hello, nice to meet you.",
        "romanization": "annyeonghaseyo, mannaseo bangapseumnida."
      }
    ],
    "cultural_notes": [
      "Most common formal greeting in Korean",
      "Used when meeting someone for the first time"
    ],
    "conjugations": {
      "informal": "안녕",
      "formal_polite": "안녕하세요",
      "formal_deferential": "안녕하십니까"
    },
    "created_at": "2024-01-09T12:00:00Z"
  }
}
```

### Batch Processing

Process multiple words in a single request.

```http
POST /v1/flashcards/batch
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "words": [
    {"word": "안녕", "category": "greeting"},
    {"word": "감사", "category": "politeness"},
    {"word": "사랑", "category": "emotion"}
  ],
  "options": {
    "include_nuance": true,
    "parallel": true,
    "batch_size": 10
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "batch_id": "batch_789012",
    "status": "processing",
    "total": 3,
    "completed": 0,
    "results_url": "/v1/batches/batch_789012/results"
  }
}
```

### Get Batch Results

```http
GET /v1/batches/{batch_id}/results
Authorization: Bearer YOUR_API_KEY
```

**Response:**
```json
{
  "success": true,
  "data": {
    "batch_id": "batch_789012",
    "status": "completed",
    "total": 3,
    "completed": 3,
    "results": [
      {
        "word": "안녕",
        "status": "success",
        "flashcard": { /* flashcard data */ }
      },
      {
        "word": "감사",
        "status": "success",
        "flashcard": { /* flashcard data */ }
      },
      {
        "word": "사랑",
        "status": "success",
        "flashcard": { /* flashcard data */ }
      }
    ],
    "completed_at": "2024-01-09T12:05:00Z"
  }
}
```

## REST API Endpoints

### Flashcard Management

#### Get Flashcard
```http
GET /v1/flashcards/{flashcard_id}
Authorization: Bearer YOUR_API_KEY
```

#### Update Flashcard
```http
PUT /v1/flashcards/{flashcard_id}
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "definition": "Updated definition",
  "examples": [
    {
      "korean": "New example",
      "english": "New translation"
    }
  ]
}
```

#### Delete Flashcard
```http
DELETE /v1/flashcards/{flashcard_id}
Authorization: Bearer YOUR_API_KEY
```

#### Search Flashcards
```http
GET /v1/flashcards/search?q=안녕&category=greeting&difficulty=beginner
Authorization: Bearer YOUR_API_KEY
```

### Export Operations

#### Export to Anki
```http
POST /v1/export/anki
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "flashcard_ids": ["fc_123", "fc_456"],
  "deck_name": "Korean Vocabulary",
  "note_type": "Korean Advanced"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "export_id": "exp_345678",
    "format": "anki",
    "download_url": "/v1/exports/exp_345678/download",
    "expires_at": "2024-01-10T12:00:00Z"
  }
}
```

#### Export to CSV
```http
POST /v1/export/csv
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "filters": {
    "category": "greeting",
    "created_after": "2024-01-01"
  },
  "columns": ["word", "definition", "romanization", "examples"]
}
```

#### Download Export
```http
GET /v1/exports/{export_id}/download
Authorization: Bearer YOUR_API_KEY
```

### Cache Management

#### Clear Cache
```http
POST /v1/cache/clear
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "scope": "all",  // or "word"
  "word": "안녕"   // if scope is "word"
}
```

#### Get Cache Statistics
```http
GET /v1/cache/stats
Authorization: Bearer YOUR_API_KEY
```

**Response:**
```json
{
  "success": true,
  "data": {
    "total_entries": 1234,
    "total_size": "45.6 MB",
    "hit_rate": 0.85,
    "oldest_entry": "2024-01-01T00:00:00Z",
    "newest_entry": "2024-01-09T12:00:00Z"
  }
}
```

### User Management

#### Get User Info
```http
GET /v1/user/me
Authorization: Bearer YOUR_API_KEY
```

#### Update User Settings
```http
PUT /v1/user/settings
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "default_difficulty": "intermediate",
  "include_nuance": true,
  "export_format": "anki"
}
```

#### Get Usage Statistics
```http
GET /v1/user/usage
Authorization: Bearer YOUR_API_KEY
```

**Response:**
```json
{
  "success": true,
  "data": {
    "period": "2024-01",
    "flashcards_created": 156,
    "api_calls": 234,
    "cache_hits": 78,
    "estimated_cost": "$1.25",
    "rate_limit": {
      "limit": 1000,
      "remaining": 766,
      "reset_at": "2024-01-09T13:00:00Z"
    }
  }
}
```

## Python SDK

### Installation
```bash
pip install flashcard-pipeline-sdk
```

### Quick Start
```python
from flashcard_pipeline import FlashcardClient

# Initialize client
client = FlashcardClient(api_key="YOUR_API_KEY")

# Process single word
flashcard = client.process_word("안녕하세요")
print(flashcard.definition)

# Batch processing
batch = client.process_batch(["안녕", "감사", "사랑"])
for result in batch.results:
    print(f"{result.word}: {result.definition}")
```

### Advanced Usage

#### Async Operations
```python
import asyncio
from flashcard_pipeline import AsyncFlashcardClient

async def main():
    client = AsyncFlashcardClient(api_key="YOUR_API_KEY")
    
    # Process multiple words concurrently
    words = ["안녕", "감사", "사랑", "행복", "꿈"]
    tasks = [client.process_word(word) for word in words]
    results = await asyncio.gather(*tasks)
    
    for flashcard in results:
        print(f"{flashcard.word}: {flashcard.definition}")

asyncio.run(main())
```

#### Custom Configuration
```python
from flashcard_pipeline import FlashcardClient, Config

config = Config(
    api_key="YOUR_API_KEY",
    base_url="https://api.flashcardpipeline.com/v1",
    timeout=30,
    max_retries=3,
    rate_limit=100
)

client = FlashcardClient(config=config)
```

#### Error Handling
```python
from flashcard_pipeline import FlashcardClient
from flashcard_pipeline.exceptions import (
    RateLimitError,
    APIError,
    ValidationError
)

client = FlashcardClient(api_key="YOUR_API_KEY")

try:
    flashcard = client.process_word("안녕")
except RateLimitError as e:
    print(f"Rate limit exceeded. Retry after: {e.retry_after}s")
except ValidationError as e:
    print(f"Invalid input: {e.message}")
except APIError as e:
    print(f"API error: {e.status_code} - {e.message}")
```

#### Pagination
```python
# Search with pagination
results = client.search_flashcards(
    query="greeting",
    page=1,
    per_page=20
)

print(f"Total results: {results.total}")
print(f"Current page: {results.page}")
print(f"Total pages: {results.pages}")

for flashcard in results.items:
    print(f"{flashcard.word}: {flashcard.definition}")

# Get next page
if results.has_next:
    next_results = results.next_page()
```

#### Callbacks and Events
```python
def on_progress(current, total):
    print(f"Progress: {current}/{total}")

def on_complete(results):
    print(f"Completed! Processed {len(results)} words")

# Batch processing with callbacks
batch = client.process_batch(
    words=["안녕", "감사", "사랑"],
    on_progress=on_progress,
    on_complete=on_complete
)
```

## Response Formats

### Success Response
```json
{
  "success": true,
  "data": {
    // Response data
  },
  "meta": {
    "request_id": "req_123456",
    "timestamp": "2024-01-09T12:00:00Z",
    "version": "v1"
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please retry after 60 seconds.",
    "details": {
      "limit": 100,
      "window": "1h",
      "retry_after": 60
    }
  },
  "meta": {
    "request_id": "req_123456",
    "timestamp": "2024-01-09T12:00:00Z"
  }
}
```

### Flashcard Object
```json
{
  "flashcard_id": "fc_123456",
  "word": "안녕하세요",
  "romanization": "annyeonghaseyo",
  "definition": "Hello (formal greeting)",
  "part_of_speech": "interjection",
  "difficulty": "beginner",
  "examples": [
    {
      "korean": "안녕하세요, 만나서 반갑습니다.",
      "english": "Hello, nice to meet you.",
      "romanization": "annyeonghaseyo, mannaseo bangapseumnida.",
      "audio_url": "/audio/example_123.mp3"
    }
  ],
  "cultural_notes": [
    "Most common formal greeting in Korean"
  ],
  "related_words": [
    {
      "word": "안녕",
      "relationship": "informal_variant"
    }
  ],
  "conjugations": {
    "informal": "안녕",
    "formal_polite": "안녕하세요",
    "formal_deferential": "안녕하십니까"
  },
  "memory_aids": {
    "mnemonic": "An young person says 'hello'",
    "visual_hint": "👋"
  },
  "tags": ["greeting", "formal", "essential"],
  "metadata": {
    "frequency_rank": 10,
    "jlpt_level": null,
    "topik_level": 1
  },
  "created_at": "2024-01-09T12:00:00Z",
  "updated_at": "2024-01-09T12:00:00Z"
}
```

## Error Handling

### Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `INVALID_API_KEY` | Invalid or missing API key | 401 |
| `INSUFFICIENT_PERMISSIONS` | API key lacks required permissions | 403 |
| `RATE_LIMIT_EXCEEDED` | Too many requests | 429 |
| `INVALID_REQUEST` | Invalid request format | 400 |
| `WORD_NOT_FOUND` | Korean word not recognized | 404 |
| `INTERNAL_ERROR` | Server error | 500 |
| `SERVICE_UNAVAILABLE` | Service temporarily unavailable | 503 |

### Error Response Format
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      // Additional error-specific information
    },
    "documentation_url": "https://docs.flashcardpipeline.com/errors/ERROR_CODE"
  }
}
```

### Retry Strategy

For transient errors (5xx status codes), implement exponential backoff:

```python
import time
from flashcard_pipeline import FlashcardClient

client = FlashcardClient(api_key="YOUR_API_KEY")

def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt
            print(f"Retry {attempt + 1} after {wait_time}s")
            time.sleep(wait_time)

# Usage
result = retry_with_backoff(
    lambda: client.process_word("안녕")
)
```

## Rate Limits

### Default Limits

| Plan | Requests/Hour | Concurrent Requests | Batch Size |
|------|---------------|---------------------|------------|
| Free | 100 | 1 | 10 |
| Basic | 1,000 | 5 | 50 |
| Pro | 10,000 | 20 | 100 |
| Enterprise | Custom | Custom | Custom |

### Rate Limit Headers

All responses include rate limit information:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 234
X-RateLimit-Reset: 1704807600
X-RateLimit-Reset-After: 3600
```

### Handling Rate Limits

```python
from flashcard_pipeline import FlashcardClient
from flashcard_pipeline.exceptions import RateLimitError
import time

client = FlashcardClient(api_key="YOUR_API_KEY")

try:
    flashcard = client.process_word("안녕")
except RateLimitError as e:
    print(f"Rate limit exceeded. Waiting {e.retry_after} seconds...")
    time.sleep(e.retry_after)
    flashcard = client.process_word("안녕")  # Retry
```

## Webhooks

### Webhook Configuration

```http
POST /v1/webhooks
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "url": "https://your-app.com/webhook",
  "events": ["flashcard.created", "batch.completed"],
  "secret": "your_webhook_secret"
}
```

### Webhook Events

| Event | Description | Payload |
|-------|-------------|---------|
| `flashcard.created` | New flashcard created | Flashcard object |
| `flashcard.updated` | Flashcard updated | Updated flashcard |
| `flashcard.deleted` | Flashcard deleted | `{flashcard_id}` |
| `batch.started` | Batch processing started | Batch info |
| `batch.completed` | Batch processing completed | Results |
| `batch.failed` | Batch processing failed | Error info |

### Webhook Payload

```json
{
  "event": "flashcard.created",
  "data": {
    // Event-specific data
  },
  "timestamp": "2024-01-09T12:00:00Z",
  "signature": "sha256=..."
}
```

### Verifying Webhooks

```python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)

# In your webhook handler
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    signature = request.headers.get('X-Webhook-Signature')
    if not verify_webhook(request.data, signature, WEBHOOK_SECRET):
        return "Invalid signature", 401
    
    # Process webhook
    event = request.json
    if event['event'] == 'flashcard.created':
        process_new_flashcard(event['data'])
    
    return "OK", 200
```

## Examples

### Complete Integration Example

```python
from flashcard_pipeline import FlashcardClient
import csv

# Initialize client
client = FlashcardClient(api_key="YOUR_API_KEY")

# Read words from CSV
words_to_process = []
with open('korean_words.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        words_to_process.append({
            'word': row['word'],
            'category': row.get('category', 'general'),
            'difficulty': row.get('difficulty', 'beginner')
        })

# Process in batches
batch_size = 50
for i in range(0, len(words_to_process), batch_size):
    batch = words_to_process[i:i+batch_size]
    
    try:
        results = client.process_batch(
            words=[item['word'] for item in batch],
            options={'include_nuance': True}
        )
        
        # Wait for completion
        results.wait_for_completion(timeout=300)
        
        # Export to Anki
        if results.status == 'completed':
            export = client.export_anki(
                flashcard_ids=[r.flashcard_id for r in results.results],
                deck_name="Korean Vocabulary Batch"
            )
            print(f"Export ready: {export.download_url}")
            
    except Exception as e:
        print(f"Error processing batch {i//batch_size + 1}: {e}")
```

### Custom Prompt Example

```python
# Use custom prompt for specialized content
custom_prompt = """
Focus on business Korean vocabulary.
Include formal usage examples.
Add notes about workplace etiquette.
"""

flashcard = client.process_word(
    "회의",
    options={
        'custom_prompt': custom_prompt,
        'include_etymology': True,
        'examples_count': 5
    }
)
```

### Streaming Example

```python
# Stream results for large batches
def process_large_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            word = line.strip()
            if word:
                try:
                    flashcard = client.process_word(word)
                    yield flashcard
                except Exception as e:
                    print(f"Error processing {word}: {e}")

# Process and save results
with open('results.jsonl', 'w', encoding='utf-8') as out:
    for flashcard in process_large_file('words.txt'):
        out.write(flashcard.to_json() + '\n')
```

## SDK Language Support

Official SDKs available for:
- Python: `pip install flashcard-pipeline-sdk`
- JavaScript/Node.js: `npm install flashcard-pipeline`
- Go: `go get github.com/flashcard-pipeline/go-sdk`
- Ruby: `gem install flashcard-pipeline`

Community SDKs:
- PHP: [github.com/community/flashcard-pipeline-php](https://github.com/community/flashcard-pipeline-php)
- Java: [github.com/community/flashcard-pipeline-java](https://github.com/community/flashcard-pipeline-java)
- C#: [github.com/community/flashcard-pipeline-dotnet](https://github.com/community/flashcard-pipeline-dotnet)

## API Changelog

### v1.2.0 (2024-01-15)
- Added webhook support
- Improved batch processing performance
- New export format: Memrise

### v1.1.0 (2023-12-01)
- Added cultural notes to flashcards
- Support for custom prompts
- Rate limit increase for Pro plans

### v1.0.0 (2023-10-01)
- Initial API release
- Core flashcard generation
- Batch processing
- Export to Anki and CSV