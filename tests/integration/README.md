# Integration Tests

Integration tests that verify multiple components work correctly together.

## Overview

Integration tests focus on the interactions between components, ensuring they integrate properly while still using some mocks for external services like APIs.

## Test Categories

### Component Integration
Tests that verify two or more internal components work together:
- Cache + Rate Limiter
- Database + Validation
- Pipeline stages
- Import + Database

### API Integration (Mocked)
Tests that verify API client integration with other components:
- API Client + Cache
- API Client + Circuit Breaker
- API Client + Rate Limiter

### Database Integration
Tests using real database operations:
- Transaction handling
- Concurrent access
- Migration execution
- Data integrity

## Test Structure

```
integration/
├── test_cache_with_api.py      # Cache integration with API client
├── test_pipeline_stages.py      # Pipeline stage integration
├── test_database_operations.py  # Database with validation
├── test_import_workflow.py      # Import process integration
└── test_concurrent_pipeline.py  # Concurrent processing
```

## Writing Integration Tests

### Example: Cache + API Integration
```python
@pytest.mark.asyncio
async def test_api_client_uses_cache():
    # Setup
    cache = Cache()
    api_client = APIClient(cache=cache)
    
    # First call - should hit API (mocked)
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.return_value.json.return_value = {"result": "data"}
        result1 = await api_client.get_data("key")
    
    # Second call - should use cache
    result2 = await api_client.get_data("key")
    
    # Verify
    assert result1 == result2
    assert mock_post.call_count == 1  # Only called once
    assert cache.hits == 1
```

### Example: Pipeline Integration
```python
@pytest.mark.asyncio
async def test_pipeline_processes_vocabulary():
    # Setup components
    db = DatabaseManager(":memory:")
    await db.initialize()
    
    pipeline = Pipeline(
        db_manager=db,
        api_client=MockAPIClient(),
        cache=Cache()
    )
    
    # Test data
    vocab_items = [
        VocabularyItem(korean="안녕", english="hello"),
        VocabularyItem(korean="감사", english="thanks")
    ]
    
    # Process
    results = await pipeline.process(vocab_items)
    
    # Verify
    assert len(results) == 2
    assert all(r.success for r in results)
    
    # Check database
    stored = await db.get_all_vocabulary()
    assert len(stored) == 2
```

## Best Practices

1. **Use Test Database** - Never use production data
2. **Mock External Services** - Don't make real API calls
3. **Test Realistic Scenarios** - Use representative data
4. **Verify Side Effects** - Check database state, cache state
5. **Clean Up** - Reset state between tests

## Common Integration Points

### Database + Components
- Validation before insert
- Transaction rollbacks
- Concurrent access
- Connection pooling

### Pipeline Integration
- Stage transitions
- Error propagation
- Partial success handling
- Progress tracking

### Import/Export Integration
- File parsing + validation
- Batch processing + database
- Error collection
- Progress reporting

## Running Integration Tests

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run specific test file
pytest tests/integration/test_pipeline_stages.py -v

# Run with real database (slower)
TEST_DB=test.db pytest tests/integration/

# Run with logging
pytest tests/integration/ -v -s --log-cli-level=INFO
```

## Performance Considerations

Integration tests are slower than unit tests:
- Use in-memory databases when possible
- Share expensive fixtures with `scope="session"`
- Run in parallel with `pytest-xdist`
- Mark slow tests with `@pytest.mark.slow`

## Debugging Integration Tests

1. **Enable Logging** - See component interactions
2. **Use Debugger** - Set breakpoints at integration points
3. **Check State** - Verify database/cache state
4. **Isolate Components** - Test pairs before full integration