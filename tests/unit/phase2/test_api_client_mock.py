"""Phase 2: API Client Mock Tests

Tests for API client with mocked HTTP responses to test request/response handling,
retry logic, error handling, and response parsing without making real API calls.
"""

import pytest
import json
import asyncio
import httpx
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from flashcard_pipeline.api_client import OpenRouterClient
from flashcard_pipeline.models import (
    VocabularyItem, Stage1Response, Stage2Response, 
    ApiResponse, ApiUsage, Comparison
)
from flashcard_pipeline.exceptions import (
    ApiError, RateLimitError, NetworkError, ValidationError, AuthenticationError
)


def create_api_response(content, tokens=None):
    """Helper to create a complete API response"""
    if tokens is None:
        tokens = {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
    return {
        "id": "test-id",
        "model": "claude-3.5-sonnet",
        "object": "chat.completion",
        "created": 1234567890,
        "choices": [{"message": {"content": content}}],
        "usage": tokens
    }


class TestApiClientInitialization:
    """Test API client initialization and configuration"""
    
    def test_client_initialization_with_defaults(self):
        """Test client initializes with default values"""
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test-key'}):
            client = OpenRouterClient()
            
            assert client.base_url == "https://openrouter.ai/api/v1/chat/completions"
            assert client.api_key == "test-key"
            # httpx.Timeout is created with these values
            assert client.timeout is not None
    
    def test_client_initialization_with_custom_values(self):
        """Test client accepts custom configuration"""
        client = OpenRouterClient(
            api_key="custom-key",
            base_url="https://custom.api.com"
        )
        
        assert client.api_key == "custom-key"
        assert client.base_url == "https://custom.api.com"
    
    @patch.dict('os.environ', {'OPENROUTER_API_KEY': 'env-key-123'})
    def test_api_key_from_environment(self):
        """Test API key is loaded from environment"""
        client = OpenRouterClient()
        assert client.api_key == "env-key-123"
    
    def test_missing_api_key_error(self):
        """Test error when API key is missing"""
        with patch.dict('os.environ', {}, clear=True):
            # Also patch Path.exists to prevent .env loading
            with patch('pathlib.Path.exists', return_value=False):
                with pytest.raises(AuthenticationError) as exc_info:
                    OpenRouterClient(api_key=None)
                assert "OPENROUTER_API_KEY" in str(exc_info.value)


class TestApiRequestHandling:
    """Test API request construction and handling"""
    
    @pytest.fixture
    def mock_client(self):
        """Create client with mocked HTTP client"""
        client = OpenRouterClient(api_key="test-key")
        client.client = AsyncMock(spec=httpx.AsyncClient)
        return client
    
    @pytest.fixture
    def sample_vocab_item(self):
        """Sample vocabulary item"""
        return VocabularyItem(position=1, term="안녕하세요", type="interjection")
    
    @pytest.mark.asyncio
    async def test_stage1_request_construction(self, mock_client, sample_vocab_item):
        """Test Stage 1 request is constructed correctly"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}  # Empty headers dict
        mock_response.json.return_value = {
            "id": "test-id",
            "model": "claude-3.5-sonnet",
            "object": "chat.completion",
            "created": 1234567890,
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "term_number": 1,
                        "term": "안녕하세요",
                        "ipa": "annyeonghaseyo",
                        "pos": "interjection",
                        "primary_meaning": "hello",
                        "other_meanings": "good day",
                        "metaphor": "sunshine greeting",
                        "metaphor_noun": "sunshine",
                        "metaphor_action": "greets",
                        "suggested_location": "doorway",
                        "anchor_object": "welcome mat",
                        "anchor_sensory": "warm feeling",
                        "explanation": "Formal greeting used in polite situations",
                        "usage_context": "When meeting someone for the first time",
                        "comparison": {"vs": "안녕", "nuance": "More formal than 안녕"},
                        "homonyms": [],
                        "korean_keywords": ["인사", "예의"]
                    })
                }
            }],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
        mock_client.client.post.return_value = mock_response
        
        # Make request
        result, usage = await mock_client.process_stage1(sample_vocab_item)
        
        # Verify request was made
        mock_client.client.post.assert_called_once()
        
        # Verify result
        assert result.ipa == "annyeonghaseyo"
        assert result.primary_meaning == "hello"
        assert usage.total_tokens == 150
    
    @pytest.mark.asyncio
    async def test_stage2_request_construction(self, mock_client, sample_vocab_item):
        """Test Stage 2 request is constructed correctly"""
        # Create Stage 1 result
        stage1_result = Stage1Response(
            term_number=1,
            term="안녕하세요",
            ipa="annyeonghaseyo",
            pos="interjection",
            primary_meaning="hello",
            other_meanings="good day",
            metaphor="sunshine greeting",
            metaphor_noun="sunshine",
            metaphor_action="greets",
            suggested_location="doorway",
            anchor_object="welcome mat",
            anchor_sensory="warm feeling",
            explanation="Formal greeting used in polite situations",
            usage_context="When meeting someone for the first time",
            comparison=Comparison(vs="안녕", nuance="More formal than 안녕"),
            homonyms=[],
            korean_keywords=["인사", "예의"]
        )
        
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}  # Empty headers dict
        mock_response.json.return_value = {
            "id": "test-id-2",
            "model": "claude-3.5-sonnet",
            "object": "chat.completion",
            "created": 1234567891,
            "choices": [{
                "message": {
                    "content": "1\t안녕하세요 [annyeonghaseyo]\t1\tScene\tMemory room\tGreeting?\tHello\tgreeting,formal\tformal"
                }
            }],
            "usage": {
                "prompt_tokens": 200,
                "completion_tokens": 100,
                "total_tokens": 300
            }
        }
        mock_client.client.post.return_value = mock_response
        
        # Make request
        result, usage = await mock_client.process_stage2(sample_vocab_item, stage1_result)
        
        # Verify request was made
        mock_client.client.post.assert_called_once()
        
        # Verify result
        assert len(result.rows) == 1
        assert result.rows[0].term == "안녕하세요 [annyeonghaseyo]"
        assert usage.total_tokens == 300


class TestApiResponseParsing:
    """Test parsing of various API response formats"""
    
    @pytest.fixture
    def mock_client(self):
        """Create client with mocked HTTP client"""
        client = OpenRouterClient(api_key="test-key")
        client.client = AsyncMock(spec=httpx.AsyncClient)
        return client
    
    @pytest.mark.asyncio
    async def test_parse_json_in_markdown_blocks(self, mock_client):
        """Test parsing JSON wrapped in markdown code blocks"""
        # Response with markdown code blocks
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = create_api_response(
            """Here's the analysis:

```json
{
    "term_number": 1,
    "term": "test",
    "ipa": "test",
    "pos": "noun",
    "primary_meaning": "test",
    "other_meanings": "",
    "metaphor": "test metaphor",
    "metaphor_noun": "test",
    "metaphor_action": "tests",
    "suggested_location": "test location",
    "anchor_object": "test object",
    "anchor_sensory": "test sense",
    "explanation": "test explanation",
    "usage_context": null,
    "comparison": {"vs": "other", "nuance": "test comparison"},
    "homonyms": [],
    "korean_keywords": ["test"]
}
```

That's the result."""
        )
        mock_client.client.post.return_value = mock_response
        
        # Should parse correctly
        item = VocabularyItem(position=1, term="test", type="noun")
        result, _ = await mock_client.process_stage1(item)
        
        assert result.ipa == "test"
        assert result.primary_meaning == "test"
    
    @pytest.mark.asyncio
    async def test_parse_tsv_with_header(self, mock_client):
        """Test parsing TSV with header row"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = create_api_response(
            """position\tterm\tterm_number\ttab_name\tprimer\tfront\tback\ttags\thonorific_level
