"""Custom exceptions for the flashcard pipeline"""

from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime


class PipelineError(Exception):
    """Base exception for all pipeline errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ApiError(PipelineError):
    """Error from OpenRouter API"""
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 response_body: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
        self.details = {
            "status_code": status_code,
            "response_body": response_body
        }


class RateLimitError(ApiError):
    """Rate limit exceeded error"""
    def __init__(self, message: str, retry_after: Optional[int] = None,
                 reset_at: Optional[int] = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after
        self.reset_at = reset_at
        self.details.update({
            "retry_after": retry_after,
            "reset_at": reset_at
        })


class ValidationError(PipelineError):
    """Data validation error"""
    def __init__(self, message: str, field: Optional[str] = None,
                 value: Any = None):
        super().__init__(message)
        self.field = field
        self.value = value
        self.details = {
            "field": field,
            "value": value
        }


class CacheError(PipelineError):
    """Cache operation error"""
    pass


class CircuitBreakerError(PipelineError):
    """Circuit breaker is open"""
    def __init__(self, message: str, service: str, 
                 failure_count: int, threshold: int):
        super().__init__(message)
        self.service = service
        self.failure_count = failure_count
        self.threshold = threshold
        self.details = {
            "service": service,
            "failure_count": failure_count,
            "threshold": threshold
        }


class AuthenticationError(ApiError):
    """Authentication failed"""
    def __init__(self, message: str = "Invalid API key"):
        super().__init__(message, status_code=401)


class NetworkError(PipelineError):
    """Network connectivity error"""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error
        if original_error:
            self.details["original_error"] = str(original_error)


class CircuitBreakerOpen(CircuitBreakerError):
    """Alias for CircuitBreakerError for compatibility"""
    pass


class DatabaseError(PipelineError):
    """Database operation error"""
    pass


class ParsingError(PipelineError):
    """Error parsing API output"""
    pass


class ProcessingError(PipelineError):
    """Error during data processing"""
    pass


class IngressError(PipelineError):
    """Error during data ingestion"""
    pass


class ExportError(PipelineError):
    """Error during data export"""
    pass


class ConfigurationError(PipelineError):
    """Configuration-related error"""
    pass


class RetryExhausted(PipelineError):
    """All retry attempts have been exhausted"""
    def __init__(self, message: str, last_exception: Optional[Exception] = None):
        super().__init__(message)
        self.last_exception = last_exception
        if last_exception:
            self.details["last_exception"] = str(last_exception)


class ErrorCategory(Enum):
    """Categorization of errors for proper handling."""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    CIRCUIT_BREAKER = "circuit_breaker"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    CACHE = "cache"
    INTERNAL = "internal"
    NETWORK = "network"
    PARSING = "parsing"
    CONFIGURATION = "configuration"


class StructuredError(Exception):
    """Base exception with structured error information.
    
    This class provides a standardized way to handle errors with
    categorization, error codes, and retry information.
    """
    
    def __init__(
        self,
        category: ErrorCategory,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        retry_after: Optional[float] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(message)
        self.category = category
        self.code = code
        self.message = message
        self.details = details or {}
        self.retry_after = retry_after
        self.original_exception = original_exception
        self.timestamp = datetime.utcnow()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "error": {
                "category": self.category.value,
                "code": self.code,
                "message": self.message,
                "details": self.details,
                "timestamp": self.timestamp.isoformat(),
            },
            "retry_after": self.retry_after
        }


# Structured versions of existing exceptions
class StructuredAPIError(StructuredError):
    """API error with structured information."""
    def __init__(
        self,
        status_code: int,
        message: str,
        response: Optional[Dict[str, Any]] = None,
        retry_after: Optional[float] = None
    ):
        code = f"API_{status_code}"
        category = ErrorCategory.EXTERNAL_SERVICE
        if status_code == 401:
            category = ErrorCategory.AUTHENTICATION
        elif status_code == 429:
            category = ErrorCategory.RATE_LIMIT
            
        super().__init__(
            category=category,
            code=code,
            message=message,
            details={"status_code": status_code, "response": response},
            retry_after=retry_after
        )
        self.status_code = status_code
        self.response = response


class StructuredRateLimitError(StructuredAPIError):
    """Rate limit error with retry information."""
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[float] = None,
        reset_at: Optional[datetime] = None
    ):
        super().__init__(
            status_code=429,
            message=message,
            retry_after=retry_after
        )
        if reset_at:
            self.details["reset_at"] = reset_at.isoformat()
        self.reset_at = reset_at