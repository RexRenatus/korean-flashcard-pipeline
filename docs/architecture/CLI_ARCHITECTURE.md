# CLI Architecture Design
*Last Updated: 2025-01-07*

## Overview

The Korean Flashcard Pipeline CLI provides a comprehensive command-line interface for processing Korean vocabulary into AI-generated flashcards. This document outlines the architecture, design principles, and technical specifications for the CLI system.

## Design Principles

### 1. **Progressive Disclosure**
- Simple commands for basic operations
- Advanced flags for power users
- Sensible defaults for all options

### 2. **Pipeline Philosophy**
- Commands can be chained together
- Output formats support piping
- Batch operations are first-class

### 3. **Feedback & Monitoring**
- Rich progress indicators
- Clear error messages
- Detailed logging options

### 4. **Resilience**
- Automatic retries with backoff
- Resume interrupted operations
- Graceful degradation

## Command Structure

```
flashcard-pipeline [GLOBAL-OPTIONS] COMMAND [COMMAND-OPTIONS] [ARGUMENTS]
```

### Global Options
```bash
--config PATH        # Custom config file (default: .flashcard-config.yml)
--log-level LEVEL    # Logging verbosity: DEBUG|INFO|WARNING|ERROR
--no-color          # Disable colored output
--json              # Output in JSON format
--quiet             # Suppress non-error output
--version           # Show version information
--help              # Show help message
```

## Core Commands

### 1. `process` - Main Processing Command
```bash
flashcard-pipeline process INPUT [OPTIONS]
```

**Purpose**: Process vocabulary through the two-stage AI pipeline

**Arguments**:
- `INPUT`: Path to CSV file or "-" for stdin

**Options**:
```bash
--output PATH           # Output file (default: stdout)
--format FORMAT         # Output format: tsv|json|anki (default: tsv)
--limit N              # Process only first N items
--start-from N         # Start processing from item N
--concurrent N         # Concurrent processing (1-50, default: 1)
--batch-id ID          # Custom batch identifier
--dry-run              # Preview without processing
--resume BATCH_ID      # Resume interrupted batch
--filter EXPR          # Filter expression (e.g., "type=noun")
--preset NAME          # Use named configuration preset
```

### 2. `import` - Data Import Command
```bash
flashcard-pipeline import SOURCE [OPTIONS]
```

**Purpose**: Import vocabulary from various sources

**Subcommands**:
- `import csv` - Import from CSV file
- `import anki` - Import from Anki deck
- `import notion` - Import from Notion database
- `import google-sheets` - Import from Google Sheets

**Options**:
```bash
--mapping PATH         # Custom field mapping file
--validate            # Validate without importing
--merge-strategy STRAT # duplicate|skip|update
--tag TAG             # Add tag to imported items
```

### 3. `export` - Data Export Command
```bash
flashcard-pipeline export DESTINATION [OPTIONS]
```

**Purpose**: Export processed flashcards to various formats

**Subcommands**:
- `export anki` - Export to Anki-compatible format
- `export csv` - Export to CSV
- `export notion` - Export to Notion
- `export pdf` - Generate PDF study sheets

**Options**:
```bash
--batch-id ID         # Export specific batch
--filter EXPR         # Filter expression
--template PATH       # Custom export template
--split-by FIELD      # Split output by field value
```

### 4. `cache` - Cache Management
```bash
flashcard-pipeline cache SUBCOMMAND [OPTIONS]
```

**Subcommands**:
- `cache stats` - Show cache statistics
- `cache clear` - Clear cache entries
- `cache warm` - Pre-warm cache
- `cache export` - Export cache data
- `cache import` - Import cache data

### 5. `db` - Database Operations
```bash
flashcard-pipeline db SUBCOMMAND [OPTIONS]
```

**Subcommands**:
- `db migrate` - Run database migrations
- `db backup` - Backup database
- `db restore` - Restore from backup
- `db stats` - Show database statistics
- `db query` - Run custom SQL query
- `db repair` - Repair database issues

### 6. `monitor` - Real-time Monitoring
```bash
flashcard-pipeline monitor [OPTIONS]
```

**Purpose**: Live dashboard for processing operations

**Options**:
```bash
--refresh-rate N      # Update frequency in seconds
--metrics METRICS     # Comma-separated metrics to display
--export-stats PATH   # Export statistics to file
```

### 7. `config` - Configuration Management
```bash
flashcard-pipeline config SUBCOMMAND [OPTIONS]
```

**Subcommands**:
- `config init` - Initialize configuration
- `config get` - Get configuration value
- `config set` - Set configuration value
- `config validate` - Validate configuration
- `config export` - Export configuration

### 8. `test` - Testing & Validation
```bash
flashcard-pipeline test SUBCOMMAND [OPTIONS]
```

**Subcommands**:
- `test connection` - Test API connection
- `test sample` - Process sample vocabulary
- `test performance` - Run performance tests
- `test quality` - Validate output quality

## Configuration System

### Configuration Hierarchy
1. Command-line arguments (highest priority)
2. Environment variables
3. Configuration file
4. Default values

