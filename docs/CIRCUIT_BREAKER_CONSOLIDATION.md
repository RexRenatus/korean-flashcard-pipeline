# Circuit Breaker Consolidation Plan

## Current State
1. **circuit_breaker.py** - Main implementation with basic features
2. **api/circuit_breaker.py** - Duplicate (removed)
3. **circuit_breaker_v2.py** - Enhanced with better monitoring and ISOLATED state
4. **scripts/hooks/core/circuit_breaker.py** - Simplified sync version for hooks

## Consolidation Strategy
Since v2 has enhanced features and is only used by 2 newer components, we will:
1. Add v2 features to the main circuit_breaker.py
2. Keep backward compatibility for existing code
3. Update the 2 files using v2 to use the enhanced main version
4. Remove circuit_breaker_v2.py
5. Keep hooks version separate (different use case)

## Features to Merge
- CircuitBreakerStats dataclass for monitoring
- ISOLATED state for manual control
- Dynamic break duration
- Failure ratio threshold instead of count
- CircuitBreakerStateProvider for monitoring
- CircuitBreakerManualControl for manual override