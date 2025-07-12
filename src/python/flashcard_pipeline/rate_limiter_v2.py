"""
Sharded rate limiter for improved performance at scale.

This module implements a distributed rate limiting system with sharding
to reduce contention and improve throughput at scale.
"""

import asyncio
import hashlib
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple, Callable
from datetime import datetime, timedelta
import logging
import json

from .rate_limiter import RateLimiter
from .exceptions import RateLimitError

logger = logging.getLogger(__name__)


@dataclass
class RateLimitResult:
    """Result of a rate limit check"""
    allowed: bool
    retry_after: Optional[float] = None
    tokens_remaining: Optional[float] = None
    shard_id: Optional[int] = None
    reason: Optional[str] = None


@dataclass
class TokenReservation:
    """Represents a reserved token allocation"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    key: str = ""
    count: int = 1
    reserved_at: float = field(default_factory=time.time)
    execute_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 60.0)
    shard_id: Optional[int] = None
    
    def is_expired(self) -> bool:
        """Check if reservation has expired"""
        return time.time() > self.expires_at
    
    def is_ready(self) -> bool:
        """Check if reservation is ready to execute"""
        return time.time() >= self.execute_at
    
    def delay_execution(self, seconds: float):
        """Delay the execution time"""
        self.execute_at = max(self.execute_at, time.time()) + seconds


class ShardedRateLimiter:
    """Rate limiter with sharding for reduced contention"""
    
    def __init__(
        self,
        rate: int,
        period: float = 60.0,
        shards: int = 1,
        algorithm: str = "token_bucket",
        burst_size: Optional[int] = None
    ):
        """
        Initialize sharded rate limiter.
        
        Args:
            rate: Requests allowed per period
            period: Time period in seconds (default 60)
            shards: Number of shards (automatically adjusted if needed)
            algorithm: Rate limiting algorithm (token_bucket, fixed_window, sliding_window)
            burst_size: Burst capacity (defaults to rate)
        """
        if shards < 1:
            raise ValueError("Shards must be >= 1")
        if rate <= 0:
            raise ValueError("Rate must be positive")
        
        self.total_rate = rate
        self.period = period
        self.algorithm = algorithm
        self.burst_size = burst_size or rate
        
        # Calculate optimal shard count
        self.shards = self._calculate_optimal_shards(rate, shards)
        
        # Distribute rate across shards
        base_rate = rate // self.shards
        extra_tokens = rate % self.shards
        
        # Create sharded limiters
        self.limiters: List[RateLimiter] = []
        for i in range(self.shards):
            shard_rate = base_rate + (1 if i < extra_tokens else 0)
            shard_burst = max(1, self.burst_size // self.shards)
            
            # Convert to requests per minute for RateLimiter compatibility
            if period == 60.0:
                requests_per_minute = shard_rate
            else:
                requests_per_minute = int(shard_rate * 60 / period)
            
            limiter = RateLimiter(
                requests_per_minute=requests_per_minute,
                requests_per_hour=requests_per_minute * 60,
                burst_size=shard_burst
            )
            self.limiters.append(limiter)
        
        # Reservation tracking
        self._reservations: Dict[str, TokenReservation] = {}
        self._reservation_lock = asyncio.Lock()
        
        # Statistics
        self._stats = {
            "total_requests": 0,
            "allowed_requests": 0,
            "denied_requests": 0,
            "reservations_created": 0,
            "reservations_expired": 0,
            "shard_distribution": [0] * self.shards
        }
        
        logger.info(
            f"Initialized ShardedRateLimiter: {self.shards} shards, "
            f"{rate} requests per {period}s, algorithm={algorithm}"
        )
    
    def _calculate_optimal_shards(self, rate: int, requested_shards: int) -> int:
        """Calculate optimal number of shards based on rate"""
        # Rule: max_qps / 2 from the research, with minimum capacity per shard
        if rate < 20:
            return 1  # Low rate, no sharding needed
        
        # Aim for at least 10 capacity per shard
        max_shards = max(1, rate // 10)
        
        # Use power of 2 for efficient hashing
        optimal = 1
        while optimal * 2 <= min(requested_shards, max_shards):
            optimal *= 2
        
        return optimal
    
    def _get_shards(self, key: str) -> Tuple[int, int]:
        """Get primary and secondary shard indices using power-of-two selection"""
        # Use MD5 for consistent hashing
        hash1 = int(hashlib.md5(key.encode()).hexdigest(), 16)
        hash2 = int(hashlib.md5(f"{key}_alt".encode()).hexdigest(), 16)
        
        primary = hash1 % self.shards
        secondary = hash2 % self.shards
        
        # Ensure secondary is different if possible
        if secondary == primary and self.shards > 1:
            secondary = (primary + 1) % self.shards
        
        return primary, secondary
    
    async def acquire(self, key: str = "default", count: int = 1) -> RateLimitResult:
        """
        Try to acquire tokens with power-of-two shard selection.
        
        Args:
            key: Key for sharding (e.g., user ID, API endpoint)
            count: Number of tokens to acquire
            
        Returns:
            RateLimitResult indicating success or retry information
        """
        self._stats["total_requests"] += 1
        
        shard1, shard2 = self._get_shards(key)
        
        # Try primary shard
        try:
            await self.limiters[shard1].acquire(count)
            self._stats["allowed_requests"] += 1
            self._stats["shard_distribution"][shard1] += 1
            return RateLimitResult(
                allowed=True,
                tokens_remaining=self.limiters[shard1].tokens,
                shard_id=shard1
            )
        except RateLimitError as e:
            primary_retry_after = e.retry_after or 1.0
        
        # Try secondary shard
        if shard2 != shard1:
            try:
                await self.limiters[shard2].acquire(count)
                self._stats["allowed_requests"] += 1
                self._stats["shard_distribution"][shard2] += 1
                return RateLimitResult(
                    allowed=True,
                    tokens_remaining=self.limiters[shard2].tokens,
                    shard_id=shard2
                )
            except RateLimitError as e:
                secondary_retry_after = e.retry_after or 1.0
        else:
            secondary_retry_after = primary_retry_after
        
        # Neither shard has capacity
        self._stats["denied_requests"] += 1
        retry_after = min(primary_retry_after, secondary_retry_after)
        
        return RateLimitResult(
            allowed=False,
            retry_after=retry_after,
            reason=f"Rate limit exceeded on all shards (retry after {retry_after:.1f}s)"
        )
    
    async def try_acquire(self, key: str = "default", count: int = 1) -> RateLimitResult:
        """Non-blocking version of acquire"""
        result = await self.acquire(key, count)
        if not result.allowed:
            # Don't raise, just return the result
            return result
        return result
    
    async def reserve(
        self,
        key: str = "default",
        count: int = 1,
        max_wait: float = 300.0
    ) -> TokenReservation:
        """
        Reserve tokens for future use.
        
        Args:
            key: Key for sharding
            count: Number of tokens to reserve
            max_wait: Maximum time to wait for tokens (seconds)
            
        Returns:
            TokenReservation object
            
        Raises:
            ValueError: If wait time exceeds max_wait
        """
        async with self._reservation_lock:
            # Clean expired reservations
            await self._cleanup_expired_reservations()
            
            # Check current availability
            result = await self.try_acquire(key, count)
            
            now = time.time()
            if result.allowed:
                execute_at = now
                shard_id = result.shard_id
            else:
                execute_at = now + (result.retry_after or 1.0)
                shard_id = None
                
                if execute_at - now > max_wait:
                    raise ValueError(
                        f"Wait time {execute_at - now:.1f}s exceeds max_wait {max_wait}s"
                    )
            
            # Create reservation
            reservation = TokenReservation(
                key=key,
                count=count,
                reserved_at=now,
                execute_at=execute_at,
                expires_at=execute_at + 60.0,  # 1 minute expiration after ready
                shard_id=shard_id
            )
            
            self._reservations[reservation.id] = reservation
            self._stats["reservations_created"] += 1
            
            logger.debug(
                f"Created reservation {reservation.id}: "
                f"{count} tokens for key '{key}', "
                f"executable at {datetime.fromtimestamp(execute_at).isoformat()}"
            )
            
            return reservation
    
    async def execute_reservation(self, reservation_id: str) -> RateLimitResult:
        """
        Execute a reservation.
        
        Args:
            reservation_id: ID of the reservation to execute
            
        Returns:
            RateLimitResult
            
        Raises:
            KeyError: If reservation not found
            ValueError: If reservation expired or not ready
        """
        async with self._reservation_lock:
            if reservation_id not in self._reservations:
                raise KeyError(f"Reservation {reservation_id} not found")
            
            reservation = self._reservations[reservation_id]
            
            if reservation.is_expired():
                del self._reservations[reservation_id]
                raise ValueError(f"Reservation {reservation_id} has expired")
            
            if not reservation.is_ready():
                wait_time = reservation.execute_at - time.time()
                raise ValueError(
                    f"Reservation {reservation_id} not ready, "
                    f"wait {wait_time:.1f}s"
                )
            
            # Try to acquire tokens
            result = await self.acquire(reservation.key, reservation.count)
            
            # Remove reservation after execution attempt
            del self._reservations[reservation_id]
            
            return result
    
    async def cancel_reservation(self, reservation_id: str) -> bool:
        """
        Cancel a reservation.
        
        Args:
            reservation_id: ID of the reservation to cancel
            
        Returns:
            True if cancelled, False if not found
        """
        async with self._reservation_lock:
            if reservation_id in self._reservations:
                del self._reservations[reservation_id]
                return True
            return False
    
    async def _cleanup_expired_reservations(self):
        """Remove expired reservations"""
        now = time.time()
        expired = [
            rid for rid, res in self._reservations.items()
            if res.is_expired()
        ]
        
        for rid in expired:
            del self._reservations[rid]
            self._stats["reservations_expired"] += 1
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the rate limiter"""
        shard_status = []
        total_available = 0
        
        for i, limiter in enumerate(self.limiters):
            status = limiter.get_status()
            tokens = limiter.tokens
            total_available += tokens
            
            shard_status.append({
                "shard_id": i,
                "tokens_available": tokens,
                "capacity": limiter.capacity,
                "rate": limiter.rate,
                "requests_handled": self._stats["shard_distribution"][i]
            })
        
        return {
            "total_rate": self.total_rate,
            "period": self.period,
            "shards": self.shards,
            "algorithm": self.algorithm,
            "total_tokens_available": total_available,
            "reservations": {
                "active": len(self._reservations),
                "total_created": self._stats["reservations_created"],
                "expired": self._stats["reservations_expired"]
            },
            "statistics": {
                "total_requests": self._stats["total_requests"],
                "allowed": self._stats["allowed_requests"],
                "denied": self._stats["denied_requests"],
                "success_rate": (
                    self._stats["allowed_requests"] / self._stats["total_requests"]
                    if self._stats["total_requests"] > 0 else 1.0
                )
            },
            "shard_details": shard_status
        }
    
    def get_shard_balance(self) -> Dict[str, Any]:
        """Get information about shard load distribution"""
        distribution = self._stats["shard_distribution"]
        total_requests = sum(distribution)
        
        if total_requests == 0:
            return {
                "balanced": True,
                "distribution": distribution,
                "imbalance_ratio": 0.0
            }
        
        expected_per_shard = total_requests / self.shards
        max_deviation = max(
            abs(count - expected_per_shard) for count in distribution
        )
        imbalance_ratio = max_deviation / expected_per_shard if expected_per_shard > 0 else 0
        
        return {
            "balanced": imbalance_ratio < 0.2,  # Within 20% is considered balanced
            "distribution": distribution,
            "imbalance_ratio": imbalance_ratio,
            "most_loaded_shard": distribution.index(max(distribution)),
            "least_loaded_shard": distribution.index(min(distribution))
        }
    
    async def reset(self):
        """Reset all shards and clear reservations"""
        for limiter in self.limiters:
            limiter.reset()
        
        async with self._reservation_lock:
            self._reservations.clear()
        
        # Reset stats but keep shard distribution for analysis
        self._stats = {
            "total_requests": 0,
            "allowed_requests": 0,
            "denied_requests": 0,
            "reservations_created": 0,
            "reservations_expired": 0,
            "shard_distribution": [0] * self.shards
        }


