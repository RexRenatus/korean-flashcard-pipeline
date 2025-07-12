# Contributing to Korean Flashcard Pipeline

Thank you for your interest in contributing to the Korean Flashcard Pipeline project! This document provides guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Process](#development-process)
- [Submitting Changes](#submitting-changes)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/yourusername/anthropic-flashcards.git
   cd anthropic-flashcards
   ```
3. Set up the development environment:
   ```bash
   # Python setup
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   
   # Rust setup
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   ```

## Development Process

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following our coding standards

3. Write or update tests as needed

4. Update documentation if you're changing functionality

5. Commit your changes with clear, descriptive messages:
   ```bash
   git commit -m "feat: add support for custom flashcard formats"
   ```

## Submitting Changes

1. Push your changes to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Open a Pull Request with:
   - Clear description of changes
   - Reference to any related issues
   - Screenshots/examples if applicable
   - Test results

3. Address any review feedback

## Coding Standards

### Python
- Follow PEP 8
- Use type hints
- Docstrings for all public functions
- Maximum line length: 100 characters

### Rust
- Follow Rust style guidelines
- Use `cargo fmt` before committing
- Run `cargo clippy` and address warnings

### General
- Write clear, self-documenting code
- Add comments for complex logic
- Keep functions focused and small
- Follow SOLID principles

## Testing

- All new features must include tests
- Maintain test coverage above 85%
- Run all tests before submitting PR:
  ```bash
  # Python tests
  pytest
  
  # Rust tests
  cargo test
  ```

## Documentation

- Update README.md for user-facing changes
- Add/update docstrings for new functions
- Update API documentation for endpoint changes
- Include examples where helpful

## Questions?

Feel free to open an issue for:
- Bug reports
- Feature requests
- Questions about the codebase
- Suggestions for improvements

Thank you for contributing!