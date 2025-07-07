# API Specifications

**Last Updated**: 2025-01-07

## Purpose

This document defines the exact API contracts, request/response formats, and integration specifications for the OpenRouter API using presets for the two-stage flashcard generation pipeline.

## OpenRouter API Endpoint

**Base URL**: `https://openrouter.ai/api/v1/chat/completions`  
**Method**: POST  
**Authentication**: Bearer token via Authorization header

## Authentication

```python
headers = {
    "Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY')}",
    "Content-Type": "application/json"
}
```

## Stage 1: Semantic Analysis API

### Request Format

```python
{
    "model": "@preset/nuance-creator",
    "messages": [
        {
            "role": "user",
            "content": vocabulary_item_json
        }
    ]
}
```

### Vocabulary Item Input Format

```json
{
    "position": 1,
    "term": "안녕하세요",
    "type": "interjection"
}
```

### Expected Response Format

```json
{
    "id": "gen-1234567890",
    "model": "@preset/nuance-creator",
    "object": "chat.completion",
    "created": 1704067200,
    "choices": [{
        "index": 0,
        "message": {
            "role": "assistant",
            "content": "{\"term_number\": 1, \"term\": \"안녕하세요\", \"ipa\": \"[an.njʌŋ.ha.se.jo]\", \"pos\": \"interjection\", \"primary_meaning\": \"Hello (formal)\", \"other_meanings\": \"Good day; How do you do\", \"metaphor\": \"A warm bow of greeting at dawn\", \"metaphor_noun\": \"bow\", \"metaphor_action\": \"greets warmly\", \"suggested_location\": \"temple entrance\", \"anchor_object\": \"wooden gate\", \"anchor_sensory\": \"smooth polished wood under palm\", \"explanation\": \"The bow represents the respectful formality inherent in this greeting\", \"usage_context\": null, \"comparison\": {\"vs\": \"안녕\", \"nuance\": \"안녕하세요 is formal/polite; 안녕 is casual between close friends\"}, \"homonyms\": [], \"korean_keywords\": [\"안녕하세요\", \"안녕\", \"인사\", \"예의\"]}"
        },
        "finish_reason": "stop"
    }],
    "usage": {
        "prompt_tokens": 150,
        "completion_tokens": 200,
        "total_tokens": 350
    }
}
```

### Stage 1 Response Data Structure

```typescript
interface Stage1Response {
    term_number: number;
    term: string;
    ipa: string;
    pos: string;  // "noun" | "verb" | "adjective" | "adverb" | "interjection" | "phrase"
    primary_meaning: string;
    other_meanings: string;
    metaphor: string;
    metaphor_noun: string;
    metaphor_action: string;
    suggested_location: string;
    anchor_object: string;
    anchor_sensory: string;
    explanation: string;
    usage_context: string | null;
    comparison: {
        vs: string;
        nuance: string;
    };
    homonyms: Array<{
        hanja: string;
        reading: string;
        meaning: string;
        differentiator: string;
    }>;
    korean_keywords: string[];
}
```

## Stage 2: Flashcard Generation API

### Request Format

```python
{
    "model": "@preset/nuance-flashcard-generator",
    "messages": [
        {
            "role": "user",
            "content": combined_data_json
        }
    ]
}
```

### Combined Input Format

```json
{
    "position": 1,
    "term": "안녕하세요",
    "stage1_result": {
        // Complete Stage 1 response object
    }
}
```

### Expected Response Format

```json
{
    "id": "gen-0987654321",
    "model": "@preset/nuance-flashcard-generator",
    "object": "chat.completion",
    "created": 1704067300,
    "choices": [{
        "index": 0,
        "message": {
            "role": "assistant",
            "content": "position\tterm\tterm_number\ttab_name\tprimer\tfront\tback\ttags\thonorific_level\n1\t안녕하세요[an.njʌŋ.ha.se.jo]\t1\tScene\tYou enter your clean, pleasant-smelling memory room...\t...\t...\tterm:안녕하세요,pos:interjection,card:Scene\t\n2\t안녕하세요[an.njʌŋ.ha.se.jo]\t1\tUsage-Comparison\t...\t...\t...\tterm:안녕하세요,pos:interjection,card:Usage-Comparison\t\n3\t안녕하세요[an.njʌŋ.ha.se.jo]\t1\tHanja\t...\t...\t...\tterm:안녕하세요,pos:interjection,card:Hanja\t"
        },
        "finish_reason": "stop"
    }],
    "usage": {
        "prompt_tokens": 400,
        "completion_tokens": 600,
        "total_tokens": 1000
    }
}
```

### Stage 2 TSV Output Format

The response content is a TSV string with the following columns:

| Column | Description | Example |
|--------|-------------|---------|
| position | Original position from CSV | 1 |
| term | Korean term with IPA | 안녕하세요[an.njʌŋ.ha.se.jo] |
| term_number | Sequential number | 1 |
| tab_name | Card type | Scene, Usage-Comparison, Hanja |
| primer | Memory palace introduction | You enter your clean... |
| front | Card front (question) | Stepping through another portal... |
| back | Card back (answer) | A warm bow of greeting... |
| tags | Metadata tags | term:안녕하세요,pos:interjection |
| honorific_level | Formality level | (empty for most cards) |

## Error Response Format

```json
{
    "error": {
        "message": "Rate limit exceeded",
        "type": "rate_limit_error",
        "code": 429
    }
}
```

## Rate Limiting

