"""
Demo showing integration of enhanced circuit breaker with retry system
"""

import asyncio
import random
import time
from datetime import datetime

from flashcard_pipeline.circuit_breaker_v2 import (
    EnhancedCircuitBreaker,
    CircuitState,
    exponential_break_duration,
)
from flashcard_pipeline.utils.retry import RetryConfig, retry_async
from flashcard_pipeline.exceptions import (
    CircuitBreakerError,
    NetworkError,
    StructuredAPIError,
)


class FlakeyAPIService:
    """Simulates a flaky API service for demonstration"""
    
    def __init__(self, failure_rate: float = 0.3):
        self.failure_rate = failure_rate
        self.call_count = 0
        self.is_down = False
        self.down_until = None
    
    async def make_request(self, endpoint: str) -> dict:
        """Simulate an API call that might fail"""
        self.call_count += 1
        
        # Simulate network delay
        await asyncio.sleep(0.1)
        
        # Check if service is down
        if self.is_down and time.time() < self.down_until:
            raise NetworkError(f"Service unavailable - down until {datetime.fromtimestamp(self.down_until).strftime('%H:%M:%S')}")
        
        # Random failures
        if random.random() < self.failure_rate:
            error_type = random.choice(["network", "server", "timeout"])
            
            if error_type == "network":
                raise NetworkError("Connection timeout")
            elif error_type == "server":
                raise StructuredAPIError(
                    status_code=500,
                    message="Internal server error"
                )
            else:
                raise TimeoutError("Request timeout")
        
        # Simulate service going down after too many requests
        if self.call_count > 0 and self.call_count % 10 == 0:
            print(f"  ⚠️  Service going down for maintenance (30 seconds)")
            self.is_down = True
            self.down_until = time.time() + 30
        
        return {
            "endpoint": endpoint,
            "status": "success",
            "data": f"Response #{self.call_count}",
            "timestamp": datetime.now().isoformat()
        }


class ResilientAPIClient:
    """API client with circuit breaker and retry logic"""
    
    def __init__(self):
        # Configure circuit breaker
        self.circuit_breaker = EnhancedCircuitBreaker(
            failure_threshold=0.5,      # Open at 50% failure rate
            min_throughput=3,           # Need at least 3 calls
            sampling_duration=30.0,     # 30 second window
            break_duration_generator=exponential_break_duration,
            expected_exception=(NetworkError, StructuredAPIError, TimeoutError),
            enable_monitoring=True,
            enable_manual_control=True,
            name="api_service"
        )
        
        # Configure retry
        self.retry_config = RetryConfig(
            max_attempts=3,
            initial_delay=0.5,
            max_delay=5.0,
            exponential_base=2.0,
            jitter=True,
            retry_on=(NetworkError, TimeoutError)  # Don't retry on server errors
        )
        
        # API service
        self.api = FlakeyAPIService(failure_rate=0.4)
    
    @retry_async()  # Uses default retry config from decorator
    async def call_with_circuit_breaker(self, endpoint: str) -> dict:
        """Make API call with circuit breaker protection"""
        # Circuit breaker will raise CircuitBreakerError if open
        return await self.circuit_breaker.call(
            self.api.make_request,
            endpoint
        )
    
    async def call_with_custom_retry(self, endpoint: str) -> dict:
        """Make API call with custom retry config"""
        @retry_async(self.retry_config)
        async def wrapped_call():
            return await self.circuit_breaker.call(
                self.api.make_request,
                endpoint
            )
        
        return await wrapped_call()
    
    def get_health_status(self) -> dict:
        """Get health status of the client"""
        cb_stats = self.circuit_breaker.get_stats()
        
        return {
            "circuit_breaker": {
                "state": cb_stats["state"],
                "success_rate": cb_stats.get("success_rate", "N/A"),
                "time_in_state": cb_stats.get("time_in_state", 0),
                "consecutive_failures": cb_stats.get("consecutive_failures", 0),
            },
            "api_calls": {
                "total": self.api.call_count,
                "is_down": self.api.is_down,
            }
        }


async def demo_basic_integration():
    """Demonstrate basic circuit breaker + retry integration"""
    print("=== Basic Circuit Breaker + Retry Integration ===\n")
    
    client = ResilientAPIClient()
    
    # Make several calls
    for i in range(10):
        try:
            print(f"Call {i+1}: ", end="")
            result = await client.call_with_circuit_breaker(f"/api/v1/data/{i}")
            print(f"✅ Success: {result['data']}")
        except CircuitBreakerError as e:
            print(f"🚫 Circuit breaker open: {e}")
        except Exception as e:
            print(f"❌ Failed after retries: {type(e).__name__}: {e}")
        
        # Small delay between calls
        await asyncio.sleep(0.5)
    
    # Show final status
    print("\nFinal health status:")
    health = client.get_health_status()
    print(f"  Circuit state: {health['circuit_breaker']['state']}")
    print(f"  Success rate: {health['circuit_breaker']['success_rate']}")
    print(f"  Total API calls: {health['api_calls']['total']}")


