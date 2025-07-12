# CLI Module

Command-line interface for the Korean Language Flashcard Pipeline.

## Overview

This module provides a comprehensive CLI for interacting with the flashcard pipeline system, including:
- Processing vocabulary files
- Managing database operations
- Monitoring system health
- Exporting flashcards

## Commands

### Main Commands
- `process` - Process vocabulary input files
- `import` - Import vocabulary from CSV
- `export` - Export flashcards to various formats
- `status` - Check system status
- `db` - Database management commands

### Usage Examples

```bash
# Process a CSV file
python -m flashcard_pipeline.cli process input.csv

# Import with options
python -m flashcard_pipeline.cli import data.csv --skip-duplicates --batch-size 50

# Export to Anki
python -m flashcard_pipeline.cli export anki --output deck.apkg

# Check status
python -m flashcard_pipeline.cli status

# Database operations
python -m flashcard_pipeline.cli db migrate
python -m flashcard_pipeline.cli db backup
```

## Implementation Structure

- **`__init__.py`** - CLI entry point and command registration
- **`commands.py`** - Main command implementations
- **`utils.py`** - CLI utilities and helpers
- **`progress.py`** - Progress bars and status displays

## Features

1. **Interactive Progress**
   - Real-time progress bars
   - Detailed status updates
   - Error reporting

2. **Batch Operations**
   - Process multiple files
   - Configurable batch sizes
   - Resume interrupted operations

3. **Configuration**
   - Environment variables
   - Config files
   - Command-line overrides

## Development

### Adding New Commands

1. Create command function in `commands.py`
2. Use Click decorators for options
3. Register in `__init__.py`
4. Add help documentation

### CLI Best Practices

- Provide clear help text
- Use consistent option names
- Show progress for long operations
- Handle errors gracefully
- Provide useful output