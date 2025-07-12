# Export System Guide

## Overview

The flashcard pipeline includes a comprehensive export system that supports multiple formats:

1. **TSV (Tab-Separated Values)** - Standard flashcard format
2. **Anki APKG** - Native Anki package format
3. **JSON** - API-friendly structured data
4. **PDF** - Print-ready flashcard layouts

## Architecture

### Core Components

```python
from flashcard_pipeline.export_service import (
    ExportService,      # Main export service
    ExportOptions,      # Export configuration
    ExportResult,       # Export result details
    ExportTemplate      # Reusable templates
)
from flashcard_pipeline.models import ExportFormat
```

### Format Exporters

- `TSVExporter` - Tab-separated values export
- `AnkiExporter` - Anki package generation
- `JSONExporter` - Structured JSON output
- `PDFExporter` - PDF document creation

## Usage

### Basic Export

```python
from flashcard_pipeline.export_service import ExportService, ExportOptions
from flashcard_pipeline.models import ExportFormat

# Initialize service
export_service = ExportService(db_manager)

# Export to TSV
options = ExportOptions(
    format=ExportFormat.TSV,
    output_path="flashcards.tsv"
)
result = await export_service.export_flashcards(options)
```

### Command Line Usage

```bash
# Export all flashcards to TSV
python scripts/export_flashcards.py -f tsv -o flashcards.tsv

# Export specific deck to Anki
python scripts/export_flashcards.py -f anki -o korean.apkg --deck-ids deck123

# Batch export to multiple formats
python scripts/export_flashcards.py -o flashcards --batch tsv json pdf

# Export with filters
python scripts/export_flashcards.py -f json -o vocab.json --tags beginner --status approved
```

## Export Formats

### TSV Export

Tab-separated values format ideal for spreadsheets and bulk imports.

```bash
# Basic TSV export
python scripts/export_flashcards.py -f tsv -o flashcards.tsv

# With custom columns
python scripts/export_flashcards.py -f tsv -o custom.tsv \
    --field-map korean:Question english:Answer tags:Category

# Include header row
python scripts/export_flashcards.py -f tsv -o flashcards.tsv --include-header
```

Output format:
```
Front	Back	Tags	Deck	Primer	HonorificLevel
안녕하세요	Hello (formal)	greeting,formal	Korean Basics	Korean greeting	formal
감사합니다	Thank you	gratitude,formal	Korean Basics	Expression of thanks	formal
```

### Anki Export

Native Anki APKG format with custom note types for Korean learning.

```bash
# Export to Anki package
python scripts/export_flashcards.py -f anki -o korean.apkg

# Filter by deck
python scripts/export_flashcards.py -f anki -o beginner.apkg \
    --deck-names "Korean Basics" "Essential Verbs"
```

Features:
- Custom "Korean Flashcard" note type
- Preserves tags and deck structure
- Korean font styling
- Media file support (future)

### JSON Export

Structured JSON format for APIs and programmatic access.

```bash
# Export to JSON
python scripts/export_flashcards.py -f json -o flashcards.json

# With compression
python scripts/export_flashcards.py -f json -o flashcards.json.gz --compress

# Pretty printed
python scripts/export_flashcards.py -f json -o flashcards.json --pretty
```

Output structure:
```json
{
  "metadata": {
    "export_date": "2025-01-09T10:30:00Z",
    "total_cards": 150,
    "format_version": "1.0"
  },
  "flashcards": [
    {
      "id": 1,
      "front": "안녕하세요",
      "back": "Hello (formal)",
      "deck": "Korean Basics",
      "tags": ["greeting", "formal"],
      "metadata": {
        "primer": "Korean greeting",
        "honorific_level": "formal",
        "position": 1
      }
    }
  ]
}
```

### PDF Export

Print-ready PDF documents with multiple layout options.

```bash
# Export to PDF with default layout
python scripts/export_flashcards.py -f pdf -o flashcards.pdf

# Use specific layout
python scripts/export_flashcards.py -f pdf -o study.pdf --template study_layout

# Compact layout for printing
python scripts/export_flashcards.py -f pdf -o print.pdf --template compact_layout
```