class AdaptiveShardedRateLimiter(ShardedRateLimiter):
    """Sharded rate limiter with adaptive shard rebalancing"""
    
    def __init__(
        self,
        rate: int,
        period: float = 60.0,
        initial_shards: int = 1,
        algorithm: str = "token_bucket",
        burst_size: Optional[int] = None,
        rebalance_threshold: float = 0.3,
        rebalance_interval: float = 300.0  # 5 minutes
    ):
        super().__init__(rate, period, initial_shards, algorithm, burst_size)
        
        self.rebalance_threshold = rebalance_threshold
        self.rebalance_interval = rebalance_interval
        self._last_rebalance = time.time()
        self._rebalance_lock = asyncio.Lock()
    
    async def acquire(self, key: str = "default", count: int = 1) -> RateLimitResult:
        """Acquire with periodic rebalancing check"""
        result = await super().acquire(key, count)
        
        # Check if rebalancing needed
        if time.time() - self._last_rebalance > self.rebalance_interval:
            asyncio.create_task(self._check_and_rebalance())
        
        return result
    
    async def _check_and_rebalance(self):
        """Check shard balance and rebalance if needed"""
        async with self._rebalance_lock:
            # Prevent frequent rebalancing
            if time.time() - self._last_rebalance < self.rebalance_interval:
                return
            
            balance = self.get_shard_balance()
            
            if balance["imbalance_ratio"] > self.rebalance_threshold:
                logger.info(
                    f"Shard imbalance detected: {balance['imbalance_ratio']:.2f}, "
                    f"rebalancing..."
                )
                
                # In a real implementation, we might:
                # 1. Adjust hash functions
                # 2. Add/remove shards
                # 3. Migrate state between shards
                
                # For now, just log and reset counters
                self._stats["shard_distribution"] = [0] * self.shards
                self._last_rebalance = time.time()


