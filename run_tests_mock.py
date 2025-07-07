#!/usr/bin/env python3
"""Test runner that ensures all tests run with mock API responses."""

import os
import sys
import subprocess
from pathlib import Path

def setup_test_env():
    """Set up test environment variables."""
    # Load test environment
    os.environ['OPENROUTER_API_KEY'] = 'test-api-key-12345'
    os.environ['USE_MOCK_API'] = 'true'
    os.environ['DATABASE_PATH'] = './test_pipeline.db'
    os.environ['CACHE_DIR'] = './tests/data/cache'
    
    # Ensure test data directories exist
    Path('./tests/data/cache').mkdir(parents=True, exist_ok=True)
    
    print("✅ Test environment configured")
    print(f"   OPENROUTER_API_KEY: {os.environ.get('OPENROUTER_API_KEY')}")
    print(f"   USE_MOCK_API: {os.environ.get('USE_MOCK_API')}")

def run_python_tests():
    """Run Python tests with pytest."""
    print("\n🐍 Running Python tests...")
    
    # Check if we're in virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Not in virtual environment. Activating venv...")
        activate_cmd = ". ./venv/bin/activate && "
    else:
        activate_cmd = ""
    
    # Run pytest with mock environment
    cmd = f"{activate_cmd}python -m pytest tests/python -v --tb=short"
    result = subprocess.run(cmd, shell=True)
    
    return result.returncode == 0

def run_integration_tests():
    """Run integration tests."""
    print("\n🔗 Running integration tests...")
    
    # These tests should use mock API responses
    cmd = "python -m pytest tests/integration -v --tb=short -k 'not real_api'"
    result = subprocess.run(cmd, shell=True)
    
    return result.returncode == 0

def run_rust_tests():
    """Run Rust tests."""
    print("\n🦀 Running Rust tests...")
    
    # Run Rust tests without Python feature
    cmd = "cargo test --no-default-features"
    result = subprocess.run(cmd, shell=True)
    
    return result.returncode == 0

def main():
    """Main test runner."""
    print("🚀 Running all tests with mock API responses")
    print("=" * 60)
    
    # Set up test environment
    setup_test_env()
    
    # Track results
    results = {
        'Python': False,
        'Integration': False,
        'Rust': False
    }
    
    # Run test suites
    try:
        results['Python'] = run_python_tests()
    except Exception as e:
        print(f"❌ Python tests failed with error: {e}")
    
    try:
        results['Integration'] = run_integration_tests()
    except Exception as e:
        print(f"❌ Integration tests failed with error: {e}")
    
    try:
        results['Rust'] = run_rust_tests()
    except Exception as e:
        print(f"❌ Rust tests failed with error: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    for suite, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {suite}: {status}")
    
    # Exit code
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()