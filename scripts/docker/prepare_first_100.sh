#!/bin/bash
#
# Extract first 100 words from the vocabulary list for testing
#

set -e

echo "Preparing first 100 words from vocabulary list..."

# Create input directory
mkdir -p data/input

# Extract header + first 100 rows
head -n 101 docs/10K_HSK_List.csv > data/input/hsk_first_100.csv

echo "✅ Created data/input/hsk_first_100.csv with first 100 vocabulary items"
echo ""
echo "You can now process this file with:"
echo "  ./docker-process.sh data/input/hsk_first_100.csv"
echo ""
echo "Or process directly from the main file (first 100 only):"
echo "  ./docker-process.sh"