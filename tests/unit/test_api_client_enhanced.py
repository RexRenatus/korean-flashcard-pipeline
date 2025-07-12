"""Unit tests for enhanced API client functionality"""

import os
import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from flashcard_pipeline.api_client_enhanced import (
    EnhancedOpenRouterClient,
    ApiHealthStatus,
    ApiHealthMetrics,
    RetryStrategy
)
from flashcard_pipeline.models import (
    VocabularyItem,
    Stage1Response,
    Stage2Response,
    ApiResponse,
    ApiUsage,
    RateLimitInfo,
    FlashcardRow
)
from flashcard_pipeline.exceptions import (
    ApiError,
    RateLimitError,
    AuthenticationError,
    NetworkError,
    ValidationError
)


@pytest.fixture
def mock_db_manager():
    """Create mock database manager"""
    db_manager = MagicMock()
    db_manager.db_manager = MagicMock()
    return db_manager


@pytest.fixture
def mock_cache_service():
    """Create mock cache service"""
    cache = AsyncMock()
    cache.get_stage1 = AsyncMock(return_value=None)
    cache.get_stage2 = AsyncMock(return_value=None)
    cache.save_stage1 = AsyncMock()
    cache.save_stage2 = AsyncMock()
    cache.get_stats = MagicMock(return_value={"hits": 0, "misses": 0})
    return cache


@pytest.fixture
def mock_rate_limiter():
    """Create mock rate limiter"""
    limiter = AsyncMock()
    limiter.acquire_for_stage = AsyncMock()
    limiter.on_success = AsyncMock()
    limiter.on_rate_limit = AsyncMock()
    return limiter


@pytest.fixture
def mock_circuit_breaker():
    """Create mock circuit breaker"""
    breaker = AsyncMock()
    breaker.call = AsyncMock()
    return breaker


@pytest.fixture
async def api_client(mock_db_manager, mock_cache_service, mock_rate_limiter, mock_circuit_breaker):
    """Create enhanced API client with mocks"""
    with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test-key'}):
        client = EnhancedOpenRouterClient(
            db_manager=mock_db_manager,
            cache_service=mock_cache_service,
            rate_limiter=mock_rate_limiter,
            circuit_breaker=mock_circuit_breaker
        )
        yield client
        await client.close()


@pytest.fixture
def sample_vocabulary():
    """Create sample vocabulary item"""
    return VocabularyItem(
        position=1,
        term="안녕하세요",
        type="phrase"
    )


@pytest.fixture
def sample_stage1_response():
    """Create sample Stage 1 response"""
    return Stage1Response(
        term="안녕하세요",
        term_with_pronunciation="안녕하세요[an-nyeong-ha-se-yo]",
        ipa="annjʌŋhasejo",
        pos="interjection",
        primary_meaning="Hello (formal)",
        metaphor="A warm bow of greeting",
        metaphor_noun="bow",
        metaphor_action="greeting warmly",
        suggested_location="entrance of a traditional Korean house",
        anchor_object="wooden door frame",
        anchor_sensory="the sound of sliding door opening",
        explanation="Formal greeting showing respect",
        korean_keywords=["인사", "공손", "만남"]
    )


@pytest.fixture
def mock_api_response():
    """Create mock API response"""
    return {
        "id": "test-123",
        "model": "anthropic/claude-3.5-sonnet",
        "choices": [{
            "message": {
                "content": json.dumps({
                    "term": "안녕하세요",
                    "term_with_pronunciation": "안녕하세요[an-nyeong-ha-se-yo]",
                    "ipa": "annjʌŋhasejo",
                    "pos": "interjection",
                    "primary_meaning": "Hello (formal)",
                    "metaphor": "A warm bow of greeting",
                    "metaphor_noun": "bow",
                    "metaphor_action": "greeting warmly",
                    "suggested_location": "entrance of a traditional Korean house",
                    "anchor_object": "wooden door frame",
                    "anchor_sensory": "the sound of sliding door opening",
                    "explanation": "Formal greeting showing respect",
                    "korean_keywords": ["인사", "공손", "만남"]
                })
            }
        }],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 150,
            "total_tokens": 250
        }
    }


