import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
import httpx
from datetime import datetime, timedelta

from flashcard_pipeline.api_client import OpenRouterClient
from flashcard_pipeline.models import (
    VocabularyItem,
    Stage1Response,
    Stage2Response,
    ApiResponse,
    ApiUsage,
    RateLimitInfo,
    Comparison
)
from flashcard_pipeline.exceptions import (
    ApiError,
    RateLimitError,
    AuthenticationError,
    NetworkError,
    ValidationError
)


def create_mock_response(status_code, headers=None, json_data=None, text="", content_type=None):
    """Create a mock httpx response with all required methods"""
    mock_response = Mock()
    mock_response.status_code = status_code
    
    # Set up headers - make it a real dict for easier use with dict()
    if headers:
        # Create a mock that behaves like a dict
        mock_headers = Mock()
        mock_headers.get = Mock(side_effect=lambda key, default=None: headers.get(key, default))
        # Support dict() conversion by making it inherit from dict
        mock_headers.__iter__ = Mock(return_value=iter(headers))
        mock_headers.__getitem__ = Mock(side_effect=lambda key: headers.get(key))
        mock_headers.keys = Mock(return_value=headers.keys())
        mock_headers.values = Mock(return_value=headers.values())
        mock_headers.items = Mock(return_value=headers.items())
        mock_response.headers = mock_headers
    else:
        # Empty headers
        mock_response.headers = {}
    
    # Set content type if provided
    if content_type:
        headers = headers or {}
        headers['content-type'] = content_type
        if hasattr(mock_response.headers, 'get'):
            mock_response.headers.get = Mock(side_effect=lambda key, default=None: headers.get(key, default))
    
    # Set up json() method
    if json_data is not None:
        mock_response.json = Mock(return_value=json_data)
    else:
        mock_response.json = Mock(side_effect=ValueError("No JSON data"))
    
    # Set up text attribute
    mock_response.text = text
    
    # Set up raise_for_status method
    def raise_for_status():
        if status_code >= 400:
            raise httpx.HTTPStatusError("Error", request=Mock(), response=mock_response)
    
    mock_response.raise_for_status = Mock(side_effect=raise_for_status)
    
    return mock_response


@pytest.fixture
def mock_api_key():
    return "test-api-key-123"


@pytest.fixture
def mock_client(mock_api_key):
    with patch.dict('os.environ', {'OPENROUTER_API_KEY': mock_api_key}):
        return OpenRouterClient()


@pytest.fixture
def sample_vocabulary_item():
    return VocabularyItem(position=1, term="테스트", type="noun")


@pytest.fixture
def sample_stage1_response():
    return Stage1Response(
        term_number=1,
        term="테스트",
        ipa="[tʰesɯtʰɯ]",
        pos="noun",
        primary_meaning="test",
        other_meanings="exam, trial",
        metaphor="like a challenge",
        metaphor_noun="challenge",
        metaphor_action="testing",
        suggested_location="classroom",
        anchor_object="paper",
        anchor_sensory="white",
        explanation="evaluation method",
        usage_context="academic",
        comparison=Comparison(
            vs="시험",
            nuance="테스트 is more casual than 시험"
        ),
        homonyms=[],
        korean_keywords=["테스트"]
    )


