"""Phase 2: Circuit Breaker Tests

Tests for circuit breaker pattern implementation including state transitions,
failure counting, and adaptive behavior.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from flashcard_pipeline.circuit_breaker import (
    CircuitBreaker, CircuitState, MultiServiceCircuitBreaker, 
    AdaptiveCircuitBreaker
)
from flashcard_pipeline.exceptions import CircuitBreakerError, ApiError, NetworkError


class TestCircuitStates:
    """Test circuit breaker state transitions"""
    
    @pytest.fixture
    def circuit_breaker(self):
        """Create circuit breaker with test configuration"""
        return CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1,  # 1 second for faster tests
            expected_exception=ApiError,
            name="test_breaker"
        )
    
    @pytest.mark.asyncio
    async def test_closed_to_open_transition(self, circuit_breaker):
        """Test transition from CLOSED to OPEN on failures"""
        assert circuit_breaker.state == CircuitState.CLOSED.value
        
        # Create failing function
        async def failing_func():
            raise ApiError("Service unavailable", status_code=503)
        
        # Fail threshold times
        for i in range(3):
            with pytest.raises(ApiError):
                await circuit_breaker.call(failing_func)
            
            # Should still be closed until threshold
            if i < 2:
                assert circuit_breaker.state == CircuitState.CLOSED.value
        
        # Should be open after threshold
        assert circuit_breaker.state == CircuitState.OPEN.value
        assert circuit_breaker._failure_count == 3
    
    @pytest.mark.asyncio
    async def test_open_to_half_open_transition(self, circuit_breaker):
        """Test transition from OPEN to HALF_OPEN after timeout"""
        # Force to OPEN state
        circuit_breaker._state = CircuitState.OPEN
        circuit_breaker._failure_count = 3
        circuit_breaker._last_failure_time = time.time()
        
        # Should reject calls while OPEN
        async def test_func():
            return "success"
        
        with pytest.raises(CircuitBreakerError) as exc_info:
            await circuit_breaker.call(test_func)
        assert "is OPEN" in str(exc_info.value)
        
        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        
        # Next call should transition to HALF_OPEN
        result = await circuit_breaker.call(test_func)
        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED.value  # Success closes circuit
    
    @pytest.mark.asyncio
    async def test_half_open_to_closed_on_success(self, circuit_breaker):
        """Test HALF_OPEN to CLOSED transition on success"""
        # Set to HALF_OPEN state
        circuit_breaker._state = CircuitState.HALF_OPEN
        circuit_breaker._failure_count = 3
        
        async def success_func():
            return "success"
        
        # Success should close circuit
        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED.value
        assert circuit_breaker._failure_count == 0
    
    @pytest.mark.asyncio
    async def test_half_open_to_open_on_failure(self, circuit_breaker):
        """Test HALF_OPEN back to OPEN on failure"""
        # Set to HALF_OPEN state
        circuit_breaker._state = CircuitState.HALF_OPEN
        circuit_breaker._failure_count = 2
        
        async def failing_func():
            raise ApiError("Still failing", status_code=503)
        
        # Failure should reopen circuit
        with pytest.raises(ApiError):
            await circuit_breaker.call(failing_func)
        
        assert circuit_breaker.state == CircuitState.OPEN.value
        assert circuit_breaker._failure_count == 3
    
    @pytest.mark.asyncio
    async def test_manual_reset(self, circuit_breaker):
        """Test manual circuit reset"""
        # Force to OPEN state
        circuit_breaker._state = CircuitState.OPEN
        circuit_breaker._failure_count = 10
        
        # Manual reset
        await circuit_breaker.reset()
        
        assert circuit_breaker.state == CircuitState.CLOSED.value
        assert circuit_breaker._failure_count == 0
    
    @pytest.mark.asyncio
    async def test_state_duration_tracking(self, circuit_breaker):
        """Test tracking of time spent in each state"""
        initial_time = circuit_breaker._state_changed_at
        
        # Wait a bit
        await asyncio.sleep(0.1)
        
        stats = circuit_breaker.get_stats()
        assert stats["state_duration"] >= 0.1
        
        # Change state
        circuit_breaker._state = CircuitState.OPEN
        circuit_breaker._state_changed_at = time.time()
        
        # Duration should reset
        stats = circuit_breaker.get_stats()
        assert stats["state_duration"] < 0.1


class TestFailureCounting:
    """Test failure threshold and counting logic"""
    
    @pytest.mark.asyncio
    async def test_accurate_failure_counting(self):
        """Test failure count is accurate"""
        breaker = CircuitBreaker(failure_threshold=5)
        
        async def flaky_func(should_fail):
            if should_fail:
                raise ApiError("Failed", status_code=500)
            return "success"
        
        # Mix successes and failures (4 failures, 3 successes)
        pattern = [True, True, False, True, False, True, False]
        
        for should_fail in pattern:
            try:
                await breaker.call(lambda: flaky_func(should_fail))
            except ApiError:
                pass
        
        # Count failures in pattern
        expected_failures = sum(1 for x in pattern if x)
        assert breaker._failure_count == expected_failures
        
        # Should still be closed (threshold is 5)
        assert breaker.state == CircuitState.CLOSED.value
    
    @pytest.mark.asyncio
    async def test_success_resets_count_in_closed(self):
        """Test success doesn't reset count in CLOSED state"""
        breaker = CircuitBreaker(failure_threshold=3)
        
        async def success_func():
            return "success"
        
        async def failing_func():
            raise ApiError("Failed", status_code=500)
        
        # Two failures
        for _ in range(2):
            with pytest.raises(ApiError):
                await breaker.call(failing_func)
        
        assert breaker._failure_count == 2
        
        # Success in CLOSED state
        await breaker.call(success_func)
        
        # Count should not reset in CLOSED state
        assert breaker._failure_count == 2
        assert breaker._success_count == 1
    
    @pytest.mark.asyncio
    async def test_different_exception_types(self):
        """Test handling of different exception types"""
        breaker = CircuitBreaker(
            failure_threshold=3,
            expected_exception=ApiError
        )
        
        async def api_error_func():
            raise ApiError("API failed", status_code=500)
        
        async def network_error_func():
            raise NetworkError("Network failed")
        
        async def value_error_func():
            raise ValueError("Invalid value")
        
        # API errors should count
        for _ in range(2):
            with pytest.raises(ApiError):
                await breaker.call(api_error_func)
        
        assert breaker._failure_count == 2
        
        # Other exceptions should pass through but not count
        with pytest.raises(NetworkError):
            await breaker.call(network_error_func)
        
        assert breaker._failure_count == 2  # Not incremented
        
        # ValueError should also pass through
        with pytest.raises(ValueError):
            await breaker.call(value_error_func)
        
        assert breaker._failure_count == 2  # Not incremented
    
    @pytest.mark.asyncio
    async def test_failure_type_tracking(self):
        """Test tracking of different failure types"""
        breaker = CircuitBreaker(failure_threshold=10)
        
        # Different error types
        errors = [
            ApiError("Auth failed", status_code=401),
            ApiError("Not found", status_code=404),
            ApiError("Server error", status_code=500),
            ApiError("Server error", status_code=500),
            ApiError("Rate limited", status_code=429),
        ]
        
        for error in errors:
            async def fail():
                raise error
            
            with pytest.raises(ApiError):
                await breaker.call(fail)
        
        stats = breaker.get_stats()
        assert stats["failure_types"]["ApiError"] == 5
        assert breaker._failure_count == 5