class TestRetryStrategy:
    """Test retry strategy functionality"""
    
    def test_exponential_backoff(self):
        """Test exponential backoff calculation"""
        strategy = RetryStrategy(base_delay=1.0, exponential_base=2.0, jitter=False)
        
        assert strategy.get_delay(0) == 1.0
        assert strategy.get_delay(1) == 2.0
        assert strategy.get_delay(2) == 4.0
        assert strategy.get_delay(3) == 8.0
    
    def test_max_delay(self):
        """Test maximum delay enforcement"""
        strategy = RetryStrategy(base_delay=1.0, max_delay=5.0, jitter=False)
        
        assert strategy.get_delay(10) == 5.0  # Should be capped at max_delay
    
    def test_jitter(self):
        """Test jitter adds randomness"""
        strategy = RetryStrategy(base_delay=1.0, jitter=True)
        
        delays = [strategy.get_delay(1) for _ in range(10)]
        # With jitter, delays should vary
        assert len(set(delays)) > 1
        # But should be within expected range
        assert all(1.0 <= d <= 2.0 for d in delays)
    
    def test_should_retry_network_errors(self):
        """Test retry on network errors"""
        strategy = RetryStrategy(max_retries=3)
        
        assert strategy.should_retry(0, NetworkError("test"))
        assert strategy.should_retry(2, NetworkError("test"))
        assert not strategy.should_retry(3, NetworkError("test"))  # Max retries
    
    def test_should_retry_server_errors(self):
        """Test retry on server errors"""
        strategy = RetryStrategy()
        
        # 5xx errors should retry
        error = ApiError("Server error", status_code=500)
        assert strategy.should_retry(0, error)
        
        # 4xx errors should not retry
        error = ApiError("Client error", status_code=400)
        assert not strategy.should_retry(0, error)
    
    def test_should_retry_rate_limits(self):
        """Test retry on rate limit errors"""
        strategy = RetryStrategy()
        
        error = RateLimitError("Rate limited", retry_after=60)
        assert strategy.should_retry(0, error)


