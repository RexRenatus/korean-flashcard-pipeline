"""Circuit breaker pattern implementation"""

import asyncio
import time
from typing import Optional, Callable, Any, Dict
from enum import Enum
from datetime import datetime, timedelta
import logging

from .exceptions import CircuitBreakerError


logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject all calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker for API calls"""
    
    def __init__(self,
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: type = Exception,
                 name: str = "circuit_breaker"):
        """Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying half-open
            expected_exception: Exception type to catch
            name: Name for logging
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name
        
        # State tracking
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state_changed_at = time.time()
        
        # Statistics
        self._call_count = 0
        self._success_count = 0
        self._failure_stats: Dict[str, int] = {}
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        return self._state
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker
        
        Args:
            func: Async function to call
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result from func
            
        Raises:
            CircuitBreakerError: If circuit is open
        """
        async with self._lock:
            self._call_count += 1
            
            # Check if we should transition from OPEN to HALF_OPEN
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    self._state_changed_at = time.time()
                    logger.info(f"{self.name}: Transitioning to HALF_OPEN")
                else:
                    raise CircuitBreakerError(
                        f"{self.name} is OPEN",
                        service=self.name,
                        failure_count=self._failure_count,
                        threshold=self.failure_threshold
                    )
        
        # Try to execute the function
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except self.expected_exception as e:
            await self._on_failure(e)
            raise
    
    async def _on_success(self):
        """Handle successful call"""
        async with self._lock:
            self._success_count += 1
            
            if self._state == CircuitState.HALF_OPEN:
                # Success in half-open state, close the circuit
                logger.info(f"{self.name}: Success in HALF_OPEN, closing circuit")
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._state_changed_at = time.time()
    
    async def _on_failure(self, exception: Exception):
        """Handle failed call"""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            # Track failure types
            error_type = type(exception).__name__
            self._failure_stats[error_type] = self._failure_stats.get(error_type, 0) + 1
            
            if self._state == CircuitState.HALF_OPEN:
                # Failure in half-open state, reopen the circuit
                logger.warning(f"{self.name}: Failure in HALF_OPEN, reopening circuit")
                self._state = CircuitState.OPEN
                self._state_changed_at = time.time()
            
            elif self._failure_count >= self.failure_threshold:
                # Too many failures, open the circuit
                logger.warning(
                    f"{self.name}: Failure threshold reached ({self._failure_count}), "
                    f"opening circuit"
                )
                self._state = CircuitState.OPEN
                self._state_changed_at = time.time()
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try reset"""
        return (
            self._last_failure_time and
            time.time() - self._last_failure_time >= self.recovery_timeout
        )
    
    async def reset(self):
        """Manually reset the circuit breaker"""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._state_changed_at = time.time()
            logger.info(f"{self.name}: Manually reset to CLOSED")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        success_rate = 0.0
        if self._call_count > 0:
            success_rate = (self._success_count / self._call_count) * 100
        
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "call_count": self._call_count,
            "success_count": self._success_count,
            "success_rate": success_rate,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "state_duration": time.time() - self._state_changed_at,
            "failure_types": self._failure_stats
        }


class MultiServiceCircuitBreaker:
    """Manages circuit breakers for multiple services"""
    
    def __init__(self):
        """Initialize multi-service circuit breaker"""
        self.breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
    
    async def get_breaker(self, service: str, **kwargs) -> CircuitBreaker:
        """Get or create circuit breaker for a service
        
        Args:
            service: Service name
            **kwargs: Arguments for CircuitBreaker if creating new
            
        Returns:
            Circuit breaker for the service
        """
        async with self._lock:
            if service not in self.breakers:
                self.breakers[service] = CircuitBreaker(
                    name=service,
                    **kwargs
                )
            return self.breakers[service]
    
    async def call(self, service: str, func: Callable, *args, **kwargs) -> Any:
        """Call function through service's circuit breaker
        
        Args:
            service: Service name
            func: Function to call
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result from func
        """
        breaker = await self.get_breaker(service)
        return await breaker.call(func, *args, **kwargs)
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers"""
        return {
            service: breaker.get_stats()
            for service, breaker in self.breakers.items()
        }
    
    async def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self.breakers.values():
            await breaker.reset()


class AdaptiveCircuitBreaker(CircuitBreaker):
    """Circuit breaker that adapts thresholds based on patterns"""
    
    def __init__(self, 
                 initial_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: type = Exception,
                 name: str = "adaptive_circuit_breaker"):
        super().__init__(initial_threshold, recovery_timeout, expected_exception, name)
        
        # Adaptive parameters
        self.min_threshold = 3
        self.max_threshold = 20
        self.threshold_adjustment = 2
        
        # Pattern tracking
        self._error_timestamps: list[float] = []
        self._error_pattern_window = 300  # 5 minutes
    
    async def _on_failure(self, exception: Exception):
        """Handle failure with pattern detection"""
        current_time = time.time()
        
        async with self._lock:
            # Add to error timestamps
            self._error_timestamps.append(current_time)
            
            # Clean old timestamps
            cutoff = current_time - self._error_pattern_window
            self._error_timestamps = [t for t in self._error_timestamps if t > cutoff]
            
            # Detect error burst pattern
            if len(self._error_timestamps) >= self.failure_threshold:
                # Calculate error rate
                time_span = self._error_timestamps[-1] - self._error_timestamps[0]
                if time_span > 0:
                    error_rate = len(self._error_timestamps) / time_span
                    
                    # Adjust threshold based on error rate
                    if error_rate > 0.5:  # More than 1 error per 2 seconds
                        # Lower threshold for faster circuit opening
                        self.failure_threshold = max(
                            self.min_threshold,
                            self.failure_threshold - self.threshold_adjustment
                        )
                        logger.info(
                            f"{self.name}: High error rate detected, "
                            f"lowering threshold to {self.failure_threshold}"
                        )
        
        # Call parent implementation
        await super()._on_failure(exception)
    
    async def _on_success(self):
        """Handle success with threshold recovery"""
        async with self._lock:
            # Clear error timestamps on success
            self._error_timestamps.clear()
            
            # Gradually increase threshold on sustained success
            if self._success_count % 10 == 0:
                self.failure_threshold = min(
                    self.max_threshold,
                    self.failure_threshold + 1
                )
                logger.debug(
                    f"{self.name}: Sustained success, "
                    f"increasing threshold to {self.failure_threshold}"
                )
        
        await super()._on_success()