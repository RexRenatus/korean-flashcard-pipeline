#!/usr/bin/env python3
"""
Example: Using the Korean Flashcard Pipeline

This example demonstrates how to use both the sequential and concurrent pipelines
to process Korean vocabulary and generate flashcards.
"""

import asyncio
from pathlib import Path
from flashcard_pipeline import PipelineOrchestrator, ConcurrentPipelineOrchestrator
from flashcard_pipeline.models import VocabularyItem
from flashcard_pipeline.api_client import OpenRouterClient
from flashcard_pipeline.cache import CacheService
from flashcard_pipeline.rate_limiter import CompositeLimiter
from flashcard_pipeline.circuit_breaker import MultiServiceCircuitBreaker


async def sequential_pipeline_example():
    """Example of using the sequential pipeline"""
    print("=== Sequential Pipeline Example ===\n")
    
    # Create vocabulary items
    items = [
        VocabularyItem(position=1, term="안녕하세요", type="phrase"),
        VocabularyItem(position=2, term="감사합니다", type="phrase"),
        VocabularyItem(position=3, term="사랑", type="noun"),
    ]
    
    # Use the pipeline orchestrator
    async with PipelineOrchestrator() as pipeline:
        output_file = Path("output_sequential.tsv")
        
        # Process batch
        batch_progress = await pipeline.process_batch(
            items=items,
            output_file=output_file
        )
        
        print(f"Batch ID: {batch_progress.batch_id}")
        print(f"Total items: {batch_progress.total_items}")
        print(f"Completed: {batch_progress.completed_items}")
        print(f"Failed: {batch_progress.failed_items}")
        print(f"Progress: {batch_progress.progress_percentage:.1f}%")
        print(f"\nResults saved to: {output_file}")


async def concurrent_pipeline_example():
    """Example of using the concurrent pipeline"""
    print("\n=== Concurrent Pipeline Example ===\n")
    
    # Create more vocabulary items for concurrent processing
    items = [
        VocabularyItem(position=i, term=term, type=type_)
        for i, (term, type_) in enumerate([
            ("안녕하세요", "phrase"),
            ("감사합니다", "phrase"),
            ("사랑", "noun"),
            ("행복", "noun"),
            ("공부하다", "verb"),
            ("먹다", "verb"),
            ("예쁘다", "adjective"),
            ("크다", "adjective"),
        ], start=1)
    ]
    
    # Configure components
    api_client = OpenRouterClient(
        rate_limiter=CompositeLimiter(),
        circuit_breaker=MultiServiceCircuitBreaker(),
        cache_service=CacheService()
    )
    
    # Use the concurrent orchestrator
    async with ConcurrentPipelineOrchestrator(
        max_concurrent=5,  # Process up to 5 items concurrently
        api_client=api_client,
        cache_service=CacheService(),
        rate_limit_rpm=600
    ) as orchestrator:
        # Process batch
        results = await orchestrator.process_batch(items)
        
        # Save results to TSV
        output_file = Path("output_concurrent.tsv")
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write("position\tterm\tterm_number\ttab_name\tprimer\tfront\tback\ttags\thonorific_level\n")
            
            # Write results
            for result in results:
                if result.flashcard_data and not result.error:
                    f.write(result.flashcard_data)
                    if not result.flashcard_data.endswith('\n'):
                        f.write('\n')
        
        # Get statistics
        stats = orchestrator.get_statistics()
        print(f"Total batches: {stats['batches_processed']}")
        print(f"Total items: {stats['total_items']}")
        print(f"Successful: {stats['total_successful']}")
        print(f"Failed: {stats['total_failed']}")
        print(f"From cache: {stats['total_from_cache']}")
        print(f"Success rate: {stats['success_rate']:.1f}%")
        print(f"Average time: {stats['average_processing_time']:.0f}ms")
        print(f"\nResults saved to: {output_file}")


async def checkpoint_resume_example():
    """Example of using checkpoint/resume functionality"""
    print("\n=== Checkpoint/Resume Example ===\n")
    
    # This example shows how to resume a batch that was interrupted
    batch_id = "batch_20240108_120000"
    
    print(f"Resuming batch: {batch_id}")
    print("Note: In a real scenario, this would resume from where it left off")
    print("      by checking the database for completed items.\n")
    
    # Create items (in real use, you'd load only unprocessed items)
    items = [
        VocabularyItem(position=4, term="책", type="noun"),
        VocabularyItem(position=5, term="물", type="noun"),
    ]
    
    async with PipelineOrchestrator() as pipeline:
        output_file = Path("output_resumed.tsv")
        
        # Process with existing batch ID
        batch_progress = await pipeline.process_batch(
            items=items,
            output_file=output_file,
            batch_id=batch_id  # Resume existing batch
        )
        
        print(f"Resumed batch completed!")
        print(f"Additional items processed: {batch_progress.completed_items}")


async def main():
    """Run all examples"""
    # Ensure we have API key
    import os
    if not os.environ.get('OPENROUTER_API_KEY'):
        print("ERROR: Please set OPENROUTER_API_KEY environment variable")
        print("       You can also create a .env file with:")
        print("       OPENROUTER_API_KEY=your-api-key-here")
        return
    
    # Run examples
    await sequential_pipeline_example()
    await concurrent_pipeline_example()
    await checkpoint_resume_example()
    
    print("\n=== All examples completed! ===")
    print("\nNext steps:")
    print("1. Check the generated TSV files")
    print("2. Import them into your flashcard application")
    print("3. Monitor cache statistics with: python -m flashcard_pipeline cache-stats")


if __name__ == "__main__":
    asyncio.run(main())