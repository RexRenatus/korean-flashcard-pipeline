#!/usr/bin/env python3
"""Coverage analysis tool for the Korean Flashcard Pipeline.

This script generates detailed coverage reports, identifies untested code paths,
provides module-by-module breakdown, and suggests test improvements.
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass
from collections import defaultdict
import ast

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class CoverageData:
    """Holds coverage data for a file."""
    filename: str
    total_lines: int
    covered_lines: int
    missing_lines: List[int]
    coverage_percent: float
    uncovered_functions: List[str]
    uncovered_classes: List[str]


@dataclass
class TestSuggestion:
    """Suggestion for improving test coverage."""
    file: str
    line_range: Tuple[int, int]
    suggestion_type: str
    description: str
    priority: str  # 'high', 'medium', 'low'
    example_test: Optional[str] = None


class CoverageAnalyzer:
    """Analyzes code coverage and suggests improvements."""
    
    def __init__(self, source_dir: str = 'src/python/flashcard_pipeline'):
        self.source_dir = Path(source_dir)
        self.project_root = project_root
        self.coverage_data: Dict[str, CoverageData] = {}
        self.suggestions: List[TestSuggestion] = []
    
    def run_coverage(self) -> bool:
        """Run pytest with coverage and collect results."""
        print("Running tests with coverage analysis...")
        
        cmd = [
            sys.executable, '-m', 'pytest',
            'tests/',
            f'--cov={self.source_dir}',
            '--cov-report=json:.coverage.json',
            '--cov-report=term-missing',
            '-q'
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.project_root
        )
        
        if result.returncode != 0:
            print(f"Warning: Some tests failed:\n{result.stderr}")
        
        # Load coverage data
        coverage_file = self.project_root / '.coverage.json'
        if not coverage_file.exists():
            print("Error: Coverage data not found")
            return False
        
        with open(coverage_file, 'r') as f:
            self.raw_coverage = json.load(f)
        
        return True
    
    def analyze_coverage(self):
        """Analyze coverage data and identify gaps."""
        files = self.raw_coverage.get('files', {})
        
        for filepath, file_data in files.items():
            # Convert to relative path
            rel_path = Path(filepath).relative_to(self.project_root)
            
            # Extract coverage metrics
            executed_lines = set(file_data.get('executed_lines', []))
            missing_lines = file_data.get('missing_lines', [])
            total_statements = file_data.get('summary', {}).get('num_statements', 0)
            
            if total_statements == 0:
                continue
            
            coverage_percent = (len(executed_lines) / total_statements) * 100
            
            # Analyze uncovered code
            uncovered_functions, uncovered_classes = self._analyze_uncovered_code(
                self.project_root / rel_path, 
                missing_lines
            )
            
            self.coverage_data[str(rel_path)] = CoverageData(
                filename=str(rel_path),
                total_lines=total_statements,
                covered_lines=len(executed_lines),
                missing_lines=missing_lines,
                coverage_percent=coverage_percent,
                uncovered_functions=uncovered_functions,
                uncovered_classes=uncovered_classes
            )
    
    def _analyze_uncovered_code(self, filepath: Path, 
                               missing_lines: List[int]) -> Tuple[List[str], List[str]]:
        """Identify uncovered functions and classes."""
        if not filepath.exists():
            return [], []
        
        try:
            with open(filepath, 'r') as f:
                source = f.read()
            
            tree = ast.parse(source, filename=str(filepath))
        except Exception:
            return [], []
        
        missing_set = set(missing_lines)
        uncovered_functions = []
        uncovered_classes = []
        
        class CodeAnalyzer(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                # Check if function has any uncovered lines
                func_lines = set(range(node.lineno, node.end_lineno + 1))
                if func_lines & missing_set:
                    coverage = 1 - (len(func_lines & missing_set) / len(func_lines))
                    if coverage < 0.5:  # Less than 50% covered
                        uncovered_functions.append(f"{node.name} (line {node.lineno})")
                self.generic_visit(node)
            
            def visit_AsyncFunctionDef(self, node):
                self.visit_FunctionDef(node)
            
            def visit_ClassDef(self, node):
                # Check if class has any uncovered lines
                class_lines = set(range(node.lineno, node.end_lineno + 1))
                if class_lines & missing_set:
                    coverage = 1 - (len(class_lines & missing_set) / len(class_lines))
                    if coverage < 0.5:  # Less than 50% covered
                        uncovered_classes.append(f"{node.name} (line {node.lineno})")
                self.generic_visit(node)
        
        analyzer = CodeAnalyzer()
        analyzer.visit(tree)
        
        return uncovered_functions, uncovered_classes
    
    def generate_suggestions(self):
        """Generate test improvement suggestions."""
        for filepath, coverage in self.coverage_data.items():
            # High priority: Files with < 50% coverage
            if coverage.coverage_percent < 50:
                self.suggestions.append(TestSuggestion(
                    file=filepath,
                    line_range=(0, 0),
                    suggestion_type='low_coverage',
                    description=f"File has only {coverage.coverage_percent:.1f}% coverage",
                    priority='high'
                ))
            
            # Suggest tests for uncovered functions
            for func in coverage.uncovered_functions:
                self.suggestions.append(TestSuggestion(
                    file=filepath,
                    line_range=(0, 0),
                    suggestion_type='uncovered_function',
                    description=f"Function '{func}' lacks test coverage",
                    priority='high' if 'init' in func or 'process' in func else 'medium'
                ))
            
            # Suggest tests for uncovered classes
            for cls in coverage.uncovered_classes:
                self.suggestions.append(TestSuggestion(
                    file=filepath,
                    line_range=(0, 0),
                    suggestion_type='uncovered_class',
                    description=f"Class '{cls}' lacks comprehensive test coverage",
                    priority='high'
                ))
            
            # Analyze specific patterns
            self._analyze_code_patterns(filepath, coverage)
    
    def _analyze_code_patterns(self, filepath: str, coverage: CoverageData):
        """Analyze code for specific patterns that need testing."""
        full_path = self.project_root / filepath
        
        if not full_path.exists():
            return
        
        try:
            with open(full_path, 'r') as f:
                lines = f.readlines()
        except Exception:
            return
        
        # Look for error handling blocks
        for i, line in enumerate(lines, 1):
            if i in coverage.missing_lines:
                line_stripped = line.strip()
                
                # Exception handling
                if line_stripped.startswith(('except', 'raise')):
                    self.suggestions.append(TestSuggestion(
                        file=filepath,
                        line_range=(i, i),
                        suggestion_type='error_handling',
                        description=f"Exception handling on line {i} not tested",
                        priority='high',
                        example_test=self._generate_exception_test_example(filepath, i)
                    ))
                
                # Edge cases (None checks, empty collections)
                elif 'if not' in line_stripped or '== None' in line_stripped:
                    self.suggestions.append(TestSuggestion(
                        file=filepath,
                        line_range=(i, i),
                        suggestion_type='edge_case',
                        description=f"Edge case on line {i} not tested",
                        priority='medium'
                    ))
                
                # Validation logic
                elif 'validate' in line_stripped.lower() or 'check' in line_stripped.lower():
                    self.suggestions.append(TestSuggestion(
                        file=filepath,
                        line_range=(i, i),
                        suggestion_type='validation',
                        description=f"Validation logic on line {i} not tested",
                        priority='high'
                    ))
    
    def _generate_exception_test_example(self, filepath: str, line_num: int) -> str:
        """Generate example test for exception handling."""
        module_name = Path(filepath).stem
        
        return f"""
