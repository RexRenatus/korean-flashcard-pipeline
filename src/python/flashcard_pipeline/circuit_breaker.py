"""Circuit breaker pattern implementation with database tracking"""

import asyncio
import time
import json
import sqlite3
from typing import Optional, Callable, Any, Dict, List, Tuple
from enum import Enum
from datetime import datetime, timedelta
from contextlib import contextmanager
from pathlib import Path
from dataclasses import dataclass, field
import logging

from .exceptions import CircuitBreakerError


logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject all calls
    HALF_OPEN = "half_open"  # Testing if service recovered
    ISOLATED = "isolated"  # Manually forced open (from v2)


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker monitoring (from v2)"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_changes: List[Dict[str, Any]] = field(default_factory=list)
    error_counts: Dict[str, int] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_calls == 0:
            return 1.0
        return self.successful_calls / self.total_calls
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate"""
        return 1.0 - self.success_rate


class CircuitBreaker:
    """Circuit breaker for API calls"""
    
    def __init__(self,
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: type = Exception,
                 name: str = "circuit_breaker"):
        """Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying half-open
            expected_exception: Exception type to catch
            name: Name for logging
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name
        
        # State tracking
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state_changed_at = time.time()
        
        # Statistics
        self._call_count = 0
        self._success_count = 0
        self._failure_stats: Dict[str, int] = {}
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    @property
    def state(self) -> str:
        """Get current circuit state as string"""
        return self._state.value
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker
        
        Args:
            func: Async function to call
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result from func
            
        Raises:
            CircuitBreakerError: If circuit is open
        """
        async with self._lock:
            self._call_count += 1
            
            # Check if we should transition from OPEN to HALF_OPEN
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    self._state_changed_at = time.time()
                    logger.info(f"{self.name}: Transitioning to HALF_OPEN")
                else:
                    raise CircuitBreakerError(
                        f"{self.name} is OPEN",
                        service=self.name,
                        failure_count=self._failure_count,
                        threshold=self.failure_threshold
                    )
        
        # Try to execute the function
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except self.expected_exception as e:
            await self._on_failure(e)
            raise
    
    async def _on_success(self):
        """Handle successful call"""
        async with self._lock:
            self._success_count += 1
            
            if self._state == CircuitState.HALF_OPEN:
                # Success in half-open state, close the circuit
                logger.info(f"{self.name}: Success in HALF_OPEN, closing circuit")
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._state_changed_at = time.time()
    
    async def _on_failure(self, exception: Exception):
        """Handle failed call"""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            # Track failure types
            error_type = type(exception).__name__
            self._failure_stats[error_type] = self._failure_stats.get(error_type, 0) + 1
            
            if self._state == CircuitState.HALF_OPEN:
                # Failure in half-open state, reopen the circuit
                logger.warning(f"{self.name}: Failure in HALF_OPEN, reopening circuit")
                self._state = CircuitState.OPEN
                self._state_changed_at = time.time()
            
            elif self._failure_count >= self.failure_threshold:
                # Too many failures, open the circuit
                logger.warning(
                    f"{self.name}: Failure threshold reached ({self._failure_count}), "
                    f"opening circuit"
                )
                self._state = CircuitState.OPEN
                self._state_changed_at = time.time()
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try reset"""
        return (
            self._last_failure_time and
            time.time() - self._last_failure_time >= self.recovery_timeout
        )
    
    async def reset(self):
        """Manually reset the circuit breaker"""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._state_changed_at = time.time()
            logger.info(f"{self.name}: Manually reset to CLOSED")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        success_rate = 0.0
        if self._call_count > 0:
            success_rate = (self._success_count / self._call_count) * 100
        
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "call_count": self._call_count,
            "success_count": self._success_count,
            "success_rate": success_rate,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "state_duration": time.time() - self._state_changed_at,
            "failure_types": self._failure_stats
        }


