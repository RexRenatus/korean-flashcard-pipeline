"""Enhanced OpenRouter API client with database integration and advanced features"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import hashlib
import time

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
from .database import ValidatedDatabaseManager
from .parsers import NuanceOutputParser, FlashcardOutputParser, OutputArchiver

logger = logging.getLogger(__name__)


class ApiHealthStatus(Enum):
    """API health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ApiHealthMetrics:
    """API health metrics"""
    status: ApiHealthStatus
    success_rate: float
    average_latency_ms: float
    error_rate: float
    last_check: datetime
    consecutive_failures: int
    last_error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "success_rate": self.success_rate,
            "average_latency_ms": self.average_latency_ms,
            "error_rate": self.error_rate,
            "last_check": self.last_check.isoformat(),
            "consecutive_failures": self.consecutive_failures,
            "last_error": self.last_error
        }


class RetryStrategy:
    """Advanced retry strategy with exponential backoff"""
    
    def __init__(self, max_retries: int = 5, base_delay: float = 1.0,
                 max_delay: float = 300.0, exponential_base: float = 2.0,
                 jitter: bool = True):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def get_delay(self, retry_count: int) -> float:
        """Calculate delay for given retry count"""
        # Exponential backoff
        delay = min(self.base_delay * (self.exponential_base ** retry_count), self.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            import random
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay
    
    def should_retry(self, retry_count: int, error: Exception) -> bool:
        """Determine if we should retry based on error type"""
        if retry_count >= self.max_retries:
            return False
        
        # Retry on specific errors
        if isinstance(error, (NetworkError, httpx.TimeoutException)):
            return True
        
        if isinstance(error, ApiError):
            # Retry on server errors (5xx)
            if hasattr(error, 'status_code') and 500 <= error.status_code < 600:
                return True
            # Don't retry on client errors (4xx)
            if hasattr(error, 'status_code') and 400 <= error.status_code < 500:
                return False
        
        if isinstance(error, RateLimitError):
            # Always retry rate limit errors
            return True
        
        # Don't retry on other errors
        return False


class EnhancedOpenRouterClient:
    """Enhanced async client for OpenRouter API with database integration"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 db_manager: Optional[ValidatedDatabaseManager] = None,
                 rate_limiter: Optional[CompositeLimiter] = None,
                 circuit_breaker: Optional[MultiServiceCircuitBreaker] = None,
                 cache_service: Optional[CacheService] = None,
                 retry_strategy: Optional[RetryStrategy] = None):
        """Initialize the enhanced OpenRouter client
        
        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            base_url: Base URL for API (defaults to official endpoint)
            db_manager: Database manager for storing outputs
            rate_limiter: Optional rate limiter instance
            circuit_breaker: Optional circuit breaker instance
            cache_service: Optional cache service instance
            retry_strategy: Optional retry strategy
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
        self.timeout = httpx.Timeout(60.0, connect=10.0)  # Increased timeout
        
        # Database and parsing
        self.db_manager = db_manager
        self.nuance_parser = NuanceOutputParser()
        self.flashcard_parser = FlashcardOutputParser()
        self.output_archiver = OutputArchiver(db_manager) if db_manager else None
        
        # Rate limiting, circuit breaker, and caching
        self.rate_limiter = rate_limiter or CompositeLimiter()
        self.circuit_breaker = circuit_breaker or MultiServiceCircuitBreaker()
        self.cache_service = cache_service or CacheService()
        self.retry_strategy = retry_strategy or RetryStrategy()
        
        # Rate limit tracking
        self.rate_limit_info: Optional[RateLimitInfo] = None
        
        # Health monitoring
        self._health_metrics = ApiHealthMetrics(
            status=ApiHealthStatus.UNKNOWN,
            success_rate=0.0,
            average_latency_ms=0.0,
            error_rate=0.0,
            last_check=datetime.now(),
            consecutive_failures=0
        )
        self._request_history: List[Dict[str, Any]] = []
        self._max_history_size = 100
        
        # Request statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "cache_hits": 0,
            "retries": 0,
            "total_latency_ms": 0.0
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
                max_keepalive_connections=20,  # Increased connections
                max_connections=50,            # Maximum concurrent connections
                keepalive_expiry=60.0         # Keep connections alive longer
            )
            
            self.client = AsyncClient(
                timeout=self.timeout,
                limits=limits,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "korean-flashcard-pipeline/1.0.0"
                },
                http2=True  # Enable HTTP/2 for better performance
            )
    
    async def close(self):
        """Close the HTTP client"""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    async def process_stage1(self, vocabulary_item: VocabularyItem,
                           task_id: Optional[str] = None) -> Tuple[Stage1Response, ApiUsage]:
        """Process Stage 1: Semantic Analysis with enhanced features
        
        Args:
            vocabulary_item: Input vocabulary item
            task_id: Optional task ID for tracking
            
        Returns:
            Tuple of (Stage1Response, ApiUsage)
        """
        start_time = time.time()
        
        # Check cache first
        cached_result = await self.cache_service.get_stage1(vocabulary_item)
        if cached_result:
            logger.info(f"Stage 1 cache hit: {vocabulary_item.term}")
            self.stats["cache_hits"] += 1
            # Unpack the result tuple
            stage1_response, tokens_saved = cached_result
            # Create a mock usage object for cached results
            usage = ApiUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
            
            # Still record the cached result in database if task_id provided
            if task_id and self.output_archiver:
                self.output_archiver.archive_stage1_output(
                    task_id, vocabulary_item.position,
                    f"CACHED: {stage1_response.model_dump_json()}",
                    stage1_response, 0, 0
                )
            
            return stage1_response, usage
        
        # Create request
        request = Stage1Request.from_vocabulary_item(vocabulary_item)
        
        # Make API call with retry
        logger.info(f"Stage 1 processing: {vocabulary_item.term}")
        response = await self._make_request_with_retry(request.model_dump())
        
        # Parse response
        try:
            api_response = ApiResponse(**response)
            content = api_response.get_content()
        except Exception as e:
            logger.error(f"Failed to parse API response structure: {e}")
            logger.error(f"Raw response: {response}")
            raise ValidationError(f"Invalid API response structure: {e}", "api_response", str(response))
        
        # Parse and validate Stage 1 response
        try:
            stage1_response = self.nuance_parser.parse(content)
        except Exception as e:
            logger.error(f"Failed to parse Stage 1 response: {e}")
            raise ValidationError(f"Invalid Stage 1 response format: {e}", "response", content)
        
        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Update statistics
        self._update_stats(api_response.usage, processing_time_ms)
        
        # Archive output if database available
        if task_id and self.output_archiver:
            self.output_archiver.archive_stage1_output(
                task_id, vocabulary_item.position,
                content, stage1_response,
                api_response.usage.total_tokens,
                processing_time_ms
            )
        
        # Cache the result
        await self.cache_service.save_stage1(vocabulary_item, stage1_response, api_response.usage.total_tokens)
        
        return stage1_response, api_response.usage
    
    async def process_stage2(self, vocabulary_item: VocabularyItem, 
                           stage1_result: Stage1Response,
                           task_id: Optional[str] = None) -> Tuple[Stage2Response, ApiUsage]:
        """Process Stage 2: Flashcard Generation with enhanced features
        
        Args:
            vocabulary_item: Original vocabulary item
            stage1_result: Result from Stage 1 processing
            task_id: Optional task ID for tracking
            
        Returns:
            Tuple of (Stage2Response, ApiUsage)
        """
        start_time = time.time()
        
        # Check cache first
        cached_result = await self.cache_service.get_stage2(vocabulary_item, stage1_result)
        if cached_result:
            logger.info(f"Stage 2 cache hit: {vocabulary_item.term}")
            self.stats["cache_hits"] += 1
            # Unpack the result tuple
            stage2_response, tokens_saved = cached_result
            # Create a mock usage object for cached results
            usage = ApiUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
            
            # Still record the cached result in database if task_id provided
            if task_id and self.output_archiver:
                self.output_archiver.archive_stage2_output(
                    task_id, vocabulary_item.position,
                    f"CACHED: {stage2_response.model_dump_json()}",
                    stage2_response, 0, 0
                )
            
            return stage2_response, usage
        
        # Create request
        request = Stage2Request.from_stage1_result(vocabulary_item, stage1_result)
        
        # Make API call with retry
        logger.info(f"Stage 2 processing: {vocabulary_item.term}")
        response = await self._make_request_with_retry(request.model_dump())
        
        # Parse response
        api_response = ApiResponse(**response)
        content = api_response.get_content()
        
        # Parse and validate Stage 2 response
        try:
            stage2_response = self.flashcard_parser.parse(content)
        except Exception as e:
            logger.error(f"Failed to parse Stage 2 response: {e}")
            raise ValidationError(f"Invalid Stage 2 response format: {e}", "response", content)
        
        # Validate TSV format
        if not self.flashcard_parser.validate_tsv_format(stage2_response):
            raise ValidationError("Stage 2 response failed TSV validation", "response", content)
        
        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Update statistics
        self._update_stats(api_response.usage, processing_time_ms)
        
        # Archive output if database available
        if task_id and self.output_archiver:
            self.output_archiver.archive_stage2_output(
                task_id, vocabulary_item.position,
                content, stage2_response,
                api_response.usage.total_tokens,
                processing_time_ms
            )
        
        # Cache the result
        await self.cache_service.save_stage2(vocabulary_item, stage1_result, stage2_response, api_response.usage.total_tokens)
        
        return stage2_response, api_response.usage
    
    async def _make_request_with_retry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request with advanced retry logic
        
        Args:
            payload: Request payload
            
        Returns:
            Response JSON data
        """
        retry_count = 0
        last_error = None
        
        while retry_count <= self.retry_strategy.max_retries:
            try:
                # Make the request
                response = await self._make_request(payload, retry_count)
                
                # Reset consecutive failures on success
                self._health_metrics.consecutive_failures = 0
                
                return response
                
            except Exception as e:
                last_error = e
                self._health_metrics.consecutive_failures += 1
                self._health_metrics.last_error = str(e)
                
                # Check if we should retry
                if self.retry_strategy.should_retry(retry_count, e):
                    delay = self.retry_strategy.get_delay(retry_count)
                    
                    # Special handling for rate limit errors
                    if isinstance(e, RateLimitError) and hasattr(e, 'retry_after'):
                        delay = max(delay, e.retry_after)
                    
                    logger.warning(f"Request failed (attempt {retry_count + 1}/{self.retry_strategy.max_retries + 1}), "
                                 f"retrying in {delay:.1f}s: {e}")
                    
                    self.stats["retries"] += 1
                    retry_count += 1
                    
                    await asyncio.sleep(delay)
                else:
                    # Don't retry this error
                    raise
        
        # All retries exhausted
        raise last_error
    
    async def _make_request(self, payload: Dict[str, Any], retry_count: int = 0) -> Dict[str, Any]:
        """Make HTTP request (internal method used by retry logic)
        
        Args:
            payload: Request payload
            retry_count: Current retry attempt
            
        Returns:
            Response JSON data
        """
        await self._ensure_client()
        
        # Determine which stage this is for rate limiting
        stage = 1 if "@preset/nuance-creator" in str(payload.get("model", "")) else 2
        
        # Record request start
        request_start = time.time()
        request_record = {
            "timestamp": datetime.now(),
            "stage": stage,
            "retry_count": retry_count,
            "success": False,
            "latency_ms": 0,
            "error": None
        }
        
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
            
            # Calculate latency
            latency_ms = (time.time() - request_start) * 1000
            request_record["latency_ms"] = latency_ms
            
            # Update rate limit info
            if response.headers:
                self.rate_limit_info = RateLimitInfo.from_headers(dict(response.headers))
            
            # Handle different status codes
            if response.status_code == 200:
                self.stats["successful_requests"] += 1
                request_record["success"] = True
                
                # Notify rate limiter of success
                await self.rate_limiter.on_success()
                
                data = response.json()
                logger.debug(f"API Response: {data}")
                
                # Update request history
                self._update_request_history(request_record)
                
                return data
            
            elif response.status_code == 429:
                # Rate limit exceeded
                self.stats["failed_requests"] += 1
                retry_after = int(response.headers.get('Retry-After', 60))
                
                # Notify rate limiter of rate limit hit
                await self.rate_limiter.on_rate_limit(retry_after)
                
                request_record["error"] = "rate_limit"
                self._update_request_history(request_record)
                
                raise RateLimitError(
                    "Rate limit exceeded",
                    retry_after=retry_after,
                    reset_at=int(response.headers.get('X-RateLimit-Reset', 0))
                )
            
            elif response.status_code == 401:
                self.stats["failed_requests"] += 1
                request_record["error"] = "authentication"
                self._update_request_history(request_record)
                raise AuthenticationError("Invalid API key")
            
            else:
                # Other errors
                self.stats["failed_requests"] += 1
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                error_message = error_data.get('error', {}).get('message', response.text)
                
                request_record["error"] = f"http_{response.status_code}"
                self._update_request_history(request_record)
                
                raise ApiError(
                    f"API error: {error_message}",
                    status_code=response.status_code,
                    response_body=response.text
                )
        
        except httpx.NetworkError as e:
            self.stats["failed_requests"] += 1
            request_record["error"] = "network"
            request_record["latency_ms"] = (time.time() - request_start) * 1000
            self._update_request_history(request_record)
            raise NetworkError(f"Network error: {str(e)}", original_error=e)
        
        except httpx.TimeoutException as e:
            self.stats["failed_requests"] += 1
            request_record["error"] = "timeout"
            request_record["latency_ms"] = (time.time() - request_start) * 1000
            self._update_request_history(request_record)
            raise NetworkError(f"Request timeout: {str(e)}", original_error=e)
        
        except CircuitBreakerError as e:
            # Circuit is open, don't retry
            self.stats["failed_requests"] += 1
            request_record["error"] = "circuit_breaker"
            self._update_request_history(request_record)
            logger.warning(f"Circuit breaker is open: {e}")
            raise
    
    def _update_stats(self, usage: ApiUsage, latency_ms: float):
        """Update internal statistics"""
        self.stats["total_tokens"] += usage.total_tokens
        self.stats["total_cost"] += usage.estimated_cost
        self.stats["total_latency_ms"] += latency_ms
    
    def _update_request_history(self, request_record: Dict[str, Any]):
        """Update request history for health monitoring"""
        self._request_history.append(request_record)
        
        # Keep only recent history
        if len(self._request_history) > self._max_history_size:
            self._request_history = self._request_history[-self._max_history_size:]
        
        # Update health metrics
        self._update_health_metrics()
    
    def _update_health_metrics(self):
        """Update API health metrics based on recent history"""
        if not self._request_history:
            return
        
        # Calculate metrics over recent history
        recent_window = datetime.now() - timedelta(minutes=5)
        recent_requests = [r for r in self._request_history if r["timestamp"] > recent_window]
        
        if not recent_requests:
            return
        
        # Calculate success rate
        successful = sum(1 for r in recent_requests if r["success"])
        total = len(recent_requests)
        success_rate = successful / total if total > 0 else 0.0
        
        # Calculate average latency
        latencies = [r["latency_ms"] for r in recent_requests if r["latency_ms"] > 0]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        
        # Calculate error rate
        errors = sum(1 for r in recent_requests if not r["success"])
        error_rate = errors / total if total > 0 else 0.0
        
        # Determine health status
        if success_rate >= 0.95 and avg_latency < 2000:
            status = ApiHealthStatus.HEALTHY
        elif success_rate >= 0.80 or avg_latency < 5000:
            status = ApiHealthStatus.DEGRADED
        else:
            status = ApiHealthStatus.UNHEALTHY
        
        # Update metrics
        self._health_metrics = ApiHealthMetrics(
            status=status,
            success_rate=success_rate,
            average_latency_ms=avg_latency,
            error_rate=error_rate,
            last_check=datetime.now(),
            consecutive_failures=self._health_metrics.consecutive_failures,
            last_error=self._health_metrics.last_error
        )
    
    async def get_health_status(self) -> ApiHealthMetrics:
        """Get current API health status
        
        Returns:
            Current health metrics
        """
        # If no recent check, perform a lightweight health check
        if (datetime.now() - self._health_metrics.last_check).seconds > 300:  # 5 minutes
            await self.test_connection()
        
        return self._health_metrics
    
    def get_stats(self) -> Dict[str, Any]:
        """Get enhanced statistics"""
        total_requests = self.stats["total_requests"]
        successful_requests = self.stats["successful_requests"]
        
        return {
            **self.stats,
            "success_rate": (
                successful_requests / total_requests 
                if total_requests > 0 else 0.0
            ),
            "average_tokens_per_request": (
                self.stats["total_tokens"] / successful_requests
                if successful_requests > 0 else 0.0
            ),
            "average_latency_ms": (
                self.stats["total_latency_ms"] / total_requests
                if total_requests > 0 else 0.0
            ),
            "cache_hit_rate": (
                self.stats["cache_hits"] / (total_requests + self.stats["cache_hits"])
                if (total_requests + self.stats["cache_hits"]) > 0 else 0.0
            ),
            "retry_rate": (
                self.stats["retries"] / total_requests
                if total_requests > 0 else 0.0
            ),
            "health_status": self._health_metrics.to_dict()
        }
    
    async def test_connection(self) -> bool:
        """Test the API connection
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Simple test to check if API is reachable
            await self._ensure_client()
            start_time = time.time()
            
            response = await self.client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10.0
            )
            response.raise_for_status()
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Update health metrics
            self._update_request_history({
                "timestamp": datetime.now(),
                "stage": 0,  # Health check
                "retry_count": 0,
                "success": True,
                "latency_ms": latency_ms,
                "error": None
            })
            
            logger.info(f"API connection test successful (latency: {latency_ms:.1f}ms)")
            return True
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            
            # Update health metrics
            self._update_request_history({
                "timestamp": datetime.now(),
                "stage": 0,  # Health check
                "retry_count": 0,
                "success": False,
                "latency_ms": 0,
                "error": str(e)
            })
            
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        return self.cache_service.get_stats()
    
    async def get_quota_usage(self) -> Dict[str, Any]:
        """Get current API quota usage and limits
        
        Returns:
            Dictionary with quota information
        """
        if not self.rate_limit_info:
            await self.check_rate_limit()
        
        stats = self.get_stats()
        
        return {
            "tokens": {
                "used": stats["total_tokens"],
                "cost": stats["total_cost"]
            },
            "requests": {
                "total": stats["total_requests"],
                "successful": stats["successful_requests"],
                "failed": stats["failed_requests"]
            },
            "rate_limits": {
                "limit": self.rate_limit_info.limit if self.rate_limit_info else None,
                "remaining": self.rate_limit_info.remaining if self.rate_limit_info else None,
                "reset_at": self.rate_limit_info.reset_at.isoformat() if self.rate_limit_info else None
            },
            "health": self._health_metrics.to_dict()
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