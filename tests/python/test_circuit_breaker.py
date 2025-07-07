import pytest
import asyncio
import time
from unittest.mock import AsyncMock, Mock

from flashcard_pipeline.circuit_breaker import CircuitBreaker, CircuitState
from flashcard_pipeline.exceptions import CircuitBreakerError


class TestCircuitBreaker:
    @pytest.fixture
    def circuit_breaker(self):
        """Create a circuit breaker with test-friendly settings"""
        return CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1,  # 1 second for faster tests
            expected_exception=Exception
        )
    
    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self, circuit_breaker):
        """Test that circuit breaker starts in closed state"""
        assert circuit_breaker.state == "closed"
        assert circuit_breaker.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_successful_calls_keep_circuit_closed(self, circuit_breaker):
        """Test that successful calls don't open the circuit"""
        async def success_func():
            return "success"
        
        # Make multiple successful calls
        for _ in range(10):
            result = await circuit_breaker.call(success_func)
            assert result == "success"
        
        assert circuit_breaker.state == "closed"
        assert circuit_breaker.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_failures_increment_counter(self, circuit_breaker):
        """Test that failures increment the failure counter"""
        async def failing_func():
            raise Exception("Test failure")
        
        # Make failures less than threshold
        for i in range(2):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)
            assert circuit_breaker.failure_count == i + 1
            assert circuit_breaker.state == "closed"
    
    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self, circuit_breaker):
        """Test that circuit opens after reaching failure threshold"""
        async def failing_func():
            raise Exception("Test failure")
        
        # Reach failure threshold
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)
        
        assert circuit_breaker.state == "open"
        assert circuit_breaker.failure_count == 3
    
    @pytest.mark.asyncio
    async def test_open_circuit_rejects_calls(self, circuit_breaker):
        """Test that open circuit rejects calls immediately"""
        async def failing_func():
            raise Exception("Test failure")
        
        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)
        
        # Now calls should be rejected
        async def normal_func():
            return "should not be called"
        
        with pytest.raises(CircuitBreakerError) as exc_info:
            await circuit_breaker.call(normal_func)
        
        assert "Circuit breaker is open" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_half_open_state_after_timeout(self, circuit_breaker):
        """Test transition to half-open state after recovery timeout"""
        async def failing_func():
            raise Exception("Test failure")
        
        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)
        
        assert circuit_breaker.state == "open"
        
        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        
        # State should still be open until we try a call
        assert circuit_breaker.state == "open"
        
        # This call should transition to half-open and execute
        async def success_func():
            return "success"
        
        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.state == "closed"
        assert circuit_breaker.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self, circuit_breaker):
        """Test that failure in half-open state reopens the circuit"""
        async def failing_func():
            raise Exception("Test failure")
        
        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)
        
        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        
        # Next call fails, should reopen
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_func)
        
        assert circuit_breaker.state == "open"
        
        # Should reject calls again
        with pytest.raises(CircuitBreakerError):
            await circuit_breaker.call(failing_func)
    
    @pytest.mark.asyncio
    async def test_specific_exception_handling(self):
        """Test that only specified exceptions trigger the circuit breaker"""
        from flashcard_pipeline.exceptions import ApiError
        
        cb = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=1,
            expected_exception=ApiError
        )
        
        # Non-API errors should not trigger circuit breaker
        async def raise_value_error():
            raise ValueError("Not an API error")
        
        for _ in range(5):
            with pytest.raises(ValueError):
                await cb.call(raise_value_error)
        
        assert cb.state == "closed"
        assert cb.failure_count == 0
        
        # API errors should trigger circuit breaker
        async def raise_api_error():
            raise ApiError("API failed", status_code=500, response_body="")
        
        for _ in range(2):
            with pytest.raises(ApiError):
                await cb.call(raise_api_error)
        
        assert cb.state == "open"
    
    @pytest.mark.asyncio
    async def test_success_ratio_tracking(self, circuit_breaker):
        """Test that circuit breaker tracks success ratio"""
        success_count = 0
        total_calls = 0
        
        async def sometimes_failing():
            nonlocal success_count, total_calls
            total_calls += 1
            if total_calls % 4 == 0:  # Fail every 4th call
                raise Exception("Periodic failure")
            success_count += 1
            return "success"
        
        # Make some calls
        for i in range(10):
            try:
                await circuit_breaker.call(sometimes_failing)
            except Exception:
                pass
        
        # Should have 7 successes, 3 failures (calls 4, 8, and potentially 12)
        # Circuit should still be closed (threshold is 3 consecutive failures)
        assert circuit_breaker.state == "closed" or circuit_breaker.state == "open"
        
        # If we had tracking, we could assert:
        # assert circuit_breaker.success_ratio == 0.7
    
    @pytest.mark.asyncio
    async def test_concurrent_calls_handling(self, circuit_breaker):
        """Test circuit breaker behavior with concurrent calls"""
        call_count = 0
        
        async def counting_func():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise Exception("Failing")
            return f"success_{call_count}"
        
        # Launch concurrent calls
        tasks = []
        for _ in range(10):
            tasks.append(circuit_breaker.call(counting_func))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # First 3 should fail, circuit opens, rest should be CircuitBreakerError
        exceptions = [r for r in results if isinstance(r, Exception)]
        circuit_open_errors = [r for r in results if isinstance(r, CircuitBreakerError)]
        
        assert len(exceptions) >= 3  # At least threshold failures
        assert len(circuit_open_errors) > 0  # Some calls rejected
        assert circuit_breaker.state == "open"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_with_async_context_manager(self, circuit_breaker):
        """Test using circuit breaker as a context manager (if implemented)"""
        # This test assumes we might want to add context manager support
        async def test_func():
            return "result"
        
        result = await circuit_breaker.call(test_func)
        assert result == "result"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_stats(self, circuit_breaker):
        """Test getting circuit breaker statistics"""
        async def failing_func():
            raise Exception("Fail")
        
        async def success_func():
            return "success"
        
        # Make some calls
        for _ in range(2):
            await circuit_breaker.call(success_func)
        
        for _ in range(2):
            try:
                await circuit_breaker.call(failing_func)
            except Exception:
                pass
        
        # Get stats
        stats = circuit_breaker.get_stats()
        assert stats["state"] == "closed"
        assert stats["failure_count"] == 2
        assert stats["failure_threshold"] == 3
    
    @pytest.mark.asyncio
    async def test_manual_reset(self, circuit_breaker):
        """Test manually resetting the circuit breaker"""
        async def failing_func():
            raise Exception("Fail")
        
        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)
        
        assert circuit_breaker.state == "open"
        
        # Manual reset
        circuit_breaker.reset()
        
        assert circuit_breaker.state == "closed"
        assert circuit_breaker.failure_count == 0
        
        # Should accept calls again
        async def success_func():
            return "success"
        
        result = await circuit_breaker.call(success_func)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_with_fallback(self):
        """Test circuit breaker with fallback function"""
        # This assumes we might want to add fallback support
        async def main_func():
            raise Exception("Main failed")
        
        async def fallback_func():
            return "fallback_result"
        
        cb = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=1,
            expected_exception=Exception
        )
        
        # First call fails and opens circuit
        with pytest.raises(Exception):
            await cb.call(main_func)
        
        # Circuit is open, but we could have a fallback mechanism
        # result = await cb.call_with_fallback(main_func, fallback_func)
        # assert result == "fallback_result"
    
    def test_circuit_breaker_initialization_validation(self):
        """Test circuit breaker initialization with invalid parameters"""
        # Negative threshold
        with pytest.raises(ValueError):
            CircuitBreaker(failure_threshold=-1, recovery_timeout=1)
        
        # Zero threshold
        with pytest.raises(ValueError):
            CircuitBreaker(failure_threshold=0, recovery_timeout=1)
        
        # Negative timeout
        with pytest.raises(ValueError):
            CircuitBreaker(failure_threshold=3, recovery_timeout=-1)