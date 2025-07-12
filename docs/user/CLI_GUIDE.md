# 📖 Korean Flashcard Pipeline - CLI User Guide

Welcome to the comprehensive CLI guide for the Korean Flashcard Pipeline. This guide covers all commands, options, and features available in the enhanced CLI v2.

> **Version**: 1.0.0 | **Last Updated**: 2025-01-10

## What's New in v1.0.0

### 🎉 Major Features
- **Enhanced CLI v2**: Complete rewrite with 40+ commands
- **Concurrent Processing**: Up to 50x faster with parallel workers
- **Smart Caching**: Reduces API costs by up to 40%
- **Resume Support**: Continue interrupted batches seamlessly
- **Live Monitoring**: Real-time dashboard with metrics
- **Plugin System**: Extend functionality with custom plugins
- **Integrations**: Direct Notion and Anki connections
- **Security Audit**: Built-in security checks and recommendations
- **Performance Testing**: Comprehensive benchmarking tools

### 🚀 Quick Upgrade Guide
```bash
# Upgrade from previous version
pip install -r requirements.txt --upgrade

# Migrate configuration
python -m flashcard_pipeline config migrate

# Test new features
python -m flashcard_pipeline test all
```

## Table of Contents

1. [Getting Started](#getting-started)
2. [Command Overview](#command-overview)
3. [Core Commands](#core-commands)
4. [Import & Export](#import--export)
5. [Database Operations](#database-operations)
6. [Cache Management](#cache-management)
7. [Monitoring & Analytics](#monitoring--analytics)
8. [Automation](#automation)
9. [Advanced Features](#advanced-features)
10. [Integrations](#integrations)
11. [Security & Testing](#security--testing)
12. [Configuration](#configuration)
13. [Troubleshooting](#troubleshooting)
14. [Examples & Recipes](#examples--recipes)

## Getting Started

### Installation

```bash
# Install core dependencies
pip install -r requirements.txt

# Install optional dependencies for advanced features
pip install watchdog  # For directory watching
pip install schedule  # For task scheduling (coming soon)

# Verify installation
python -m flashcard_pipeline --version
```

### First Time Setup

```bash
# 1. Initialize configuration
python -m flashcard_pipeline init

# 2. Set your API key
export OPENROUTER_API_KEY="your-api-key-here"

# 3. Test connection
python -m flashcard_pipeline test connection

# 4. Process your first file
python -m flashcard_pipeline process test_5_words.csv
```

## Command Overview

The CLI uses a hierarchical command structure:

```
flashcard-pipeline [GLOBAL-OPTIONS] COMMAND [COMMAND-OPTIONS] [ARGUMENTS]
```

### Global Options

| Option | Short | Description |
|--------|-------|-------------|
| `--config PATH` | `-c` | Custom configuration file |
| `--log-level LEVEL` | `-l` | Set logging level (DEBUG, INFO, WARNING, ERROR) |
| `--no-color` | | Disable colored output |
| `--json` | | Output in JSON format |
| `--quiet` | `-q` | Suppress non-error output |
| `--version` | `-v` | Show version information |
| `--help` | `-h` | Show help message |

## Core Commands

### `init` - Initialize Configuration

Creates a new configuration file with default settings.

```bash
# Create default config
python -m flashcard_pipeline init

# Create config at custom location
python -m flashcard_pipeline init my-config.yml

# Force overwrite existing config
python -m flashcard_pipeline init --force
```

### `config` - Manage Configuration

View and modify configuration settings.

```bash
# List all configuration
python -m flashcard_pipeline config --list

# Get specific value
python -m flashcard_pipeline config --get api.model

# Set value
python -m flashcard_pipeline config --set "api.timeout=60"

# Validate configuration
python -m flashcard_pipeline config --validate

# Export configuration
python -m flashcard_pipeline config --export backup-config.yml
```

### `process` - Process Vocabulary

The main command for processing Korean vocabulary into flashcards.

```bash
# Basic usage
python -m flashcard_pipeline process input.csv

# With options
python -m flashcard_pipeline process input.csv \
  --output results.tsv \
  --concurrent 20 \
  --limit 100 \
  --start-from 50
```

#### Process Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output PATH` | Output file path | Auto-generated |
| `--format FORMAT` | Output format (tsv, json, csv) | tsv |
| `--limit N` | Process only N items | All |
| `--start-from N` | Start from item N | 0 |
| `--concurrent N` | Concurrent workers (1-50) | 1 |
| `--batch-id ID` | Custom batch identifier | Auto-generated |
| `--dry-run` | Preview without processing | False |
| `--resume ID` | Resume interrupted batch | None |
| `--filter EXPR` | Filter expression | None |
| `--preset NAME` | Use configuration preset | None |
| `--db-write/--no-db-write` | Write to database | True |
| `--cache-only` | Use only cached results (no API calls) | False |

#### New Features in v1.0.0

- **Resume Processing**: Continue interrupted batches with `--resume`
- **Cache-Only Mode**: Process using only cached data to save API costs
- **Custom Batch IDs**: Assign meaningful identifiers to your processing batches
- **Preset Support**: Use predefined configuration sets

#### Filter Expressions

```bash
# Filter by type
python -m flashcard_pipeline process input.csv --filter "type=noun"

# Filter by position range
python -m flashcard_pipeline process input.csv --filter "position>100,position<200"

# Complex filters (evaluated as Python)
python -m flashcard_pipeline process input.csv --filter "row['type']=='verb' and len(row['term']) > 2"
```

## Import & Export

### Import Commands

Import vocabulary from various sources.

```bash
# Import from CSV
python -m flashcard_pipeline import csv vocabulary.csv

# Import with field mapping
python -m flashcard_pipeline import csv data.csv --mapping field-map.yml

# Import with validation only
python -m flashcard_pipeline import csv data.csv --validate

# Import with tags
python -m flashcard_pipeline import csv data.csv --tag "lesson-1" --tag "beginner"

# Merge strategies
python -m flashcard_pipeline import csv data.csv --merge skip    # Skip duplicates (default)
python -m flashcard_pipeline import csv data.csv --merge update  # Update existing
python -m flashcard_pipeline import csv data.csv --merge duplicate # Allow duplicates
```

### Export Commands

Export flashcards to various formats with advanced filtering and customization.

```bash
# Export to Anki
python -m flashcard_pipeline export anki output.apkg

# Export specific batch
python -m flashcard_pipeline export anki output.apkg --batch-id batch_20240107_120000

# Export with filter
python -m flashcard_pipeline export csv filtered.csv --filter "tags contains 'beginner'"

# Export with custom template
python -m flashcard_pipeline export anki deck.apkg --template my-template.html

# Split output by field
python -m flashcard_pipeline export csv output --split-by type
# Creates: output_noun.csv, output_verb.csv, etc.

# Export with quality threshold
python -m flashcard_pipeline export anki high-quality.apkg --filter "confidence >= 0.85"

# Export date range
python -m flashcard_pipeline export csv recent.csv --filter "created_date > '2024-01-01'"

# Export formats
python -m flashcard_pipeline export json data.json      # JSON format
python -m flashcard_pipeline export xlsx data.xlsx     # Excel format
python -m flashcard_pipeline export markdown data.md   # Markdown tables
```

#### Supported Export Formats

| Format | Extension | Description | Features |
|--------|-----------|-------------|----------|
| TSV | .tsv | Tab-separated values | Anki-compatible, preserves formatting |
| CSV | .csv | Comma-separated values | Excel-compatible, widely supported |
| JSON | .json | JavaScript Object Notation | Full metadata, programmatic access |
| XLSX | .xlsx | Excel workbook | Multiple sheets, formatting |
| Anki | .apkg | Anki package | Ready to import, includes media |
| Markdown | .md | Markdown tables | Human-readable, GitHub-compatible |

## Database Operations

### Database Commands

```bash
# Run migrations
python -m flashcard_pipeline db migrate

# Show statistics
python -m flashcard_pipeline db stats

# Backup database
python -m flashcard_pipeline db backup my-backup.db

# Restore from backup
python -m flashcard_pipeline db restore my-backup.db

# Run custom query
python -m flashcard_pipeline db query "SELECT COUNT(*) FROM flashcards"

# Repair database
python -m flashcard_pipeline db repair
```

### Database Statistics Output

```
Database Statistics
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━┓
┃ Table               ┃ Rows   ┃ Size (KB) ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━┩
│ flashcards          │ 1,234  │ 456.7     │
│ vocabulary_items    │ 5,678  │ 234.5     │
│ cache_entries       │ 3,456  │ 678.9     │
│ processing_batches  │ 12     │ 3.4       │
└─────────────────────┴────────┴───────────┘
```

## Cache Management

### Cache Commands

```bash
# Show cache statistics
python -m flashcard_pipeline cache stats

# Clear all cache
python -m flashcard_pipeline cache clear --yes

# Clear specific stage
python -m flashcard_pipeline cache clear --stage stage1

# Warm cache from batch
python -m flashcard_pipeline cache warm --batch-id batch_20240107

# Export cache
python -m flashcard_pipeline cache export cache-backup.tar.gz

# Import cache
python -m flashcard_pipeline cache import cache-backup.tar.gz
```

### Cache Statistics Output

```
Cache Statistics
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Metric           ┃ Value     ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ Total Entries    │ 1,234     │
│ Stage 1 Entries  │ 617       │
│ Stage 2 Entries  │ 617       │
│ Total Size       │ 45.6 MB   │
│ Hit Rate         │ 78.3%     │
│ Tokens Saved     │ 1,234,567 │
└──────────────────┴───────────┘
```

## Monitoring & Analytics

### `monitor` - Real-time Dashboard

Launch a live monitoring dashboard for processing operations.

```bash
# Basic monitoring
python -m flashcard_pipeline monitor

# Custom refresh rate
python -m flashcard_pipeline monitor --refresh 2

# Monitor specific metrics
python -m flashcard_pipeline monitor --metrics "rate,errors,cache_hits"

# Export statistics
python -m flashcard_pipeline monitor --export stats.jsonl
```

### Dashboard View

```
╔═══════════════════════════════════════════════════════╗
║         Korean Flashcard Pipeline Monitor             ║
╚═══════════════════════════════════════════════════════╝

Current Metrics
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric             ┃ Value         ┃ Trend ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Active Batches     │ 2             │ ↑     │
│ Processing Rate    │ 5.2 items/sec │ ↑     │
│ API Calls          │ 234           │ ↑     │
│ Cache Hits         │ 62%           │ →     │
│ Errors             │ 2             │ ↓     │
│ Memory Usage       │ 145 MB        │ →     │
└────────────────────┴───────────────┴───────┘

Press Ctrl+C to exit
```

## Automation

### `watch` - Directory Monitoring

Automatically process new files as they appear.

```bash
# Watch current directory
python -m flashcard_pipeline watch

# Watch specific directory
python -m flashcard_pipeline watch /path/to/input

# Custom pattern
python -m flashcard_pipeline watch ./input --pattern "*.csv"

# Custom command
python -m flashcard_pipeline watch ./input --command "process --concurrent 20"

# Recursive watching
python -m flashcard_pipeline watch ./data --recursive
```

### `schedule` - Task Scheduling

Schedule processing tasks with cron-like syntax.

```bash
# Daily at 9 AM
python -m flashcard_pipeline schedule "0 9 * * *" "process daily-vocab.csv"

# Every Monday at 6 PM
python -m flashcard_pipeline schedule "0 18 * * 1" "process weekly-vocab.csv"

# Named schedule
python -m flashcard_pipeline schedule "0 0 * * *" "db backup" --name "daily-backup"
```

## Advanced Features

### `test` - System Testing

Test various system components.

```bash
# Test all components
python -m flashcard_pipeline test all

# Test specific component
python -m flashcard_pipeline test connection
python -m flashcard_pipeline test cache
python -m flashcard_pipeline test database
python -m flashcard_pipeline test performance

# Verbose output
python -m flashcard_pipeline test all --verbose
```

### `audit` - Security Audit

Check for security issues and misconfigurations.

```bash
# Run security audit
python -m flashcard_pipeline audit

# Export audit report
python -m flashcard_pipeline audit --output audit-report.json
```

### `optimize` - Performance Optimization

Optimize system components for better performance.

```bash
# Optimize all components
python -m flashcard_pipeline optimize

# Optimize specific component
python -m flashcard_pipeline optimize --component cache
python -m flashcard_pipeline optimize --component database

# Run with profiling
python -m flashcard_pipeline optimize --profile
```

### `interactive` - REPL Mode

Launch interactive mode for exploratory usage.

```bash
python -m flashcard_pipeline interactive
```

Interactive mode commands:
- `process <file>` - Process a file
- `cache stats` - Show cache statistics
- `db query <sql>` - Run SQL query
- `help` - Show available commands
- `exit` - Exit interactive mode

### Plugin System

The CLI supports a plugin architecture for extending functionality.

```bash
# List installed plugins
python -m flashcard_pipeline plugins list

# Install plugin
python -m flashcard_pipeline plugins install https://github.com/user/plugin
python -m flashcard_pipeline plugins install my-local-plugin/

# Enable/disable plugins
python -m flashcard_pipeline plugins enable plugin-name
python -m flashcard_pipeline plugins disable plugin-name

# Plugin information
python -m flashcard_pipeline plugins info plugin-name
```

> **Note**: Plugin installation is currently in beta. Check documentation for plugin development guidelines.

## Integrations

### Notion Integration

Sync your flashcards with Notion databases for collaborative learning.

```bash
# Connect to Notion database
python -m flashcard_pipeline integrate notion DATABASE_ID --token YOUR_TOKEN

# Two-way sync
python -m flashcard_pipeline integrate notion DATABASE_ID --sync

# Export to Notion
python -m flashcard_pipeline integrate notion DATABASE_ID --export-only

# Import from Notion
python -m flashcard_pipeline integrate notion DATABASE_ID --import-only
```

### Anki-Connect Integration

Direct integration with Anki desktop application via AnkiConnect addon.

```bash
# Connect to Anki
python -m flashcard_pipeline integrate anki-connect "Korean Vocabulary"

# Custom host/port
python -m flashcard_pipeline integrate anki-connect "My Deck" --host localhost --port 8765

# Add cards with specific model
python -m flashcard_pipeline integrate anki-connect "My Deck" --model "Korean-English"

# Sync specific batch
python -m flashcard_pipeline integrate anki-connect "My Deck" --batch-id batch_20240107
```

### Prerequisites for Integrations

- **Notion**: Requires Notion API token and database permissions
- **AnkiConnect**: Requires Anki desktop with AnkiConnect addon installed

## Security & Testing

### Security Audit

Ensure your pipeline configuration meets security best practices.

```bash
# Run security audit
python -m flashcard_pipeline audit

# Export detailed report
python -m flashcard_pipeline audit --output audit-report.json

# Check specific components
python -m flashcard_pipeline audit --component api
python -m flashcard_pipeline audit --component database
python -m flashcard_pipeline audit --component cache
```

Audit checks include:
- API key exposure risks
- Database permissions
- Cache directory security
- Configuration file permissions
- Log file sanitization

### System Testing

Comprehensive testing suite for all components.

```bash
# Test all components
python -m flashcard_pipeline test all

# Test specific components
python -m flashcard_pipeline test connection    # API connectivity
python -m flashcard_pipeline test cache        # Cache functionality
python -m flashcard_pipeline test database     # Database operations
python -m flashcard_pipeline test performance  # Performance benchmarks

# Verbose testing
python -m flashcard_pipeline test all --verbose

# Save test results
python -m flashcard_pipeline test all --output test-results.json
```

### Performance Testing

```bash
# Run performance benchmarks
python -m flashcard_pipeline test performance

# Custom benchmark parameters
python -m flashcard_pipeline test performance --iterations 100 --concurrent 20

# Profile specific operation
python -m flashcard_pipeline test performance --profile process
```

## Configuration

### Configuration File Structure

```yaml
# .flashcard-config.yml
api:
  provider: openrouter
  model: anthropic/claude-3.5-sonnet
  base_url: https://openrouter.ai/api/v1
  timeout: 30
  max_retries: 3

processing:
  max_concurrent: 20
  batch_size: 100
  rate_limit:
    requests_per_minute: 60
    tokens_per_minute: 90000

cache:
  enabled: true
  path: .cache/flashcards
  ttl_days: 30
  max_size_gb: 10.0

database:
  path: pipeline.db
  connection_pool_size: 5
  enable_wal: true

output:
  default_format: tsv
  anki:
    deck_name: "Korean Vocabulary"
    tags: ["korean", "ai-generated"]
  quality:
    min_confidence: 0.8
    require_examples: true

logging:
  level: INFO
  file: flashcard-pipeline.log
  max_size_mb: 100
  retention_days: 7

# Custom presets
presets:
  beginner:
    processing:
      max_concurrent: 5
    output:
      anki:
        tags: ["beginner", "korean"]
  
  advanced:
    processing:
      max_concurrent: 50
    output:
      quality:
        min_confidence: 0.9
```

### Environment Variables

```bash
# API Configuration
export FLASHCARD_API_KEY="your-api-key"
export FLASHCARD_API_MODEL="anthropic/claude-3.5-sonnet"
export FLASHCARD_API_TIMEOUT=30

# Processing
export FLASHCARD_MAX_CONCURRENT=20
export FLASHCARD_BATCH_SIZE=100

# Cache
export FLASHCARD_CACHE_ENABLED=true
export FLASHCARD_CACHE_PATH=".cache/flashcards"

# Database
export FLASHCARD_DB_PATH="pipeline.db"

# Logging
export FLASHCARD_LOG_LEVEL="INFO"
```

### Configuration Hierarchy

1. Command-line arguments (highest priority)
2. Environment variables
3. Configuration file
4. Default values (lowest priority)

## Troubleshooting

### Common Issues

#### API Key Not Found

```bash
# Check if API key is set
python -m flashcard_pipeline config --validate

# Set API key
export OPENROUTER_API_KEY="your-key"
# Or add to .env file
echo "OPENROUTER_API_KEY=your-key" >> .env
```

#### Rate Limit Errors

```bash
# Reduce concurrent workers
python -m flashcard_pipeline process input.csv --concurrent 5

# Check rate limit status
python -m flashcard_pipeline monitor --metrics "rate_limit"
```

#### Database Errors

```bash
# Check database integrity
python -m flashcard_pipeline db repair

# Reset database
rm pipeline.db
python -m flashcard_pipeline db migrate
```

#### Cache Issues

```bash
# Clear corrupted cache
python -m flashcard_pipeline cache clear --yes

# Verify cache
python -m flashcard_pipeline test cache
```

### Debug Mode

```bash
# Enable debug logging
python -m flashcard_pipeline --log-level DEBUG process input.csv

# Save debug output
python -m flashcard_pipeline --log-level DEBUG process input.csv 2> debug.log
```

## Examples & Recipes

### Basic Processing

```bash
# Process entire file
python -m flashcard_pipeline process korean_vocab.csv

# Process with progress bar
python -m flashcard_pipeline process korean_vocab.csv --concurrent 20

# Process first 50 words
python -m flashcard_pipeline process korean_vocab.csv --limit 50
```

### Batch Processing

```bash
# Process multiple files
for file in vocab/*.csv; do
  python -m flashcard_pipeline process "$file" --output "output/$(basename $file .csv).tsv"
done

# Process with custom batch ID
python -m flashcard_pipeline process vocab.csv --batch-id "lesson-1-$(date +%Y%m%d)"
```

### Filtering and Selection

```bash
# Process only nouns
python -m flashcard_pipeline process vocab.csv --filter "type=noun"

# Process words 100-200
python -m flashcard_pipeline process vocab.csv --start-from 100 --limit 100

# Process high-frequency words
python -m flashcard_pipeline process vocab.csv --filter "frequency>1000"
```

### Automation Setup

```bash
# Set up daily processing
python -m flashcard_pipeline schedule "0 6 * * *" \
  "process /data/daily-vocab.csv --concurrent 20"

# Watch folder for new files
python -m flashcard_pipeline watch /dropbox/korean-vocab \
  --pattern "*.csv" \
  --command "process --concurrent 10 --output /output/"
```

### Performance Optimization

```bash
# Warm cache before processing
python -m flashcard_pipeline cache warm --batch-id previous-batch
python -m flashcard_pipeline process new-vocab.csv

# Use maximum concurrency
python -m flashcard_pipeline process large-vocab.csv \
  --concurrent 50 \
  --batch-size 200

# Monitor while processing
python -m flashcard_pipeline monitor &
python -m flashcard_pipeline process vocab.csv --concurrent 20
```

### Export Workflows

```bash
# Export to Anki with custom deck
python -m flashcard_pipeline export anki korean-deck.apkg \
  --batch-id latest \
  --filter "confidence>0.8"

# Split export by difficulty
python -m flashcard_pipeline export csv output/ \
  --split-by difficulty_level

# Export with custom template
python -m flashcard_pipeline export anki deck.apkg \
  --template templates/korean-card.html
```

## Tips & Best Practices

1. **Start Small**: Test with a small batch before processing large files
2. **Use Concurrent Processing**: Start with 10-20 workers, adjust based on results
3. **Monitor Performance**: Use the monitor command to track processing
4. **Regular Backups**: Backup your database regularly
5. **Cache Management**: Clear cache periodically to save disk space
6. **Configuration Presets**: Create presets for different use cases
7. **Error Recovery**: Use --resume to continue interrupted batches
8. **API Rate Limits**: Respect rate limits to avoid throttling
9. **Batch Organization**: Use meaningful batch IDs for easy tracking
10. **Automation**: Set up watch folders for hands-free processing

## Getting Help

```bash
# General help
python -m flashcard_pipeline --help

# Command-specific help
python -m flashcard_pipeline process --help
python -m flashcard_pipeline import --help

# Version information
python -m flashcard_pipeline --version

# Test system
python -m flashcard_pipeline test all
```

For more information, visit the [project documentation](../README.md) or [file an issue](https://github.com/RexRenatus/korean-flashcard-pipeline/issues).

## Connect With Us

- **GitHub**: [Korean Flashcard Pipeline](https://github.com/RexRenatus/korean-flashcard-pipeline)
- **Portfolio**: [RexRenatus.io](https://rexrenatus.github.io/RexRenatus.io/)
- **Instagram**: [@devi.nws](https://www.instagram.com/devi.nws/)