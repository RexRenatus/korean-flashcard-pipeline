"""Thread-safe distributed rate limiter for concurrent requests"""

import asyncio
import time
from typing import Optional, Dict, Any
import logging
from dataclasses import dataclass

from ..exceptions import RateLimitError

logger = logging.getLogger(__name__)


@dataclass
class RateLimitStats:
    """Statistics for rate limiter"""
    total_acquisitions: int = 0
    total_releases: int = 0
    total_timeouts: int = 0
    total_wait_time_ms: float = 0.0
    current_available: int = 0
    max_concurrent: int = 0


class DistributedRateLimiter:
    """Thread-safe rate limiter for concurrent requests
    
    Uses a token bucket algorithm with async semaphore for thread safety.
    Designed to handle high concurrency while respecting API rate limits.
    """
    
    def __init__(self, requests_per_minute: int = 600, buffer_factor: float = 0.8):
        """Initialize rate limiter
        
        Args:
            requests_per_minute: API rate limit
            buffer_factor: Safety buffer (0.8 = use 80% of limit)
        """
        # Apply safety buffer
        self.safe_limit = int(requests_per_minute * buffer_factor)
        self.requests_per_minute = requests_per_minute
        
        # Semaphore controls concurrent access
        self.semaphore = asyncio.Semaphore(self.safe_limit)
        
        # Token bucket for rate limiting
        self.tokens = asyncio.Queue(maxsize=self.safe_limit)
        self.refill_rate = self.safe_limit / 60.0  # tokens per second
        
        # Statistics
        self.stats = RateLimitStats(
            current_available=self.safe_limit,
            max_concurrent=self.safe_limit
        )
        self._lock = asyncio.Lock()
        
        # Start refill task
        self._refill_task = None
        self._running = False
        
        logger.info(f"Initialized rate limiter: {self.safe_limit} requests/minute "
                   f"(buffer: {buffer_factor}, original: {requests_per_minute})")
    
    async def start(self):
        """Start the rate limiter"""
        if self._running:
            return
            
        self._running = True
        
        # Fill initial tokens
        for _ in range(self.safe_limit):
            try:
                self.tokens.put_nowait(1)
            except asyncio.QueueFull:
                break
        
        # Start refill task
        self._refill_task = asyncio.create_task(self._refill_tokens())
        logger.info("Rate limiter started")
    
    async def stop(self):
        """Stop the rate limiter"""
        self._running = False
        if self._refill_task:
            self._refill_task.cancel()
            try:
                await self._refill_task
            except asyncio.CancelledError:
                pass
        logger.info("Rate limiter stopped")
    
    async def acquire(self, timeout: float = 30.0) -> float:
        """Acquire a token, blocking if necessary
        
        Args:
            timeout: Maximum time to wait for a token
            
        Returns:
            Wait time in seconds
            
        Raises:
            RateLimitError: If timeout exceeded
        """
        start_time = time.time()
        
        try:
            # First acquire semaphore (controls concurrency)
            await asyncio.wait_for(self.semaphore.acquire(), timeout)
            
            # Then get a token (controls rate)
            remaining_timeout = timeout - (time.time() - start_time)
            if remaining_timeout <= 0:
                self.semaphore.release()
                raise asyncio.TimeoutError()
            
            await asyncio.wait_for(self.tokens.get(), remaining_timeout)
            
            wait_time = time.time() - start_time
            
            # Update stats
            async with self._lock:
                self.stats.total_acquisitions += 1
                self.stats.total_wait_time_ms += wait_time * 1000
                self.stats.current_available = self.tokens.qsize()
            
            logger.debug(f"Token acquired after {wait_time:.2f}s wait")
            return wait_time
            
        except asyncio.TimeoutError:
            async with self._lock:
                self.stats.total_timeouts += 1
            
            raise RateLimitError(
                f"Rate limit token acquisition timeout ({timeout}s)",
                retry_after=60.0 / self.refill_rate
            )
    
    def release(self):
        """Release a token back to the pool"""
        self.semaphore.release()
        
        # Update stats
        asyncio.create_task(self._update_release_stats())
    
    async def _update_release_stats(self):
        """Update release statistics"""
        async with self._lock:
            self.stats.total_releases += 1
            self.stats.current_available = self.tokens.qsize()
    
    async def _refill_tokens(self):
        """Continuously refill tokens at the specified rate"""
        logger.info(f"Token refill started: {self.refill_rate:.2f} tokens/second")
        
        while self._running:
            try:
                # Calculate sleep time for one token
                sleep_time = 1.0 / self.refill_rate
                await asyncio.sleep(sleep_time)
                
                # Try to add a token
                try:
                    self.tokens.put_nowait(1)
                    logger.debug(f"Token refilled. Queue size: {self.tokens.qsize()}")
                except asyncio.QueueFull:
                    # Queue is full, no need to add more tokens
                    logger.debug("Token bucket full, skipping refill")
                    
            except asyncio.CancelledError:
                logger.info("Token refill task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in token refill: {e}")
                await asyncio.sleep(1.0)  # Prevent tight loop on error
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        return {
            "total_acquisitions": self.stats.total_acquisitions,
            "total_releases": self.stats.total_releases,
            "total_timeouts": self.stats.total_timeouts,
            "average_wait_ms": (
                self.stats.total_wait_time_ms / self.stats.total_acquisitions
                if self.stats.total_acquisitions > 0 else 0
            ),
            "current_available": self.stats.current_available,
            "max_concurrent": self.stats.max_concurrent,
            "requests_per_minute": self.requests_per_minute,
            "safe_limit": self.safe_limit
        }
    
    async def wait_if_needed(self, requests_made: int, time_window: float = 60.0) -> float:
        """Wait if we're approaching rate limit
        
        Args:
            requests_made: Number of requests made in the time window
            time_window: Time window in seconds
            
        Returns:
            Time waited in seconds
        """
        if requests_made >= self.safe_limit:
            # Calculate how long to wait
            wait_time = time_window - (time.time() % time_window)
            logger.warning(f"Approaching rate limit. Waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            return wait_time
        return 0.0
    
    def __str__(self) -> str:
        """String representation"""
        stats = self.get_stats()
        return (f"DistributedRateLimiter("
                f"limit={stats['safe_limit']}/min, "
                f"available={stats['current_available']}, "
                f"acquisitions={stats['total_acquisitions']})")