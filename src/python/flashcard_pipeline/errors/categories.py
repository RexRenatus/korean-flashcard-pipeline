"""Specific error categories for the Flashcard Pipeline"""

from typing import Optional, Dict, Any
from .base import FlashcardError, ErrorCategory, ErrorSeverity


# ============================================================================
# TRANSIENT ERRORS - Temporary failures that can be retried
# ============================================================================

class TransientError(FlashcardError):
    """Base class for transient errors"""
    default_category = ErrorCategory.TRANSIENT
    default_severity = ErrorSeverity.MEDIUM
    default_recoverable = True


class NetworkError(TransientError):
    """Network-related errors"""
    default_severity = ErrorSeverity.MEDIUM
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        url: Optional[str] = None,
        **extra
    ):
        super().__init__(message, **extra)
        if status_code:
            self.metadata.extra["status_code"] = status_code
        if url:
            self.metadata.extra["url"] = url
    
    def get_user_message(self) -> str:
        return "Network connection issue. Please check your connection and try again."


class RateLimitError(TransientError):
    """Rate limit exceeded error"""
    default_severity = ErrorSeverity.LOW
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None,
        limit: Optional[int] = None,
        window: Optional[str] = None,
        **extra
    ):
        super().__init__(message, **extra)
        if retry_after:
            self.metadata.extra["retry_after"] = retry_after
        if limit:
            self.metadata.extra["rate_limit"] = limit
        if window:
            self.metadata.extra["rate_window"] = window
    
    def get_retry_after(self) -> Optional[float]:
        """Get retry delay from rate limit response"""
        return self.metadata.extra.get("retry_after", 60.0)  # Default 60s
    
    def get_user_message(self) -> str:
        retry_after = self.get_retry_after()
        if retry_after:
            return f"Rate limit exceeded. Please wait {int(retry_after)} seconds before retrying."
        return "Rate limit exceeded. Please try again later."


class TimeoutError(TransientError):
    """Operation timeout error"""
    default_severity = ErrorSeverity.MEDIUM
    
    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[float] = None,
        operation: Optional[str] = None,
        **extra
    ):
        super().__init__(message, **extra)
        if timeout_seconds:
            self.metadata.extra["timeout_seconds"] = timeout_seconds
        if operation:
            self.metadata.extra["operation"] = operation
    
    def get_user_message(self) -> str:
        return "The operation took too long to complete. Please try again."


class TemporaryUnavailableError(TransientError):
    """Service temporarily unavailable"""
    default_severity = ErrorSeverity.HIGH
    
    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
        estimated_recovery: Optional[float] = None,
        **extra
    ):
        super().__init__(message, **extra)
        if service:
            self.metadata.extra["service"] = service
        if estimated_recovery:
            self.metadata.extra["estimated_recovery"] = estimated_recovery
    
    def get_user_message(self) -> str:
        service = self.metadata.extra.get("service", "The service")
        return f"{service} is temporarily unavailable. Please try again in a few moments."


# ============================================================================
# PERMANENT ERRORS - Cannot be recovered through retry
# ============================================================================

class PermanentError(FlashcardError):
    """Base class for permanent errors"""
    default_category = ErrorCategory.PERMANENT
    default_severity = ErrorSeverity.HIGH
    default_recoverable = False


class ValidationError(PermanentError):
    """Input validation error"""
    default_severity = ErrorSeverity.LOW
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        constraints: Optional[Dict[str, Any]] = None,
        **extra
    ):
        super().__init__(message, **extra)
        if field:
            self.metadata.extra["field"] = field
        if value is not None:
            self.metadata.extra["invalid_value"] = str(value)
        if constraints:
            self.metadata.extra["constraints"] = constraints
    
    def get_user_message(self) -> str:
        field = self.metadata.extra.get("field")
        if field:
            return f"Invalid value for {field}: {self}"
        return f"Invalid input: {self}"


class AuthenticationError(PermanentError):
    """Authentication failure"""
    default_severity = ErrorSeverity.HIGH
    
    def __init__(
        self,
        message: str = "Authentication failed",
        auth_method: Optional[str] = None,
        **extra
    ):
        super().__init__(message, **extra)
        if auth_method:
            self.metadata.extra["auth_method"] = auth_method
    
    def get_user_message(self) -> str:
        return "Authentication failed. Please check your credentials."


