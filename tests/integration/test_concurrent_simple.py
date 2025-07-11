"""Simple test script for concurrent processing"""

import asyncio
from pathlib import Path
import sys
import pytest

from flashcard_pipeline.concurrent import OrderedResultsCollector, DistributedRateLimiter
from flashcard_pipeline.concurrent.ordered_collector import ProcessingResult


@pytest.mark.asyncio
async def test_ordered_collector():
    """Test basic ordered collector functionality"""
    print("Testing OrderedResultsCollector...")
    
    collector = OrderedResultsCollector()
    collector.set_expected_count(3)
    
    # Add results out of order
    await collector.add_result(2, ProcessingResult(position=2, term="word2", flashcard_data="data2"))
    await collector.add_result(1, ProcessingResult(position=1, term="word1", flashcard_data="data1"))
    await collector.add_result(3, ProcessingResult(position=3, term="word3", flashcard_data="data3"))
    
    # Get ordered results
    ordered = collector.get_ordered_results()
    
    # Verify order
    for i, result in enumerate(ordered):
        assert result.position == i + 1
        assert result.term == f"word{i + 1}"
        print(f"✓ Position {result.position}: {result.term}")
    
    print("✓ OrderedResultsCollector test passed!\n")


@pytest.mark.asyncio
async def test_rate_limiter():
    """Test basic rate limiter functionality"""
    print("Testing DistributedRateLimiter...")
    
    limiter = DistributedRateLimiter(requests_per_minute=600, buffer_factor=0.8)
    await limiter.start()
    
    try:
        # Acquire some tokens
        for i in range(5):
            wait_time = await limiter.acquire(timeout=1.0)
            print(f"✓ Acquired token {i+1}, wait time: {wait_time:.3f}s")
            limiter.release()
        
        stats = limiter.get_stats()
        print(f"\nStats: {stats['total_acquisitions']} acquisitions, "
              f"{stats['current_available']} available")
        
    finally:
        await limiter.stop()
    
    print("✓ DistributedRateLimiter test passed!\n")


# The main function is no longer needed as pytest will run the tests