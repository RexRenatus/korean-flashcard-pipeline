# CLI Migration Guide

This guide helps you migrate from the old CLI (`cli.py`) to the new modern CLI (`modern_cli.py`).

## Overview

The new CLI provides:
- 🎯 Better command structure
- 🎨 Rich output formatting
- 🤝 Interactive features
- 📊 Real-time monitoring
- 🔌 Plugin support
- 🚀 Better performance

## Command Mapping

### Old Commands → New Commands

| Old Command | New Command | Notes |
|-------------|-------------|-------|
| `python -m flashcard_pipeline.cli process word` | `flashcard process single word` | More intuitive |
| `python -m flashcard_pipeline.cli batch file.csv` | `flashcard process batch file.csv` | Better options |
| `python -m flashcard_pipeline.cli --stats` | `flashcard cache stats` | Dedicated command |
| `python -m flashcard_pipeline.cli --clear-cache` | `flashcard cache clear` | With confirmation |
| `python -m flashcard_pipeline.cli --migrate` | `flashcard db migrate` | Database group |

### New Command Structure

```
flashcard
├── process         # Processing commands
│   ├── single     # Process single word
│   └── batch      # Process batch file
├── cache          # Cache management
│   ├── stats      # Show statistics
│   └── clear      # Clear cache
├── db             # Database operations
│   ├── migrate    # Run migrations
│   └── stats      # Database statistics
├── monitor        # Monitoring
│   ├── errors     # Error analytics
│   └── health     # Health check
└── config         # Configuration
    ├── show       # Display config
    ├── set        # Set values
    └── validate   # Validate config
```

## Feature Comparison

### 1. Single Word Processing

**Old way:**
```bash
python -m flashcard_pipeline.cli process "안녕하세요"
```

**New way:**
```bash
# Basic
flashcard process single "안녕하세요"

# With context
flashcard process single "어렵다" --context "In studying context"

# Without saving
flashcard process single "사랑" --no-save

# Force reprocessing
flashcard process single "감사합니다" --force
```

### 2. Batch Processing

**Old way:**
```bash
python -m flashcard_pipeline.cli batch words.csv
```

**New way:**
```bash
# Basic
flashcard process batch words.csv

# With options
flashcard process batch words.csv \
  --output results.json \
  --batch-size 20 \
  --continue-on-error

# CSV options
flashcard process batch data.csv \
  --delimiter ";" \
  --column 2

# With progress
flashcard process batch large_file.csv --progress
```

### 3. Output Formats

**Old way:**
```bash
# Limited to console output
python -m flashcard_pipeline.cli process word
```

**New way:**
```bash
# Human-readable (default)
flashcard process single "안녕하세요"

# JSON output
flashcard process single "안녕하세요" --output json

# YAML output
flashcard process single "안녕하세요" --output yaml

# Global output format
flashcard --output json process batch words.csv
```

### 4. Cache Management

**Old way:**
```bash
# Show stats
python -m flashcard_pipeline.cli --stats

# Clear cache
python -m flashcard_pipeline.cli --clear-cache
```

**New way:**
```bash
# Detailed statistics
flashcard cache stats

# Clear with confirmation
flashcard cache clear

# Clear specific tier
flashcard cache clear --tier l1
flashcard cache clear --tier l2
```

### 5. Error Handling

**Old way:**
```bash
# Errors printed to console
python -m flashcard_pipeline.cli batch file.csv
```

**New way:**
```bash
# Monitor errors
flashcard monitor errors --last 1h
flashcard monitor errors --category network --severity high

# Continue on error
flashcard process batch file.csv --continue-on-error

# Real-time monitoring
flashcard monitor errors --follow
```

## New Features

### 1. Interactive Mode

When required arguments are missing, the CLI enters interactive mode:

```bash
$ flashcard process batch
🎯 Interactive Mode
Missing required arguments. Let's fill them in!

Input file path: words.csv
CSV delimiter: ,
Column index: 0
Batch size: 10
Continue on errors? (Y/n): y
Save results to file? (Y/n): y
Output file path: results.json
```

### 2. Configuration Management

