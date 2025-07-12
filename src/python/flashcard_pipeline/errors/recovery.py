"""Error recovery strategies and policies"""

import asyncio
import time
import random
import logging
from enum import Enum
from typing import Optional, Callable, Any, Dict, List, Type, Union, TypeVar
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from .base import FlashcardError, ErrorCategory, ErrorSeverity
from .categories import (
    TransientError,
    NetworkError,
    RateLimitError,
    TimeoutError,
    CacheError,
    FallbackUsedError,
)
from .collector import ErrorRecord, get_error_collector
from ..telemetry import create_span, record_metric, add_event
from ..circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RecoveryStrategy(Enum):
    """Available recovery strategies"""
    RETRY = "retry"                # Retry with backoff
    CIRCUIT_BREAK = "circuit_break" # Use circuit breaker
    FALLBACK = "fallback"          # Use fallback value/service
    DEGRADE = "degrade"            # Graceful degradation
    SKIP = "skip"                  # Skip and continue
    FAIL = "fail"                  # Fail immediately


@dataclass
class RetryPolicy:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    
    # Retry conditions
    retry_on: List[Type[Exception]] = field(default_factory=lambda: [TransientError])
    retry_on_status_codes: List[int] = field(default_factory=lambda: [429, 502, 503, 504])
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Check if error should be retried"""
        if attempt >= self.max_attempts:
            return False
        
        # Check error type
        if isinstance(error, FlashcardError):
            # Use error's own retry logic
            if not error.should_retry():
                return False
        
        # Check against retry conditions
        for error_type in self.retry_on:
            if isinstance(error, error_type):
                return True
        
        # Check status codes for network errors
        if isinstance(error, NetworkError):
            status_code = error.metadata.extra.get("status_code")
            if status_code in self.retry_on_status_codes:
                return True
        
        return False
    
    def get_delay(self, attempt: int, error: Optional[Exception] = None) -> float:
        """Calculate retry delay"""
        # Check for explicit retry_after
        if error and isinstance(error, FlashcardError):
            retry_after = error.get_retry_after()
            if retry_after:
                return retry_after
        
        # Exponential backoff
        delay = min(
            self.initial_delay * (self.exponential_base ** (attempt - 1)),
            self.max_delay
        )
        
        # Add jitter
        if self.jitter:
            delay *= (0.5 + random.random())
        
        return delay


@dataclass
class FallbackPolicy:
    """Configuration for fallback behavior"""
    fallback_value: Optional[Any] = None
    fallback_function: Optional[Callable[[], Any]] = None
    cache_fallback: bool = True
    degrade_gracefully: bool = True
    
    def get_fallback(self) -> Any:
        """Get fallback value"""
        if self.fallback_function:
            return self.fallback_function()
        return self.fallback_value


class RecoveryHandler(ABC):
    """Base class for recovery handlers"""
    
    @abstractmethod
    async def handle(self, error: FlashcardError, context: Dict[str, Any]) -> Any:
        """Handle error recovery"""
        pass


class RetryHandler(RecoveryHandler):
    """Handler for retry recovery"""
    
    def __init__(self, policy: RetryPolicy):
        self.policy = policy
    
    async def handle(self, error: FlashcardError, context: Dict[str, Any]) -> Any:
        """Handle retry recovery"""
        func = context.get("function")
        args = context.get("args", ())
        kwargs = context.get("kwargs", {})
        attempt = context.get("attempt", 1)
        
        if not func:
            raise ValueError("No function provided for retry")
        
        with create_span(
            "recovery.retry",
            attributes={
                "retry.attempt": attempt,
                "retry.max_attempts": self.policy.max_attempts,
                "error.type": type(error).__name__
            }
        ) as span:
            # Check if should retry
            if not self.policy.should_retry(error, attempt):
                span.set_attribute("retry.exhausted", True)
                raise error
            
            # Calculate delay
            delay = self.policy.get_delay(attempt, error)
            span.set_attribute("retry.delay_seconds", delay)
            
            # Record retry metric
            record_metric(
                "recovery.retry",
                1,
                metric_type="counter",
                attributes={
                    "attempt": attempt,
                    "error_type": type(error).__name__
                }
            )
            
            # Wait before retry
            if delay > 0:
                add_event(
                    "retry.waiting",
                    attributes={"delay_seconds": delay}
                )
                await asyncio.sleep(delay)
            
            # Retry the function
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                span.set_attribute("retry.successful", True)
                
                record_metric(
                    "recovery.retry.success",
                    1,
                    metric_type="counter",
                    attributes={"attempts": attempt}
                )
                
                return result
                
            except Exception as e:
                # Update context for next attempt
                context["attempt"] = attempt + 1
                context["last_error"] = e
                
                # Try again or propagate
                if self.policy.should_retry(e, attempt + 1):
                    return await self.handle(e if isinstance(e, FlashcardError) else 
                                           FlashcardError(str(e), cause=e), context)
                raise


class CircuitBreakerHandler(RecoveryHandler):
    """Handler for circuit breaker recovery"""
    
    def __init__(self, circuit_breaker: CircuitBreaker):
        self.circuit_breaker = circuit_breaker
    
    async def handle(self, error: FlashcardError, context: Dict[str, Any]) -> Any:
        """Handle circuit breaker recovery"""
        func = context.get("function")
        args = context.get("args", ())
        kwargs = context.get("kwargs", {})
        
        if not func:
            raise ValueError("No function provided for circuit breaker")
        
        with create_span(
            "recovery.circuit_breaker",
            attributes={
                "circuit_breaker.name": self.circuit_breaker.name,
                "circuit_breaker.state": self.circuit_breaker.state.value
            }
        ):
            try:
                # Execute through circuit breaker
                if asyncio.iscoroutinefunction(func):
                    result = await self.circuit_breaker.call_async(func, *args, **kwargs)
                else:
                    result = await self.circuit_breaker.call(func, *args, **kwargs)
                
                return result
                
            except Exception as e:
                # Circuit breaker opened or call failed
                record_metric(
                    "recovery.circuit_breaker.failed",
                    1,
                    metric_type="counter",
                    attributes={
                        "circuit_breaker": self.circuit_breaker.name,
                        "state": self.circuit_breaker.state.value
                    }
                )
                raise


class FallbackHandler(RecoveryHandler):
    """Handler for fallback recovery"""
    
    def __init__(self, policy: FallbackPolicy):
        self.policy = policy
    
    async def handle(self, error: FlashcardError, context: Dict[str, Any]) -> Any:
        """Handle fallback recovery"""
        with create_span(
            "recovery.fallback",
            attributes={
                "fallback.cache_enabled": self.policy.cache_fallback,
                "fallback.graceful_degradation": self.policy.degrade_gracefully
            }
        ) as span:
            # Try cache fallback first
            if self.policy.cache_fallback:
                cache = context.get("cache")
                cache_key = context.get("cache_key")
                
                if cache and cache_key:
                    try:
                        cached_value = await cache.get(cache_key)
                        if cached_value is not None:
                            span.set_attribute("fallback.cache_hit", True)
                            
                            add_event(
                                "fallback.cache_used",
                                attributes={"cache_key": cache_key}
                            )
                            
                            # Create degraded error for tracking
                            fallback_error = FallbackUsedError(
                                "Using cached fallback due to error",
                                primary_service=context.get("service", "unknown"),
                                fallback_service="cache",
                                degradation_reason=str(error)
                            )
                            
                            # Collect but don't raise
                            get_error_collector().collect(fallback_error)
                            
                            return cached_value
                    except Exception as cache_error:
                        logger.warning(f"Cache fallback failed: {cache_error}")
            
            # Use configured fallback
            fallback_value = self.policy.get_fallback()
            
            if fallback_value is not None:
                span.set_attribute("fallback.default_used", True)
                
                # Create degraded error
                fallback_error = FallbackUsedError(
                    "Using default fallback due to error",
                    primary_service=context.get("service", "unknown"),
                    fallback_service="default",
                    degradation_reason=str(error)
                )
                
                get_error_collector().collect(fallback_error)
                
                record_metric(
                    "recovery.fallback.used",
                    1,
                    metric_type="counter",
                    attributes={
                        "fallback_type": "default",
                        "original_error": type(error).__name__
                    }
                )
                
                return fallback_value
            
            # No fallback available
            raise error


class ErrorRecoveryManager:
    """Manages error recovery strategies"""
    
    def __init__(self):
        self.strategies: Dict[ErrorCategory, RecoveryStrategy] = {
            ErrorCategory.TRANSIENT: RecoveryStrategy.RETRY,
            ErrorCategory.PERMANENT: RecoveryStrategy.FAIL,
            ErrorCategory.DEGRADED: RecoveryStrategy.FALLBACK,
            ErrorCategory.SYSTEM: RecoveryStrategy.CIRCUIT_BREAK,
            ErrorCategory.BUSINESS: RecoveryStrategy.FAIL,
        }
        
        self.handlers: Dict[RecoveryStrategy, RecoveryHandler] = {}
        
        # Default policies
        self.retry_policy = RetryPolicy()
        self.fallback_policy = FallbackPolicy()
        
        # Set up default handlers
        self.handlers[RecoveryStrategy.RETRY] = RetryHandler(self.retry_policy)
        self.handlers[RecoveryStrategy.FALLBACK] = FallbackHandler(self.fallback_policy)
    
    def set_strategy(self, category: ErrorCategory, strategy: RecoveryStrategy):
        """Set recovery strategy for error category"""
        self.strategies[category] = strategy
    
    def set_handler(self, strategy: RecoveryStrategy, handler: RecoveryHandler):
        """Set handler for recovery strategy"""
        self.handlers[strategy] = handler
    
    def get_strategy(self, error: FlashcardError) -> RecoveryStrategy:
        """Get recovery strategy for error"""
        # Check for explicit strategy in metadata
        explicit_strategy = error.metadata.recovery_strategy
        if explicit_strategy:
            try:
                return RecoveryStrategy(explicit_strategy)
            except ValueError:
                pass
        
        # Use category-based strategy
        return self.strategies.get(error.category, RecoveryStrategy.FAIL)
    
    async def recover(
        self,
        error: FlashcardError,
        function: Optional[Callable] = None,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Attempt to recover from error
        
        Args:
            error: The error to recover from
            function: Function that failed (for retry)
            args: Function arguments
            kwargs: Function keyword arguments
            context: Additional context for recovery
            
        Returns:
            Recovery result or raises error
        """
        kwargs = kwargs or {}
        context = context or {}
        
        # Add function context
        if function:
            context.update({
                "function": function,
                "args": args,
                "kwargs": kwargs
            })
        
        with create_span(
            "error.recover",
            attributes={
                "error.type": type(error).__name__,
                "error.category": error.category.value,
                "error.severity": error.severity.value,
                "error.recoverable": error.recoverable
            }
        ) as span:
            # Collect error
            error_record = get_error_collector().collect(error)
            
            # Get recovery strategy
            strategy = self.get_strategy(error)
            span.set_attribute("recovery.strategy", strategy.value)
            
            # Get handler
            handler = self.handlers.get(strategy)
            if not handler:
                span.set_attribute("recovery.no_handler", True)
                raise error
            
            try:
                # Attempt recovery
                result = await handler.handle(error, context)
                
                # Mark as recovered
                get_error_collector().mark_processed(
                    error_record.error_id,
                    recovery_attempted=True,
                    recovery_successful=True
                )
                
                span.set_attribute("recovery.successful", True)
                
                record_metric(
                    "error.recovery.success",
                    1,
                    metric_type="counter",
                    attributes={
                        "strategy": strategy.value,
                        "error_type": type(error).__name__
                    }
                )
                
                return result
                
            except Exception as recovery_error:
                # Recovery failed
                get_error_collector().mark_processed(
                    error_record.error_id,
                    recovery_attempted=True,
                    recovery_successful=False
                )
                
                span.set_attribute("recovery.successful", False)
                
                record_metric(
                    "error.recovery.failed",
                    1,
                    metric_type="counter",
                    attributes={
                        "strategy": strategy.value,
                        "error_type": type(error).__name__,
                        "recovery_error": type(recovery_error).__name__
                    }
                )
                
                raise recovery_error


