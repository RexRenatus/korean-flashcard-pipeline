"""Korean Language Flashcard Pipeline - Python API Client

This package provides the Python API client for interacting with OpenRouter
to generate Korean language flashcards using a two-stage AI pipeline.
"""

__version__ = "0.1.0"

from .api import OpenRouterClient
from .models import (
    VocabularyItem,
    Stage1Request,
    Stage1Response,
    Stage2Request,
    Stage2Response,
    FlashcardRow,
    Comparison
)
from .cache import CacheService
from .api import RateLimiter, CompositeLimiter
from .api import CircuitBreaker, MultiServiceCircuitBreaker
from .exceptions import (
    PipelineError,
    ApiError,
    RateLimitError,
    ValidationError,
    CircuitBreakerOpen,
    NetworkError
)

# Import pipeline orchestrator and related classes
from .pipeline import (
    PipelineOrchestrator,
    PipelineConfig,
    PipelineStats,
    ProcessingMode,
    create_pipeline
)

# Import concurrent processing components
from .concurrent import (
    ConcurrentPipelineOrchestrator,
    OrderedResultsCollector,
    OrderedBatchDatabaseWriter,
    ConcurrentProcessingMonitor
)

# Import CLI app and main function for programmatic access
from .cli.v2 import app as cli_app, main as cli_main

__all__ = [
    # API Client
    "OpenRouterClient",
    # Models
    "VocabularyItem",
    "Stage1Request",
    "Stage1Response", 
    "Stage2Request",
    "Stage2Response",
    "FlashcardRow",
    "Comparison",
    # Cache
    "CacheService",
    # Rate Limiting
    "RateLimiter",
    "CompositeLimiter",
    # Circuit Breaker
    "CircuitBreaker",
    "MultiServiceCircuitBreaker",
    # Exceptions
    "PipelineError",
    "ApiError",
    "RateLimitError",
    "ValidationError",
    "CircuitBreakerOpen",
    "NetworkError",
    # Pipeline Orchestration
    "PipelineOrchestrator",
    "PipelineConfig",
    "PipelineStats",
    "ProcessingMode",
    "create_pipeline",
    # Concurrent Processing
    "ConcurrentPipelineOrchestrator",
    "OrderedResultsCollector",
    "OrderedBatchDatabaseWriter",
    "ConcurrentProcessingMonitor",
    # CLI
    "cli_app",
    "cli_main"
]