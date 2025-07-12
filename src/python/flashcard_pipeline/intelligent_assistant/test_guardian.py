"""
Test Guardian Component

Ensures tests are created, maintained, and executed automatically.
"""

import re
import ast
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Set
from collections import defaultdict
from datetime import datetime
import importlib.util

logger = logging.getLogger(__name__)


class TestGuardian:
    """
    Automated test management and enforcement system.
    
    Features:
    - Automatic test file creation
    - Test execution monitoring
    - Coverage tracking
    - Test generation suggestions
    - Test failure handling
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.coverage_target = self.config.get("coverage_target", 80)
        
        # Test frameworks detection
        self.test_frameworks = {
            "python": ["pytest", "unittest", "nose"],
            "javascript": ["jest", "mocha", "jasmine"],
            "rust": ["cargo test"],
            "go": ["go test"]
        }
        
        # Test patterns
        self.test_patterns = {
            "test_prefix": ["test_", "test"],
            "test_suffix": ["_test", "Test", ".test", ".spec"],
            "test_dirs": ["tests", "test", "__tests__", "spec"]
        }
        
        # Test generation templates
        self.test_templates = self._load_test_templates()
        
        # Coverage data
        self.coverage_data = {}
        self.test_history = []
        
        # Detected framework for the project
        self.detected_framework = None
        
        logger.info("Test Guardian initialized")
    
    def initialize(self):
        """Initialize test guardian by detecting test framework."""
        self.detected_framework = self._detect_test_framework()
        logger.info(f"Detected test framework: {self.detected_framework}")
    
    def handle_test_files(self, task_result: Dict[str, Any]) -> Dict[str, Any]:
        """Main handler for test automation."""
        test_results = {
            "tests_created": [],
            "tests_updated": [],
            "tests_run": [],
            "coverage_report": {},
            "failures": [],
            "suggestions": []
        }
        
        modified_files = task_result.get("modified_files", [])
        new_files = task_result.get("new_files", [])
        
        all_files = modified_files + new_files
        
        for file_path in all_files:
            # Check if it's a test file
            if self.is_test_file(file_path):
                # Run the test immediately
                logger.info(f"Running test file: {file_path}")
                test_result = self.run_test_file(file_path)
                test_results["tests_run"].append(test_result)
                
                # Handle failures
                if not test_result["success"]:
                    test_results["failures"].append(test_result)
                    self._handle_test_failure(test_result)
            
            # Check if it's a source file needing tests
            elif self._needs_test_file(file_path):
                # Get or create test file
                test_file_path = self.get_test_file_path(file_path)
                
                if not Path(test_file_path).exists():
                    # Create new test file
                    logger.info(f"Creating test file for: {file_path}")
                    test_content = self.generate_test_file(file_path)
                    
                    # Create directory if needed
                    Path(test_file_path).parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(test_file_path, 'w', encoding='utf-8') as f:
                        f.write(test_content)
                    
                    test_results["tests_created"].append(test_file_path)
                    
                    # Run the new test
                    test_result = self.run_test_file(test_file_path)
                    test_results["tests_run"].append(test_result)
                else:
                    # Check if existing test needs update
                    if self._test_needs_update(file_path, test_file_path):
                        logger.info(f"Updating test file: {test_file_path}")
                        self._update_test_file(test_file_path, file_path)
                        test_results["tests_updated"].append(test_file_path)
                    
                    # Run the test
                    test_result = self.run_test_file(test_file_path)
                    test_results["tests_run"].append(test_result)
        
        # Calculate coverage if tests were run
        if test_results["tests_run"]:
            test_results["coverage_report"] = self.calculate_coverage()
            
            # Check coverage target
            total_coverage = test_results["coverage_report"].get("total_coverage", 0)
            if total_coverage < self.coverage_target:
                test_results["suggestions"].extend(
                    self._suggest_additional_tests(test_results["coverage_report"])
                )
        
        return test_results
    
    def is_test_file(self, file_path: str) -> bool:
        """Determine if a file is a test file."""
        path = Path(file_path)
        file_name = path.stem.lower()
        
        # Check directory
        for test_dir in self.test_patterns["test_dirs"]:
            if test_dir in path.parts:
                return True
        
        # Check prefix
        for prefix in self.test_patterns["test_prefix"]:
            if file_name.startswith(prefix):
                return True
        
        # Check suffix
        for suffix in self.test_patterns["test_suffix"]:
            if file_name.endswith(suffix.lower()):
                return True
        
        return False
    
    def get_test_file_path(self, source_file_path: str) -> str:
        """Get the corresponding test file path for a source file."""
        source_path = Path(source_file_path)
        
        # Determine test directory
        if "src" in source_path.parts:
            # Replace 'src' with 'tests'
            parts = list(source_path.parts)
            src_index = parts.index("src")
            parts[src_index] = "tests"
            test_dir = Path(*parts[:-1])
        else:
            # Default to tests directory
            test_dir = Path("tests") / source_path.parent
        
        # Generate test file name
        if source_path.stem.startswith("test_"):
            test_name = source_path.name
        else:
            test_name = f"test_{source_path.name}"
        
        return str(test_dir / test_name)
    
    def run_test_file(self, test_file_path: str) -> Dict[str, Any]:
        """Execute test file and capture results."""
        result = {
            "file": test_file_path,
            "success": False,
            "duration": 0,
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "failures": [],
            "output": "",
            "coverage": {}
        }
        
        if not Path(test_file_path).exists():
            result["output"] = f"Test file not found: {test_file_path}"
            return result
        
        language = self._detect_language(test_file_path)
        framework = self.detected_framework or self._detect_framework_for_file(test_file_path)
        
        # Build test command
        test_cmd = self._build_test_command(test_file_path, framework, language)
        
        if not test_cmd:
            result["output"] = f"No test framework detected for {test_file_path}"
            return result
        
        # Execute test
        start_time = datetime.now()
        
        try:
            logger.debug(f"Running command: {' '.join(test_cmd)}")
            process = subprocess.run(
                test_cmd,
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            result["duration"] = duration
            result["output"] = process.stdout + process.stderr
            result["success"] = process.returncode == 0
            
            # Parse test results
            parsed = self._parse_test_output(process.stdout, framework)
            result.update(parsed)
            
            # Store in history
            self.test_history.append({
                "timestamp": datetime.now().isoformat(),
                "file": test_file_path,
                "success": result["success"],
                "duration": duration,
                "tests_run": result["tests_run"],
                "tests_passed": result["tests_passed"]
            })
            
        except subprocess.TimeoutExpired:
            result["output"] = "Test execution timed out after 60 seconds"
        except Exception as e:
            result["output"] = f"Test execution failed: {str(e)}"
            logger.error(f"Failed to run test {test_file_path}: {e}")
        
        return result
    
    def generate_test_file(self, source_file_path: str) -> str:
        """Generate comprehensive test file for a source file."""
        language = self._detect_language(source_file_path)
        
        try:
            with open(source_file_path, 'r', encoding='utf-8') as f:
                source_content = f.read()
        except Exception as e:
            logger.error(f"Failed to read source file {source_file_path}: {e}")
            return self._get_basic_test_template(language)
        
        # Extract testable elements
        testable_elements = self._extract_testable_elements(source_content, language)
        
        # Get template
        template = self.test_templates.get(language, self.test_templates.get("default"))
        
        # Generate test cases
        test_cases = []
        
        for element in testable_elements:
            test_case = self._generate_test_case(element, language)
            test_cases.append(test_case)
        
        # Build imports
        imports = self._generate_test_imports(source_file_path, language)
        
        # Format test file
        test_content = template.format(
            source_file=source_file_path,
            imports=imports,
            test_cases="\n\n".join(test_cases),
            timestamp=datetime.now().isoformat()
        )
        
        return test_content
    
    def calculate_coverage(self) -> Dict[str, Any]:
        """Calculate test coverage for the project."""
        coverage_report = {
            "total_coverage": 0,
            "file_coverage": {},
            "uncovered_files": [],
            "summary": {
                "statements": 0,
                "covered": 0,
                "missing": 0
            }
        }
        
        # Try to run coverage tool
        coverage_cmd = None
        
        if self.detected_framework == "pytest":
            coverage_cmd = ["pytest", "--cov=.", "--cov-report=json", "--quiet"]
        elif self.detected_framework == "jest":
            coverage_cmd = ["jest", "--coverage", "--json"]
        
        if coverage_cmd:
            try:
                process = subprocess.run(
                    coverage_cmd,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if process.returncode == 0:
                    # Parse coverage data
                    coverage_data = self._parse_coverage_output(
                        process.stdout, 
                        self.detected_framework
                    )
                    coverage_report.update(coverage_data)
            except Exception as e:
                logger.error(f"Failed to calculate coverage: {e}")
        
        # Fallback: estimate coverage based on test existence
        if not coverage_report["file_coverage"]:
            coverage_report = self._estimate_coverage()
        
        self.coverage_data = coverage_report
        return coverage_report
    
    def get_status(self) -> Dict[str, Any]:
        """Get current test guardian status."""
        return {
            "framework": self.detected_framework,
            "coverage_target": self.coverage_target,
            "tests_run": len(self.test_history),
            "current_coverage": self.coverage_data.get("total_coverage", 0),
            "last_run": self.test_history[-1] if self.test_history else None
        }
    
    def shutdown(self):
        """Clean shutdown."""
        # Save test history
        self._save_test_history()
        logger.info("Test Guardian shutdown complete")
    
    # Helper methods
    
    def _load_test_templates(self) -> Dict[str, str]:
        """Load test file templates for different languages."""
        return {
            "python": '''"""