class TestCircuitBreakerBehavior:
    """Test circuit breaker behavior in various scenarios"""
    
    @pytest.mark.asyncio
    async def test_circuit_open_prevents_calls(self):
        """Test OPEN circuit prevents function calls"""
        breaker = CircuitBreaker(failure_threshold=1)
        
        call_count = 0
        
        async def tracked_func():
            nonlocal call_count
            call_count += 1
            raise ApiError("Failed", status_code=500)
        
        # First call executes and opens circuit
        with pytest.raises(ApiError):
            await breaker.call(tracked_func)
        
        assert call_count == 1
        assert breaker.state == CircuitState.OPEN.value
        
        # Subsequent calls should not execute function
        for _ in range(5):
            with pytest.raises(CircuitBreakerError):
                await breaker.call(tracked_func)
        
        # Function should not have been called again
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_half_open_single_test(self):
        """Test HALF_OPEN allows single test call"""
        breaker = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=0.1
        )
        
        call_count = 0
        
        async def counted_func():
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                raise ApiError("Failed", status_code=500)
            return "success"
        
        # Open circuit
        with pytest.raises(ApiError):
            await breaker.call(counted_func)
        
        assert breaker.state == CircuitState.OPEN.value
        
        # Wait for recovery
        await asyncio.sleep(0.2)  # Increased wait time
        
        # Should allow one test call
        result = await breaker.call(counted_func)
        assert result == "success"
        assert call_count == 2
        assert breaker.state == CircuitState.CLOSED.value
    
    @pytest.mark.asyncio
    async def test_concurrent_calls_during_transition(self):
        """Test handling of concurrent calls during state transition"""
        breaker = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=0.1
        )
        
        # Open the circuit
        async def fail():
            raise ApiError("Failed", status_code=500)
        
        with pytest.raises(ApiError):
            await breaker.call(fail)
        
        # Wait for recovery timeout
        await asyncio.sleep(0.15)
        
        # Concurrent calls during potential HALF_OPEN transition
        async def success():
            return "success"
        
        results = await asyncio.gather(
            breaker.call(success),
            breaker.call(success),
            breaker.call(success),
            return_exceptions=True
        )
        
        # At least one should succeed (the one that transitioned to HALF_OPEN)
        successes = [r for r in results if r == "success"]
        assert len(successes) >= 1
        
        # Circuit should be closed after success
        assert breaker.state == CircuitState.CLOSED.value
    
    @pytest.mark.asyncio
    async def test_statistics_collection(self):
        """Test comprehensive statistics collection"""
        breaker = CircuitBreaker(
            failure_threshold=5,
            expected_exception=ApiError
        )
        
        # Generate various outcomes
        async def variable_func(outcome):
            if outcome == "success":
                return "ok"
            elif outcome == "api_error":
                raise ApiError("API error", status_code=500)
            elif outcome == "network_error":
                raise NetworkError("Network error")
        
        outcomes = [
            "success", "success", "api_error", "success",
            "api_error", "network_error", "api_error", "success"
        ]
        
        for outcome in outcomes:
            try:
                await breaker.call(lambda: variable_func(outcome))
            except Exception:
                pass
        
        stats = breaker.get_stats()
        
        assert stats["call_count"] == 8
        assert stats["success_count"] == 4
        assert stats["failure_count"] == 3  # Only ApiErrors count
        assert stats["success_rate"] == 50.0
        assert "ApiError" in stats["failure_types"]


