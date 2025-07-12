"""Unit tests for enhanced circuit breaker with state monitoring"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta

from flashcard_pipeline.circuit_breaker_v2 import (
    EnhancedCircuitBreaker,
    CircuitState,
    CircuitBreakerStateProvider,
    CircuitBreakerManualControl,
    exponential_break_duration,
    linear_break_duration,
    adaptive_break_duration,
)
from flashcard_pipeline.exceptions import CircuitBreakerError


class TestEnhancedCircuitBreaker:
    """Test enhanced circuit breaker functionality"""
    
    @pytest.fixture
    def breaker(self):
        """Create a test circuit breaker"""
        return EnhancedCircuitBreaker(
            failure_threshold=0.5,  # 50% failure rate
            min_throughput=2,       # Minimum 2 calls
            sampling_duration=10.0,
            break_duration=1.0,     # Short for testing
            name="test_breaker"
        )
    
    @pytest.mark.asyncio
    async def test_initial_state(self, breaker):
        """Test initial circuit breaker state"""
        assert breaker._state == CircuitState.CLOSED
        assert breaker._stats.total_calls == 0
        assert breaker._stats.success_rate == 1.0
        assert await breaker.is_allowed() is True
    
    @pytest.mark.asyncio
    async def test_successful_calls(self, breaker):
        """Test circuit remains closed on successful calls"""
        async def success_func():
            return "success"
        
        # Make several successful calls
        for _ in range(5):
            result = await breaker.call(success_func)
            assert result == "success"
        
        assert breaker._state == CircuitState.CLOSED
        assert breaker._stats.successful_calls == 5
        assert breaker._stats.consecutive_successes == 5
        assert breaker._stats.success_rate == 1.0
    
    @pytest.mark.asyncio
    async def test_circuit_opens_on_failures(self, breaker):
        """Test circuit opens when failure threshold is exceeded"""
        async def failing_func():
            raise ValueError("Test error")
        
        # Make calls to exceed threshold
        # Need at least min_throughput calls
        with pytest.raises(ValueError):
            await breaker.call(failing_func)
        
        with pytest.raises(ValueError):
            await breaker.call(failing_func)
        
        # Circuit should now be open
        assert breaker._state == CircuitState.OPEN
        assert breaker._stats.consecutive_failures == 2
        
        # Further calls should be rejected
        with pytest.raises(CircuitBreakerError) as exc_info:
            await breaker.call(failing_func)
        
        assert "is open" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_half_open_recovery(self, breaker):
        """Test circuit recovery through half-open state"""
        async def failing_func():
            raise ValueError("Test error")
        
        async def success_func():
            return "success"
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)
        
        assert breaker._state == CircuitState.OPEN
        
        # Wait for break duration
        await asyncio.sleep(1.1)
        
        # Next call should transition to half-open and succeed
        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker._state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_half_open_failure_reopens(self, breaker):
        """Test failure in half-open state reopens circuit"""
        async def failing_func():
            raise ValueError("Test error")
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)
        
        # Wait for break duration
        await asyncio.sleep(1.1)
        
        # Next call should transition to half-open but fail
        with pytest.raises(ValueError):
            await breaker.call(failing_func)
        
        assert breaker._state == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_sampling_window_cleanup(self, breaker):
        """Test that old calls are removed from sampling window"""
        breaker.sampling_duration = 0.5  # Short window for testing
        
        async def success_func():
            return "success"
        
        # Make some calls
        await breaker.call(success_func)
        await breaker.call(success_func)
        
        assert len(breaker._call_results) == 2
        
        # Wait for sampling window to expire
        await asyncio.sleep(0.6)
        
        # Make another call to trigger cleanup
        await breaker.call(success_func)
        
        # Old calls should be removed
        assert len(breaker._call_results) == 1


class TestCircuitBreakerStateProvider:
    """Test state monitoring functionality"""
    
    @pytest.fixture
    def monitored_breaker(self):
        """Create breaker with monitoring enabled"""
        return EnhancedCircuitBreaker(
            failure_threshold=0.5,
            min_throughput=2,
            break_duration=1.0,
            enable_monitoring=True,
            name="monitored_breaker"
        )
    
    @pytest.mark.asyncio
    async def test_state_provider_exists(self, monitored_breaker):
        """Test state provider is created when monitoring is enabled"""
        assert monitored_breaker.state_provider is not None
        assert isinstance(monitored_breaker.state_provider, CircuitBreakerStateProvider)
    
    @pytest.mark.asyncio
    async def test_state_tracking(self, monitored_breaker):
        """Test state changes are tracked"""
        provider = monitored_breaker.state_provider
        
        async def failing_func():
            raise ValueError("Test error")
        
        # Cause state change to OPEN
        for _ in range(2):
            with pytest.raises(ValueError):
                await monitored_breaker.call(failing_func)
        
        # Check state history
        history = provider._state_history
        assert len(history) > 0
        
        last_change = history[-1]
        assert last_change["from_state"] == "closed"
        assert last_change["to_state"] == "open"
        assert "Failure threshold exceeded" in last_change["reason"]
    
    @pytest.mark.asyncio
    async def test_stats_reporting(self, monitored_breaker):
        """Test comprehensive stats reporting"""
        provider = monitored_breaker.state_provider
        
        async def mixed_func():
            if monitored_breaker._stats.total_calls % 2 == 0:
                raise ValueError("Test error")
            return "success"
        
        # Make some mixed calls
        for i in range(4):
            try:
                await monitored_breaker.call(mixed_func)
            except ValueError:
                pass
        
        stats = provider.stats
        
        assert stats["state"] == "open"  # Should be open after failures
        assert stats["total_calls"] == 4
        assert "50.00%" in stats["success_rate"]
        assert stats["consecutive_failures"] > 0
        assert "ValueError" in stats["error_breakdown"]
    
    @pytest.mark.asyncio
    async def test_state_timeline(self, monitored_breaker):
        """Test retrieving state timeline"""
        provider = monitored_breaker.state_provider
        
        async def failing_func():
            raise ValueError("Test error")
        
        # Cause multiple state changes
        for _ in range(2):
            with pytest.raises(ValueError):
                await monitored_breaker.call(failing_func)
        
        # Get timeline
        timeline = provider.get_state_timeline(hours=1)
        assert len(timeline) > 0
        assert all("timestamp" in event for event in timeline)


class TestCircuitBreakerManualControl:
    """Test manual control functionality"""
    
    @pytest.fixture
    def controlled_breaker(self):
        """Create breaker with manual control enabled"""
        return EnhancedCircuitBreaker(
            failure_threshold=0.5,
            min_throughput=2,
            break_duration=1.0,
            enable_manual_control=True,
            name="controlled_breaker"
        )
    
    @pytest.mark.asyncio
    async def test_manual_control_exists(self, controlled_breaker):
        """Test manual control is created when enabled"""
        assert controlled_breaker.manual_control is not None
        assert isinstance(controlled_breaker.manual_control, CircuitBreakerManualControl)
    
    @pytest.mark.asyncio
    async def test_manual_isolation(self, controlled_breaker):
        """Test manual isolation of circuit"""
        control = controlled_breaker.manual_control
        
        async def test_func():
            return "success"
        
        # Circuit should work normally
        result = await controlled_breaker.call(test_func)
        assert result == "success"
        
        # Manually isolate
        await control.isolate("Maintenance mode")
        
        assert controlled_breaker._state == CircuitState.ISOLATED
        assert control.is_isolated is True
        
        # Calls should be rejected
        with pytest.raises(CircuitBreakerError):
            await controlled_breaker.call(test_func)
        
        # Check isolation info
        info = control.isolation_info
        assert info["reason"] == "Maintenance mode"
        assert "isolated_at" in info
    
    @pytest.mark.asyncio
    async def test_manual_reset(self, controlled_breaker):
        """Test manual reset of circuit"""
        control = controlled_breaker.manual_control
        
        async def failing_func():
            raise ValueError("Test error")
        
        # Open the circuit through failures
        for _ in range(2):
            with pytest.raises(ValueError):
                await controlled_breaker.call(failing_func)
        
        assert controlled_breaker._state == CircuitState.OPEN
        
        # Manually reset
        await control.reset()
        
        assert controlled_breaker._state == CircuitState.CLOSED
        assert controlled_breaker._stats.consecutive_failures == 0
        
        # Circuit should work again
        async def success_func():
            return "success"
        
        result = await controlled_breaker.call(success_func)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_force_half_open(self, controlled_breaker):
        """Test forcing circuit to half-open state"""
        control = controlled_breaker.manual_control
        
        async def failing_func():
            raise ValueError("Test error")
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await controlled_breaker.call(failing_func)
        
        assert controlled_breaker._state == CircuitState.OPEN
        
        # Force to half-open
        await control.force_half_open()
        
        assert controlled_breaker._state == CircuitState.HALF_OPEN
        
        # Next successful call should close it
        async def success_func():
            return "success"
        
        result = await controlled_breaker.call(success_func)
        assert result == "success"
        assert controlled_breaker._state == CircuitState.CLOSED


class TestDynamicBreakDuration:
    """Test dynamic break duration functionality"""
    
    @pytest.mark.asyncio
    async def test_exponential_break_duration(self):
        """Test exponential break duration generator"""
        breaker = EnhancedCircuitBreaker(
            failure_threshold=0.5,
            min_throughput=2,
            break_duration_generator=exponential_break_duration,
            name="exponential_breaker"
        )
        
        # Simulate increasing failures
        breaker._stats.consecutive_failures = 1
        assert breaker._calculate_break_duration() == 30.0  # Base
        
        breaker._stats.consecutive_failures = 2
        assert breaker._calculate_break_duration() == 45.0  # 30 * 1.5
        
        breaker._stats.consecutive_failures = 3
        assert breaker._calculate_break_duration() == 67.5  # 30 * 1.5^2
    
    @pytest.mark.asyncio
    async def test_linear_break_duration(self):
        """Test linear break duration generator"""
        breaker = EnhancedCircuitBreaker(
            failure_threshold=0.5,
            min_throughput=2,
            break_duration_generator=linear_break_duration,
            name="linear_breaker"
        )
        
        # Simulate increasing failures
        breaker._stats.consecutive_failures = 1
        assert breaker._calculate_break_duration() == 30.0  # Base
        
        breaker._stats.consecutive_failures = 2
        assert breaker._calculate_break_duration() == 45.0  # 30 + 15
        
        breaker._stats.consecutive_failures = 3
        assert breaker._calculate_break_duration() == 60.0  # 30 + 30
    
    @pytest.mark.asyncio
    async def test_adaptive_break_duration(self):
        """Test adaptive break duration generator"""
        breaker = EnhancedCircuitBreaker(
            failure_threshold=0.5,
            min_throughput=2,
            break_duration_generator=adaptive_break_duration,
            name="adaptive_breaker"
        )
        
        # Test different failure counts
        breaker._stats.consecutive_failures = 1
        assert breaker._calculate_break_duration() == 30.0  # Quick retry
        
        breaker._stats.consecutive_failures = 4
        assert breaker._calculate_break_duration() == 60.0  # Medium delay
        
        breaker._stats.consecutive_failures = 10
        assert breaker._calculate_break_duration() == 120.0  # Long delay
    
    @pytest.mark.asyncio
    async def test_break_duration_bounds(self):
        """Test break duration is bounded"""
        def extreme_duration(failures):
            return failures * 100  # Very long duration
        
        breaker = EnhancedCircuitBreaker(
            failure_threshold=0.5,
            min_throughput=2,
            break_duration_generator=extreme_duration,
            name="bounded_breaker"
        )
        
        breaker._stats.consecutive_failures = 10
        duration = breaker._calculate_break_duration()
        
        # Should be capped at 300 seconds (5 minutes)
        assert duration == 300.0


class TestIntegrationScenarios:
    """Test real-world integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_api_client_scenario(self):
        """Test circuit breaker with API client scenario"""
        # Simulate an API that fails intermittently
        call_count = 0
        
        async def flaky_api():
            nonlocal call_count
            call_count += 1
            
            # Fail first 3 calls, then succeed
            if call_count <= 3:
                raise ConnectionError("API unavailable")
            return {"status": "ok"}
        
        breaker = EnhancedCircuitBreaker(
            failure_threshold=0.6,
            min_throughput=2,
            break_duration=0.5,
            expected_exception=ConnectionError,
            enable_monitoring=True,
            name="api_breaker"
        )
        
        # First calls fail and open circuit
        for _ in range(2):
            with pytest.raises(ConnectionError):
                await breaker.call(flaky_api)
        
        assert breaker._state == CircuitState.OPEN
        
        # Wait for recovery
        await asyncio.sleep(0.6)
        
        # Next call should succeed and close circuit
        result = await breaker.call(flaky_api)
        assert result == {"status": "ok"}
        assert breaker._state == CircuitState.CLOSED
        
        # Check monitoring captured the recovery
        stats = breaker.state_provider.stats
        assert stats["state"] == "closed"
        assert len(stats["recent_state_changes"]) >= 2
    
    @pytest.mark.asyncio
    async def test_cascading_failure_prevention(self):
        """Test preventing cascading failures with manual control"""
        breaker1 = EnhancedCircuitBreaker(
            failure_threshold=0.5,
            min_throughput=2,
            break_duration=1.0,
            enable_manual_control=True,
            name="service1"
        )
        
        breaker2 = EnhancedCircuitBreaker(
            failure_threshold=0.5,
            min_throughput=2,
            break_duration=1.0,
            enable_manual_control=True,
            name="service2"
        )
        
        async def service1_call():
            # Service 1 depends on service 2
            if breaker2._state != CircuitState.CLOSED:
                raise RuntimeError("Dependency unavailable")
            return "service1 result"
        
        async def service2_call():
            raise ConnectionError("Service 2 down")
        
        # Service 2 fails
        for _ in range(2):
            with pytest.raises(ConnectionError):
                await breaker2.call(service2_call)
        
        # Service 2 circuit is open
        assert breaker2._state == CircuitState.OPEN
        
        # Manually isolate service 1 to prevent cascading
        await breaker1.manual_control.isolate("Dependency failure - preventing cascade")
        
        # Service 1 calls are rejected immediately
        with pytest.raises(CircuitBreakerError) as exc_info:
            await breaker1.call(service1_call)
        
        assert "isolated" in str(exc_info.value)
        
        # This prevents service 1 from being overwhelmed
        assert breaker1._stats.failed_calls == 0