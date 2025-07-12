"""Unit tests for the enhanced retry system"""

import asyncio
import pytest
import time
from unittest.mock import Mock, patch, AsyncMock

from flashcard_pipeline.utils.retry import RetryConfig, retry_async, retry_sync, retry_with_config
from flashcard_pipeline.exceptions import RetryExhausted


class TestRetryConfig:
    """Test RetryConfig functionality"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert config.retry_on == (Exception,)
    
    def test_calculate_delay_without_jitter(self):
        """Test delay calculation without jitter"""
        config = RetryConfig(
            initial_delay=1.0,
            exponential_base=2.0,
            max_delay=10.0,
            jitter=False
        )
        
        # Test exponential backoff
        assert config.calculate_delay(0) == 1.0  # 1 * 2^0
        assert config.calculate_delay(1) == 2.0  # 1 * 2^1
        assert config.calculate_delay(2) == 4.0  # 1 * 2^2
        assert config.calculate_delay(3) == 8.0  # 1 * 2^3
        
        # Test max delay cap
        assert config.calculate_delay(10) == 10.0  # Should cap at max_delay
    
    def test_calculate_delay_with_jitter(self):
        """Test delay calculation with jitter"""
        config = RetryConfig(
            initial_delay=1.0,
            exponential_base=2.0,
            jitter=True
        )
        
        # Run multiple times to test jitter randomness
        delays = [config.calculate_delay(1) for _ in range(100)]
        
        # All delays should be between 1.0 and 2.0 (base delay is 2.0)
        assert all(1.0 <= d <= 2.0 for d in delays)
        
        # Should have some variation due to jitter
        assert len(set(delays)) > 50  # At least 50 different values


class TestRetryAsync:
    """Test async retry decorator"""
    
    @pytest.mark.asyncio
    async def test_successful_call(self):
        """Test successful function call without retries"""
        call_count = 0
        
        @retry_async(RetryConfig(max_attempts=3))
        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await success_func()
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_on_exception(self):
        """Test retry on expected exception"""
        call_count = 0
        
        @retry_async(RetryConfig(
            max_attempts=3,
            initial_delay=0.01,  # Fast for testing
            retry_on=(ValueError,)
        ))
        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Test error")
            return "success"
        
        result = await failing_func()
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Test retry exhaustion"""
        call_count = 0
        
        @retry_async(RetryConfig(
            max_attempts=3,
            initial_delay=0.01,
            retry_on=(ValueError,)
        ))
        async def always_failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Test error")
        
        with pytest.raises(RetryExhausted) as exc_info:
            await always_failing_func()
        
        assert call_count == 3
        assert "Retry exhausted after 3 attempts" in str(exc_info.value)
        assert isinstance(exc_info.value.last_exception, ValueError)
    
    @pytest.mark.asyncio
    async def test_no_retry_on_unexpected_exception(self):
        """Test no retry on unexpected exception type"""
        call_count = 0
        
        @retry_async(RetryConfig(
            max_attempts=3,
            retry_on=(ValueError,)
        ))
        async def unexpected_error_func():
            nonlocal call_count
            call_count += 1
            raise TypeError("Unexpected error")
        
        with pytest.raises(TypeError):
            await unexpected_error_func()
        
        assert call_count == 1  # No retries
    
    @pytest.mark.asyncio
    async def test_delay_between_retries(self):
        """Test delay is applied between retries"""
        call_times = []
        
        @retry_async(RetryConfig(
            max_attempts=3,
            initial_delay=0.1,
            jitter=False,
            retry_on=(ValueError,)
        ))
        async def timed_func():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ValueError("Test error")
            return "success"
        
        start_time = time.time()
        result = await timed_func()
        
        assert result == "success"
        assert len(call_times) == 3
        
        # Check delays between calls
        # First retry after ~0.1s (initial_delay * 2^0)
        assert 0.08 < call_times[1] - call_times[0] < 0.12
        
        # Second retry after ~0.2s (initial_delay * 2^1)
        assert 0.18 < call_times[2] - call_times[1] < 0.22