async def demo_manual_control():
    """Demonstrate manual circuit breaker control"""
    print("\n\n=== Manual Circuit Breaker Control ===\n")
    
    client = ResilientAPIClient()
    control = client.circuit_breaker.manual_control
    
    # Make some successful calls
    print("Making normal calls...")
    for i in range(3):
        try:
            result = await client.call_with_circuit_breaker(f"/api/v1/users/{i}")
            print(f"✅ Call {i+1} succeeded")
        except Exception as e:
            print(f"❌ Call {i+1} failed: {e}")
    
    # Manually isolate for maintenance
    print("\n🔧 Manually isolating service for maintenance...")
    await control.isolate("Planned maintenance window")
    
    # Calls should now fail immediately
    print("\nAttempting calls during isolation:")
    for i in range(3):
        try:
            await client.call_with_circuit_breaker(f"/api/v1/users/{i}")
        except CircuitBreakerError as e:
            print(f"  ❌ Call rejected: {e}")
    
    # Show isolation info
    if control.is_isolated:
        info = control.isolation_info
        print(f"\nIsolation info:")
        print(f"  Reason: {info['reason']}")
        print(f"  Duration: {info['duration']:.1f} seconds")
    
    # Reset the circuit
    print("\n♻️  Resetting circuit breaker...")
    await control.reset()
    
    # Calls should work again
    print("\nCalls after reset:")
    try:
        result = await client.call_with_circuit_breaker("/api/v1/status")
        print(f"✅ Service restored: {result['status']}")
    except Exception as e:
        print(f"❌ Still failing: {e}")


async def demo_monitoring():
    """Demonstrate circuit breaker monitoring"""
    print("\n\n=== Circuit Breaker Monitoring ===\n")
    
    client = ResilientAPIClient()
    provider = client.circuit_breaker.state_provider
    
    # Generate some activity
    print("Generating activity for monitoring...")
    for i in range(15):
        try:
            await client.call_with_custom_retry(f"/api/v1/metrics/{i}")
            print(".", end="", flush=True)
        except Exception:
            print("x", end="", flush=True)
        await asyncio.sleep(0.2)
    
    print("\n\nMonitoring Report:")
    stats = provider.stats
    
    print(f"  Current state: {stats['state']}")
    print(f"  Time in state: {stats['time_in_state']:.1f}s")
    print(f"  Success rate: {stats['success_rate']}")
    print(f"  Failure rate: {stats['failure_rate']}")
    print(f"  Consecutive failures: {stats['consecutive_failures']}")
    
    print("\nError breakdown:")
    for error_type, count in stats['error_breakdown'].items():
        print(f"  {error_type}: {count}")
    
    print("\nRecent state changes:")
    for change in stats['recent_state_changes']:
        print(f"  {change['timestamp']}: {change['from_state']} → {change['to_state']} ({change['reason']})")
    
    # Get timeline
    timeline = provider.get_state_timeline(hours=1)
    print(f"\nState changes in last hour: {len(timeline)}")


async def demo_break_duration_adaptation():
    """Demonstrate dynamic break duration adaptation"""
    print("\n\n=== Dynamic Break Duration Adaptation ===\n")
    
    # Create client with custom break duration
    client = ResilientAPIClient()
    breaker = client.circuit_breaker
    
    # Force some failures to see break duration increase
    print("Simulating repeated failures to show break duration adaptation...")
    
    async def force_failure():
        raise NetworkError("Forced failure")
    
    for attempt in range(5):
        print(f"\nAttempt {attempt + 1}:")
        
        # Force failures to open circuit
        for _ in range(3):
            try:
                await breaker.call(force_failure)
            except NetworkError:
                pass
        
        # Show current break duration
        current_duration = breaker._calculate_break_duration()
        print(f"  Circuit opened - break duration: {current_duration:.1f}s")
        print(f"  Consecutive failures: {breaker._stats.consecutive_failures}")
        
        # Wait for circuit to allow retry
        print(f"  Waiting {current_duration:.1f}s...")
        await asyncio.sleep(current_duration + 0.1)
        
        # Try to recover (will fail and increase duration)
        try:
            await breaker.call(force_failure)
        except NetworkError:
            pass
    
    print("\nBreak duration increases exponentially with repeated failures!")


async def main():
    """Run all demonstrations"""
    print("Circuit Breaker + Retry Integration Demo")
    print("=" * 50)
    
    await demo_basic_integration()
    await demo_manual_control()
    await demo_monitoring()
    await demo_break_duration_adaptation()
    
    print("\n" + "=" * 50)
    print("Demo completed!")


if __name__ == "__main__":
    asyncio.run(main())