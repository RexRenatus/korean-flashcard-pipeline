# Comprehensive Testing Plan for Korean Flashcard Pipeline

## Overview

This document outlines a phased testing approach for the Korean Flashcard Pipeline, ensuring each component works correctly before integration. The plan covers unit tests, integration tests, performance tests, and end-to-end validation.

## Testing Philosophy

1. **Test Without API First**: Use mock data to validate logic
2. **Incremental Complexity**: Start simple, add complexity gradually
3. **Component Isolation**: Test each component independently
4. **Integration Validation**: Verify components work together
5. **Performance Benchmarking**: Measure and optimize

## Phase 1: Foundation Testing (Week 1)

### 1.1 Model Validation Tests
**Objective**: Ensure data models correctly parse and validate input

```python
# test_models_validation.py
def test_vocabulary_item_parsing():
    """Test VocabularyItem handles various CSV formats"""
    # Test cases:
    # - Standard format (Hangul, Position, Word_Type)
    # - Legacy format (term, position, type)
    # - Missing fields
    # - Invalid data types
    
def test_stage1_response_structure():
    """Validate Stage1Response model"""
    # - Required fields present
    # - Optional fields handled
    # - Nested structures valid
    
def test_flashcard_row_generation():
    """Test FlashcardRow creation"""
    # - All fields populated
    # - Defaults applied correctly
    # - Validation rules enforced
```

### 1.2 Configuration System Tests
**Objective**: Verify configuration loading and precedence

```python
# test_configuration.py
def test_config_loading_hierarchy():
    """Test configuration precedence"""
    # Order: CLI args > ENV > File > Defaults
    
def test_environment_variable_loading():
    """Ensure .env files load correctly"""
    # - API key loading
    # - Override behavior
    # - Missing file handling
    
def test_config_validation():
    """Validate configuration constraints"""
    # - Rate limits within bounds
    # - File paths valid
    # - Required fields present
```

### 1.3 Error Handling Tests
**Objective**: Ensure graceful error handling

```python
# test_error_handling.py
def test_structured_errors():
    """Test CLIError system"""
    # - Error codes consistent
    # - Categories meaningful
    # - JSON output format
    
def test_error_recovery():
    """Test error recovery mechanisms"""
    # - Retry logic
    # - Circuit breaker behavior
    # - User-friendly messages
```

## Phase 2: Component Testing (Week 2)

### 2.1 Cache Service Tests
**Objective**: Validate caching logic without external dependencies

```python
# test_cache_service.py
def test_cache_operations():
    """Test basic cache operations"""
    # - Store and retrieve
    # - TTL enforcement
    # - Key generation
    
def test_cache_invalidation():
    """Test cache cleanup"""
    # - Size limits
    # - Expired entries
    # - Manual clearing
    
def test_cache_statistics():
    """Verify cache metrics"""
    # - Hit/miss tracking
    # - Size calculation
    # - Performance impact
```

### 2.2 Rate Limiter Tests
**Objective**: Ensure rate limiting works correctly

```python
# test_rate_limiter.py
def test_token_bucket():
    """Test token bucket algorithm"""
    # - Token consumption
    # - Refill rate
    # - Burst capacity
    
def test_distributed_rate_limiting():
    """Test thread-safe operations"""
    # - Concurrent access
    # - Fair distribution
    # - No race conditions
```

### 2.3 Circuit Breaker Tests
**Objective**: Validate failure protection

```python
# test_circuit_breaker.py
def test_circuit_states():
    """Test state transitions"""
    # - Closed → Open on failures
    # - Open → Half-Open after timeout
    # - Half-Open → Closed on success
    
def test_failure_counting():
    """Test failure threshold"""
    # - Accurate counting
    # - Reset on success
    # - Timeout behavior
```

## Phase 3: Integration Testing (Week 3)

### 3.1 Mock API Integration Tests
**Objective**: Test full pipeline with mock API

