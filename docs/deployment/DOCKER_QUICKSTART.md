# Docker Quick Start Guide

This guide will help you quickly get started with the Korean Flashcard Pipeline using Docker.

## Prerequisites

- Docker and Docker Compose installed
- OpenRouter API key

## Initial Setup

1. **Create your environment file**:
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENROUTER_API_KEY
   ```

2. **Build the Docker image**:
   ```bash
   docker-compose build
   ```

## Running the Pipeline

### Step 1: Run Database Migrations

Before processing any vocabulary, you need to set up the database:

```bash
./docker-migrate.sh
```

This will:
- Create the database if it doesn't exist
- Run all migrations in order
- Show you the database status

### Step 2: Process Vocabulary

To process the first 100 words from the vocabulary list:

```bash
./docker-process.sh
```

To process a custom vocabulary file:

```bash
./docker-process.sh path/to/your/vocabulary.csv
```

The processed flashcards will be saved to `data/output/hsk_100_processed.tsv`

## What Happens During Processing

1. **Stage 1 - Semantic Analysis**: Each vocabulary item is analyzed for context and meaning
2. **Stage 2 - Flashcard Generation**: Detailed flashcards are created with:
   - Reading (pronunciation)
   - Definition
   - Part of speech
   - Example sentences (Korean and English)
   - Common collocations
   - Formality/politeness levels
   - Cultural notes
   - Synonyms/antonyms
   - And more...

## Directory Structure

```
data/
├── input/          # Input vocabulary files
├── output/         # Processed flashcard files
├── cache/          # API response cache
└── flashcards.db   # SQLite database
```

## Useful Commands

### View database tables:
```bash
docker-compose run --rm flashcard-pipeline \
  sqlite3 /app/data/flashcards.db ".tables"
```

### Run CLI commands:
```bash
# Show help
docker-compose run --rm flashcard-pipeline \
  python -m flashcard_pipeline.pipeline_cli --help

# Import vocabulary to database
docker-compose run --rm flashcard-pipeline \
  python -m flashcard_pipeline.pipeline_cli ingress import /app/data/input/vocabulary.csv

# Process from database
docker-compose run --rm flashcard-pipeline \
  python -m flashcard_pipeline.pipeline_cli process --source database
```

### Extract first 100 words for testing:
```bash
./prepare_first_100.sh
```

## Troubleshooting

### API Key Error
If you see "OPENROUTER_API_KEY not found", make sure:
1. Your `.env` file exists
2. It contains: `OPENROUTER_API_KEY=your-actual-key-here`

### Database Errors
If you encounter database errors:
1. Remove the old database: `rm data/flashcards.db`
2. Run migrations again: `./docker-migrate.sh`

### Rate Limiting
The pipeline includes rate limiting (30 requests/minute by default). If you hit rate limits:
- The pipeline will automatically wait
- Consider processing in smaller batches

## Example Output

A processed flashcard looks like this:

```
term: 내가
reading: nɛ.ka
definition: I (informal subject form)
part_of_speech: pronoun
example_korean: 내가 밥을 먹었어
example_english: I ate rice
formality_level: informal
politeness_level: casual
...
```

## Next Steps

- Review the processed flashcards in `data/output/`
- Import them into your preferred flashcard application
- Process additional vocabulary files as needed