"""
Unit tests for the comprehensive error handling system
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from flashcard_pipeline.error_handler import (
    ErrorHandler, ErrorCategory, ErrorSeverity, ErrorContext,
    ErrorAnalyzer, AutoResolver, ErrorPatternMatcher,
    RetryStrategy, RateLimitRecoveryStrategy, handle_errors
)
from flashcard_pipeline.exceptions import (
    ApiError, RateLimitError, ValidationError, NetworkError,
    DatabaseError, CacheError, CircuitBreakerError
)


class TestErrorCategorization:
    """Test error categorization and severity determination"""
    
    @pytest.fixture
    def error_handler(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            handler = ErrorHandler(f.name)
            yield handler
            os.unlink(f.name)
    
    def test_categorize_api_errors(self, error_handler):
        """Test categorization of API errors"""
        api_error = ApiError("API failed", status_code=500)
        category = error_handler._categorize_error(api_error)
        assert category == ErrorCategory.API
        
        rate_limit = RateLimitError("Rate limited", retry_after=60)
        category = error_handler._categorize_error(rate_limit)
        assert category == ErrorCategory.API
    
    def test_categorize_network_errors(self, error_handler):
        """Test categorization of network errors"""
        network_error = NetworkError("Connection failed")
        category = error_handler._categorize_error(network_error)
        assert category == ErrorCategory.NETWORK
    
    def test_categorize_validation_errors(self, error_handler):
        """Test categorization of validation errors"""
        validation_error = ValidationError("Invalid data", field="korean")
        category = error_handler._categorize_error(validation_error)
        assert category == ErrorCategory.VALIDATION
    
    def test_categorize_unknown_errors(self, error_handler):
        """Test categorization of unknown errors"""
        unknown_error = Exception("Something went wrong")
        category = error_handler._categorize_error(unknown_error)
        assert category == ErrorCategory.UNKNOWN
    
    def test_determine_severity(self, error_handler):
        """Test severity determination"""
        # Critical errors
        auth_error = ApiError("Unauthorized", status_code=401)
        assert error_handler._determine_severity(auth_error) == ErrorSeverity.CRITICAL
        
        # High severity
        network_error = NetworkError("Connection lost")
        assert error_handler._determine_severity(network_error) == ErrorSeverity.HIGH
        
        # Medium severity
        rate_limit = RateLimitError("Rate limited")
        assert error_handler._determine_severity(rate_limit) == ErrorSeverity.MEDIUM
        
        # Low severity
        validation_error = ValidationError("Invalid format")
        assert error_handler._determine_severity(validation_error) == ErrorSeverity.LOW


class TestErrorContext:
    """Test error context capture"""
    
    @pytest.fixture
    def error_handler(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            handler = ErrorHandler(f.name)
            yield handler
            os.unlink(f.name)
    
    def test_capture_error_context(self, error_handler):
        """Test capturing full error context"""
        error = ValidationError("Invalid input", field="test_field")
        context = error_handler.capture_error(
            error,
            component="TestComponent",
            operation="test_operation",
            input_data={"test": "data"},
            user_id="user123",
            session_id="session456"
        )
        
        assert context.error_type == "ValidationError"
        assert context.error_message == "Invalid input"
        assert context.component == "TestComponent"
        assert context.operation == "test_operation"
        assert context.input_data == {"test": "data"}
        assert context.user_id == "user123"
        assert context.session_id == "session456"
        assert context.category == ErrorCategory.VALIDATION
        assert context.severity == ErrorSeverity.LOW
    
    def test_error_context_manager(self, error_handler):
        """Test error context manager"""
        with pytest.raises(ValidationError):
            with error_handler.error_context(
                component="TestComponent",
                operation="test_operation",
                input_data={"test": "data"}
            ):
                raise ValidationError("Test error")
        
        # Check that error was logged
        errors = error_handler.db_manager.get_errors_since(
            datetime.now() - timedelta(minutes=1)
        )
        assert len(errors) == 1
        assert errors[0].error_message == "Test error"


class TestErrorPatternMatcher:
    """Test error pattern matching"""
    
    def test_match_api_key_errors(self):
        """Test matching API key errors"""
        matcher = ErrorPatternMatcher()
        
        # Test various API key error messages
        messages = [
            "Invalid API key provided",
            "Unauthorized: Bad API key",
            "401 Unauthorized"
        ]
        
        for msg in messages:
            match = matcher.match_error(msg)
            assert match is not None
            assert match["category"] == ErrorCategory.API
            assert match["severity"] == ErrorSeverity.CRITICAL
    
    def test_match_network_errors(self):
        """Test matching network errors"""
        matcher = ErrorPatternMatcher()
        
        messages = [
            "Connection refused",
            "Request timeout",
            "Host unreachable"
        ]
        
        for msg in messages:
            match = matcher.match_error(msg)
            assert match is not None
            assert match["category"] == ErrorCategory.NETWORK
    
    def test_match_rate_limit_errors(self):
        """Test matching rate limit errors"""
        matcher = ErrorPatternMatcher()
        
        messages = [
            "Rate limit exceeded",
            "429 Too Many Requests",
            "Too many requests"
        ]
        
        for msg in messages:
            match = matcher.match_error(msg)
            assert match is not None
            assert match["category"] == ErrorCategory.API


class TestRecoveryStrategies:
    """Test error recovery strategies"""
    
    @pytest.mark.asyncio
    async def test_retry_strategy(self):
        """Test retry recovery strategy"""
        strategy = RetryStrategy(max_retries=3, base_delay=0.1)
        
        context = ErrorContext(
            error_id="test",
            timestamp=datetime.now(),
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.HIGH,
            error_type="NetworkError",
            error_message="Connection failed",
            stack_trace="",
            component="test",
            operation="test",
            retry_count=0
        )
        
        # Should be able to handle network errors
        assert strategy.can_handle(context)
        
        # Test retry with delay
        start = datetime.now()
        result = await strategy.attempt_recovery(context)
        end = datetime.now()
        
        assert result is True
        assert (end - start).total_seconds() >= 0.1
    
    @pytest.mark.asyncio
    async def test_rate_limit_recovery(self):
        """Test rate limit recovery strategy"""
        strategy = RateLimitRecoveryStrategy()
        
        context = ErrorContext(
            error_id="test",
            timestamp=datetime.now(),
            category=ErrorCategory.API,
            severity=ErrorSeverity.MEDIUM,
            error_type="RateLimitError",
            error_message="Rate limit exceeded",
            stack_trace="",
            component="test",
            operation="test",
            additional_info={"retry_after": 0.1}
        )
        
        assert strategy.can_handle(context)
        
        start = datetime.now()
        result = await strategy.attempt_recovery(context)
        end = datetime.now()
        
        assert result is True
        assert (end - start).total_seconds() >= 0.1
    
    @pytest.mark.asyncio
    async def test_cache_failover_strategy(self):
        """Test cache failover strategy"""
        from flashcard_pipeline.error_handler import CacheFailoverStrategy
        
        strategy = CacheFailoverStrategy()
        
        context = ErrorContext(
            error_id="test",
            timestamp=datetime.now(),
            category=ErrorCategory.CACHE,
            severity=ErrorSeverity.MEDIUM,
            error_type="CacheError",
            error_message="Cache unavailable",
            stack_trace="",
            component="test",
            operation="test"
        )
        
        assert strategy.can_handle(context)
        
        result = await strategy.attempt_recovery(context)
        assert result is True
        assert context.additional_info.get('cache_disabled') is True


class TestErrorAnalyzer:
    """Test error analysis functionality"""
    
    @pytest.fixture
    def analyzer(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            handler = ErrorHandler(f.name)
            
            # Add some test errors
            for i in range(10):
                error = ErrorContext(
                    error_id=f"error_{i}",
                    timestamp=datetime.now(),
                    category=ErrorCategory.API if i < 5 else ErrorCategory.NETWORK,
                    severity=ErrorSeverity.HIGH if i < 3 else ErrorSeverity.MEDIUM,
                    error_type="TestError",
                    error_message="Test error message",
                    stack_trace="",
                    component="TestComponent",
                    operation="test_op",
                    recovery_attempted=i % 2 == 0,
                    recovery_successful=i % 4 == 0
                )
                handler.db_manager.log_error(error)
            
            yield handler.analyzer
            os.unlink(f.name)
    
    def test_analyze_recent_errors(self, analyzer):
        """Test error analysis"""
        analysis = analyzer.analyze_recent_errors(hours=24)
        
        assert analysis["total_errors"] == 10
        assert analysis["by_category"]["API"] == 5
        assert analysis["by_category"]["NETWORK"] == 5
        assert analysis["by_severity"]["HIGH"] == 3
        assert analysis["by_severity"]["MEDIUM"] == 7
        assert analysis["recovery_success_rate"] == 0.4  # 2/5
    
    def test_identify_error_clusters(self, analyzer):
        """Test error clustering"""
        clusters = analyzer.identify_error_clusters(hours=24)
        
        # Should have at least one cluster
        assert len(clusters) >= 1
        
        # Check cluster structure
        for cluster in clusters:
            assert "signature" in cluster
            assert "count" in cluster
            assert "first_occurrence" in cluster
            assert "last_occurrence" in cluster


class TestAutoResolver:
    """Test automatic error resolution"""
    
    @pytest.mark.asyncio
    async def test_identify_issue_types(self):
        """Test issue type identification"""
        resolver = AutoResolver()
        
        # API key issues
        context = ErrorContext(
            error_id="test",
            timestamp=datetime.now(),
            category=ErrorCategory.API,
            severity=ErrorSeverity.CRITICAL,
            error_type="ApiError",
            error_message="Invalid API key",
            stack_trace="",
            component="test",
            operation="test"
        )
        
        issue_type = resolver._identify_issue(context)
        assert issue_type == "invalid_api_key"
        
        # Cache corruption
        context.error_message = "Cache corrupted"
        issue_type = resolver._identify_issue(context)
        assert issue_type == "cache_corruption"
        
        # Database lock
        context.error_message = "Database is locked"
        issue_type = resolver._identify_issue(context)
        assert issue_type == "database_locked"


class TestErrorHandlerDecorator:
    """Test the error handler decorator"""
    
    def test_decorator_with_handler(self):
        """Test decorator when error handler is available"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            error_handler = ErrorHandler(f.name)
            
            class TestClass:
                def __init__(self):
                    self.error_handler = error_handler
                
                @handle_errors("TestClass")
                def risky_method(self, should_fail=False):
                    if should_fail:
                        raise ValidationError("Test error")
                    return "success"
            
            obj = TestClass()
            
            # Test successful execution
            result = obj.risky_method(should_fail=False)
            assert result == "success"
            
            # Test error handling
            with pytest.raises(ValidationError):
                obj.risky_method(should_fail=True)
            
            # Check that error was logged
            errors = error_handler.db_manager.get_errors_since(
                datetime.now() - timedelta(minutes=1)
            )
            assert len(errors) == 1
            assert errors[0].component == "TestClass"
            assert errors[0].operation == "risky_method"
            
            os.unlink(f.name)
    
    def test_decorator_without_handler(self):
        """Test decorator when no error handler is available"""
        class TestClass:
            @handle_errors("TestClass")
            def method(self):
                return "success"
        
        obj = TestClass()
        result = obj.method()
        assert result == "success"


