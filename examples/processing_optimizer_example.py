#!/usr/bin/env python3
"""
Example usage of the ProcessingOptimizer class.

This script demonstrates how to use the ProcessingOptimizer for concurrent
batch processing with checkpoints, metrics, and progress tracking.
"""

import sys
import os
import time
import logging
from typing import Tuple, Dict, Any
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.python.flashcard_pipeline.processing_optimizer import ProcessingOptimizer, ProcessingMetrics
from src.python.flashcard_pipeline.database.db_manager import DatabaseManager, VocabularyRecord
from src.python.flashcard_pipeline.models import BatchProgress

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def simulate_api_processing(vocab: VocabularyRecord) -> Tuple[bool, Dict[str, Any]]:
    """
    Simulate processing a vocabulary item through the API.
    
    This would normally call your actual API client and process the item.
    For demonstration, we'll simulate with random delays and results.
    """
    import random
    
    # Simulate processing time (50-200ms)
    processing_time = random.uniform(0.05, 0.2)
    time.sleep(processing_time)
    
    # Simulate cache hit (30% chance)
    cache_hit = random.random() < 0.3
    
    # Simulate success (90% chance)
    success = random.random() < 0.9
    
    # Create result data
    result_data = {
        "cache_hit": cache_hit,
        "api_calls": 0 if cache_hit else 1,
        "tokens": 0 if cache_hit else random.randint(500, 2000),
        "cost": 0.0 if cache_hit else random.uniform(0.01, 0.10),
        "vocab_id": vocab.id,
        "korean": vocab.korean
    }
    
    # Simulate occasional errors
    if not success:
        raise Exception(f"Simulated processing error for vocab {vocab.id}")
    
    return success, result_data


def progress_callback(progress: BatchProgress):
    """Handle progress updates"""
    logger.info(
        f"Progress: {progress.completed_items}/{progress.total_items} "
        f"({progress.progress_percentage:.1f}%) - "
        f"Failed: {progress.failed_items} - "
        f"Rate: {progress.items_per_second:.2f} items/s"
    )


def error_callback(error_info: Dict[str, Any]):
    """Handle error notifications"""
    logger.error(
        f"Error processing vocab {error_info.get('vocab_id')}: "
        f"{error_info.get('error')}"
    )


def main():
    """Main example function"""
    # Initialize database manager (use test database)
    db_path = "test_processing_optimizer.db"
    db_manager = DatabaseManager(db_path)
    
    # Create some test vocabulary items if needed
    logger.info("Creating test vocabulary items...")
    test_items = [
        ("안녕하세요", "hello"),
        ("감사합니다", "thank you"),
        ("사랑", "love"),
        ("친구", "friend"),
        ("학교", "school"),
        ("컴퓨터", "computer"),
        ("음식", "food"),
        ("물", "water"),
        ("하늘", "sky"),
        ("바다", "sea"),
    ]
    
    for korean, english in test_items:
        existing = db_manager.get_vocabulary_by_korean(korean)
        if not existing:
            vocab = VocabularyRecord(
                korean=korean,
                english=english,
                type="word"
            )
            db_manager.create_vocabulary(vocab)
    
    # Initialize the ProcessingOptimizer
    optimizer = ProcessingOptimizer(
        db_manager=db_manager,
        max_workers=3,  # 3 concurrent workers
        batch_size=5,   # Process 5 items per batch
        checkpoint_interval=10,  # Save checkpoint every 10 items
        enable_metrics=True
    )
    
    # Add callbacks
    optimizer.add_progress_callback(progress_callback)
    optimizer.add_error_callback(error_callback)
    
    logger.info("Starting processing with ProcessingOptimizer...")
    
    # Process all pending items
    try:
        metrics = optimizer.process_batch_concurrent(
            processor_func=simulate_api_processing,
            total_items=None,  # Process all pending
            resume_from_checkpoint=None,  # Fresh start
            stage="stage1"
        )
        
        # Display final metrics
        logger.info("\n" + "="*50)
        logger.info("Processing Complete! Final Metrics:")
        logger.info("="*50)
        logger.info(f"Total items: {metrics.total_items}")
        logger.info(f"Processed: {metrics.processed_items}")
        logger.info(f"Successful: {metrics.successful_items}")
        logger.info(f"Failed: {metrics.failed_items}")
        logger.info(f"Duration: {metrics.duration_seconds:.2f} seconds")
        logger.info(f"Throughput: {metrics.throughput:.2f} items/second")
        logger.info(f"Cache hit rate: {metrics.cache_hit_rate:.1f}%")
        logger.info(f"Total API calls: {metrics.total_api_calls}")
        logger.info(f"Total tokens: {metrics.total_tokens}")
        logger.info(f"Total cost: ${metrics.total_cost:.2f}")
        logger.info(f"Average latency: {metrics.avg_latency_ms:.2f}ms")
        
        # Demonstrate batch size optimization
        logger.info("\n" + "="*50)
        logger.info("Optimizing batch size based on performance...")
        new_batch_size = optimizer.optimize_batch_size(target_latency_ms=100.0)
        logger.info(f"Optimized batch size: {new_batch_size}")
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise
    
    # Demonstrate checkpoint recovery
    logger.info("\n" + "="*50)
    logger.info("Demonstrating checkpoint recovery...")
    
    # Get the batch ID from the previous run
    batch_id = optimizer._current_batch_id
    
    # Create a new optimizer instance
    optimizer2 = ProcessingOptimizer(
        db_manager=db_manager,
        max_workers=3,
        batch_size=5,
        checkpoint_interval=10,
        enable_metrics=True
    )
    
    # Try to load the checkpoint
    checkpoint = optimizer2.load_checkpoint(batch_id)
    if checkpoint:
        logger.info(f"Loaded checkpoint {checkpoint.checkpoint_id}")
        logger.info(f"Processed items: {len(checkpoint.processed_items)}")
        logger.info(f"Pending items: {len(checkpoint.pending_items)}")
    else:
        logger.info("No checkpoint found")
    
    # Get database statistics
    logger.info("\n" + "="*50)
    logger.info("Database Statistics:")
    stats = db_manager.get_database_stats()
    for key, value in stats.items():
        if isinstance(value, dict):
            logger.info(f"{key}:")
            for k, v in value.items():
                logger.info(f"  {k}: {v}")
        else:
            logger.info(f"{key}: {value}")


if __name__ == "__main__":
    main()