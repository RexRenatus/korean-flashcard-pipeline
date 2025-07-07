"""Tests for concurrent processing components"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
import time
from datetime import datetime

from flashcard_pipeline.concurrent import (
    OrderedResultsCollector,
    DistributedRateLimiter,
    ConcurrentProgressTracker,
    ConcurrentPipelineOrchestrator,
    OrderedBatchDatabaseWriter,
    ConcurrentProcessingMonitor
)
from flashcard_pipeline.concurrent.ordered_collector import ProcessingResult
from flashcard_pipeline.models import VocabularyItem, Stage1Response, Stage2Response
from flashcard_pipeline.exceptions import RateLimitError


class TestOrderedResultsCollector:
    """Test OrderedResultsCollector functionality"""
    
    @pytest.mark.asyncio
    async def test_order_preservation(self):
        """Test that items maintain order despite concurrent processing"""
        collector = OrderedResultsCollector()
        collector.set_expected_count(5)
        
        # Add results out of order
        results = [
            ProcessingResult(position=3, term="word3", flashcard_data="data3"),
            ProcessingResult(position=1, term="word1", flashcard_data="data1"),
            ProcessingResult(position=5, term="word5", flashcard_data="data5"),
            ProcessingResult(position=2, term="word2", flashcard_data="data2"),
            ProcessingResult(position=4, term="word4", flashcard_data="data4"),
        ]
        
        # Add results concurrently
        tasks = [collector.add_result(r.position, r) for r in results]
        await asyncio.gather(*tasks)
        
        # Get ordered results
        ordered = collector.get_ordered_results()
        
        # Verify order
        assert len(ordered) == 5
        for i, result in enumerate(ordered):
            assert result.position == i + 1
            assert result.term == f"word{i + 1}"
    
    @pytest.mark.asyncio
    async def test_completion_detection(self):
        """Test completion event is set when all results collected"""
        collector = OrderedResultsCollector()
        collector.set_expected_count(3)
        
        # Start waiting for completion
        wait_task = asyncio.create_task(collector.wait_for_all(timeout=1.0))
        
        # Add results
        await collector.add_result(1, ProcessingResult(position=1, term="word1"))
        await collector.add_result(2, ProcessingResult(position=2, term="word2"))
        
        # Should not be complete yet
        assert not wait_task.done()
        
        # Add final result
        await collector.add_result(3, ProcessingResult(position=3, term="word3"))
        
        # Should complete now
        completed = await wait_task
        assert completed is True
    
    @pytest.mark.asyncio
    async def test_statistics(self):
        """Test statistics collection"""
        collector = OrderedResultsCollector()
        collector.set_expected_count(4)
        
        # Add mix of successful and failed results
        await collector.add_result(1, ProcessingResult(
            position=1, term="word1", flashcard_data="data", from_cache=True
        ))
        await collector.add_result(2, ProcessingResult(
            position=2, term="word2", error="API error"
        ))
        await collector.add_result(3, ProcessingResult(
            position=3, term="word3", flashcard_data="data"
        ))
        await collector.add_result(4, ProcessingResult(
            position=4, term="word4", flashcard_data="data", from_cache=True
        ))
        
        stats = collector.get_statistics()
        assert stats["total_expected"] == 4
        assert stats["total_collected"] == 4
        assert stats["successful"] == 3
        assert stats["failed"] == 1
        assert stats["from_cache"] == 2
        assert stats["cache_hit_rate"] == 50.0


class TestDistributedRateLimiter:
    """Test DistributedRateLimiter functionality"""
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test that rate limiter enforces limits"""
        # Create limiter with very low rate for testing
        limiter = DistributedRateLimiter(requests_per_minute=60, buffer_factor=1.0)
        await limiter.start()
        
        try:
            # Acquire tokens rapidly
            acquisition_times = []
            for _ in range(3):
                start = time.time()
                await limiter.acquire(timeout=0.1)
                acquisition_times.append(time.time() - start)
                limiter.release()
            
            # First should be immediate, others may wait
            assert acquisition_times[0] < 0.01  # First is immediate
            
        finally:
            await limiter.stop()
    
    @pytest.mark.asyncio
    async def test_concurrent_rate_limiting(self):
        """Test rate limiting with concurrent requests"""
        limiter = DistributedRateLimiter(requests_per_minute=120, buffer_factor=1.0)
        await limiter.start()
        
        try:
            # Try to acquire many tokens concurrently
            async def acquire_and_release():
                await limiter.acquire()
                await asyncio.sleep(0.01)  # Simulate work
                limiter.release()
            
            # Create concurrent tasks
            tasks = [acquire_and_release() for _ in range(5)]
            
            # All should complete without timeout
            await asyncio.gather(*tasks)
            
            # Check stats
            stats = limiter.get_stats()
            assert stats["total_acquisitions"] == 5
            assert stats["total_releases"] == 5
            
        finally:
            await limiter.stop()
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout when rate limit exceeded"""
        # Create limiter with 1 token
        limiter = DistributedRateLimiter(requests_per_minute=1, buffer_factor=1.0)
        await limiter.start()
        
        try:
            # Acquire the only token
            await limiter.acquire()
            
            # Try to acquire another (should timeout)
            with pytest.raises(RateLimitError):
                await limiter.acquire(timeout=0.1)
            
        finally:
            await limiter.stop()


class TestConcurrentProgressTracker:
    """Test ConcurrentProgressTracker functionality"""
    
    @pytest.mark.asyncio
    async def test_progress_tracking(self):
        """Test progress tracking for concurrent items"""
        tracker = ConcurrentProgressTracker(total_items=10)
        
        # Track some items
        await tracker.start_item(1)
        await tracker.start_item(2)
        await tracker.start_item(3)
        
        stats = tracker.get_stats()
        assert stats["in_progress"] == 3
        assert stats["completed"] == 0
        assert stats["failed"] == 0
        
        # Complete some items
        await tracker.complete_item(1, success=True)
        await tracker.complete_item(2, success=False, error_msg="Test error")
        
        stats = tracker.get_stats()
        assert stats["in_progress"] == 1
        assert stats["completed"] == 1
        assert stats["failed"] == 1
        assert stats["progress_percent"] == 20.0  # 2/10
    
    @pytest.mark.asyncio
    async def test_callback_notifications(self):
        """Test progress callbacks are called"""
        tracker = ConcurrentProgressTracker(total_items=5)
        
        callback_stats = []
        
        def progress_callback(stats):
            callback_stats.append(stats.copy())
        
        tracker.add_callback(progress_callback)
        
        # Make some progress
        await tracker.start_item(1)
        await tracker.complete_item(1, success=True)
        
        # Should have received callbacks
        assert len(callback_stats) >= 2
        assert callback_stats[-1]["completed"] == 1


class TestConcurrentPipelineOrchestrator:
    """Test ConcurrentPipelineOrchestrator functionality"""
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self):
        """Test concurrent processing of vocabulary items"""
        # Create mock API client
        mock_client = AsyncMock()
        mock_client.process_stage1 = AsyncMock(return_value=(
            Stage1Response(
                term="test",
                phonetic="[test]",
                definition_korean="테스트",
                definition_english="test",
                etymology="test origin",
                related_words=["test1", "test2"],
                homonyms=[],
                primary_pos="noun"
            ),
            Mock(total_tokens=100, estimated_cost=0.01)
        ))
        mock_client.process_stage2 = AsyncMock(return_value=(
            Mock(to_tsv=lambda: "1\ttest\t1\tScene\tprimer\tfront\tback\ttags\t"),
            Mock(total_tokens=200, estimated_cost=0.02)
        ))
        
        # Create mock cache service  
        mock_cache = AsyncMock()
        mock_cache.warm_cache_from_batch = AsyncMock(return_value={"stage1_cached": 0})
        mock_cache.get_stage1 = AsyncMock(return_value=None)
        mock_cache.get_stage2 = AsyncMock(return_value=None)
        mock_cache.save_stage1 = AsyncMock()
        mock_cache.save_stage2 = AsyncMock()
        
        # Create orchestrator
        async with ConcurrentPipelineOrchestrator(
            max_concurrent=5,
            api_client=mock_client,
            cache_service=mock_cache
        ) as orchestrator:
            # Process items
            items = [
                VocabularyItem(position=i, term=f"word{i}", type="noun")
                for i in range(1, 11)
            ]
            
            results = await orchestrator.process_batch(items)
            
            # Verify all processed
            assert len(results) == 10
            
            # Verify order maintained
            for i, result in enumerate(results):
                assert result.position == i + 1
                assert result.term == f"word{i + 1}"
                assert result.is_success
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in concurrent processing"""
        # Create mock API client that fails for some items
        mock_client = AsyncMock()
        
        async def mock_stage1(item):
            if item.position == 3:
                raise Exception("API error for position 3")
            return (Mock(), Mock(total_tokens=100))
        
        mock_client.process_stage1 = mock_stage1
        mock_client.process_stage2 = AsyncMock(return_value=(
            Mock(to_tsv=lambda: "tsv_data"),
            Mock(total_tokens=200)
        ))
        
        # Create mock cache
        mock_cache = AsyncMock()
        mock_cache.warm_cache_from_batch = AsyncMock(return_value={"stage1_cached": 0})
        mock_cache.get_stage1 = AsyncMock(return_value=None)
        mock_cache.get_stage2 = AsyncMock(return_value=None)
        
        async with ConcurrentPipelineOrchestrator(
            max_concurrent=3,
            api_client=mock_client,
            cache_service=mock_cache
        ) as orchestrator:
            items = [
                VocabularyItem(position=i, term=f"word{i}", type="noun")
                for i in range(1, 6)
            ]
            
            results = await orchestrator.process_batch(items)
            
            # Should have all results (including failures)
            assert len(results) == 5
            
            # Check specific failure
            assert results[2].position == 3
            assert not results[2].is_success
            assert "API error" in results[2].error


