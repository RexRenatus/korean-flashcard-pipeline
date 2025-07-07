#!/usr/bin/env python3
"""Run Phase 1 Foundation Tests

This script runs all Phase 1 tests and provides a summary of results.
"""

import sys
import subprocess
from pathlib import Path

# Test files for Phase 1
PHASE1_TESTS = [
    "tests/unit/phase1/test_models_validation.py",
    "tests/unit/phase1/test_configuration.py", 
    "tests/unit/phase1/test_error_handling.py"
]

def run_tests():
    """Run all Phase 1 tests"""
    print("=" * 60)
    print("PHASE 1: FOUNDATION TESTING")
    print("=" * 60)
    print()
    
    # Check if pytest is installed
    try:
        import pytest
    except ImportError:
        print("ERROR: pytest not installed. Run: pip install pytest pytest-asyncio pytest-cov")
        return 1
    
    # Run each test file
    all_passed = True
    results = []
    
    for test_file in PHASE1_TESTS:
        if not Path(test_file).exists():
            print(f"WARNING: Test file not found: {test_file}")
            continue
            
        print(f"\nRunning {test_file}...")
        print("-" * 40)
        
        # Run pytest with coverage
        cmd = [
            sys.executable, "-m", "pytest",
            test_file,
            "-v",  # Verbose
            "--tb=short",  # Short traceback
            "-x",  # Stop on first failure
            "--cov=flashcard_pipeline",  # Coverage for our package
            "--cov-append",  # Append to coverage data
            "--no-cov-on-fail"  # Don't report coverage on failure
        ]
        
        result = subprocess.run(cmd, capture_output=False)
        
        if result.returncode != 0:
            all_passed = False
            results.append((test_file, "FAILED"))
        else:
            results.append((test_file, "PASSED"))
    
    # Print summary
    print("\n" + "=" * 60)
    print("PHASE 1 TEST SUMMARY")
    print("=" * 60)
    
    for test_file, status in results:
        test_name = Path(test_file).stem
        status_symbol = "✅" if status == "PASSED" else "❌"
        print(f"{status_symbol} {test_name}: {status}")
    
    print("\n" + "-" * 60)
    
    if all_passed:
        print("✅ All Phase 1 tests PASSED!")
        
        # Show coverage report
        print("\nGenerating coverage report...")
        subprocess.run([sys.executable, "-m", "coverage", "report"])
        
        return 0
    else:
        print("❌ Some Phase 1 tests FAILED!")
        print("\nNext steps:")
        print("1. Fix failing tests")
        print("2. Run individual test files to debug")
        print("3. Check test output above for details")
        
        return 1

def main():
    """Main entry point"""
    print("Setting up test environment...")
    
    # Ensure we're in the project root
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root / "src" / "python"))
    
    # Run the tests
    exit_code = run_tests()
    
    # Cleanup
    print("\nCleaning up coverage data...")
    coverage_file = Path(".coverage")
    if coverage_file.exists():
        coverage_file.unlink()
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()