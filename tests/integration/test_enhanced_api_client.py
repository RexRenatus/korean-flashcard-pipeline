"""Integration tests for enhanced API client with retry logic"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import time

from flashcard_pipeline.api.enhanced_client import EnhancedOpenRouterClient
from flashcard_pipeline.utils.retry import RetryConfig
from flashcard_pipeline.exceptions import (
    StructuredAPIError,
    StructuredRateLimitError,
    NetworkError,
    RetryExhausted,
)
from flashcard_pipeline.circuit_breaker import CircuitBreaker
from flashcard_pipeline.rate_limiter import RateLimiter


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client"""
    client = AsyncMock(spec=httpx.AsyncClient)
    return client


@pytest.fixture
def api_client(mock_http_client):
    """Create an API client with mocked HTTP client"""
    client = EnhancedOpenRouterClient(
        api_key="test-key",
        retry_config=RetryConfig(
            max_attempts=3,
            initial_delay=0.01,  # Fast for testing
            jitter=False,
        )
    )
    # Replace the HTTP client with our mock
    client.client = mock_http_client
    return client


class TestEnhancedAPIClientRetry:
    """Test retry functionality in the enhanced API client"""
    
    @pytest.mark.asyncio
    async def test_successful_request_no_retry(self, api_client, mock_http_client):
        """Test successful request doesn't retry"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}],
            "usage": {"total_tokens": 100}
        }
        mock_response.headers = {}
        
        mock_http_client.post.return_value = mock_response
        
        # Make request
        response = await api_client._make_request_with_retry([{"role": "user", "content": "test"}])
        
        # Verify
        assert response["choices"][0]["message"]["content"] == "Test response"
        assert mock_http_client.post.call_count == 1
        assert api_client.stats.requests == 1
        assert api_client.stats.errors == 0
    
    @pytest.mark.asyncio
    async def test_retry_on_network_error(self, api_client, mock_http_client):
        """Test retry on network errors"""
        # First two calls fail, third succeeds
        mock_http_client.post.side_effect = [
            httpx.NetworkError("Connection failed"),
            httpx.NetworkError("Connection failed"),
            MagicMock(
                status_code=200,
                json=lambda: {"choices": [{"message": {"content": "Success"}}]},
                headers={}
            )
        ]
        
        # Make request
        response = await api_client._make_request_with_retry([{"role": "user", "content": "test"}])
        
        # Verify
        assert response["choices"][0]["message"]["content"] == "Success"
        assert mock_http_client.post.call_count == 3
        assert api_client.stats.errors == 2  # Two failures recorded
    
    @pytest.mark.asyncio
    async def test_retry_exhausted_on_persistent_error(self, api_client, mock_http_client):
        """Test retry exhaustion after max attempts"""
        # All calls fail
        mock_http_client.post.side_effect = httpx.NetworkError("Connection failed")
        
        # Make request
        with pytest.raises(RetryExhausted) as exc_info:
            await api_client._make_request_with_retry([{"role": "user", "content": "test"}])
        
        # Verify
        assert "Retry exhausted after 3 attempts" in str(exc_info.value)
        assert mock_http_client.post.call_count == 3
        assert api_client.stats.errors == 3
    
    @pytest.mark.asyncio
    async def test_rate_limit_with_retry_after(self, api_client, mock_http_client):
        """Test handling rate limit with retry-after header"""
        # Mock rate limit response
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"retry-after": "2.5"}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "429 Too Many Requests",
            request=MagicMock(),
            response=mock_response
        )
        
        mock_http_client.post.return_value = mock_response
        
        # Make request
        with pytest.raises(RetryExhausted) as exc_info:
            await api_client._make_request_with_retry([{"role": "user", "content": "test"}])
        
        # The last exception should be StructuredRateLimitError
        last_error = exc_info.value.last_exception
        assert isinstance(last_error, StructuredRateLimitError)
        assert last_error.retry_after == 2.5
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, api_client):
        """Test circuit breaker integration"""
        # Add circuit breaker
        api_client.circuit_breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1,
            expected_exception=Exception
        )
        
        # Mock the circuit breaker to be open
        api_client.circuit_breaker.is_open = True
        api_client.circuit_breaker._failure_count = 5
        
        # Make request - should fail immediately
        with pytest.raises(CircuitBreakerError) as exc_info:
            await api_client._make_request_with_retry([{"role": "user", "content": "test"}])
        
        assert "Circuit breaker is open" in str(exc_info.value)
        assert api_client.stats.circuit_breaker_trips == 1
    
    @pytest.mark.asyncio
    async def test_health_metrics_tracking(self, api_client, mock_http_client):
        """Test health metrics are updated correctly"""
        # Success then failure
        mock_http_client.post.side_effect = [
            MagicMock(
                status_code=200,
                json=lambda: {"choices": [{"message": {"content": "Success"}}]},
                headers={}
            ),
            httpx.NetworkError("Connection failed"),
        ]
        
        # First request - success
        await api_client._make_request_with_retry([{"role": "user", "content": "test"}])
        
        assert api_client.health_metrics["consecutive_failures"] == 0
        assert api_client.health_metrics["success_rate"] > 0.9
        
        # Second request - failure
        with pytest.raises(RetryExhausted):
            await api_client._make_request_with_retry([{"role": "user", "content": "test"}])
        
        assert api_client.health_metrics["consecutive_failures"] == 3  # 3 retry attempts
        assert api_client.health_metrics["last_error"] is not None
        assert api_client.health_metrics["error_rate"] > 0


class TestEnhancedAPIClientStages:
    """Test stage processing with enhanced error handling"""
    
    @pytest.mark.asyncio
    async def test_stage1_with_cache_miss(self, api_client, mock_http_client):
        """Test Stage 1 processing with cache miss"""
        # Mock cache miss
        mock_cache = AsyncMock()
        mock_cache.get_stage1.return_value = None
        api_client.cache = mock_cache
        
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "1. Formal usage\n2. Informal usage\n3. Technical usage"
                }
            }],
            "usage": {"total_tokens": 150}
        }
        mock_response.headers = {}
        
        mock_http_client.post.return_value = mock_response
        
        # Process Stage 1
        result = await api_client.process_stage1("테스트", "noun")
        
        # Verify
        assert result.term == "테스트"
        assert result.pos == "noun"
        assert len(result.nuances) == 3
        assert api_client.stats.cache_misses == 1
        assert api_client.stats.cache_hits == 0
        
        # Verify cache was updated
        mock_cache.set_stage1.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stage1_with_cache_hit(self, api_client, mock_http_client):
        """Test Stage 1 processing with cache hit"""
        # Mock cache hit
        from flashcard_pipeline.core.models import Stage1Output
        cached_output = Stage1Output(
            term="테스트",
            pos="noun",
            nuances=["Cached nuance 1", "Cached nuance 2"],
            raw_output="Cached content",
            created_at=datetime.utcnow()
        )
        
        mock_cache = AsyncMock()
        mock_cache.get_stage1.return_value = cached_output
        api_client.cache = mock_cache
        
        # Process Stage 1
        result = await api_client.process_stage1("테스트", "noun")
        
        # Verify
        assert result == cached_output
        assert api_client.stats.cache_hits == 1
        assert api_client.stats.cache_misses == 0
        
        # API should not be called
        mock_http_client.post.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_stage2_with_retry(self, api_client, mock_http_client):
        """Test Stage 2 processing with retry on failure"""
        # First call fails, second succeeds
        mock_http_client.post.side_effect = [
            httpx.NetworkError("Temporary network issue"),
            MagicMock(
                status_code=200,
                json=lambda: {
                    "choices": [{
                        "message": {
                            "content": "Flashcard 1:\nKorean: 테스트\nEnglish: Test"
                        }
                    }]
                },
                headers={}
            )
        ]
        
        # Process Stage 2
        result = await api_client.process_stage2(
            "테스트", 
            "noun", 
            ["Technical testing", "Academic examination"]
        )
        
        # Verify
        assert result.term == "테스트"
        assert len(result.flashcards) > 0
        assert mock_http_client.post.call_count == 2  # One failure, one success


class TestEnhancedAPIClientConfiguration:
    """Test client configuration and initialization"""
    
    def test_custom_retry_config(self):
        """Test client with custom retry configuration"""
        custom_config = RetryConfig(
            max_attempts=5,
            initial_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=True,
            retry_on=(ValueError, TypeError)
        )
        
        client = EnhancedOpenRouterClient(
            api_key="test-key",
            retry_config=custom_config
        )
        
        assert client.retry_config == custom_config
        assert client.retry_config.max_attempts == 5
        assert client.retry_config.exponential_base == 3.0
    
    def test_default_retry_config(self):
        """Test client with default retry configuration"""
        client = EnhancedOpenRouterClient(api_key="test-key")
        
        assert client.retry_config.max_attempts == 3  # DEFAULT_RETRY_COUNT
        assert client.retry_config.jitter is True
        assert NetworkError in client.retry_config.retry_on
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test client as async context manager"""
        async with EnhancedOpenRouterClient(api_key="test-key") as client:
            assert client is not None
            assert isinstance(client.client, httpx.AsyncClient)
        
        # After context exit, client should be closed
        # We can't directly test if it's closed, but no exceptions should be raised
    
    def test_health_status(self):
        """Test getting health status"""
        client = EnhancedOpenRouterClient(api_key="test-key")
        
        status = client.get_health_status()
        
        assert "stats" in status
        assert "health" in status
        assert "retry_config" in status
        
        assert status["stats"]["requests"] == 0
        assert status["health"]["success_rate"] == 1.0
        assert status["retry_config"]["jitter"] is True


class TestDelayCalculation:
    """Test delay calculation between retries"""
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self, api_client, mock_http_client):
        """Test that delays follow exponential backoff"""
        # Track call times
        call_times = []
        
        async def track_time(*args, **kwargs):
            call_times.append(time.time())
            raise httpx.NetworkError("Test error")
        
        mock_http_client.post.side_effect = track_time
        
        # Configure known delays (no jitter)
        api_client.retry_config = RetryConfig(
            max_attempts=4,
            initial_delay=0.1,
            exponential_base=2.0,
            jitter=False,
            retry_on=(httpx.NetworkError,)
        )
        
        # Make request
        with pytest.raises(RetryExhausted):
            await api_client._make_request_with_retry([{"role": "user", "content": "test"}])
        
        # Verify timing
        assert len(call_times) == 4
        
        # Check delays (with some tolerance for execution time)
        # Delay 1: 0.1 * 2^0 = 0.1
        assert 0.08 < call_times[1] - call_times[0] < 0.12
        
        # Delay 2: 0.1 * 2^1 = 0.2
        assert 0.18 < call_times[2] - call_times[1] < 0.22
        
        # Delay 3: 0.1 * 2^2 = 0.4
        assert 0.38 < call_times[3] - call_times[2] < 0.42