Available layouts:
- **flashcard_layout** - Traditional flashcard format (2 per page)
- **list_layout** - Sequential list format
- **table_layout** - Tabular format
- **study_layout** - Study sheet with examples
- **compact_layout** - Maximum cards per page

## Filtering Options

### By Deck

```bash
# Single deck by ID
python scripts/export_flashcards.py -f tsv -o deck1.tsv --deck-ids 123

# Multiple decks by name
python scripts/export_flashcards.py -f tsv -o decks.tsv \
    --deck-names "Korean Basics" "Essential Verbs"
```

### By Tags

```bash
# Single tag
python scripts/export_flashcards.py -f tsv -o beginner.tsv --tags beginner

# Multiple tags (OR logic)
python scripts/export_flashcards.py -f tsv -o vocab.tsv --tags vocab grammar

# Tag exclusion
python scripts/export_flashcards.py -f tsv -o no_advanced.tsv --exclude-tags advanced
```

### By Status

```bash
# Only approved cards
python scripts/export_flashcards.py -f tsv -o approved.tsv --status approved

# Include unpublished
python scripts/export_flashcards.py -f tsv -o all.tsv --include-unpublished
```

### By Date

```bash
# Created after date
python scripts/export_flashcards.py -f tsv -o recent.tsv \
    --created-after 2025-01-01

# Modified in date range
python scripts/export_flashcards.py -f tsv -o january.tsv \
    --modified-after 2025-01-01 --modified-before 2025-01-31
```

### By Processing Stage

```bash
# Only cards that passed nuance stage
python scripts/export_flashcards.py -f tsv -o nuanced.tsv --stage nuance_complete

# Cards pending flashcard generation
python scripts/export_flashcards.py -f tsv -o pending.tsv --stage flashcard_pending
```

## Custom Field Mapping

Map flashcard fields to custom column names:

```bash
# Simple mapping
python scripts/export_flashcards.py -f tsv -o custom.tsv \
    --field-map front_content:Question back_content:Answer

# Complex mapping
python scripts/export_flashcards.py -f tsv -o custom.tsv \
    --field-map front_content:Q back_content:A tags:Categories \
    deck_name:Subject primer:Hint honorific_level:Formality
```

## Batch Export

Export to multiple formats simultaneously:

```bash
# Export to all formats
python scripts/export_flashcards.py -o flashcards --batch tsv json pdf anki

# Selected formats with options
python scripts/export_flashcards.py -o export_batch \
    --batch tsv json \
    --compress \
    --include-header
```

Creates:
- `export_batch.tsv`
- `export_batch.json.gz`

## Export Templates

### Using Templates

```bash
# List available templates
python scripts/export_flashcards.py --list-templates

# Use a template
python scripts/export_flashcards.py --template beginner_export

# Save current options as template
python scripts/export_flashcards.py -f tsv -o test.tsv \
    --tags beginner --save-template my_template
```

### Creating Templates

Templates are JSON files in `exports/templates/`:

```json
{
  "name": "beginner_export",
  "format": "tsv",
  "options": {
    "include_header": true,
    "tags": ["beginner", "essential"],
    "validation_status": "approved",
    "field_mapping": {
      "front_content": "Korean",
      "back_content": "English"
    }
  }
}
```

## Scheduling Exports

### Cron Examples

```bash
# Daily TSV export at 2 AM
0 2 * * * cd /app && python scripts/export_flashcards.py -f tsv -o daily_export.tsv

# Weekly Anki export on Sundays
0 0 * * 0 cd /app && python scripts/export_flashcards.py -f anki -o weekly.apkg

# Monthly JSON backup
0 0 1 * * cd /app && python scripts/export_flashcards.py -f json -o backup_$(date +%Y%m).json.gz --compress
```

### Automated Exports

