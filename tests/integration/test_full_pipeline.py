"""Comprehensive integration tests for the full pipeline"""
import pytest
import asyncio
import os
import tempfile
import csv
import json
import sqlite3
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
import time

from flashcard_pipeline import (
    PipelineOrchestrator,
    VocabularyItem,
    Stage1Response,
    Stage2Response,
    FlashcardRow,
    Comparison,
    OpenRouterClient,
    CacheService,
    AdaptiveRateLimiter,
    CircuitBreaker
)
from flashcard_pipeline.exceptions import (
    RateLimitError,
    ApiError,
    CircuitBreakerOpen
)


@pytest.fixture
def test_db_path():
    """Create a test database"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    yield db_path
    os.unlink(db_path)


@pytest.fixture
def test_cache_dir():
    """Create a test cache directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def large_vocabulary_list():
    """Create a large vocabulary list for testing"""
    items = []
    categories = ['noun', 'verb', 'adjective', 'adverb', 'expression']
    
    for i in range(100):
        items.append({
            'position': i + 1,
            'term': f'단어{i}',
            'type': categories[i % len(categories)]
        })
    
    return items


@pytest.fixture
def mock_api_responses():
    """Create mock API responses for testing"""
    def create_stage1_response(item):
        return Stage1Response(
            term_number=item['position'],
            term=item['term'],
            ipa=f"[{item['term']}]",
            pos=item['type'],
            primary_meaning=f"Meaning of {item['term']}",
            other_meanings="Other meanings",
            metaphor="Like something",
            metaphor_noun="thing",
            metaphor_action="action",
            suggested_location="place",
            anchor_object="object",
            anchor_sensory="sense",
            explanation="Explanation",
            usage_context="Context",
            comparison=Comparison(
                similar_to=["similar"],
                different_from=["different"],
                commonly_confused_with=[]
            ),
            homonyms=[],
            korean_keywords=["keyword"]
        )
    
    def create_stage2_tsv(item, stage1):
        return f"{item['position']}\t{item['term']}\t{stage1.ipa}\t{stage1.pos}\tFront\tSecondary\tExample\tBack\tBack secondary\tBack example\tMnemonic\tbeginner\tcommon\ttag1,tag2\tNotes"
    
    return create_stage1_response, create_stage2_tsv


