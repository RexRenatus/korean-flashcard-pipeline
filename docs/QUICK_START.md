# Quick Start Guide - Korean Flashcard Pipeline

Get up and running in 5 minutes! 🚀

## 1. Prerequisites (1 minute)

✅ Check you have:
- Python 3.8+ installed
- Internet connection
- OpenRouter API key ([Get one here](https://openrouter.ai))

Test Python:
```bash
python --version
# Should show: Python 3.8.x or higher
```

## 2. Installation (2 minutes)

### Clone and Setup
```bash
# Clone repository
git clone https://github.com/yourusername/korean-flashcard-pipeline.git
cd korean-flashcard-pipeline

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configure API Key
Create `.env` file:
```bash
echo "OPENROUTER_API_KEY=your_key_here" > .env
```

## 3. First Flashcard (1 minute)

### Initialize Database
```bash
python -m flashcard_pipeline.cli init-db
```

### Generate Your First Flashcard
```bash
python -m flashcard_pipeline.cli process-word "안녕하세요"
```

Expected output:
```
Processing: 안녕하세요
✓ Flashcard created
✓ Nuance enhancement completed
✓ Saved to database

Flashcard Preview:
- Definition: Hello (formal greeting)
- Romanization: annyeonghaseyo
- Example: 안녕하세요, 만나서 반갑습니다.
```

## 4. Batch Processing (1 minute)

### Create Input File
Create `my_words.csv`:
```csv
word,category,difficulty
안녕하세요,greeting,beginner
감사합니다,politeness,beginner
사랑해요,emotion,intermediate
```

### Process Batch
```bash
python -m flashcard_pipeline.cli process-csv my_words.csv
```

### Export Results
```bash
# Export as Anki deck
python -m flashcard_pipeline.cli export anki

# Export as CSV
python -m flashcard_pipeline.cli export csv --output my_flashcards.csv
```

## 5. Common Workflows

### Daily Study List
```bash
# Create today's words
cat > today.csv << EOF
word,category,difficulty
오늘,time,beginner
내일,time,beginner
어제,time,beginner
EOF

# Process them
python -m flashcard_pipeline.cli process-csv today.csv

# Export for Anki
python -m flashcard_pipeline.cli export anki --tag daily-study
```

### Topic-Based Learning
```bash
# Food vocabulary
python -m flashcard_pipeline.cli process-word "김치" --tag food
python -m flashcard_pipeline.cli process-word "밥" --tag food
python -m flashcard_pipeline.cli process-word "불고기" --tag food

# Export food cards only
python -m flashcard_pipeline.cli export csv --filter-tag food
```

### Quick Lookup
```bash
# Check if word is already processed
python -m flashcard_pipeline.cli lookup "사랑"

# Reprocess with fresh data (no cache)
python -m flashcard_pipeline.cli process-word "사랑" --no-cache
```

## Interactive Mode

Launch interactive shell:
```bash
python -m flashcard_pipeline.cli interactive
```

Quick commands:
```
> process 안녕
> batch my_words.csv
> export anki
> status
> help
> exit
```

## Basic Commands Reference

| Command | Description | Example |
|---------|-------------|---------|
| `process-word` | Process single word | `process-word "안녕"` |
| `process-csv` | Process CSV file | `process-csv words.csv` |
| `export` | Export flashcards | `export anki` |
| `lookup` | Find existing card | `lookup "사랑"` |
| `status` | Check system status | `status` |
| `cache clear` | Clear cache | `cache clear` |

## Next Steps

📚 **Learn More:**
- [Full User Guide](USER_GUIDE.md) - Comprehensive documentation
- [API Reference](API_REFERENCE.md) - For developers
- [Examples](../examples/) - Sample files and scripts

🛠️ **Customize:**
- Edit prompts in `prompts/` directory
- Modify `config.yaml` for advanced settings
- Create custom export templates

💬 **Get Help:**
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [GitHub Issues](https://github.com/yourusername/korean-flashcard-pipeline/issues)
- [Community Discord](https://discord.gg/flashcards)

## Tips for Success

1. **Start Small**: Process 5-10 words first to test your setup
2. **Use Categories**: Organize words by topic for better learning
3. **Regular Exports**: Export to Anki daily for consistent practice
4. **Cache Wisely**: Let cache save you money on repeated words
5. **Check Quality**: Review generated cards and report issues

Happy learning! 화이팅! 💪