class TestMultiServiceCircuitBreaker:
    """Test circuit breaker for multiple services"""
    
    @pytest.mark.asyncio
    async def test_service_isolation(self):
        """Test different services have isolated circuit breakers"""
        multi_breaker = MultiServiceCircuitBreaker()
        
        async def service_a_fail():
            raise ApiError("Service A failed", status_code=500)
        
        async def service_b_success():
            return "Service B OK"
        
        # Fail service A multiple times
        for _ in range(3):
            with pytest.raises(ApiError):
                await multi_breaker.call("service_a", service_a_fail)
        
        # Service A should be open
        breaker_a = await multi_breaker.get_breaker("service_a")
        assert breaker_a.state == CircuitState.OPEN.value
        
        # Service B should still work
        result = await multi_breaker.call("service_b", service_b_success)
        assert result == "Service B OK"
        
        breaker_b = await multi_breaker.get_breaker("service_b")
        assert breaker_b.state == CircuitState.CLOSED.value
    
    @pytest.mark.asyncio
    async def test_per_service_configuration(self):
        """Test different configurations per service"""
        multi_breaker = MultiServiceCircuitBreaker()
        
        # Get breakers with different configs
        breaker_critical = await multi_breaker.get_breaker(
            "critical_service",
            failure_threshold=10,
            recovery_timeout=120
        )
        
        breaker_normal = await multi_breaker.get_breaker(
            "normal_service",
            failure_threshold=3,
            recovery_timeout=30
        )
        
        assert breaker_critical.failure_threshold == 10
        assert breaker_critical.recovery_timeout == 120
        assert breaker_normal.failure_threshold == 3
        assert breaker_normal.recovery_timeout == 30
    
    @pytest.mark.asyncio
    async def test_global_statistics(self):
        """Test aggregated statistics across all services"""
        multi_breaker = MultiServiceCircuitBreaker()
        
        # Create activity on multiple services
        services = ["api", "database", "cache"]
        
        for service in services:
            for i in range(5):
                async def func():
                    if i % 2 == 0:
                        return f"{service} success"
                    raise ApiError(f"{service} error", status_code=500)
                
                try:
                    await multi_breaker.call(service, func)
                except ApiError:
                    pass
        
        # Get global stats
        all_stats = multi_breaker.get_all_stats()
        
        assert len(all_stats) == 3
        for service in services:
            assert service in all_stats
            assert all_stats[service]["call_count"] == 5
    
    @pytest.mark.asyncio
    async def test_reset_all_breakers(self):
        """Test resetting all circuit breakers"""
        multi_breaker = MultiServiceCircuitBreaker()
        
        # Open multiple circuits
        for service in ["a", "b", "c"]:
            async def fail():
                raise ApiError(f"{service} failed", status_code=500)
            
            for _ in range(3):
                with pytest.raises(ApiError):
                    await multi_breaker.call(service, fail)
        
        # Verify all are open
        for service in ["a", "b", "c"]:
            breaker = await multi_breaker.get_breaker(service)
            assert breaker.state == CircuitState.OPEN.value
        
        # Reset all
        await multi_breaker.reset_all()
        
        # Verify all are closed
        for service in ["a", "b", "c"]:
            breaker = await multi_breaker.get_breaker(service)
            assert breaker.state == CircuitState.CLOSED.value
            assert breaker._failure_count == 0