### Headers to Monitor
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1704067500
```

### Rate Limit Strategy
1. Check remaining requests before each call
2. If remaining < 5, calculate wait time until reset
3. Implement exponential backoff on 429 errors

## Python Client Implementation

### Base Client Class

```python
import httpx
import asyncio
from typing import Dict, Any, Optional
import os
import json
from datetime import datetime

class OpenRouterClient:
    def __init__(self):
        self.api_key = os.environ.get('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")
        
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def stage1_semantic_analysis(self, vocabulary_item: Dict[str, Any]) -> Dict[str, Any]:
        """Call Stage 1: Semantic Analysis"""
        payload = {
            "model": "@preset/nuance-creator",
            "messages": [
                {
                    "role": "user",
                    "content": json.dumps(vocabulary_item, ensure_ascii=False)
                }
            ]
        }
        
        response = await self._make_request(payload)
        return self._parse_stage1_response(response)
    
    async def stage2_card_generation(self, vocabulary_item: Dict[str, Any], 
                                   stage1_result: Dict[str, Any]) -> str:
        """Call Stage 2: Flashcard Generation"""
        combined_input = {
            "position": vocabulary_item["position"],
            "term": vocabulary_item["term"],
            "stage1_result": stage1_result
        }
        
        payload = {
            "model": "@preset/nuance-flashcard-generator",
            "messages": [
                {
                    "role": "user",
                    "content": json.dumps(combined_input, ensure_ascii=False)
                }
            ]
        }
        
        response = await self._make_request(payload)
        return self._parse_stage2_response(response)
    
    async def _make_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                response = await self.client.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    # Rate limit - wait and retry
                    wait_time = self._calculate_backoff(attempt)
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # Other error
                    response.raise_for_status()
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(self._calculate_backoff(attempt))
        
        raise Exception(f"Failed after {max_retries} attempts")
    
    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay"""
        return min(2 ** attempt, 30.0)
    
    def _parse_stage1_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and parse Stage 1 response"""
        content = response["choices"][0]["message"]["content"]
        return json.loads(content)
    
    def _parse_stage2_response(self, response: Dict[str, Any]) -> str:
        """Extract Stage 2 TSV response"""
        return response["choices"][0]["message"]["content"]
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
```

## Request/Response Caching

### Cache Key Generation

```python
import hashlib

def generate_cache_key(stage: int, vocabulary_item: Dict[str, Any]) -> str:
    """Generate deterministic cache key"""
    # For Stage 1: hash the term and type
    if stage == 1:
        content = f"{vocabulary_item['term']}:{vocabulary_item.get('type', 'unknown')}"
    # For Stage 2: hash the term and stage1 result
    else:
        content = f"{vocabulary_item['term']}:{json.dumps(vocabulary_item.get('stage1_result', {}), sort_keys=True)}"
    
    return hashlib.sha256(content.encode('utf-8')).hexdigest()
```

## Integration with Rust Pipeline

### Python-Rust Bridge

```rust
// Rust side
use pyo3::prelude::*;

#[pyfunction]
fn process_vocabulary_item(item: &str) -> PyResult<String> {
    // Call Python OpenRouterClient
    Python::with_gil(|py| {
        let client = py.import("flashcard_pipeline.api_client")?;
        let result = client.call_method1("process_item", (item,))?;
        Ok(result.to_string())
    })
}
```

## Testing Strategy

### Mock Responses

```python
# tests/fixtures/api_responses.py
MOCK_STAGE1_RESPONSE = {
    "choices": [{
        "message": {
            "content": json.dumps({
                "term_number": 1,
                "term": "test",
                "ipa": "[test]",
                # ... complete mock response
            })
        }
    }]
}

MOCK_STAGE2_RESPONSE = {
    "choices": [{
        "message": {
            "content": "position\tterm\t..."  # Mock TSV
        }
    }]
}
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_pipeline():
    """Test complete two-stage processing"""
    client = OpenRouterClient()
    
    # Test item
    item = {"position": 1, "term": "안녕하세요", "type": "interjection"}
    
    # Stage 1
    stage1_result = await client.stage1_semantic_analysis(item)
    assert stage1_result["term"] == "안녕하세요"
    
    # Stage 2
    tsv_output = await client.stage2_card_generation(item, stage1_result)
    assert "\t" in tsv_output  # TSV format
    
    await client.close()
```

## Performance Considerations

### Connection Pooling
- Reuse HTTP connections with httpx
- Maintain persistent client instance
- Configure appropriate timeouts

### Concurrent Processing
```python
async def process_batch(items: List[Dict[str, Any]], max_concurrent: int = 10):
    """Process multiple items concurrently"""
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_with_limit(item):
        async with semaphore:
            return await process_single_item(item)
    
    tasks = [process_with_limit(item) for item in items]
    return await asyncio.gather(*tasks)
```

## Monitoring & Logging

### Request Logging
```python
import logging

logger = logging.getLogger(__name__)

# Log each API call
logger.info(f"API Request: stage={stage}, term={item['term']}")
logger.debug(f"Request payload: {json.dumps(payload, ensure_ascii=False)}")
logger.info(f"API Response: status=200, tokens={response['usage']['total_tokens']}")
```

### Metrics Collection
```python
# Track API usage
METRICS = {
    "total_requests": 0,
    "stage1_requests": 0,
    "stage2_requests": 0,
    "total_tokens": 0,
    "cache_hits": 0,
    "cache_misses": 0,
    "errors": 0
}
```