class MultiServiceCircuitBreaker:
    """Manages circuit breakers for multiple services"""
    
    def __init__(self):
        """Initialize multi-service circuit breaker"""
        self.breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
    
    async def get_breaker(self, service: str, **kwargs) -> CircuitBreaker:
        """Get or create circuit breaker for a service
        
        Args:
            service: Service name
            **kwargs: Arguments for CircuitBreaker if creating new
            
        Returns:
            Circuit breaker for the service
        """
        async with self._lock:
            if service not in self.breakers:
                # Use a default failure_threshold of 3 if not specified
                if 'failure_threshold' not in kwargs:
                    kwargs['failure_threshold'] = 3
                self.breakers[service] = CircuitBreaker(
                    name=service,
                    **kwargs
                )
            return self.breakers[service]
    
    async def call(self, service: str, func: Callable, *args, **kwargs) -> Any:
        """Call function through service's circuit breaker
        
        Args:
            service: Service name
            func: Function to call
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result from func
        """
        breaker = await self.get_breaker(service)
        return await breaker.call(func, *args, **kwargs)
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers"""
        return {
            service: breaker.get_stats()
            for service, breaker in self.breakers.items()
        }
    
    async def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self.breakers.values():
            await breaker.reset()


class AdaptiveCircuitBreaker(CircuitBreaker):
    """Circuit breaker that adapts thresholds based on patterns"""
    
    def __init__(self, 
                 initial_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: type = Exception,
                 name: str = "adaptive_circuit_breaker"):
        super().__init__(initial_threshold, recovery_timeout, expected_exception, name)
        
        # Adaptive parameters
        self.min_threshold = 3
        self.max_threshold = 20
        self.threshold_adjustment = 2
        
        # Pattern tracking
        self._error_timestamps: list[float] = []
        self._error_pattern_window = 300  # 5 minutes
    
    async def _on_failure(self, exception: Exception):
        """Handle failure with pattern detection"""
        current_time = time.time()
        
        async with self._lock:
            # Add to error timestamps
            self._error_timestamps.append(current_time)
            
            # Clean old timestamps
            cutoff = current_time - self._error_pattern_window
            self._error_timestamps = [t for t in self._error_timestamps if t > cutoff]
            
            # Detect error burst pattern (check when we have at least 3 errors)
            if len(self._error_timestamps) >= min(3, self.failure_threshold):
                # Calculate error rate
                time_span = self._error_timestamps[-1] - self._error_timestamps[0]
                if time_span > 0:
                    error_rate = len(self._error_timestamps) / time_span
                    
                    # Adjust threshold based on error rate
                    if error_rate > 0.5:  # More than 1 error per 2 seconds
                        # Lower threshold for faster circuit opening
                        self.failure_threshold = max(
                            self.min_threshold,
                            self.failure_threshold - self.threshold_adjustment
                        )
                        logger.info(
                            f"{self.name}: High error rate detected, "
                            f"lowering threshold to {self.failure_threshold}"
                        )
        
        # Call parent implementation
        await super()._on_failure(exception)
    
    async def _on_success(self):
        """Handle success with threshold recovery"""
        async with self._lock:
            # Clear error timestamps on success
            self._error_timestamps.clear()
            
            # Gradually increase threshold on sustained success
            if self._success_count % 10 == 0:
                self.failure_threshold = min(
                    self.max_threshold,
                    self.failure_threshold + 1
                )
                logger.debug(
                    f"{self.name}: Sustained success, "
                    f"increasing threshold to {self.failure_threshold}"
                )
        
        await super()._on_success()


class DatabaseCircuitBreaker(CircuitBreaker):
    """Circuit breaker with database persistence and intelligent pattern analysis"""
    
    def __init__(self,
                 db_path: str = "pipeline.db",
                 service_name: str = "default",
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: type = Exception,
                 enable_alerts: bool = True,
                 alert_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        """Initialize database-backed circuit breaker
        
        Args:
            db_path: Path to SQLite database
            service_name: Unique service identifier
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying half-open
            expected_exception: Exception type to catch
            enable_alerts: Whether to generate alerts
            alert_callback: Optional callback for alerts
        """
        super().__init__(failure_threshold, recovery_timeout, expected_exception, service_name)
        
        self.db_path = db_path
        self.service_name = service_name
        self.enable_alerts = enable_alerts
        self.alert_callback = alert_callback
        
        # Pattern detection parameters
        self.pattern_window = 300  # 5 minutes
        self.min_events_for_pattern = 5
        
        # Metrics tracking
        self._metrics_buffer: List[Dict[str, Any]] = []
        self._last_metrics_flush = time.time()
        self._metrics_flush_interval = 60  # Flush every minute
        
        # Initialize database state
        self._initialize_database()
        self._load_state()
    
    @contextmanager
    def _get_db_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _initialize_database(self):
        """Ensure service exists in database"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if service exists
            cursor.execute(
                "SELECT 1 FROM circuit_breaker_states WHERE service_name = ?",
                (self.service_name,)
            )
            
            if not cursor.fetchone():
                # Create initial state
                cursor.execute("""
                    INSERT INTO circuit_breaker_states 
                    (service_name, current_state, failure_count, failure_threshold, recovery_timeout)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    self.service_name,
                    CircuitState.CLOSED.value,
                    0,
                    self.failure_threshold,
                    self.recovery_timeout
                ))
                conn.commit()
    
    def _load_state(self):
        """Load circuit state from database"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT current_state, failure_count, failure_threshold, recovery_timeout,
                       last_failure_time, state_changed_at
                FROM circuit_breaker_states
                WHERE service_name = ?
            """, (self.service_name,))
            
            row = cursor.fetchone()
            if row:
                self._state = CircuitState(row['current_state'])
                self._failure_count = row['failure_count']
                self.failure_threshold = row['failure_threshold']
                self.recovery_timeout = row['recovery_timeout']
                
                if row['last_failure_time']:
                    # Convert ISO format to timestamp
                    dt = datetime.fromisoformat(row['last_failure_time'].replace('Z', '+00:00'))
                    self._last_failure_time = dt.timestamp()
                
                if row['state_changed_at']:
                    dt = datetime.fromisoformat(row['state_changed_at'].replace('Z', '+00:00'))
                    self._state_changed_at = dt.timestamp()
    
    def _save_state(self):
        """Save current state to database"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE circuit_breaker_states
                SET current_state = ?, failure_count = ?, 
                    last_failure_time = ?, state_changed_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE service_name = ?
            """, (
                self._state.value,
                self._failure_count,
                datetime.fromtimestamp(self._last_failure_time).isoformat() if self._last_failure_time else None,
                datetime.fromtimestamp(self._state_changed_at).isoformat(),
                self.service_name
            ))
            conn.commit()
    
    def _record_event(self, event_type: str, from_state: Optional[str] = None,
                      to_state: Optional[str] = None, error_type: Optional[str] = None,
                      error_message: Optional[str] = None, additional_data: Optional[Dict] = None):
        """Record an event in the database"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO circuit_breaker_events
                (service_name, event_type, from_state, to_state, failure_count,
                 error_type, error_message, additional_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.service_name,
                event_type,
                from_state,
                to_state,
                self._failure_count,
                error_type,
                error_message,
                json.dumps(additional_data) if additional_data else None
            ))
            conn.commit()
    
    def _create_alert(self, alert_type: str, severity: str, message: str, details: Optional[Dict] = None):
        """Create an alert in the database and optionally call callback"""
        if not self.enable_alerts:
            return
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO circuit_breaker_alerts
                (service_name, alert_type, severity, message, details)
                VALUES (?, ?, ?, ?, ?)
            """, (
                self.service_name,
                alert_type,
                severity,
                message,
                json.dumps(details) if details else None
            ))
            conn.commit()
        
        # Call alert callback if provided
        if self.alert_callback:
            alert_data = {
                'service_name': self.service_name,
                'alert_type': alert_type,
                'severity': severity,
                'message': message,
                'details': details,
                'timestamp': datetime.now().isoformat()
            }
            try:
                self.alert_callback(alert_data)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    async def _on_state_change(self, from_state: CircuitState, to_state: CircuitState):
        """Handle state changes with database tracking"""
        self._record_event(
            event_type='state_change',
            from_state=from_state.value,
            to_state=to_state.value
        )
        
        # Create alerts for significant state changes
        if to_state == CircuitState.OPEN:
            self._create_alert(
                alert_type='circuit_opened',
                severity='error',
                message=f"Circuit breaker for {self.service_name} has opened after {self._failure_count} failures",
                details={'failure_count': self._failure_count, 'threshold': self.failure_threshold}
            )
        elif from_state == CircuitState.OPEN and to_state == CircuitState.CLOSED:
            self._create_alert(
                alert_type='circuit_closed',
                severity='info',
                message=f"Circuit breaker for {self.service_name} has recovered and closed",
                details={'recovery_time': time.time() - self._state_changed_at}
            )
        
        self._save_state()
    
    async def _on_success(self):
        """Handle successful call with database tracking"""
        old_state = self._state
        await super()._on_success()
        
        self._record_event(event_type='success')
        
        if old_state != self._state:
            await self._on_state_change(old_state, self._state)
        
        # Add to metrics buffer
        self._metrics_buffer.append({
            'timestamp': time.time(),
            'success': True,
            'state': self._state.value
        })
        
        # Flush metrics if needed
        await self._flush_metrics_if_needed()
    
    async def _on_failure(self, exception: Exception):
        """Handle failed call with database tracking and pattern analysis"""
        old_state = self._state
        error_type = type(exception).__name__
        error_message = str(exception)
        
        await super()._on_failure(exception)
        
        self._record_event(
            event_type='failure',
            error_type=error_type,
            error_message=error_message
        )
        
        if old_state != self._state:
            await self._on_state_change(old_state, self._state)
        
        # Add to metrics buffer
        self._metrics_buffer.append({
            'timestamp': time.time(),
            'success': False,
            'state': self._state.value,
            'error_type': error_type
        })
        
        # Analyze failure patterns
        await self._analyze_failure_patterns()
        
        # Flush metrics if needed
        await self._flush_metrics_if_needed()
    
    async def _analyze_failure_patterns(self):
        """Analyze recent failures to detect patterns and suggest optimizations"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get recent events
            cutoff_time = (datetime.now() - timedelta(seconds=self.pattern_window)).isoformat()
            cursor.execute("""
                SELECT event_type, error_type, created_at
                FROM circuit_breaker_events
                WHERE service_name = ? AND created_at > ?
                ORDER BY created_at DESC
            """, (self.service_name, cutoff_time))
            
            events = cursor.fetchall()
            
            if len(events) < self.min_events_for_pattern:
                return
            
            # Calculate failure metrics
            failures = [e for e in events if e['event_type'] == 'failure']
            if not failures:
                return
            
            failure_count = len(failures)
            time_span = (datetime.now() - datetime.fromisoformat(events[-1]['created_at'].replace('Z', '+00:00'))).total_seconds()
            
            if time_span <= 0:
                return
            
            error_rate = failure_count / time_span
            
            # Count error types
            error_counts = {}
            for f in failures:
                error_type = f['error_type'] or 'unknown'
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
            
            most_common_error = max(error_counts, key=error_counts.get)
            
            # Determine pattern type
            pattern_type = self._classify_pattern(events, time_span)
            
            # Calculate suggested thresholds
            suggested_threshold, suggested_timeout, confidence = self._calculate_optimal_thresholds(
                error_rate, pattern_type, failure_count, time_span
            )
            
            # Record pattern
            cursor.execute("""
                INSERT INTO circuit_breaker_failure_patterns
                (service_name, pattern_type, time_window_seconds, failure_count,
                 error_rate, most_common_error, suggested_threshold, suggested_timeout, confidence_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.service_name,
                pattern_type,
                int(time_span),
                failure_count,
                error_rate,
                most_common_error,
                suggested_threshold,
                suggested_timeout,
                confidence
            ))
            conn.commit()
            
            # Create alert if pattern suggests threshold adjustment
            if confidence > 0.7 and (
                abs(suggested_threshold - self.failure_threshold) > 2 or
                abs(suggested_timeout - self.recovery_timeout) > 30
            ):
                self._create_alert(
                    alert_type='threshold_recommendation',
                    severity='warning',
                    message=f"Pattern analysis suggests adjusting thresholds for {self.service_name}",
                    details={
                        'current_threshold': self.failure_threshold,
                        'suggested_threshold': suggested_threshold,
                        'current_timeout': self.recovery_timeout,
                        'suggested_timeout': suggested_timeout,
                        'pattern_type': pattern_type,
                        'confidence': confidence
                    }
                )
    
    def _classify_pattern(self, events: List[sqlite3.Row], time_span: float) -> str:
        """Classify the failure pattern type"""
        if not events:
            return 'unknown'
        
        # Calculate inter-event times
        event_times = [datetime.fromisoformat(e['created_at'].replace('Z', '+00:00')).timestamp() 
                      for e in events if e['event_type'] == 'failure']
        
        if len(event_times) < 2:
            return 'intermittent'
        
        inter_times = [event_times[i] - event_times[i+1] for i in range(len(event_times)-1)]
        avg_inter_time = sum(inter_times) / len(inter_times)
        
        # Classify based on timing patterns
        if max(inter_times) < 5:  # All failures within 5 seconds
            return 'burst'
        elif all(abs(t - avg_inter_time) < avg_inter_time * 0.3 for t in inter_times):
            return 'steady'
        elif len([t for t in inter_times if t > 60]) > len(inter_times) / 2:
            return 'intermittent'
        else:
            # Check if failure rate is increasing
            first_half = event_times[:len(event_times)//2]
            second_half = event_times[len(event_times)//2:]
            
            if len(first_half) > 1 and len(second_half) > 1:
                first_rate = len(first_half) / (first_half[0] - first_half[-1])
                second_rate = len(second_half) / (second_half[0] - second_half[-1])
                
                if second_rate > first_rate * 1.5:
                    return 'escalating'
        
        return 'intermittent'
    
    def _calculate_optimal_thresholds(self, error_rate: float, pattern_type: str,
                                    failure_count: int, time_span: float) -> Tuple[int, int, float]:
        """Calculate optimal thresholds based on pattern analysis"""
        confidence = 0.5  # Base confidence
        
        # Adjust based on pattern type
        if pattern_type == 'burst':
            # For burst patterns, lower threshold and longer timeout
            suggested_threshold = max(3, min(failure_count // 2, 10))
            suggested_timeout = min(300, int(time_span * 2))
            confidence = 0.8
        elif pattern_type == 'steady':
            # For steady patterns, threshold based on rate
            suggested_threshold = max(3, min(int(error_rate * 30), 15))
            suggested_timeout = int(60 / error_rate) if error_rate > 0 else 60
            confidence = 0.9
        elif pattern_type == 'escalating':
            # For escalating patterns, aggressive thresholds
            suggested_threshold = max(3, failure_count // 3)
            suggested_timeout = 120
            confidence = 0.85
        else:  # intermittent
            # For intermittent patterns, moderate thresholds
            suggested_threshold = max(5, min(failure_count, 10))
            suggested_timeout = 90
            confidence = 0.6
        
        # Ensure reasonable bounds
        suggested_threshold = max(3, min(suggested_threshold, 20))
        suggested_timeout = max(30, min(suggested_timeout, 600))
        
        return suggested_threshold, suggested_timeout, confidence
    
    async def _flush_metrics_if_needed(self):
        """Flush metrics buffer to database if needed"""
        current_time = time.time()
        if current_time - self._last_metrics_flush < self._metrics_flush_interval:
            return
        
        if not self._metrics_buffer:
            return
        
        # Calculate metrics for the period
        period_start = datetime.fromtimestamp(self._last_metrics_flush)
        period_end = datetime.fromtimestamp(current_time)
        
        total_calls = len(self._metrics_buffer)
        successful_calls = sum(1 for m in self._metrics_buffer if m['success'])
        failed_calls = total_calls - successful_calls
        
        # Calculate circuit open duration
        open_duration = sum(
            m['timestamp'] - self._metrics_buffer[i-1]['timestamp']
            for i, m in enumerate(self._metrics_buffer)
            if i > 0 and m['state'] == 'open'
        )
        
        circuit_open_count = sum(
            1 for i, m in enumerate(self._metrics_buffer)
            if i > 0 and m['state'] == 'open' and self._metrics_buffer[i-1]['state'] != 'open'
        )
        
        # Store metrics
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO circuit_breaker_metrics
                (service_name, measurement_period_start, measurement_period_end,
                 total_calls, successful_calls, failed_calls,
                 circuit_open_count, circuit_open_duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.service_name,
                period_start.isoformat(),
                period_end.isoformat(),
                total_calls,
                successful_calls,
                failed_calls,
                circuit_open_count,
                int(open_duration)
            ))
            conn.commit()
        
        # Check for high failure rate
        if total_calls > 10 and failed_calls / total_calls > 0.5:
            self._create_alert(
                alert_type='high_failure_rate',
                severity='warning',
                message=f"High failure rate detected for {self.service_name}: {failed_calls}/{total_calls} calls failed",
                details={
                    'failure_rate': failed_calls / total_calls,
                    'total_calls': total_calls,
                    'period_minutes': (current_time - self._last_metrics_flush) / 60
                }
            )
        
        # Clear buffer and update flush time
        self._metrics_buffer.clear()
        self._last_metrics_flush = current_time
    
    async def reset(self):
        """Manually reset the circuit breaker with database tracking"""
        old_state = self._state
        await super().reset()
        
        self._record_event(event_type='manual_reset', from_state=old_state.value, to_state=self._state.value)
        self._save_state()
        
        self._create_alert(
            alert_type='circuit_closed',
            severity='info',
            message=f"Circuit breaker for {self.service_name} was manually reset",
            details={'from_state': old_state.value}
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics including database metrics"""
        base_stats = super().get_stats()
        
        # Add database-specific stats
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get recent patterns
            cursor.execute("""
                SELECT pattern_type, confidence_score, suggested_threshold, suggested_timeout
                FROM circuit_breaker_failure_patterns
                WHERE service_name = ?
                ORDER BY detected_at DESC
                LIMIT 1
            """, (self.service_name,))
            
            pattern_row = cursor.fetchone()
            if pattern_row:
                base_stats['latest_pattern'] = {
                    'type': pattern_row['pattern_type'],
                    'confidence': pattern_row['confidence_score'],
                    'suggested_threshold': pattern_row['suggested_threshold'],
                    'suggested_timeout': pattern_row['suggested_timeout']
                }
            
            # Get recent metrics
            cursor.execute("""
                SELECT SUM(total_calls) as total, SUM(successful_calls) as success,
                       SUM(failed_calls) as failed, SUM(circuit_open_duration_seconds) as open_duration
                FROM circuit_breaker_metrics
                WHERE service_name = ? AND measurement_period_start > datetime('now', '-1 hour')
            """, (self.service_name,))
            
            metrics_row = cursor.fetchone()
            if metrics_row and metrics_row['total']:
                base_stats['last_hour_metrics'] = {
                    'total_calls': metrics_row['total'],
                    'success_rate': (metrics_row['success'] / metrics_row['total']) * 100,
                    'circuit_open_duration': metrics_row['open_duration']
                }
            
            # Get unacknowledged alerts count
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM circuit_breaker_alerts
                WHERE service_name = ? AND acknowledged = FALSE
            """, (self.service_name,))
            
            alerts_row = cursor.fetchone()
            base_stats['unacknowledged_alerts'] = alerts_row['count']
        
        return base_stats
    
    def get_recommendations(self) -> Dict[str, Any]:
        """Get intelligent recommendations based on patterns"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get recent patterns with high confidence
            cursor.execute("""
                SELECT pattern_type, suggested_threshold, suggested_timeout, 
                       confidence_score, error_rate, most_common_error
                FROM circuit_breaker_failure_patterns
                WHERE service_name = ? AND confidence_score > 0.7
                ORDER BY detected_at DESC
                LIMIT 5
            """, (self.service_name,))
            
            patterns = cursor.fetchall()
            
            if not patterns:
                return {
                    'has_recommendations': False,
                    'message': 'Insufficient data for recommendations'
                }
            
            # Average the suggestions weighted by confidence
            total_confidence = sum(p['confidence_score'] for p in patterns)
            avg_threshold = sum(p['suggested_threshold'] * p['confidence_score'] for p in patterns) / total_confidence
            avg_timeout = sum(p['suggested_timeout'] * p['confidence_score'] for p in patterns) / total_confidence
            
            # Determine if adjustment is needed
            threshold_diff = abs(avg_threshold - self.failure_threshold)
            timeout_diff = abs(avg_timeout - self.recovery_timeout)
            
            recommendations = {
                'has_recommendations': threshold_diff > 1 or timeout_diff > 15,
                'current_threshold': self.failure_threshold,
                'recommended_threshold': int(avg_threshold),
                'current_timeout': self.recovery_timeout,
                'recommended_timeout': int(avg_timeout),
                'confidence': total_confidence / len(patterns),
                'based_on_patterns': len(patterns),
                'most_common_error': patterns[0]['most_common_error'],
                'primary_pattern': patterns[0]['pattern_type']
            }
            
            if recommendations['has_recommendations']:
                recommendations['message'] = f"Based on {len(patterns)} recent patterns, " \
                    f"consider adjusting threshold to {int(avg_threshold)} " \
                    f"and timeout to {int(avg_timeout)} seconds"
            else:
                recommendations['message'] = "Current settings appear optimal"
            
            return recommendations


class MultiServiceDatabaseCircuitBreaker(MultiServiceCircuitBreaker):
    """Manages database-backed circuit breakers for multiple services"""
    
    def __init__(self, db_path: str = "pipeline.db", enable_alerts: bool = True,
                 alert_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        """Initialize multi-service database circuit breaker
        
        Args:
            db_path: Path to SQLite database
            enable_alerts: Whether to generate alerts
            alert_callback: Optional callback for alerts
        """
        super().__init__()
        self.db_path = db_path
        self.enable_alerts = enable_alerts
        self.alert_callback = alert_callback
    
    async def get_breaker(self, service: str, **kwargs) -> DatabaseCircuitBreaker:
        """Get or create database-backed circuit breaker for a service"""
        async with self._lock:
            if service not in self.breakers:
                # Merge provided kwargs with defaults
                breaker_kwargs = {
                    'db_path': self.db_path,
                    'service_name': service,
                    'enable_alerts': self.enable_alerts,
                    'alert_callback': self.alert_callback
                }
                breaker_kwargs.update(kwargs)
                
                self.breakers[service] = DatabaseCircuitBreaker(**breaker_kwargs)
            return self.breakers[service]
    
    def get_all_recommendations(self) -> Dict[str, Dict[str, Any]]:
        """Get recommendations for all services"""
        return {
            service: breaker.get_recommendations()
            for service, breaker in self.breakers.items()
            if isinstance(breaker, DatabaseCircuitBreaker)
        }
    
    def get_services_needing_attention(self) -> List[str]:
        """Get list of services with unacknowledged alerts or recommendations"""
        services = []
        for service, breaker in self.breakers.items():
            if isinstance(breaker, DatabaseCircuitBreaker):
                stats = breaker.get_stats()
                recommendations = breaker.get_recommendations()
                
                if stats.get('unacknowledged_alerts', 0) > 0 or recommendations.get('has_recommendations', False):
                    services.append(service)
        
        return services