# Developer Documentation

Comprehensive guide for developers contributing to the Korean Language Flashcard Pipeline project.

## Quick Start

### Prerequisites
- Python 3.8+ (3.11 recommended)
- Rust 1.70+ (for future components)
- Git
- SQLite3

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/YourUsername/Anthropic_Flashcards.git
cd Anthropic_Flashcards

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests to verify setup
pytest tests/
```

## Development Workflow

### 1. Create Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes
- Write code following our [Code Style Guide](./CODE_STYLE.md)
- Add tests for new functionality
- Update documentation

### 3. Test Your Changes
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_models.py

# Run with coverage
pytest --cov=flashcard_pipeline --cov-report=html

# Run linters
black src/
flake8 src/
mypy src/
```

### 4. Commit Changes
```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: Add Korean pronunciation validation

- Add pronunciation field validation
- Support both Hangul and romanization
- Include tests for edge cases"
```

### 5. Push and Create PR
```bash
git push origin feature/your-feature-name
# Then create PR on GitHub
```

## Project Structure

```
.
├── src/                    # Source code
│   ├── python/            # Python implementation
│   │   └── flashcard_pipeline/
│   └── rust/              # Rust implementation (planned)
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── e2e/              # End-to-end tests
├── docs/                  # Documentation
├── scripts/               # Utility scripts
├── migrations/            # Database migrations
└── examples/              # Usage examples
```

## Code Standards

### Python Code Style
- Follow PEP 8
- Use Black for formatting
- Type hints required for all functions
- Docstrings for all public methods

### Example:
```python
from typing import Optional, List

def process_vocabulary(
    items: List[VocabularyItem], 
    options: Optional[ProcessOptions] = None
) -> List[Flashcard]:
    """
    Process vocabulary items into flashcards.
    
    Args:
        items: List of vocabulary items to process
        options: Optional processing configuration
        
    Returns:
        List of generated flashcards
        
    Raises:
        ValidationError: If items contain invalid data
        ProcessingError: If processing fails
    """
    # Implementation
```

### Commit Messages
Follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Test additions/changes
- `chore:` Build process or auxiliary tool changes

## Testing

### Test Organization
- Unit tests: Test individual components
- Integration tests: Test component interactions
- E2E tests: Test complete workflows

### Writing Tests
```python
import pytest
from flashcard_pipeline.models import VocabularyItem

class TestVocabularyItem:
    def test_valid_creation(self):
        """Test creating vocabulary with valid data."""
        item = VocabularyItem(
            korean="안녕하세요",
            english="Hello",
            type="phrase"
        )
        assert item.korean == "안녕하세요"
        
    def test_validation_error(self):
        """Test validation rejects empty Korean."""
        with pytest.raises(ValidationError):
            VocabularyItem(korean="", english="Hello")
```

### Test Coverage
- Maintain >85% code coverage
- Focus on critical paths
- Test error cases

## Debugging

### Logging
```python
import logging
logger = logging.getLogger(__name__)

# Use appropriate log levels
logger.debug("Detailed information for debugging")
logger.info("General information")
logger.warning("Warning messages")
logger.error("Error messages")
```

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with Python debugger
python -m pdb scripts/process_vocabulary.py
```

## Documentation

### Code Documentation
- Docstrings for all public APIs
- Type hints for clarity
- Comments for complex logic

### User Documentation
- Update relevant user guides
- Include examples
- Keep language simple

## Common Tasks

### Adding a New Feature
1. Create issue describing feature
2. Design API/interface
3. Write tests first (TDD)
4. Implement feature
5. Update documentation
6. Submit PR

### Fixing a Bug
1. Create failing test
2. Fix the bug
3. Verify test passes
4. Check for related issues
5. Submit PR with test

### Performance Optimization
1. Profile to find bottleneck
2. Benchmark current performance
3. Implement optimization
4. Verify improvement
5. Document changes

## Resources

### Internal Resources
- [Architecture Documentation](../architecture/)
- [API Documentation](../api/)
- [Implementation Guides](../implementation/)

### External Resources
- [Python Packaging Guide](https://packaging.python.org/)
- [Rust Book](https://doc.rust-lang.org/book/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)

## Getting Help

- Check existing issues on GitHub
- Ask in discussions
- Review documentation
- Contact maintainers

## License

This project is licensed under the MIT License. See LICENSE file for details.