class DistributedRateLimiter:
    """
    Rate limiter designed for distributed systems.
    
    This would typically use Redis or similar for shared state.
    For now, this is a local implementation that demonstrates the interface.
    """
    
    def __init__(
        self,
        rate: int,
        period: float = 60.0,
        namespace: str = "default",
        backend: str = "memory"  # Could be "redis", "memcached", etc.
    ):
        self.rate = rate
        self.period = period
        self.namespace = namespace
        self.backend = backend
        
        # For demo, use local sharded implementation
        self._local_limiter = ShardedRateLimiter(
            rate=rate,
            period=period,
            shards=4,  # Default to 4 shards
            algorithm="sliding_window"  # Better for distributed
        )
        
        logger.info(
            f"Initialized DistributedRateLimiter: "
            f"namespace={namespace}, backend={backend}"
        )
    
    async def acquire(self, key: str, count: int = 1) -> RateLimitResult:
        """Acquire tokens from distributed rate limiter"""
        # In real implementation, this would:
        # 1. Connect to Redis/Memcached
        # 2. Use Lua scripts for atomic operations
        # 3. Handle network failures gracefully
        
        full_key = f"{self.namespace}:{key}"
        return await self._local_limiter.acquire(full_key, count)
    
    async def reserve(self, key: str, count: int = 1, max_wait: float = 300.0) -> TokenReservation:
        """Reserve tokens with distributed coordination"""
        full_key = f"{self.namespace}:{key}"
        return await self._local_limiter.reserve(full_key, count, max_wait)
    
    def get_status(self) -> Dict[str, Any]:
        """Get status including backend health"""
        status = self._local_limiter.get_status()
        status["backend"] = {
            "type": self.backend,
            "healthy": True,  # Would check actual backend
            "namespace": self.namespace
        }
        return status