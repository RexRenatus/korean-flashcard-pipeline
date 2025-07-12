"""
Demo script showing the enhanced retry system in action
"""

import asyncio
import random
from datetime import datetime

from flashcard_pipeline.utils.retry import RetryConfig, retry_async
from flashcard_pipeline.exceptions import (
    StructuredAPIError,
    StructuredRateLimitError,
    NetworkError,
)


# Simulate an unreliable API
class UnreliableAPI:
    def __init__(self):
        self.call_count = 0
        self.failure_rate = 0.7  # 70% failure rate
    
    @retry_async(RetryConfig(
        max_attempts=5,
        initial_delay=1.0,
        max_delay=10.0,
        exponential_base=2.0,
        jitter=True,
        retry_on=(NetworkError, StructuredAPIError)
    ))
    async def make_request(self, endpoint: str):
        """Simulate an API call that might fail"""
        self.call_count += 1
        print(f"\n[Attempt {self.call_count}] Calling {endpoint}...")
        
        # Simulate network delay
        await asyncio.sleep(0.5)
        
        # Randomly fail
        if random.random() < self.failure_rate:
            error_type = random.choice(["network", "server", "rate_limit"])
            
            if error_type == "network":
                print(f"  ❌ Network error!")
                raise NetworkError("Connection timeout")
            elif error_type == "server":
                print(f"  ❌ Server error!")
                raise StructuredAPIError(
                    status_code=500,
                    message="Internal server error"
                )
            else:
                print(f"  ❌ Rate limited!")
                raise StructuredRateLimitError(
                    message="Too many requests",
                    retry_after=2.0
                )
        
        # Success!
        print(f"  ✅ Success!")
        return {
            "status": "success",
            "data": f"Response from {endpoint}",
            "timestamp": datetime.utcnow().isoformat()
        }


async def demo_retry_with_jitter():
    """Demonstrate retry with exponential backoff and jitter"""
    print("=== Retry Demo with Exponential Backoff and Jitter ===")
    
    api = UnreliableAPI()
    
    try:
        result = await api.make_request("/api/v1/flashcards")
        print(f"\nFinal result: {result}")
        print(f"Total attempts: {api.call_count}")
    except Exception as e:
        print(f"\nFailed after {api.call_count} attempts: {type(e).__name__}: {e}")


async def demo_structured_errors():
    """Demonstrate structured error handling"""
    print("\n\n=== Structured Error Handling Demo ===")
    
    @retry_async(RetryConfig(max_attempts=3, initial_delay=0.5))
    async def api_call_with_structured_errors():
        # This will always fail to demonstrate error structure
        raise StructuredAPIError(
            status_code=503,
            message="Service temporarily unavailable",
            response={
                "error": "maintenance_mode",
                "retry_after": 3600,
                "maintenance_window": "2 hours"
            },
            retry_after=3600
        )
    
    try:
        await api_call_with_structured_errors()
    except Exception as e:
        if hasattr(e, 'last_exception') and hasattr(e.last_exception, 'to_dict'):
            print("\nStructured error details:")
            import json
            print(json.dumps(e.last_exception.to_dict(), indent=2))


async def demo_custom_retry_config():
    """Demonstrate custom retry configuration"""
    print("\n\n=== Custom Retry Configuration Demo ===")
    
    # Fast retries for demos
    fast_retry = RetryConfig(
        max_attempts=3,
        initial_delay=0.1,
        max_delay=1.0,
        exponential_base=2.0,
        jitter=False  # No jitter for predictable timing
    )
    
    attempt_times = []
    
    @retry_async(fast_retry)
    async def timed_function():
        attempt_times.append(datetime.utcnow())
        if len(attempt_times) < 3:
            raise ValueError("Not yet!")
        return "Success!"
    
    start = datetime.utcnow()
    result = await timed_function()
    end = datetime.utcnow()
    
    print(f"Result: {result}")
    print(f"Total time: {(end - start).total_seconds():.2f} seconds")
    print("\nAttempt timeline:")
    for i, t in enumerate(attempt_times):
        if i == 0:
            print(f"  Attempt {i+1}: 0.00s")
        else:
            delay = (t - attempt_times[i-1]).total_seconds()
            print(f"  Attempt {i+1}: +{delay:.2f}s")


async def main():
    """Run all demos"""
    await demo_retry_with_jitter()
    await demo_structured_errors()
    await demo_custom_retry_config()


if __name__ == "__main__":
    print("Enhanced Retry System Demo")
    print("=" * 50)
    asyncio.run(main())