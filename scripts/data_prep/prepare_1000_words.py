#!/usr/bin/env python3
"""Extract and format first 1000 words from 10K_HSK_List.csv"""

import csv

# Read the source file and extract first 1000 words
input_file = "docs/10K_HSK_List.csv"
output_file = "data/input/vocabulary_1000.csv"

with open(input_file, 'r', encoding='utf-8') as infile:
    reader = csv.DictReader(infile)
    
    with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        # Write header for our pipeline format
        writer = csv.writer(outfile)
        writer.writerow(['position', 'term', 'type'])
        
        count = 0
        for row in reader:
            if count >= 1000:
                break
            
            # Map columns: Position -> position, Hangul -> term, Word_Type -> type
            position = row.get('Position', str(count + 1))
            term = row.get('Hangul', '')
            word_type = row.get('Word_Type', 'unknown')
            
            if term:  # Only write if we have a term
                writer.writerow([position, term, word_type])
                count += 1
        
        print(f"✓ Extracted {count} words to {output_file}")

# Also create a sample file for testing cache efficiency
sample_file = "data/input/vocabulary_sample_100.csv"
with open(input_file, 'r', encoding='utf-8') as infile:
    reader = csv.DictReader(infile)
    
    with open(sample_file, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(['position', 'term', 'type'])
        
        count = 0
        for row in reader:
            if count >= 100:
                break
            
            position = row.get('Position', str(count + 1))
            term = row.get('Hangul', '')
            word_type = row.get('Word_Type', 'unknown')
            
            if term:
                writer.writerow([position, term, word_type])
                count += 1
        
        print(f"✓ Created sample file with {count} words at {sample_file}")