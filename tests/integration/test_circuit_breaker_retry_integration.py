"""Integration tests for circuit breaker and retry system working together"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock
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
    RetryExhausted,
)


class TestCircuitBreakerRetryIntegration:
    """Test circuit breaker and retry system working together"""
    
    @pytest.fixture
    def circuit_breaker(self):
        """Create a test circuit breaker"""
        return EnhancedCircuitBreaker(
            failure_threshold=0.5,
            min_throughput=2,
            sampling_duration=10.0,
            break_duration=0.5,  # Short for testing
            enable_monitoring=True,
            enable_manual_control=True,
            name="test_service"
        )
    
    @pytest.fixture
    def retry_config(self):
        """Create a test retry configuration"""
        return RetryConfig(
            max_attempts=3,
            initial_delay=0.1,
            max_delay=1.0,
            jitter=False,  # No jitter for predictable tests
            retry_on=(NetworkError, StructuredAPIError)
        )
    
    @pytest.mark.asyncio
    async def test_retry_with_circuit_breaker_success(self, circuit_breaker, retry_config):
        """Test successful calls through both systems"""
        call_count = 0
        
        @retry_async(retry_config)
        async def protected_call():
            nonlocal call_count
            call_count += 1
            
            async def api_call():
                return {"status": "success", "call": call_count}
            
            return await circuit_breaker.call(api_call)
        
        # Should succeed on first try
        result = await protected_call()
        assert result["status"] == "success"
        assert call_count == 1
        assert circuit_breaker._state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_retry_recovers_before_circuit_opens(self, circuit_breaker, retry_config):
        """Test retry recovers from transient failures before circuit opens"""
        call_count = 0
        
        @retry_async(retry_config)
        async def protected_call():
            nonlocal call_count
            call_count += 1
            
            async def flaky_api():
                # Fail first attempt, succeed on retry
                if call_count == 1:
                    raise NetworkError("Transient network error")
                return {"status": "success", "attempt": call_count}
            
            return await circuit_breaker.call(flaky_api)
        
        # Should succeed after retry
        result = await protected_call()
        assert result["status"] == "success"
        assert result["attempt"] == 2
        assert call_count == 2
        
        # Circuit should still be closed (only 1 failure)
        assert circuit_breaker._state == CircuitState.CLOSED
        assert circuit_breaker._stats.failed_calls == 1
        assert circuit_breaker._stats.successful_calls == 1
    
    @pytest.mark.asyncio
    async def test_circuit_opens_stops_retries(self, circuit_breaker, retry_config):
        """Test circuit breaker stops retry attempts when open"""
        call_count = 0
        
        # First, open the circuit with failures
        async def failing_api():
            raise NetworkError("Service down")
        
        # Make enough calls to open circuit
        for _ in range(2):
            with pytest.raises(NetworkError):
                await circuit_breaker.call(failing_api)
        
        assert circuit_breaker._state == CircuitState.OPEN
        
        # Now try with retry
        @retry_async(retry_config)
        async def protected_call():
            nonlocal call_count
            call_count += 1
            return await circuit_breaker.call(failing_api)
        
        # Should fail immediately with CircuitBreakerError (not retried)
        with pytest.raises(CircuitBreakerError) as exc_info:
            await protected_call()
        
        # Only one attempt because CircuitBreakerError is not in retry_on
        assert call_count == 1
        assert "is open" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_circuit_recovery_with_retry(self, circuit_breaker):
        """Test circuit recovery process with retry helping"""
        # Custom retry that handles CircuitBreakerError
        retry_config = RetryConfig(
            max_attempts=5,
            initial_delay=0.2,
            retry_on=(NetworkError, CircuitBreakerError)
        )
        
        call_sequence = []
        
        @retry_async(retry_config)
        async def protected_call():
            async def api_call():
                call_sequence.append(time.time())
                # Fail first 2 calls, then succeed
                if len(call_sequence) <= 2:
                    raise NetworkError("Service recovering")
                return {"status": "recovered"}
            
            return await circuit_breaker.call(api_call)
        
        # This will:
        # 1. Fail twice and open circuit
        # 2. Get CircuitBreakerError while open
        # 3. Retry until circuit allows half-open
        # 4. Succeed and close circuit
        
        start_time = time.time()
        result = await protected_call()
        end_time = time.time()
        
        assert result["status"] == "recovered"
        assert circuit_breaker._state == CircuitState.CLOSED
        
        # Should have taken at least the break duration
        assert end_time - start_time >= circuit_breaker.break_duration
    
    @pytest.mark.asyncio
    async def test_different_error_handling(self, circuit_breaker, retry_config):
        """Test different error types are handled appropriately"""
        call_log = []
        
        async def complex_api(request_id: int):
            call_log.append(request_id)
            
            if request_id == 1:
                # Transient error - should retry
                raise NetworkError("Timeout")
            elif request_id == 2:
                # Server error - should retry
                raise StructuredAPIError(500, "Server error")
            elif request_id == 3:
                # Client error - should NOT retry (not in retry_on)
                raise StructuredAPIError(400, "Bad request")
            else:
                return {"id": request_id, "status": "success"}
        
        # Test 1: Network error - retries and succeeds
        @retry_async(retry_config)
        async def call_1():
            return await circuit_breaker.call(complex_api, 1)
        
        # Should fail with network error
        with pytest.raises(NetworkError):
            await call_1()
        
        # Test 2: Server error - retries
        @retry_async(retry_config)
        async def call_2():
            return await circuit_breaker.call(complex_api, 2)
        
        with pytest.raises(StructuredAPIError):
            await call_2()
        
        # Test 3: Client error - no retry
        @retry_async(retry_config)
        async def call_3():
            return await circuit_breaker.call(complex_api, 3)
        
        with pytest.raises(StructuredAPIError) as exc_info:
            await call_3()
        
        assert exc_info.value.status_code == 400
        
        # Verify retry behavior
        # Call 1 and 2 should have been retried (3 attempts each)
        # Call 3 should not retry (1 attempt)
        assert call_log.count(1) == 3
        assert call_log.count(2) == 3
        assert call_log.count(3) == 1
    
    @pytest.mark.asyncio
    async def test_manual_control_with_retry(self, circuit_breaker):
        """Test manual control interaction with retry"""
        control = circuit_breaker.manual_control
        
        retry_config = RetryConfig(
            max_attempts=3,
            initial_delay=0.1,
            retry_on=(NetworkError, CircuitBreakerError)
        )
        
        async def api_call():
            return {"status": "ok"}
        
        # Isolate the circuit
        await control.isolate("Emergency maintenance")
        
        @retry_async(retry_config)
        async def protected_call():
            return await circuit_breaker.call(api_call)
        
        # Should fail even with retries
        with pytest.raises(RetryExhausted) as exc_info:
            await protected_call()
        
        # All attempts should have failed with CircuitBreakerError
        assert isinstance(exc_info.value.last_exception, CircuitBreakerError)
        
        # Reset and verify recovery
        await control.reset()
        result = await protected_call()
        assert result["status"] == "ok"
    
    @pytest.mark.asyncio
    async def test_dynamic_break_duration_with_retry(self, circuit_breaker):
        """Test dynamic break duration affecting retry timing"""
        # Use exponential break duration
        circuit_breaker.break_duration_generator = exponential_break_duration
        
        # Retry config that waits for circuit
        retry_config = RetryConfig(
            max_attempts=10,
            initial_delay=0.5,
            max_delay=5.0,
            retry_on=(NetworkError, CircuitBreakerError)
        )
        
        failure_count = 0
        recovery_times = []
        
        async def eventually_recovering_api():
            nonlocal failure_count
            failure_count += 1
            
            # Fail 6 times (causing increasing break durations)
            if failure_count <= 6:
                raise NetworkError("Still down")
            
            recovery_times.append(time.time())
            return {"recovered": True}
        
        @retry_async(retry_config)
        async def protected_call():
            return await circuit_breaker.call(eventually_recovering_api)
        
        start_time = time.time()
        result = await protected_call()
        total_time = time.time() - start_time
        
        assert result["recovered"] is True
        
        # Verify break duration increased
        # Initial failures will cause exponentially increasing break durations
        assert total_time > 2.0  # Should take several seconds with retries
        
        # Circuit should have opened and recovered
        assert circuit_breaker._state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_monitoring_with_retry_patterns(self, circuit_breaker, retry_config):
        """Test monitoring captures retry patterns"""
        provider = circuit_breaker.state_provider
        
        attempt_count = 0
        
        @retry_async(retry_config)
        async def monitored_call():
            nonlocal attempt_count
            attempt_count += 1
            
            async def api():
                # Fail first 4 attempts to trigger both retry and circuit patterns
                if attempt_count <= 4:
                    raise NetworkError(f"Attempt {attempt_count} failed")
                return {"attempts": attempt_count}
            
            return await circuit_breaker.call(api)
        
        # Make several calls
        results = []
        for i in range(3):
            attempt_count = 0
            try:
                result = await monitored_call()
                results.append(("success", result))
            except Exception as e:
                results.append(("failure", str(e)))
            
            # Small delay between calls
            await asyncio.sleep(0.1)
        
        # Get monitoring stats
        stats = provider.stats
        timeline = provider.get_state_timeline(hours=1)
        
        # Verify monitoring captured the pattern
        assert stats["total_calls"] > 0
        assert stats["error_breakdown"].get("NetworkError", 0) > 0
        
        # Should have state changes if circuit opened
        if timeline:
            assert any(event["to_state"] == "open" for event in timeline)
    
    @pytest.mark.asyncio
    async def test_cascading_protection(self, retry_config):
        """Test protecting against cascading failures with multiple services"""
        # Create circuit breakers for multiple services
        service_a = EnhancedCircuitBreaker(
            failure_threshold=0.5,
            min_throughput=2,
            break_duration=1.0,
            name="service_a"
        )
        
        service_b = EnhancedCircuitBreaker(
            failure_threshold=0.5,
            min_throughput=2,
            break_duration=1.0,
            enable_manual_control=True,
            name="service_b"
        )
        
        # Service B depends on Service A
        @retry_async(retry_config)
        async def call_service_b():
            async def service_b_logic():
                # First call service A
                try:
                    await service_a.call(lambda: 1/0)  # Service A is broken
                except:
                    raise NetworkError("Dependency failed")
            
            return await service_b.call(service_b_logic)
        
        # Service A failures will cascade to B
        with pytest.raises(RetryExhausted):
            await call_service_b()
        
        # Manually isolate B to prevent further cascade
        await service_b.manual_control.isolate("Dependency failure - preventing cascade")
        
        # Further calls fail fast
        with pytest.raises(CircuitBreakerError):
            await call_service_b()
        
        # This prevents overwhelming service B with doomed requests
        assert service_a._state == CircuitState.OPEN
        assert service_b._state == CircuitState.ISOLATED


class TestRealWorldScenarios:
    """Test real-world integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_api_client_scenario(self):
        """Test realistic API client with circuit breaker and retry"""
        # Simulate API with intermittent failures
        class MockAPI:
            def __init__(self):
                self.call_count = 0
                self.failure_window = (3, 7)  # Fail on calls 3-7
            
            async def call(self, endpoint: str):
                self.call_count += 1
                
                if self.failure_window[0] <= self.call_count <= self.failure_window[1]:
                    raise NetworkError(f"API error on call {self.call_count}")
                
                return {
                    "endpoint": endpoint,
                    "call": self.call_count,
                    "timestamp": datetime.now().isoformat()
                }
        
        api = MockAPI()
        breaker = EnhancedCircuitBreaker(
            failure_threshold=0.6,
            min_throughput=3,
            break_duration=0.5,
            enable_monitoring=True,
            expected_exception=NetworkError
        )
        
        retry_config = RetryConfig(
            max_attempts=3,
            initial_delay=0.1,
            retry_on=(NetworkError,)
        )
        
        @retry_async(retry_config)
        async def make_api_call(endpoint: str):
            return await breaker.call(api.call, endpoint)
        
        results = []
        
        # Make 10 API calls
        for i in range(10):
            try:
                result = await make_api_call(f"/api/v1/data/{i}")
                results.append(("success", result))
            except Exception as e:
                results.append(("failure", type(e).__name__))
            
            await asyncio.sleep(0.1)
        
        # Analyze results
        successes = [r for r in results if r[0] == "success"]
        failures = [r for r in results if r[0] == "failure"]
        
        # Should have some successes before and after failure window
        assert len(successes) > 0
        assert len(failures) > 0
        
        # Circuit should have opened during failure window
        stats = breaker.state_provider.stats
        assert any(
            change["to_state"] == "open" 
            for change in stats["recent_state_changes"]
        )
    
    @pytest.mark.asyncio
    async def test_gradual_recovery_scenario(self):
        """Test system gradually recovering from failures"""
        # Simulate service with gradual recovery
        class GraduallyRecoveringService:
            def __init__(self):
                self.start_time = time.time()
                self.recovery_time = 2.0  # Takes 2 seconds to fully recover
            
            async def call(self):
                elapsed = time.time() - self.start_time
                recovery_progress = min(elapsed / self.recovery_time, 1.0)
                
                # Probability of success increases over time
                import random
                if random.random() > recovery_progress:
                    raise NetworkError("Service still recovering")
                
                return {"status": "ok", "recovery": f"{recovery_progress:.0%}"}
        
        service = GraduallyRecoveringService()
        breaker = EnhancedCircuitBreaker(
            failure_threshold=0.4,  # Open at 40% failure rate
            min_throughput=5,
            sampling_duration=5.0,
            break_duration=0.3,
            enable_monitoring=True
        )
        
        retry_config = RetryConfig(
            max_attempts=2,
            initial_delay=0.1,
            retry_on=(NetworkError,)
        )
        
        @retry_async(retry_config)
        async def call_service():
            return await breaker.call(service.call)
        
        # Make calls over time to see recovery
        results = []
        for i in range(30):
            try:
                result = await call_service()
                results.append(("success", result))
            except:
                results.append(("failure", None))
            
            await asyncio.sleep(0.1)
        
        # Should see increasing success rate over time
        early_results = results[:10]
        late_results = results[-10:]
        
        early_successes = sum(1 for r in early_results if r[0] == "success")
        late_successes = sum(1 for r in late_results if r[0] == "success")
        
        # Success rate should improve
        assert late_successes > early_successes
        
        # Final state should be healthy
        assert breaker._state == CircuitState.CLOSED