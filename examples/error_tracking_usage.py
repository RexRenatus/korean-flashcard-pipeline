"""Examples of using the enhanced error tracking system"""

import asyncio
import random
import logging
from datetime import timedelta

from flashcard_pipeline.errors import (
    # Error types
    NetworkError,
    RateLimitError,
    ValidationError,
    DatabaseError,
    CacheError,
    QuotaExceededError,
    ProcessingError,
    FallbackUsedError,
    
    # Base classes
    ErrorCategory,
    ErrorSeverity,
    with_error_handling,
    async_with_error_handling,
    
    # Recovery
    RetryPolicy,
    FallbackPolicy,
    recover_with_retry,
    recover_with_fallback,
    get_recovery_manager,
    
    # Analytics
    ErrorAnalytics,
    get_error_collector,
    initialize_error_collector,
)

from flashcard_pipeline.telemetry import init_telemetry, create_span
from flashcard_pipeline.database.database_manager_v2 import DatabaseManager
from flashcard_pipeline.cache.cache_manager_v2 import CacheManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def basic_error_handling_example():
    """Basic example of structured error handling"""
    print("\n=== Basic Error Handling Example ===")
    
    # Example 1: Creating structured errors
    try:
        # Simulate a network error
        raise NetworkError(
            "Failed to connect to API",
            status_code=503,
            url="https://api.example.com/endpoint"
        )
    except NetworkError as e:
        print(f"Caught network error: {e}")
        print(f"  Category: {e.category.value}")
        print(f"  Severity: {e.severity.value}")
        print(f"  Recoverable: {e.recoverable}")
        print(f"  User message: {e.get_user_message()}")
        print(f"  Error ID: {e.metadata.error_id}")
        print(f"  Fingerprint: {e.metadata.fingerprint}")
    
    # Example 2: Rate limit error with retry information
    try:
        raise RateLimitError(
            "API rate limit exceeded",
            retry_after=60.0,
            limit=100,
            window="1m"
        )
    except RateLimitError as e:
        print(f"\nCaught rate limit error: {e}")
        print(f"  Retry after: {e.get_retry_after()} seconds")
        print(f"  Should retry: {e.should_retry()}")
    
    # Example 3: Validation error with field information
    try:
        raise ValidationError(
            "Invalid email format",
            field="email",
            value="not-an-email",
            constraints={"format": "email", "required": True}
        )
    except ValidationError as e:
        print(f"\nCaught validation error: {e}")
        print(f"  Field: {e.metadata.extra.get('field')}")
        print(f"  Invalid value: {e.metadata.extra.get('invalid_value')}")
        print(f"  User message: {e.get_user_message()}")


async def error_context_example():
    """Example of adding context to errors"""
    print("\n\n=== Error Context Example ===")
    
    try:
        # Create error with context
        error = ProcessingError(
            "Failed to process flashcard",
            stage="translation",
            item_id="flashcard_123"
        )
        
        # Add more context
        error.with_context(
            model="claude-3-haiku",
            attempt=3,
            processing_time=5.2
        )
        
        # Add user context
        error.with_user_context(
            user_id="user_456",
            session_id="session_789"
        )
        
        # Add tags
        error.with_tags("critical_path", "api_failure", "retry_exhausted")
        
        raise error
        
    except ProcessingError as e:
        print(f"Error with full context: {e}")
        print(f"  Metadata: {e.metadata.to_dict()}")


