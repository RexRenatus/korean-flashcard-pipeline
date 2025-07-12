"""Rate limiting implementation for API calls"""

import asyncio
import time
import os
from typing import Optional, Dict, Any, Tuple, List, Callable
from datetime import datetime, timedelta
import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, asdict
import json
from pathlib import Path

from .exceptions import RateLimitError


logger = logging.getLogger(__name__)


# Token pricing based on OpenRouter's Claude Sonnet 3.5 pricing
# Prices in USD per 1M tokens
TOKEN_PRICING = {
    "claude-3-5-sonnet": {
        "input": 3.00,   # $3.00 per 1M input tokens
        "output": 15.00  # $15.00 per 1M output tokens
    },
    "default": {
        "input": 3.00,
        "output": 15.00
    }
}


@dataclass
class UsageAlert:
    """Represents a usage alert threshold"""
    threshold_percent: float
    message: str
    alert_type: str = "info"  # info, warning, critical
    callback: Optional[Callable] = None


class RateLimiter:
    """Token bucket rate limiter with sliding window"""
    
    def __init__(self, 
                 requests_per_minute: int = None,
                 requests_per_hour: int = None,
                 burst_size: int = None):
        """Initialize rate limiter
        
        Args:
            requests_per_minute: Max requests per minute (default from env or 600)
            requests_per_hour: Max requests per hour (default from env or 36000)
            burst_size: Max burst requests allowed (default from env or 20)
        """
        # Use environment variables with OpenRouter-appropriate defaults
        if requests_per_minute is None:
            requests_per_minute = int(os.getenv('REQUESTS_PER_MINUTE', '600'))
        if requests_per_hour is None:
            requests_per_hour = int(os.getenv('REQUESTS_PER_HOUR', '36000'))
        if burst_size is None:
            burst_size = int(os.getenv('BURST_SIZE', '20'))
        
        # Validate inputs
        if requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")
        if requests_per_hour <= 0:
            raise ValueError("requests_per_hour must be positive")
        
        # Cap very high rates
        self.requests_per_minute = min(requests_per_minute, 600000)  # 10k per second max
        self.requests_per_hour = min(requests_per_hour, 36000000)  # 10k per second max
        self.burst_size = min(burst_size, 10000)  # Reasonable burst cap
        
        # Token bucket for minute-level limiting
        self.minute_tokens = float(self.burst_size)
        self.minute_rate = requests_per_minute / 60.0  # tokens per second
        self.minute_last_update = time.monotonic()
        
        # Sliding window for hour-level limiting
        self.hour_window: list[float] = []
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
        
        # Properties for test compatibility
        self.capacity = self.burst_size
        
        # Statistics tracking
        self.stats = {
            "requests_allowed": 0,
            "requests_denied": 0,
            "start_time": time.time()
        }
        
    @property
    def tokens(self):
        """Current token count (updates based on time)"""
        now = time.monotonic()
        elapsed = now - self.minute_last_update
        current = min(
            self.capacity,
            self.minute_tokens + elapsed * self.minute_rate
        )
        # Round to avoid floating point precision issues in tests
        return round(current, 0)
    
    @property
    def rate(self):
        """Current rate limit (requests per second)"""
        return self.requests_per_minute / 60.0
    
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
    
    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without blocking
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens were acquired, False otherwise
        """
        # Update token bucket
        now = time.monotonic()
        elapsed = now - self.minute_last_update
        self.minute_tokens = min(
            self.capacity,
            self.minute_tokens + elapsed * self.minute_rate
        )
        self.minute_last_update = now
        
        # Check if we have enough tokens
        if self.minute_tokens >= tokens:
            self.minute_tokens -= tokens
            self.stats["requests_allowed"] += 1
            return True
        self.stats["requests_denied"] += 1
        return False
    
    async def acquire_async(self, timeout: float = None) -> bool:
        """Acquire a token asynchronously with optional timeout
        
        Args:
            timeout: Maximum time to wait for a token
            
        Returns:
            True if token was acquired
            
        Raises:
            RateLimitError: If timeout is reached
            ValueError: If timeout is negative
        """
        if timeout is not None and timeout < 0:
            raise ValueError("timeout must be non-negative")
            
        start_time = time.time()
        
        while True:
            if self.try_acquire():
                return True
            
            if timeout is not None and (time.time() - start_time) >= timeout:
                wait_time = (1 - self.minute_tokens) / self.minute_rate
                raise RateLimitError(
                    f"Rate limit timeout after {timeout}s",
                    retry_after=int(wait_time + 1)
                )
            
            # Wait a bit before trying again
            await asyncio.sleep(0.1)
    
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
    
    def set_rate(self, requests_per_minute: int):
        """Update the rate limit
        
        Args:
            requests_per_minute: New rate limit
        """
        self.requests_per_minute = requests_per_minute
        self.minute_rate = requests_per_minute / 60.0
        
        # Adjust capacity based on rate (1 second worth of tokens, minimum 1)
        self.capacity = max(1, int(self.minute_rate))
        self.burst_size = self.capacity
        
        # Update current tokens if they exceed new capacity
        if self.minute_tokens > self.capacity:
            self.minute_tokens = float(self.capacity)
    
    def reset_stats(self):
        """Reset statistics tracking"""
        self.stats = {
            "requests_allowed": 0,
            "requests_denied": 0,
            "start_time": time.time()
        }
    
    def reset(self):
        """Reset the rate limiter"""
        self.minute_tokens = float(self.burst_size)
        self.minute_last_update = time.monotonic()
        self.hour_window = []
        self.reset_stats()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about rate limiter usage"""
        # Calculate capacity utilization
        current_tokens = self.tokens
        capacity_utilization = 1.0 - (current_tokens / self.capacity) if self.capacity > 0 else 0.0
        
        return {
            "requests_allowed": self.stats["requests_allowed"],
            "requests_denied": self.stats["requests_denied"],
            "capacity_utilization": capacity_utilization,
            "current_tokens": current_tokens,
            "capacity": self.capacity
        }
    
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
                 initial_requests_per_minute: int = None,
                 initial_requests_per_hour: int = None,
                 burst_size: int = None):
        # Use defaults if not provided
        if initial_requests_per_minute is None:
            initial_requests_per_minute = int(os.getenv('REQUESTS_PER_MINUTE', '600'))
        if initial_requests_per_hour is None:
            initial_requests_per_hour = int(os.getenv('REQUESTS_PER_HOUR', '36000'))
        if burst_size is None:
            burst_size = int(os.getenv('BURST_SIZE', '20'))
            
        super().__init__(initial_requests_per_minute, initial_requests_per_hour, burst_size)
        
        # Adaptive parameters - adjust for OpenRouter's limits
        self.min_requests_per_minute = 10
        self.max_requests_per_minute = int(os.getenv('MAX_REQUESTS_PER_MINUTE', '1200'))  # Allow growth
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
        # Primary limiter based on API limits (OpenRouter defaults)
        self.api_limiter = AdaptiveRateLimiter(
            initial_requests_per_minute=int(os.getenv('REQUESTS_PER_MINUTE', '600')),
            initial_requests_per_hour=int(os.getenv('REQUESTS_PER_HOUR', '36000')),
            burst_size=int(os.getenv('BURST_SIZE', '20'))
        )
        
        # Cost-based limiter (tokens per hour) - more permissive for OpenRouter
        self.cost_limiter = RateLimiter(
            requests_per_minute=int(os.getenv('COST_REQUESTS_PER_MINUTE', '300')),  # Higher limit
            requests_per_hour=int(os.getenv('COST_REQUESTS_PER_HOUR', '1000')),     # More permissive
            burst_size=int(os.getenv('COST_BURST_SIZE', '10'))
        )
        
        # Stage-specific limiters - adjusted for OpenRouter capacity
        self.stage1_limiter = RateLimiter(
            requests_per_minute=int(os.getenv('STAGE1_REQUESTS_PER_MINUTE', '300')),
            requests_per_hour=int(os.getenv('STAGE1_REQUESTS_PER_HOUR', '18000')),
            burst_size=int(os.getenv('STAGE1_BURST_SIZE', '10'))
        )
        
        self.stage2_limiter = RateLimiter(
            requests_per_minute=int(os.getenv('STAGE2_REQUESTS_PER_MINUTE', '300')),
            requests_per_hour=int(os.getenv('STAGE2_REQUESTS_PER_HOUR', '18000')),
            burst_size=int(os.getenv('STAGE2_BURST_SIZE', '10'))
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


class DatabaseRateLimiter(RateLimiter):
    """Rate limiter with database tracking and quota management"""
    
    def __init__(self,
                 db_path: str,
                 requests_per_minute: int = None,
                 requests_per_hour: int = None,
                 burst_size: int = None,
                 daily_token_quota: Optional[int] = None,
                 monthly_budget_usd: Optional[float] = None,
                 model_name: str = "claude-3-5-sonnet"):
        """Initialize database-backed rate limiter
        
        Args:
            db_path: Path to SQLite database
            requests_per_minute: Max requests per minute
            requests_per_hour: Max requests per hour
            burst_size: Max burst requests allowed
            daily_token_quota: Optional daily token limit
            monthly_budget_usd: Optional monthly budget in USD
            model_name: Model name for pricing calculations
        """
        super().__init__(requests_per_minute, requests_per_hour, burst_size)
        
        self.db_path = db_path
        self.daily_token_quota = daily_token_quota
        self.monthly_budget_usd = monthly_budget_usd
        self.model_name = model_name
        
        # Alert thresholds
        self.alerts: List[UsageAlert] = [
            UsageAlert(50.0, "50% of quota used", "info"),
            UsageAlert(80.0, "80% of quota used", "warning"),
            UsageAlert(90.0, "90% of quota used - consider increasing limits", "critical")
        ]
        
        # Track alerts already sent to avoid spam
        self._alerts_sent: Dict[float, datetime] = {}
        
        # Initialize database
        self._init_database()
        
        # Restore state from database
        self._restore_state()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with proper settings"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_database(self):
        """Initialize database tables for usage tracking"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # API usage tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_usage_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    endpoint TEXT,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    total_tokens INTEGER NOT NULL DEFAULT 0,
                    estimated_cost_usd REAL NOT NULL DEFAULT 0.0,
                    status TEXT NOT NULL DEFAULT 'success',
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(request_id)
                )
            """)
            
            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_usage_created_at 
                ON api_usage_tracking(created_at DESC)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_usage_model_name 
                ON api_usage_tracking(model_name)
            """)
            
            # Quota configuration table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_quota_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    quota_type TEXT NOT NULL,  -- 'daily_tokens', 'monthly_budget'
                    quota_value REAL NOT NULL,
                    effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(quota_type, effective_date)
                )
            """)
            
            # Rate limiter state table for persistence
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rate_limiter_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    limiter_id TEXT NOT NULL UNIQUE,
                    minute_tokens REAL NOT NULL,
                    hour_window TEXT NOT NULL,  -- JSON array of timestamps
                    last_update REAL NOT NULL,
                    saved_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Usage alerts log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usage_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_type TEXT NOT NULL,
                    threshold_percent REAL NOT NULL,
                    current_usage REAL NOT NULL,
                    quota_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            
            # Initialize quota config if provided
            if self.daily_token_quota:
                cursor.execute("""
                    INSERT OR REPLACE INTO api_quota_config (quota_type, quota_value, effective_date)
                    VALUES ('daily_tokens', ?, CURRENT_DATE)
                """, (self.daily_token_quota,))
            
            if self.monthly_budget_usd:
                cursor.execute("""
                    INSERT OR REPLACE INTO api_quota_config (quota_type, quota_value, effective_date)
                    VALUES ('monthly_budget', ?, date('now', 'start of month'))
                """, (self.monthly_budget_usd,))
            
            conn.commit()
    
    def _restore_state(self):
        """Restore rate limiter state from database"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Try to restore recent state (within last hour)
            cursor.execute("""
                SELECT minute_tokens, hour_window, last_update
                FROM rate_limiter_state
                WHERE limiter_id = ?
                AND saved_at > datetime('now', '-1 hour')
                ORDER BY saved_at DESC
                LIMIT 1
            """, (f"{self.__class__.__name__}",))
            
            row = cursor.fetchone()
            if row:
                self.minute_tokens = row['minute_tokens']
                self.hour_window = json.loads(row['hour_window'])
                # Adjust for time passed since save
                time_passed = time.monotonic() - row['last_update']
                if time_passed > 0:
                    recovered_tokens = time_passed * self.minute_rate
                    self.minute_tokens = min(
                        self.burst_size,
                        self.minute_tokens + recovered_tokens
                    )
                logger.info(f"Restored rate limiter state from database")
    
    def _save_state(self):
        """Save current rate limiter state to database"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO rate_limiter_state 
                (limiter_id, minute_tokens, hour_window, last_update)
                VALUES (?, ?, ?, ?)
            """, (
                f"{self.__class__.__name__}",
                self.minute_tokens,
                json.dumps(self.hour_window),
                self.minute_last_update
            ))
            
            conn.commit()
    
    async def track_usage(self,
                         request_id: str,
                         input_tokens: int,
                         output_tokens: int,
                         endpoint: Optional[str] = None,
                         status: str = "success",
                         error_message: Optional[str] = None) -> float:
        """Track API usage in database
        
        Args:
            request_id: Unique request identifier
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            endpoint: API endpoint called
            status: Request status (success/failed/rate_limited)
            error_message: Error message if failed
            
        Returns:
            Estimated cost in USD
        """
        total_tokens = input_tokens + output_tokens
        
        # Calculate cost
        pricing = TOKEN_PRICING.get(self.model_name, TOKEN_PRICING["default"])
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO api_usage_tracking 
                    (request_id, model_name, endpoint, input_tokens, output_tokens, 
                     total_tokens, estimated_cost_usd, status, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    request_id, self.model_name, endpoint, input_tokens,
                    output_tokens, total_tokens, total_cost, status, error_message
                ))
                conn.commit()
            except sqlite3.IntegrityError:
                # Request already tracked, update retry count
                cursor.execute("""
                    UPDATE api_usage_tracking 
                    SET retry_count = retry_count + 1,
                        status = ?,
                        error_message = ?
                    WHERE request_id = ?
                """, (status, error_message, request_id))
                conn.commit()
        
        # Check quotas after tracking
        await self._check_quotas()
        
        # Save state periodically
        self._save_state()
        
        return total_cost
    
    async def _check_quotas(self):
        """Check usage against quotas and send alerts if needed"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check daily token quota
            if self.daily_token_quota:
                cursor.execute("""
                    SELECT SUM(total_tokens) as daily_tokens
                    FROM api_usage_tracking
                    WHERE DATE(created_at) = DATE('now')
                    AND status = 'success'
                """)
                row = cursor.fetchone()
                daily_tokens = row['daily_tokens'] or 0
                
                usage_percent = (daily_tokens / self.daily_token_quota) * 100
                await self._check_alerts(usage_percent, daily_tokens, "daily_tokens")
                
                if daily_tokens >= self.daily_token_quota:
                    raise RateLimitError(
                        f"Daily token quota exceeded: {daily_tokens}/{self.daily_token_quota}",
                        retry_after=86400  # Try again tomorrow
                    )
            
            # Check monthly budget
            if self.monthly_budget_usd:
                cursor.execute("""
                    SELECT SUM(estimated_cost_usd) as monthly_cost
                    FROM api_usage_tracking
                    WHERE DATE(created_at) >= DATE('now', 'start of month')
                    AND status = 'success'
                """)
                row = cursor.fetchone()
                monthly_cost = row['monthly_cost'] or 0.0
                
                usage_percent = (monthly_cost / self.monthly_budget_usd) * 100
                await self._check_alerts(usage_percent, monthly_cost, "monthly_budget")
                
                if monthly_cost >= self.monthly_budget_usd:
                    raise RateLimitError(
                        f"Monthly budget exceeded: ${monthly_cost:.2f}/${self.monthly_budget_usd:.2f}",
                        retry_after=2592000  # Try again next month
                    )
    
    async def _check_alerts(self, usage_percent: float, current_usage: float, quota_type: str):
        """Check and send usage alerts"""
        for alert in self.alerts:
            if usage_percent >= alert.threshold_percent:
                # Check if we already sent this alert today
                alert_key = f"{quota_type}:{alert.threshold_percent}"
                last_sent = self._alerts_sent.get(alert.threshold_percent)
                
                if not last_sent or (datetime.now() - last_sent).days >= 1:
                    # Log alert
                    with self._get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO usage_alerts 
                            (alert_type, threshold_percent, current_usage, quota_type, message)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            alert.alert_type,
                            alert.threshold_percent,
                            current_usage,
                            quota_type,
                            alert.message
                        ))
                        conn.commit()
                    
                    # Log based on alert type
                    if alert.alert_type == "critical":
                        logger.critical(f"Usage alert: {alert.message} - {usage_percent:.1f}% of {quota_type}")
                    elif alert.alert_type == "warning":
                        logger.warning(f"Usage alert: {alert.message} - {usage_percent:.1f}% of {quota_type}")
                    else:
                        logger.info(f"Usage alert: {alert.message} - {usage_percent:.1f}% of {quota_type}")
                    
                    # Call callback if provided
                    if alert.callback:
                        try:
                            await alert.callback(usage_percent, current_usage, quota_type)
                        except Exception as e:
                            logger.error(f"Alert callback failed: {e}")
                    
                    # Mark as sent
                    self._alerts_sent[alert.threshold_percent] = datetime.now()
    
    async def acquire(self, tokens: int = 1) -> None:
        """Acquire permission to make a request with quota checking"""
        # Check quotas before standard rate limiting
        await self._check_quotas()
        
        # Standard rate limiting
        await super().acquire(tokens)
    
    def get_usage_stats(self, period: str = "today") -> Dict[str, Any]:
        """Get usage statistics for a period
        
        Args:
            period: 'today', 'week', 'month', or 'all'
            
        Returns:
            Dictionary with usage statistics
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Build date filter
            if period == "today":
                date_filter = "DATE(created_at) = DATE('now')"
            elif period == "week":
                date_filter = "DATE(created_at) >= DATE('now', '-7 days')"
            elif period == "month":
                date_filter = "DATE(created_at) >= DATE('now', 'start of month')"
            else:
                date_filter = "1=1"  # All time
            
            # Get aggregate stats
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_requests,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_requests,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_requests,
                    SUM(CASE WHEN status = 'rate_limited' THEN 1 ELSE 0 END) as rate_limited_requests,
                    SUM(input_tokens) as total_input_tokens,
                    SUM(output_tokens) as total_output_tokens,
                    SUM(total_tokens) as total_tokens,
                    SUM(estimated_cost_usd) as total_cost_usd,
                    AVG(total_tokens) as avg_tokens_per_request,
                    MAX(total_tokens) as max_tokens_request
                FROM api_usage_tracking
                WHERE {date_filter}
            """)
            
            stats = dict(cursor.fetchone())
            
            # Get quota usage
            if self.daily_token_quota:
                cursor.execute("""
                    SELECT SUM(total_tokens) as daily_tokens
                    FROM api_usage_tracking
                    WHERE DATE(created_at) = DATE('now')
                    AND status = 'success'
                """)
                daily_tokens = cursor.fetchone()['daily_tokens'] or 0
                stats['daily_tokens_used'] = daily_tokens
                stats['daily_tokens_quota'] = self.daily_token_quota
                stats['daily_tokens_percent'] = (daily_tokens / self.daily_token_quota * 100) if self.daily_token_quota else 0
            
            if self.monthly_budget_usd:
                cursor.execute("""
                    SELECT SUM(estimated_cost_usd) as monthly_cost
                    FROM api_usage_tracking
                    WHERE DATE(created_at) >= DATE('now', 'start of month')
                    AND status = 'success'
                """)
                monthly_cost = cursor.fetchone()['monthly_cost'] or 0.0
                stats['monthly_cost_usd'] = monthly_cost
                stats['monthly_budget_usd'] = self.monthly_budget_usd
                stats['monthly_budget_percent'] = (monthly_cost / self.monthly_budget_usd * 100) if self.monthly_budget_usd else 0
            
            # Get recent alerts
            cursor.execute("""
                SELECT alert_type, threshold_percent, message, created_at
                FROM usage_alerts
                WHERE DATE(created_at) >= DATE('now', '-7 days')
                ORDER BY created_at DESC
                LIMIT 10
            """)
            stats['recent_alerts'] = [dict(row) for row in cursor.fetchall()]
            
            return stats
    
    def get_usage_by_model(self) -> Dict[str, Any]:
        """Get usage breakdown by model"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    model_name,
                    COUNT(*) as request_count,
                    SUM(total_tokens) as total_tokens,
                    SUM(estimated_cost_usd) as total_cost
                FROM api_usage_tracking
                WHERE status = 'success'
                GROUP BY model_name
                ORDER BY total_cost DESC
            """)
            
            return {row['model_name']: dict(row) for row in cursor.fetchall()}
    
    def set_quota(self, quota_type: str, value: float):
        """Update quota configuration
        
        Args:
            quota_type: 'daily_tokens' or 'monthly_budget'
            value: New quota value
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if quota_type == "daily_tokens":
                self.daily_token_quota = int(value)
                effective_date = "CURRENT_DATE"
            elif quota_type == "monthly_budget":
                self.monthly_budget_usd = value
                effective_date = "date('now', 'start of month')"
            else:
                raise ValueError(f"Invalid quota type: {quota_type}")
            
            cursor.execute(f"""
                INSERT OR REPLACE INTO api_quota_config 
                (quota_type, quota_value, effective_date)
                VALUES (?, ?, {effective_date})
            """, (quota_type, value))
            
            conn.commit()
    
    def add_alert(self, threshold_percent: float, message: str, 
                  alert_type: str = "info", callback: Optional[Callable] = None):
        """Add a custom usage alert
        
        Args:
            threshold_percent: Percentage threshold to trigger alert
            message: Alert message
            alert_type: Type of alert (info/warning/critical)
            callback: Optional async callback function
        """
        alert = UsageAlert(threshold_percent, message, alert_type, callback)
        self.alerts.append(alert)
        self.alerts.sort(key=lambda x: x.threshold_percent)