class TestFullPipelineIntegration:
    """Test the complete pipeline with all components"""
    
    @pytest.mark.asyncio
    async def test_complete_pipeline_flow(self, test_cache_dir, large_vocabulary_list, mock_api_responses):
        """Test processing a large batch through the entire pipeline"""
        
        create_stage1, create_stage2_tsv = mock_api_responses
        
        # Create CSV file
        csv_file = test_cache_dir / "input.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['position', 'term', 'type'])
            writer.writeheader()
            writer.writerows(large_vocabulary_list)
        
        # Mock API client
        with patch('flashcard_pipeline.api_client.OpenRouterClient') as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            
            # Set up mock responses
            async def mock_stage1(vocab_item):
                await asyncio.sleep(0.01)  # Simulate API delay
                item_dict = {
                    'position': vocab_item.position,
                    'term': vocab_item.term,
                    'type': vocab_item.type
                }
                return create_stage1(item_dict), {'total_tokens': 100, 'estimated_cost': 0.001}
            
            async def mock_stage2(vocab_item, stage1_response):
                await asyncio.sleep(0.01)  # Simulate API delay
                item_dict = {
                    'position': vocab_item.position,
                    'term': vocab_item.term,
                    'type': vocab_item.type
                }
                tsv = create_stage2_tsv(item_dict, stage1_response)
                return Stage2Response.from_tsv(tsv), {'total_tokens': 150, 'estimated_cost': 0.0015}
            
            mock_client.process_stage1.side_effect = mock_stage1
            mock_client.process_stage2.side_effect = mock_stage2
            
            # Create orchestrator with realistic settings
            orchestrator = PipelineOrchestrator(
                cache_dir=str(test_cache_dir),
                rate_limit=600,  # 600 requests per minute
                max_concurrent=10,
                circuit_breaker_threshold=5,
                circuit_breaker_timeout=30
            )
            
            # Process the batch
            output_file = test_cache_dir / "output.tsv"
            start_time = time.time()
            
            results = await orchestrator.process_csv(
                str(csv_file),
                str(output_file),
                progress_callback=lambda current, total: print(f"Progress: {current}/{total}")
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Verify results
            assert len(results) == 100
            assert output_file.exists()
            
            # Check output file
            with open(output_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                assert len(lines) == 101  # Header + 100 data rows
            
            # Verify processing time is reasonable
            assert processing_time < 30  # Should complete within 30 seconds
            
            # Check cache was used
            cache_stats = orchestrator.cache_service.get_stats()
            assert cache_stats['total_entries'] > 0
    
    @pytest.mark.asyncio
    async def test_pipeline_resume_capability(self, test_cache_dir, test_db_path):
        """Test that the pipeline can resume from a checkpoint"""
        
        # Create a batch that will be interrupted
        items = [VocabularyItem(position=i, term=f"word{i}", type="noun") for i in range(20)]
        
        with patch('flashcard_pipeline.api_client.OpenRouterClient') as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            
            call_count = 0
            
            async def mock_stage1_with_failure(vocab_item):
                nonlocal call_count
                call_count += 1
                
                # Fail after 10 items
                if call_count == 10:
                    raise Exception("Simulated failure")
                
                await asyncio.sleep(0.01)
                return Stage1Response(
                    term_number=vocab_item.position,
                    term=vocab_item.term,
                    ipa=f"[{vocab_item.term}]",
                    pos="noun",
                    primary_meaning="meaning",
                    other_meanings="",
                    metaphor="",
                    metaphor_noun="",
                    metaphor_action="",
                    suggested_location="",
                    anchor_object="",
                    anchor_sensory="",
                    explanation="",
                    comparison=Comparison(similar_to=[], different_from=[], commonly_confused_with=[]),
                    homonyms=[],
                    korean_keywords=[]
                ), {'total_tokens': 50, 'estimated_cost': 0.0005}
            
            mock_client.process_stage1.side_effect = mock_stage1_with_failure
            mock_client.process_stage2.return_value = (
                Stage2Response.from_tsv("1\tterm\t[ipa]\tnoun\tFront\t\t\tBack\t\t\t\tbeginner\tcommon\t\t"),
                {'total_tokens': 50, 'estimated_cost': 0.0005}
            )
            
            orchestrator = PipelineOrchestrator(
                cache_dir=str(test_cache_dir),
                db_path=test_db_path
            )
            
            # First attempt - should fail
            with pytest.raises(Exception) as exc_info:
                await orchestrator.process_batch(items, batch_id=1)
            
            assert "Simulated failure" in str(exc_info.value)
            
            # Check checkpoint was saved
            checkpoint = orchestrator.get_checkpoint(batch_id=1)
            assert checkpoint is not None
            assert checkpoint < 20  # Some items processed
            
            # Reset mock for resume
            call_count = 0
            mock_client.process_stage1.side_effect = None
            mock_client.process_stage1.return_value = (
                Stage1Response(
                    term_number=1,
                    term="test",
                    ipa="[test]",
                    pos="noun",
                    primary_meaning="meaning",
                    other_meanings="",
                    metaphor="",
                    metaphor_noun="",
                    metaphor_action="",
                    suggested_location="",
                    anchor_object="",
                    anchor_sensory="",
                    explanation="",
                    comparison=Comparison(similar_to=[], different_from=[], commonly_confused_with=[]),
                    homonyms=[],
                    korean_keywords=[]
                ),
                {'total_tokens': 50, 'estimated_cost': 0.0005}
            )
            
            # Resume processing
            resumed_results = await orchestrator.resume_batch(batch_id=1)
            
            # Should complete remaining items
            assert len(resumed_results) > 0
    
    @pytest.mark.asyncio
    async def test_rate_limiting_behavior(self, test_cache_dir):
        """Test that rate limiting works correctly under load"""
        
        with patch('flashcard_pipeline.api_client.OpenRouterClient') as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            
            # Track API call times
            call_times = []
            
            async def track_calls(vocab_item):
                call_times.append(time.time())
                return Stage1Response(
                    term_number=vocab_item.position,
                    term=vocab_item.term,
                    ipa="[test]",
                    pos="noun",
                    primary_meaning="test",
                    other_meanings="",
                    metaphor="",
                    metaphor_noun="",
                    metaphor_action="",
                    suggested_location="",
                    anchor_object="",
                    anchor_sensory="",
                    explanation="",
                    comparison=Comparison(similar_to=[], different_from=[], commonly_confused_with=[]),
                    homonyms=[],
                    korean_keywords=[]
                ), {'total_tokens': 50, 'estimated_cost': 0.0005}
            
            mock_client.process_stage1.side_effect = track_calls
            mock_client.process_stage2.return_value = (
                Stage2Response.from_tsv("1\tterm\t[ipa]\tnoun\tFront\t\t\tBack\t\t\t\tbeginner\tcommon\t\t"),
                {'total_tokens': 50, 'estimated_cost': 0.0005}
            )
            
            # Create orchestrator with low rate limit
            orchestrator = PipelineOrchestrator(
                cache_dir=str(test_cache_dir),
                rate_limit=60,  # 60 requests per minute = 1 per second
                max_concurrent=1  # Force sequential processing
            )
            
            # Process multiple items
            items = [VocabularyItem(position=i, term=f"rate_test_{i}") for i in range(5)]
            
            start_time = time.time()
            await asyncio.gather(*[orchestrator.process_item(item) for item in items])
            total_time = time.time() - start_time
            
            # With 5 items (10 API calls) at 1/sec, should take ~10 seconds
            assert total_time >= 8  # Allow some tolerance
            
            # Check call spacing
            for i in range(1, len(call_times)):
                time_diff = call_times[i] - call_times[i-1]
                assert time_diff >= 0.9  # Should be ~1 second apart
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_behavior(self, test_cache_dir):
        """Test circuit breaker opens and closes correctly"""
        
        with patch('flashcard_pipeline.api_client.OpenRouterClient') as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            
            failure_count = 0
            
            async def failing_api_call(vocab_item):
                nonlocal failure_count
                failure_count += 1
                raise ApiError("API Error", status_code=500, response_body="Server error")
            
            mock_client.process_stage1.side_effect = failing_api_call
            
            orchestrator = PipelineOrchestrator(
                cache_dir=str(test_cache_dir),
                circuit_breaker_threshold=3,
                circuit_breaker_timeout=1  # 1 second timeout for testing
            )
            
            # Make requests until circuit opens
            items = [VocabularyItem(position=i, term=f"cb_test_{i}") for i in range(5)]
            
            for i, item in enumerate(items):
                try:
                    await orchestrator.process_item(item)
                except (ApiError, CircuitBreakerOpen):
                    pass
                
                if i >= 2:  # After 3 failures
                    # Circuit should be open
                    assert orchestrator.circuit_breaker.state == "open"
                    break
            
            # Further requests should fail immediately
            with pytest.raises(CircuitBreakerOpen):
                await orchestrator.process_item(items[4])
            
            # Wait for timeout
            await asyncio.sleep(1.5)
            
            # Reset mock to succeed
            mock_client.process_stage1.side_effect = None
            mock_client.process_stage1.return_value = (
                Stage1Response(
                    term_number=1,
                    term="test",
                    ipa="[test]",
                    pos="noun",
                    primary_meaning="test",
                    other_meanings="",
                    metaphor="",
                    metaphor_noun="",
                    metaphor_action="",
                    suggested_location="",
                    anchor_object="",
                    anchor_sensory="",
                    explanation="",
                    comparison=Comparison(similar_to=[], different_from=[], commonly_confused_with=[]),
                    homonyms=[],
                    korean_keywords=[]
                ),
                {'total_tokens': 50, 'estimated_cost': 0.0005}
            )
            
            # Circuit should be half-open, next request should succeed
            result = await orchestrator.process_item(items[4])
            assert result is not None
            assert orchestrator.circuit_breaker.state == "closed"
    
    @pytest.mark.asyncio
    async def test_cache_persistence(self, test_cache_dir):
        """Test that cache persists across orchestrator instances"""
        
        item = VocabularyItem(position=1, term="캐시테스트", type="noun")
        
        with patch('flashcard_pipeline.api_client.OpenRouterClient') as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            
            mock_client.process_stage1.return_value = (
                Stage1Response(
                    term_number=1,
                    term="캐시테스트",
                    ipa="[cache-test]",
                    pos="noun",
                    primary_meaning="cache test",
                    other_meanings="",
                    metaphor="",
                    metaphor_noun="",
                    metaphor_action="",
                    suggested_location="",
                    anchor_object="",
                    anchor_sensory="",
                    explanation="",
                    comparison=Comparison(similar_to=[], different_from=[], commonly_confused_with=[]),
                    homonyms=[],
                    korean_keywords=[]
                ),
                {'total_tokens': 50, 'estimated_cost': 0.0005}
            )
            
            mock_client.process_stage2.return_value = (
                Stage2Response.from_tsv("1\t캐시테스트\t[cache-test]\tnoun\tCache Test\t\t\tCache Test\t\t\t\tbeginner\tcommon\t\t"),
                {'total_tokens': 50, 'estimated_cost': 0.0005}
            )
            
            # First orchestrator instance
            orchestrator1 = PipelineOrchestrator(cache_dir=str(test_cache_dir))
            result1 = await orchestrator1.process_item(item)
            
            # Should have made API calls
            assert mock_client.process_stage1.call_count == 1
            assert mock_client.process_stage2.call_count == 1
            
            # Create new orchestrator instance with same cache dir
            orchestrator2 = PipelineOrchestrator(cache_dir=str(test_cache_dir))
            
            # Reset mock call counts
            mock_client.process_stage1.reset_mock()
            mock_client.process_stage2.reset_mock()
            
            # Process same item
            result2 = await orchestrator2.process_item(item)
            
            # Should NOT make API calls (cache hit)
            assert mock_client.process_stage1.call_count == 0
            assert mock_client.process_stage2.call_count == 0
            
            # Results should be identical
            assert result1 == result2
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, test_cache_dir):
        """Test that concurrent processing works correctly"""
        
        with patch('flashcard_pipeline.api_client.OpenRouterClient') as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            
            # Track concurrent calls
            active_calls = 0
            max_concurrent = 0
            call_lock = asyncio.Lock()
            
            async def track_concurrency(vocab_item):
                nonlocal active_calls, max_concurrent
                
                async with call_lock:
                    active_calls += 1
                    max_concurrent = max(max_concurrent, active_calls)
                
                # Simulate processing time
                await asyncio.sleep(0.1)
                
                async with call_lock:
                    active_calls -= 1
                
                return Stage1Response(
                    term_number=vocab_item.position,
                    term=vocab_item.term,
                    ipa="[test]",
                    pos="noun",
                    primary_meaning="test",
                    other_meanings="",
                    metaphor="",
                    metaphor_noun="",
                    metaphor_action="",
                    suggested_location="",
                    anchor_object="",
                    anchor_sensory="",
                    explanation="",
                    comparison=Comparison(similar_to=[], different_from=[], commonly_confused_with=[]),
                    homonyms=[],
                    korean_keywords=[]
                ), {'total_tokens': 50, 'estimated_cost': 0.0005}
            
            mock_client.process_stage1.side_effect = track_concurrency
            mock_client.process_stage2.return_value = (
                Stage2Response.from_tsv("1\tterm\t[ipa]\tnoun\tFront\t\t\tBack\t\t\t\tbeginner\tcommon\t\t"),
                {'total_tokens': 50, 'estimated_cost': 0.0005}
            )
            
            orchestrator = PipelineOrchestrator(
                cache_dir=str(test_cache_dir),
                max_concurrent=5,
                rate_limit=1000  # High limit to test concurrency
            )
            
            # Process many items concurrently
            items = [VocabularyItem(position=i, term=f"concurrent_{i}") for i in range(20)]
            
            start_time = time.time()
            results = await asyncio.gather(*[
                orchestrator.process_item(item) for item in items
            ])
            total_time = time.time() - start_time
            
            # All should complete
            assert len(results) == 20
            
            # Should have achieved concurrency
            assert max_concurrent >= 3  # At least some concurrency
            assert max_concurrent <= 5  # Respects limit
            
            # Should be faster than sequential (20 * 0.1 = 2 seconds)
            assert total_time < 1.5
    
    @pytest.mark.asyncio
    async def test_error_recovery_strategies(self, test_cache_dir):
        """Test various error recovery strategies"""
        
        with patch('flashcard_pipeline.api_client.OpenRouterClient') as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            
            # Different error scenarios
            error_scenarios = {
                1: RateLimitError("Rate limited", retry_after=1),
                2: ApiError("Server error", status_code=500, response_body=""),
                3: ApiError("Bad request", status_code=400, response_body=""),
                4: NetworkError("Connection timeout"),
                5: None  # Success
            }
            
            call_count = 0
            
            async def varied_responses(vocab_item):
                nonlocal call_count
                call_count += 1
                
                error = error_scenarios.get(vocab_item.position)
                if error:
                    raise error
                
                return Stage1Response(
                    term_number=vocab_item.position,
                    term=vocab_item.term,
                    ipa="[test]",
                    pos="noun",
                    primary_meaning="test",
                    other_meanings="",
                    metaphor="",
                    metaphor_noun="",
                    metaphor_action="",
                    suggested_location="",
                    anchor_object="",
                    anchor_sensory="",
                    explanation="",
                    comparison=Comparison(similar_to=[], different_from=[], commonly_confused_with=[]),
                    homonyms=[],
                    korean_keywords=[]
                ), {'total_tokens': 50, 'estimated_cost': 0.0005}
            
            mock_client.process_stage1.side_effect = varied_responses
            mock_client.process_stage2.return_value = (
                Stage2Response.from_tsv("1\tterm\t[ipa]\tnoun\tFront\t\t\tBack\t\t\t\tbeginner\tcommon\t\t"),
                {'total_tokens': 50, 'estimated_cost': 0.0005}
            )
            
            orchestrator = PipelineOrchestrator(
                cache_dir=str(test_cache_dir),
                max_retries=3,
                retry_delay=0.1
            )
            
            # Process items with different error scenarios
            results = []
            errors = []
            
            for position in error_scenarios.keys():
                item = VocabularyItem(position=position, term=f"error_test_{position}")
                try:
                    result = await orchestrator.process_item(item)
                    results.append((position, result))
                except Exception as e:
                    errors.append((position, type(e).__name__))
            
            # Item 5 should succeed
            assert any(pos == 5 for pos, _ in results)
            
            # Items 1-4 should have errors
            assert len(errors) >= 3  # Some might retry successfully