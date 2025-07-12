"""Core module containing shared models, exceptions, and constants"""

from .models import (
    NuanceLevel,
    FlashcardDifficulty,
    PartOfSpeech,
    ExportFormat,
    VocabularyItem,
    ValidationError,
    BatchResult,
    ProcessingMetrics,
    ErrorInfo,
)

from .exceptions import (
    PipelineError,
    ApiError,
    ValidationError as ValidationException,
    ProcessingError,
    CacheError,
    RateLimitError,
    CircuitBreakerError,
    ExportError,
    DatabaseError,
    ConfigurationError,
)

from .constants import (
    DEFAULT_API_TIMEOUT,
    DEFAULT_RETRY_COUNT,
    DEFAULT_CACHE_TTL,
    DEFAULT_RATE_LIMIT,
    DEFAULT_BATCH_SIZE,
    VERSION,
)

__all__ = [
    # Models
    "NuanceLevel",
    "FlashcardDifficulty", 
    "PartOfSpeech",
    "ExportFormat",
    "VocabularyItem",
    "ValidationError",
    "BatchResult",
    "ProcessingMetrics",
    "ErrorInfo",
    
    # Exceptions
    "PipelineError",
    "ApiError",
    "ValidationException",
    "ProcessingError",
    "CacheError",
    "RateLimitError",
    "CircuitBreakerError",
    "ExportError",
    "DatabaseError",
    "ConfigurationError",
    
    # Constants
    "DEFAULT_API_TIMEOUT",
    "DEFAULT_RETRY_COUNT",
    "DEFAULT_CACHE_TTL",
    "DEFAULT_RATE_LIMIT",
    "DEFAULT_BATCH_SIZE",
    "VERSION",
]