1\t안녕\t1\tScene\tMemory\tGreeting?\tHello\tgreeting\tcasual"""
        )
        mock_client.client.post.return_value = mock_response
        
        item = VocabularyItem(position=1, term="안녕", type="greeting")
        stage1 = Stage1Response(
            term_number=1,
            term="안녕",
            ipa="annyeong",
            pos="interjection",
            primary_meaning="hi",
            other_meanings="",
            metaphor="casual wave",
            metaphor_noun="wave",
            metaphor_action="greets",
            suggested_location="playground",
            anchor_object="friendly wave",
            anchor_sensory="relaxed feeling",
            explanation="Casual greeting among friends",
            usage_context=None,
            comparison=Comparison(vs="안녕하세요", nuance="Less formal than 안녕하세요"),
            homonyms=[],
            korean_keywords=["casual", "greeting"]
        )
        
        result, _ = await mock_client.process_stage2(item, stage1)
        
        assert len(result.rows) == 1
        assert result.rows[0].term == "안녕"
        assert result.rows[0].tab_name == "Scene"
    
    @pytest.mark.asyncio
    async def test_handle_null_values_in_response(self, mock_client):
        """Test handling of null values in API response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = create_api_response(
            json.dumps({
                "term_number": 1,
                "term": "test",
                "ipa": "test",
                "pos": "noun",
                "primary_meaning": "test",
                "other_meanings": "",
                "metaphor": "test metaphor",
                "metaphor_noun": "test",
                "metaphor_action": "tests",
                "suggested_location": "test location",
                "anchor_object": "test object",
                "anchor_sensory": "test sense",
                "explanation": "test explanation",
                "usage_context": None,
                "comparison": None,
                "homonyms": None,
                "korean_keywords": ["test"]
            })
        )
        mock_client.client.post.return_value = mock_response
        
        item = VocabularyItem(position=1, term="test", type="noun")
        result, _ = await mock_client.process_stage1(item)
        
        # Null values should be handled correctly
        assert result.usage_context is None
        assert result.comparison is None
        assert result.homonyms == []


