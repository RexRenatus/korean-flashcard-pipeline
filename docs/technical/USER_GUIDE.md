# User Guide - Korean Language Flashcard Pipeline

## Table of Contents
1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Installation](#installation)
4. [Basic Usage](#basic-usage)
5. [Advanced Features](#advanced-features)
6. [Configuration](#configuration)
7. [Troubleshooting](#troubleshooting)
8. [FAQ](#faq)

## Introduction

The Korean Language Flashcard Pipeline is an AI-powered system that generates nuanced flashcards for Korean language learning. It uses advanced language models to create comprehensive learning materials including definitions, examples, cultural notes, and memory aids.

### Key Features
- **Two-stage AI processing**: Initial generation followed by nuance enhancement
- **Comprehensive flashcards**: Definitions, examples, conjugations, and cultural notes
- **Smart caching**: Reduces API costs and improves speed
- **Batch processing**: Handle multiple words efficiently
- **Export formats**: Anki, CSV, JSON, and Markdown

## Getting Started

### Prerequisites
- Python 3.8 or higher
- SQLite3
- Internet connection for API access
- OpenRouter API key

### Quick Setup
1. Clone the repository
2. Set up your environment
3. Configure API credentials
4. Run your first flashcard generation

## Installation

### Step 1: Clone the Repository
```bash
git clone https://github.com/yourusername/korean-flashcard-pipeline.git
cd korean-flashcard-pipeline
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Set Up Configuration
Create a `.env` file in the project root:
```env
OPENROUTER_API_KEY=your_api_key_here
DATABASE_PATH=./pipeline.db
LOG_LEVEL=INFO
```

### Step 5: Initialize Database
```bash
python -m flashcard_pipeline.cli init-db
```

## Basic Usage

### Single Word Processing
Generate a flashcard for a single Korean word:
```bash
python -m flashcard_pipeline.cli process-word "안녕하세요"
```

### Batch Processing from CSV
Process multiple words from a CSV file:
```bash
python -m flashcard_pipeline.cli process-csv input.csv --output output/
```

CSV format example:
```csv
word,category,difficulty
안녕하세요,greeting,beginner
감사합니다,politeness,beginner
사랑,emotion,intermediate
```

### Interactive Mode
Launch the interactive CLI:
```bash
python -m flashcard_pipeline.cli interactive
```

Commands in interactive mode:
- `process <word>` - Process a single word
- `batch <file>` - Process a CSV file
- `status` - Check processing status
- `export <format>` - Export flashcards
- `help` - Show available commands
- `exit` - Exit interactive mode

## Advanced Features

### Custom Prompts
Use custom prompts for specialized content:
```bash
python -m flashcard_pipeline.cli process-word "김치" --prompt-template custom_food.txt
```

### Parallel Processing
Enable parallel processing for large batches:
```bash
python -m flashcard_pipeline.cli process-csv large_batch.csv --parallel --workers 4
```

### Caching Control
Manage the cache:
```bash
# Clear cache
python -m flashcard_pipeline.cli cache clear

# View cache statistics
python -m flashcard_pipeline.cli cache stats

# Disable cache for fresh results
python -m flashcard_pipeline.cli process-word "word" --no-cache
```

### Export Formats

#### Anki Export
```bash
python -m flashcard_pipeline.cli export anki --output flashcards.apkg
```

#### CSV Export
```bash
python -m flashcard_pipeline.cli export csv --output flashcards.csv
```

#### JSON Export
```bash
python -m flashcard_pipeline.cli export json --output flashcards.json --pretty
```

#### Markdown Export
```bash
python -m flashcard_pipeline.cli export markdown --output flashcards.md
```

### Database Management

#### Backup Database
```bash
python -m flashcard_pipeline.cli db backup --output backup.db
```

#### Restore Database
```bash
python -m flashcard_pipeline.cli db restore --input backup.db
```

#### Database Statistics
```bash
python -m flashcard_pipeline.cli db stats
```

## Configuration

### Configuration File
Create `config.yaml` for advanced settings:
```yaml
api:
  base_url: "https://openrouter.ai/api/v1"
  timeout: 30
  max_retries: 3
  
models:
  flashcard_creator: "claude-3-sonnet"
  nuance_creator: "claude-3-sonnet"
  
processing:
  batch_size: 10
  rate_limit: 60  # requests per minute
  
cache:
  enabled: true
  ttl: 604800  # 7 days in seconds
  
export:
  anki:
    deck_name: "Korean Vocabulary"
    note_type: "Korean Advanced"
  csv:
    delimiter: ","
    encoding: "utf-8"
```

### Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key | Required |
| `DATABASE_PATH` | Path to SQLite database | `./pipeline.db` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `CONFIG_PATH` | Path to config file | `./config.yaml` |
| `CACHE_DIR` | Directory for cache files | `./.cache` |

### Logging Configuration
Configure logging in `logging.yaml`:
```yaml
version: 1
formatters:
  default:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
handlers:
  console:
    class: logging.StreamHandler
    formatter: default
  file:
    class: logging.FileHandler
    filename: pipeline.log
    formatter: default
root:
  level: INFO
  handlers: [console, file]
```

## Troubleshooting

### Common Issues

#### API Key Not Found
**Error**: `OpenRouter API key not found`
**Solution**: 
1. Check `.env` file exists and contains `OPENROUTER_API_KEY`
2. Ensure no spaces around the `=` sign
3. Restart your terminal/command prompt

#### Database Locked
**Error**: `database is locked`
**Solution**:
1. Close any other instances of the application
2. Check file permissions
3. Use `python -m flashcard_pipeline.cli db unlock`

#### Rate Limit Exceeded
**Error**: `Rate limit exceeded`
**Solution**:
1. Wait for the cooldown period
2. Reduce batch size
3. Configure rate limiting in `config.yaml`

#### Memory Issues with Large Batches
**Error**: `MemoryError` during batch processing
**Solution**:
1. Reduce batch size
2. Enable streaming mode: `--stream`
3. Process in smaller chunks

### Debug Mode
Enable debug logging for detailed information:
```bash
export LOG_LEVEL=DEBUG
python -m flashcard_pipeline.cli process-word "test" --debug
```

### Performance Optimization

#### Database Optimization
```bash
# Vacuum database
python -m flashcard_pipeline.cli db optimize

# Rebuild indexes
python -m flashcard_pipeline.cli db reindex
```

#### Cache Optimization
```bash
# Warm up cache with common words
python -m flashcard_pipeline.cli cache warmup --file common_words.txt

# Prune old cache entries
python -m flashcard_pipeline.cli cache prune --days 30
```

## FAQ

### General Questions

**Q: How much does it cost to generate flashcards?**
A: Costs depend on your OpenRouter usage. Typically:
- Basic flashcard: ~$0.002-0.004
- With nuance enhancement: ~$0.004-0.008
- Cached results: Free

**Q: Can I use my own AI models?**
A: Yes! Configure custom models in `config.yaml`:
```yaml
models:
  flashcard_creator: "your-model-id"
  nuance_creator: "your-model-id"
```

**Q: How do I add custom fields to flashcards?**
A: Extend the prompt templates in `prompts/` directory.

**Q: Is there a limit on batch size?**
A: Default is 100 words per batch. Adjust in configuration based on your needs.

### Technical Questions

**Q: Can I use this offline?**
A: No, API access is required. However, cached results work offline.

**Q: How do I integrate with my app?**
A: Use the Python API directly:
```python
from flashcard_pipeline import FlashcardPipeline

pipeline = FlashcardPipeline()
result = pipeline.process_word("안녕")
```

**Q: What Python versions are supported?**
A: Python 3.8, 3.9, 3.10, and 3.11 are tested and supported.

**Q: Can I contribute to the project?**
A: Yes! See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for contribution guidelines.

### Data & Privacy

**Q: Is my data stored anywhere?**
A: Only in your local database. API calls are not logged by our system.

**Q: Can I delete my data?**
A: Yes, use `python -m flashcard_pipeline.cli db clear` to remove all data.

**Q: Are the flashcards copyrighted?**
A: Generated content is yours to use. Original Korean words are not copyrightable.

## Support

### Getting Help
- GitHub Issues: [Report bugs](https://github.com/yourusername/korean-flashcard-pipeline/issues)
- Documentation: [Full docs](https://docs.flashcardpipeline.com)
- Email: support@flashcardpipeline.com

### Community
- Discord: [Join our server](https://discord.gg/flashcards)
- Reddit: [r/KoreanFlashcards](https://reddit.com/r/KoreanFlashcards)

### Updates
Follow development:
- [Changelog](../CHANGELOG.md)
- [Roadmap](../planning/PHASE_ROADMAP.md)
- [Blog](https://blog.flashcardpipeline.com)