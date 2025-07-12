"""
Demonstration of the comprehensive error handling system

This script shows how to:
1. Set up error handling
2. Handle different types of errors
3. Analyze error patterns
4. Use automatic recovery
"""

import asyncio
import random
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.python.flashcard_pipeline.error_handler import (
    ErrorHandler, ErrorCategory, ErrorSeverity, handle_errors
)
from src.python.flashcard_pipeline.exceptions import (
    ApiError, RateLimitError, ValidationError, NetworkError,
    DatabaseError, CacheError, CircuitBreakerError
)


class FlashcardService:
    """Example service that uses error handling"""
    
    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler
        self.api_calls = 0
    
    @handle_errors("FlashcardService")
    async def generate_flashcard(self, word: str, simulate_error: str = None):
        """Generate a flashcard with error simulation"""
        self.api_calls += 1
        
        # Simulate different types of errors
        if simulate_error == "rate_limit":
            raise RateLimitError(
                "Rate limit exceeded",
                retry_after=2,
                reset_at=int((datetime.now() + timedelta(seconds=10)).timestamp())
            )
        elif simulate_error == "network":
            raise NetworkError("Connection timeout", original_error=TimeoutError())
        elif simulate_error == "validation":
            raise ValidationError("Invalid Korean word", field="korean", value=word)
        elif simulate_error == "api":
            raise ApiError("API service unavailable", status_code=503)
        elif simulate_error == "database":
            raise DatabaseError("Database connection lost")
        elif simulate_error == "cache":
            raise CacheError("Cache server unreachable")
        elif simulate_error == "circuit_breaker":
            raise CircuitBreakerError(
                "Circuit breaker open",
                service="openrouter",
                failure_count=10,
                threshold=5
            )
        elif simulate_error == "random":
            # Random error for testing
            if random.random() < 0.3:
                errors = ["rate_limit", "network", "validation"]
                return await self.generate_flashcard(word, random.choice(errors))
        
        # Simulate successful generation
        return {
            "word": word,
            "flashcard": {
                "front": f"What is '{word}' in Korean?",
                "back": f"[Korean translation of {word}]",
                "example": f"Example sentence with {word}"
            },
            "generated_at": datetime.now().isoformat()
        }
    
    @handle_errors("FlashcardService")
    async def batch_generate(self, words: list, error_rate: float = 0.2):
        """Generate flashcards for multiple words with controlled error rate"""
        results = []
        
        for i, word in enumerate(words):
            try:
                # Simulate errors based on error rate
                if random.random() < error_rate:
                    error_type = random.choice([
                        "rate_limit", "network", "validation", "api"
                    ])
                    result = await self.generate_flashcard(word, error_type)
                else:
                    result = await self.generate_flashcard(word)
                
                results.append({"word": word, "status": "success", "data": result})
            except Exception as e:
                results.append({
                    "word": word,
                    "status": "error",
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                
                # For rate limits, wait before continuing
                if isinstance(e, RateLimitError):
                    print(f"Rate limited. Waiting {e.retry_after}s...")
                    await asyncio.sleep(e.retry_after)
        
        return results


async def demonstrate_error_handling():
    """Demonstrate the error handling system"""
    
    # Initialize error handler
    error_handler = ErrorHandler("error_demo.db")
    service = FlashcardService(error_handler)
    
    print("=== Error Handling System Demo ===\n")
    
    # 1. Demonstrate different error types
    print("1. Testing different error types:")
    error_types = [
        "rate_limit", "network", "validation", "api",
        "database", "cache", "circuit_breaker"
    ]
    
    for error_type in error_types:
        try:
            print(f"\n   Testing {error_type} error...")
            result = await service.generate_flashcard("안녕하세요", error_type)
        except Exception as e:
            print(f"   ✗ {type(e).__name__}: {e}")
    
    # 2. Demonstrate batch processing with errors
    print("\n\n2. Batch processing with 30% error rate:")
    words = ["안녕하세요", "감사합니다", "사랑해요", "미안해요", "잘자요"]
    results = await service.batch_generate(words, error_rate=0.3)
    
    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = sum(1 for r in results if r["status"] == "error")
    
    print(f"\n   Results: {success_count} success, {error_count} errors")
    for result in results:
        if result["status"] == "error":
            print(f"   ✗ {result['word']}: {result['error_type']}")
        else:
            print(f"   ✓ {result['word']}: Generated successfully")
    
    # 3. Analyze errors
    print("\n\n3. Error Analysis:")
    analysis = error_handler.get_error_analysis(hours=1)
    
    print(f"\n   Total errors: {analysis['total_errors']}")
    print("\n   Errors by category:")
    for category, count in analysis['by_category'].items():
        print(f"   - {category}: {count}")
    
    print("\n   Errors by severity:")
    for severity, count in analysis['by_severity'].items():
        print(f"   - {severity}: {count}")
    
    if analysis['recovery_success_rate'] > 0:
        print(f"\n   Recovery success rate: {analysis['recovery_success_rate']:.1%}")
    
    if analysis['recommendations']:
        print("\n   Recommendations:")
        for rec in analysis['recommendations']:
            print(f"   - {rec}")
    
    # 4. Show error clusters
    print("\n\n4. Error Clusters:")
    clusters = error_handler.get_error_clusters(hours=1)
    
    if clusters:
        print(f"\n   Found {len(clusters)} error clusters:")
        for cluster in clusters[:3]:  # Show top 3
            print(f"\n   Cluster: {cluster['signature']}")
            print(f"   - Count: {cluster['count']}")
            print(f"   - Time span: {cluster['first_occurrence']} to {cluster['last_occurrence']}")
    else:
        print("\n   No significant error clusters found")
    
    # 5. Demonstrate recovery
    print("\n\n5. Testing automatic recovery:")
    
    # Test retry strategy
    print("\n   Testing network error with retry...")
    for attempt in range(3):
        try:
            if attempt < 2:
                result = await service.generate_flashcard("테스트", "network")
            else:
                result = await service.generate_flashcard("테스트")
                print(f"   ✓ Success on attempt {attempt + 1}")
                break
        except NetworkError:
            print(f"   ✗ Attempt {attempt + 1} failed")
            await asyncio.sleep(1)
    
    # 6. Show error details
    print("\n\n6. Recent Error Details:")
    recent_errors = error_handler.db_manager.get_errors_since(
        datetime.now() - timedelta(minutes=5)
    )
    
    if recent_errors:
        print(f"\n   Last 3 errors:")
        for error in recent_errors[:3]:
            print(f"\n   Error ID: {error.error_id}")
            print(f"   - Type: {error.error_type}")
            print(f"   - Category: {error.category.name}")
            print(f"   - Severity: {error.severity.name}")
            print(f"   - Component: {error.component}.{error.operation}")
            print(f"   - Message: {error.error_message}")
            if error.recovery_attempted:
                print(f"   - Recovery: {'Success' if error.recovery_successful else 'Failed'}")


async def demonstrate_custom_error_handling():
    """Demonstrate custom error handling patterns"""
    
    print("\n\n=== Custom Error Handling Patterns ===\n")
    
    error_handler = ErrorHandler("error_demo.db")
    
    # 1. Context manager pattern
    print("1. Using context manager for error capture:")
    
    try:
        with error_handler.error_context(
            component="DataProcessor",
            operation="validate_input",
            user_id="demo_user",
            input_data={"word": "test", "language": "ko"}
        ):
            # Simulate validation error
            if not "test".encode().isalpha():
                raise ValidationError("Word contains invalid characters", field="word")
    except ValidationError as e:
        print(f"   ✗ Validation error captured: {e}")
    
    # 2. Manual error capture
    print("\n2. Manual error capture with full context:")
    
    try:
        # Simulate an API error
        raise ApiError("Model overloaded", status_code=503, response_body='{"error": "overloaded"}')
    except ApiError as e:
        context = error_handler.capture_error(
            e,
            component="APIClient",
            operation="call_model",
            request_id="req_123",
            additional_info={
                "model": "claude-3-sonnet",
                "prompt_tokens": 1500,
                "retry_count": 2
            }
        )
        error_handler.handle_error(context)
        print(f"   ✓ Error captured with ID: {context.error_id}")
    
    # 3. Async error handling
    print("\n3. Async operation with error handling:")
    
    async def async_operation():
        with error_handler.error_context(
            component="AsyncProcessor",
            operation="process_batch"
        ):
            await asyncio.sleep(0.1)
            # Simulate timeout
            raise TimeoutError("Operation timed out after 30s")
    
    try:
        await async_operation()
    except TimeoutError:
        print("   ✗ Timeout error handled")
    
    # Wait for any async recovery attempts
    await asyncio.sleep(1)


async def main():
    """Run all demonstrations"""
    try:
        await demonstrate_error_handling()
        await demonstrate_custom_error_handling()
        
        print("\n\n=== Demo Complete ===")
        print("\nError logs have been saved to 'error_demo.db'")
        print("You can query this database to analyze historical errors.")
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\nUnexpected error in demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())