"""End-to-end integration tests for the flashcard pipeline"""
import pytest
import asyncio
import os
import tempfile
import csv
from pathlib import Path
from unittest.mock import patch, AsyncMock

from flashcard_pipeline import (
    PipelineOrchestrator,
    VocabularyItem,
    Stage1Response,
    Stage2Response,
    FlashcardRow,
    Comparison
)


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_csv_file():
    """Create a sample CSV file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        writer = csv.writer(f)
        writer.writerow(['position', 'term', 'type'])
        writer.writerow([1, '안녕하세요', 'greeting'])
        writer.writerow([2, '감사합니다', 'expression'])
        writer.writerow([3, '사랑', 'noun'])
        f.flush()
        yield Path(f.name)
    os.unlink(f.name)


@pytest.fixture
def mock_stage1_response():
    """Create a mock Stage1Response"""
    return Stage1Response(
        term_number=1,
        term="안녕하세요",
        ipa="[an.njʌŋ.ha.se.jo]",
        pos="greeting",
        primary_meaning="Hello (formal)",
        other_meanings="Hi, Good day",
        metaphor="like a warm welcome",
        metaphor_noun="welcome",
        metaphor_action="greeting",
        suggested_location="doorway",
        anchor_object="handshake",
        anchor_sensory="warm",
        explanation="Formal greeting used with strangers or elders",
        usage_context="formal situations",
        comparison=Comparison(
            similar_to=["안녕", "여보세요"],
            different_from=["잘가요"],
            commonly_confused_with=[]
        ),
        homonyms=[],
        korean_keywords=["인사", "격식"]
    )


@pytest.fixture
def mock_stage2_tsv():
    """Create mock Stage2 TSV response"""
    return "1\t안녕하세요\t[an.njʌŋ.ha.se.jo]\tgreeting\tHello (formal)\tFormal greeting\t안녕하세요, 만나서 반갑습니다.\tHello (formal greeting)\tannyeonghaseyo\tHello, nice to meet you.\tAn young person says hello\tbeginner\tessential\tgreeting,formal\tUsed with strangers"


class TestEndToEndPipeline:
    @pytest.mark.asyncio
    async def test_full_pipeline_with_mocked_api(self, temp_cache_dir, sample_csv_file):
        """Test the complete pipeline with mocked API responses"""
        
        # Mock the API client
        with patch('flashcard_pipeline.api_client.OpenRouterClient') as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            
            # Set up mock responses
            mock_client.process_stage1.return_value = (
                mock_stage1_response(),
                {'total_tokens': 100, 'estimated_cost': 0.001}
            )
            
            mock_client.process_stage2.return_value = (
                Stage2Response.from_tsv(mock_stage2_tsv()),
                {'total_tokens': 150, 'estimated_cost': 0.0015}
            )
            
            # Create orchestrator
            orchestrator = PipelineOrchestrator(
                cache_dir=str(temp_cache_dir),
                rate_limit=10  # Low limit for testing
            )
            
            # Process the CSV file
            output_file = temp_cache_dir / "output.tsv"
            results = await orchestrator.process_csv(
                str(sample_csv_file),
                str(output_file)
            )
            
            # Verify results
            assert len(results) == 3  # 3 items in sample CSV
            assert output_file.exists()
            
            # Check output file content
            with open(output_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                assert len(lines) == 4  # Header + 3 data rows
                assert "Position\tTerm\tIPA" in lines[0]  # Header
    
    @pytest.mark.asyncio
    async def test_pipeline_with_cache_hit(self, temp_cache_dir):
        """Test that cache is properly utilized"""
        
        with patch('flashcard_pipeline.api_client.OpenRouterClient') as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            
            # Set up mock responses
            mock_client.process_stage1.return_value = (
                mock_stage1_response(),
                {'total_tokens': 100, 'estimated_cost': 0.001}
            )
            
            mock_client.process_stage2.return_value = (
                Stage2Response.from_tsv(mock_stage2_tsv()),
                {'total_tokens': 150, 'estimated_cost': 0.0015}
            )
            
            orchestrator = PipelineOrchestrator(cache_dir=str(temp_cache_dir))
            
            # Process same item twice
            item = VocabularyItem(position=1, term="테스트", type="noun")
            
            # First call - should hit API
            result1 = await orchestrator.process_item(item)
            assert mock_client.process_stage1.call_count == 1
            assert mock_client.process_stage2.call_count == 1
            
            # Second call - should hit cache
            result2 = await orchestrator.process_item(item)
            assert mock_client.process_stage1.call_count == 1  # No additional calls
            assert mock_client.process_stage2.call_count == 1  # No additional calls
            
            # Results should be identical
            assert result1 == result2
    
    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self, temp_cache_dir):
        """Test error handling in the pipeline"""
        
        with patch('flashcard_pipeline.api_client.OpenRouterClient') as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            
            # Simulate API error
            mock_client.process_stage1.side_effect = Exception("API Error")
            
            orchestrator = PipelineOrchestrator(cache_dir=str(temp_cache_dir))
            
            item = VocabularyItem(position=1, term="에러", type="noun")
            
            # Should handle error gracefully
            with pytest.raises(Exception) as exc_info:
                await orchestrator.process_item(item)
            
            assert "API Error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, temp_cache_dir):
        """Test that rate limiting is properly enforced"""
        
        with patch('flashcard_pipeline.api_client.OpenRouterClient') as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            
            # Quick responses to test rate limiting
            mock_client.process_stage1.return_value = (
                mock_stage1_response(),
                {'total_tokens': 100, 'estimated_cost': 0.001}
            )
            
            mock_client.process_stage2.return_value = (
                Stage2Response.from_tsv(mock_stage2_tsv()),
                {'total_tokens': 150, 'estimated_cost': 0.0015}
            )
            
            # Very low rate limit
            orchestrator = PipelineOrchestrator(
                cache_dir=str(temp_cache_dir),
                rate_limit=2  # 2 requests per minute
            )
            
            # Process multiple items
            items = [
                VocabularyItem(position=i, term=f"테스트{i}", type="noun")
                for i in range(5)
            ]
            
            start_time = asyncio.get_event_loop().time()
            
            results = []
            for item in items:
                result = await orchestrator.process_item(item)
                results.append(result)
            
            end_time = asyncio.get_event_loop().time()
            elapsed = end_time - start_time
            
            # Should take some time due to rate limiting
            # With 2 req/min and 5 items (10 API calls), should take >2 seconds
            assert elapsed > 2.0
            assert len(results) == 5


class TestCLIIntegration:
    """Test the CLI interface integration"""
    
    def test_cli_process_command(self, temp_cache_dir, sample_csv_file, monkeypatch):
        """Test the CLI process command"""
        from flashcard_pipeline.cli import app
        from typer.testing import CliRunner
        
        runner = CliRunner()
        
        # Mock environment variable
        monkeypatch.setenv('OPENROUTER_API_KEY', 'test-key')
        
        # Mock the orchestrator to avoid actual API calls
        with patch('flashcard_pipeline.cli.PipelineOrchestrator') as MockOrchestrator:
            mock_instance = MockOrchestrator.return_value
            mock_instance.process_csv = AsyncMock(return_value=[])
            
            result = runner.invoke(app, [
                'process',
                str(sample_csv_file),
                '--output', str(temp_cache_dir / 'output.tsv'),
                '--cache-dir', str(temp_cache_dir)
            ])
            
            assert result.exit_code == 0
            assert mock_instance.process_csv.called
    
    def test_cli_cache_stats_command(self, temp_cache_dir, monkeypatch):
        """Test the cache stats command"""
        from flashcard_pipeline.cli import app
        from typer.testing import CliRunner
        
        runner = CliRunner()
        monkeypatch.setenv('OPENROUTER_API_KEY', 'test-key')
        
        with patch('flashcard_pipeline.cache.CacheService') as MockCache:
            mock_cache = MockCache.return_value
            mock_cache.get_stats.return_value = {
                'total_entries': 10,
                'stage1_entries': 5,
                'stage2_entries': 5,
                'total_size': 1024 * 100  # 100KB
            }
            
            result = runner.invoke(app, [
                'cache-stats',
                '--cache-dir', str(temp_cache_dir)
            ])
            
            assert result.exit_code == 0
            assert "Total entries: 10" in result.output
            assert "100.0 KB" in result.output


class TestCircuitBreakerIntegration:
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self, temp_cache_dir):
        """Test that circuit breaker opens after consecutive failures"""
        
        with patch('flashcard_pipeline.api_client.OpenRouterClient') as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            
            # Simulate multiple failures
            mock_client.process_stage1.side_effect = Exception("API Error")
            
            orchestrator = PipelineOrchestrator(
                cache_dir=str(temp_cache_dir),
                circuit_breaker_threshold=3
            )
            
            item = VocabularyItem(position=1, term="테스트", type="noun")
            
            # Make requests until circuit opens
            for i in range(3):
                try:
                    await orchestrator.process_item(item)
                except:
                    pass
            
            # Circuit should be open now
            assert orchestrator.circuit_breaker.state == "open"
            
            # Further requests should fail immediately
            with pytest.raises(Exception) as exc_info:
                await orchestrator.process_item(item)
            
            assert "Circuit breaker is open" in str(exc_info.value)