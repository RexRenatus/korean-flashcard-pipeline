# Korean Flashcard Processor 🇰🇷

A simple CLI tool to convert Korean vocabulary into AI-generated flashcards using memory palace techniques.

## Features ✨

- 🤖 AI-powered flashcard generation using Claude 3.5 Sonnet
- 🏃 Concurrent processing for faster results
- 📊 Progress tracking with real-time updates
- 🎯 Interactive prompts for easy configuration
- 💾 TSV output format compatible with Anki and other flashcard apps

## Quick Start 🚀

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up API Key

Get your OpenRouter API key from https://openrouter.ai/keys

Create a `.env` file:
```bash
OPENROUTER_API_KEY=your-api-key-here
```

### 3. Run the Tool

#### Interactive Mode (Recommended)
```bash
python flashcard_processor.py process
```

The tool will prompt you for:
- Input CSV file path
- Output file location
- Number of cards to process
- Processing speed (1-20 concurrent requests)

#### Command Line Mode
```bash
python flashcard_processor.py process \
    --input vocabulary.csv \
    --output flashcards.tsv \
    --limit 10 \
    --concurrent 5
```

## Input File Format 📝

Your CSV file should have these columns:
```csv
position,term,type
1,안녕하세요,phrase
2,감사합니다,phrase
3,사랑,noun
```

- **position**: Number for ordering (1, 2, 3...)
- **term**: Korean word or phrase
- **type**: Part of speech (noun, verb, adjective, phrase, etc.)

## Commands 🛠️

### Generate Example File
```bash
python flashcard_processor.py example
```
Creates `example_vocabulary.csv` with sample Korean words.

### Test API Connection
```bash
python flashcard_processor.py test
```
Verifies your API key is working correctly.

### Get Help
```bash
python flashcard_processor.py --help
```

## Output Format 📤

The tool generates TSV files with these columns:
- **position**: Card order
- **term**: Korean term with pronunciation
- **term_number**: Original position from input
- **tab_name**: Card type (Scene, Usage-Comparison, Hanja)
- **primer**: Memory palace setup instructions
- **front**: Question for flashcard front
- **back**: Detailed answer with vivid imagery
- **tags**: Metadata tags
- **honorific_level**: Formality level information

## Tips 💡

1. **Start Small**: Process 5-10 words first to test your setup
2. **Batch Processing**: The tool handles up to 20 concurrent requests
3. **Cost Estimation**: ~$0.003 per vocabulary item (varies by complexity)
4. **Rate Limits**: The tool automatically manages API rate limits

## Troubleshooting 🔧

### "API key not found"
- Make sure `.env` file exists in the same directory
- Check that your API key is correct

### "Connection error"
- Verify internet connection
- Check if OpenRouter API is accessible
- Try reducing concurrent requests

### "Invalid CSV format"
- Ensure your CSV has the required columns
- Check for UTF-8 encoding
- Remove any special characters from headers

## Example Usage 📖

```bash
# Create example file
python flashcard_processor.py example

# Process with interactive prompts
python flashcard_processor.py process

# Process specific file
python flashcard_processor.py process -i korean_words.csv -o my_flashcards.tsv -l 20 -c 10
```

## Support 🤝

For issues or questions:
- Check the error messages for specific guidance
- Ensure all dependencies are installed
- Verify your API key has sufficient credits

Happy learning! 화이팅! 💪