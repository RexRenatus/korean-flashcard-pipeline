# Dependency Management Evaluation

## Current State
The project currently uses `requirements.txt` for dependency management.

## Options Evaluated

### 1. Poetry
**Pros:**
- Modern dependency resolver
- Lock files for reproducible builds
- Built-in virtual environment management
- Separate dev dependencies
- Publishing to PyPI support
- Semantic versioning support

**Cons:**
- Additional tool to install
- Learning curve for team members
- May conflict with existing pip workflows

### 2. Pipenv
**Pros:**
- Official Python packaging recommendation
- Pipfile and Pipfile.lock
- Automatic virtual environment
- Security vulnerability scanning

**Cons:**
- Slower dependency resolution
- Less active development recently
- Some compatibility issues reported

### 3. pip-tools
**Pros:**
- Minimal change from current workflow
- Generates requirements.txt from requirements.in
- Pin exact versions with pip-compile
- Works with existing pip

**Cons:**
- Less features than Poetry
- Manual virtual environment management

## Recommendation: Poetry

### Why Poetry?
1. **Better dependency resolution** - Handles complex dependency trees
2. **Lock files** - Ensures exact same versions across all environments
3. **Groups** - Separate dev, test, and optional dependencies
4. **Modern tooling** - Active development and community

### Migration Plan

1. **Install Poetry**
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Initialize Poetry**
   ```bash
   poetry init
   poetry add $(cat requirements.txt)
   ```

3. **Create pyproject.toml**
   ```toml
   [tool.poetry]
   name = "flashcard-pipeline"
   version = "2.0.0"
   description = "AI-powered Korean flashcard generation"
   authors = ["Your Name <email@example.com>"]
   
   [tool.poetry.dependencies]
   python = "^3.9"
   httpx = "^0.24.0"
   pydantic = "^2.0.0"
   typer = "^0.9.0"
   rich = "^13.0.0"
   # ... other dependencies
   
   [tool.poetry.group.dev.dependencies]
   pytest = "^7.0.0"
   black = "^23.0.0"
   ruff = "^0.1.0"
   mypy = "^1.0.0"
   
   [build-system]
   requires = ["poetry-core"]
   build-backend = "poetry.core.masonry.api"
   ```

4. **Update documentation**
   ```bash
   # Old way
   pip install -r requirements.txt
   
   # New way
   poetry install
   ```

5. **Keep requirements.txt for compatibility**
   ```bash
   poetry export -f requirements.txt --output requirements.txt
   ```

### Benefits for This Project
1. **Reproducible builds** - Critical for production deployment
2. **Dependency groups** - Separate CLI, API, testing dependencies
3. **Version constraints** - Better handling of OpenRouter/httpx updates
4. **Virtual env integration** - Simplifies development setup

### Timeline
- Week 1: Set up Poetry in development
- Week 2: Migrate dependencies and test
- Week 3: Update CI/CD pipelines
- Week 4: Update documentation and train team