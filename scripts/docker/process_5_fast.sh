#!/bin/bash
# Ultra-fast processing script for 5 Korean words
# Uses maximum concurrent processing for speed

echo "⚡ Korean Flashcard Fast Processor"
echo "=================================="
echo ""

# Set up environment
export PYTHONPATH="/mnt/c/Users/JackTheRipper/Desktop/(00) ClaudeCode/Anthropic_Flashcards/src/python"
# OpenRouter API key should be set in environment variables
# export OPENROUTER_API_KEY="your-api-key-here"

# Activate virtual environment
source venv/bin/activate

# Create timestamp for output file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="data/output/flashcards_fast_${TIMESTAMP}.tsv"

echo "🚀 Processing 5 words with MAXIMUM speed (20 concurrent requests)"
echo "Input: data/input/test_5_words_fixed.csv"
echo "Output: $OUTPUT_FILE"
echo ""

# Time the processing
START_TIME=$(date +%s.%N)

# Run with maximum concurrent processing
python -m flashcard_pipeline.cli_v2 process \
    data/input/test_5_words_fixed.csv \
    --output "$OUTPUT_FILE" \
    --concurrent 20 \
    2>/dev/null

END_TIME=$(date +%s.%N)
DURATION=$(echo "$END_TIME - $START_TIME" | bc)

# Show results
echo ""
echo "✅ Processing Complete!"
echo "⏱️  Time taken: ${DURATION} seconds"
echo ""

# Count flashcards generated
CARD_COUNT=$(tail -n +2 "$OUTPUT_FILE" | wc -l)
echo "📊 Statistics:"
echo "   - Words processed: 5"
echo "   - Flashcards generated: $CARD_COUNT"
echo "   - Average time per word: $(echo "scale=2; $DURATION / 5" | bc) seconds"
echo "   - Processing speed: $(echo "scale=1; 5 / $DURATION * 60" | bc) words/minute"
echo ""

# Show sample output
echo "📝 Sample flashcard (first card):"
head -2 "$OUTPUT_FILE" | tail -1 | cut -f2,4,6 | awk -F'\t' '{printf "   Term: %s\n   Type: %s\n   Front: %.60s...\n", $1, $2, $3}'
echo ""
echo "💾 Full results saved to: $OUTPUT_FILE"