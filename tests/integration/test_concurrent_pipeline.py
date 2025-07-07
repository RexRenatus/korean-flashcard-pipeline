"""Integration tests for concurrent pipeline processing"""

import asyncio
import pytest
from pathlib import Path
import json
import os
from unittest.mock import patch, Mock, AsyncMock

from flashcard_pipeline.models import VocabularyItem
from flashcard_pipeline.cli import PipelineOrchestrator


class TestConcurrentPipelineIntegration:
    """Test full concurrent pipeline integration"""
    
    @pytest.fixture
    async def mock_api_responses(self):
        """Create mock API responses"""
        # Load mock responses
        mock_responses_path = Path(__file__).parent.parent / "data" / "mock_api_responses.json"
        with open(mock_responses_path, 'r', encoding='utf-8') as f:
            responses = json.load(f)
        
        return responses
    
    @pytest.fixture
    def mock_openrouter_client(self, mock_api_responses):
        """Create mock OpenRouter client"""
        client = AsyncMock()
        
        # Create response cycle
        stage1_cycle = iter(mock_api_responses["stage1_responses"])
        stage2_cycle = iter(mock_api_responses["stage2_responses"])
        
        async def mock_stage1(item):
            try:
                response_data = next(stage1_cycle)
            except StopIteration:
                # Restart cycle
                nonlocal stage1_cycle
                stage1_cycle = iter(mock_api_responses["stage1_responses"])
                response_data = next(stage1_cycle)
            
            # Parse response
            from flashcard_pipeline.models import Stage1Response
            stage1 = Stage1Response.parse_raw(response_data["content"])
            usage = Mock(
                total_tokens=response_data["usage"]["total_tokens"],
                estimated_cost=response_data["usage"]["total_tokens"] * 0.00001
            )
            return stage1, usage
        
        async def mock_stage2(item, stage1_result):
            try:
                response_data = next(stage2_cycle)
            except StopIteration:
                # Restart cycle
                nonlocal stage2_cycle
                stage2_cycle = iter(mock_api_responses["stage2_responses"])
                response_data = next(stage2_cycle)
            
            # Parse response
            from flashcard_pipeline.models import Stage2Response
            stage2 = Stage2Response.parse_raw(response_data["content"])
            usage = Mock(
                total_tokens=response_data["usage"]["total_tokens"],
                estimated_cost=response_data["usage"]["total_tokens"] * 0.00001
            )
            return stage2, usage
        
        client.process_stage1 = mock_stage1
        client.process_stage2 = mock_stage2
        
        return client
    
    @pytest.mark.asyncio
    async def test_concurrent_batch_processing(self, tmp_path, mock_openrouter_client):
        """Test processing batch with concurrent execution"""
        # Create test vocabulary items
        items = [
            VocabularyItem(position=i, term=f"테스트{i}", type="noun")
            for i in range(1, 11)  # 10 items
        ]
        
        output_file = tmp_path / "output.tsv"
        
        # Process with different concurrency levels
        for max_concurrent in [1, 5, 10]:
            output_file = tmp_path / f"output_{max_concurrent}.tsv"
            
            with patch('flashcard_pipeline.cli.OpenRouterClient') as mock_client_class:
                mock_client_class.return_value = mock_openrouter_client
                
                async with PipelineOrchestrator() as orchestrator:
                    start_time = asyncio.get_event_loop().time()
                    
                    batch_progress = await orchestrator.process_batch_concurrent(
                        items, output_file, f"test_batch_{max_concurrent}", max_concurrent
                    )
                    
                    duration = asyncio.get_event_loop().time() - start_time
                    
                    # Verify results
                    assert batch_progress.total_items == 10
                    assert batch_progress.completed_items == 10
                    assert batch_progress.failed_items == 0
                    
                    # Check output file
                    assert output_file.exists()
                    content = output_file.read_text(encoding='utf-8')
                    lines = content.strip().split('\n')
                    
                    # Should have header + data rows
                    assert len(lines) >= 11  # At least header + 10 items
                    assert lines[0].startswith("position\tterm")
                    
                    print(f"Concurrency {max_concurrent}: {duration:.2f}s")
    
    @pytest.mark.asyncio
    async def test_concurrent_with_cache(self, tmp_path, mock_openrouter_client):
        """Test concurrent processing with cache hits"""
        items = [
            VocabularyItem(position=i, term=f"캐시{i % 3}", type="noun")  # Repeat some terms
            for i in range(1, 16)  # 15 items with duplicates
        ]
        
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        output_file = tmp_path / "output_cached.tsv"
        
        with patch('flashcard_pipeline.cli.OpenRouterClient') as mock_client_class:
            mock_client_class.return_value = mock_openrouter_client
            
            # First run - populate cache
            async with PipelineOrchestrator(str(cache_dir)) as orchestrator:
                await orchestrator.process_batch_concurrent(
                    items[:5], output_file, "cache_batch_1", 5
                )
            
            # Second run - should hit cache for duplicates
            async with PipelineOrchestrator(str(cache_dir)) as orchestrator:
                batch_progress = await orchestrator.process_batch_concurrent(
                    items, output_file, "cache_batch_2", 10
                )
                
                # Check cache stats
                cache_stats = orchestrator.cache_service.get_stats()
                assert cache_stats.overall_hit_rate > 0  # Should have cache hits
    
    @pytest.mark.asyncio
    async def test_concurrent_error_handling(self, tmp_path):
        """Test concurrent processing with errors"""
        items = [
            VocabularyItem(position=i, term=f"에러{i}", type="noun")
            for i in range(1, 11)
        ]
        
        output_file = tmp_path / "output_errors.tsv"
        
        # Create client that fails for some items
        mock_client = AsyncMock()
        
        async def mock_stage1(item):
            if item.position in [3, 7]:  # Fail specific positions
                raise Exception(f"Mock API error for position {item.position}")
            
            from flashcard_pipeline.models import Stage1Response
            return (
                Stage1Response(
                    term=item.term,
                    phonetic=f"[{item.term}]",
                    definition_korean="정의",
                    definition_english="definition",
                    etymology="origin",
                    related_words=[],
                    homonyms=[],
                    primary_pos="noun"
                ),
                Mock(total_tokens=100, estimated_cost=0.001)
            )
        
        mock_client.process_stage1 = mock_stage1
        mock_client.process_stage2 = AsyncMock(return_value=(
            Mock(to_tsv=lambda: "mock\ttsv\tdata"),
            Mock(total_tokens=200, estimated_cost=0.002)
        ))
        
        with patch('flashcard_pipeline.cli.OpenRouterClient') as mock_client_class:
            mock_client_class.return_value = mock_client
            
            async with PipelineOrchestrator() as orchestrator:
                batch_progress = await orchestrator.process_batch_concurrent(
                    items, output_file, "error_batch", 5
                )
                
                # Should have some failures
                assert batch_progress.failed_items == 2
                assert batch_progress.completed_items == 8
    
    @pytest.mark.asyncio
    async def test_concurrent_rate_limiting(self, mock_openrouter_client):
        """Test that rate limiting works in concurrent mode"""
        items = [
            VocabularyItem(position=i, term=f"속도{i}", type="noun")
            for i in range(1, 21)  # 20 items
        ]
        
        # Track API call times
        call_times = []
        original_stage1 = mock_openrouter_client.process_stage1
        
        async def tracked_stage1(item):
            call_times.append(asyncio.get_event_loop().time())
            return await original_stage1(item)
        
        mock_openrouter_client.process_stage1 = tracked_stage1
        
        with patch('flashcard_pipeline.cli.OpenRouterClient') as mock_client_class:
            mock_client_class.return_value = mock_openrouter_client
            
            async with PipelineOrchestrator() as orchestrator:
                # Use high concurrency to test rate limiting
                await orchestrator.process_batch_concurrent(
                    items, Path("test.tsv"), "rate_limit_batch", 20
                )
                
                # Verify calls were spread out (not all immediate)
                if len(call_times) > 10:
                    # Check that not all calls happened in first 100ms
                    first_10_duration = call_times[9] - call_times[0]
                    assert first_10_duration > 0.05  # Should take some time