class TestEnhancedApiClient:
    """Test enhanced API client functionality"""
    
    async def test_successful_stage1_request(self, api_client, sample_vocabulary, mock_api_response):
        """Test successful Stage 1 processing"""
        # Mock the HTTP response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_response
        mock_response.headers = {}
        
        api_client.circuit_breaker.call.return_value = mock_response
        
        # Process Stage 1
        response, usage = await api_client.process_stage1(sample_vocabulary, task_id="test-task-1")
        
        # Verify response
        assert response.term == "안녕하세요"
        assert response.primary_meaning == "Hello (formal)"
        assert usage.total_tokens == 250
        
        # Verify cache was updated
        api_client.cache_service.save_stage1.assert_called_once()
        
        # Verify stats updated
        assert api_client.stats["successful_requests"] == 1
        assert api_client.stats["total_tokens"] == 250
    
    async def test_cached_stage1_response(self, api_client, sample_vocabulary, sample_stage1_response):
        """Test Stage 1 with cached response"""
        # Mock cache hit
        api_client.cache_service.get_stage1.return_value = (sample_stage1_response, 250)
        
        # Process Stage 1
        response, usage = await api_client.process_stage1(sample_vocabulary)
        
        # Verify response
        assert response == sample_stage1_response
        assert usage.total_tokens == 0  # No tokens used for cached response
        
        # Verify stats
        assert api_client.stats["cache_hits"] == 1
        assert api_client.stats["total_requests"] == 0  # No API request made
    
    async def test_retry_on_rate_limit(self, api_client, sample_vocabulary):
        """Test retry logic on rate limit errors"""
        # First response: rate limited
        rate_limit_response = AsyncMock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {'Retry-After': '1'}
        
        # Second response: success
        success_response = AsyncMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps({"term": "test"})}}],
            "usage": {"total_tokens": 100}
        }
        success_response.headers = {}
        
        # Mock circuit breaker to return different responses
        api_client.circuit_breaker.call.side_effect = [rate_limit_response, success_response]
        
        # Mock output parser
        with patch.object(api_client.nuance_parser, 'parse') as mock_parse:
            mock_parse.return_value = MagicMock()
            
            # Process with retry
            await api_client.process_stage1(sample_vocabulary)
            
            # Verify retry happened
            assert api_client.stats["retries"] == 1
            assert api_client.circuit_breaker.call.call_count == 2
    
    async def test_retry_on_network_error(self, api_client, sample_vocabulary):
        """Test retry on network errors"""
        # First attempt: network error
        # Second attempt: success
        success_response = AsyncMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps({"term": "test"})}}],
            "usage": {"total_tokens": 100}
        }
        success_response.headers = {}
        
        api_client.circuit_breaker.call.side_effect = [
            httpx.NetworkError("Connection failed"),
            success_response
        ]
        
        # Mock output parser
        with patch.object(api_client.nuance_parser, 'parse') as mock_parse:
            mock_parse.return_value = MagicMock()
            
            # Process with retry
            await api_client.process_stage1(sample_vocabulary)
            
            # Verify retry happened
            assert api_client.stats["retries"] == 1
    
    async def test_max_retries_exceeded(self, api_client, sample_vocabulary):
        """Test max retries exceeded"""
        # All attempts fail
        api_client.circuit_breaker.call.side_effect = httpx.NetworkError("Connection failed")
        api_client.retry_strategy.max_retries = 2
        
        # Should raise after max retries
        with pytest.raises(httpx.NetworkError):
            await api_client.process_stage1(sample_vocabulary)
        
        # Verify retries
        assert api_client.stats["retries"] == 2
        assert api_client.stats["failed_requests"] >= 1
    
    async def test_health_monitoring(self, api_client):
        """Test health monitoring functionality"""
        # Simulate some successful requests
        for _ in range(10):
            api_client._update_request_history({
                "timestamp": datetime.now(),
                "stage": 1,
                "retry_count": 0,
                "success": True,
                "latency_ms": 500,
                "error": None
            })
        
        # Simulate some failures
        for _ in range(2):
            api_client._update_request_history({
                "timestamp": datetime.now(),
                "stage": 1,
                "retry_count": 0,
                "success": False,
                "latency_ms": 0,
                "error": "timeout"
            })
        
        # Get health status
        health = await api_client.get_health_status()
        
        assert health.status == ApiHealthStatus.DEGRADED  # 83% success rate
        assert health.success_rate == pytest.approx(0.833, 0.01)
        assert health.average_latency_ms == 500.0
        assert health.error_rate == pytest.approx(0.167, 0.01)
    
    async def test_quota_tracking(self, api_client):
        """Test API quota tracking"""
        # Set some stats
        api_client.stats.update({
            "total_tokens": 10000,
            "total_cost": 0.25,
            "total_requests": 100,
            "successful_requests": 95,
            "failed_requests": 5
        })
        
        # Mock rate limit info
        api_client.rate_limit_info = RateLimitInfo(
            limit=1000,
            remaining=850,
            reset_at=datetime.now() + timedelta(hours=1)
        )
        
        # Get quota usage
        quota = await api_client.get_quota_usage()
        
        assert quota["tokens"]["used"] == 10000
        assert quota["tokens"]["cost"] == 0.25
        assert quota["requests"]["total"] == 100
        assert quota["rate_limits"]["remaining"] == 850
    
    def test_enhanced_statistics(self, api_client):
        """Test enhanced statistics calculation"""
        # Set some stats
        api_client.stats.update({
            "total_requests": 100,
            "successful_requests": 90,
            "failed_requests": 10,
            "total_tokens": 25000,
            "total_latency_ms": 50000,
            "cache_hits": 20,
            "retries": 5
        })
        
        stats = api_client.get_stats()
        
        assert stats["success_rate"] == 0.9
        assert stats["average_tokens_per_request"] == pytest.approx(277.78, 0.01)
        assert stats["average_latency_ms"] == 500.0
        assert stats["cache_hit_rate"] == pytest.approx(0.167, 0.01)  # 20/(100+20)
        assert stats["retry_rate"] == 0.05
    
    async def test_connection_test(self, api_client):
        """Test connection testing"""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(api_client, 'client') as mock_client:
            mock_client.get = AsyncMock(return_value=mock_response)
            
            result = await api_client.test_connection()
            
            assert result is True
            # Health should be updated
            assert len(api_client._request_history) > 0
    
    async def test_stage2_with_validation(self, api_client, sample_vocabulary, sample_stage1_response):
        """Test Stage 2 processing with validation"""
        # Mock API response with TSV content
        tsv_content = """position\tterm\tterm_number\ttab_name\tprimer\tfront\tback\ttags\thonorific_level
1\t안녕하세요\t1\tScene\t\tFront content\tBack content\ttag1,tag2\tformal"""
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": tsv_content}}],
            "usage": {"total_tokens": 200}
        }
        mock_response.headers = {}
        
        api_client.circuit_breaker.call.return_value = mock_response
        
        # Process Stage 2
        response, usage = await api_client.process_stage2(
            sample_vocabulary,
            sample_stage1_response,
            task_id="test-task-2"
        )
        
        # Verify response
        assert len(response.flashcard_rows) == 1
        assert response.flashcard_rows[0].term == "안녕하세요"
        assert usage.total_tokens == 200
        
        # Verify validation occurred
        assert api_client.flashcard_parser.validate_tsv_format(response)


@pytest.mark.integration
class TestApiClientIntegration:
    """Integration tests for API client"""
    
    @pytest.mark.skipif(not os.environ.get('OPENROUTER_API_KEY'), 
                       reason="Requires OPENROUTER_API_KEY")
    async def test_real_api_connection(self):
        """Test real API connection (requires API key)"""
        async with EnhancedOpenRouterClient() as client:
            result = await client.test_connection()
            assert result is True
            
            # Check health
            health = await client.get_health_status()
            assert health.status in [ApiHealthStatus.HEALTHY, ApiHealthStatus.UNKNOWN]