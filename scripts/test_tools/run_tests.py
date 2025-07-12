#!/usr/bin/env python3
"""
Unified Test Runner
Combines functionality for running tests with coverage and analysis
"""

import argparse
import sys
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.python.flashcard_pipeline.utils import setup_logging, get_logger

logger = get_logger(__name__)


class TestRunner:
    """Comprehensive test execution and analysis tool"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.test_dir = self.project_root / "tests"
        self.coverage_dir = self.project_root / "coverage"
    
    def run_all_tests(
        self,
        pattern: str = None,
        coverage: bool = True,
        verbose: bool = False,
        failfast: bool = False
    ) -> Dict[str, Any]:
        """Run all tests with optional coverage"""
        logger.info("Running test suite...")
        
        # Build pytest command
        cmd = ["python", "-m", "pytest"]
        
        if verbose:
            cmd.append("-v")
        if failfast:
            cmd.append("-x")
        if pattern:
            cmd.extend(["-k", pattern])
        
        # Add coverage options
        if coverage:
            cmd.extend([
                "--cov=src/python/flashcard_pipeline",
                "--cov-report=term-missing",
                "--cov-report=html:coverage/html",
                "--cov-report=xml:coverage/coverage.xml",
                "--cov-report=json:coverage/coverage.json"
            ])
        
        # Add test directory
        cmd.append(str(self.test_dir))
        
        # Run tests
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Parse results
        test_results = {
            "command": " ".join(cmd),
            "return_code": result.returncode,
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timestamp": datetime.now().isoformat()
        }
        
        # Parse coverage if available
        if coverage and (self.coverage_dir / "coverage.json").exists():
            test_results["coverage"] = self._parse_coverage()
        
        return test_results
    
    def run_specific_tests(
        self,
        test_files: List[str],
        coverage: bool = True,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """Run specific test files"""
        logger.info(f"Running {len(test_files)} test file(s)...")
        
        # Build pytest command
        cmd = ["python", "-m", "pytest"]
        
        if verbose:
            cmd.append("-v")
        
        if coverage:
            cmd.extend([
                "--cov=src/python/flashcard_pipeline",
                "--cov-report=term-missing"
            ])
        
        # Add test files
        cmd.extend(test_files)
        
        # Run tests
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            "command": " ".join(cmd),
            "return_code": result.returncode,
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    
    def run_by_phase(self, phase: int) -> Dict[str, Any]:
        """Run tests for a specific phase"""
        phase_patterns = {
            1: "test_unit_phase1_",
            2: "test_unit_phase2_",
            3: "test_integration_",
            4: "test_pipeline_",
            5: "test_e2e_"
        }
        
        pattern = phase_patterns.get(phase)
        if not pattern:
            raise ValueError(f"Invalid phase: {phase}")
        
        logger.info(f"Running Phase {phase} tests...")
        return self.run_all_tests(pattern=pattern)
    
    def analyze_coverage(self) -> Dict[str, Any]:
        """Analyze test coverage in detail"""
        coverage_file = self.coverage_dir / "coverage.json"
        
        if not coverage_file.exists():
            raise FileNotFoundError("No coverage data found. Run tests with coverage first.")
        
        coverage_data = self._parse_coverage()
        
        # Analyze by module
        module_coverage = {}
        for file_path, file_data in coverage_data.get("files", {}).items():
            module = self._get_module_from_path(file_path)
            if module not in module_coverage:
                module_coverage[module] = {
                    "files": 0,
                    "statements": 0,
                    "missing": 0,
                    "coverage": 0
                }
            
            module_coverage[module]["files"] += 1
            module_coverage[module]["statements"] += file_data["summary"]["num_statements"]
            module_coverage[module]["missing"] += file_data["summary"]["missing_lines"]
        
        # Calculate module percentages
        for module_data in module_coverage.values():
            if module_data["statements"] > 0:
                module_data["coverage"] = (
                    (module_data["statements"] - module_data["missing"]) 
                    / module_data["statements"] * 100
                )
        
        return {
            "total_coverage": coverage_data["totals"]["percent_covered"],
            "total_statements": coverage_data["totals"]["num_statements"],
            "total_missing": coverage_data["totals"]["missing_lines"],
            "by_module": module_coverage,
            "uncovered_files": self._find_uncovered_files(coverage_data)
        }
    
    def generate_report(self, format: str = "text") -> str:
        """Generate test report in various formats"""
        # Get latest test results
        analysis = self.analyze_coverage()
        
        if format == "json":
            return json.dumps(analysis, indent=2)
        
        elif format == "markdown":
            return self._generate_markdown_report(analysis)
        
        else:  # text format
            return self._generate_text_report(analysis)
    
    def _parse_coverage(self) -> Dict[str, Any]:
        """Parse coverage JSON file"""
        coverage_file = self.coverage_dir / "coverage.json"
        with open(coverage_file) as f:
            return json.load(f)
    
    def _get_module_from_path(self, file_path: str) -> str:
        """Extract module name from file path"""
        parts = Path(file_path).parts
        
        # Find the module after flashcard_pipeline
        try:
            idx = parts.index("flashcard_pipeline")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        except ValueError:
            pass
        
        return "other"
    
    def _find_uncovered_files(self, coverage_data: Dict[str, Any]) -> List[str]:
        """Find files with low coverage"""
        uncovered = []
        threshold = 80  # Consider files under 80% as needing attention
        
        for file_path, file_data in coverage_data.get("files", {}).items():
            coverage = file_data["summary"]["percent_covered"]
            if coverage < threshold:
                uncovered.append({
                    "file": file_path,
                    "coverage": coverage,
                    "missing_lines": file_data["summary"]["missing_lines"]
                })
        
        return sorted(uncovered, key=lambda x: x["coverage"])
    
    def _generate_text_report(self, analysis: Dict[str, Any]) -> str:
        """Generate text format report"""
        lines = []
        lines.append("=" * 60)
        lines.append("TEST COVERAGE REPORT")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        lines.append("")
        
        # Overall coverage
        lines.append(f"Total Coverage: {analysis['total_coverage']:.1f}%")
        lines.append(f"Total Statements: {analysis['total_statements']:,}")
        lines.append(f"Missing Lines: {analysis['total_missing']:,}")
        lines.append("")
        
        # Module breakdown
        lines.append("Coverage by Module:")
        lines.append("-" * 40)
        for module, data in sorted(analysis["by_module"].items()):
            lines.append(
                f"{module:<20} {data['coverage']:>5.1f}% "
                f"({data['statements'] - data['missing']}/{data['statements']})"
            )
        lines.append("")
        
        # Files needing attention
        if analysis["uncovered_files"]:
            lines.append("Files Needing Attention (< 80% coverage):")
            lines.append("-" * 40)
            for file_info in analysis["uncovered_files"][:10]:
                lines.append(
                    f"{Path(file_info['file']).name:<30} "
                    f"{file_info['coverage']:>5.1f}%"
                )
        
        return "\n".join(lines)
    
    def _generate_markdown_report(self, analysis: Dict[str, Any]) -> str:
        """Generate markdown format report"""
        lines = []
        lines.append("# Test Coverage Report")
        lines.append("")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Coverage**: {analysis['total_coverage']:.1f}%")
        lines.append(f"- **Total Statements**: {analysis['total_statements']:,}")
        lines.append(f"- **Missing Lines**: {analysis['total_missing']:,}")
        lines.append("")
        
        # Module table
        lines.append("## Coverage by Module")
        lines.append("")
        lines.append("| Module | Coverage | Statements | Missing |")
        lines.append("|--------|----------|------------|---------|")
        
        for module, data in sorted(analysis["by_module"].items()):
            lines.append(
                f"| {module} | {data['coverage']:.1f}% | "
                f"{data['statements']} | {data['missing']} |"
            )
        lines.append("")
        
        # Files needing attention
        if analysis["uncovered_files"]:
            lines.append("## Files Needing Attention")
            lines.append("")
            lines.append("Files with coverage below 80%:")
            lines.append("")
            
            for file_info in analysis["uncovered_files"][:10]:
                lines.append(
                    f"- `{Path(file_info['file']).name}` - "
                    f"{file_info['coverage']:.1f}% coverage"
                )
        
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Test Runner - Execute and analyze test suite"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run tests")
    run_parser.add_argument(
        "--pattern",
        "-k",
        help="Run tests matching pattern"
    )
    run_parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2, 3, 4, 5],
        help="Run tests for specific phase"
    )
    run_parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Run without coverage"
    )
    run_parser.add_argument(
        "--failfast",
        "-x",
        action="store_true",
        help="Stop on first failure"
    )
    run_parser.add_argument(
        "files",
        nargs="*",
        help="Specific test files to run"
    )
    
    # Coverage command
    coverage_parser = subparsers.add_parser("coverage", help="Analyze coverage")
    coverage_parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Report format"
    )
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate test report")
    report_parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Report format"
    )
    
    # Global options
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Setup logging
    setup_logging(verbose=args.verbose)
    
    # Create test runner
    runner = TestRunner()
    
    try:
        if args.command == "run":
            if args.files:
                # Run specific files
                result = runner.run_specific_tests(
                    args.files,
                    coverage=not args.no_coverage,
                    verbose=args.verbose
                )
            elif args.phase:
                # Run phase tests
                result = runner.run_by_phase(args.phase)
            else:
                # Run all tests
                result = runner.run_all_tests(
                    pattern=args.pattern,
                    coverage=not args.no_coverage,
                    verbose=args.verbose,
                    failfast=args.failfast
                )
            
            # Print output
            print(result["stdout"])
            if result["stderr"]:
                print(result["stderr"], file=sys.stderr)
            
            return result["return_code"]
        
        elif args.command == "coverage":
            analysis = runner.analyze_coverage()
            report = runner.generate_report(format=args.format)
            print(report)
            return 0
        
        elif args.command == "report":
            report = runner.generate_report(format=args.format)
            print(report)
            return 0
        
    except Exception as e:
        logger.error(f"Command failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())