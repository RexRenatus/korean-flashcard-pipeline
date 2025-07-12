"""Enhanced OpenRouter API client with advanced retry and error handling"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx

from ..utils.retry import RetryConfig, retry_async
from ..exceptions import (
    StructuredAPIError,
    StructuredRateLimitError,
    CircuitBreakerError,
    ErrorCategory,
    NetworkError,
)
from ..core.models import (
    Stage1Output,
    Stage2Input,
    Stage2Output,
    APIUsageStats,
    NuanceCreatorOutput,
    FlashcardOutput,
)
from ..core.constants import (
    DEFAULT_API_TIMEOUT,
    DEFAULT_RETRY_COUNT,
    DEFAULT_MODEL,
)
from ..rate_limiter import RateLimiter
from ..circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class EnhancedOpenRouterClient:
    """OpenRouter API client with enhanced retry logic and structured error handling"""
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = DEFAULT_MODEL,
        rate_limiter: Optional[RateLimiter] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        cache_service=None,
        database_manager=None,
        timeout: int = DEFAULT_API_TIMEOUT,
        retry_config: Optional[RetryConfig] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.rate_limiter = rate_limiter
        self.circuit_breaker = circuit_breaker
        self.cache = cache_service
        self.db_manager = database_manager
        self.timeout = timeout
        
        # Use custom retry config or defaults with jitter
        self.retry_config = retry_config or RetryConfig(
            max_attempts=DEFAULT_RETRY_COUNT,
            initial_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=True,
            retry_on=(httpx.HTTPError, NetworkError, StructuredAPIError)
        )
        
        # HTTP client with optimized settings
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
                keepalive_expiry=30,
            ),
            http2=True,  # Enable HTTP/2
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
        
        # Health metrics
        self.health_metrics = {
            "success_rate": 1.0,
            "avg_latency_ms": 0.0,
            "error_rate": 0.0,
            "last_error": None,
            "consecutive_failures": 0,
        }
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    def _update_health_metrics(self, success: bool, latency_ms: float):
        """Update health metrics for monitoring"""
        # Update success rate (exponential moving average)
        alpha = 0.1  # Smoothing factor
        self.health_metrics["success_rate"] = (
            alpha * (1.0 if success else 0.0) + 
            (1 - alpha) * self.health_metrics["success_rate"]
        )
        
        # Update average latency
        if success:
            self.health_metrics["avg_latency_ms"] = (
                alpha * latency_ms + 
                (1 - alpha) * self.health_metrics["avg_latency_ms"]
            )
        
        # Update error tracking
        if success:
            self.health_metrics["consecutive_failures"] = 0
        else:
            self.health_metrics["consecutive_failures"] += 1
            self.health_metrics["last_error"] = datetime.utcnow()
        
        self.health_metrics["error_rate"] = 1.0 - self.health_metrics["success_rate"]
    
    async def _check_circuit_breaker(self):
        """Check if circuit breaker allows the request"""
        if self.circuit_breaker and not await self.circuit_breaker.is_allowed():
            self.stats.circuit_breaker_trips += 1
            raise CircuitBreakerError(
                message="Circuit breaker is open",
                service="openrouter_api",
                failure_count=self.circuit_breaker._failure_count,
                threshold=self.circuit_breaker.failure_threshold,
            )
    
    async def _check_rate_limit(self):
        """Check if rate limiter allows the request"""
        if self.rate_limiter and not await self.rate_limiter.acquire():
            self.stats.rate_limit_hits += 1
            retry_after = await self.rate_limiter.get_retry_after()
            raise StructuredRateLimitError(
                message="Rate limit exceeded",
                retry_after=retry_after,
            )
    
    @retry_async()  # Uses the default retry config from the decorator
    async def _make_request_with_retry(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        """Make API request with enhanced retry logic"""
        
        # Pre-flight checks
        await self._check_circuit_breaker()
        await self._check_rate_limit()
        
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
            
            # Handle different status codes with structured errors
            if response.status_code == 429:
                # Extract retry-after header if available
                retry_after = None
                if "retry-after" in response.headers:
                    try:
                        retry_after = float(response.headers["retry-after"])
                    except ValueError:
                        pass
                
                raise StructuredRateLimitError(
                    message="Rate limit exceeded",
                    retry_after=retry_after,
                )
            
            response.raise_for_status()
            
            # Record success
            if self.circuit_breaker:
                await self.circuit_breaker.record_success()
            
            # Update metrics
            latency = (time.time() - start_time) * 1000
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
            latency = (time.time() - start_time) * 1000
            self._update_health_metrics(False, latency)
            
            self.stats.errors += 1
            
            # Convert to structured error
            response_data = None
            try:
                response_data = e.response.json()
            except:
                response_data = {"text": e.response.text}
            
            raise StructuredAPIError(
                status_code=e.response.status_code,
                message=f"API request failed: {e}",
                response=response_data,
            )
            
        except httpx.NetworkError as e:
            # Network-level errors
            if self.circuit_breaker:
                await self.circuit_breaker.record_failure()
            
            latency = (time.time() - start_time) * 1000
            self._update_health_metrics(False, latency)
            
            self.stats.errors += 1
            
            raise NetworkError(
                message=f"Network error: {e}",
                original_error=e,
            )
            
        except Exception as e:
            # Unexpected errors
            if self.circuit_breaker:
                await self.circuit_breaker.record_failure()
            
            latency = (time.time() - start_time) * 1000
            self._update_health_metrics(False, latency)
            
            self.stats.errors += 1
            raise
    
    async def process_stage1(
        self, term: str, pos: str, temperature: float = 0.7
    ) -> Stage1Output:
        """Process Stage 1: Generate nuances with enhanced error handling"""
        
        # Check cache first
        if self.cache:
            try:
                cached = await self.cache.get_stage1(term, pos)
                if cached:
                    self.stats.cache_hits += 1
                    return cached
            except Exception as e:
                logger.warning(f"Cache retrieval failed: {e}")
            
            self.stats.cache_misses += 1
        
        # Prepare prompt
        messages = [
            {
                "role": "system",
                "content": "You are a Korean language expert creating educational flashcards."
            },
            {
                "role": "user",
                "content": self._build_stage1_prompt(term, pos)
            }
        ]
        
        # Make request with retry
        response = await self._make_request_with_retry(messages, temperature=temperature)
        
        # Parse response
        content = response["choices"][0]["message"]["content"]
        
        # Create output
        output = Stage1Output(
            term=term,
            pos=pos,
            nuances=self._parse_nuances(content),
            raw_output=content,
            created_at=datetime.utcnow(),
        )
        
        # Cache result
        if self.cache:
            try:
                await self.cache.set_stage1(term, pos, output)
            except Exception as e:
                logger.warning(f"Cache storage failed: {e}")
        
        # Store in database if available
        if self.db_manager:
            try:
                await self.db_manager.store_stage1_output(output)
            except Exception as e:
                logger.warning(f"Database storage failed: {e}")
        
        return output
    
    async def process_stage2(
        self, term: str, pos: str, nuances: List[str], temperature: float = 0.7
    ) -> Stage2Output:
        """Process Stage 2: Generate flashcards with enhanced error handling"""
        
        # Check cache first
        if self.cache:
            try:
                cached = await self.cache.get_stage2(term, pos)
                if cached:
                    self.stats.cache_hits += 1
                    return cached
            except Exception as e:
                logger.warning(f"Cache retrieval failed: {e}")
            
            self.stats.cache_misses += 1
        
        # Prepare prompt
        messages = [
            {
                "role": "system",
                "content": "You are creating Korean language flashcards with example sentences."
            },
            {
                "role": "user",
                "content": self._build_stage2_prompt(term, pos, nuances)
            }
        ]
        
        # Make request with retry
        response = await self._make_request_with_retry(messages, temperature=temperature)
        
        # Parse response
        content = response["choices"][0]["message"]["content"]
        
        # Create output
        output = Stage2Output(
            term=term,
            pos=pos,
            flashcards=self._parse_flashcards(content),
            raw_output=content,
            created_at=datetime.utcnow(),
        )
        
        # Cache result
        if self.cache:
            try:
                await self.cache.set_stage2(term, pos, output)
            except Exception as e:
                logger.warning(f"Cache storage failed: {e}")
        
        # Store in database if available
        if self.db_manager:
            try:
                await self.db_manager.store_stage2_output(output)
            except Exception as e:
                logger.warning(f"Database storage failed: {e}")
        
        return output
    
    def _build_stage1_prompt(self, term: str, pos: str) -> str:
        """Build prompt for Stage 1"""
        return f"""Create nuanced meanings for the Korean term:
