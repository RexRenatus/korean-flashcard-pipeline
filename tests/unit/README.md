# Unit Tests

Unit tests for individual components of the flashcard pipeline system.

## Overview

This directory contains unit tests organized by testing phase. Each phase builds upon the previous, ensuring comprehensive coverage of all system components.

## Structure

```
unit/
├── phase1/     # Foundation tests (models, config, errors)
├── phase2/     # Component tests (cache, rate limiter, etc.)
├── phase3/     # Integration component tests
├── phase4/     # Performance unit tests
└── intelligent_assistant/  # AI assistant specific tests
```

## Phase Organization

### Phase 1: Foundation Testing ✅
Tests for core data structures and basic functionality:
- Data models and validation
- Configuration management
- Error handling framework
- Basic utilities

### Phase 2: Component Testing ✅
Tests for individual service components:
- Cache service operations
- Rate limiting algorithms
- Circuit breaker patterns
- API client (mocked)

### Phase 3: Integration Components 🚧
Tests for components that integrate multiple services:
- Database operations
- Pipeline stages
- Import/export functions

### Phase 4: Performance Units 🚧
Performance tests for individual components:
- Algorithm efficiency
- Memory usage patterns
- Cache performance

## Writing Unit Tests

### Test Isolation
Each unit test should:
- Test a single unit of functionality
- Not depend on external services
- Use mocks for dependencies
- Run quickly (<100ms)

### Example Structure
```python
class TestVocabularyModel:
    """Test VocabularyItem model validation and behavior"""
    
    def test_valid_vocabulary_creation(self):
        """Test creating vocabulary with valid data"""
        vocab = VocabularyItem(
            korean="안녕",
            english="hello",
            type="word"
        )
        assert vocab.korean == "안녕"
        assert vocab.is_valid()
    
    def test_validation_rejects_empty_korean(self):
        """Test that empty Korean term is rejected"""
        with pytest.raises(ValidationError):
            VocabularyItem(korean="", english="hello")
```

## Best Practices

1. **One Assertion Per Test** - Keep tests focused
2. **Descriptive Names** - Test name should describe what's being tested
3. **Use Fixtures** - Share common test data via fixtures
4. **Mock External Dependencies** - Never call real services
5. **Test Edge Cases** - Empty, null, boundary values

## Running Unit Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific phase
pytest tests/unit/phase1/ -v

# Run with coverage
pytest tests/unit/ --cov=flashcard_pipeline

# Run specific test class
pytest tests/unit/phase1/test_models_validation.py::TestVocabularyModel -v
```

## Coverage Goals

- Phase 1: 95%+ (foundation must be solid)
- Phase 2: 90%+ (core components)
- Phase 3: 85%+ (integration points)
- Phase 4: Baseline metrics established