class AuthorizationError(PermanentError):
    """Authorization failure"""
    default_severity = ErrorSeverity.HIGH
    
    def __init__(
        self,
        message: str = "Access denied",
        resource: Optional[str] = None,
        required_permission: Optional[str] = None,
        **extra
    ):
        super().__init__(message, **extra)
        if resource:
            self.metadata.extra["resource"] = resource
        if required_permission:
            self.metadata.extra["required_permission"] = required_permission
    
    def get_user_message(self) -> str:
        resource = self.metadata.extra.get("resource", "this resource")
        return f"You don't have permission to access {resource}."


class NotFoundError(PermanentError):
    """Resource not found"""
    default_severity = ErrorSeverity.LOW
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **extra
    ):
        super().__init__(message, **extra)
        if resource_type:
            self.metadata.extra["resource_type"] = resource_type
        if resource_id:
            self.metadata.extra["resource_id"] = resource_id
    
    def get_user_message(self) -> str:
        resource_type = self.metadata.extra.get("resource_type", "Resource")
        return f"{resource_type} not found."


class ConflictError(PermanentError):
    """Resource conflict (e.g., duplicate)"""
    default_severity = ErrorSeverity.MEDIUM
    
    def __init__(
        self,
        message: str,
        conflicting_resource: Optional[str] = None,
        conflict_type: Optional[str] = None,
        **extra
    ):
        super().__init__(message, **extra)
        if conflicting_resource:
            self.metadata.extra["conflicting_resource"] = conflicting_resource
        if conflict_type:
            self.metadata.extra["conflict_type"] = conflict_type
    
    def get_user_message(self) -> str:
        return "A conflict occurred with an existing resource."


# ============================================================================
# SYSTEM ERRORS - Infrastructure and system-level issues
# ============================================================================

class SystemError(FlashcardError):
    """Base class for system errors"""
    default_category = ErrorCategory.SYSTEM
    default_severity = ErrorSeverity.HIGH
    default_recoverable = False


class DatabaseError(SystemError):
    """Database-related errors"""
    default_severity = ErrorSeverity.CRITICAL
    
    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        database: Optional[str] = None,
        **extra
    ):
        super().__init__(message, **extra)
        if query:
            # Sanitize query for security
            self.metadata.extra["query"] = query[:200] + "..." if len(query) > 200 else query
        if database:
            self.metadata.extra["database"] = database
    
    def get_user_message(self) -> str:
        return "A database error occurred. Our team has been notified."


class CacheError(SystemError):
    """Cache-related errors"""
    default_severity = ErrorSeverity.MEDIUM
    default_recoverable = True  # Can often fallback to direct access
    
    def __init__(
        self,
        message: str,
        cache_key: Optional[str] = None,
        cache_backend: Optional[str] = None,
        **extra
    ):
        super().__init__(message, **extra)
        if cache_key:
            self.metadata.extra["cache_key"] = cache_key
        if cache_backend:
            self.metadata.extra["cache_backend"] = cache_backend
    
    def get_user_message(self) -> str:
        return "Cache service issue detected. Performance may be degraded."


class ResourceExhaustedError(SystemError):
    """System resource exhausted (memory, disk, etc)"""
    default_severity = ErrorSeverity.CRITICAL
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        current_usage: Optional[float] = None,
        limit: Optional[float] = None,
        **extra
    ):
        super().__init__(message, **extra)
        if resource_type:
            self.metadata.extra["resource_type"] = resource_type
        if current_usage is not None:
            self.metadata.extra["current_usage"] = current_usage
        if limit is not None:
            self.metadata.extra["limit"] = limit
    
    def get_user_message(self) -> str:
        return "System resources temporarily exhausted. Please try again later."


class ConfigurationError(SystemError):
    """Configuration error"""
    default_severity = ErrorSeverity.CRITICAL
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_file: Optional[str] = None,
        **extra
    ):
        super().__init__(message, **extra)
        if config_key:
            self.metadata.extra["config_key"] = config_key
        if config_file:
            self.metadata.extra["config_file"] = config_file
    
    def get_user_message(self) -> str:
        return "System configuration error. Please contact support."


