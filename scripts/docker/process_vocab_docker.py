#!/usr/bin/env python3
"""Process vocabulary from HSK list using the flashcard pipeline"""

import os
import sys
import csv
import asyncio
from pathlib import Path

# Add the src/python directory to the path
sys.path.insert(0, '/app/src/python')

from flashcard_pipeline import (
    OpenRouterClient,
    VocabularyItem,
    CacheService,
    RateLimiter,
    CircuitBreaker
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/.env')

async def process_vocabulary():
    """Process the first 100 words from the HSK list"""
    
    # Initialize API client with resilience features
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print("Error: OPENROUTER_API_KEY not found in environment")
        return
    
    # Initialize components
    cache_service = CacheService(cache_dir=Path('/app/data/cache'))
    rate_limiter = RateLimiter(requests_per_minute=30)
    circuit_breaker = CircuitBreaker()
    
    client = OpenRouterClient(
        api_key=api_key,
        cache_service=cache_service,
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker
    )
    
    # Read vocabulary file
    vocab_file = Path('/app/docs/10K_HSK_List.csv')
    if not vocab_file.exists():
        print(f"Error: File not found: {vocab_file}")
        return
    
    items = []
    with open(vocab_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 100:  # Process only first 100 words
                break
            
            # Create vocabulary item from CSV data
            # CSV columns: Position,Hangul,IPA_Pronunciation,Word_Type,TOPIK_Level,Definition,etc.
            item = VocabularyItem(
                term=row.get('Hangul', ''),
                pos=row.get('Word_Type', ''),  # pos instead of type
                level=f"TOPIK_{row.get('TOPIK_Level', '1')}",  # Convert TOPIK level
                definition=row.get('Definition', ''),
                example=row.get('Example_Sentence', '')
            )
            items.append(item)
    
    print(f"Loaded {len(items)} vocabulary items")
    
    # Process items
    output_file = Path('/app/data/output/hsk_100_processed.tsv')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter='\t')
        # Write header matching FlashcardRow fields
        writer.writerow([
            'term', 'reading', 'definition', 'part_of_speech', 
            'example_korean', 'example_english', 'common_collocations',
            'formality_level', 'politeness_level', 'nuance',
            'gender_specific', 'appropriate_context', 'etymology',
            'cultural_note', 'synonyms', 'antonyms',
            'frequency', 'difficulty_level', 'semantic_field',
            'register', 'loan_word_origin', 'hanja'
        ])
        
        # Track statistics
        success_count = 0
        error_count = 0
        
        for i, item in enumerate(items):
            print(f"Processing {i+1}/{len(items)}: {item.term}")
            
            try:
                # Process through both stages using the complete pipeline
                result, tokens = await client.process_item_complete(item)
                
                if result and result.stage2_response and result.stage2_response.flashcards:
                    # Get the first flashcard from the response
                    fc = result.stage2_response.flashcards[0]
                    
                    # Write all flashcard fields
                    writer.writerow([
                        fc.term,
                        fc.reading,
                        fc.definition,
                        fc.part_of_speech,
                        fc.example_korean,
                        fc.example_english,
                        ', '.join(fc.common_collocations) if fc.common_collocations else '',
                        fc.formality_level,
                        fc.politeness_level,
                        fc.nuance,
                        'Yes' if fc.gender_specific else 'No',
                        fc.appropriate_context,
                        fc.etymology or '',
                        fc.cultural_note or '',
                        ', '.join(fc.synonyms) if fc.synonyms else '',
                        ', '.join(fc.antonyms) if fc.antonyms else '',
                        fc.frequency,
                        fc.difficulty_level,
                        fc.semantic_field,
                        fc.register,
                        fc.loan_word_origin or '',
                        fc.hanja or ''
                    ])
                    print(f"✓ Processed: {fc.term} (tokens used: {tokens})")
                    success_count += 1
                else:
                    print(f"✗ Failed: {item.term} - No flashcard generated")
                    error_count += 1
                    
            except Exception as e:
                print(f"✗ Error processing {item.term}: {e}")
                error_count += 1
        
        print(f"\n{'='*50}")
        print(f"Processing Summary:")
        print(f"  Total items: {len(items)}")
        print(f"  Successful: {success_count}")
        print(f"  Failed: {error_count}")
        print(f"  Success rate: {success_count/len(items)*100:.1f}%")
    
    print(f"\nProcessing complete! Results saved to: {output_file}")

def main():
    """Main entry point for the script"""
    try:
        # Run the async process_vocabulary function
        asyncio.run(process_vocabulary())
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()