"""Unified OpenRouter API client with simple and advanced modes"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
    before_sleep_log,
)

from ..core.models import (
    Stage1Response,
    Stage2Response,
    Stage1Request,
    Stage2Request,
    FlashcardRow,
    VocabularyItem,
    ApiUsage,
)
from ..core.exceptions import ApiError as APIError, RateLimitError, CircuitBreakerError, AuthenticationError
from ..core.constants import (
    DEFAULT_API_TIMEOUT,
    DEFAULT_RETRY_COUNT,
    DEFAULT_MODEL,
)
from ..rate_limiter import RateLimiter
from ..circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class APIUsageStats:
    """Simple class to track API usage statistics"""
    def __init__(self, requests=0, tokens_used=0, cache_hits=0, cache_misses=0, 
                 errors=0, rate_limit_hits=0, circuit_breaker_trips=0):
        self.requests = requests
        self.tokens_used = tokens_used
        self.cache_hits = cache_hits
        self.cache_misses = cache_misses
        self.errors = errors
        self.rate_limit_hits = rate_limit_hits
        self.circuit_breaker_trips = circuit_breaker_trips
    
    def model_dump(self):
        """Return dictionary representation"""
        return {
            "requests": self.requests,
            "tokens_used": self.tokens_used,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "errors": self.errors,
            "rate_limit_hits": self.rate_limit_hits,
            "circuit_breaker_trips": self.circuit_breaker_trips
        }


class ClientMode:
    """Client operation modes"""
    SIMPLE = "simple"  # Basic functionality only
    ADVANCED = "advanced"  # Full features with database


class OpenRouterClient:
    """Unified OpenRouter API client"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = DEFAULT_MODEL,
        mode: str = ClientMode.SIMPLE,
        rate_limiter: Optional[RateLimiter] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        cache_service=None,
        database_manager=None,
        timeout: int = DEFAULT_API_TIMEOUT,
        max_retries: int = DEFAULT_RETRY_COUNT,
    ):
        # Get API key from argument or environment
        self.api_key = api_key or os.environ.get('OPENROUTER_API_KEY')
        if not self.api_key:
            raise AuthenticationError("API key must be provided or set in OPENROUTER_API_KEY environment variable")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.mode = mode
        self.rate_limiter = rate_limiter
        self.circuit_breaker = circuit_breaker
        self.cache = cache_service
        self.cache_service = cache_service  # Alias for compatibility
        self.db_manager = database_manager if mode == ClientMode.ADVANCED else None
        self.timeout = timeout
        self.max_retries = max_retries
        
        # HTTP client with optimized settings
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
                keepalive_expiry=30,
            ),
        )
        
        # Statistics tracking
        self.stats = APIUsageStats(
            requests=0,
            tokens_used=0,
            cache_hits=0,
            cache_misses=0,
            errors=0,
            rate_limit_hits=0,
            circuit_breaker_trips=0,
        )
        
        # Advanced mode features
        if self.mode == ClientMode.ADVANCED:
            self._init_advanced_features()
    
    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        # This is called by tests - no-op since we initialize in __init__
        pass
    
    def _init_advanced_features(self):
        """Initialize advanced mode features"""
        self.health_metrics = {
            "latency_ms": [],
            "success_count": 0,
            "error_count": 0,
            "last_error": None,
            "health_score": 1.0,
        }
        self.request_history: List[Dict[str, Any]] = []
        
        # Initialize output parsers if available
        try:
            from ..parsers import NuanceOutputParser, FlashcardOutputParser
            self.nuance_parser = NuanceOutputParser()
            self.flashcard_parser = FlashcardOutputParser()
        except ImportError:
            logger.warning("Output parsers not available, using basic parsing")
            self.nuance_parser = None
            self.flashcard_parser = None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, APIError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _make_request(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        """Make API request with retry logic"""
        
        # Check rate limiter
        if self.rate_limiter:
            try:
                await self.rate_limiter.acquire()
            except Exception as e:
                self.stats.rate_limit_hits += 1
                raise RateLimitError(f"Rate limit exceeded: {e}")
        
        # Check circuit breaker
        if self.circuit_breaker:
            if not await self.circuit_breaker.call():
                self.stats.circuit_breaker_trips += 1
                raise CircuitBreakerError("Circuit breaker is open")
        
        # Prepare request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/example/flashcard-pipeline",
            "X-Title": "Flashcard Generation Pipeline",
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        start_time = time.time()
        
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            
            # Record success
            if self.circuit_breaker:
                await self.circuit_breaker.record_success()
            
            # Update metrics
            latency = (time.time() - start_time) * 1000
            if self.mode == ClientMode.ADVANCED:
                self._update_health_metrics(True, latency)
            
            result = response.json()
            
            # Update stats
            self.stats.requests += 1
            if "usage" in result:
                self.stats.tokens_used += result["usage"].get("total_tokens", 0)
            
            return result
            
        except httpx.HTTPStatusError as e:
            # Record failure
            if self.circuit_breaker:
                await self.circuit_breaker.record_failure()
            
            # Update metrics
            if self.mode == ClientMode.ADVANCED:
                self._update_health_metrics(False, time.time() - start_time)
            
            self.stats.errors += 1
            
            if e.response.status_code == 429:
                raise RateLimitError(f"Rate limit exceeded: {e}")
            raise APIError(f"API request failed: {e}")
            
        except Exception as e:
            if self.circuit_breaker:
                await self.circuit_breaker.record_failure()
            
            if self.mode == ClientMode.ADVANCED:
                self._update_health_metrics(False, time.time() - start_time)
            
            self.stats.errors += 1
            raise APIError(f"Unexpected error: {e}")
    
    async def process_stage1(
        self, item: VocabularyItem, temperature: float = 0.7
    ) -> Tuple[Stage1Response, ApiUsage]:
        """Process Stage 1: Generate nuances"""
        
        # Initialize default cache_service and rate_limiter if not provided
        if not hasattr(self, 'cache_service'):
            self.cache_service = self.cache
        if not hasattr(self, 'rate_limiter') or self.rate_limiter is None:
            from ..api.rate_limiter import RateLimiter
            self.rate_limiter = RateLimiter()
        if not hasattr(self, 'circuit_breaker') or self.circuit_breaker is None:
            from ..api.circuit_breaker import CircuitBreaker
            self.circuit_breaker = CircuitBreaker()
        
        # Check cache first
        if self.cache_service:
            cached = await self.cache_service.get_stage1(item)
            if cached:
                self.stats.cache_hits += 1
                # Return cached result with zero usage
                return cached[0], ApiUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
            self.stats.cache_misses += 1
        
        # Create Stage1Request from VocabularyItem
        request = Stage1Request.from_vocabulary_item(item)
        
        # Rate limiting
        if hasattr(self.rate_limiter, 'acquire_for_stage'):
            await self.rate_limiter.acquire_for_stage('stage1')
        
        # Circuit breaker call
        async def make_api_call():
            # Make request
            response = await self._make_request(request.messages, temperature=temperature)
            
            # Parse response
            content = response["choices"][0]["message"]["content"]
            
            # Use appropriate parser
            if self.mode == ClientMode.ADVANCED and self.nuance_parser:
                output = self.nuance_parser.parse(content)
            else:
                output = self._parse_stage1_basic(content)
            
            # Create ApiUsage from response
            usage_data = response.get("usage", {})
            usage = ApiUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0)
            )
            
            return output, usage
        
        if hasattr(self.circuit_breaker, 'call'):
            output, usage = await self.circuit_breaker.call('stage1', make_api_call)
        else:
            output, usage = await make_api_call()
        
        # Save to cache
        if self.cache_service:
            await self.cache_service.save_stage1(item, output, usage.total_tokens)
        
        # Archive if in advanced mode
        if self.mode == ClientMode.ADVANCED and self.db_manager:
            await self._archive_output("stage1", item.term, output)
        
        # Notify rate limiter of success
        if hasattr(self.rate_limiter, 'on_success'):
            await self.rate_limiter.on_success()
        
        return output, usage
    
    async def process_stage2(
        self, item: VocabularyItem, stage1_result: Stage1Response, temperature: float = 0.7
    ) -> Tuple[Stage2Response, ApiUsage]:
        """Process Stage 2: Generate flashcards"""
        
        # Initialize default cache_service and rate_limiter if not provided
        if not hasattr(self, 'cache_service'):
            self.cache_service = self.cache
        if not hasattr(self, 'rate_limiter') or self.rate_limiter is None:
            from ..api.rate_limiter import RateLimiter
            self.rate_limiter = RateLimiter()
        if not hasattr(self, 'circuit_breaker') or self.circuit_breaker is None:
            from ..api.circuit_breaker import CircuitBreaker
            self.circuit_breaker = CircuitBreaker()
        
        # Check cache first
        if self.cache_service:
            cached = await self.cache_service.get_stage2(item, stage1_result)
            if cached:
                self.stats.cache_hits += 1
                # Return cached result with zero usage
                return cached[0], ApiUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
            self.stats.cache_misses += 1
        
        # Create Stage2Request from Stage1Result
        stage2_request = Stage2Request.from_stage1_result(item, stage1_result)
        
        # Rate limiting
        if hasattr(self.rate_limiter, 'acquire_for_stage'):
            await self.rate_limiter.acquire_for_stage('stage2')
        
        # Circuit breaker call
        async def make_api_call():
            # Make request
            response = await self._make_request(stage2_request.messages, temperature=temperature)
            
            # Parse response
            content = response["choices"][0]["message"]["content"]
            
            # Use appropriate parser
            if self.mode == ClientMode.ADVANCED and self.flashcard_parser:
                output = self.flashcard_parser.parse(content)
            else:
                output = self._parse_stage2_basic(content)
            
            # Create ApiUsage from response
            usage_data = response.get("usage", {})
            usage = ApiUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0)
            )
            
            return output, usage
        
        if hasattr(self.circuit_breaker, 'call'):
            output, usage = await self.circuit_breaker.call('stage2', make_api_call)
        else:
            output, usage = await make_api_call()
        
        # Save to cache
        if self.cache_service:
            await self.cache_service.save_stage2(item, stage1_result, output, usage.total_tokens)
        
        # Archive if in advanced mode
        if self.mode == ClientMode.ADVANCED and self.db_manager:
            await self._archive_output("stage2", item.term, output)
        
        # Notify rate limiter of success
        if hasattr(self.rate_limiter, 'on_success'):
            await self.rate_limiter.on_success()
        
        return output, usage
    
    def _build_stage1_prompt(self, item: VocabularyItem) -> str:
        """Build Stage 1 prompt"""
        return f"""Create comprehensive nuance descriptions for the Korean term: {item.term}
Part of speech: {item.type}

Provide a detailed analysis including:
1. Literal meaning and etymology
2. Common usage contexts
3. Emotional or cultural connotations
4. Comparison with similar terms
5. Example sentences

Format your response as JSON."""
    
    def _build_stage2_prompt(self, stage2_input: Stage2Request) -> str:
        """Build Stage 2 prompt"""
        # Stage2Request has messages field
        if stage2_input.messages and len(stage2_input.messages) > 0:
            return stage2_input.messages[0]["content"]
        else:
            return "Create flashcards for the provided vocabulary item."
    
    def _parse_stage1_basic(self, content: str) -> Stage1Response:
        """Basic parsing for Stage 1 output"""
        try:
            # Try to extract JSON from content
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return Stage1Response.model_validate(data)
            else:
                # Fallback - create minimal response
                raise APIError("Could not parse Stage 1 response as JSON")
        except Exception as e:
            logger.error(f"Failed to parse Stage 1 output: {e}")
            raise APIError(f"Failed to parse response: {e}")
    
    def _parse_stage2_basic(self, content: str) -> Stage2Response:
        """Basic parsing for Stage 2 output"""
        try:
            # Try to extract JSON from content
            import re
            # Stage2Response expects TSV content, not JSON
            # Try to parse as TSV
            if content.strip():
                return Stage2Response.from_tsv_content(content)
            else:
                # Empty response
                raise APIError("Stage 2 response was empty")
        except Exception as e:
            logger.error(f"Failed to parse Stage 2 output: {e}")
            raise APIError(f"Failed to parse response: {e}")
    
    def _update_health_metrics(self, success: bool, latency_ms: float):
        """Update health metrics for advanced mode"""
        self.health_metrics["latency_ms"].append(latency_ms)
        
        # Keep only last 100 latencies
        if len(self.health_metrics["latency_ms"]) > 100:
            self.health_metrics["latency_ms"] = self.health_metrics["latency_ms"][-100:]
        
        if success:
            self.health_metrics["success_count"] += 1
        else:
            self.health_metrics["error_count"] += 1
            self.health_metrics["last_error"] = datetime.now().isoformat()
        
        # Calculate health score
        total = self.health_metrics["success_count"] + self.health_metrics["error_count"]
        if total > 0:
            success_rate = self.health_metrics["success_count"] / total
            avg_latency = sum(self.health_metrics["latency_ms"]) / len(self.health_metrics["latency_ms"])
            
            # Health score based on success rate and latency
            latency_score = max(0, 1 - (avg_latency / 5000))  # 5 seconds as baseline
            self.health_metrics["health_score"] = (success_rate * 0.7) + (latency_score * 0.3)
    
    async def _archive_output(self, stage: str, term: str, output: Any):
        """Archive output to database"""
        if not self.db_manager:
            return
            
        try:
            self.db_manager.execute(
                """INSERT INTO api_outputs (stage, term, output, created_at)
                VALUES (?, ?, ?, ?)""",
                (stage, term, output.model_dump_json(), datetime.now().isoformat())
            )
        except Exception as e:
            logger.error(f"Failed to archive output: {e}")
    
    async def test_connection(self) -> bool:
        """Test API connection"""
        try:
            messages = [{"role": "user", "content": "Hello"}]
            await self._make_request(messages, max_tokens=10)
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        stats = self.stats.model_dump()
        
        # Add mode-specific stats
        stats["mode"] = self.mode
        
        # Add calculated stats
        total_requests = stats["requests"]
        successful_requests = stats["requests"] - stats["errors"]
        failed_requests = stats["errors"]
        
        stats["total_requests"] = total_requests
        stats["successful_requests"] = successful_requests
        stats["failed_requests"] = failed_requests
        stats["total_tokens"] = stats["tokens_used"]
        
        # Calculate success rate
        if total_requests > 0:
            stats["success_rate"] = successful_requests / total_requests
        else:
            stats["success_rate"] = 0.0
        
        if self.mode == ClientMode.ADVANCED:
            stats["health_metrics"] = self.health_metrics
            stats["request_history_size"] = len(self.request_history)
        
        return stats
    
    async def close(self):
        """Close client connections"""
        await self.client.aclose()


# Factory function
def create_api_client(
    api_key: str,
    simple_mode: bool = True,
    **kwargs
) -> OpenRouterClient:
    """Create an API client instance"""
    mode = ClientMode.SIMPLE if simple_mode else ClientMode.ADVANCED
    return OpenRouterClient(api_key=api_key, mode=mode, **kwargs)