async def automatic_recovery_example():
    """Example of automatic error recovery"""
    print("\n\n=== Automatic Recovery Example ===")
    
    # Initialize error collector
    collector = initialize_error_collector()
    await collector.start()
    
    # Example 1: Retry recovery
    print("\n1. Retry Recovery:")
    
    async def flaky_api_call():
        """Simulates a flaky API that fails 60% of the time"""
        if random.random() < 0.6:
            raise NetworkError("Connection timeout", status_code=504)
        return {"status": "success", "data": "API response"}
    
    # Use recovery with retry
    try:
        result = await recover_with_retry(
            flaky_api_call,
            retry_policy=RetryPolicy(
                max_attempts=5,
                initial_delay=0.1,
                max_delay=2.0
            )
        )
        print(f"  Success after retries: {result}")
    except Exception as e:
        print(f"  Failed after all retries: {e}")
    
    # Example 2: Fallback recovery
    print("\n2. Fallback Recovery:")
    
    async def unreliable_service():
        """Always fails to simulate service outage"""
        raise DatabaseError("Database connection lost")
    
    # Use recovery with fallback
    result = await recover_with_fallback(
        unreliable_service,
        fallback_value={"status": "degraded", "data": "cached_response"}
    )
    print(f"  Used fallback: {result}")
    
    # Example 3: Recovery manager
    print("\n3. Recovery Manager:")
    
    recovery_manager = get_recovery_manager()
    
    async def critical_operation():
        raise QuotaExceededError(
            "Monthly API quota exceeded",
            quota_type="api_calls",
            current_usage=10000,
            quota_limit=10000
        )
    
    try:
        # Recovery manager will determine strategy based on error type
        result = await recovery_manager.recover(
            QuotaExceededError("Quota exceeded"),
            function=critical_operation,
            context={
                "cache": CacheManager(),
                "cache_key": "critical_operation_result"
            }
        )
    except Exception as e:
        print(f"  Recovery failed: {e}")
        print(f"  Error category: {e.category.value}")
        print(f"  Recovery strategy attempted: {recovery_manager.get_strategy(e).value}")


async def error_decorator_example():
    """Example of using error handling decorators"""
    print("\n\n=== Error Decorator Example ===")
    
    # Example 1: Basic error wrapping
    @with_error_handling(
        category=ErrorCategory.BUSINESS,
        severity=ErrorSeverity.MEDIUM,
        recoverable=True
    )
    def process_data(data: dict) -> dict:
        """Process data with automatic error wrapping"""
        if not data.get("required_field"):
            raise ValueError("Missing required field")
        return {"processed": True, **data}
    
    try:
        result = process_data({"optional_field": "value"})
    except Exception as e:
        print(f"Wrapped error: {e}")
        print(f"  Original cause: {e.cause}")
    
    # Example 2: Async error handling
    @async_with_error_handling(
        category=ErrorCategory.SYSTEM,
        severity=ErrorSeverity.HIGH
    )
    async def fetch_external_data(url: str) -> dict:
        """Fetch data with error handling"""
        if "invalid" in url:
            raise ConnectionError("Invalid URL")
        return {"url": url, "data": "fetched"}
    
    try:
        result = await fetch_external_data("https://invalid.example.com")
    except Exception as e:
        print(f"\nAsync wrapped error: {e}")


