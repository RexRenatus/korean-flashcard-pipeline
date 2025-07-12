"""OpenRouter API client for Korean flashcard generation"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

import httpx
from httpx import AsyncClient, Response
from dotenv import load_dotenv

from .models import (
    VocabularyItem,
    Stage1Request,
    Stage1Response,
    Stage2Request,
    Stage2Response,
    ApiResponse,
    ApiUsage,
    RateLimitInfo
)
from .exceptions import (
    ApiError,
    RateLimitError,
    AuthenticationError,
    NetworkError,
    ValidationError,
    CircuitBreakerError
)
from .rate_limiter import CompositeLimiter
from .circuit_breaker import MultiServiceCircuitBreaker
from .cache import CacheService


logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Async client for OpenRouter API"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 rate_limiter: Optional[CompositeLimiter] = None,
                 circuit_breaker: Optional[MultiServiceCircuitBreaker] = None,
                 cache_service: Optional[CacheService] = None):
        """Initialize the OpenRouter client
        
        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            base_url: Base URL for API (defaults to official endpoint)
            rate_limiter: Optional rate limiter instance
            circuit_breaker: Optional circuit breaker instance
            cache_service: Optional cache service instance
        """
        # Load .env file if it exists
        env_path = Path.cwd() / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            logger.debug(f"Loaded environment from {env_path}")
        
        self.api_key = api_key or os.environ.get('OPENROUTER_API_KEY')
        if not self.api_key:
            raise AuthenticationError("OPENROUTER_API_KEY not found in environment or .env file")
        
        self.base_url = base_url or "https://openrouter.ai/api/v1/chat/completions"
        
        # HTTP client configuration
        self.client: Optional[AsyncClient] = None
        self.timeout = httpx.Timeout(30.0, connect=5.0)
        
        # Rate limiting, circuit breaker, and caching
        self.rate_limiter = rate_limiter or CompositeLimiter()
        self.circuit_breaker = circuit_breaker or MultiServiceCircuitBreaker()
        self.cache_service = cache_service or CacheService()
        
        # Rate limit tracking
        self.rate_limit_info: Optional[RateLimitInfo] = None
        
        # Request statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        if self.client is None:
            # Configure connection pooling
            limits = httpx.Limits(
                max_keepalive_connections=10,  # Connections to keep alive
                max_connections=20,            # Maximum concurrent connections
                keepalive_expiry=30.0         # Keep connections alive for 30s
            )
            
            self.client = AsyncClient(
                timeout=self.timeout,
                limits=limits,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "korean-flashcard-pipeline/0.1.0"
                },
                http2=False  # Disable HTTP/2 (requires h2 package)
            )
    
    async def close(self):
        """Close the HTTP client"""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    async def process_stage1(self, vocabulary_item: VocabularyItem) -> Tuple[Stage1Response, ApiUsage]:
        """Process Stage 1: Semantic Analysis
        
        Args:
            vocabulary_item: Input vocabulary item
            
        Returns:
            Tuple of (Stage1Response, ApiUsage)
        """
        # Check cache first
        cached_result = await self.cache_service.get_stage1(vocabulary_item)
        if cached_result:
            logger.info(f"Stage 1 cache hit: {vocabulary_item.term}")
            # Unpack the result tuple
            stage1_response, tokens_saved = cached_result
            # Create a mock usage object for cached results
            usage = ApiUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
            return stage1_response, usage
        
        # Create request
        request = Stage1Request.from_vocabulary_item(vocabulary_item)
        
        # Make API call
        logger.info(f"Stage 1 processing: {vocabulary_item.term}")
        response = await self._make_request(request.model_dump())
        
        # Parse response
        try:
            api_response = ApiResponse(**response)
            content = api_response.get_content()
        except Exception as e:
            logger.error(f"Failed to parse API response structure: {e}")
            logger.error(f"Raw response: {response}")
            raise ValidationError(f"Invalid API response structure: {e}", "api_response", str(response))
        
        logger.info(f"Stage 1 content received: {content[:200]}...")  # First 200 chars
        
        # Extract JSON from markdown code block if present
        import re
        
        # Try to find JSON in markdown code block
        json_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', content, re.DOTALL)
        if json_match:
            json_content = json_match.group(1)
        else:
            # If no markdown block, assume the entire content is JSON
            json_content = content.strip()
        
        try:
            stage1_data = json.loads(json_content)
            stage1_response = Stage1Response(**stage1_data)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse Stage 1 JSON: {content}")
            raise ValidationError(f"Invalid Stage 1 response format: {e}", "response", content)
        
        # Update statistics
        self._update_stats(api_response.usage)
        
        # Cache the result
        await self.cache_service.save_stage1(vocabulary_item, stage1_response, api_response.usage.total_tokens)
        
        return stage1_response, api_response.usage
    
    async def process_stage2(self, vocabulary_item: VocabularyItem, 
                           stage1_result: Stage1Response) -> Tuple[Stage2Response, ApiUsage]:
        """Process Stage 2: Flashcard Generation
        
        Args:
            vocabulary_item: Original vocabulary item
            stage1_result: Result from Stage 1 processing
            
        Returns:
            Tuple of (Stage2Response, ApiUsage)
        """
        # Check cache first
        cached_result = await self.cache_service.get_stage2(vocabulary_item, stage1_result)
        if cached_result:
            logger.info(f"Stage 2 cache hit: {vocabulary_item.term}")
            # Unpack the result tuple
            stage2_response, tokens_saved = cached_result
            # Create a mock usage object for cached results
            usage = ApiUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
            return stage2_response, usage
        
        # Create request
        request = Stage2Request.from_stage1_result(vocabulary_item, stage1_result)
        
        # Make API call
        logger.info(f"Stage 2 processing: {vocabulary_item.term}")
        response = await self._make_request(request.model_dump())
        
        # Parse response
        api_response = ApiResponse(**response)
        content = api_response.get_content()
        
        logger.info(f"Stage 2 content received: {content[:200]}...")  # First 200 chars
        
        # Extract TSV from markdown code block if present
        if content.strip().startswith("```"):
            # Remove markdown code block markers
            lines = content.strip().split('\n')
            if lines[0].startswith("```"):
                lines = lines[1:]  # Remove first line
            if lines[-1] == "```":
                lines = lines[:-1]  # Remove last line
            content = '\n'.join(lines)
        
        try:
            stage2_response = Stage2Response.from_tsv_content(content)
        except Exception as e:
            logger.error(f"Failed to parse Stage 2 TSV: {content}")
            raise ValidationError(f"Invalid Stage 2 response format: {e}", "response", content)
        
        # Update statistics
        self._update_stats(api_response.usage)
        
        # Cache the result
        await self.cache_service.save_stage2(vocabulary_item, stage1_result, stage2_response, api_response.usage.total_tokens)
        
        return stage2_response, api_response.usage
    
    async def process_item_complete(self, vocabulary_item: VocabularyItem) -> Tuple[Stage2Response, int]:
        """Process a vocabulary item through both stages
        
        Args:
            vocabulary_item: Input vocabulary item
            
        Returns:
            Tuple of (Stage2Response, total_tokens_used)
        """
        # Stage 1
        stage1_result, usage1 = await self.process_stage1(vocabulary_item)
        
        # Stage 2
        stage2_result, usage2 = await self.process_stage2(vocabulary_item, stage1_result)
        
        total_tokens = usage1.total_tokens + usage2.total_tokens
        
        return stage2_result, total_tokens
    
    async def _make_request(self, payload: Dict[str, Any], retry_count: int = 0) -> Dict[str, Any]:
        """Make HTTP request with retry logic
        
        Args:
            payload: Request payload
            retry_count: Current retry attempt
            
        Returns:
            Response JSON data
        """
        await self._ensure_client()
        
        max_retries = 3
        base_delay = 1.0  # seconds
        
        # Determine which stage this is for rate limiting
        stage = 1 if "@preset/nuance-creator" in str(payload.get("model", "")) else 2
        
        try:
            # Check rate limit before making request
            await self.rate_limiter.acquire_for_stage(stage)
            
            # Make request through circuit breaker
            async def make_api_call():
                self.stats["total_requests"] += 1
                return await self.client.post(
                    self.base_url,
                    json=payload
                )
            
            response = await self.circuit_breaker.call("openrouter", make_api_call)
            
            # Update rate limit info
            if response.headers:
                self.rate_limit_info = RateLimitInfo.from_headers(dict(response.headers))
            
            # Handle different status codes
            if response.status_code == 200:
                self.stats["successful_requests"] += 1
                # Notify rate limiter of success
                await self.rate_limiter.on_success()
                data = response.json()
                logger.debug(f"API Response: {data}")
                return data
            
            elif response.status_code == 429:
                # Rate limit exceeded
                self.stats["failed_requests"] += 1
                retry_after = int(response.headers.get('Retry-After', 60))
                
                # Notify rate limiter of rate limit hit
                await self.rate_limiter.on_rate_limit(retry_after)
                
                if retry_count < max_retries:
                    logger.warning(f"Rate limit hit, waiting {retry_after}s before retry")
                    await asyncio.sleep(retry_after)
                    return await self._make_request(payload, retry_count + 1)
                
                raise RateLimitError(
                    "Rate limit exceeded after retries",
                    retry_after=retry_after,
                    reset_at=int(response.headers.get('X-RateLimit-Reset', 0))
                )
            
            elif response.status_code == 401:
                self.stats["failed_requests"] += 1
                raise AuthenticationError("Invalid API key")
            
            else:
                # Other errors
                self.stats["failed_requests"] += 1
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                error_message = error_data.get('error', {}).get('message', response.text)
                
                if retry_count < max_retries and response.status_code >= 500:
                    # Retry on server errors
                    delay = base_delay * (2 ** retry_count)
                    logger.warning(f"Server error {response.status_code}, retrying in {delay}s")
                    await asyncio.sleep(delay)
                    return await self._make_request(payload, retry_count + 1)
                
                raise ApiError(
                    f"API error: {error_message}",
                    status_code=response.status_code,
                    response_body=response.text
                )
        
        except httpx.NetworkError as e:
            self.stats["failed_requests"] += 1
            if retry_count < max_retries:
                delay = base_delay * (2 ** retry_count)
                logger.warning(f"Network error, retrying in {delay}s: {e}")
                await asyncio.sleep(delay)
                return await self._make_request(payload, retry_count + 1)
            
            raise NetworkError(f"Network error after {max_retries} retries: {str(e)}", original_error=e)
        
        except httpx.TimeoutException as e:
            self.stats["failed_requests"] += 1
            if retry_count < max_retries:
                delay = base_delay * (2 ** retry_count)
                logger.warning(f"Request timeout, retrying in {delay}s")
                await asyncio.sleep(delay)
                return await self._make_request(payload, retry_count + 1)
            
            raise NetworkError(f"Request timeout after {max_retries} retries: {str(e)}", original_error=e)
        
        except CircuitBreakerError as e:
            # Circuit is open, don't retry
            self.stats["failed_requests"] += 1
            logger.warning(f"Circuit breaker is open: {e}")
            raise
    
    def _update_stats(self, usage: ApiUsage):
        """Update internal statistics"""
        self.stats["total_tokens"] += usage.total_tokens
        self.stats["total_cost"] += usage.estimated_cost
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        return {
            **self.stats,
            "success_rate": (
                self.stats["successful_requests"] / self.stats["total_requests"] 
                if self.stats["total_requests"] > 0 else 0.0
            ),
            "average_tokens_per_request": (
                self.stats["total_tokens"] / self.stats["successful_requests"]
                if self.stats["successful_requests"] > 0 else 0.0
            )
        }
    
    async def check_rate_limit(self) -> Optional[RateLimitInfo]:
        """Check current rate limit status
        
        Returns:
            Current rate limit info if available
        """
        if not self.rate_limit_info:
            # Make a minimal request to get rate limit info
            try:
                await self._ensure_client()
                response = await self.client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                if response.headers:
                    self.rate_limit_info = RateLimitInfo.from_headers(dict(response.headers))
            except Exception as e:
                logger.warning(f"Failed to check rate limit: {e}")
        
        return self.rate_limit_info
    
    def should_wait_for_rate_limit(self) -> Tuple[bool, Optional[float]]:
        """Check if we should wait due to rate limits
        
        Returns:
            Tuple of (should_wait, wait_seconds)
        """
        if not self.rate_limit_info:
            return False, None
        
        # If we have less than 5 requests remaining, wait
        if self.rate_limit_info.remaining < 5:
            wait_until = self.rate_limit_info.reset_at
            wait_seconds = max(0, (wait_until - datetime.now()).total_seconds())
            return True, wait_seconds
        
        return False, None
    
    async def test_connection(self) -> bool:
        """Test the API connection
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Simple test to check if API is reachable
            await self._ensure_client()
            response = await self.client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10.0
            )
            response.raise_for_status()
            logger.info("API connection test successful")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        return self.cache_service.get_stats()