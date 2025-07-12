# Examples Directory

This directory contains example files, scripts, and use cases for the Korean Language Flashcard Pipeline.

## Overview

Examples help users understand how to use the system effectively by providing:
- Sample input files
- Example scripts
- Common use cases
- Integration examples
- Best practices demonstrations

## Directory Structure

```
examples/
├── input/               # Sample input files
│   ├── basic_vocab.csv      # Simple vocabulary list
│   ├── advanced_vocab.csv   # Complex vocabulary with all fields
│   ├── phrases.csv          # Korean phrases
│   └── grammar.csv          # Grammar patterns
├── scripts/             # Example Python scripts
│   ├── basic_usage.py       # Simple pipeline usage
│   ├── batch_processing.py  # Processing multiple files
│   ├── custom_pipeline.py   # Customized pipeline
│   └── api_integration.py   # Direct API usage
├── output/              # Example output files
│   ├── flashcards.json      # JSON output example
│   ├── anki_deck.apkg       # Anki format example
│   └── study_guide.md       # Markdown format
└── configs/             # Example configurations
    ├── basic_config.yaml    # Minimal configuration
    ├── advanced_config.yaml # Full configuration
    └── .env.example         # Environment variables

```

## Example Categories

### 1. Input Examples

#### Basic Vocabulary (`input/basic_vocab.csv`)
```csv
korean,english,type
안녕하세요,Hello,phrase
책,book,noun
읽다,to read,verb
```

#### Advanced Vocabulary (`input/advanced_vocab.csv`)
```csv
korean,english,type,difficulty,hanja,romanization,tags,notes
안녕하세요,Hello (formal),phrase,1,,annyeonghaseyo,"greeting,formal",Common greeting
책,book,noun,1,冊,chaek,"object,education",Also means volume
읽다,to read,verb,2,,ilkda,"action,education",Irregular verb
```

### 2. Script Examples

#### Basic Usage (`scripts/basic_usage.py`)
```python
#!/usr/bin/env python3
"""Basic example of using the flashcard pipeline."""

import asyncio
from flashcard_pipeline import Pipeline, VocabularyItem

async def main():
    # Initialize pipeline
    pipeline = Pipeline(api_key="your-api-key")
    
    # Create vocabulary items
    items = [
        VocabularyItem(korean="안녕하세요", english="Hello"),
        VocabularyItem(korean="감사합니다", english="Thank you")
    ]
    
    # Process items
    results = await pipeline.process(items)
    
    # Display results
    for result in results:
        print(f"Korean: {result.korean}")
        print(f"Flashcard: {result.front} | {result.back}")
        print("---")

if __name__ == "__main__":
    asyncio.run(main())
```

#### Batch Processing (`scripts/batch_processing.py`)
```python
#!/usr/bin/env python3
"""Example of processing multiple files concurrently."""

import asyncio
from pathlib import Path
from flashcard_pipeline import Pipeline

async def process_file(pipeline, file_path):
    """Process a single CSV file."""
    print(f"Processing {file_path.name}...")
    results = await pipeline.process_csv(file_path)
    print(f"Completed {file_path.name}: {len(results)} flashcards")
    return results

async def main():
    # Initialize pipeline with concurrent processing
    pipeline = Pipeline(
        api_key="your-api-key",
        max_concurrent=10
    )
    
    # Find all CSV files
    input_dir = Path("input")
    csv_files = list(input_dir.glob("*.csv"))
    
    # Process all files concurrently
    tasks = [process_file(pipeline, f) for f in csv_files]
    results = await asyncio.gather(*tasks)
    
    # Summary
    total = sum(len(r) for r in results)
    print(f"\nTotal flashcards created: {total}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Configuration Examples

#### Basic Configuration (`configs/basic_config.yaml`)
```yaml
# Minimal configuration for flashcard pipeline
api:
  provider: openrouter
  model: anthropic/claude-3-sonnet

processing:
  batch_size: 10
  cache_enabled: true

output:
  format: json
  directory: ./output
```

#### Advanced Configuration (`configs/advanced_config.yaml`)
```yaml
# Complete configuration with all options
api:
  provider: openrouter
  model: anthropic/claude-3-sonnet
  api_key_env: OPENROUTER_API_KEY
  timeout: 30
  max_retries: 3

processing:
  batch_size: 50
  max_concurrent: 10
  cache_enabled: true
  cache_ttl: 86400  # 24 hours

database:
  path: ./flashcards.db
  connection_pool_size: 5

output:
  format: json
  directory: ./output
  include_metadata: true
  compress: true

monitoring:
  enabled: true
  log_level: INFO
  metrics_enabled: true

features:
  auto_romanization: true
  difficulty_detection: true
  example_generation: true
  cultural_notes: true
```

### 4. Output Examples

#### JSON Output (`output/flashcards.json`)
```json
{
  "flashcards": [
    {
      "id": "fc_001",
      "korean": "안녕하세요",
      "english": "Hello (formal)",
      "front": "안녕하세요",
      "back": "Hello (formal)\n[an-nyeong-ha-se-yo]\n\nUsed when greeting someone politely.",
      "tags": ["greeting", "formal", "beginner"],
      "difficulty": 1,
      "examples": [
        {
          "korean": "안녕하세요, 만나서 반갑습니다.",
          "english": "Hello, nice to meet you."
        }
      ]
    }
  ],
  "metadata": {
    "created": "2024-01-09T10:30:00Z",
    "version": "1.0",
    "total_cards": 1
  }
}
```

## How to Use Examples

### Running Example Scripts

1. **Setup Environment**
   ```bash
   cd examples
   pip install -r ../requirements.txt
   export OPENROUTER_API_KEY=your-key
   ```

2. **Run Basic Example**
   ```bash
   python scripts/basic_usage.py
   ```

3. **Try Batch Processing**
   ```bash
   python scripts/batch_processing.py
   ```

### Using Example Input Files

1. Copy example files as templates
2. Modify for your vocabulary
3. Process with the pipeline
4. Check output directory

### Customizing Examples

Feel free to:
- Modify scripts for your needs
- Combine features from different examples
- Create new examples
- Share useful patterns

## Best Practices Demonstrated

1. **Error Handling**: All examples include proper error handling
2. **Async/Await**: Proper use of async patterns
3. **Configuration**: Different configuration approaches
4. **Logging**: Appropriate logging levels
5. **Resource Management**: Proper cleanup and connection handling

## Contributing Examples

To add new examples:
1. Follow the existing structure
2. Include clear documentation
3. Test thoroughly
4. Add to this README
5. Submit PR

## Notes

- Replace `your-api-key` with actual API key
- Example outputs are for illustration
- Some features may require specific API plans
- Check current API limits before batch processing