class TestOrderedBatchDatabaseWriter:
    """Test OrderedBatchDatabaseWriter functionality"""
    
    @pytest.mark.asyncio
    async def test_tsv_file_writing(self, tmp_path):
        """Test writing results to TSV file in order"""
        writer = OrderedBatchDatabaseWriter("test.db")
        
        # Create test results
        results = [
            ProcessingResult(
                position=1,
                term="word1",
                flashcard_data="1\tword1\t1\tScene\tprimer1\tfront1\tback1\ttags1\t"
            ),
            ProcessingResult(
                position=2,
                term="word2",
                flashcard_data="2\tword2\t1\tUsage\tprimer2\tfront2\tback2\ttags2\t"
            ),
            ProcessingResult(
                position=3,
                term="word3",
                error="Failed to process"
            ),
        ]
        
        output_file = tmp_path / "output.tsv"
        count = await writer.write_to_file(results, output_file)
        
        # Should write 2 successful results
        assert count == 2
        
        # Verify file content
        content = output_file.read_text(encoding='utf-8')
        lines = content.strip().split('\n')
        
        # Should have header + 2 data rows
        assert len(lines) == 3
        assert lines[0].startswith("position\tterm")
        assert "word1" in lines[1]
        assert "word2" in lines[2]


class TestConcurrentProcessingMonitor:
    """Test ConcurrentProcessingMonitor functionality"""
    
    @pytest.mark.asyncio
    async def test_batch_monitoring(self):
        """Test monitoring batch processing"""
        monitor = ConcurrentProcessingMonitor()
        
        # Start batch
        await monitor.start_batch("batch_001", total_items=100, max_concurrent=50)
        
        # Record some activity
        await monitor.record_concurrent_count(25)
        await monitor.record_concurrent_count(40)
        await monitor.record_concurrent_count(35)
        
        await monitor.record_rate_limit_hit()
        await monitor.record_rate_limit_hit()
        
        await monitor.record_cache_hit()
        await monitor.record_cache_hit()
        await monitor.record_cache_hit()
        
        # Record item processing
        for i in range(10):
            await monitor.record_item_processing(
                position=i,
                success=i != 5,  # Fail position 5
                processing_time_ms=100 + i * 10,
                from_cache=i < 3
            )
        
        # End batch
        await monitor.end_batch("batch_001", {
            "total_successful": 9,
            "total_failed": 1
        })
        
        # Check stats
        stats = monitor.get_current_stats()
        assert stats["concurrent_high_water_mark"] == 40
        assert stats["global_metrics"]["total_rate_limit_hits"] == 2
        assert stats["global_metrics"]["total_cache_hits"] == 3
        assert stats["global_metrics"]["total_successful"] == 9
        assert stats["global_metrics"]["total_failed"] == 1
        
        # Get batch summary
        batch_summary = monitor.get_batch_summary("batch_001")
        assert batch_summary is not None
        assert batch_summary["rate_limit_hits"] == 2
        assert batch_summary["cache_hits"] == 3