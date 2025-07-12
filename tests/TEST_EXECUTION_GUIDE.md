# Test Execution Guide

**Last Updated**: 2025-01-08

This guide provides comprehensive instructions for running tests in the Korean Flashcard Pipeline project.

## 📁 Test Directory Structure

```
tests/
├── conftest.py               # Shared pytest fixtures and configuration
├── run_tests.sh             # Main test runner script (all tests)
├── run_tests_mock.py        # Mock API test runner
├── test_pipeline_integration.py  # Pipeline integration tests
├── test_simple.py           # Simple test cases
├── README.md                # Test suite overview
├── TEST_EXECUTION_GUIDE.md  # This file
├── PHASE4_TEST_RESULTS.md   # Phase 4 test results
│
├── data/                    # Test data directory
│   ├── cache/              # Test cache directory
│   ├── input/              # Input test files
│   ├── output/             # Output test files
│   ├── mock_api_responses.json  # Mock API responses
│   ├── test_5_words.csv    # Small test vocabulary
│   └── test_vocabulary.csv # Full test vocabulary
│
├── fixtures/               # Additional test fixtures
│   └── sample_vocabulary.csv
│
├── unit/                   # Unit tests by phase
│   ├── __init__.py
│   ├── phase1/            # Foundation tests
│   │   ├── __init__.py
│   │   ├── run_phase1_tests.py
│   │   ├── test_configuration.py
│   │   ├── test_error_handling.py
│   │   └── test_models_validation.py
│   │
│   └── phase2/            # Component tests
│       ├── __init__.py
│       ├── run_phase2_tests.py
│       ├── test_api_client_mock.py
│       ├── test_cache_service.py
│       ├── test_circuit_breaker.py
│       └── test_rate_limiter.py
│
├── integration/           # Integration tests
│   ├── test_concurrent_pipeline.py
│   ├── test_concurrent_simple.py
│   ├── test_end_to_end.py
│   └── test_full_pipeline.py
│
├── python/               # Python component tests
│   ├── test_api_client.py
│   ├── test_cache_service.py
│   ├── test_circuit_breaker.py
│   ├── test_concurrent_processing.py
│   ├── test_models.py
│   └── test_rate_limiter.py
│
└── rust/                # Rust component tests (placeholder)
    ├── test_cache_manager.rs
    ├── test_database_repositories.rs
    ├── test_models.rs
    └── test_python_bridge.rs
```

## 🚀 Quick Start

### Prerequisites

1. **Python Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

2. **Environment Variables**:
   ```bash
   # Create test environment file
   cp .env.example .env.test
   # Edit .env.test with your test configuration
   ```

3. **Test Dependencies**:
   ```bash
   pip install pytest pytest-asyncio pytest-cov pytest-benchmark pytest-mock
   ```

## 🧪 Running Tests

### 1. Run All Tests
```bash
# Using the main test runner script
./tests/run_tests.sh

# Or using pytest directly
pytest tests/ -v
```

### 2. Run Tests by Phase

#### Phase 1: Foundation Tests
```bash
# Using phase runner
python tests/unit/phase1/run_phase1_tests.py

# Or directly with pytest
pytest tests/unit/phase1/ -v
```

#### Phase 2: Component Tests
```bash
# Using phase runner
python tests/unit/phase2/run_phase2_tests.py

# Or directly with pytest
pytest tests/unit/phase2/ -v
```

### 3. Run Specific Test Categories

#### Unit Tests Only
```bash
pytest tests/unit/ -v -m "unit"
```

#### Integration Tests Only
```bash
pytest tests/integration/ -v -m "integration"
```

#### Python Component Tests
```bash
pytest tests/python/ -v
```

### 4. Run Individual Test Files
```bash
# Specific test file
pytest tests/unit/phase1/test_models_validation.py -v

# Specific test function
pytest tests/unit/phase1/test_models_validation.py::test_vocabulary_item_validation -v

# Tests matching pattern
pytest tests/ -k "test_cache" -v
```

### 5. Run with Mock API
```bash
# Use mock responses instead of real API calls
python tests/run_tests_mock.py
```

## 📊 Test Coverage