```python
# Python script for scheduled exports
import asyncio
from datetime import datetime
from flashcard_pipeline.export_service import ExportService, ExportOptions

async def scheduled_export():
    export_service = ExportService(db_manager)
    
    # Daily TSV export
    options = ExportOptions(
        format=ExportFormat.TSV,
        output_path=f"daily_{datetime.now():%Y%m%d}.tsv",
        validation_status=ValidationStatus.APPROVED
    )
    
    result = await export_service.export_flashcards(options)
    if result.success:
        print(f"Exported {result.total_exported} flashcards")
```

## API Integration

### Export Endpoint Example

```python
from fastapi import FastAPI, Response
from flashcard_pipeline.export_service import ExportService, ExportOptions

app = FastAPI()

@app.get("/export/{format}")
async def export_flashcards(
    format: str,
    deck_id: int = None,
    tags: str = None
):
    options = ExportOptions(
        format=ExportFormat[format.upper()],
        output_path=f"temp_export.{format}",
        deck_ids=[deck_id] if deck_id else None,
        tags=tags.split(",") if tags else None
    )
    
    result = await export_service.export_flashcards(options)
    
    if result.success:
        with open(result.file_path, 'rb') as f:
            content = f.read()
        
        media_type = {
            "tsv": "text/tab-separated-values",
            "json": "application/json",
            "pdf": "application/pdf",
            "anki": "application/octet-stream"
        }.get(format, "application/octet-stream")
        
        return Response(content=content, media_type=media_type)
```

## Performance Optimization

### Large Dataset Exports

```python
# Streaming export for large datasets
async def export_large_dataset():
    options = ExportOptions(
        format=ExportFormat.TSV,
        output_path="large_export.tsv",
        batch_size=1000  # Process in chunks
    )
    
    # Progress tracking
    def progress_callback(current, total):
        print(f"Progress: {current}/{total} ({current/total*100:.1f}%)")
    
    result = await export_service.export_flashcards(
        options,
        progress_callback=progress_callback
    )
```

### Memory-Efficient Export

```python
# Use streaming for JSON export
options = ExportOptions(
    format=ExportFormat.JSON,
    output_path="large.json",
    streaming=True  # Write incrementally
)
```

## Troubleshooting

### Common Issues

1. **Unicode Errors**
   - Ensure UTF-8 encoding is used
   - TSV exporter adds BOM by default
   - Check system locale settings

2. **Memory Issues with Large Exports**
   - Use batch processing
   - Enable streaming for JSON
   - Increase Python memory limit

3. **Anki Import Failures**
   - Verify APKG file integrity
   - Check Anki version compatibility
   - Ensure note type doesn't conflict

4. **PDF Font Issues**
   - Install Korean fonts: `apt-get install fonts-nanum`
   - Configure font path in PDF exporter
   - Use embedded fonts option

### Debug Mode

```bash
# Enable debug logging
export FLASHCARD_DEBUG=1
python scripts/export_flashcards.py -f tsv -o debug.tsv --verbose

# Test export without saving
python scripts/export_flashcards.py -f tsv --dry-run
```

## Export Validation

### Verify Export Integrity

```python
# Validate TSV export
from flashcard_pipeline.exporters.tsv_exporter import TSVExporter

exporter = TSVExporter()
is_valid = exporter.validate_tsv("flashcards.tsv")

# Validate JSON structure
import json
with open("flashcards.json") as f:
    data = json.load(f)
    assert "flashcards" in data
    assert all("front" in card for card in data["flashcards"])
```

### Export Statistics

```bash
# Get export statistics
python scripts/export_flashcards.py --stats

# Output:
# Total flashcards: 1,234
# Published: 1,200
# Decks: 15
# Tags: 45
# Last export: 2025-01-09 10:30:00
```

## Best Practices

1. **Regular Exports**
   - Schedule daily backups
   - Export before major changes
   - Keep version history

2. **Format Selection**
   - TSV for spreadsheet analysis
   - Anki for study purposes
   - JSON for API integration
   - PDF for offline review

3. **Filtering Strategy**
   - Export by proficiency level
   - Separate formal/informal content
   - Group by topic or deck

4. **Template Usage**
   - Create templates for common exports
   - Version control templates
   - Document template purpose

5. **Performance**
   - Batch large exports
   - Use compression for archives
   - Clean up old exports regularly