async def error_analytics_example():
    """Example of error analytics and reporting"""
    print("\n\n=== Error Analytics Example ===")
    
    # Set up database for analytics
    db = DatabaseManager(":memory:")
    await db.initialize()
    
    # Initialize collector with database
    collector = initialize_error_collector(database=db, enable_persistence=True)
    await collector.start()
    
    # Generate some test errors
    print("Generating test errors...")
    
    error_types = [
        (NetworkError, {"status_code": 500}),
        (RateLimitError, {"retry_after": 60}),
        (ValidationError, {"field": "email"}),
        (DatabaseError, {"query": "SELECT * FROM users"}),
        (CacheError, {"cache_key": "user:123"}),
    ]
    
    for i in range(50):
        error_class, extra = random.choice(error_types)
        try:
            raise error_class(f"Test error {i}", **extra)
        except Exception as e:
            collector.collect(e)
    
    # Let errors be processed
    await asyncio.sleep(0.1)
    
    # Create analytics instance
    analytics = ErrorAnalytics(collector, db)
    
    # Get error metrics
    print("\n1. Error Metrics (last hour):")
    metrics = await analytics.get_error_metrics(timedelta(hours=1))
    print(f"  Total errors: {metrics.total_errors}")
    print(f"  Unique errors: {metrics.unique_errors}")
    print(f"  Error rate: {metrics.error_rate:.2f} per minute")
    print(f"  By category: {dict(metrics.errors_by_category)}")
    print(f"  By severity: {dict(metrics.errors_by_severity)}")
    
    # Get error trends
    print("\n2. Error Trends:")
    trends = await analytics.get_error_trends(
        timedelta(hours=1),
        granularity="hour"
    )
    for trend in trends[:5]:
        print(f"  {trend.timestamp}: {trend.count} errors")
    
    # Get impact analysis
    print("\n3. Top Impact Errors:")
    impacts = await analytics.get_error_impact_analysis(limit=5)
    for impact in impacts:
        print(f"  {impact.error_fingerprint[:8]}...")
        print(f"    Occurrences: {impact.total_occurrences}")
        print(f"    Severity: {impact.severity.value}")
        print(f"    Impact score: {impact.estimated_impact_score:.2f}")
    
    # Generate report
    print("\n4. Error Report Summary:")
    report = await analytics.generate_error_report(timedelta(hours=1))
    print(f"  Generated at: {report['generated_at']}")
    print(f"  Summary: {report['summary']}")
    if report.get('alerts'):
        print(f"  Alerts: {report['alerts']}")
    
    await collector.stop()


async def circuit_breaker_integration_example():
    """Example of error tracking with circuit breaker"""
    print("\n\n=== Circuit Breaker Integration Example ===")
    
    from flashcard_pipeline.circuit_breaker_v2 import EnhancedCircuitBreaker
    from flashcard_pipeline.errors.recovery import CircuitBreakerHandler
    
    # Create circuit breaker
    circuit_breaker = EnhancedCircuitBreaker(
        name="external_api",
        failure_threshold=3,
        recovery_timeout=5.0,
        expected_exception_types=[NetworkError]
    )
    
    # Set up recovery with circuit breaker
    recovery_manager = get_recovery_manager()
    recovery_manager.set_handler(
        RecoveryStrategy.CIRCUIT_BREAK,
        CircuitBreakerHandler(circuit_breaker)
    )
    
    async def external_api_call():
        """Simulates external API that fails"""
        if random.random() < 0.8:  # 80% failure rate
            raise NetworkError("API unavailable", status_code=503)
        return {"status": "ok"}
    
    # Make multiple calls
    print("Making API calls through circuit breaker:")
    for i in range(10):
        try:
            with create_span(f"api_call_{i}"):
                result = await circuit_breaker.call_async(external_api_call)
                print(f"  Call {i}: Success - {result}")
        except Exception as e:
            print(f"  Call {i}: Failed - {e}")
            print(f"    Circuit state: {circuit_breaker.state.value}")
        
        await asyncio.sleep(0.5)


