"""Unit tests for enhanced error tracking system"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from flashcard_pipeline.errors import (
    # Base
    FlashcardError,
    ErrorCategory,
    ErrorSeverity,
    ErrorMetadata,
    
    # Categories
    NetworkError,
    RateLimitError,
    ValidationError,
    DatabaseError,
    QuotaExceededError,
    FallbackUsedError,
    
    # Decorators
    with_error_handling,
    async_with_error_handling,
    
    # Collector
    ErrorCollector,
    ErrorRecord,
    initialize_error_collector,
    
    # Recovery
    RetryPolicy,
    FallbackPolicy,
    ErrorRecoveryManager,
    recover_with_retry,
    recover_with_fallback,
    
    # Analytics
    ErrorAnalytics,
    ErrorMetrics,
    ErrorImpact,
)

from flashcard_pipeline.database.database_manager_v2 import DatabaseManager


class TestErrorBase:
    """Test base error functionality"""
    
    def test_flashcard_error_creation(self):
        """Test creating FlashcardError"""
        error = FlashcardError(
            "Test error",
            category=ErrorCategory.TRANSIENT,
            severity=ErrorSeverity.HIGH,
            recoverable=True
        )
        
        assert str(error) == "Test error"
        assert error.category == ErrorCategory.TRANSIENT
        assert error.severity == ErrorSeverity.HIGH
        assert error.recoverable is True
        assert error.metadata.error_type == "FlashcardError"
        assert error.metadata.fingerprint != ""
    
    def test_error_metadata(self):
        """Test error metadata generation"""
        error = NetworkError("Connection failed", status_code=500)
        
        assert error.metadata.category == ErrorCategory.TRANSIENT
        assert error.metadata.severity == ErrorSeverity.MEDIUM
        assert error.metadata.error_message == "Connection failed"
        assert error.metadata.extra["status_code"] == 500
        assert error.metadata.timestamp > 0
    
    def test_error_context(self):
        """Test adding context to errors"""
        error = ValidationError("Invalid input")
        
        # Add context
        error.with_context(
            field="email",
            value="invalid@",
            validation_rule="email_format"
        )
        
        assert error.metadata.extra["field"] == "email"
        assert error.metadata.extra["value"] == "invalid@"
        assert error.metadata.extra["validation_rule"] == "email_format"
    
    def test_error_chaining(self):
        """Test error cause chaining"""
        original = ValueError("Original error")
        wrapped = FlashcardError("Wrapped error", cause=original)
        
        assert wrapped.cause is original
        assert wrapped.__cause__ is original
        assert "caused by: Original error" in str(wrapped)
    
    def test_user_messages(self):
        """Test user-friendly error messages"""
        errors = [
            (NetworkError("API down"), "Network connection issue"),
            (RateLimitError("Too many requests"), "Rate limit exceeded"),
            (ValidationError("Bad input"), "Invalid input"),
            (QuotaExceededError("Limit reached"), "quota has been exceeded"),
        ]
        
        for error, expected_phrase in errors:
            user_msg = error.get_user_message()
            assert expected_phrase in user_msg
            assert len(user_msg) > len(str(error))  # More descriptive


class TestErrorCategories:
    """Test specific error categories"""
    
    def test_network_error(self):
        """Test NetworkError specifics"""
        error = NetworkError(
            "Request failed",
            status_code=503,
            url="https://api.example.com"
        )
        
        assert error.category == ErrorCategory.TRANSIENT
        assert error.recoverable is True
        assert error.metadata.extra["status_code"] == 503
        assert error.metadata.extra["url"] == "https://api.example.com"
    
    def test_rate_limit_error(self):
        """Test RateLimitError specifics"""
        error = RateLimitError(
            "Rate limit hit",
            retry_after=60.0,
            limit=100,
            window="1m"
        )
        
        assert error.should_retry() is True
        assert error.get_retry_after() == 60.0
        assert "60 seconds" in error.get_user_message()
    
    def test_validation_error(self):
        """Test ValidationError specifics"""
        error = ValidationError(
            "Email invalid",
            field="email",
            value="not-an-email",
            constraints={"pattern": r"^[\w\.-]+@[\w\.-]+\.\w+$"}
        )
        
        assert error.category == ErrorCategory.PERMANENT
        assert error.recoverable is False
        assert error.metadata.extra["field"] == "email"
        assert "email" in error.get_user_message()
    
    def test_fallback_used_error(self):
        """Test FallbackUsedError specifics"""
        error = FallbackUsedError(
            "Using cache",
            primary_service="api",
            fallback_service="cache",
            degradation_reason="API timeout"
        )
        
        assert error.category == ErrorCategory.DEGRADED
        assert error.severity == ErrorSeverity.LOW
        assert "degraded mode" in error.get_user_message()


class TestErrorCollector:
    """Test error collection functionality"""
    
    @pytest.fixture
    def collector(self):
        """Create test collector"""
        return ErrorCollector(
            max_buffer_size=100,
            flush_interval=60.0,
            enable_persistence=False
        )
    
    def test_error_collection(self, collector):
        """Test collecting errors"""
        error = NetworkError("Test error")
        record = collector.collect(error)
        
        assert record.error_id == error.metadata.error_id
        assert record.fingerprint == error.metadata.fingerprint
        assert record.metadata == error.metadata
        
        # Check statistics
        stats = collector.get_statistics()
        assert stats["total_collected"] == 1
        assert stats["errors_by_category"][ErrorCategory.TRANSIENT.value] == 1
    
    def test_error_retrieval(self, collector):
        """Test retrieving collected errors"""
        # Collect multiple errors
        error1 = NetworkError("Error 1")
        error2 = ValidationError("Error 2")
        
        record1 = collector.collect(error1)
        record2 = collector.collect(error2)
        
        # Retrieve by ID
        retrieved = collector.get_error(record1.error_id)
        assert retrieved == record1
        
        # Retrieve by fingerprint
        similar = collector.get_errors_by_fingerprint(record1.fingerprint)
        assert record1 in similar
    
    def test_error_handlers(self, collector):
        """Test error handler callbacks"""
        handler_called = False
        received_record = None
        
        def test_handler(record: ErrorRecord):
            nonlocal handler_called, received_record
            handler_called = True
            received_record = record
        
        collector.add_handler(test_handler)
        
        error = DatabaseError("Test")
        collector.collect(error)
        
        assert handler_called is True
        assert received_record is not None
        assert received_record.metadata.error_type == "DatabaseError"
    
    @pytest.mark.asyncio
    async def test_error_persistence(self, tmp_path):
        """Test error persistence to database"""
        # Create database
        db = DatabaseManager(str(tmp_path / "test.db"))
        await db.initialize()
        
        # Create collector with persistence
        collector = initialize_error_collector(
            database=db,
            enable_persistence=True
        )
        await collector.start()
        
        # Collect errors
        for i in range(5):
            error = NetworkError(f"Error {i}")
            collector.collect(error)
        
        # Flush to database
        await collector.flush()
        
        # Verify persistence
        result = await db.execute("SELECT COUNT(*) FROM error_records")
        assert result.rows[0][0] == 5
        
        await collector.stop()


class TestErrorRecovery:
    """Test error recovery mechanisms"""
    
    def test_retry_policy(self):
        """Test retry policy configuration"""
        policy = RetryPolicy(
            max_attempts=3,
            initial_delay=1.0,
            exponential_base=2.0
        )
        
        # Test should retry
        error = NetworkError("Timeout")
        assert policy.should_retry(error, attempt=1) is True
        assert policy.should_retry(error, attempt=3) is True
        assert policy.should_retry(error, attempt=4) is False
        
        # Test delay calculation
        assert policy.get_delay(1) >= 0.5  # With jitter
        assert policy.get_delay(2) >= 1.0
        assert policy.get_delay(3) >= 2.0
    
    @pytest.mark.asyncio
    async def test_retry_recovery(self):
        """Test retry recovery handler"""
        attempt_count = 0
        
        async def flaky_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise NetworkError("Temporary failure")
            return "success"
        
        result = await recover_with_retry(
            flaky_function,
            retry_policy=RetryPolicy(max_attempts=5, initial_delay=0.01)
        )
        
        assert result == "success"
        assert attempt_count == 3
    
    @pytest.mark.asyncio
    async def test_fallback_recovery(self):
        """Test fallback recovery"""
        async def failing_function():
            raise DatabaseError("Connection lost")
        
        # Static fallback
        result = await recover_with_fallback(
            failing_function,
            fallback_value="default"
        )
        assert result == "default"
        
        # Dynamic fallback
        result = await recover_with_fallback(
            failing_function,
            fallback_function=lambda: "computed_fallback"
        )
        assert result == "computed_fallback"
    
    @pytest.mark.asyncio
    async def test_recovery_manager(self):
        """Test recovery manager"""
        manager = ErrorRecoveryManager()
        
        # Test strategy selection
        assert manager.get_strategy(NetworkError("test")) == RecoveryStrategy.RETRY
        assert manager.get_strategy(ValidationError("test")) == RecoveryStrategy.FAIL
        assert manager.get_strategy(FallbackUsedError("test")) == RecoveryStrategy.FALLBACK
        
        # Test recovery execution
        async def recoverable_function():
            raise NetworkError("Temporary issue")
        
        with pytest.raises(NetworkError):
            # Should fail after retries
            await manager.recover(
                NetworkError("test"),
                function=recoverable_function
            )


class TestErrorAnalytics:
    """Test error analytics functionality"""
    
    @pytest.fixture
    async def analytics_setup(self, tmp_path):
        """Set up analytics test environment"""
        db = DatabaseManager(str(tmp_path / "analytics.db"))
        await db.initialize()
        
        collector = initialize_error_collector(database=db)
        await collector.start()
        
        analytics = ErrorAnalytics(collector, db)
        
        yield collector, analytics, db
        
        await collector.stop()
    
    @pytest.mark.asyncio
    async def test_error_metrics(self, analytics_setup):
        """Test error metrics calculation"""
        collector, analytics, db = analytics_setup
        
        # Generate test errors
        for i in range(10):
            if i < 6:
                collector.collect(NetworkError(f"Network error {i}"))
            else:
                collector.collect(ValidationError(f"Validation error {i}"))
        
        await collector.flush()
        
        # Get metrics
        metrics = await analytics.get_error_metrics(timedelta(hours=1))
        
        assert metrics.total_errors == 10
        assert metrics.errors_by_category[ErrorCategory.TRANSIENT.value] == 6
        assert metrics.errors_by_category[ErrorCategory.PERMANENT.value] == 4
        assert metrics.error_rate > 0
    
    @pytest.mark.asyncio
    async def test_error_trends(self, analytics_setup):
        """Test error trend analysis"""
        collector, analytics, db = analytics_setup
        
        # Generate errors over time
        base_time = time.time()
        for i in range(5):
            error = NetworkError(f"Error {i}")
            error.metadata.timestamp = base_time + (i * 60)  # 1 minute apart
            collector.collect(error)
        
        await collector.flush()
        
        # Get trends
        trends = await analytics.get_error_trends(
            timedelta(hours=1),
            granularity="hour"
        )
        
        assert len(trends) > 0
        assert all(t.count > 0 for t in trends)
    
    @pytest.mark.asyncio
    async def test_impact_analysis(self, analytics_setup):
        """Test error impact analysis"""
        collector, analytics, db = analytics_setup
        
        # Generate errors with different impacts
        for i in range(20):
            error = NetworkError(f"Common error")
            if i < 10:
                error.with_user_context(f"user_{i}")
            collector.collect(error)
        
        await collector.flush()
        
        # Get impact analysis
        impacts = await analytics.get_error_impact_analysis(limit=5)
        
        assert len(impacts) > 0
        assert impacts[0].total_occurrences == 20
        assert impacts[0].affected_users == 10
        assert impacts[0].estimated_impact_score > 0


class TestErrorDecorators:
    """Test error handling decorators"""
    
    def test_sync_error_decorator(self):
        """Test synchronous error handling decorator"""
        @with_error_handling(
            category=ErrorCategory.BUSINESS,
            severity=ErrorSeverity.MEDIUM
        )
        def failing_function():
            raise ValueError("Test error")
        
        with pytest.raises(FlashcardError) as exc_info:
            failing_function()
        
        error = exc_info.value
        assert error.category == ErrorCategory.BUSINESS
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.cause.__class__.__name__ == "ValueError"
    
    @pytest.mark.asyncio
    async def test_async_error_decorator(self):
        """Test asynchronous error handling decorator"""
        @async_with_error_handling(
            category=ErrorCategory.SYSTEM,
            recoverable=True
        )
        async def async_failing_function():
            raise RuntimeError("Async error")
        
        with pytest.raises(FlashcardError) as exc_info:
            await async_failing_function()
        
        error = exc_info.value
        assert error.category == ErrorCategory.SYSTEM
        assert error.recoverable is True
        assert "async_failing_function" in str(error)


from flashcard_pipeline.errors.recovery import RecoveryStrategy