```python
# test_mock_pipeline_integration.py
class MockOpenRouterClient:
    """Mock API client for testing"""
    async def process_stage1(self, item):
        # Return consistent mock data
        
    async def process_stage2(self, stage1_result):
        # Return mock flashcard

def test_sequential_processing():
    """Test single-threaded pipeline"""
    # - Item flows through stages
    # - Results ordered correctly
    # - Errors handled gracefully
    
def test_concurrent_processing():
    """Test multi-threaded pipeline"""
    # - Order preservation
    # - Rate limit compliance
    # - Progress tracking
```

### 3.2 Database Integration Tests
**Objective**: Verify database operations

```python
# test_database_integration.py
def test_migration_system():
    """Test database migrations"""
    # - Fresh database setup
    # - Migration ordering
    # - Rollback capability
    
def test_batch_writing():
    """Test batch database writes"""
    # - Transaction handling
    # - Order preservation
    # - Error recovery
    
def test_query_performance():
    """Benchmark database queries"""
    # - Index effectiveness
    # - Batch size optimization
    # - Connection pooling
```

### 3.3 CLI Integration Tests
**Objective**: Test command-line interface

```python
# test_cli_integration.py
def test_basic_commands():
    """Test core CLI commands"""
    # - init, config, process
    # - Argument parsing
    # - Output formatting
    
def test_advanced_features():
    """Test complex CLI features"""
    # - Filtering
    # - Presets
    # - Progress display
    
def test_error_reporting():
    """Test CLI error handling"""
    # - User-friendly messages
    # - Exit codes
    # - Debug information
```

## Phase 4: Performance Testing (Week 4)

### 4.1 Load Testing
**Objective**: Determine system limits

```python
# test_performance_load.py
def test_concurrent_limits():
    """Find optimal concurrency"""
    # Test with: 1, 5, 10, 20, 50 workers
    # Measure:
    # - Throughput (items/second)
    # - Memory usage
    # - Error rates
    
def test_large_batches():
    """Test with large datasets"""
    # - 1,000 items
    # - 10,000 items
    # - Memory efficiency
```

### 4.2 Stress Testing
**Objective**: Test failure scenarios

```python
# test_performance_stress.py
def test_api_failures():
    """Simulate API errors"""
    # - Random failures
    # - Timeout scenarios
    # - Rate limit hits
    
def test_resource_exhaustion():
    """Test system limits"""
    # - Memory pressure
    # - Disk space limits
    # - Database locks
```

### 4.3 Optimization Testing
**Objective**: Identify bottlenecks

```python
# test_performance_optimization.py
def profile_processing_pipeline():
    """Profile code execution"""
    # - CPU hotspots
    # - Memory allocations
    # - I/O wait times
    
def benchmark_cache_impact():
    """Measure cache effectiveness"""
    # - Hit rates
    # - Performance gains
    # - Memory trade-offs
```

## Phase 5: End-to-End Testing (Week 5)

### 5.1 Real Data Testing
**Objective**: Validate with actual vocabulary

```python
# test_e2e_real_data.py
def test_korean_vocabulary_processing():
    """Process real Korean words"""
    # Use 10K_HSK_List.csv
    # - First 10 words (smoke test)
    # - First 100 words (validation)
    # - First 1000 words (performance)
    
def test_data_quality():
    """Validate output quality"""
    # - All fields populated
    # - Encoding correct
    # - Format consistency
```

### 5.2 System Integration Testing
**Objective**: Test full system deployment

```python
# test_e2e_system.py
def test_fresh_installation():
    """Test from clean state"""
    # - Initialize database
    # - Configure system
    # - Process batch
    # - Export results
    
def test_resume_capability():
    """Test interruption recovery"""
    # - Start processing
    # - Interrupt mid-batch
    # - Resume from checkpoint
    # - Verify completeness
```

### 5.3 User Acceptance Testing
**Objective**: Validate user experience