class TestRetrySync:
    """Test sync retry decorator"""
    
    def test_successful_call(self):
        """Test successful function call without retries"""
        call_count = 0
        
        @retry_sync(RetryConfig(max_attempts=3))
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = success_func()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_on_exception(self):
        """Test retry on expected exception"""
        call_count = 0
        
        @retry_sync(RetryConfig(
            max_attempts=3,
            initial_delay=0.01,
            retry_on=(ValueError,)
        ))
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Test error")
            return "success"
        
        result = failing_func()
        assert result == "success"
        assert call_count == 3
    
    def test_function_metadata_preserved(self):
        """Test that function metadata is preserved"""
        @retry_sync()
        def documented_func():
            """This is a documented function"""
            return "result"
        
        assert documented_func.__name__ == "documented_func"
        assert documented_func.__doc__ == "This is a documented function"


class TestRetryWithConfig:
    """Test retry_with_config function"""
    
    @pytest.mark.asyncio
    async def test_retry_with_custom_config(self):
        """Test retry with custom configuration"""
        call_count = 0
        
        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Test error")
            return "success"
        
        config = RetryConfig(
            max_attempts=3,
            initial_delay=0.01,
            retry_on=(ValueError,)
        )
        
        result = await retry_with_config(failing_func, config=config)
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_with_args_and_kwargs(self):
        """Test retry with function arguments"""
        call_count = 0
        
        async def func_with_args(a, b, c=None):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Test error")
            return f"{a}-{b}-{c}"
        
        config = RetryConfig(
            max_attempts=3,
            initial_delay=0.01,
            retry_on=(ValueError,)
        )
        
        result = await retry_with_config(
            func_with_args,
            "arg1",
            "arg2",
            config=config,
            c="kwarg"
        )
        
        assert result == "arg1-arg2-kwarg"
        assert call_count == 2


class TestIntegrationScenarios:
    """Test real-world integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_api_call_simulation(self):
        """Simulate API call with retries"""
        # Simulate an API that fails twice then succeeds
        api_calls = []
        
        @retry_async(RetryConfig(
            max_attempts=5,
            initial_delay=0.01,
            exponential_base=2.0,
            jitter=True,
            retry_on=(ConnectionError, TimeoutError)
        ))
        async def simulated_api_call():
            api_calls.append(time.time())
            
            if len(api_calls) <= 2:
                raise ConnectionError("Network error")
            
            return {"status": "success", "data": "result"}
        
        result = await simulated_api_call()
        
        assert result == {"status": "success", "data": "result"}
        assert len(api_calls) == 3
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self):
        """Test retry with circuit breaker pattern"""
        from flashcard_pipeline.exceptions import CircuitBreakerError
        
        circuit_open = True
        
        @retry_async(RetryConfig(
            max_attempts=3,
            initial_delay=0.01,
            retry_on=(CircuitBreakerError,)
        ))
        async def circuit_protected_call():
            nonlocal circuit_open
            
            if circuit_open:
                # Simulate circuit opening after first attempt
                circuit_open = False
                raise CircuitBreakerError(
                    "Circuit breaker open",
                    service="test",
                    failure_count=5,
                    threshold=5
                )
            
            return "success"
        
        result = await circuit_protected_call()
        assert result == "success"
    
    def test_logging_integration(self, caplog):
        """Test retry logging"""
        import logging
        
        @retry_sync(RetryConfig(
            max_attempts=3,
            initial_delay=0.01,
            retry_on=(ValueError,)
        ))
        def logged_func():
            if len(caplog.records) < 2:
                raise ValueError("Test error")
            return "success"
        
        with caplog.at_level(logging.WARNING):
            result = logged_func()
        
        assert result == "success"
        
        # Check log messages
        assert len(caplog.records) >= 2
        assert "Retry 1/3" in caplog.records[0].message
        assert "Retry 2/3" in caplog.records[1].message
        assert "ValueError: Test error" in caplog.records[0].message