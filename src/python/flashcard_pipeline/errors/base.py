"""Base error classes and utilities"""

import sys
import traceback
import time
import hashlib
import json
from enum import Enum
from typing import Dict, Any, Optional, List, Type, Callable, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
import functools
import inspect

from ..telemetry import (
    get_trace_id,
    get_span_id,
    get_current_span,
    record_metric,
    add_event,
    set_span_attributes,
)
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode


class ErrorCategory(Enum):
    """Error categories for classification"""
    TRANSIENT = "transient"      # Temporary, can retry
    PERMANENT = "permanent"      # Cannot recover, don't retry
    DEGRADED = "degraded"        # Partial failure, fallback used
    SYSTEM = "system"            # Infrastructure issues
    BUSINESS = "business"        # Domain-specific errors


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"              # Minor issue, doesn't affect functionality
    MEDIUM = "medium"        # Affects some functionality
    HIGH = "high"            # Major functionality impacted
    CRITICAL = "critical"    # System-wide impact


@dataclass
class ErrorMetadata:
    """Metadata associated with an error"""
    # Identity
    error_id: str = field(default_factory=lambda: f"err_{int(time.time() * 1000000)}")
    fingerprint: str = ""
    
    # Classification
    category: ErrorCategory = ErrorCategory.SYSTEM
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    
    # Context
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Details
    timestamp: float = field(default_factory=time.time)
    service_name: str = "flashcard-pipeline"
    environment: str = "unknown"
    host: str = ""
    
    # Error specifics
    error_type: str = ""
    error_message: str = ""
    stack_trace: str = ""
    
    # Recovery
    recoverable: bool = False
    retry_count: int = 0
    recovery_strategy: Optional[str] = None
    
    # Additional context
    tags: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Generate fingerprint and capture context"""
        if not self.fingerprint:
            self.fingerprint = self._generate_fingerprint()
        
        # Capture trace context if available
        if not self.trace_id:
            self.trace_id = get_trace_id()
        if not self.span_id:
            self.span_id = get_span_id()
    
    def _generate_fingerprint(self) -> str:
        """Generate unique fingerprint for error deduplication"""
        # Use error type, category, and key parts of message
        fingerprint_data = f"{self.error_type}:{self.category.value}:{self.error_message[:100]}"
        return hashlib.md5(fingerprint_data.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        # Convert enums to strings
        data["category"] = self.category.value
        data["severity"] = self.severity.value
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), default=str)


class FlashcardError(Exception):
    """Base exception class for Flashcard Pipeline errors"""
    
    # Default category and severity for subclasses
    default_category = ErrorCategory.SYSTEM
    default_severity = ErrorSeverity.MEDIUM
    default_recoverable = False
    
    def __init__(
        self,
        message: str,
        category: Optional[ErrorCategory] = None,
        severity: Optional[ErrorSeverity] = None,
        recoverable: Optional[bool] = None,
        cause: Optional[Exception] = None,
        **extra
    ):
        super().__init__(message)
        
        # Use defaults from class if not provided
        self.category = category or self.default_category
        self.severity = severity or self.default_severity
        self.recoverable = recoverable if recoverable is not None else self.default_recoverable
        
        # Store cause for error chaining
        self.cause = cause
        self.__cause__ = cause  # Python's exception chaining
        
        # Create metadata
        self.metadata = ErrorMetadata(
            category=self.category,
            severity=self.severity,
            recoverable=self.recoverable,
            error_type=self.__class__.__name__,
            error_message=message,
            stack_trace=self._capture_stack_trace(),
            extra=extra
        )
        
        # Record in telemetry
        self._record_telemetry()
    
    def _capture_stack_trace(self) -> str:
        """Capture current stack trace"""
        return "".join(traceback.format_tb(sys.exc_info()[2]))
    
    def _record_telemetry(self):
        """Record error in telemetry system"""
        # Record metric
        record_metric(
            "errors.total",
            1,
            metric_type="counter",
            attributes={
                "error_type": self.metadata.error_type,
                "category": self.category.value,
                "severity": self.severity.value,
                "recoverable": str(self.recoverable)
            }
        )
        
        # Add to current span if available
        span = get_current_span()
        if span and span.is_recording():
            span.record_exception(self)
            span.set_status(Status(StatusCode.ERROR, str(self)))
            
            # Add error attributes
            set_span_attributes({
                "error.category": self.category.value,
                "error.severity": self.severity.value,
                "error.recoverable": self.recoverable,
                "error.fingerprint": self.metadata.fingerprint
            })
            
            # Add error event
            add_event(
                "error.occurred",
                attributes={
                    "error_id": self.metadata.error_id,
                    "error_type": self.metadata.error_type,
                    "fingerprint": self.metadata.fingerprint
                }
            )
    
    def with_context(self, **context) -> "FlashcardError":
        """Add additional context to the error"""
        self.metadata.extra.update(context)
        return self
    
    def with_user_context(self, user_id: str, session_id: Optional[str] = None) -> "FlashcardError":
        """Add user context to the error"""
        self.metadata.user_id = user_id
        if session_id:
            self.metadata.session_id = session_id
        return self
    
    def with_tags(self, *tags: str) -> "FlashcardError":
        """Add tags to the error"""
        self.metadata.tags.extend(tags)
        return self
    
    def get_user_message(self) -> str:
        """Get user-friendly error message"""
        # Override in subclasses for better messages
        if self.recoverable:
            return f"A temporary issue occurred: {self}. Please try again."
        return f"An error occurred: {self}. Please contact support if this persists."
    
    def should_retry(self) -> bool:
        """Check if error is retryable"""
        return self.recoverable and self.category == ErrorCategory.TRANSIENT
    
    def get_retry_after(self) -> Optional[float]:
        """Get retry delay in seconds (for rate limits, etc)"""
        return self.metadata.extra.get("retry_after")
    
    def __str__(self):
        """String representation"""
        if self.cause:
            return f"{super().__str__()} (caused by: {self.cause})"
        return super().__str__()
    
    def __repr__(self):
        """Detailed representation"""
        return (
            f"{self.__class__.__name__}("
            f"message={super().__str__()!r}, "
            f"category={self.category.value}, "
            f"severity={self.severity.value}, "
            f"recoverable={self.recoverable})"
        )


def error_handler(
    *error_types: Type[Exception],
    fallback_value: Any = None,
    reraise: bool = True,
    log_error: bool = True
) -> Callable:
    """Decorator for consistent error handling
    
    Args:
        *error_types: Exception types to catch
        fallback_value: Value to return on error
        reraise: Whether to re-raise the exception
        log_error: Whether to log the error
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except error_types as e:
                # Convert to FlashcardError if needed
                if not isinstance(e, FlashcardError):
                    e = FlashcardError(
                        str(e),
                        category=ErrorCategory.SYSTEM,
                        cause=e
                    )
                
                if log_error:
                    # Error is automatically logged via telemetry
                    pass
                
                if reraise:
                    raise
                
                return fallback_value
        
        return wrapper
    return decorator


def with_error_handling(
    category: ErrorCategory = ErrorCategory.SYSTEM,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    recoverable: bool = False
) -> Callable:
    """Decorator to wrap exceptions in FlashcardError
    
    Args:
        category: Error category for wrapped exceptions
        severity: Error severity for wrapped exceptions
        recoverable: Whether wrapped errors are recoverable
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except FlashcardError:
                # Already a FlashcardError, just re-raise
                raise
            except Exception as e:
                # Wrap in FlashcardError
                raise FlashcardError(
                    f"Error in {func.__name__}: {str(e)}",
                    category=category,
                    severity=severity,
                    recoverable=recoverable,
                    cause=e
                )
        
        return wrapper
    return decorator


def async_with_error_handling(
    category: ErrorCategory = ErrorCategory.SYSTEM,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    recoverable: bool = False
) -> Callable:
    """Async version of with_error_handling decorator"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except FlashcardError:
                raise
            except Exception as e:
                raise FlashcardError(
                    f"Error in {func.__name__}: {str(e)}",
                    category=category,
                    severity=severity,
                    recoverable=recoverable,
                    cause=e
                )
        
        return wrapper
    return decorator