```yaml
# test_scenarios.yaml
scenarios:
  - name: "First Time User"
    steps:
      - Initialize configuration
      - Process small batch
      - View results
      - Export to Anki
      
  - name: "Power User"
    steps:
      - Custom configuration
      - Large batch processing
      - Monitor performance
      - Optimize settings
      
  - name: "Error Recovery"
    steps:
      - Simulate failures
      - Follow error messages
      - Apply fixes
      - Verify recovery
```

## Test Execution Strategy

### 1. Test Environment Setup
```bash
# Create test environment
python -m venv test_env
source test_env/bin/activate
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov pytest-benchmark

# Set up test database
export TEST_DATABASE_PATH="test_pipeline.db"
export TEST_CACHE_PATH=".test_cache"
```

### 2. Test Execution Order
```bash
# Phase 1: Foundation
pytest tests/unit/test_models_validation.py -v
pytest tests/unit/test_configuration.py -v
pytest tests/unit/test_error_handling.py -v

# Phase 2: Components
pytest tests/unit/test_cache_service.py -v
pytest tests/unit/test_rate_limiter.py -v
pytest tests/unit/test_circuit_breaker.py -v

# Phase 3: Integration
pytest tests/integration/test_mock_pipeline.py -v
pytest tests/integration/test_database.py -v
pytest tests/integration/test_cli.py -v

# Phase 4: Performance
pytest tests/performance/test_load.py -v --benchmark-only
pytest tests/performance/test_stress.py -v
pytest tests/performance/test_optimization.py -v --profile

# Phase 5: End-to-End
pytest tests/e2e/test_real_data.py -v -s
pytest tests/e2e/test_system.py -v
pytest tests/e2e/test_user_acceptance.py -v
```

### 3. Continuous Integration
```yaml
# .github/workflows/test.yml
name: Pipeline Tests
on: [push, pull_request]

jobs:
  test:
    strategy:
      matrix:
        python: [3.9, 3.10, 3.11, 3.12]
        os: [ubuntu-latest, windows-latest, macos-latest]
    
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --cov=flashcard_pipeline
```

## Success Criteria

### Phase 1: Foundation ✓
- [ ] All models parse CSV correctly
- [ ] Configuration system works as designed
- [ ] Errors are informative and actionable

### Phase 2: Components ✓
- [ ] Cache improves performance by >50%
- [ ] Rate limiter prevents API throttling
- [ ] Circuit breaker protects against cascading failures

### Phase 3: Integration ✓
- [ ] Mock pipeline processes 1000 items without errors
- [ ] Database handles concurrent writes
- [ ] CLI provides good user experience

### Phase 4: Performance ✓
- [ ] System handles 50 concurrent requests
- [ ] Memory usage < 500MB for 10K items
- [ ] Processing rate > 10 items/second

### Phase 5: End-to-End ✓
- [ ] Real vocabulary processes correctly
- [ ] System recovers from failures
- [ ] Users can complete all scenarios

## Troubleshooting Guide

### Common Issues and Fixes

1. **Import Errors**
   - Ensure PYTHONPATH includes src/python
   - Check virtual environment activation
   - Verify all dependencies installed

2. **Database Errors**
   - Run migrations first
   - Check file permissions
   - Ensure SQLite version > 3.35

3. **API Mock Failures**
   - Verify mock data structure
   - Check async/await usage
   - Ensure consistent return types

4. **Performance Issues**
   - Profile with cProfile
   - Check database indexes
   - Monitor memory usage
   - Optimize batch sizes

## Next Steps

1. **Implement Missing Tests**
   - Create test files following the plan
   - Add fixtures for common data
   - Set up test utilities

2. **Fix Current Issues**
   - Resolve `set_progress_callback` error
   - Ensure all models handle HSK CSV format
   - Validate concurrent processing

3. **Document Results**
   - Create test coverage report
   - Document performance benchmarks
   - Update user guide with findings

---

This comprehensive testing plan ensures the Korean Flashcard Pipeline is robust, performant, and user-friendly. Each phase builds on the previous, creating confidence in the system's reliability.