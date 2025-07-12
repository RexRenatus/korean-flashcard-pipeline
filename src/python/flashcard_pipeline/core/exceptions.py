"""Custom exceptions for the flashcard pipeline"""

from typing import Optional, Dict, Any


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