# Global recovery manager
_recovery_manager = ErrorRecoveryManager()


def get_recovery_manager() -> ErrorRecoveryManager:
    """Get global recovery manager"""
    return _recovery_manager


async def recover_with_retry(
    func: Callable[..., T],
    *args,
    retry_policy: Optional[RetryPolicy] = None,
    **kwargs
) -> T:
    """Execute function with retry recovery
    
    Args:
        func: Function to execute
        *args: Function arguments
        retry_policy: Custom retry policy
        **kwargs: Function keyword arguments
        
    Returns:
        Function result
    """
    policy = retry_policy or RetryPolicy()
    
    attempt = 1
    last_error = None
    
    while attempt <= policy.max_attempts:
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            
            if not policy.should_retry(e, attempt):
                raise
            
            if attempt < policy.max_attempts:
                delay = policy.get_delay(attempt, e)
                await asyncio.sleep(delay)
            
            attempt += 1
    
    # Max attempts reached
    raise last_error or Exception("Max retry attempts reached")


async def recover_with_fallback(
    func: Callable[..., T],
    *args,
    fallback_value: Optional[T] = None,
    fallback_function: Optional[Callable[[], T]] = None,
    **kwargs
) -> T:
    """Execute function with fallback recovery
    
    Args:
        func: Function to execute
        *args: Function arguments
        fallback_value: Static fallback value
        fallback_function: Function to get fallback value
        **kwargs: Function keyword arguments
        
    Returns:
        Function result or fallback
    """
    try:
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    except Exception as e:
        # Log the error
        logger.warning(f"Using fallback due to error: {e}")
        
        # Use fallback
        if fallback_function:
            return fallback_function()
        return fallback_value