async def real_world_scenario():
    """Real-world scenario: Flashcard processing with error handling"""
    print("\n\n=== Real-World Scenario: Flashcard Processing ===")
    
    # Initialize telemetry and error tracking
    init_telemetry(service_name="flashcard-processor", enable_console_export=False)
    
    db = DatabaseManager(":memory:")
    await db.initialize()
    
    collector = initialize_error_collector(database=db)
    await collector.start()
    
    # Flashcard processor with comprehensive error handling
    class FlashcardProcessor:
        def __init__(self):
            self.cache = CacheManager()
            self.processed_count = 0
            self.error_count = 0
        
        @async_with_error_handling(
            category=ErrorCategory.BUSINESS,
            severity=ErrorSeverity.HIGH
        )
        async def process_flashcard(self, word: str) -> dict:
            """Process a flashcard with full error handling"""
            with create_span("flashcard.process", attributes={"word": word}):
                # Stage 1: Validation
                try:
                    self._validate_input(word)
                except ValidationError as e:
                    self.error_count += 1
                    # Add context and re-raise
                    raise e.with_context(processing_stage="validation")
                
                # Stage 2: Check cache
                cache_key = f"flashcard:{word}"
                cached_result = await self.cache.get(cache_key)
                if cached_result:
                    return cached_result
                
                # Stage 3: API processing
                try:
                    result = await self._call_translation_api(word)
                except NetworkError as e:
                    self.error_count += 1
                    # Try fallback
                    fallback_result = await recover_with_fallback(
                        lambda: self._call_translation_api(word),
                        fallback_function=lambda: self._get_basic_translation(word)
                    )
                    
                    # Report degraded service
                    collector.collect(FallbackUsedError(
                        "Using basic translation due to API failure",
                        primary_service="translation_api",
                        fallback_service="basic_dictionary"
                    ))
                    
                    result = fallback_result
                
                # Stage 4: Save to cache
                await self.cache.set(cache_key, result, ttl=3600)
                
                self.processed_count += 1
                return result
        
        def _validate_input(self, word: str):
            """Validate input word"""
            if not word or len(word) > 100:
                raise ValidationError(
                    "Invalid word length",
                    field="word",
                    value=word,
                    constraints={"min_length": 1, "max_length": 100}
                )
        
        async def _call_translation_api(self, word: str) -> dict:
            """Simulate API call"""
            # Simulate various failure modes
            rand = random.random()
            if rand < 0.1:  # 10% network error
                raise NetworkError("Connection timeout", status_code=504)
            elif rand < 0.15:  # 5% rate limit
                raise RateLimitError("Rate limit exceeded", retry_after=30)
            elif rand < 0.2:  # 5% server error
                raise NetworkError("Internal server error", status_code=500)
            
            return {
                "word": word,
                "translation": f"Translation of {word}",
                "difficulty": random.randint(1, 5)
            }
        
        def _get_basic_translation(self, word: str) -> dict:
            """Basic fallback translation"""
            return {
                "word": word,
                "translation": f"Basic translation of {word}",
                "difficulty": 3,
                "degraded": True
            }
    
    # Process batch of flashcards
    processor = FlashcardProcessor()
    words = ["안녕하세요", "감사합니다", "사랑해요", "미안해요", "잘가요"]
    
    print("Processing flashcards with error handling:")
    
    for word in words:
        try:
            result = await processor.process_flashcard(word)
            print(f"  ✓ {word}: {result['translation']}")
            if result.get("degraded"):
                print(f"    ⚠️  Used fallback translation")
        except Exception as e:
            print(f"  ✗ {word}: Failed - {e}")
            print(f"    Category: {e.category.value}")
            print(f"    User message: {e.get_user_message()}")
    
    print(f"\nProcessing summary:")
    print(f"  Processed: {processor.processed_count}")
    print(f"  Errors: {processor.error_count}")
    
    # Get error analytics
    analytics = ErrorAnalytics(collector, db)
    metrics = await analytics.get_error_metrics(timedelta(minutes=5))
    
    print(f"\nError metrics:")
    print(f"  Total errors: {metrics.total_errors}")
    print(f"  Error types: {dict(metrics.errors_by_type)}")
    
    await collector.stop()


async def main():
    """Run all examples"""
    print("Enhanced Error Tracking Examples")
    print("=" * 50)
    
    await basic_error_handling_example()
    await error_context_example()
    await automatic_recovery_example()
    await error_decorator_example()
    await error_analytics_example()
    await circuit_breaker_integration_example()
    await real_world_scenario()
    
    print("\n" + "=" * 50)
    print("Examples completed!")
    print("\nKey takeaways:")
    print("1. Structured errors provide rich context for debugging")
    print("2. Automatic recovery reduces manual intervention")
    print("3. Error analytics help identify patterns and trends")
    print("4. Integration with telemetry provides full observability")
    print("5. Graceful degradation improves user experience")


if __name__ == "__main__":
    asyncio.run(main())