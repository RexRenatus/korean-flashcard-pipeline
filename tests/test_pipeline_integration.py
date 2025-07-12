"""Test Phase 4 Pipeline Integration"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from pathlib import Path

from flashcard_pipeline.pipeline_cli import PipelineOrchestrator
from flashcard_pipeline.concurrent import ConcurrentPipelineOrchestrator
from flashcard_pipeline.models import (
    VocabularyItem,
    Stage1Response,
    Stage2Response,
    FlashcardRow,
    ApiUsage,
    Comparison
)


class TestPipelineOrchestrator:
    """Test sequential pipeline orchestrator"""
    
    @pytest.mark.asyncio
    async def test_pipeline_initialization(self):
        """Test that pipeline initializes correctly"""
        orchestrator = PipelineOrchestrator()
        assert orchestrator.cache_service is not None
        assert orchestrator.rate_limiter is not None
        assert orchestrator.circuit_breaker is not None
        assert orchestrator.client is None  # Lazy initialization
    
    @pytest.mark.asyncio
    async def test_pipeline_context_manager(self):
        """Test pipeline context manager"""
        async with PipelineOrchestrator() as orchestrator:
            assert orchestrator.client is not None
            # Should have initialized the API client
    
    @pytest.mark.asyncio
    async def test_process_item_with_mocked_api(self):
        """Test processing a single item with mocked API"""
        # Create test vocabulary item
        item = VocabularyItem(position=1, term="테스트", type="noun")
        
        # Create mock responses
        mock_stage1 = Stage1Response(
            term_number=1,
            term="테스트",
            ipa="[tʰesɯtʰɯ]",
            pos="noun",
            primary_meaning="test",
            metaphor="like a challenge",
            metaphor_noun="challenge",
            metaphor_action="testing",
            suggested_location="classroom",
            anchor_object="paper",
            anchor_sensory="white",
            explanation="evaluation method",
            comparison=Comparison(vs="시험", nuance="테스트 is more casual"),
            korean_keywords=["테스트"]
        )
        
        mock_stage2 = Stage2Response(
            rows=[FlashcardRow(
                position=1,
                term="테스트 [tʰesɯtʰɯ]",
                term_number=1,
                tab_name="Core",
                primer="Think of a test",
                front="테스트",
                back="test, exam",
                tags="noun,beginner"
            )]
        )
        
        mock_usage = ApiUsage(prompt_tokens=100, completion_tokens=200, total_tokens=300)
        
        async with PipelineOrchestrator() as orchestrator:
            # Mock the API client
            orchestrator.client = AsyncMock()
            orchestrator.client.process_stage1.return_value = (mock_stage1, mock_usage)
            orchestrator.client.process_stage2.return_value = (mock_stage2, mock_usage)
            
            # Process item
            tsv_output, from_cache = await orchestrator.process_item(item)
            
            # Verify results
            assert isinstance(tsv_output, str)
            assert "테스트" in tsv_output
            assert from_cache is False
            
            # Verify API was called
            orchestrator.client.process_stage1.assert_called_once()
            orchestrator.client.process_stage2.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_batch(self):
        """Test batch processing"""
        items = [
            VocabularyItem(position=1, term="안녕", type="interjection"),
            VocabularyItem(position=2, term="감사", type="noun"),
        ]
        
        output_file = Path("/tmp/test_output.tsv")
        
        async with PipelineOrchestrator() as orchestrator:
            # Mock the process_item method
            orchestrator.process_item = AsyncMock()
            orchestrator.process_item.side_effect = [
                ("1\t안녕\t1\tCore\tGreeting\t안녕\thello\tinterjection\t", False),
                ("2\t감사\t2\tCore\tGratitude\t감사\tthanks\tnoun\t", False)
            ]
            
            # Process batch
            batch_progress = await orchestrator.process_batch(items, output_file)
            
            # Verify progress
            assert batch_progress.total_items == 2
            assert batch_progress.completed_items == 2
            assert batch_progress.failed_items == 0
            assert batch_progress.batch_id.startswith("batch_")
            
            # Verify output file was created
            assert output_file.exists()
            content = output_file.read_text(encoding='utf-8')
            assert "position\tterm" in content  # Header
            assert "안녕" in content
            assert "감사" in content
            
            # Cleanup
            output_file.unlink()


class TestConcurrentPipelineOrchestrator:
    """Test concurrent pipeline orchestrator"""
    
    @pytest.mark.asyncio
    async def test_concurrent_pipeline_initialization(self):
        """Test concurrent pipeline initialization"""
        orchestrator = ConcurrentPipelineOrchestrator(max_concurrent=5)
        assert orchestrator.max_concurrent == 5
        assert orchestrator.rate_limiter is not None
        assert orchestrator.circuit_breaker is not None
        assert orchestrator.results_collector is not None
        assert orchestrator.progress_tracker is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_batch_processing(self):
        """Test concurrent batch processing with mocked components"""
        items = [
            VocabularyItem(position=i, term=f"단어{i}", type="noun")
            for i in range(1, 6)
        ]
        
        # Mock API client
        mock_api_client = AsyncMock()
        
        # Create mock stage responses
        async def mock_stage1(item):
            await asyncio.sleep(0.01)  # Simulate API delay
            return Stage1Response(
                term_number=item.position,
                term=item.term,
                ipa="[test]",
                pos="noun",
                primary_meaning="word",
                metaphor="test",
                metaphor_noun="test",
                metaphor_action="test",
                suggested_location="test",
                anchor_object="test",
                anchor_sensory="test",
                explanation="test",
                comparison=Comparison(vs="test", nuance="test"),
                korean_keywords=["test"]
            ), ApiUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        
        async def mock_stage2(item, stage1):
            await asyncio.sleep(0.01)  # Simulate API delay
            return Stage2Response(
                rows=[FlashcardRow(
                    position=item.position,
                    term=f"{item.term} [test]",
                    term_number=item.position,
                    tab_name="Core",
                    primer="Test",
                    front=item.term,
                    back="word",
                    tags="noun"
                )]
            ), ApiUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        
        mock_api_client.process_stage1.side_effect = mock_stage1
        mock_api_client.process_stage2.side_effect = mock_stage2
        
        async with ConcurrentPipelineOrchestrator(
            max_concurrent=3,
            api_client=mock_api_client
        ) as orchestrator:
            # Process batch
            results = await orchestrator.process_batch(items)
            
            # Verify results
            assert len(results) == 5
            
            # Check that results are in order
            for i, result in enumerate(results):
                assert result.position == i + 1
                assert not result.error
                assert result.flashcard_data is not None
            
            # Verify statistics
            stats = orchestrator.get_statistics()
            assert stats["total_items"] == 5
            assert stats["total_successful"] == 5
            assert stats["total_failed"] == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_error_handling(self):
        """Test error handling in concurrent processing"""
        items = [
            VocabularyItem(position=1, term="성공", type="noun"),
            VocabularyItem(position=2, term="실패", type="noun"),  # This will fail
            VocabularyItem(position=3, term="다시", type="adverb"),
        ]
        
        # Mock API client
        mock_api_client = AsyncMock()
        
        # Make second item fail
        async def mock_stage1_with_error(item):
            if item.position == 2:
                raise Exception("Simulated API error")
            return Stage1Response(
                term_number=item.position,
                term=item.term,
                ipa="[test]",
                pos=item.type,
                primary_meaning="test",
                metaphor="test",
                metaphor_noun="test",
                metaphor_action="test",
                suggested_location="test",
                anchor_object="test",
                anchor_sensory="test",
                explanation="test",
                comparison=Comparison(vs="test", nuance="test"),
                korean_keywords=["test"]
            ), ApiUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        
        mock_api_client.process_stage1.side_effect = mock_stage1_with_error
        
        async with ConcurrentPipelineOrchestrator(
            max_concurrent=3,
            api_client=mock_api_client
        ) as orchestrator:
            # Process batch
            results = await orchestrator.process_batch(items)
            
            # Verify results
            assert len(results) == 3
            assert results[0].error is None  # First item succeeded
            assert results[1].error is not None  # Second item failed
            assert "Simulated API error" in results[1].error
            assert results[2].error is None  # Third item succeeded
            
            # Verify statistics
            stats = orchestrator.get_statistics()
            assert stats["total_successful"] == 2
            assert stats["total_failed"] == 1


class TestPipelineIntegration:
    """Test full pipeline integration"""
    
    @pytest.mark.asyncio
    async def test_cache_integration(self):
        """Test that cache is properly integrated"""
        item = VocabularyItem(position=1, term="캐시", type="noun")
        
        async with PipelineOrchestrator() as orchestrator:
            # Mock API client
            orchestrator.client = AsyncMock()
            
            # First call - should hit API
            tsv1, from_cache1 = await orchestrator.process_item(item)
            assert from_cache1 is False
            
            # Second call - should hit cache
            tsv2, from_cache2 = await orchestrator.process_item(item)
            assert from_cache2 is True
            
            # Results should be the same
            assert tsv1 == tsv2
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self):
        """Test that rate limiting is properly integrated"""
        items = [VocabularyItem(position=i, term=f"단어{i}", type="noun") for i in range(1, 4)]
        
        async with PipelineOrchestrator() as orchestrator:
            # Verify rate limiter is called
            with patch.object(orchestrator.rate_limiter, 'acquire_for_stage') as mock_acquire:
                mock_acquire.return_value = None
                
                await orchestrator.process_item(items[0])
                
                # Should have been called for both stages
                assert mock_acquire.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self):
        """Test that circuit breaker is properly integrated"""
        item = VocabularyItem(position=1, term="회로", type="noun")
        
        async with PipelineOrchestrator() as orchestrator:
            # Verify circuit breaker is used
            with patch.object(orchestrator.circuit_breaker, 'call') as mock_call:
                # Make circuit breaker pass through the function
                async def passthrough(service, func):
                    return await func()
                mock_call.side_effect = passthrough
                
                await orchestrator.process_item(item)
                
                # Should have been called for both stages
                assert mock_call.call_count >= 2


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])