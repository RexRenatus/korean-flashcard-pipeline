# Exporters Module

Export functionality for converting flashcards to various formats.

## Overview

This module provides exporters for different flashcard platforms and formats, allowing users to use generated flashcards in their preferred study applications.

## Supported Formats

### Currently Implemented
- **Anki** - `.apkg` format with media support
- **CSV** - Simple spreadsheet format
- **JSON** - Structured data format
- **Markdown** - Human-readable documentation

### Planned
- **Quizlet** - Direct API integration
- **Memrise** - Course format
- **PDF** - Printable flashcards
- **HTML** - Web-based study

## Architecture

```
exporters/
├── __init__.py          # Base exporter class and registry
├── anki_exporter.py     # Anki package exporter
├── csv_exporter.py      # CSV file exporter
├── json_exporter.py     # JSON format exporter
├── markdown_exporter.py # Markdown documentation
└── templates/           # Export templates
```

## Base Exporter Interface

All exporters implement this interface:

```python
class BaseExporter:
    async def export(self, flashcards: List[Flashcard], output_path: str) -> ExportResult:
        """Export flashcards to the target format"""
        
    async def validate(self, flashcards: List[Flashcard]) -> ValidationResult:
        """Validate flashcards before export"""
        
    def get_supported_features(self) -> List[str]:
        """Return list of supported features"""
```

## Usage Examples

```python
# Export to Anki
from flashcard_pipeline.exporters import AnkiExporter

exporter = AnkiExporter()
result = await exporter.export(
    flashcards=cards,
    output_path="korean_deck.apkg",
    deck_name="Korean Vocabulary"
)

# Export to CSV
from flashcard_pipeline.exporters import CSVExporter

exporter = CSVExporter()
await exporter.export(
    flashcards=cards,
    output_path="flashcards.csv",
    include_headers=True
)

# Batch export to multiple formats
from flashcard_pipeline.exporters import export_all_formats

results = await export_all_formats(
    flashcards=cards,
    formats=["anki", "csv", "json"],
    output_dir="exports/"
)
```

## Format-Specific Features

### Anki Exporter
- Supports custom note types
- Includes audio pronunciation
- Handles images and media
- Preserves tags and metadata
- Configurable card templates

### CSV Exporter
- Configurable column mapping
- Multiple encoding support
- Custom delimiters
- Header customization

### JSON Exporter
- Pretty printing option
- Schema validation
- Nested structure support
- Metadata inclusion

### Markdown Exporter
- Multiple layout templates
- Table of contents generation
- Difficulty-based sections
- Study guide format

## Configuration

Each exporter can be configured:

```python
config = {
    "anki": {
        "note_type": "Korean Enhanced",
        "include_audio": True,
        "card_css": "custom.css"
    },
    "csv": {
        "encoding": "utf-8",
        "delimiter": ",",
        "columns": ["korean", "english", "notes"]
    }
}

exporter = AnkiExporter(config["anki"])
```

## Error Handling

Exporters handle common issues:
- Missing required fields
- Invalid characters for format
- File system errors
- Memory constraints for large exports

## Best Practices

1. **Validate before export** to catch issues early
2. **Use streaming for large datasets** to manage memory
3. **Provide progress callbacks** for long exports
4. **Handle partial exports** gracefully
5. **Test with various character sets** (Korean, English, special chars)