class TestApiErrorHandling:
    """Test API error handling and retry logic"""
    
    @pytest.fixture
    def mock_client(self):
        """Create client with mocked HTTP client"""
        client = OpenRouterClient(api_key="test-key")
        client.client = AsyncMock(spec=httpx.AsyncClient)
        return client
    
    @pytest.mark.asyncio
    async def test_retry_on_transient_errors(self, mock_client):
        """Test retry logic for transient errors"""
        # First two calls fail, third succeeds
        responses = [
            Mock(status_code=503, json=lambda: {"error": {"message": "Service unavailable"}}),
            Mock(status_code=502, json=lambda: {"error": {"message": "Bad gateway"}}),
            Mock(status_code=200, headers={}, json=lambda: {
                "choices": [{"message": {"content": '{"romanization":"test","definitions":["test"],"part_of_speech":"noun","difficulty_level":"beginner","formality_level":"neutral"}'}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
            })
        ]
        mock_client.client.post.side_effect = responses
        
        item = VocabularyItem(position=1, term="test", type="noun")
        
        # Should retry and eventually succeed
        with patch('asyncio.sleep'):  # Speed up test
            result, _ = await mock_client.process_stage1(item)
        
        assert result.ipa == "test"
        assert result.primary_meaning == "test"
        assert mock_client.client.post.call_count == 3
    
    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self, mock_client):
        """Test handling of rate limit errors"""
        # Always return 429 to exhaust retries
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60", "X-RateLimit-Reset": "1234567890"}
        mock_response.json.return_value = {
            "error": {"message": "Rate limit exceeded"}
        }
        mock_client.client.post.return_value = mock_response
        
        item = VocabularyItem(position=1, term="test", type="noun")
        
        with patch('asyncio.sleep'):  # Speed up retries
            with pytest.raises(RateLimitError) as exc_info:
                await mock_client.process_stage1(item)
        
        assert exc_info.value.retry_after == 60
        assert "Rate limit" in str(exc_info.value)
        # Should have tried 4 times (initial + 3 retries)
        assert mock_client.client.post.call_count == 4
    
    @pytest.mark.asyncio
    async def test_authentication_error(self, mock_client):
        """Test handling of authentication errors"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": {"message": "Invalid API key"}
        }
        mock_client.client.post.return_value = mock_response
        
        item = VocabularyItem(position=1, term="test", type="noun")
        
        with pytest.raises(AuthenticationError) as exc_info:
            await mock_client.process_stage1(item)
        
        assert "Invalid API key" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_network_error_handling(self, mock_client):
        """Test handling of network errors"""
        # Simulate network error
        mock_client.client.post.side_effect = httpx.NetworkError("Connection failed")
        
        item = VocabularyItem(position=1, term="test", type="noun")
        
        with pytest.raises(NetworkError) as exc_info:
            with patch('asyncio.sleep'):  # Speed up retries
                await mock_client.process_stage1(item)
        
        assert "Connection failed" in str(exc_info.value)
        # Should have retried 3 times plus initial = 4 total
        assert mock_client.client.post.call_count == 4
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, mock_client):
        """Test handling of timeout errors"""
        mock_client.client.post.side_effect = httpx.TimeoutException("Request timed out")
        
        item = VocabularyItem(position=1, term="test", type="noun")
        
        with pytest.raises(NetworkError) as exc_info:
            with patch('asyncio.sleep'):
                await mock_client.process_stage1(item)
        
        assert "timed out" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validation_error_on_invalid_response(self, mock_client):
        """Test validation error for invalid API responses"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"invalid": "response", "missing": "required fields"}'
                }
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
        }
        mock_client.client.post.return_value = mock_response
        
        item = VocabularyItem(position=1, term="test", type="noun")
        
        with pytest.raises(ValidationError) as exc_info:
            await mock_client.process_stage1(item)
        
        assert "Invalid Stage 1 response" in str(exc_info.value)