@pytest.mark.asyncio
async def test_{module_name}_exception_handling():
    '''Test exception handling on line {line_num} of {filepath}'''
    # Arrange
    # Set up conditions to trigger the exception
    
    # Act & Assert
    with pytest.raises(ExpectedException):
        # Call the function/method that should raise
        pass
"""
    
    def generate_module_report(self) -> Dict[str, Any]:
        """Generate module-by-module coverage breakdown."""
        modules = defaultdict(lambda: {
            'files': [],
            'total_lines': 0,
            'covered_lines': 0,
            'coverage_percent': 0.0
        })
        
        for filepath, coverage in self.coverage_data.items():
            # Extract module from filepath
            parts = Path(filepath).parts
            if len(parts) > 3:  # src/python/flashcard_pipeline/...
                module = parts[3]
            else:
                module = 'root'
            
            modules[module]['files'].append(filepath)
            modules[module]['total_lines'] += coverage.total_lines
            modules[module]['covered_lines'] += coverage.covered_lines
        
        # Calculate module coverage
        for module, data in modules.items():
            if data['total_lines'] > 0:
                data['coverage_percent'] = (
                    data['covered_lines'] / data['total_lines'] * 100
                )
        
        return dict(modules)
    
    def generate_report(self) -> str:
        """Generate comprehensive coverage report."""
        if not self.coverage_data:
            return "No coverage data available"
        
        # Calculate totals
        total_lines = sum(c.total_lines for c in self.coverage_data.values())
        covered_lines = sum(c.covered_lines for c in self.coverage_data.values())
        overall_coverage = (covered_lines / total_lines * 100) if total_lines > 0 else 0
        
        report_lines = [
            "# Coverage Analysis Report",
            f"\n## Overall Coverage: {overall_coverage:.1f}%",
            f"- Total Lines: {total_lines}",
            f"- Covered Lines: {covered_lines}",
            f"- Missing Lines: {total_lines - covered_lines}",
            "\n## Module Breakdown"
        ]
        
        # Module breakdown
        modules = self.generate_module_report()
        for module, data in sorted(modules.items(), 
                                  key=lambda x: x[1]['coverage_percent'], 
                                  reverse=True):
            report_lines.extend([
                f"\n### {module}",
                f"- Coverage: {data['coverage_percent']:.1f}%",
                f"- Files: {len(data['files'])}",
                f"- Lines: {data['covered_lines']}/{data['total_lines']}"
            ])
        
        # Files with lowest coverage
        report_lines.append("\n## Files Needing Attention")
        
        worst_files = sorted(
            self.coverage_data.values(),
            key=lambda x: x.coverage_percent
        )[:10]
        
        for file_data in worst_files:
            if file_data.coverage_percent < 80:
                report_lines.extend([
                    f"\n### {file_data.filename}",
                    f"- Coverage: {file_data.coverage_percent:.1f}%",
                    f"- Missing Lines: {len(file_data.missing_lines)}"
                ])
                
                if file_data.uncovered_functions:
                    report_lines.append("- Uncovered Functions:")
                    for func in file_data.uncovered_functions[:5]:
                        report_lines.append(f"  - {func}")
                
                if file_data.uncovered_classes:
                    report_lines.append("- Uncovered Classes:")
                    for cls in file_data.uncovered_classes[:5]:
                        report_lines.append(f"  - {cls}")
        
        # Test improvement suggestions
        report_lines.append("\n## Test Improvement Suggestions")
        
        # Group suggestions by priority
        high_priority = [s for s in self.suggestions if s.priority == 'high']
        medium_priority = [s for s in self.suggestions if s.priority == 'medium']
        
        if high_priority:
            report_lines.append("\n### High Priority")
            for suggestion in high_priority[:10]:
                report_lines.append(
                    f"- **{suggestion.file}**: {suggestion.description}"
                )
                if suggestion.example_test:
                    report_lines.extend([
                        "  Example test:",
                        "  ```python",
                        suggestion.example_test.strip(),
                        "  ```"
                    ])
        
        if medium_priority:
            report_lines.append("\n### Medium Priority")
            for suggestion in medium_priority[:10]:
                report_lines.append(
                    f"- {suggestion.file}: {suggestion.description}"
                )
        
        # Coverage trends (if historical data available)
        report_lines.extend([
            "\n## Recommendations",
            "1. Focus on testing error handling and edge cases",
            "2. Increase coverage for core modules (api_client, models, pipeline)",
            "3. Add integration tests for uncovered code paths",
            "4. Consider property-based testing for validation logic",
            f"5. Target: Achieve {max(80, overall_coverage + 10):.0f}% coverage"
        ])
        
        return '\n'.join(report_lines)
    
    def save_reports(self):
        """Save all coverage reports."""
        reports_dir = self.project_root / '.test-reports'
        reports_dir.mkdir(exist_ok=True)
        
        # Save detailed report
        report = self.generate_report()
        report_path = reports_dir / 'coverage_analysis.md'
        with open(report_path, 'w') as f:
            f.write(report)
        
        # Save suggestions as JSON
        suggestions_data = [
            {
                'file': s.file,
                'type': s.suggestion_type,
                'description': s.description,
                'priority': s.priority,
                'example': s.example_test
            }
            for s in self.suggestions
        ]
        
        suggestions_path = reports_dir / 'test_suggestions.json'
        with open(suggestions_path, 'w') as f:
            json.dump(suggestions_data, f, indent=2)
        
        print(f"\nReports saved:")
        print(f"- Coverage analysis: {report_path}")
        print(f"- Test suggestions: {suggestions_path}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze test coverage and suggest improvements'
    )
    parser.add_argument(
        '--source',
        default='src/python/flashcard_pipeline',
        help='Source directory to analyze'
    )
    
    args = parser.parse_args()
    
    analyzer = CoverageAnalyzer(source_dir=args.source)
    
    # Run coverage
    if not analyzer.run_coverage():
        return 1
    
    # Analyze results
    analyzer.analyze_coverage()
    analyzer.generate_suggestions()
    
    # Generate and save reports
    analyzer.save_reports()
    
    # Print summary
    total_coverage = sum(
        c.covered_lines for c in analyzer.coverage_data.values()
    )
    total_lines = sum(
        c.total_lines for c in analyzer.coverage_data.values()
    )
    
    if total_lines > 0:
        overall = (total_coverage / total_lines) * 100
        print(f"\nOverall Coverage: {overall:.1f}%")
        print(f"High Priority Suggestions: {len([s for s in analyzer.suggestions if s.priority == 'high'])}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())