### Configuration File Format
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
  max_size_gb: 10

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
```

## Plugin System

### Plugin Architecture
```python
# Plugin interface
class FlashcardPlugin:
    """Base class for pipeline plugins"""
    
    @property
    def name(self) -> str:
        """Plugin name"""
        pass
    
    @property
    def version(self) -> str:
        """Plugin version"""
        pass
    
    def on_startup(self, config: Config) -> None:
        """Called when pipeline starts"""
        pass
    
    def pre_process(self, item: VocabularyItem) -> VocabularyItem:
        """Called before processing each item"""
        return item
    
    def post_process(self, result: FlashcardResult) -> FlashcardResult:
        """Called after processing each item"""
        return result
    
    def on_error(self, error: Exception, item: VocabularyItem) -> None:
        """Called when processing fails"""
        pass
```

### Plugin Discovery
```bash
flashcard-pipeline plugins list         # List installed plugins
flashcard-pipeline plugins install URL  # Install plugin
flashcard-pipeline plugins enable NAME  # Enable plugin
flashcard-pipeline plugins disable NAME # Disable plugin
```

## Error Handling

### Error Categories
1. **Input Errors** (Exit code: 1)
   - Invalid file format
   - Missing required fields
   - Encoding issues

2. **API Errors** (Exit code: 2)
   - Authentication failures
   - Rate limit exceeded
   - Model unavailable

3. **Processing Errors** (Exit code: 3)
   - Parsing failures
   - Validation errors
   - Quality check failures

4. **System Errors** (Exit code: 4)
   - Database errors
   - File system errors
   - Memory issues

### Error Output Format
```json
{
  "error": {
    "code": "E001",
    "category": "input_error",
    "message": "Invalid CSV format",
    "details": "Missing required column: 'term'",
    "file": "input.csv",
    "line": 1,
    "suggestion": "Ensure CSV has columns: position, term, type"
  }
}
```

## Progress & Monitoring

### Progress Indicators
```
Processing vocabulary [████████████░░░░░░░] 75% | 750/1000 items | ETA: 2m 30s
├─ Stage 1: ████████████████████ 100% (cached: 450)
├─ Stage 2: ████████░░░░░░░░░░░░  40% (processing)
├─ Rate: 5.2 items/sec | API calls: 234 | Cache hits: 62%
└─ Errors: 2 | Warnings: 5
```

### Monitoring Metrics
- Processing rate (items/second)
- API call count and costs
- Cache hit ratio
- Error rate
- Token usage
- Memory usage
- Database operations

## Integration Points

### 1. **Stdin/Stdout Support**
```bash
# Pipe from another command
cat vocabulary.csv | flashcard-pipeline process - > output.tsv

# Chain with other tools
flashcard-pipeline export csv | grep "noun" | wc -l
```

### 2. **Environment Variables**
```bash
FLASHCARD_API_KEY=xxx
FLASHCARD_LOG_LEVEL=DEBUG
FLASHCARD_CACHE_DIR=/custom/cache
FLASHCARD_DB_PATH=/custom/db.sqlite
```

### 3. **Exit Codes**
- 0: Success
- 1: Input/argument error
- 2: API error
- 3: Processing error
- 4: System error
- 130: Interrupted (Ctrl+C)

### 4. **Signal Handling**
- SIGINT: Graceful shutdown
- SIGTERM: Save state and exit
- SIGUSR1: Dump statistics
- SIGUSR2: Reload configuration

## Performance Optimization

### 1. **Batch Processing**
- Automatic batching for large inputs
- Configurable batch sizes
- Memory-efficient streaming

### 2. **Concurrent Processing**
- Thread pool for I/O operations
- Async/await for API calls
- Rate limit aware scheduling

### 3. **Caching Strategy**
- Multi-level cache (memory + disk)
- Bloom filters for quick lookups
- Cache warming capabilities

### 4. **Database Optimization**
- Connection pooling
- Prepared statements
- Write-ahead logging
- Periodic VACUUM

## Security Considerations

### 1. **Credential Management**
- No hardcoded credentials
- Support for credential helpers
- Secure storage integration

### 2. **Input Validation**
- Sanitize all user inputs
- Validate file paths
- Check file sizes

### 3. **API Security**
- TLS verification
- Request signing
- Token rotation support

## Testing Strategy

### Unit Tests
- Command parsing
- Input validation
- Output formatting
- Plugin system

### Integration Tests
- API communication
- Database operations
- Cache functionality
- File operations

### End-to-End Tests
- Full pipeline processing
- Error scenarios
- Performance benchmarks
- Concurrent operations

## Future Enhancements

### Planned Features
1. **Interactive Mode**
   - REPL for exploration
   - Visual progress dashboard
   - Real-time editing

2. **Advanced Filtering**
   - SQL-like query language
   - Regular expression support
   - Custom filter functions

3. **Workflow Automation**
   - Scheduled processing
   - Watch mode for folders
   - Webhook integration

4. **Cloud Integration**
   - Remote storage support
   - Distributed processing
   - Team collaboration

### Extension Points
- Custom output formats
- Alternative AI providers
- Language expansion
- Quality metrics

---

This architecture provides a solid foundation for a professional-grade CLI tool that balances ease of use with advanced capabilities.