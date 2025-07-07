"""Korean Language Flashcard Pipeline - Python API Client

This package provides the Python API client for interacting with OpenRouter
to generate Korean language flashcards using a two-stage AI pipeline.
"""

__version__ = "0.1.0"

from .api_client import OpenRouterClient
from .models import (
    VocabularyItem,
    Stage1Request,
    Stage1Response,
    Stage2Request,
    Stage2Response,
    FlashcardRow
)
from .cache import CacheService
from .rate_limiter import RateLimiter
from .exceptions import (
    PipelineError,
    ApiError,
    RateLimitError,
    ValidationError
)

__all__ = [
    "OpenRouterClient",
    "VocabularyItem",
    "Stage1Request",
    "Stage1Response", 
    "Stage2Request",
    "Stage2Response",
    "FlashcardRow",
    "CacheService",
    "RateLimiter",
    "PipelineError",
    "ApiError",
    "RateLimitError",
    "ValidationError"
]