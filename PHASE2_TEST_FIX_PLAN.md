# Phase 2 Test Fix Plan

**Created**: 2025-01-08  
**Current Status**: 37/85 tests passing (44%)  
**Target**: 80%+ pass rate

## Overview

Phase 2 Component Testing is currently at 44% pass rate. This plan breaks down the fixes needed by component, prioritizing based on impact and dependencies.

## Component Status Summary

| Component | Pass Rate | Tests | Priority | Complexity |
|-----------|-----------|-------|----------|------------|
| Cache Service | 82% | 18/22 | Low | Easy |
| API Client | 42% | 8/19 | High | Medium |
| Circuit Breaker | 37% | 7/19 | Medium | High |
| Rate Limiter | 14% | 4/29 | High | Medium |

## Sub-Phase 1: Cache Service Completion (82% → 95%+)
**Timeline**: 0.5-1 hour  
**Current**: 18/22 passing

### Issues to Fix:
1. **Concurrency Tests** (2 failures)
   - `test_concurrent_writes` - File locking issue
   - `test_concurrent_read_write` - Race condition
   - **Fix**: Add proper async locking in cache operations

2. **Edge Cases** (2 failures)
   - `test_corrupted_cache_file` - Error handling
   - `test_size_calculation` - Stats tracking
   - **Fix**: Add try-except blocks and update stats logic

### Implementation Steps:
```python
# 1. Fix concurrent writes
async def save_stage1(self, ...):
    async with self._get_lock(cache_key):  # Already exists
        # Add file operation error handling
        
# 2. Fix corrupted file handling
try:
    data = json.loads(content)
except json.JSONDecodeError:
    # Log and return None instead of raising
    return None
```

## Sub-Phase 2: API Client Fixes (42% → 80%+)
**Timeline**: 1-2 hours  
**Current**: 8/19 passing

### Critical Issues:

1. **Response Parsing** (3 failures)
   - Markdown block parsing incomplete
   - Null comparison handling
   - Missing response fields

2. **Error Response Headers** (8 failures)
   - All error responses missing headers
   - Authentication error returns wrong exception type
   - Retry logic expects headers on error responses

### Fix Strategy:

#### 2.1 Fix Markdown Parsing
```python
# Current issue: Expects pure JSON after stripping markdown
# Fix: Extract JSON from within markdown content
def extract_json_from_markdown(content):
    # Find JSON block between ```json and ```
    import re
    json_match = re.search(r'```json\s*\n(.*?)\n```', content, re.DOTALL)
    if json_match:
        return json_match.group(1)
    return content
```

#### 2.2 Fix Error Responses
```python
# Update all error mock responses
Mock(status_code=503, headers={}, json=lambda: {"error": {"message": "Service unavailable"}})
# Add to create_api_response helper for error cases
```

#### 2.3 Fix Model Mismatches
```python
# Update test responses to use correct Stage1Response format:
# - term_number, term, ipa, pos (not romanization, part_of_speech)
# - comparison is required (not optional)
# - All 15+ fields must be present
```

## Sub-Phase 3: Rate Limiter Implementation (14% → 70%+)
**Timeline**: 2-3 hours  
**Current**: 4/29 passing, 8 errors

### Major Issues:

1. **Missing Fixtures** (8 errors)
   - Distributed rate limiter fixture
   - Async context manager support
   - Thread-safe operations

2. **Core Implementation** (17 failures)
   - Token bucket algorithm incomplete
   - Refill rate calculation
   - Async acquire/release

### Implementation Plan:

#### 3.1 Create Missing Fixtures
```python
@pytest.fixture
def rate_limiter():
    return RateLimiter(rate=10, capacity=100)

@pytest.fixture
def distributed_limiter():
    return DistributedRateLimiter(rate=10, capacity=100)
```

#### 3.2 Implement Core Token Bucket
```python
class RateLimiter:
    def __init__(self, rate: float, capacity: int):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        async with self._lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
```

## Sub-Phase 4: Circuit Breaker Features (37% → 70%+)
**Timeline**: 2-3 hours  
**Current**: 7/19 passing

### Missing Features:

1. **Multi-Service Support** (5 failures)
   - Service isolation
   - Reset all breakers
   - Per-service configuration

2. **Adaptive Thresholds** (7 failures)
   - Error burst detection
   - Dynamic threshold adjustment
   - Pattern recognition

### Implementation Approach:

#### 4.1 Multi-Service Architecture
```python
class CircuitBreakerManager:
    def __init__(self):
        self.breakers = {}
    
    def get_breaker(self, service: str) -> CircuitBreaker:
        if service not in self.breakers:
            self.breakers[service] = CircuitBreaker()
        return self.breakers[service]
```

#### 4.2 Adaptive Features
```python
class AdaptiveCircuitBreaker(CircuitBreaker):
    def __init__(self):
        super().__init__()
        self.error_history = deque(maxlen=100)
        self.adaptive_threshold = 0.5
    
    def record_error(self):
        self.error_history.append(time.time())
        self._adjust_threshold()
```

## Execution Order

### Day 1 (Quick Wins):
1. **Cache Service** (0.5-1 hour) - Get to 95%+
2. **API Client Response Parsing** (1 hour) - Fix markdown & nulls

### Day 2 (Core Features):
3. **API Client Error Handling** (1 hour) - Fix all error responses
4. **Rate Limiter Fixtures** (1 hour) - Unblock tests

### Day 3 (Complex Features):
5. **Rate Limiter Implementation** (2 hours) - Core algorithm
6. **Circuit Breaker Multi-Service** (1 hour) - Basic isolation

### Day 4 (Advanced):
7. **Circuit Breaker Adaptive** (2 hours) - Pattern detection
8. **Integration Testing** (1 hour) - Verify all components

## Success Metrics

### Minimum Acceptable (Phase 2 Complete):
- Overall: 70%+ pass rate (60+ tests passing)
- Each component: 60%+ pass rate
- No blocking errors

### Target Goal:
- Overall: 85%+ pass rate (72+ tests passing)  
- Cache: 95%+ (21/22)
- API Client: 85%+ (16/19)
- Rate Limiter: 70%+ (20/29)
- Circuit Breaker: 70%+ (13/19)

## Quick Fix Checklist

- [ ] Add headers to all Mock responses
- [ ] Update all error responses to use correct format
- [ ] Create missing pytest fixtures
- [ ] Fix JSON extraction from markdown
- [ ] Add async locks where needed
- [ ] Implement token bucket algorithm
- [ ] Add service isolation to circuit breaker
- [ ] Fix all import errors

## Notes

1. Some tests expect features that may not be in requirements (TTL, size limits)
2. Consider marking some tests as `@pytest.mark.skip("Feature not implemented")`
3. Focus on core functionality first, advanced features later
4. Update implementation to match test expectations where reasonable