Test file for {source_file}
Generated by Test Guardian on {timestamp}
"""

import pytest
import unittest
from unittest.mock import Mock, patch

{imports}


class Test{class_name}(unittest.TestCase):
    """Test cases for {source_file}"""
    
    def setUp(self):
        """Set up test fixtures"""
        pass
    
    def tearDown(self):
        """Clean up after tests"""
        pass
    
{test_cases}


if __name__ == '__main__':
    unittest.main()
''',
            "javascript": '''/**
 * Test file for {source_file}
 * Generated by Test Guardian on {timestamp}
 */

{imports}

describe('{source_file}', () => {{
    beforeEach(() => {{
        // Setup
    }});
    
    afterEach(() => {{
        // Cleanup
    }});
    
{test_cases}
}});
''',
            "default": '''# Test file for {source_file}
# Generated by Test Guardian on {timestamp}

{imports}

{test_cases}
'''
        }
    
    def _detect_test_framework(self) -> Optional[str]:
        """Detect which test framework is used in the project."""
        # Check for configuration files
        framework_files = {
            "pytest": ["pytest.ini", "setup.cfg", "pyproject.toml"],
            "jest": ["jest.config.js", "jest.config.json", "package.json"],
            "mocha": [".mocharc.js", ".mocharc.json", "mocha.opts"],
            "cargo": ["Cargo.toml"]
        }
        
        for framework, files in framework_files.items():
            for file in files:
                if Path(file).exists():
                    # Additional check for package.json
                    if file == "package.json":
                        try:
                            with open(file, 'r') as f:
                                data = json.load(f)
                                if "jest" in data.get("devDependencies", {}):
                                    return "jest"
                                elif "mocha" in data.get("devDependencies", {}):
                                    return "mocha"
                        except:
                            pass
                    else:
                        return framework
        
        # Check for test files to infer framework
        test_files = list(Path(".").glob("**/test_*.py"))
        if test_files:
            return "pytest"  # Default for Python
        
        test_files = list(Path(".").glob("**/*.test.js"))
        if test_files:
            return "jest"  # Default for JavaScript
        
        return None
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.rs': 'rust',
            '.go': 'go',
            '.rb': 'ruby',
            '.java': 'java'
        }
        
        return extension_map.get(Path(file_path).suffix, 'unknown')
    
    def _needs_test_file(self, file_path: str) -> bool:
        """Determine if a source file needs a test file."""
        path = Path(file_path)
        
        # Skip test files
        if self.is_test_file(file_path):
            return False
        
        # Skip non-source files
        source_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.rs', '.go'}
        if path.suffix not in source_extensions:
            return False
        
        # Skip certain directories
        skip_dirs = {'__pycache__', 'node_modules', 'vendor', '.git', 'build', 'dist'}
        if any(skip_dir in path.parts for skip_dir in skip_dirs):
            return False
        
        # Skip certain files
        skip_patterns = ['__init__.py', 'setup.py', 'conf.py']
        if path.name in skip_patterns:
            return False
        
        return True
    
    def _test_needs_update(self, source_file: str, test_file: str) -> bool:
        """Check if test file needs updating based on source changes."""
        try:
            source_stat = Path(source_file).stat()
            test_stat = Path(test_file).stat()
            
            # Test is older than source
            if source_stat.st_mtime > test_stat.st_mtime:
                return True
            
            # Check if source has new functions/classes not in test
            with open(source_file, 'r', encoding='utf-8') as f:
                source_content = f.read()
            
            with open(test_file, 'r', encoding='utf-8') as f:
                test_content = f.read()
            
            language = self._detect_language(source_file)
            source_elements = self._extract_testable_elements(source_content, language)
            
            for element in source_elements:
                if element["name"] not in test_content:
                    return True
        
        except Exception as e:
            logger.error(f"Failed to check if test needs update: {e}")
        
        return False
    
    def _update_test_file(self, test_file_path: str, source_file_path: str):
        """Update existing test file with new test cases."""
        try:
            # Read current test file
            with open(test_file_path, 'r', encoding='utf-8') as f:
                test_content = f.read()
            
            # Read source file
            with open(source_file_path, 'r', encoding='utf-8') as f:
                source_content = f.read()
            
            language = self._detect_language(source_file_path)
            
            # Extract new elements to test
            source_elements = self._extract_testable_elements(source_content, language)
            new_test_cases = []
            
            for element in source_elements:
                # Check if test already exists
                test_name = f"test_{element['name']}"
                if test_name not in test_content:
                    test_case = self._generate_test_case(element, language)
                    new_test_cases.append(test_case)
            
            if new_test_cases:
                # Append new test cases
                if language == "python":
                    # Find the last test method
                    insertion_point = test_content.rfind("\n\n    def test_")
                    if insertion_point > 0:
                        before = test_content[:insertion_point]
                        after = test_content[insertion_point:]
                        test_content = before + "\n\n" + "\n\n".join(new_test_cases) + after
                    else:
                        # Append to end of class
                        test_content += "\n\n" + "\n\n".join(new_test_cases)
                
                # Write updated content
                with open(test_file_path, 'w', encoding='utf-8') as f:
                    f.write(test_content)
                
                logger.info(f"Updated test file with {len(new_test_cases)} new test cases")
        
        except Exception as e:
            logger.error(f"Failed to update test file: {e}")
    
    def _extract_testable_elements(self, content: str, language: str) -> List[Dict[str, Any]]:
        """Extract functions, classes, and methods that need testing."""
        elements = []
        
        if language == "python":
            try:
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        elements.append({
                            "type": "function",
                            "name": node.name,
                            "args": [arg.arg for arg in node.args.args],
                            "lineno": node.lineno,
                            "docstring": ast.get_docstring(node)
                        })
                    elif isinstance(node, ast.ClassDef):
                        elements.append({
                            "type": "class",
                            "name": node.name,
                            "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                            "lineno": node.lineno,
                            "docstring": ast.get_docstring(node)
                        })
            except Exception as e:
                logger.error(f"Failed to parse Python content: {e}")
        
        elif language in ["javascript", "typescript"]:
            # Simplified regex-based extraction for JS/TS
            # Function declarations
            func_pattern = r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\("
            for match in re.finditer(func_pattern, content):
                elements.append({
                    "type": "function",
                    "name": match.group(1),
                    "args": []  # Would need proper parsing
                })
            
            # Class declarations
            class_pattern = r"(?:export\s+)?class\s+(\w+)"
            for match in re.finditer(class_pattern, content):
                elements.append({
                    "type": "class",
                    "name": match.group(1),
                    "methods": []  # Would need proper parsing
                })
        
        return elements
    
    def _generate_test_case(self, element: Dict[str, Any], language: str) -> str:
        """Generate a test case for a testable element."""
        if language == "python":
            if element["type"] == "function":
                return f'''    def test_{element["name"]}(self):
        """Test {element["name"]} function"""
        # TODO: Implement test for {element["name"]}
        # Args: {", ".join(element.get("args", []))}
        result = {element["name"]}()  # Add appropriate arguments
        self.assertIsNotNone(result)
        # Add more specific assertions'''
            
            elif element["type"] == "class":
                return f'''    def test_{element["name"]}_creation(self):
        """Test {element["name"]} class instantiation"""
        instance = {element["name"]}()
        self.assertIsNotNone(instance)
        
    def test_{element["name"]}_methods(self):
        """Test {element["name"]} class methods"""
        instance = {element["name"]}()
        # Test methods: {", ".join(element.get("methods", []))}
        # TODO: Add method tests'''
        
        elif language in ["javascript", "typescript"]:
            if element["type"] == "function":
                return f'''    it('should test {element["name"]} function', () => {{
        // TODO: Implement test for {element["name"]}
        const result = {element["name"]}(); // Add appropriate arguments
        expect(result).toBeDefined();
        // Add more specific assertions
    }});'''
            
            elif element["type"] == "class":
                return f'''    describe('{element["name"]}', () => {{
        it('should create instance', () => {{
            const instance = new {element["name"]}();
            expect(instance).toBeDefined();
        }});
        
        // TODO: Add method tests
    }});'''
        
        return f"# TODO: Generate test for {element['name']}"
    
    def _generate_test_imports(self, source_file_path: str, language: str) -> str:
        """Generate import statements for test file."""
        source_path = Path(source_file_path)
        
        if language == "python":
            # Calculate relative import path
            module_path = source_path.stem
            if source_path.parent != Path("."):
                module_parts = list(source_path.parent.parts)
                if "src" in module_parts:
                    module_parts[module_parts.index("src")] = ""
                module_path = ".".join(filter(None, module_parts)) + "." + module_path
            
            return f"from {module_path} import *  # Import all for testing"
        
        elif language in ["javascript", "typescript"]:
            # Calculate relative import path
            test_file_dir = Path("tests") / source_path.parent
            relative_path = Path("..") / source_path
            
            return f"import {{ * }} from '{relative_path.with_suffix('')}';"
        
        return ""
    
    def _build_test_command(self, test_file: str, framework: str, language: str) -> List[str]:
        """Build command to run tests."""
        commands = {
            "pytest": ["pytest", "-v", test_file],
            "unittest": ["python", "-m", "unittest", test_file],
            "jest": ["jest", test_file],
            "mocha": ["mocha", test_file],
            "cargo": ["cargo", "test", "--", test_file],
            "go": ["go", "test", test_file]
        }
        
        return commands.get(framework, [])
    
    def _parse_test_output(self, output: str, framework: str) -> Dict[str, Any]:
        """Parse test output to extract results."""
        parsed = {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "failures": []
        }
        
        if framework == "pytest":
            # Parse pytest output
            # Example: "5 passed, 2 failed in 1.23s"
            match = re.search(r"(\d+) passed", output)
            if match:
                parsed["tests_passed"] = int(match.group(1))
            
            match = re.search(r"(\d+) failed", output)
            if match:
                parsed["tests_failed"] = int(match.group(1))
            
            parsed["tests_run"] = parsed["tests_passed"] + parsed["tests_failed"]
            
            # Extract failure details
            failure_pattern = r"FAILED (.*?) - (.*)"
            for match in re.finditer(failure_pattern, output):
                parsed["failures"].append({
                    "test": match.group(1),
                    "error": match.group(2)
                })
        
        elif framework == "jest":
            # Parse jest output
            # Example: "Tests: 2 failed, 5 passed, 7 total"
            match = re.search(r"Tests:.*?(\d+) passed", output)
            if match:
                parsed["tests_passed"] = int(match.group(1))
            
            match = re.search(r"Tests:.*?(\d+) failed", output)
            if match:
                parsed["tests_failed"] = int(match.group(1))
            
            match = re.search(r"Tests:.*?(\d+) total", output)
            if match:
                parsed["tests_run"] = int(match.group(1))
        
        return parsed
    
    def _parse_coverage_output(self, output: str, framework: str) -> Dict[str, Any]:
        """Parse coverage output."""
        coverage_data = {
            "file_coverage": {},
            "total_coverage": 0
        }
        
        try:
            if framework == "pytest":
                # Try to find coverage summary
                match = re.search(r"TOTAL.*?(\d+)%", output)
                if match:
                    coverage_data["total_coverage"] = int(match.group(1))
            
            elif framework == "jest":
                # Parse jest coverage output
                match = re.search(r"All files.*?(\d+\.?\d*)", output)
                if match:
                    coverage_data["total_coverage"] = float(match.group(1))
        
        except Exception as e:
            logger.error(f"Failed to parse coverage output: {e}")
        
        return coverage_data
    
    def _estimate_coverage(self) -> Dict[str, Any]:
        """Estimate coverage based on test file existence."""
        source_files = []
        test_files = []
        
        # Find all source files
        for ext in ['.py', '.js', '.ts']:
            source_files.extend(Path(".").glob(f"**/*{ext}"))
        
        # Filter out test files
        source_files = [f for f in source_files if not self.is_test_file(str(f))]
        
        # Find corresponding test files
        files_with_tests = 0
        for source_file in source_files:
            test_file = self.get_test_file_path(str(source_file))
            if Path(test_file).exists():
                files_with_tests += 1
        
        # Estimate coverage
        if source_files:
            estimated_coverage = (files_with_tests / len(source_files)) * 100
        else:
            estimated_coverage = 0
        
        return {
            "total_coverage": estimated_coverage,
            "file_coverage": {},
            "summary": {
                "total_files": len(source_files),
                "files_with_tests": files_with_tests,
                "files_without_tests": len(source_files) - files_with_tests
            }
        }
    
    def _suggest_additional_tests(self, coverage_report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest additional tests to improve coverage."""
        suggestions = []
        
        # Find files with low coverage
        for file_path, coverage in coverage_report.get("file_coverage", {}).items():
            if coverage < self.coverage_target:
                suggestions.append({
                    "type": "low_coverage",
                    "file": file_path,
                    "current_coverage": coverage,
                    "target_coverage": self.coverage_target,
                    "message": f"Increase test coverage for {file_path}"
                })
        
        # Find files without tests
        if "summary" in coverage_report:
            if coverage_report["summary"].get("files_without_tests", 0) > 0:
                suggestions.append({
                    "type": "missing_tests",
                    "count": coverage_report["summary"]["files_without_tests"],
                    "message": "Create tests for files without any test coverage"
                })
        
        return suggestions
    
    def _handle_test_failure(self, test_result: Dict[str, Any]):
        """Handle test failure by creating issue or notification."""
        failure_info = {
            "timestamp": datetime.now().isoformat(),
            "test_file": test_result["file"],
            "failures": test_result["failures"],
            "output": test_result["output"]
        }
        
        # Log failure
        logger.error(f"Test failed: {test_result['file']}")
        
        # Could create GitHub issue, send notification, etc.
        # For now, just log
        logger.info(f"Test failure recorded: {len(test_result['failures'])} tests failed")
    
    def _detect_framework_for_file(self, file_path: str) -> Optional[str]:
        """Detect test framework for a specific file."""
        language = self._detect_language(file_path)
        
        # Check file content for framework imports
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if language == "python":
                if "import pytest" in content or "from pytest" in content:
                    return "pytest"
                elif "import unittest" in content:
                    return "unittest"
            
            elif language in ["javascript", "typescript"]:
                if "describe(" in content and "it(" in content:
                    if "expect(" in content and "toBe" in content:
                        return "jest"
                    else:
                        return "mocha"
        
        except Exception as e:
            logger.error(f"Failed to detect framework for {file_path}: {e}")
        
        return None
    
    def _get_basic_test_template(self, language: str) -> str:
        """Get a basic test template when source reading fails."""
        if language == "python":
            return '''"""Basic test file"""

import unittest


class TestBasic(unittest.TestCase):
    def test_placeholder(self):
        """Placeholder test"""
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
'''
        else:
            return '''// Basic test file

describe('Basic', () => {
    it('should pass', () => {
        expect(true).toBe(true);
    });
});
'''
    
    def _save_test_history(self):
        """Save test execution history."""
        history_path = Path(".test_guardian") / "history.json"
        history_path.parent.mkdir(exist_ok=True)
        
        try:
            with open(history_path, 'w') as f:
                json.dump({
                    "history": self.test_history[-1000:],  # Keep last 1000 runs
                    "last_updated": datetime.now().isoformat()
                }, f, indent=2)
            
            logger.debug("Saved test history")
        except Exception as e:
            logger.error(f"Failed to save test history: {e}")