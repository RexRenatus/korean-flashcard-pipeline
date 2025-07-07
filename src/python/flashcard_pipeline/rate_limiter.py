"""Rate limiting implementation for API calls"""

import asyncio
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from .exceptions import RateLimitError


logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter with sliding window"""
    
    def __init__(self, 
                 requests_per_minute: int = 60,
                 requests_per_hour: int = 3000,
                 burst_size: int = 10):
        """Initialize rate limiter
        
        Args:
            requests_per_minute: Max requests per minute
            requests_per_hour: Max requests per hour
            burst_size: Max burst requests allowed
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size
        
        # Token bucket for minute-level limiting
        self.minute_tokens = float(burst_size)
        self.minute_rate = requests_per_minute / 60.0  # tokens per second
        self.minute_last_update = time.monotonic()
        
        # Sliding window for hour-level limiting
        self.hour_window: list[float] = []
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> None:
        """Acquire permission to make a request
        
        Args:
            tokens: Number of tokens to acquire (default 1)
            
        Raises:
            RateLimitError: If rate limit would be exceeded
        """
        async with self._lock:
            # Update token bucket
            now = time.monotonic()
            elapsed = now - self.minute_last_update
            self.minute_tokens = min(
                self.burst_size,
                self.minute_tokens + elapsed * self.minute_rate
            )
            self.minute_last_update = now
            
            # Clean old entries from hour window
            hour_ago = time.time() - 3600
            self.hour_window = [t for t in self.hour_window if t > hour_ago]
            
            # Check minute-level limit
            if self.minute_tokens < tokens:
                wait_time = (tokens - self.minute_tokens) / self.minute_rate
                raise RateLimitError(
                    f"Rate limit exceeded: need to wait {wait_time:.1f}s",
                    retry_after=int(wait_time + 1)
                )
            
            # Check hour-level limit
            if len(self.hour_window) + tokens > self.requests_per_hour:
                oldest_request = self.hour_window[0] if self.hour_window else time.time()
                wait_until = oldest_request + 3600
                wait_time = wait_until - time.time()
                raise RateLimitError(
                    f"Hourly rate limit exceeded: need to wait {wait_time:.1f}s",
                    retry_after=int(wait_time + 1)
                )
            
            # Consume tokens
            self.minute_tokens -= tokens
            current_time = time.time()
            for _ in range(tokens):
                self.hour_window.append(current_time)
            
            logger.debug(f"Rate limiter: {self.minute_tokens:.1f} tokens remaining")
    
    async def wait_if_needed(self, tokens: int = 1) -> None:
        """Wait if necessary before acquiring tokens
        
        Args:
            tokens: Number of tokens to acquire
        """
        while True:
            try:
                await self.acquire(tokens)
                break
            except RateLimitError as e:
                wait_time = e.retry_after or 1
                logger.info(f"Rate limit reached, waiting {wait_time}s")
                await asyncio.sleep(wait_time)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current rate limiter status"""
        hour_ago = time.time() - 3600
        recent_requests = len([t for t in self.hour_window if t > hour_ago])
        
        return {
            "minute_tokens_available": self.minute_tokens,
            "minute_limit": self.requests_per_minute,
            "hour_requests_made": recent_requests,
            "hour_limit": self.requests_per_hour,
            "burst_size": self.burst_size
        }


class AdaptiveRateLimiter(RateLimiter):
    """Rate limiter that adapts based on API responses"""
    
    def __init__(self, 
                 initial_requests_per_minute: int = 60,
                 initial_requests_per_hour: int = 3000,
                 burst_size: int = 10):
        super().__init__(initial_requests_per_minute, initial_requests_per_hour, burst_size)
        
        # Adaptive parameters
        self.min_requests_per_minute = 10
        self.max_requests_per_minute = 120
        self.adjustment_factor = 0.9  # Reduce by 10% on rate limit
        self.recovery_factor = 1.05   # Increase by 5% on success
        
        # Success tracking
        self.consecutive_successes = 0
        self.consecutive_failures = 0
    
    async def on_success(self):
        """Called when a request succeeds"""
        async with self._lock:
            self.consecutive_successes += 1
            self.consecutive_failures = 0
            
            # Gradually increase rate after 10 consecutive successes
            if self.consecutive_successes >= 10:
                new_rate = min(
                    self.max_requests_per_minute,
                    self.requests_per_minute * self.recovery_factor
                )
                if new_rate > self.requests_per_minute:
                    logger.info(f"Increasing rate limit: {self.requests_per_minute} → {new_rate:.1f}")
                    self.requests_per_minute = new_rate
                    self.minute_rate = new_rate / 60.0
                    self.consecutive_successes = 0
    
    async def on_rate_limit(self, retry_after: Optional[int] = None):
        """Called when a rate limit is hit"""
        async with self._lock:
            self.consecutive_failures += 1
            self.consecutive_successes = 0
            
            # Reduce rate immediately
            new_rate = max(
                self.min_requests_per_minute,
                self.requests_per_minute * self.adjustment_factor
            )
            if new_rate < self.requests_per_minute:
                logger.warning(f"Reducing rate limit: {self.requests_per_minute} → {new_rate:.1f}")
                self.requests_per_minute = new_rate
                self.minute_rate = new_rate / 60.0
            
            # If we have retry_after info, adjust tokens accordingly
            if retry_after:
                self.minute_tokens = -retry_after * self.minute_rate
    
    def get_status(self) -> Dict[str, Any]:
        """Get current adaptive rate limiter status"""
        status = super().get_status()
        status.update({
            "adaptive_enabled": True,
            "consecutive_successes": self.consecutive_successes,
            "consecutive_failures": self.consecutive_failures,
            "current_requests_per_minute": self.requests_per_minute
        })
        return status


class CompositeLimiter:
    """Combines multiple rate limiters with different strategies"""
    
    def __init__(self):
        """Initialize composite limiter"""
        # Primary limiter based on API limits
        self.api_limiter = AdaptiveRateLimiter(
            initial_requests_per_minute=60,
            initial_requests_per_hour=3000,
            burst_size=10
        )
        
        # Cost-based limiter (tokens per hour)
        self.cost_limiter = RateLimiter(
            requests_per_minute=100,  # Effectively unlimited per minute
            requests_per_hour=20,     # But limited per hour for cost
            burst_size=5
        )
        
        # Stage-specific limiters
        self.stage1_limiter = RateLimiter(
            requests_per_minute=30,
            requests_per_hour=1500,
            burst_size=5
        )
        
        self.stage2_limiter = RateLimiter(
            requests_per_minute=30,
            requests_per_hour=1500,
            burst_size=5
        )
    
    async def acquire_for_stage(self, stage: int, estimated_tokens: int = 350) -> None:
        """Acquire permission for a specific stage
        
        Args:
            stage: Processing stage (1 or 2)
            estimated_tokens: Estimated tokens for request
        """
        # Check all applicable limiters
        await self.api_limiter.acquire()
        
        # Cost-based limiting (1 token per ~350 API tokens)
        if estimated_tokens > 1000:
            await self.cost_limiter.acquire()
        
        # Stage-specific limiting
        if stage == 1:
            await self.stage1_limiter.acquire()
        else:
            await self.stage2_limiter.acquire()
    
    async def on_success(self):
        """Notify limiters of successful request"""
        await self.api_limiter.on_success()
    
    async def on_rate_limit(self, retry_after: Optional[int] = None):
        """Notify limiters of rate limit hit"""
        await self.api_limiter.on_rate_limit(retry_after)
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all limiters"""
        return {
            "api_limiter": self.api_limiter.get_status(),
            "cost_limiter": self.cost_limiter.get_status(),
            "stage1_limiter": self.stage1_limiter.get_status(),
            "stage2_limiter": self.stage2_limiter.get_status()
        }