class TestOpenRouterClient:
    @pytest.mark.asyncio
    async def test_client_initialization(self, mock_api_key):
        client = OpenRouterClient(api_key=mock_api_key)
        assert client.api_key == mock_api_key
        assert client.base_url == "https://openrouter.ai/api/v1/chat/completions"
        assert client.client is None  # Lazy initialization
    
    @pytest.mark.asyncio
    async def test_client_context_manager(self, mock_client):
        # Test async context manager
        async with mock_client as client:
            assert client.client is not None
        assert mock_client.client is None  # Should be closed
    
    @pytest.mark.asyncio
    async def test_successful_stage1_request(self, mock_client, sample_vocabulary_item):
        # Mock cache service to return None (cache miss)
        mock_client.cache_service = AsyncMock()
        mock_client.cache_service.get_stage1.return_value = None
        
        # Mock the HTTP response
        mock_response_data = {
            "id": "test-id",
            "model": "claude-3.5-sonnet",
            "object": "chat.completion",
            "created": 1234567890,
            "choices": [{
                "message": {
                    "content": """```json
{
    "term_number": 1,
    "term": "테스트",
    "ipa": "[tʰesɯtʰɯ]",
    "pos": "noun",
    "primary_meaning": "test",
    "other_meanings": "exam, trial",
    "metaphor": "like a challenge",
    "metaphor_noun": "challenge",
    "metaphor_action": "testing",
    "suggested_location": "classroom",
    "anchor_object": "paper",
    "anchor_sensory": "white",
    "explanation": "evaluation method",
    "usage_context": "academic",
    "comparison": {
        "vs": "시험",
        "nuance": "테스트 is more casual than 시험"
    },
    "homonyms": [],
    "korean_keywords": ["테스트"]
}
```"""
                }
            }],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 200,
                "total_tokens": 300
            }
        }
        
        with patch.object(mock_client, '_make_request', return_value=mock_response_data):
            stage1_response, usage = await mock_client.process_stage1(sample_vocabulary_item)
            
            assert stage1_response.term == "테스트"
            assert stage1_response.pos == "noun"
            assert usage.total_tokens == 300
    
    @pytest.mark.asyncio
    async def test_rate_limit_error(self, mock_client, sample_vocabulary_item):
        # Mock rate limiter and circuit breaker to allow the request
        mock_client.rate_limiter = AsyncMock()
        mock_client.circuit_breaker = AsyncMock()
        
        # Mock cache service to return None (cache miss)
        mock_client.cache_service = AsyncMock()
        mock_client.cache_service.get_stage1.return_value = None
        
        # Create a proper mock response with rate limit headers
        mock_response = create_mock_response(
            status_code=429,
            headers={
                'Retry-After': '60',
                'X-RateLimit-Reset': str(int(datetime.now().timestamp()) + 60)
            },
            text="Rate limit exceeded"
        )
        
        async def mock_call(service, func):
            return await func()
        
        mock_client.circuit_breaker.call = mock_call
        
        with patch.object(mock_client, '_ensure_client'):
            mock_client.client = AsyncMock()
            mock_client.client.post.return_value = mock_response
            
            # Patch asyncio.sleep to speed up the test
            with patch('flashcard_pipeline.api_client.asyncio.sleep', new_callable=AsyncMock):
                with pytest.raises(RateLimitError) as exc_info:
                    await mock_client.process_stage1(sample_vocabulary_item)
                
                assert exc_info.value.retry_after == 60
    
    @pytest.mark.asyncio
    async def test_authentication_error(self, mock_client, sample_vocabulary_item):
        # Mock rate limiter and circuit breaker to allow the request
        mock_client.rate_limiter = AsyncMock()
        mock_client.circuit_breaker = AsyncMock()
        
        # Mock cache service to return None (cache miss)
        mock_client.cache_service = AsyncMock()
        mock_client.cache_service.get_stage1.return_value = None
        
        # Create mock response for authentication error
        mock_response = create_mock_response(
            status_code=401,
            text="Invalid API key"
        )
        
        async def mock_call(service, func):
            return await func()
        
        mock_client.circuit_breaker.call = mock_call
        
        with patch.object(mock_client, '_ensure_client'):
            mock_client.client = AsyncMock()
            mock_client.client.post.return_value = mock_response
            
            with pytest.raises(AuthenticationError):
                await mock_client.process_stage1(sample_vocabulary_item)
    
    @pytest.mark.asyncio
    async def test_network_error_with_retry(self, mock_client, sample_vocabulary_item):
        # Mock cache service to return None (cache miss)
        mock_client.cache_service = AsyncMock()
        mock_client.cache_service.get_stage1.return_value = None
        
        # Mock rate limiter and circuit breaker
        mock_client.rate_limiter = AsyncMock()
        mock_client.circuit_breaker = AsyncMock()
        
        # Track call count
        call_count = 0
        
        async def mock_call(service, func):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # First two calls fail
                raise httpx.NetworkError("Connection failed")
            else:
                # Third call succeeds
                return await func()
        
        mock_client.circuit_breaker.call = mock_call
        
        # Create successful response for the third attempt
        mock_response = create_mock_response(
            status_code=200,
            json_data={
                "id": "test-id",
                "model": "claude-3.5-sonnet",
                "object": "chat.completion",
                "created": 1234567890,
                "choices": [{
                    "message": {"content": '{"term_number": 1, "term": "테스트", "ipa": "[test]", "pos": "noun", "primary_meaning": "test", "metaphor": "test", "metaphor_noun": "test", "metaphor_action": "test", "suggested_location": "test", "anchor_object": "test", "anchor_sensory": "test", "explanation": "test", "comparison": {"vs": "test", "nuance": "test"}, "korean_keywords": ["test"]}'}
                }],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
            }
        )
        
        with patch.object(mock_client, '_ensure_client'):
            mock_client.client = AsyncMock()
            mock_client.client.post.return_value = mock_response
            
            # Should succeed after retries
            with patch('flashcard_pipeline.api_client.asyncio.sleep'):  # Skip actual sleep in tests
                stage1_response, usage = await mock_client.process_stage1(sample_vocabulary_item)
                
                # Verify retries happened
                assert call_count == 3
                assert stage1_response.term == "테스트"
    
    @pytest.mark.asyncio
    async def test_cache_integration(self, mock_client, sample_vocabulary_item):
        # Test that cache service is used
        mock_cache_service = AsyncMock()
        mock_cache_service.get_stage1.return_value = None  # Cache miss
        mock_client.cache_service = mock_cache_service
        
        mock_response_data = {
            "id": "test-id",
            "model": "claude-3.5-sonnet",
            "object": "chat.completion",
            "created": 1234567890,
            "choices": [{
                "message": {"content": '{"term_number": 1, "term": "테스트", "ipa": "[test]", "pos": "noun", "primary_meaning": "test", "metaphor": "test", "metaphor_noun": "test", "metaphor_action": "test", "suggested_location": "test", "anchor_object": "test", "anchor_sensory": "test", "explanation": "test", "comparison": {"vs": "test", "nuance": "test"}, "korean_keywords": ["test"]}'}
            }],
            "usage": {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300}
        }
        
        with patch.object(mock_client, '_make_request', return_value=mock_response_data):
            await mock_client.process_stage1(sample_vocabulary_item)
            
            # Verify cache was checked and saved
            mock_cache_service.get_stage1.assert_called_once()
            mock_cache_service.save_stage1.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stats_tracking(self, mock_client, sample_vocabulary_item):
        # Mock cache service to return None (cache miss)
        mock_client.cache_service = AsyncMock()
        mock_client.cache_service.get_stage1.return_value = None
        
        # Mock rate limiter and circuit breaker
        mock_client.rate_limiter = AsyncMock()
        mock_client.circuit_breaker = AsyncMock()
        
        # Create a proper mock response
        mock_response = create_mock_response(
            status_code=200,
            json_data={
                "id": "test-id",
                "model": "claude-3.5-sonnet",
                "object": "chat.completion",
                "created": 1234567890,
                "choices": [{
                    "message": {"content": '{"term_number": 1, "term": "테스트", "ipa": "[test]", "pos": "noun", "primary_meaning": "test", "metaphor": "test", "metaphor_noun": "test", "metaphor_action": "test", "suggested_location": "test", "anchor_object": "test", "anchor_sensory": "test", "explanation": "test", "comparison": {"vs": "test", "nuance": "test"}, "korean_keywords": ["test"]}'}
                }],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 200,
                    "total_tokens": 300
                }
            }
        )
        
        async def mock_call(service, func):
            # Execute the function to ensure stats are updated
            return await func()
        
        mock_client.circuit_breaker.call = mock_call
        
        with patch.object(mock_client, '_ensure_client'):
            mock_client.client = AsyncMock()
            mock_client.client.post.return_value = mock_response
            
            await mock_client.process_stage1(sample_vocabulary_item)
            
            stats = mock_client.get_stats()
            assert stats["total_requests"] == 1
            assert stats["successful_requests"] == 1
            assert stats["total_tokens"] == 300
            assert stats["success_rate"] == 1.0
    
    @pytest.mark.asyncio
    async def test_connection_test(self, mock_client):
        with patch.object(mock_client, '_ensure_client'):
            mock_client.client = AsyncMock()
            # Create a proper mock response for successful connection
            mock_response = create_mock_response(
                status_code=200,
                json_data={"models": ["claude-3.5-sonnet"]},
                text='{"models": ["claude-3.5-sonnet"]}'
            )
            mock_client.client.get.return_value = mock_response
            
            result = await mock_client.test_connection()
            assert result is True
            
            # Test failure case
            mock_client.client.get.side_effect = Exception("Connection failed")
            result = await mock_client.test_connection()
            assert result is False