class TestApiClientStatistics:
    """Test API client statistics tracking"""
    
    @pytest.fixture
    def mock_client(self):
        """Create client with mocked HTTP client"""
        client = OpenRouterClient(api_key="test-key")
        client.client = AsyncMock(spec=httpx.AsyncClient)
        return client
    
    @pytest.mark.asyncio
    async def test_request_counting(self, mock_client):
        """Test request counting statistics"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"romanization":"test","definitions":["test"],"part_of_speech":"noun","difficulty_level":"beginner","formality_level":"neutral"}'}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        }
        mock_client.client.post.return_value = mock_response
        
        # Make multiple requests
        item = VocabularyItem(position=1, term="test", type="noun")
        for _ in range(3):
            await mock_client.process_stage1(item)
        
        stats = mock_client.get_stats()
        assert stats["total_requests"] == 3
        assert stats["successful_requests"] == 3
        assert stats["failed_requests"] == 0
    
    @pytest.mark.asyncio
    async def test_token_usage_tracking(self, mock_client):
        """Test token usage tracking"""
        responses = [
            Mock(status_code=200, headers={}, json=lambda: {
                "choices": [{"message": {"content": '{"romanization":"test1","definitions":["test1"],"part_of_speech":"noun","difficulty_level":"beginner","formality_level":"neutral"}'}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
            }),
            Mock(status_code=200, headers={}, json=lambda: {
                "choices": [{"message": {"content": '{"romanization":"test2","definitions":["test2"],"part_of_speech":"noun","difficulty_level":"beginner","formality_level":"neutral"}'}}],
                "usage": {"prompt_tokens": 120, "completion_tokens": 60, "total_tokens": 180}
            })
        ]
        mock_client.client.post.side_effect = responses
        
        # Make requests
        for i in range(2):
            item = VocabularyItem(position=i, term=f"test{i}", type="noun")
            await mock_client.process_stage1(item)
        
        stats = mock_client.get_stats()
        # Current implementation doesn't track prompt/completion separately
        assert stats["total_tokens"] == 330  # 150 + 180
    
    @pytest.mark.asyncio
    async def test_error_rate_tracking(self, mock_client):
        """Test error rate calculation"""
        # Mix of success and failure responses
        responses = [
            Mock(status_code=200, headers={}, json=lambda: {
                "choices": [{"message": {"content": json.dumps({
                    "term_number": 1, "term": "test", "ipa": "test", "pos": "noun",
                    "primary_meaning": "test", "other_meanings": "", "metaphor": "test metaphor",
                    "metaphor_noun": "test", "metaphor_action": "tests", "suggested_location": "test location",
                    "anchor_object": "test object", "anchor_sensory": "test sense", "explanation": "test explanation",
                    "usage_context": None, "comparison": {"vs": "other", "nuance": "test"}, "homonyms": [], "korean_keywords": ["test"]
                })}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
            }),
            Mock(status_code=500, json=lambda: {"error": {"message": "Server error"}}),
            Mock(status_code=200, headers={}, json=lambda: {
                "choices": [{"message": {"content": json.dumps({
                    "term_number": 1, "term": "test", "ipa": "test", "pos": "noun",
                    "primary_meaning": "test", "other_meanings": "", "metaphor": "test metaphor",
                    "metaphor_noun": "test", "metaphor_action": "tests", "suggested_location": "test location",
                    "anchor_object": "test object", "anchor_sensory": "test sense", "explanation": "test explanation",
                    "usage_context": None, "comparison": {"vs": "other", "nuance": "test"}, "homonyms": [], "korean_keywords": ["test"]
                })}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
            }),
            Mock(status_code=429, headers={"retry-after": "60"}, json=lambda: {"error": {"message": "Rate limited"}})
        ]
        mock_client.client.post.side_effect = responses
        
        # Make requests, catching errors
        for i in range(4):
            item = VocabularyItem(position=i, term="test", type="noun")
            try:
                await mock_client.process_stage1(item)
            except Exception:
                pass
        
        stats = mock_client.get_stats()
        assert stats["total_requests"] == 4
        assert stats["successful_requests"] == 2
        assert stats["failed_requests"] == 2
        # Calculate error rate
        assert stats["success_rate"] == 50.0  # 2 successes out of 4 requests


class TestApiClientIntegration:
    """Test API client integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_complete_vocabulary_processing(self):
        """Test complete vocabulary item processing through both stages"""
        client = OpenRouterClient(api_key="test-key")
        client.client = AsyncMock(spec=httpx.AsyncClient)
        
        # Mock Stage 1 response
        stage1_response = Mock()
        stage1_response.status_code = 200
        stage1_response.json.return_value = {
            "id": "stage1-id",
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "term_number": 1,
                        "term": "안녕하세요",
                        "ipa": "annyeonghaseyo",
                        "pos": "interjection",
                        "primary_meaning": "hello",
                        "other_meanings": "good day",
                        "metaphor": "sunshine greeting",
                        "metaphor_noun": "sunshine",
                        "metaphor_action": "greets",
                        "suggested_location": "doorway",
                        "anchor_object": "welcome mat",
                        "anchor_sensory": "warm feeling",
                        "explanation": "Formal greeting used in polite situations",
                        "usage_context": "When meeting someone for the first time",
                        "comparison": {
                            "vs": "안녕",
                            "nuance": "More formal than 안녕, used with strangers or elders"
                        },
                        "homonyms": [],
                        "korean_keywords": ["인사", "예의"]
                    })
                }
            }],
            "usage": {"prompt_tokens": 150, "completion_tokens": 100, "total_tokens": 250}
        }
        
        # Mock Stage 2 response
        stage2_response = Mock()
        stage2_response.status_code = 200
        stage2_response.json.return_value = {
            "id": "stage2-id",
            "choices": [{
                "message": {
                    "content": """1\t안녕하세요 [annyeonghaseyo]\t1\tScene\tMemory room\tWhat greeting?\t안녕하세요 - formal hello\tgreeting,formal\tformal
1\t안녕하세요 [annyeonghaseyo]\t2\tUsage\tMemory room\tWhen to use?\tUse with strangers or elders\tusage,formal\tformal"""
                }
            }],
            "usage": {"prompt_tokens": 200, "completion_tokens": 150, "total_tokens": 350}
        }
        
        client.client.post.side_effect = [stage1_response, stage2_response]
        
        # Process vocabulary item
        item = VocabularyItem(position=1, term="안녕하세요", type="interjection")
        
        # Process through both stages
        stage1_result, usage1 = await client.process_stage1(item)
        stage2_result, usage2 = await client.process_stage2(item, stage1_result)
        
        # Verify Stage 1
        assert stage1_result.ipa == "annyeonghaseyo"
        assert stage1_result.primary_meaning == "hello"
        assert stage1_result.comparison.vs == "안녕"
        assert usage1.total_tokens == 250
        
        # Verify Stage 2
        assert len(stage2_result.rows) == 2
        assert stage2_result.rows[0].tab_name == "Scene"
        assert stage2_result.rows[1].tab_name == "Usage"
        assert usage2.total_tokens == 350
        
        # Verify total usage
        total_tokens = usage1.total_tokens + usage2.total_tokens
        assert total_tokens == 600