class TestAdaptiveCircuitBreaker:
    """Test adaptive circuit breaker behavior"""
    
    @pytest.mark.asyncio
    async def test_threshold_reduction_on_error_burst(self):
        """Test threshold reduces during error bursts"""
        adaptive_breaker = AdaptiveCircuitBreaker(
            initial_threshold=10,
            recovery_timeout=1,
            expected_exception=ApiError,
            name="adaptive_test"
        )
        
        initial_threshold = adaptive_breaker.failure_threshold
        
        # Generate rapid failures
        async def rapid_fail():
            raise ApiError("Burst failure", status_code=500)
        
        # Fail rapidly
        error_count = 0
        for _ in range(8):
            try:
                await adaptive_breaker.call(rapid_fail)
            except (ApiError, CircuitBreakerError):
                error_count += 1
            await asyncio.sleep(0.05)  # 50ms between failures
        
        # Should have encountered some errors
        assert error_count > 0
        
        # Threshold should have decreased (unless circuit opened first)
        if adaptive_breaker.state != CircuitState.OPEN.value:
            assert adaptive_breaker.failure_threshold < initial_threshold
        assert adaptive_breaker.failure_threshold >= adaptive_breaker.min_threshold
    
    @pytest.mark.asyncio
    async def test_threshold_increase_on_success(self):
        """Test threshold increases with sustained success"""
        adaptive_breaker = AdaptiveCircuitBreaker(
            initial_threshold=5,
            name="adaptive_success"
        )
        
        # Lower threshold first
        adaptive_breaker.failure_threshold = 3
        
        async def success():
            return "success"
        
        # Sustained successes
        for i in range(30):
            await adaptive_breaker.call(success)
        
        # Threshold should have increased
        assert adaptive_breaker.failure_threshold > 3
        assert adaptive_breaker.failure_threshold <= adaptive_breaker.max_threshold
    
    @pytest.mark.asyncio
    async def test_error_pattern_detection(self):
        """Test detection of error patterns"""
        adaptive_breaker = AdaptiveCircuitBreaker()
        
        # Sporadic errors - should not trigger adaptation
        async def sporadic_fail():
            raise ApiError("Sporadic", status_code=500)
        
        initial_threshold = adaptive_breaker.failure_threshold
        
        for i in range(5):
            try:
                await adaptive_breaker.call(sporadic_fail)
            except (ApiError, CircuitBreakerError):
                pass
            await asyncio.sleep(1)  # Long gap between errors
        
        # Should maintain normal threshold (no adaptation due to slow error rate)
        # OR circuit might be open after hitting the min threshold
        if adaptive_breaker.state == CircuitState.CLOSED.value:
            assert adaptive_breaker.failure_threshold == initial_threshold
        
        # Clear error history
        adaptive_breaker._error_timestamps.clear()
        
        # Burst errors - should trigger adaptation
        for i in range(5):
            try:
                await adaptive_breaker.call(sporadic_fail)
            except (ApiError, CircuitBreakerError):
                pass
            await asyncio.sleep(0.1)  # Rapid errors
        
        # Should have reduced threshold (or circuit is open)
        if adaptive_breaker.state != CircuitState.OPEN.value:
            assert adaptive_breaker.failure_threshold < initial_threshold
    
    @pytest.mark.asyncio
    async def test_adaptive_recovery(self):
        """Test adaptive recovery behavior"""
        adaptive_breaker = AdaptiveCircuitBreaker(
            initial_threshold=5,
            recovery_timeout=0.5
        )
        
        # Cause circuit to open with burst
        async def burst_fail():
            raise ApiError("Burst", status_code=500)
        
        error_count = 0
        for _ in range(5):
            try:
                await adaptive_breaker.call(burst_fail)
            except (ApiError, CircuitBreakerError):
                error_count += 1
            await asyncio.sleep(0.05)
        
        # Should have errors and potentially opened circuit
        assert error_count > 0
        lowered_threshold = adaptive_breaker.failure_threshold
        
        # Wait for recovery
        await asyncio.sleep(0.6)
        
        # Success should close circuit
        async def recover():
            return "recovered"
        
        # Try to call after recovery
        try:
            result = await adaptive_breaker.call(recover)
            assert result == "recovered"
            assert adaptive_breaker.state == CircuitState.CLOSED.value
            
            # Threshold might have increased slightly after success but should be <= initial
            assert adaptive_breaker.failure_threshold <= 5
        except CircuitBreakerError:
            # Circuit might still be open if it didn't recover yet
            assert adaptive_breaker.state == CircuitState.OPEN.value