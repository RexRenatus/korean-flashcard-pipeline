"""Unit tests for structured error handling"""

import pytest
from datetime import datetime
import json

from flashcard_pipeline.exceptions import (
    ErrorCategory,
    StructuredError,
    StructuredAPIError,
    StructuredRateLimitError,
    RetryExhausted,
)


class TestErrorCategory:
    """Test ErrorCategory enum"""
    
    def test_error_categories(self):
        """Test all error categories are defined"""
        expected_categories = [
            "validation",
            "authentication",
            "rate_limit",
            "circuit_breaker",
            "external_service",
            "database",
            "cache",
            "internal",
            "network",
            "parsing",
            "configuration",
        ]
        
        actual_categories = [cat.value for cat in ErrorCategory]
        
        for expected in expected_categories:
            assert expected in actual_categories


class TestStructuredError:
    """Test StructuredError base class"""
    
    def test_basic_structured_error(self):
        """Test creating a basic structured error"""
        error = StructuredError(
            category=ErrorCategory.VALIDATION,
            code="VAL_001",
            message="Invalid input format",
        )
        
        assert error.category == ErrorCategory.VALIDATION
        assert error.code == "VAL_001"
        assert error.message == "Invalid input format"
        assert error.details == {}
        assert error.retry_after is None
        assert error.original_exception is None
        assert isinstance(error.timestamp, datetime)
    
    def test_structured_error_with_details(self):
        """Test structured error with additional details"""
        details = {
            "field": "email",
            "value": "invalid@",
            "reason": "Missing domain"
        }
        
        error = StructuredError(
            category=ErrorCategory.VALIDATION,
            code="VAL_EMAIL",
            message="Invalid email format",
            details=details,
        )
        
        assert error.details == details
    
    def test_structured_error_with_retry_info(self):
        """Test structured error with retry information"""
        error = StructuredError(
            category=ErrorCategory.RATE_LIMIT,
            code="RATE_429",
            message="Too many requests",
            retry_after=30.5,
        )
        
        assert error.retry_after == 30.5
    
    def test_structured_error_with_original_exception(self):
        """Test structured error wrapping original exception"""
        original = ValueError("Original error")
        
        error = StructuredError(
            category=ErrorCategory.INTERNAL,
            code="INT_500",
            message="Processing failed",
            original_exception=original,
        )
        
        assert error.original_exception is original
    
    def test_to_dict_serialization(self):
        """Test error serialization to dictionary"""
        error = StructuredError(
            category=ErrorCategory.EXTERNAL_SERVICE,
            code="EXT_503",
            message="Service unavailable",
            details={"service": "openrouter", "endpoint": "/v1/chat"},
            retry_after=60.0,
        )
        
        error_dict = error.to_dict()
        
        assert error_dict["error"]["category"] == "external_service"
        assert error_dict["error"]["code"] == "EXT_503"
        assert error_dict["error"]["message"] == "Service unavailable"
        assert error_dict["error"]["details"]["service"] == "openrouter"
        assert error_dict["error"]["timestamp"]
        assert error_dict["retry_after"] == 60.0
        
        # Should be JSON serializable
        json_str = json.dumps(error_dict)
        assert json_str
    
    def test_error_inheritance(self):
        """Test that StructuredError inherits from Exception"""
        error = StructuredError(
            category=ErrorCategory.INTERNAL,
            code="TEST",
            message="Test error"
        )
        
        assert isinstance(error, Exception)
        assert str(error) == "Test error"


class TestStructuredAPIError:
    """Test StructuredAPIError class"""
    
    def test_api_error_401(self):
        """Test API error for authentication failure"""
        error = StructuredAPIError(
            status_code=401,
            message="Invalid API key",
            response={"error": "Unauthorized"},
        )
        
        assert error.status_code == 401
        assert error.category == ErrorCategory.AUTHENTICATION
        assert error.code == "API_401"
        assert error.response == {"error": "Unauthorized"}
    
    def test_api_error_429(self):
        """Test API error for rate limiting"""
        error = StructuredAPIError(
            status_code=429,
            message="Rate limit exceeded",
            retry_after=45.0,
        )
        
        assert error.status_code == 429
        assert error.category == ErrorCategory.RATE_LIMIT
        assert error.code == "API_429"
        assert error.retry_after == 45.0
    
    def test_api_error_500(self):
        """Test API error for server errors"""
        error = StructuredAPIError(
            status_code=500,
            message="Internal server error",
        )
        
        assert error.status_code == 500
        assert error.category == ErrorCategory.EXTERNAL_SERVICE
        assert error.code == "API_500"
    
    def test_api_error_serialization(self):
        """Test API error serialization"""
        error = StructuredAPIError(
            status_code=503,
            message="Service temporarily unavailable",
            response={"status": "maintenance", "eta": "2 hours"},
            retry_after=7200,
        )
        
        error_dict = error.to_dict()
        
        assert error_dict["error"]["details"]["status_code"] == 503
        assert error_dict["error"]["details"]["response"]["status"] == "maintenance"
        assert error_dict["retry_after"] == 7200