### Generate Coverage Report
```bash
# HTML coverage report
pytest tests/ --cov=flashcard_pipeline --cov-report=html
open htmlcov/index.html  # On Windows: start htmlcov/index.html

# Terminal coverage report
pytest tests/ --cov=flashcard_pipeline --cov-report=term-missing

# XML coverage (for CI)
pytest tests/ --cov=flashcard_pipeline --cov-report=xml
```

### Coverage by Component
```bash
# API Client coverage
pytest tests/python/test_api_client.py --cov=flashcard_pipeline.api_client

# Cache Service coverage
pytest tests/python/test_cache_service.py --cov=flashcard_pipeline.cache

# Rate Limiter coverage
pytest tests/python/test_rate_limiter.py --cov=flashcard_pipeline.rate_limiter
```

## 🎯 Test Markers

The project uses pytest markers to categorize tests:

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (slower, may use real components)
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.asyncio` - Asynchronous tests

### Running Tests by Marker
```bash
# Run only unit tests
pytest -m "unit" -v

# Run all except slow tests
pytest -m "not slow" -v

# Run only async tests
pytest -m "asyncio" -v
```

## 🔧 Test Configuration

### pytest.ini Configuration
Located at project root, configures:
- Test paths
- Python path for imports
- Coverage settings
- Test markers
- Environment files

### conftest.py Fixtures
Provides shared test fixtures:
- `temp_dir` - Temporary directory for tests
- `mock_env` - Mock environment variables
- `sample_vocabulary_items` - Test vocabulary data
- `sample_stage1_response` - Mock API responses
- `sample_flashcard_rows` - Test flashcard data
- `sample_config` - Test configuration
- `mock_api_responses` - Mock API response data

## 🐛 Debugging Tests

### Verbose Output
```bash
# Show detailed test output
pytest tests/ -vv

# Show print statements
pytest tests/ -s

# Show full traceback
pytest tests/ --tb=long
```

### Debug Specific Failures
```bash
# Stop on first failure
pytest tests/ -x

# Drop to PDB on failure
pytest tests/ --pdb

# Run last failed tests
pytest tests/ --lf

# Run failed tests first
pytest tests/ --ff
```

### Test Timing
```bash
# Show test durations
pytest tests/ --durations=10

# Profile slow tests
pytest tests/ --profile
```

## 📝 Writing New Tests

### Test File Naming
- Unit tests: `test_<component>.py`
- Integration tests: `test_<scenario>_integration.py`
- End-to-end tests: `test_e2e_<feature>.py`

### Test Function Naming
```python
def test_<component>_<scenario>_<expected_result>():
    """Test that <component> <does something> when <condition>."""
    pass
```

### Using Fixtures
```python
def test_api_client_with_mock_response(mock_api_responses, sample_config):
    """Test API client handles mock responses correctly."""
    client = APIClient(config=sample_config)
    # Use fixtures in test...
```

## 🔄 Continuous Integration

The test suite is integrated with CI/CD:

1. **Pre-commit Hooks**: Run fast unit tests
2. **PR Checks**: Run all unit and integration tests
3. **Main Branch**: Run full test suite with coverage
4. **Nightly**: Run extended test suite with performance tests

## ⚡ Performance Considerations

### Test Execution Time Goals
- Unit tests: < 0.1s per test
- Integration tests: < 1s per test
- End-to-end tests: < 5s per test
- Full suite: < 2 minutes

### Optimizing Test Speed
1. Use fixtures to avoid repeated setup
2. Mock external dependencies
3. Use pytest-xdist for parallel execution:
   ```bash
   pytest tests/ -n auto
   ```

## 🚨 Common Issues and Solutions

### Import Errors
```bash
# Ensure Python path is set
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src/python"
```

### Missing Dependencies
```bash
# Install all test dependencies
pip install -r requirements-dev.txt
```

### Cache Conflicts
```bash
# Clear test cache
rm -rf tests/data/cache/*
rm -rf .pytest_cache
```

### Environment Variables
```bash
# Verify test environment
python -c "from flashcard_pipeline.cli.config import load_config; print(load_config())"
```

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Python Testing Best Practices](https://realpython.com/pytest-python-testing/)
- Project-specific test patterns in `/docs/TESTING_PATTERNS.md`