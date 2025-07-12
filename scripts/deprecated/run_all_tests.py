#!/usr/bin/env python3
"""Comprehensive test runner for the Korean Flashcard Pipeline.

This script runs all test suites, generates coverage reports,
performance benchmarks, and security audit results.
"""

import sys
import os
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestRunner:
    """Orchestrates running all test suites."""
    
    def __init__(self, verbose: bool = False, parallel: bool = True):
        self.verbose = verbose
        self.parallel = parallel
        self.results = {
            'timestamp': datetime.utcnow().isoformat(),
            'suites': {},
            'summary': {
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 0,
                'errors': 0,
                'duration': 0
            }
        }
    
    def run_pytest_suite(self, suite_name: str, test_path: str, 
                        extra_args: List[str] = None) -> Dict[str, Any]:
        """Run a pytest test suite and capture results."""
        print(f"\n{'='*60}")
        print(f"Running {suite_name} tests...")
        print(f"{'='*60}")
        
        cmd = [
            sys.executable, '-m', 'pytest',
            test_path,
            '--tb=short',
            '--no-header',
            '-v' if self.verbose else '-q',
            '--json-report',
            f'--json-report-file=.test-reports/{suite_name}.json'
        ]
        
        if extra_args:
            cmd.extend(extra_args)
        
        if self.parallel and 'performance' not in suite_name:
            cmd.extend(['-n', 'auto'])  # Use pytest-xdist for parallel execution
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=project_root
            )
            
            duration = time.time() - start_time
            
            # Parse JSON report
            report_path = project_root / f'.test-reports/{suite_name}.json'
            if report_path.exists():
                with open(report_path, 'r') as f:
                    json_report = json.load(f)
                
                return {
                    'status': 'passed' if result.returncode == 0 else 'failed',
                    'duration': duration,
                    'total': json_report['summary']['total'],
                    'passed': json_report['summary']['passed'],
                    'failed': json_report['summary']['failed'],
                    'skipped': json_report['summary']['skipped'],
                    'error': json_report['summary']['error'],
                    'stdout': result.stdout if self.verbose else '',
                    'stderr': result.stderr if result.returncode != 0 else ''
                }
            else:
                # Fallback parsing from output
                return self._parse_pytest_output(result, duration)
                
        except Exception as e:
            return {
                'status': 'error',
                'duration': time.time() - start_time,
                'error': str(e),
                'stdout': '',
                'stderr': ''
            }
    
    def _parse_pytest_output(self, result: subprocess.CompletedProcess, 
                           duration: float) -> Dict[str, Any]:
        """Parse pytest output when JSON report is not available."""
        output = result.stdout
        
        # Extract test counts from output
        import re
        
        passed = len(re.findall(r'PASSED', output))
        failed = len(re.findall(r'FAILED', output))
        skipped = len(re.findall(r'SKIPPED', output))
        errors = len(re.findall(r'ERROR', output))
        
        total = passed + failed + skipped + errors
        
        return {
            'status': 'passed' if result.returncode == 0 else 'failed',
            'duration': duration,
            'total': total,
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'error': errors,
            'stdout': output if self.verbose else '',
            'stderr': result.stderr
        }
    
    def run_coverage_analysis(self) -> Dict[str, Any]:
        """Run coverage analysis across all test suites."""
        print(f"\n{'='*60}")
        print("Running Coverage Analysis...")
        print(f"{'='*60}")
        
        cmd = [
            sys.executable, '-m', 'pytest',
            'tests/',
            '--cov=src/python/flashcard_pipeline',
            '--cov-report=term-missing',
            '--cov-report=html:.test-reports/coverage',
            '--cov-report=json:.test-reports/coverage.json',
            '-q'
        ]
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=project_root
            )
            
            duration = time.time() - start_time
            
            # Parse coverage JSON
            coverage_path = project_root / '.test-reports/coverage.json'
            if coverage_path.exists():
                with open(coverage_path, 'r') as f:
                    coverage_data = json.load(f)
                
                return {
                    'status': 'completed',
                    'duration': duration,
                    'total_coverage': coverage_data['totals']['percent_covered'],
                    'files': coverage_data['files'],
                    'missing_lines': coverage_data['totals']['missing_lines'],
                    'covered_lines': coverage_data['totals']['covered_lines']
                }
            else:
                # Parse from output
                coverage_match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', result.stdout)
                coverage_percent = int(coverage_match.group(1)) if coverage_match else 0
                
                return {
                    'status': 'completed',
                    'duration': duration,
                    'total_coverage': coverage_percent,
                    'output': result.stdout
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'duration': time.time() - start_time,
                'error': str(e)
            }
    
    def run_security_audit(self) -> Dict[str, Any]:
        """Run security audit using bandit and safety."""
        print(f"\n{'='*60}")
        print("Running Security Audit...")
        print(f"{'='*60}")
        
        results = {}
        
        # Run bandit for static security analysis
        print("\n→ Running Bandit security scan...")
        bandit_cmd = [
            sys.executable, '-m', 'bandit',
            '-r', 'src/python/flashcard_pipeline',
            '-f', 'json',
            '-o', '.test-reports/bandit.json'
        ]
        
        try:
            bandit_result = subprocess.run(
                bandit_cmd,
                capture_output=True,
                text=True,
                cwd=project_root
            )
            
            # Parse bandit results
            bandit_path = project_root / '.test-reports/bandit.json'
            if bandit_path.exists():
                with open(bandit_path, 'r') as f:
                    bandit_data = json.load(f)
                
                results['bandit'] = {
                    'status': 'completed',
                    'issues': len(bandit_data.get('results', [])),
                    'severity_high': sum(1 for r in bandit_data.get('results', []) 
                                       if r['issue_severity'] == 'HIGH'),
                    'severity_medium': sum(1 for r in bandit_data.get('results', []) 
                                         if r['issue_severity'] == 'MEDIUM'),
                    'severity_low': sum(1 for r in bandit_data.get('results', []) 
                                      if r['issue_severity'] == 'LOW')
                }
        except Exception as e:
            results['bandit'] = {'status': 'error', 'error': str(e)}
        
        # Run safety check for dependency vulnerabilities
        print("\n→ Running Safety dependency check...")
        safety_cmd = [
            sys.executable, '-m', 'safety', 'check',
            '--json', '--output', '.test-reports/safety.json'
        ]
        
        try:
            safety_result = subprocess.run(
                safety_cmd,
                capture_output=True,
                text=True,
                cwd=project_root
            )
            
            # Parse safety results
            safety_path = project_root / '.test-reports/safety.json'
            if safety_path.exists():
                with open(safety_path, 'r') as f:
                    safety_data = json.load(f)
                
                results['safety'] = {
                    'status': 'completed',
                    'vulnerabilities': len(safety_data),
                    'packages': [v['package'] for v in safety_data]
                }
        except Exception as e:
            results['safety'] = {'status': 'error', 'error': str(e)}
        
        return results
    
    def run_performance_benchmarks(self) -> Dict[str, Any]:
        """Run performance benchmarks."""
        print(f"\n{'='*60}")
        print("Running Performance Benchmarks...")
        print(f"{'='*60}")
        
        # Run performance tests with benchmarking
        result = self.run_pytest_suite(
            'performance',
            'tests/performance/',
            extra_args=['--benchmark-only', '-m', 'performance']
        )
        
        # Extract benchmark results if available
        benchmark_path = project_root / '.test-reports/benchmark.json'
        if benchmark_path.exists():
            with open(benchmark_path, 'r') as f:
                benchmark_data = json.load(f)
            
            result['benchmarks'] = benchmark_data.get('benchmarks', [])
        
        return result
    
    def generate_report(self) -> str:
        """Generate a comprehensive test report."""
        report_lines = [
            "# Korean Flashcard Pipeline - Test Report",
            f"\nGenerated: {self.results['timestamp']}",
            "\n## Summary",
            f"- Total Tests: {self.results['summary']['total_tests']}",
            f"- Passed: {self.results['summary']['passed']} ✓",
            f"- Failed: {self.results['summary']['failed']} ✗",
            f"- Skipped: {self.results['summary']['skipped']} ⚠",
            f"- Errors: {self.results['summary']['errors']} ⚠",
            f"- Total Duration: {self.results['summary']['duration']:.2f}s",
            "\n## Test Suites"
        ]
        
        for suite_name, suite_results in self.results['suites'].items():
            status_icon = '✓' if suite_results.get('status') == 'passed' else '✗'
            report_lines.extend([
                f"\n### {suite_name} {status_icon}",
                f"- Status: {suite_results.get('status', 'unknown')}",
                f"- Duration: {suite_results.get('duration', 0):.2f}s"
            ])
            
            if 'total' in suite_results:
                report_lines.extend([
                    f"- Total: {suite_results['total']}",
                    f"- Passed: {suite_results.get('passed', 0)}",
                    f"- Failed: {suite_results.get('failed', 0)}",
                    f"- Skipped: {suite_results.get('skipped', 0)}"
                ])
            
            if suite_results.get('stderr'):
                report_lines.extend([
                    "\n#### Errors:",
                    "```",
                    suite_results['stderr'][:500],  # Limit error output
                    "```"
                ])
        
        # Add coverage report
        if 'coverage' in self.results:
            coverage = self.results['coverage']
            report_lines.extend([
                "\n## Code Coverage",
                f"- Total Coverage: {coverage.get('total_coverage', 0):.1f}%",
                f"- Covered Lines: {coverage.get('covered_lines', 0)}",
                f"- Missing Lines: {coverage.get('missing_lines', 0)}"
            ])
        
        # Add security report
        if 'security' in self.results:
            security = self.results['security']
            report_lines.extend([
                "\n## Security Audit",
            ])
            
            if 'bandit' in security:
                bandit = security['bandit']
                report_lines.extend([
                    "\n### Static Analysis (Bandit)",
                    f"- High Severity: {bandit.get('severity_high', 0)}",
                    f"- Medium Severity: {bandit.get('severity_medium', 0)}",
                    f"- Low Severity: {bandit.get('severity_low', 0)}"
                ])
            
            if 'safety' in security:
                safety = security['safety']
                report_lines.extend([
                    "\n### Dependency Vulnerabilities (Safety)",
                    f"- Vulnerabilities Found: {safety.get('vulnerabilities', 0)}"
                ])
                
                if safety.get('packages'):
                    report_lines.append("- Affected Packages: " + 
                                      ', '.join(safety['packages'][:5]))
        
        return '\n'.join(report_lines)
    
    def run_all_tests(self):
        """Run all test suites and generate reports."""
        # Create test reports directory
        reports_dir = project_root / '.test-reports'
        reports_dir.mkdir(exist_ok=True)
        
        # Define test suites
        test_suites = [
            ('Unit Tests - Phase 1', 'tests/unit/phase1/'),
            ('Unit Tests - Phase 2', 'tests/unit/phase2/'),
            ('Integration Tests', 'tests/integration/'),
            ('Performance Tests', 'tests/performance/'),
            ('Security Tests', 'tests/security/'),
        ]
        
        # Run each test suite
        for suite_name, test_path in test_suites:
            suite_results = self.run_pytest_suite(suite_name, test_path)
            self.results['suites'][suite_name] = suite_results
            
            # Update summary
            self.results['summary']['total_tests'] += suite_results.get('total', 0)
            self.results['summary']['passed'] += suite_results.get('passed', 0)
            self.results['summary']['failed'] += suite_results.get('failed', 0)
            self.results['summary']['skipped'] += suite_results.get('skipped', 0)
            self.results['summary']['errors'] += suite_results.get('error', 0)
            self.results['summary']['duration'] += suite_results.get('duration', 0)
        
        # Run coverage analysis
        self.results['coverage'] = self.run_coverage_analysis()
        
        # Run security audit
        self.results['security'] = self.run_security_audit()
        
        # Generate and save report
        report = self.generate_report()
        report_path = reports_dir / 'test_report.md'
        with open(report_path, 'w') as f:
            f.write(report)
        
        # Save JSON results
        json_path = reports_dir / 'test_results.json'
        with open(json_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n{'='*60}")
        print("Test Run Complete!")
        print(f"{'='*60}")
        print(f"\nReport saved to: {report_path}")
        print(f"JSON results saved to: {json_path}")
        print(f"\nTotal tests: {self.results['summary']['total_tests']}")
        print(f"Passed: {self.results['summary']['passed']}")
        print(f"Failed: {self.results['summary']['failed']}")
        
        # Return exit code based on failures
        return 0 if self.results['summary']['failed'] == 0 else 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run all tests for the Korean Flashcard Pipeline'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--no-parallel',
        action='store_true',
        help='Disable parallel test execution'
    )
    
    args = parser.parse_args()
    
    runner = TestRunner(
        verbose=args.verbose,
        parallel=not args.no_parallel
    )
    
    return runner.run_all_tests()


if __name__ == '__main__':
    sys.exit(main())