# User Documentation

Welcome to the user documentation for the Korean Language Flashcard Pipeline. This section contains everything you need to know to use the system effectively.

## Getting Started

New to the flashcard pipeline? Start here:

1. **[Quick Start Guide](./QUICK_START.md)** - Get up and running in 5 minutes
2. **[Installation Guide](./INSTALLATION.md)** - Detailed installation instructions
3. **[First Steps](./FIRST_STEPS.md)** - Your first vocabulary processing

## User Guides

### Core Documentation
- **[CLI User Guide](./CLI_GUIDE.md)** - Complete command-line interface reference
- **[Configuration Guide](./CONFIGURATION.md)** - How to configure the pipeline
- **[Import/Export Guide](./IMPORT_EXPORT.md)** - Working with different file formats

### Feature Guides
- **[Batch Processing](./BATCH_PROCESSING.md)** - Processing large vocabulary sets
- **[Caching Guide](./CACHING.md)** - Understanding and managing the cache
- **[Performance Tuning](./PERFORMANCE.md)** - Optimizing processing speed

### Troubleshooting
- **[FAQ](./FAQ.md)** - Frequently asked questions
- **[Common Issues](./TROUBLESHOOTING.md)** - Solutions to common problems
- **[Error Messages](./ERROR_REFERENCE.md)** - Understanding error messages

## Quick Reference

### Basic Commands

```bash
# Process a vocabulary file
flashcard-cli process input.csv

# Import with options
flashcard-cli import data.csv --skip-duplicates

# Export to different formats
flashcard-cli export anki --output deck.apkg
flashcard-cli export csv --output flashcards.csv

# Check system status
flashcard-cli status
```

### Common Workflows

#### Processing New Vocabulary
1. Prepare your CSV file with Korean terms
2. Run: `flashcard-cli process vocabulary.csv`
3. Review generated flashcards
4. Export to your preferred format

#### Batch Processing
1. Place multiple CSV files in a directory
2. Run: `flashcard-cli process-batch /path/to/files/`
3. Monitor progress with status command
4. Find results in output directory

#### Managing Cache
```bash
# View cache statistics
flashcard-cli cache stats

# Clear cache (if needed)
flashcard-cli cache clear

# Optimize cache
flashcard-cli cache optimize
```

## File Formats

### Input CSV Format
```csv
korean,english,type,difficulty
안녕하세요,Hello,phrase,1
책,book,noun,1
읽다,to read,verb,2
```

### Supported Export Formats
- **Anki** (.apkg) - For Anki flashcard app
- **CSV** (.csv) - Universal spreadsheet format
- **JSON** (.json) - For programmatic use
- **TSV** (.tsv) - Tab-separated values
- **Markdown** (.md) - Human-readable format

## Configuration

The pipeline can be configured via:
1. Configuration file (`~/.flashcards/config.yaml`)
2. Environment variables
3. Command-line arguments

See [Configuration Guide](./CONFIGURATION.md) for details.

## Best Practices

### For Best Results
1. **Organize vocabulary by difficulty** - Process similar-level words together
2. **Use consistent formatting** - Follow the CSV format guidelines
3. **Leverage caching** - Reprocess files to save on API calls
4. **Monitor usage** - Check your API usage regularly

### Performance Tips
1. **Batch processing** - Process multiple items at once
2. **Enable caching** - Reduces API calls significantly
3. **Adjust concurrency** - Find optimal settings for your system
4. **Use filters** - Process only what you need

## Getting Help

### Documentation
- This user guide
- In-app help: `flashcard-cli --help`
- Command help: `flashcard-cli [command] --help`

### Support
- Check [FAQ](./FAQ.md) first
- Search [GitHub Issues](https://github.com/YourRepo/issues)
- Ask in [Discussions](https://github.com/YourRepo/discussions)

## System Requirements

### Minimum Requirements
- Python 3.8+
- 2GB RAM
- 1GB free disk space
- Internet connection

### Recommended
- Python 3.11+
- 4GB RAM
- SSD storage
- Stable internet connection

## Privacy & Security

- API keys are stored securely
- No vocabulary data is shared
- Cache is stored locally
- See [Privacy Policy](./PRIVACY.md) for details

## Updates

To update to the latest version:
```bash
pip install --upgrade flashcard-pipeline
```

Check [Release Notes](./RELEASES.md) for new features and changes.