Term: {term}
Part of Speech: {pos}

Provide 3-5 distinct nuances or uses of this term, each with:
1. A clear explanation of the specific meaning
2. Common contexts where this nuance applies
3. Any connotations or formality levels

Format as a numbered list."""
    
    def _build_stage2_prompt(self, term: str, pos: str, nuances: List[str]) -> str:
        """Build prompt for Stage 2"""
        nuances_text = "\n".join(f"{i+1}. {n}" for i, n in enumerate(nuances))
        
        return f"""Create flashcards for the Korean term:
Term: {term}
Part of Speech: {pos}

Nuances:
{nuances_text}

For each nuance, create a flashcard with:
1. Korean example sentence
2. English translation
3. Romanization (revised)
4. Usage notes or cultural context

Format each flashcard clearly with labels."""
    
    def _parse_nuances(self, content: str) -> List[str]:
        """Parse nuances from Stage 1 output"""
        # Simple parsing - can be enhanced with proper NLP
        lines = content.strip().split("\n")
        nuances = []
        
        for line in lines:
            line = line.strip()
            # Look for numbered items
            if line and (line[0].isdigit() or line.startswith("-")):
                # Remove numbering/bullets
                cleaned = line.lstrip("0123456789.-) ").strip()
                if cleaned:
                    nuances.append(cleaned)
        
        return nuances[:5]  # Limit to 5 nuances
    
    def _parse_flashcards(self, content: str) -> List[Dict[str, Any]]:
        """Parse flashcards from Stage 2 output"""
        # Simple parsing - can be enhanced with proper NLP
        flashcards = []
        
        # Split by flashcard markers
        sections = content.split("Flashcard")
        
        for section in sections[1:]:  # Skip first empty section
            flashcard = {}
            
            # Extract fields with simple pattern matching
            lines = section.strip().split("\n")
            
            for line in lines:
                line = line.strip()
                if "Korean:" in line or "Example:" in line:
                    flashcard["korean"] = line.split(":", 1)[1].strip()
                elif "English:" in line or "Translation:" in line:
                    flashcard["english"] = line.split(":", 1)[1].strip()
                elif "Romanization:" in line:
                    flashcard["romanization"] = line.split(":", 1)[1].strip()
                elif "Notes:" in line or "Context:" in line:
                    flashcard["notes"] = line.split(":", 1)[1].strip()
            
            if flashcard:
                flashcards.append(flashcard)
        
        return flashcards
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status of the client"""
        return {
            "stats": {
                "requests": self.stats.requests,
                "tokens_used": self.stats.tokens_used,
                "cache_hits": self.stats.cache_hits,
                "cache_misses": self.stats.cache_misses,
                "errors": self.stats.errors,
                "rate_limit_hits": self.stats.rate_limit_hits,
                "circuit_breaker_trips": self.stats.circuit_breaker_trips,
            },
            "health": self.health_metrics,
            "retry_config": {
                "max_attempts": self.retry_config.max_attempts,
                "initial_delay": self.retry_config.initial_delay,
                "max_delay": self.retry_config.max_delay,
                "jitter": self.retry_config.jitter,
            }
        }