class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limit_info_parsing(self, mock_client):
        headers = {
            'X-RateLimit-Limit': '100',
            'X-RateLimit-Remaining': '50',
            'X-RateLimit-Reset': str(int((datetime.now() + timedelta(minutes=5)).timestamp()))
        }
        
        rate_info = RateLimitInfo.from_headers(headers)
        assert rate_info.limit == 100
        assert rate_info.remaining == 50
        assert rate_info.reset_at > datetime.now()
    
    @pytest.mark.asyncio
    async def test_should_wait_for_rate_limit(self, mock_client):
        # No rate limit info
        should_wait, wait_time = mock_client.should_wait_for_rate_limit()
        assert should_wait is False
        
        # Set rate limit info with low remaining
        mock_client.rate_limit_info = RateLimitInfo(
            limit=100,
            remaining=3,
            reset_at=datetime.now() + timedelta(seconds=30)
        )
        
        should_wait, wait_time = mock_client.should_wait_for_rate_limit()
        assert should_wait is True
        assert wait_time > 0
        assert wait_time <= 30


class TestStage2Processing:
    @pytest.mark.asyncio
    async def test_successful_stage2_request(
        self, 
        mock_client, 
        sample_vocabulary_item,
        sample_stage1_response
    ):
        # Mock cache service to return None (cache miss)
        mock_client.cache_service = AsyncMock()
        mock_client.cache_service.get_stage2.return_value = None
        
        mock_response_data = {
            "id": "test-id",
            "model": "claude-3.5-sonnet", 
            "object": "chat.completion",
            "created": 1234567890,
            "choices": [{
                "message": {
                    "content": "position\tterm\tterm_number\ttab_name\tprimer\tfront\tback\ttags\thonorific_level\n1\t테스트 [tʰesɯtʰɯ]\t1\tCore\tThink of a test in school\t테스트 (test)\ta test, examination\tnoun,beginner\t"
                }
            }],
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 250,
                "total_tokens": 400
            }
        }
        
        with patch.object(mock_client, '_make_request', return_value=mock_response_data):
            stage2_response, usage = await mock_client.process_stage2(
                sample_vocabulary_item,
                sample_stage1_response
            )
            
            assert len(stage2_response.rows) == 1
            assert stage2_response.rows[0].term == "테스트 [tʰesɯtʰɯ]"
            assert stage2_response.rows[0].position == 1
            assert usage.total_tokens == 400


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_validation_error_on_invalid_json(self, mock_client, sample_vocabulary_item):
        # Mock cache service to return None (cache miss)
        mock_client.cache_service = AsyncMock()
        mock_client.cache_service.get_stage1.return_value = None
        
        mock_response_data = {
            "id": "test-id",
            "model": "claude-3.5-sonnet",
            "object": "chat.completion",
            "created": 1234567890,
            "choices": [{
                "message": {"content": "This is not JSON"}
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        }
        
        with patch.object(mock_client, '_make_request', return_value=mock_response_data):
            with pytest.raises(ValidationError) as exc_info:
                await mock_client.process_stage1(sample_vocabulary_item)
            
            assert "Invalid Stage 1 response format" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_timeout_error_with_retry(self, mock_client, sample_vocabulary_item):
        # Mock cache service to return None (cache miss)
        mock_client.cache_service = AsyncMock()
        mock_client.cache_service.get_stage1.return_value = None
        
        # Mock rate limiter and circuit breaker
        mock_client.rate_limiter = AsyncMock()
        mock_client.circuit_breaker = AsyncMock()
        
        # Track call count
        call_count = 0
        
        async def mock_call(service, func):
            nonlocal call_count
            call_count += 1
            # Always timeout - should fail after max retries
            raise httpx.TimeoutException("Request timed out")
        
        mock_client.circuit_breaker.call = mock_call
        
        with patch.object(mock_client, '_ensure_client'):
            mock_client.client = AsyncMock()
            
            with patch('flashcard_pipeline.api_client.asyncio.sleep'):  # Skip actual sleep in tests
                with pytest.raises(NetworkError) as exc_info:
                    await mock_client.process_stage1(sample_vocabulary_item)
                
                assert "timeout" in str(exc_info.value).lower()
                assert call_count == 4  # Initial + 3 retries