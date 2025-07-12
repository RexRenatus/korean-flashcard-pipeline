#!/usr/bin/env python3
"""Quick test to check if our fixes are working"""

import sys
import os

# Add src/python to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'python'))

print("Testing imports...")

try:
    from flashcard_pipeline import (
        OpenRouterClient,
        VocabularyItem,
        Stage1Response,
        Stage2Response,
        CircuitBreakerOpen,
        NetworkError
    )
    print(" Main imports successful")
except Exception as e:
    print(f" Main imports failed: {e}")
    sys.exit(1)

try:
    from flashcard_pipeline.pipeline_cli import PipelineOrchestrator
    print(" PipelineOrchestrator import successful")
except Exception as e:
    print(f" PipelineOrchestrator import failed: {e}")
    sys.exit(1)

try:
    from flashcard_pipeline.models import Comparison
    print(" Comparison import successful")
except Exception as e:
    print(f" Comparison import failed: {e}")
    sys.exit(1)

print("\nTesting PipelineOrchestrator initialization...")
try:
    orchestrator = PipelineOrchestrator(
        cache_dir="/tmp/test_cache",
        rate_limit=60,
        max_concurrent=10,
        circuit_breaker_threshold=5,
        circuit_breaker_timeout=30,
        db_path="/tmp/test.db"
    )
    print(" PipelineOrchestrator initialization successful")
    
    # Test circuit breaker property
    cb = orchestrator.circuit_breaker
    print(f" Circuit breaker accessible: {cb.name}")
    print(f"  - State: {cb.state}")
    print(f"  - Threshold: {cb.failure_threshold}")
    
except Exception as e:
    print(f" PipelineOrchestrator test failed: {e}")
    import traceback
    traceback.print_exc()

print("\nAll basic checks completed!")