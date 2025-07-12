"""
Advanced retry utilities with exponential backoff and jitter.

This module provides a configurable retry mechanism with exponential backoff
and optional jitter to prevent thundering herd problems.
"""
from dataclasses import dataclass
from typing import TypeVar, Callable, Awaitable, Optional, Union, Tuple
import asyncio
import random
import time
from functools import wraps
import logging

from ..exceptions import RetryExhausted

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class RetryConfig:
    """Configuration for retry behavior.
    
    Attributes:
        max_attempts: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds between retries (default: 1.0)
        max_delay: Maximum delay in seconds between retries (default: 60.0)
        exponential_base: Base for exponential backoff calculation (default: 2.0)
        jitter: Whether to add jitter to delays (default: True)
        retry_on: Tuple of exception types to retry on (default: (Exception,))
    """
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on: Tuple[type[Exception], ...] = (Exception,)
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay with optional jitter.
        
        Args:
            attempt: The attempt number (0-based)
            
        Returns:
            The delay in seconds to wait before the next attempt
        """
        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        if self.jitter:
            # Add 0-50% jitter to prevent thundering herd
            delay *= (0.5 + random.random() * 0.5)
        return delay


def retry_async(config: Optional[RetryConfig] = None):
    """Decorator for retrying async functions.
    
    Args:
        config: Retry configuration (uses defaults if None)
        
    Returns:
        Decorated function that implements retry logic
    """
    if config is None:
        config = RetryConfig()
        
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except config.retry_on as e:
                    last_exception = e
                    
                    if attempt < config.max_attempts - 1:
                        delay = config.calculate_delay(attempt)
                        logger.warning(
                            f"Retry {attempt + 1}/{config.max_attempts} for {func.__name__} "
                            f"after {type(e).__name__}: {str(e)}. "
                            f"Waiting {delay:.2f}s before next attempt."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {config.max_attempts} retry attempts exhausted for {func.__name__}"
                        )
                        
            # Raise RetryExhausted with the original exception
            raise RetryExhausted(
                f"Retry exhausted after {config.max_attempts} attempts",
                last_exception=last_exception
            )
            
        return wrapper
    return decorator


def retry_sync(config: Optional[RetryConfig] = None):
    """Decorator for retrying synchronous functions.
    
    Args:
        config: Retry configuration (uses defaults if None)
        
    Returns:
        Decorated function that implements retry logic
    """
    if config is None:
        config = RetryConfig()
        
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except config.retry_on as e:
                    last_exception = e
                    
                    if attempt < config.max_attempts - 1:
                        delay = config.calculate_delay(attempt)
                        logger.warning(
                            f"Retry {attempt + 1}/{config.max_attempts} for {func.__name__} "
                            f"after {type(e).__name__}: {str(e)}. "
                            f"Waiting {delay:.2f}s before next attempt."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {config.max_attempts} retry attempts exhausted for {func.__name__}"
                        )
                        
            # Raise RetryExhausted with the original exception
            raise RetryExhausted(
                f"Retry exhausted after {config.max_attempts} attempts",
                last_exception=last_exception
            )
            
        return wrapper
    return decorator


async def retry_with_config(
    func: Callable[..., Awaitable[T]],
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> T:
    """Execute an async function with retry logic.
    
    Args:
        func: Async function to retry
        *args: Positional arguments for func
        config: Retry configuration (uses defaults if None)
        **kwargs: Keyword arguments for func
        
    Returns:
        Result of the function
        
    Raises:
        RetryExhausted: If all retry attempts fail
    """
    if config is None:
        config = RetryConfig()
        
    last_exception = None
    
    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)
        except config.retry_on as e:
            last_exception = e
            
            if attempt < config.max_attempts - 1:
                delay = config.calculate_delay(attempt)
                logger.warning(
                    f"Retry {attempt + 1}/{config.max_attempts} for {func.__name__} "
                    f"after {type(e).__name__}: {str(e)}. "
                    f"Waiting {delay:.2f}s before next attempt."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"All {config.max_attempts} retry attempts exhausted for {func.__name__}"
                )
                
    raise RetryExhausted(
        f"Retry exhausted after {config.max_attempts} attempts",
        last_exception=last_exception
    )