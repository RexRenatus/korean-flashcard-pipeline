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
            similar_to=["시험"],
            different_from=[],
            commonly_confused_with=[]
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
    async def test_headers_generation(self, mock_client):
        headers = mock_client._get_headers()
        assert headers["Authorization"] == f"Bearer {mock_client.api_key}"
        assert headers["Content-Type"] == "application/json"
        assert "X-Title" in headers
    
    @pytest.mark.asyncio
    async def test_successful_stage1_request(self, mock_client, sample_vocabulary_item):
        # Mock the HTTP response
        mock_response_data = {
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
        "similar_to": ["시험"],
        "different_from": [],
        "commonly_confused_with": []
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
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {
            'retry-after': '60',
            'x-ratelimit-remaining': '0'
        }
        mock_response.json.return_value = {
            'error': {'message': 'Rate limit exceeded'}
        }
        
        with patch.object(mock_client, 'client') as mock_http_client:
            mock_http_client.post.side_effect = httpx.HTTPStatusError(
                "429 Too Many Requests",
                request=Mock(),
                response=mock_response
            )
            
            with pytest.raises(RateLimitError) as exc_info:
                await mock_client.process_stage1(sample_vocabulary_item)
            
            assert exc_info.value.retry_after == 60
    
    @pytest.mark.asyncio
    async def test_authentication_error(self, mock_client, sample_vocabulary_item):
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            'error': {'message': 'Invalid API key'}
        }
        
        with patch.object(mock_client, 'client') as mock_http_client:
            mock_http_client.post.side_effect = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=Mock(),
                response=mock_response
            )
            
            with pytest.raises(AuthenticationError):
                await mock_client.process_stage1(sample_vocabulary_item)
    
    @pytest.mark.asyncio
    async def test_network_error_with_retry(self, mock_client, sample_vocabulary_item):
        # First two calls fail, third succeeds
        side_effects = [
            httpx.NetworkError("Connection failed"),
            httpx.NetworkError("Connection failed"),
            {
                "choices": [{
                    "message": {"content": '```json\n{"term_number": 1}\n```'}
                }],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
            }
        ]
        
        with patch.object(mock_client, '_make_request') as mock_request:
            mock_request.side_effect = side_effects
            
            # Should succeed after retries
            with patch('asyncio.sleep'):  # Skip actual sleep in tests
                stage1_response, usage = await mock_client.process_stage1(sample_vocabulary_item)
                
                # Verify retries happened
                assert mock_request.call_count == 3
    
    @pytest.mark.asyncio
    async def test_json_extraction_from_response(self, mock_client):
        content_with_markdown = """Here's the analysis:

```json
{
    "term_number": 1,
    "term": "test"
}
```

Additional notes here."""
        
        extracted = mock_client._extract_json_from_content(content_with_markdown)
        assert extracted == '{\n    "term_number": 1,\n    "term": "test"\n}'
    
    @pytest.mark.asyncio
    async def test_stats_tracking(self, mock_client, sample_vocabulary_item):
        mock_response_data = {
            "choices": [{
                "message": {"content": '```json\n{"term_number": 1}\n```'}
            }],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 200,
                "total_tokens": 300
            }
        }
        
        with patch.object(mock_client, '_make_request', return_value=mock_response_data):
            await mock_client.process_stage1(sample_vocabulary_item)
            
            stats = mock_client.get_stats()
            assert stats["total_requests"] == 1
            assert stats["successful_requests"] == 1
            assert stats["total_tokens"] == 300
            assert stats["success_rate"] == 1.0
    
    @pytest.mark.asyncio
    async def test_connection_test(self, mock_client):
        with patch.object(mock_client, 'client') as mock_http_client:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_http_client.get.return_value = mock_response
            
            result = await mock_client.test_connection()
            assert result is True
            
            # Test failure case
            mock_http_client.get.side_effect = Exception("Connection failed")
            result = await mock_client.test_connection()
            assert result is False


class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limit_info_parsing(self, mock_client):
        headers = {
            'x-ratelimit-limit': '100',
            'x-ratelimit-remaining': '50',
            'x-ratelimit-reset': str(int((datetime.now() + timedelta(minutes=5)).timestamp()))
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
        mock_response_data = {
            "choices": [{
                "message": {
                    "content": "1\t테스트\t[tʰesɯtʰɯ]\tnoun\tTest\tEvaluation method\t이것은 테스트입니다.\tTest\tteseuteu\tThis is a test.\tThink of testing\tbeginner\tcommon\tstudy,academic\tCommonly used"
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
            
            assert stage2_response.flashcard_row.term == "테스트"
            assert stage2_response.flashcard_row.difficulty == "beginner"
            assert usage.total_tokens == 400


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_validation_error_on_invalid_json(self, mock_client, sample_vocabulary_item):
        mock_response_data = {
            "choices": [{
                "message": {"content": "This is not JSON"}
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        }
        
        with patch.object(mock_client, '_make_request', return_value=mock_response_data):
            with pytest.raises(ValidationError) as exc_info:
                await mock_client.process_stage1(sample_vocabulary_item)
            
            assert "JSON" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_timeout_error_with_retry(self, mock_client, sample_vocabulary_item):
        with patch.object(mock_client, '_make_request') as mock_request:
            mock_request.side_effect = httpx.TimeoutException("Request timed out")
            
            with patch('asyncio.sleep'):  # Skip actual sleep in tests
                with pytest.raises(NetworkError) as exc_info:
                    await mock_client.process_stage1(sample_vocabulary_item)
                
                assert "timeout" in str(exc_info.value).lower()
                assert mock_request.call_count == 4  # Initial + 3 retries