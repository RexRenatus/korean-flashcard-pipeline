#!/usr/bin/env python3
"""
Circuit breaker for hook execution to prevent cascading failures.
"""
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import threading
import logging

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

@dataclass
class CircuitStats:
    failures: int = 0
    successes: int = 0
    last_failure: Optional[datetime] = None
    last_success: Optional[datetime] = None
    consecutive_failures: int = 0
    state_changed_at: datetime = field(default_factory=datetime.now)

class CircuitBreaker:
    def __init__(self,
                 failure_threshold: int = 3,
                 success_threshold: int = 2,
                 timeout: timedelta = timedelta(seconds=60),
                 half_open_limit: int = 1):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.half_open_limit = half_open_limit
        self.circuits: Dict[str, CircuitStats] = {}
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
    def is_open(self, hook_id: str) -> bool:
        """Check if circuit is open for a hook."""
        with self.lock:
            if hook_id not in self.circuits:
                return False
                
            state = self._get_state(hook_id)
            return state == CircuitState.OPEN
            
    def can_execute(self, hook_id: str) -> bool:
        """Check if hook can be executed."""
        state = self._get_state(hook_id)
        
        if state == CircuitState.CLOSED:
            return True
            
        if state == CircuitState.HALF_OPEN:
            with self.lock:
                stats = self.circuits.get(hook_id)
                # Allow limited requests in half-open state
                return stats.successes < self.half_open_limit
                
        return False  # OPEN state
        
    def record_success(self, hook_id: str):
        """Record successful execution."""
        with self.lock:
            if hook_id not in self.circuits:
                self.circuits[hook_id] = CircuitStats()
                
            stats = self.circuits[hook_id]
            stats.successes += 1
            stats.last_success = datetime.now()
            stats.consecutive_failures = 0
            
            # Check state transition
            current_state = self._get_state(hook_id)
            if current_state == CircuitState.HALF_OPEN:
                if stats.successes >= self.success_threshold:
                    # Close the circuit
                    self._transition_to_closed(hook_id)
                    
    def record_failure(self, hook_id: str):
        """Record failed execution."""
        with self.lock:
            if hook_id not in self.circuits:
                self.circuits[hook_id] = CircuitStats()
                
            stats = self.circuits[hook_id]
            stats.failures += 1
            stats.consecutive_failures += 1
            stats.last_failure = datetime.now()
            
            # Check state transition
            if stats.consecutive_failures >= self.failure_threshold:
                self._transition_to_open(hook_id)
                
    def _get_state(self, hook_id: str) -> CircuitState:
        """Get current circuit state."""
        if hook_id not in self.circuits:
            return CircuitState.CLOSED
            
        stats = self.circuits[hook_id]
        
        if stats.consecutive_failures >= self.failure_threshold:
            # Check if timeout has passed
            if datetime.now() - stats.state_changed_at > self.timeout:
                # Transition to half-open
                self._transition_to_half_open(hook_id)
                return CircuitState.HALF_OPEN
            return CircuitState.OPEN
            
        return CircuitState.CLOSED
        
    def _transition_to_open(self, hook_id: str):
        """Transition circuit to open state."""
        stats = self.circuits[hook_id]
        stats.state_changed_at = datetime.now()
        self.logger.warning(f"Circuit breaker OPEN for hook: {hook_id}")
        
    def _transition_to_half_open(self, hook_id: str):
        """Transition circuit to half-open state."""
        stats = self.circuits[hook_id]
        stats.state_changed_at = datetime.now()
        stats.successes = 0  # Reset success counter
        self.logger.info(f"Circuit breaker HALF-OPEN for hook: {hook_id}")
        
    def _transition_to_closed(self, hook_id: str):
        """Transition circuit to closed state."""
        stats = self.circuits[hook_id]
        stats.state_changed_at = datetime.now()
        stats.failures = 0
        stats.consecutive_failures = 0
        self.logger.info(f"Circuit breaker CLOSED for hook: {hook_id}")
        
    def get_stats(self, hook_id: str) -> Optional[Dict[str, Any]]:
        """Get circuit breaker stats for monitoring."""
        with self.lock:
            if hook_id not in self.circuits:
                return None
                
            stats = self.circuits[hook_id]
            state = self._get_state(hook_id)
            
            return {
                'state': state.value,
                'failures': stats.failures,
                'successes': stats.successes,
                'consecutive_failures': stats.consecutive_failures,
                'last_failure': stats.last_failure.isoformat() if stats.last_failure else None,
                'last_success': stats.last_success.isoformat() if stats.last_success else None,
                'state_changed_at': stats.state_changed_at.isoformat()
            }
            
    def reset(self, hook_id: str):
        """Manually reset circuit breaker for a hook."""
        with self.lock:
            if hook_id in self.circuits:
                del self.circuits[hook_id]
                self.logger.info(f"Circuit breaker reset for hook: {hook_id}")

# Global circuit breaker instance
_circuit_breaker = None

def get_circuit_breaker() -> CircuitBreaker:
    """Get global circuit breaker instance."""
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = CircuitBreaker()
    return _circuit_breaker

if __name__ == "__main__":
    # Test circuit breaker
    logging.basicConfig(level=logging.INFO)
    cb = CircuitBreaker(failure_threshold=2, timeout=timedelta(seconds=5))
    
    # Test hook
    hook_id = "test_hook"
    
    print(f"Can execute: {cb.can_execute(hook_id)}")  # True
    
    # Record failures
    cb.record_failure(hook_id)
    print(f"After 1 failure - Can execute: {cb.can_execute(hook_id)}")  # True
    
    cb.record_failure(hook_id)
    print(f"After 2 failures - Can execute: {cb.can_execute(hook_id)}")  # False (OPEN)
    
    print(f"Stats: {cb.get_stats(hook_id)}")
    
    # Wait for timeout
    print("Waiting for timeout...")
    import time
    time.sleep(6)
    
    print(f"After timeout - Can execute: {cb.can_execute(hook_id)}")  # True (HALF-OPEN)
    
    # Record success
    cb.record_success(hook_id)
    cb.record_success(hook_id)
    print(f"After 2 successes - Can execute: {cb.can_execute(hook_id)}")  # True (CLOSED)