```bash
# Show current config
flashcard config show

# Set configuration values
flashcard config set api_key "your-key-here"
flashcard config set output json
flashcard config set telemetry false

# Validate configuration
flashcard config validate
```

### 3. Rich Output

The new CLI provides beautiful, colored output:

- ✅ Success messages in green
- ❌ Errors in red
- ⚠️  Warnings in yellow
- ℹ️  Info in blue
- Progress bars with ETA
- Tables for structured data
- Syntax highlighting for JSON/YAML

### 4. Environment Variables

```bash
# API key
export OPENROUTER_API_KEY=your-key

# Database path
export FLASHCARD_DB=/path/to/database.db

# Disable telemetry
export FLASHCARD_TELEMETRY=false
```

### 5. Config Files

Create a config file at `~/.flashcard/config.yaml`:

```yaml
api_key: your-key-here
database: /path/to/flashcards.db
output_format: json
telemetry_enabled: true
cache:
  type: redis
  redis_url: redis://localhost:6379
```

Use with:
```bash
flashcard --config ~/.flashcard/config.yaml process batch words.csv
```

## Migration Steps

### Step 1: Install New CLI

```bash
# Update requirements
pip install -r requirements.txt

# Verify installation
flashcard --version
```

### Step 2: Update Scripts

Replace old CLI calls in your scripts:

```python
# Old
import subprocess
subprocess.run(["python", "-m", "flashcard_pipeline.cli", "process", word])

# New
import subprocess
subprocess.run(["flashcard", "process", "single", word])
```

### Step 3: Update Aliases

Update your shell aliases:

```bash
# Old
alias fc="python -m flashcard_pipeline.cli"

# New
alias fc="flashcard"
```

### Step 4: Setup Completion

Enable shell completion for better productivity:

```bash
# Bash
eval "$(_FLASHCARD_COMPLETE=bash_source flashcard)"

# Zsh
eval "$(_FLASHCARD_COMPLETE=zsh_source flashcard)"

# Fish
eval (env _FLASHCARD_COMPLETE=fish_source flashcard)
```

## Advanced Usage

### 1. Parallel Processing

```bash
# Process multiple files in parallel
flashcard process batch file1.csv &
flashcard process batch file2.csv &
flashcard process batch file3.csv &
wait
```

### 2. Pipeline Commands

```bash
# Process and monitor
flashcard process batch input.csv | \
  flashcard monitor errors --real-time

# Extract translations
flashcard process single "사랑" --output json | \
  jq -r '.translation'
```

### 3. Custom Scripts

Use CLI components in your scripts:

```python
from flashcard_pipeline.cli.modern_cli import CLIContext
from flashcard_pipeline.cli.rich_output import RichOutput

async def custom_processor():
    ctx = CLIContext()
    await ctx.initialize_components()
    
    rich = RichOutput()
    result = await ctx.api_client.process_complete("안녕하세요")
    rich.print_flashcard(result, detailed=True)
    
    await ctx.cleanup()
```

## Troubleshooting

### Issue: Command not found

```bash
# Add to PATH
export PATH="$PATH:$(python -m site --user-base)/bin"

# Or use python -m
python -m flashcard_pipeline.cli.modern_cli
```

### Issue: Import errors

```bash
# Reinstall in development mode
pip install -e .
```

### Issue: No color output

```bash
# Force color
flashcard --no-color=false process single word

# Or set environment variable
export FORCE_COLOR=1
```

## Benefits of Migration

1. **Better UX**: Interactive prompts, rich output, progress tracking
2. **More Features**: Advanced filtering, real-time monitoring, plugins
3. **Better Performance**: Async operations, optimized caching
4. **Easier Scripting**: Structured output, proper exit codes
5. **Future-Proof**: Active development, new features

## Getting Help

```bash
# General help
flashcard --help

# Command help
flashcard process --help
flashcard process single --help

# Interactive mode
flashcard  # Shows main help

# Debug mode
flashcard --debug process single word
```

---

The new CLI is designed to be more intuitive, powerful, and pleasant to use. Happy migrating! 🚀