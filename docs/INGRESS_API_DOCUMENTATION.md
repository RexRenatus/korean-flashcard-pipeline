# Ingress API Documentation

## Overview

The Ingress feature provides a database-driven approach to managing vocabulary items for the Korean Flashcard Pipeline. This documentation covers all CLI commands and their usage.

## CLI Commands

### 1. Import CSV to Database

```bash
flashcard-pipeline ingress import <csv_file> [OPTIONS]
```

**Description**: Import a CSV vocabulary file into the database for processing.

**Arguments**:
- `csv_file` (required): Path to the CSV file containing vocabulary items

**Options**:
- `--batch-id`: Custom batch ID (auto-generated if not provided)
- `--db-path`: Database path (defaults to DATABASE_PATH env var or ./pipeline.db)

**Example**:
```bash
# Import with auto-generated batch ID
flashcard-pipeline ingress import vocabulary.csv

# Import with custom batch ID
flashcard-pipeline ingress import vocabulary.csv --batch-id batch_2024_01_08
```

**CSV Format**:
```csv
position,term,type
1,안녕하세요,phrase
2,감사합니다,phrase
3,사랑,word
```

### 2. List Import Batches

```bash
flashcard-pipeline ingress list-batches [OPTIONS]
```

**Description**: List all import batches with their status and statistics.

**Options**:
- `--status`: Filter by status (pending, processing, completed, failed, partial)
- `--limit`: Number of batches to show (default: 20)
- `--db-path`: Database path

**Example**:
```bash
# List all batches
flashcard-pipeline ingress list-batches

# List only pending batches
flashcard-pipeline ingress list-batches --status pending

# List last 50 batches
flashcard-pipeline ingress list-batches --limit 50
```

### 3. Check Batch Status

```bash
flashcard-pipeline ingress status <batch_id> [OPTIONS]
```

**Description**: Get detailed status of a specific import batch.

**Arguments**:
- `batch_id` (required): The batch ID to check

**Options**:
- `--db-path`: Database path

**Example**:
```bash
flashcard-pipeline ingress status batch_20240108_143052_a1b2c3d4
```

### 4. Process from Database

```bash
flashcard-pipeline process --source database [OPTIONS]
```

**Description**: Process vocabulary items from the database instead of CSV files.

**Options**:
- `--source`: Set to "database" for database processing
- `--db-batch-id`: Process specific batch ID only
- `--output`: Output TSV file (default: output.tsv)
- `--limit`: Limit number of items to process
- `--concurrent`: Enable concurrent processing (max 50)
- `--cache-dir`: Cache directory

**Example**:
```bash
# Process all pending items
flashcard-pipeline process --source database

# Process specific batch
flashcard-pipeline process --source database --db-batch-id batch_20240108_143052_a1b2c3d4

# Process with concurrency
flashcard-pipeline process --source database --concurrent 20 --limit 100
```

## Data Flow

### 1. Import Flow
```
CSV File → Ingress Import → vocabulary_items table → Status: pending
```

### 2. Processing Flow
```
vocabulary_items (pending) → Pipeline Processing → Flashcard Generation → Status: completed/failed
```

### 3. Status Transitions
```
pending → processing → completed
                    ↘ failed
                    ↘ partial (some items failed)
```

## Database Schema

### vocabulary_items Table
- `id`: Auto-incrementing primary key
- `korean`: Korean term (unique)
- `english`: English translation
- `type`: Item type (word, phrase, idiom, grammar)
- `source_file`: Original CSV filename
- `import_batch_id`: Associated batch ID
- `status`: Processing status
- `created_at`: Import timestamp
- `updated_at`: Last update timestamp

### import_batches Table
- `id`: Batch ID (text primary key)
- `source_file`: Source CSV filename
- `total_items`: Total items in batch
- `processed_items`: Successfully processed count
- `failed_items`: Failed processing count
- `status`: Batch status
- `created_at`: Batch creation time
- `completed_at`: Batch completion time

## Docker Usage

### Using Docker Compose

```bash
# Import CSV using Docker
docker-compose run flashcard-pipeline python -m flashcard_pipeline.pipeline_cli ingress import /app/data/input/vocabulary.csv

# List batches
docker-compose run flashcard-pipeline python -m flashcard_pipeline.pipeline_cli ingress list-batches

# Process from database
docker-compose run flashcard-pipeline python -m flashcard_pipeline.pipeline_cli process --source database
```

### Direct Docker Commands

```bash
# Build image
docker build -t korean-flashcard-pipeline .

# Import CSV
docker run -v $(pwd)/data:/app/data korean-flashcard-pipeline \
  python -m flashcard_pipeline.pipeline_cli ingress import /app/data/input/vocabulary.csv

# Process from database
docker run -v $(pwd)/data:/app/data -v $(pwd)/.env:/app/.env korean-flashcard-pipeline \
  python -m flashcard_pipeline.pipeline_cli process --source database
```

## Environment Variables

The following environment variables affect ingress operations:

```env
# Database location
DATABASE_PATH=./pipeline.db

# Ingress settings
INGRESS_BATCH_SIZE=1000        # Max items per batch
INGRESS_AUTO_PROCESS=false     # Auto-process after import
INGRESS_CLEANUP_DAYS=30        # Days to keep completed batches
DATABASE_POOL_SIZE=5           # Connection pool size
```

## Error Handling

### Common Errors

1. **Duplicate Items**: Items with duplicate Korean terms are skipped during import
2. **Invalid CSV Format**: Rows missing required fields are skipped with warnings
3. **Database Locked**: Use SQLite WAL mode for concurrent access
4. **Processing Failures**: Failed items remain in 'pending' status for retry

### Retry Strategy

Failed items can be reprocessed by:
1. Running process command again (picks up pending items)
2. Resetting item status in database
3. Creating new import batch with failed items only

## Best Practices

1. **Batch Naming**: Use descriptive batch IDs for easy tracking
2. **Concurrent Processing**: Start with 10-20 concurrent for optimal performance
3. **Regular Cleanup**: Remove old completed batches periodically
4. **Monitor Progress**: Use `ingress status` to track batch progress
5. **Error Recovery**: Check logs for failed items and retry as needed

## Migration from CSV-based Processing

To migrate existing CSV-based workflows:

1. Import all CSV files to database:
   ```bash
   flashcard-pipeline ingress import vocabulary1.csv
   flashcard-pipeline ingress import vocabulary2.csv
   ```

2. Process from database instead of CSV:
   ```bash
   # Old way
   flashcard-pipeline process vocabulary.csv
   
   # New way
   flashcard-pipeline process --source database
   ```

3. Benefits:
   - Resume interrupted processing
   - Track processing history
   - Process multiple sources together
   - Better error recovery
   - Performance analytics