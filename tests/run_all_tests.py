#!/usr/bin/env python
"""
Unified test runner for the Korean Flashcard Pipeline project.
Runs all test suites with appropriate configuration.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode != 0:
        print(f"\n❌ {description} failed with exit code {result.returncode}")
        return False
    
    print(f"\n✅ {description} passed")
    return True


def main():
    parser = argparse.ArgumentParser(description="Run all tests for Korean Flashcard Pipeline")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("--performance", action="store_true", help="Run only performance tests")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    
    args = parser.parse_args()
    
    # Base pytest command
    pytest_cmd = [sys.executable, "-m", "pytest"]
    
    if args.verbose:
        pytest_cmd.append("-vv")
    else:
        pytest_cmd.append("-v")
    
    # Add coverage options
    if args.coverage:
        pytest_cmd.extend([
            "--cov=flashcard_pipeline",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov"
        ])
    
    # Test selection
    if args.unit:
        pytest_cmd.extend(["-m", "unit"])
    elif args.integration:
        pytest_cmd.extend(["-m", "integration"])
    elif args.performance:
        pytest_cmd.extend(["-m", "performance"])
    
    # Skip slow tests if requested
    if args.fast:
        pytest_cmd.extend(["-m", "not slow"])
    
    all_passed = True
    
    # Run Python tests
    if not run_command(pytest_cmd, "Python Tests"):
        all_passed = False
    
    # Run Rust tests if not specific test type requested
    if not (args.unit or args.integration or args.performance):
        rust_cmd = ["cargo", "test"]
        if args.verbose:
            rust_cmd.append("--verbose")
            
        if Path("Cargo.toml").exists():
            if not run_command(rust_cmd, "Rust Tests"):
                all_passed = False
    
    # Summary
    print("\n" + "="*60)
    if all_passed:
        print("✅ All tests passed!")
        if args.coverage:
            print(f"📊 Coverage report generated at: {Path('htmlcov/index.html').absolute()}")
    else:
        print("❌ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()