class TestErrorDatabaseManager:
    """Test error database operations"""
    
    @pytest.fixture
    def db_manager(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            from flashcard_pipeline.error_handler import ErrorDatabaseManager
            manager = ErrorDatabaseManager(f.name)
            yield manager
            os.unlink(f.name)
    
    def test_log_and_retrieve_errors(self, db_manager):
        """Test logging and retrieving errors"""
        # Create test error
        error = ErrorContext(
            error_id="test_error_1",
            timestamp=datetime.now(),
            category=ErrorCategory.API,
            severity=ErrorSeverity.HIGH,
            error_type="ApiError",
            error_message="Test API error",
            stack_trace="Traceback...",
            component="TestComponent",
            operation="test_operation",
            input_data={"test": "data"},
            user_id="user123"
        )
        
        # Log error
        db_manager.log_error(error)
        
        # Retrieve errors
        errors = db_manager.get_errors_since(
            datetime.now() - timedelta(minutes=1)
        )
        
        assert len(errors) == 1
        retrieved = errors[0]
        assert retrieved.error_id == "test_error_1"
        assert retrieved.category == ErrorCategory.API
        assert retrieved.severity == ErrorSeverity.HIGH
        assert retrieved.component == "TestComponent"
        assert retrieved.input_data == {"test": "data"}


@pytest.mark.integration
class TestErrorHandlerIntegration:
    """Integration tests for the complete error handling system"""
    
    @pytest.mark.asyncio
    async def test_full_error_handling_flow(self):
        """Test complete error handling flow with recovery"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            handler = ErrorHandler(f.name)
            
            # Simulate an error that can be recovered
            try:
                with handler.error_context(
                    component="TestComponent",
                    operation="test_operation"
                ):
                    raise RateLimitError("Rate limit exceeded", retry_after=0.1)
            except RateLimitError:
                pass
            
            # Wait a bit for async recovery
            await asyncio.sleep(0.2)
            
            # Check error was logged
            errors = handler.db_manager.get_errors_since(
                datetime.now() - timedelta(minutes=1)
            )
            assert len(errors) >= 1
            
            # Get analysis
            analysis = handler.get_error_analysis(hours=1)
            assert analysis["total_errors"] >= 1
            assert "API" in analysis["by_category"]
            
            os.unlink(f.name)