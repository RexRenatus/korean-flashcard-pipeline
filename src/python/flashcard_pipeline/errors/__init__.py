"""Enhanced error tracking system for Flashcard Pipeline"""

from .base import (
    FlashcardError,
    ErrorCategory,
    ErrorSeverity,
    ErrorMetadata,
    error_handler,
    with_error_handling,
    async_with_error_handling,
)

from .categories import (
    # Transient errors
    TransientError,
    NetworkError,
    RateLimitError,
    TimeoutError,
    TemporaryUnavailableError,
    
    # Permanent errors
    PermanentError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ConflictError,
    
    # System errors
    SystemError,
    DatabaseError,
    CacheError,
    ResourceExhaustedError,
    ConfigurationError,
    
    # Business errors
    BusinessError,
    QuotaExceededError,
    InvalidInputError,
    ProcessingError,
    
    # Degraded errors
    DegradedError,
    FallbackUsedError,
    PartialSuccessError,
)

from .collector import (
    ErrorCollector,
    ErrorRecord,
    get_error_collector,
)

from .recovery import (
    RecoveryStrategy,
    RetryPolicy,
    FallbackPolicy,
    ErrorRecoveryManager,
)

from .analytics import (
    ErrorAnalytics,
    ErrorMetrics,
    ErrorTrends,
)

__all__ = [
    # Base classes
    "FlashcardError",
    "ErrorCategory",
    "ErrorSeverity",
    "ErrorMetadata",
    "error_handler",
    "with_error_handling",
    "async_with_error_handling",
    
    # Error categories
    "TransientError",
    "NetworkError",
    "RateLimitError",
    "TimeoutError",
    "TemporaryUnavailableError",
    "PermanentError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "ConflictError",
    "SystemError",
    "DatabaseError",
    "CacheError",
    "ResourceExhaustedError",
    "ConfigurationError",
    "BusinessError",
    "QuotaExceededError",
    "InvalidInputError",
    "ProcessingError",
    "DegradedError",
    "FallbackUsedError",
    "PartialSuccessError",
    
    # Collector
    "ErrorCollector",
    "ErrorRecord",
    "get_error_collector",
    
    # Recovery
    "RecoveryStrategy",
    "RetryPolicy",
    "FallbackPolicy",
    "ErrorRecoveryManager",
    
    # Analytics
    "ErrorAnalytics",
    "ErrorMetrics",
    "ErrorTrends",
]