class TestStructuredRateLimitError:
    """Test StructuredRateLimitError class"""
    
    def test_rate_limit_error_basic(self):
        """Test basic rate limit error"""
        error = StructuredRateLimitError()
        
        assert error.status_code == 429
        assert error.category == ErrorCategory.RATE_LIMIT
        assert error.message == "Rate limit exceeded"
        assert error.reset_at is None
    
    def test_rate_limit_error_with_reset(self):
        """Test rate limit error with reset time"""
        reset_time = datetime.utcnow()
        
        error = StructuredRateLimitError(
            message="API quota exceeded",
            retry_after=3600,
            reset_at=reset_time,
        )
        
        assert error.retry_after == 3600
        assert error.reset_at == reset_time
        
        # Check serialization includes reset_at
        error_dict = error.to_dict()
        assert "reset_at" in error_dict["error"]["details"]
        assert error_dict["error"]["details"]["reset_at"] == reset_time.isoformat()


class TestRetryExhausted:
    """Test RetryExhausted exception"""
    
    def test_retry_exhausted_basic(self):
        """Test basic retry exhausted error"""
        error = RetryExhausted("All retries failed")
        
        assert str(error) == "All retries failed"
        assert error.last_exception is None
        assert error.details == {}
    
    def test_retry_exhausted_with_last_exception(self):
        """Test retry exhausted with last exception"""
        last_error = ConnectionError("Network timeout")
        
        error = RetryExhausted(
            "Retry exhausted after 3 attempts",
            last_exception=last_error
        )
        
        assert error.last_exception is last_error
        assert error.details["last_exception"] == "Network timeout"


class TestErrorHandlingPatterns:
    """Test common error handling patterns"""
    
    def test_exception_chaining(self):
        """Test chaining exceptions for context"""
        try:
            # Simulate an API call
            raise ConnectionError("Network unreachable")
        except ConnectionError as e:
            # Wrap in structured error
            structured = StructuredError(
                category=ErrorCategory.NETWORK,
                code="NET_001",
                message="Failed to connect to API",
                original_exception=e,
            )
            
            assert structured.original_exception is e
            assert isinstance(structured.original_exception, ConnectionError)
    
    def test_error_recovery_info(self):
        """Test errors with recovery information"""
        # Rate limit error with recovery info
        error = StructuredRateLimitError(
            retry_after=60,
            reset_at=datetime.utcnow(),
        )
        
        # Client can use retry_after to schedule retry
        assert error.retry_after == 60
        assert error.reset_at is not None
        
        # Circuit breaker error with state info
        cb_error = StructuredError(
            category=ErrorCategory.CIRCUIT_BREAKER,
            code="CB_OPEN",
            message="Circuit breaker is open",
            details={
                "service": "api_client",
                "failure_rate": 0.75,
                "state": "open",
                "will_retry_at": (datetime.utcnow()).isoformat(),
            }
        )
        
        assert cb_error.details["failure_rate"] == 0.75
        assert cb_error.details["state"] == "open"
    
    def test_error_categorization_for_handling(self):
        """Test using error categories for handling logic"""
        errors = [
            StructuredError(ErrorCategory.VALIDATION, "VAL_001", "Invalid input"),
            StructuredError(ErrorCategory.AUTHENTICATION, "AUTH_001", "Bad token"),
            StructuredError(ErrorCategory.RATE_LIMIT, "RATE_001", "Too fast"),
            StructuredError(ErrorCategory.INTERNAL, "INT_001", "Bug"),
        ]
        
        # Categorize errors for different handling
        retryable = []
        client_errors = []
        server_errors = []
        
        for error in errors:
            if error.category in [ErrorCategory.RATE_LIMIT, ErrorCategory.INTERNAL]:
                retryable.append(error)
            elif error.category in [ErrorCategory.VALIDATION, ErrorCategory.AUTHENTICATION]:
                client_errors.append(error)
            else:
                server_errors.append(error)
        
        assert len(retryable) == 2
        assert len(client_errors) == 2
        assert len(server_errors) == 0