# ============================================================================
# BUSINESS ERRORS - Domain-specific errors
# ============================================================================

class BusinessError(FlashcardError):
    """Base class for business logic errors"""
    default_category = ErrorCategory.BUSINESS
    default_severity = ErrorSeverity.MEDIUM
    default_recoverable = False


class QuotaExceededError(BusinessError):
    """User quota exceeded"""
    default_severity = ErrorSeverity.MEDIUM
    
    def __init__(
        self,
        message: str,
        quota_type: Optional[str] = None,
        current_usage: Optional[int] = None,
        quota_limit: Optional[int] = None,
        reset_time: Optional[float] = None,
        **extra
    ):
        super().__init__(message, **extra)
        if quota_type:
            self.metadata.extra["quota_type"] = quota_type
        if current_usage is not None:
            self.metadata.extra["current_usage"] = current_usage
        if quota_limit is not None:
            self.metadata.extra["quota_limit"] = quota_limit
        if reset_time:
            self.metadata.extra["reset_time"] = reset_time
    
    def get_user_message(self) -> str:
        quota_type = self.metadata.extra.get("quota_type", "quota")
        return f"Your {quota_type} has been exceeded. Please upgrade your plan or wait for the quota to reset."


class InvalidInputError(BusinessError):
    """Invalid business input"""
    default_severity = ErrorSeverity.LOW
    
    def __init__(
        self,
        message: str,
        input_type: Optional[str] = None,
        reason: Optional[str] = None,
        **extra
    ):
        super().__init__(message, **extra)
        if input_type:
            self.metadata.extra["input_type"] = input_type
        if reason:
            self.metadata.extra["reason"] = reason
    
    def get_user_message(self) -> str:
        return f"Invalid input: {self}"


class ProcessingError(BusinessError):
    """Processing pipeline error"""
    default_severity = ErrorSeverity.HIGH
    
    def __init__(
        self,
        message: str,
        stage: Optional[str] = None,
        item_id: Optional[str] = None,
        **extra
    ):
        super().__init__(message, **extra)
        if stage:
            self.metadata.extra["processing_stage"] = stage
        if item_id:
            self.metadata.extra["item_id"] = item_id
    
    def get_user_message(self) -> str:
        return "An error occurred while processing your request."


# ============================================================================
# DEGRADED ERRORS - Partial failures with fallback
# ============================================================================

class DegradedError(FlashcardError):
    """Base class for degraded service errors"""
    default_category = ErrorCategory.DEGRADED
    default_severity = ErrorSeverity.LOW
    default_recoverable = False  # Already recovered via fallback


class FallbackUsedError(DegradedError):
    """Fallback mechanism was used"""
    
    def __init__(
        self,
        message: str,
        primary_service: Optional[str] = None,
        fallback_service: Optional[str] = None,
        degradation_reason: Optional[str] = None,
        **extra
    ):
        super().__init__(message, **extra)
        if primary_service:
            self.metadata.extra["primary_service"] = primary_service
        if fallback_service:
            self.metadata.extra["fallback_service"] = fallback_service
        if degradation_reason:
            self.metadata.extra["degradation_reason"] = degradation_reason
    
    def get_user_message(self) -> str:
        return "Service is operating in degraded mode. Some features may be limited."


class PartialSuccessError(DegradedError):
    """Operation partially succeeded"""
    
    def __init__(
        self,
        message: str,
        total_items: Optional[int] = None,
        successful_items: Optional[int] = None,
        failed_items: Optional[List[str]] = None,
        **extra
    ):
        super().__init__(message, **extra)
        if total_items is not None:
            self.metadata.extra["total_items"] = total_items
        if successful_items is not None:
            self.metadata.extra["successful_items"] = successful_items
        if failed_items:
            self.metadata.extra["failed_items"] = failed_items
    
    def get_user_message(self) -> str:
        successful = self.metadata.extra.get("successful_items", 0)
        total = self.metadata.extra.get("total_items", 0)
        if total > 0:
            return f"Operation partially completed: {successful}/{total} items processed successfully."
        return "Operation partially completed with some errors."