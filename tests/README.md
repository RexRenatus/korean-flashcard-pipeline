# Test Suite for Korean Flashcard Pipeline

This directory contains the comprehensive test suite organized by testing phases.

## Structure

```
tests/
├── conftest.py          # Shared pytest fixtures and configuration
├── unit/                # Unit tests
│   ├── phase1/         # Foundation Testing
│   ├── phase2/         # Component Testing  
│   ├── phase3/         # Integration Testing
│   └── phase4/         # Performance Testing
└── e2e/                # End-to-End tests (Phase 5)
```

## Phase 1: Foundation Testing (✅ Complete)

Tests for core models, configuration system, and error handling.

**Files:**
- `test_models_validation.py` - VocabularyItem, Stage1/2Response, FlashcardRow validation
- `test_configuration.py` - Config loading, environment variables, validation
- `test_error_handling.py` - Error codes, recovery, user-friendly messages

**Run Phase 1 tests:**
```bash
python run_phase1_tests.py
```

## Phase 2: Component Testing (✅ Complete)

Tests for individual components:
- Cache Service - File-based caching with TTL and LRU memory cache
- Rate Limiter - Token bucket algorithm with distributed support
- Circuit Breaker - State transitions and adaptive thresholds
- API Client - Mocked HTTP responses and retry logic

**Files:**
- `test_cache_service.py` - Cache operations, invalidation, statistics
- `test_rate_limiter.py` - Token bucket, distributed limiting, fairness
- `test_circuit_breaker.py` - State transitions, failure handling, adaptation
- `test_api_client_mock.py` - Request/response handling without real API calls

**Run Phase 2 tests:**
```bash
python run_phase2_tests.py
```

## Phase 3: Integration Testing (🔄 Pending)

Tests for component integration:
- Mock Pipeline Processing
- Database Operations
- CLI Commands

## Phase 4: Performance Testing (🔄 Pending)

Performance and stress tests:
- Load Testing (concurrent processing)
- Memory Usage
- Cache Performance

## Phase 5: End-to-End Testing (🔄 Pending)

Full system tests with real data:
- Real vocabulary processing
- System recovery
- User scenarios

## Running Tests

### Prerequisites
```bash
pip install pytest pytest-asyncio pytest-cov pytest-benchmark
```

### Run all tests
```bash
pytest tests/ -v
```

### Run specific phase
```bash
pytest tests/unit/phase1/ -v
```

### Run with coverage
```bash
pytest tests/ --cov=flashcard_pipeline --cov-report=html
```

### Run specific test file
```bash
pytest tests/unit/phase1/test_models_validation.py -v
```

## Test Guidelines

1. **Mock External Dependencies** - Never make real API calls in tests
2. **Use Fixtures** - Leverage conftest.py fixtures for common data
3. **Test Edge Cases** - Include boundary conditions and error scenarios
4. **Clear Test Names** - Use descriptive test function names
5. **Isolated Tests** - Each test should be independent

## Coverage Goals

- Phase 1-3: 90%+ coverage for tested components
- Phase 4: Performance baselines established
- Phase 5: Critical user paths validated