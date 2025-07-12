"""
Smart Linter Component

Intelligent code quality enforcement beyond standard linting.
"""

import re
import ast
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Set
from collections import defaultdict
from dataclasses import dataclass
import importlib.util

logger = logging.getLogger(__name__)


@dataclass
class LintIssue:
    """Represents a linting issue."""
    file: str
    line: int
    column: int
    rule: str
    message: str
    severity: str  # error, warning, info
    fixable: bool = False
    fix_suggestion: Optional[str] = None


class SmartLinter:
    """
    Advanced code quality analysis and enforcement.
    
    Features:
    - Custom project rules
    - Code complexity analysis
    - Pattern detection
    - Auto-fixing capabilities
    - Multi-language support
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.auto_fix_enabled = self.config.get("auto_fix", False)
        
        # Project rules
        self.project_rules = {}
        self.custom_patterns = {}
        
        # Metrics thresholds
        self.metrics_thresholds = {
            "complexity": self.config.get("max_complexity", 10),
            "function_length": self.config.get("max_function_length", 50),
            "file_length": self.config.get("max_file_length", 500),
            "line_length": self.config.get("max_line_length", 120),
            "duplicate_threshold": self.config.get("duplicate_threshold", 0.15),
            "nesting_depth": self.config.get("max_nesting_depth", 4)
        }
        
        # Language-specific configurations
        self.language_configs = {
            "python": {
                "linter": "pylint",
                "formatter": "black",
                "type_checker": "mypy"
            },
            "javascript": {
                "linter": "eslint",
                "formatter": "prettier"
            },
            "rust": {
                "linter": "clippy",
                "formatter": "rustfmt"
            }
        }
        
        # Auto-fixable issues
        self.auto_fixable_rules = {
            "trailing_whitespace",
            "missing_final_newline",
            "mixed_indentation",
            "unused_imports",
            "import_order",
            "quote_consistency",
            "semicolon_consistency"
        }
        
        # Code patterns to detect
        self.code_patterns = self._initialize_code_patterns()
        
        logger.info("Smart Linter initialized")
    
    def initialize(self):
        """Initialize linter by loading project configuration."""
        self.load_project_rules()
        logger.info("Smart Linter ready")
    
    def load_project_rules(self):
        """Load project-specific linting rules."""
        # Check for project lint config files
        config_files = [
            ".pylintrc",
            ".eslintrc.json",
            "pyproject.toml",
            ".flake8",
            "setup.cfg"
        ]
        
        for config_file in config_files:
            config_path = Path(config_file)
            if config_path.exists():
                self._load_config_file(config_path)
        
        # Load custom rules from project
        custom_rules_path = Path(".lint") / "custom_rules.json"
        if custom_rules_path.exists():
            try:
                with open(custom_rules_path, 'r') as f:
                    self.project_rules = json.load(f)
                logger.info(f"Loaded {len(self.project_rules)} custom lint rules")
            except Exception as e:
                logger.warning(f"Failed to load custom rules: {e}")
    
    def check_modified_files(self, task_result: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive linting of modified files."""
        lint_results = {
            "errors": [],
            "warnings": [],
            "info": [],
            "suggestions": [],
            "metrics": {},
            "summary": {
                "total_issues": 0,
                "fixable_issues": 0,
                "files_checked": 0
            }
        }
        
        modified_files = task_result.get("modified_files", [])
        
        for file_path in modified_files:
            if self._should_lint_file(file_path):
                logger.debug(f"Linting {file_path}")
                
                # Standard linting
                standard_results = self._run_standard_linter(file_path)
                
                # Custom project rules
                custom_results = self._check_custom_rules(file_path)
                
                # Code quality metrics
                metrics = self._calculate_code_metrics(file_path)
                
                # Pattern detection
                pattern_issues = self._check_code_patterns(file_path)
                
                # Security checks
                security_issues = self._check_security_patterns(file_path)
                
                # Aggregate results
                all_issues = (
                    standard_results + 
                    custom_results + 
                    pattern_issues + 
                    security_issues
                )
                
                # Categorize by severity
                for issue in all_issues:
                    if issue.severity == "error":
                        lint_results["errors"].append(issue.__dict__)
                    elif issue.severity == "warning":
                        lint_results["warnings"].append(issue.__dict__)
                    else:
                        lint_results["info"].append(issue.__dict__)
                    
                    if issue.fixable:
                        lint_results["summary"]["fixable_issues"] += 1
                
                # Store metrics
                lint_results["metrics"][file_path] = metrics
                lint_results["summary"]["files_checked"] += 1
        
        lint_results["summary"]["total_issues"] = (
            len(lint_results["errors"]) + 
            len(lint_results["warnings"]) + 
            len(lint_results["info"])
        )
        
        # Generate suggestions based on results
        lint_results["suggestions"] = self._generate_suggestions(lint_results)
        
        return lint_results
    
    def quick_syntax_check(self, file_path: str) -> Dict[str, Any]:
        """Quick syntax check for a file."""
        result = {
            "valid": True,
            "errors": [],
            "suggestions": []
        }
        
        if not file_path or not Path(file_path).exists():
            return result
        
        language = self._detect_language(file_path)
        
        try:
            if language == "python":
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    result["valid"] = False
                    result["errors"].append({
                        "line": e.lineno,
                        "column": e.offset,
                        "message": str(e)
                    })
                    result["suggestions"].append(f"Check line {e.lineno}, column {e.offset}")
            
            elif language in ["javascript", "typescript"]:
                # Use external tool for JS/TS
                cmd = ["node", "--check", file_path]
                process = subprocess.run(cmd, capture_output=True, text=True)
                
                if process.returncode != 0:
                    result["valid"] = False
                    result["errors"].append({
                        "message": process.stderr
                    })
        
        except Exception as e:
            logger.error(f"Syntax check failed for {file_path}: {e}")
        
        return result
    
    def auto_fix_issues(self, lint_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Automatically fix certain linting issues."""
        fixes_applied = []
        
        if not self.auto_fix_enabled:
            logger.info("Auto-fix is disabled")
            return fixes_applied
        
        # Group issues by file
        issues_by_file = defaultdict(list)
        for issue_dict in lint_results.get("errors", []) + lint_results.get("warnings", []):
            if issue_dict.get("fixable"):
                issues_by_file[issue_dict["file"]].append(issue_dict)
        
        for file_path, issues in issues_by_file.items():
            # Sort issues by line number (reverse order to avoid offset issues)
            issues.sort(key=lambda x: x.get("line", 0), reverse=True)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                original_content = ''.join(lines)
                modified = False
                
                for issue in issues:
                    if issue["rule"] in self.auto_fixable_rules:
                        fix_result = self._apply_fix(lines, issue)
                        if fix_result["success"]:
                            modified = True
                            fixes_applied.append({
                                "file": file_path,
                                "rule": issue["rule"],
                                "line": issue.get("line"),
                                "fix": fix_result["description"]
                            })
                
                if modified:
                    new_content = ''.join(lines)
                    if new_content != original_content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        
                        logger.info(f"Applied {len(fixes_applied)} fixes to {file_path}")
            
            except Exception as e:
                logger.error(f"Failed to auto-fix {file_path}: {e}")
        
        return fixes_applied
    
    def get_status(self) -> Dict[str, Any]:
        """Get current linter status."""
        return {
            "rules_loaded": len(self.project_rules),
            "custom_patterns": len(self.custom_patterns),
            "auto_fix_enabled": self.auto_fix_enabled,
            "thresholds": self.metrics_thresholds
        }
    
    def shutdown(self):
        """Clean shutdown."""
        logger.info("Smart Linter shutdown complete")
    
    # Helper methods
    
    def _initialize_code_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize code patterns to detect."""
        return {
            "no_console_log": {
                "pattern": r"console\.(log|debug|info)",
                "message": "Remove console statements before production",
                "severity": "warning",
                "languages": ["javascript", "typescript"]
            },
            "no_print_statements": {
                "pattern": r"^\s*print\s*\(",
                "message": "Use logging instead of print statements",
                "severity": "warning",
                "languages": ["python"]
            },
            "no_hardcoded_credentials": {
                "pattern": r"(password|api_key|secret)\s*=\s*['\"][^'\"]+['\"]",
                "message": "Never hardcode credentials",
                "severity": "error",
                "languages": ["all"]
            },
            "no_todo_comments": {
                "pattern": r"#\s*(TODO|FIXME|HACK)",
                "message": "Address TODO comments",
                "severity": "info",
                "languages": ["all"]
            },
            "proper_error_handling": {
                "pattern": r"except\s*:",
                "message": "Avoid bare except clauses",
                "severity": "warning",
                "languages": ["python"]
            }
        }
    
    def _should_lint_file(self, file_path: str) -> bool:
        """Determine if file should be linted."""
        path = Path(file_path)
        
        # Skip non-existent files
        if not path.exists():
            return False
        
        # Skip binary files
        binary_extensions = {'.pyc', '.pyo', '.so', '.dll', '.exe', '.bin'}
        if path.suffix in binary_extensions:
            return False
        
        # Skip vendor/third-party code
        skip_dirs = {'node_modules', 'vendor', 'venv', '__pycache__', '.git'}
        if any(skip_dir in path.parts for skip_dir in skip_dirs):
            return False
        
        # Check supported file types
        supported_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.rs', '.go'}
        return path.suffix in supported_extensions
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.rs': 'rust',
            '.go': 'go',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.cs': 'csharp'
        }
        
        return extension_map.get(Path(file_path).suffix, 'unknown')
    
    def _run_standard_linter(self, file_path: str) -> List[LintIssue]:
        """Run standard linter for the file."""
        issues = []
        language = self._detect_language(file_path)
        
        if language == "python":
            issues.extend(self._run_python_linter(file_path))
        elif language in ["javascript", "typescript"]:
            issues.extend(self._run_javascript_linter(file_path))
        elif language == "rust":
            issues.extend(self._run_rust_linter(file_path))
        
        return issues
    
    def _run_python_linter(self, file_path: str) -> List[LintIssue]:
        """Run Python linter (pylint/flake8)."""
        issues = []
        
        try:
            # Try pylint first
            cmd = ["pylint", "--output-format=json", file_path]
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.stdout:
                lint_data = json.loads(process.stdout)
                for item in lint_data:
                    issues.append(LintIssue(
                        file=file_path,
                        line=item.get("line", 0),
                        column=item.get("column", 0),
                        rule=item.get("symbol", "unknown"),
                        message=item.get("message", ""),
                        severity="error" if item.get("type") == "error" else "warning",
                        fixable=self._is_fixable(item.get("symbol"))
                    ))
        except Exception as e:
            logger.debug(f"Pylint not available: {e}")
            
            # Fallback to basic AST checking
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                # Basic checks using AST
                for node in ast.walk(tree):
                    # Check function length
                    if isinstance(node, ast.FunctionDef):
                        func_lines = node.end_lineno - node.lineno
                        if func_lines > self.metrics_thresholds["function_length"]:
                            issues.append(LintIssue(
                                file=file_path,
                                line=node.lineno,
                                column=0,
                                rule="function_too_long",
                                message=f"Function '{node.name}' is {func_lines} lines (max: {self.metrics_thresholds['function_length']})",
                                severity="warning",
                                fixable=False
                            ))
            except Exception as e:
                logger.error(f"Failed to parse Python file {file_path}: {e}")
        
        return issues
    
    def _run_javascript_linter(self, file_path: str) -> List[LintIssue]:
        """Run JavaScript/TypeScript linter."""
        issues = []
        
        # Simplified - would use ESLint in practice
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            # Basic pattern checks
            for i, line in enumerate(lines, 1):
                # Check line length
                if len(line) > self.metrics_thresholds["line_length"]:
                    issues.append(LintIssue(
                        file=file_path,
                        line=i,
                        column=self.metrics_thresholds["line_length"],
                        rule="line_too_long",
                        message=f"Line exceeds {self.metrics_thresholds['line_length']} characters",
                        severity="warning",
                        fixable=False
                    ))
        except Exception as e:
            logger.error(f"Failed to lint JavaScript file {file_path}: {e}")
        
        return issues
    
    def _run_rust_linter(self, file_path: str) -> List[LintIssue]:
        """Run Rust linter (clippy)."""
        issues = []
        
        try:
            cmd = ["cargo", "clippy", "--message-format=json", "--", file_path]
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            for line in process.stdout.splitlines():
                try:
                    msg = json.loads(line)
                    if msg.get("reason") == "compiler-message":
                        message = msg.get("message", {})
                        if message.get("level") in ["warning", "error"]:
                            spans = message.get("spans", [])
                            if spans:
                                span = spans[0]
                                issues.append(LintIssue(
                                    file=file_path,
                                    line=span.get("line_start", 0),
                                    column=span.get("column_start", 0),
                                    rule=message.get("code", {}).get("code", "clippy"),
                                    message=message.get("message", ""),
                                    severity=message.get("level", "warning"),
                                    fixable=False
                                ))
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.debug(f"Clippy not available: {e}")
        
        return issues
    
    def _check_custom_rules(self, file_path: str) -> List[LintIssue]:
        """Check project-specific custom rules."""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            language = self._detect_language(file_path)
            
            # Apply custom patterns
            for rule_name, rule_config in self.project_rules.get(language, {}).items():
                pattern = rule_config.get("pattern")
                if pattern:
                    for i, line in enumerate(lines, 1):
                        if re.search(pattern, line):
                            issues.append(LintIssue(
                                file=file_path,
                                line=i,
                                column=0,
                                rule=rule_name,
                                message=rule_config.get("message", "Custom rule violation"),
                                severity=rule_config.get("severity", "warning"),
                                fixable=rule_config.get("fixable", False)
                            ))
        
        except Exception as e:
            logger.error(f"Failed to check custom rules for {file_path}: {e}")
        
        return issues
    
    def _check_code_patterns(self, file_path: str) -> List[LintIssue]:
        """Check for code patterns and anti-patterns."""
        issues = []
        language = self._detect_language(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            for pattern_name, pattern_config in self.code_patterns.items():
                # Check if pattern applies to this language
                pattern_languages = pattern_config.get("languages", ["all"])
                if "all" not in pattern_languages and language not in pattern_languages:
                    continue
                
                pattern = pattern_config.get("pattern")
                if pattern:
                    for i, line in enumerate(lines, 1):
                        if re.search(pattern, line):
                            issues.append(LintIssue(
                                file=file_path,
                                line=i,
                                column=0,
                                rule=pattern_name,
                                message=pattern_config.get("message", "Pattern detected"),
                                severity=pattern_config.get("severity", "warning"),
                                fixable=False
                            ))
        
        except Exception as e:
            logger.error(f"Failed to check patterns for {file_path}: {e}")
        
        return issues
    
    def _check_security_patterns(self, file_path: str) -> List[LintIssue]:
        """Check for security vulnerabilities."""
        issues = []
        
        security_patterns = {
            "sql_injection": {
                "pattern": r"(query|execute)\s*\(\s*['\"].*%s.*['\"].*%",
                "message": "Potential SQL injection vulnerability",
                "severity": "error"
            },
            "command_injection": {
                "pattern": r"(os\.system|subprocess\.call)\s*\([^)]*\+",
                "message": "Potential command injection vulnerability",
                "severity": "error"
            },
            "path_traversal": {
                "pattern": r"\.\.\/",
                "message": "Potential path traversal vulnerability",
                "severity": "error"
            }
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            for vuln_name, vuln_config in security_patterns.items():
                pattern = vuln_config.get("pattern")
                if pattern:
                    for i, line in enumerate(lines, 1):
                        if re.search(pattern, line):
                            issues.append(LintIssue(
                                file=file_path,
                                line=i,
                                column=0,
                                rule=f"security_{vuln_name}",
                                message=vuln_config.get("message"),
                                severity=vuln_config.get("severity", "error"),
                                fixable=False
                            ))
        
        except Exception as e:
            logger.error(f"Failed to check security patterns for {file_path}: {e}")
        
        return issues
    
    def _calculate_code_metrics(self, file_path: str) -> Dict[str, Any]:
        """Calculate comprehensive code quality metrics."""
        metrics = {
            "lines_of_code": 0,
            "cyclomatic_complexity": 0,
            "function_count": 0,
            "class_count": 0,
            "average_function_length": 0,
            "max_function_length": 0,
            "comment_ratio": 0,
            "import_count": 0,
            "max_nesting_depth": 0
        }
        
        language = self._detect_language(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            # Basic metrics
            metrics["lines_of_code"] = len([l for l in lines if l.strip() and not l.strip().startswith('#')])
            
            if language == "python":
                metrics.update(self._calculate_python_metrics(content))
            
            # Comment ratio
            comment_lines = len([l for l in lines if l.strip().startswith('#') or l.strip().startswith('//')])
            if lines:
                metrics["comment_ratio"] = comment_lines / len(lines)
        
        except Exception as e:
            logger.error(f"Failed to calculate metrics for {file_path}: {e}")
        
        return metrics
    
    def _calculate_python_metrics(self, content: str) -> Dict[str, Any]:
        """Calculate Python-specific metrics."""
        metrics = {}
        
        try:
            tree = ast.parse(content)
            
            functions = []
            classes = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(node)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    metrics["import_count"] = metrics.get("import_count", 0) + 1
            
            metrics["function_count"] = len(functions)
            metrics["class_count"] = len(classes)
            
            # Function lengths
            if functions:
                func_lengths = []
                for func in functions:
                    if hasattr(func, 'end_lineno'):
                        length = func.end_lineno - func.lineno
                        func_lengths.append(length)
                
                if func_lengths:
                    metrics["average_function_length"] = sum(func_lengths) / len(func_lengths)
                    metrics["max_function_length"] = max(func_lengths)
            
            # Cyclomatic complexity (simplified)
            complexity = 1  # Base complexity
            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.While, ast.For)):
                    complexity += 1
                elif isinstance(node, ast.BoolOp):
                    complexity += len(node.values) - 1
            
            metrics["cyclomatic_complexity"] = complexity
        
        except Exception as e:
            logger.error(f"Failed to calculate Python metrics: {e}")
        
        return metrics
    
    def _is_fixable(self, rule: str) -> bool:
        """Determine if a rule violation is auto-fixable."""
        return rule in self.auto_fixable_rules
    
    def _apply_fix(self, lines: List[str], issue: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a fix for an issue."""
        result = {"success": False, "description": ""}
        
        try:
            rule = issue["rule"]
            line_num = issue.get("line", 0) - 1  # Convert to 0-based index
            
            if line_num < 0 or line_num >= len(lines):
                return result
            
            if rule == "trailing_whitespace":
                lines[line_num] = lines[line_num].rstrip() + '\n'
                result["success"] = True
                result["description"] = "Removed trailing whitespace"
            
            elif rule == "missing_final_newline":
                if lines and not lines[-1].endswith('\n'):
                    lines[-1] += '\n'
                result["success"] = True
                result["description"] = "Added final newline"
            
            elif rule == "mixed_indentation":
                # Convert tabs to spaces (assuming 4 spaces per tab)
                lines[line_num] = lines[line_num].replace('\t', '    ')
                result["success"] = True
                result["description"] = "Converted tabs to spaces"
        
        except Exception as e:
            logger.error(f"Failed to apply fix for {rule}: {e}")
        
        return result
    
    def _generate_suggestions(self, lint_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate actionable suggestions based on lint results."""
        suggestions = []
        
        # High error count
        if len(lint_results["errors"]) > 10:
            suggestions.append({
                "type": "high_error_count",
                "message": "Consider addressing critical errors first",
                "priority": "high"
            })
        
        # Many fixable issues
        if lint_results["summary"]["fixable_issues"] > 5:
            suggestions.append({
                "type": "auto_fix_available",
                "message": f"{lint_results['summary']['fixable_issues']} issues can be auto-fixed",
                "action": "Run auto-fix to clean up code",
                "priority": "medium"
            })
        
        # Code complexity
        for file_path, metrics in lint_results["metrics"].items():
            if metrics.get("cyclomatic_complexity", 0) > 15:
                suggestions.append({
                    "type": "high_complexity",
                    "file": file_path,
                    "message": "Consider refactoring to reduce complexity",
                    "priority": "medium"
                })
        
        return suggestions
    
    def _load_config_file(self, config_path: Path):
        """Load configuration from a lint config file."""
        try:
            if config_path.suffix == ".json":
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    # Process config based on type
                    logger.info(f"Loaded config from {config_path}")
            
            elif config_path.name == "pyproject.toml":
                # Would use toml library in practice
                logger.info("Would load pyproject.toml config")
        
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")