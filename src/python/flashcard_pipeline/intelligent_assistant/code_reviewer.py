#!/usr/bin/env python3
"""
Smart Code Review System
AI-powered code review that understands business logic and suggests improvements
"""
import ast
import re
import json
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import difflib
from datetime import datetime
from collections import defaultdict

class ReviewCategory(Enum):
    """Categories of code review issues"""
    ARCHITECTURE = "architecture"
    PERFORMANCE = "performance"
    SECURITY = "security"
    MAINTAINABILITY = "maintainability"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    BUSINESS_LOGIC = "business_logic"
    BEST_PRACTICES = "best_practices"

class Severity(Enum):
    """Severity levels for review findings"""
    INFO = "info"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"

@dataclass
class ReviewFinding:
    """A single finding from code review"""
    file_path: str
    line_number: int
    category: ReviewCategory
    severity: Severity
    title: str
    description: str
    suggestion: str
    code_snippet: str
    confidence: float = 0.8
    examples: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)

@dataclass
class CodeMetrics:
    """Metrics for code quality assessment"""
    complexity: int
    maintainability_index: float
    lines_of_code: int
    comment_ratio: float
    test_coverage: float
    duplication_ratio: float
    coupling: int
    cohesion: float

class SmartCodeReviewer:
    """AI-powered code review system"""
    
    def __init__(self):
        # Design patterns to recognize
        self.design_patterns = {
            'singleton': r'class\s+\w+.*:\s*\n\s*_instance\s*=\s*None',
            'factory': r'def\s+create_\w+|class\s+\w*Factory',
            'observer': r'def\s+(?:attach|detach|notify|update)\s*\(',
            'strategy': r'class\s+\w*Strategy.*:\s*\n\s*def\s+execute',
            'decorator': r'def\s+\w+\(.*\):\s*\n\s*def\s+wrapper',
        }
        
        # Anti-patterns to detect
        self.anti_patterns = {
            'god_class': {'max_methods': 20, 'max_lines': 500},
            'long_method': {'max_lines': 50},
            'feature_envy': {'max_external_calls': 5},
            'data_clumps': {'min_param_group': 3},
            'primitive_obsession': {'max_primitives': 7},
        }
        
        # Business logic patterns
        self.business_patterns = {
            'validation': r'def\s+validate_|if\s+not\s+.*:\s*raise',
            'calculation': r'def\s+calculate_|return\s+.*[\+\-\*/]',
            'transformation': r'def\s+transform_|\.map\(|\.filter\(',
            'persistence': r'\.save\(|\.create\(|\.update\(|\.delete\(',
        }
        
        # Security patterns
        self.security_patterns = {
            'sql_injection': r'\.execute\([^,]*%|\.format\(.*\).*(?:SELECT|INSERT|UPDATE|DELETE)',
            'command_injection': r'os\.system\(|subprocess\..*\(.*\+|eval\(',
            'path_traversal': r'\.\.\/|\.join\([^)]*user_input',
            'hardcoded_secrets': r'(?:password|api_key|secret|token)\s*=\s*["\'][^"\']+["\']',
            'weak_crypto': r'md5|sha1|DES|ECB',
        }
        
        # Performance patterns
        self.performance_patterns = {
            'n_plus_one': r'for.*:\s*\n.*\.(get|filter|select)\(',
            'inefficient_loop': r'for.*:\s*\n\s*.*\.append\(|in\s+.*\s+for\s+.*\s+in',
            'repeated_computation': r'for.*:\s*\n.*len\(|\.count\(',
            'unnecessary_list': r'list\(.*\).*\[0\]|list\(.*\)\[.*\]',
        }
        
        # Cache for learned patterns
        self.learned_patterns = {}
        
    def review_code(self, file_path: str, previous_version: Optional[str] = None) -> List[ReviewFinding]:
        """Perform comprehensive code review"""
        findings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            return findings
        
        # Analyze different aspects
        findings.extend(self._analyze_architecture(file_path, content, lines))
        findings.extend(self._analyze_security(file_path, content, lines))
        findings.extend(self._analyze_performance(file_path, content, lines))
        findings.extend(self._analyze_maintainability(file_path, content, lines))
        findings.extend(self._analyze_business_logic(file_path, content, lines))
        
        # Python-specific analysis
        if file_path.endswith('.py'):
            findings.extend(self._analyze_python_specific(file_path, content))
        
        # Diff analysis if previous version provided
        if previous_version:
            findings.extend(self._analyze_changes(file_path, content, previous_version))
        
        # Sort by severity
        findings.sort(key=lambda f: ['info', 'minor', 'major', 'critical'].index(f.severity.value))
        
        return findings
    
    def _analyze_architecture(self, file_path: str, content: str, lines: List[str]) -> List[ReviewFinding]:
        """Analyze architectural aspects"""
        findings = []
        
        # Check for design patterns
        for pattern_name, pattern_regex in self.design_patterns.items():
            if re.search(pattern_regex, content, re.MULTILINE):
                # Pattern detected - check if properly implemented
                if pattern_name == 'singleton':
                    if not re.search(r'__new__|_instance', content):
                        findings.append(ReviewFinding(
                            file_path=file_path,
                            line_number=1,
                            category=ReviewCategory.ARCHITECTURE,
                            severity=Severity.MINOR,
                            title="Incomplete Singleton Pattern",
                            description="Singleton pattern detected but implementation may be incomplete",
                            suggestion="Ensure thread-safe singleton implementation with __new__ method",
                            code_snippet="",
                            examples=["def __new__(cls): if not cls._instance: cls._instance = super().__new__(cls)"]
                        ))
        
        # Check for anti-patterns
        if file_path.endswith('.py'):
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Check for god class
                        methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                        if len(methods) > self.anti_patterns['god_class']['max_methods']:
                            findings.append(ReviewFinding(
                                file_path=file_path,
                                line_number=node.lineno,
                                category=ReviewCategory.ARCHITECTURE,
                                severity=Severity.MAJOR,
                                title="God Class Anti-pattern",
                                description=f"Class '{node.name}' has {len(methods)} methods (max recommended: {self.anti_patterns['god_class']['max_methods']})",
                                suggestion="Consider breaking down into smaller, focused classes following Single Responsibility Principle",
                                code_snippet=f"class {node.name}: # {len(methods)} methods"
                            ))
            except:
                pass
        
        return findings
    
    def _analyze_security(self, file_path: str, content: str, lines: List[str]) -> List[ReviewFinding]:
        """Analyze security aspects"""
        findings = []
        
        for vuln_name, pattern in self.security_patterns.items():
            for match in re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE):
                line_no = content[:match.start()].count('\n') + 1
                
                finding = ReviewFinding(
                    file_path=file_path,
                    line_number=line_no,
                    category=ReviewCategory.SECURITY,
                    severity=Severity.CRITICAL if vuln_name in ['sql_injection', 'command_injection'] else Severity.MAJOR,
                    title=f"Potential {vuln_name.replace('_', ' ').title()} Vulnerability",
                    description=self._get_security_description(vuln_name),
                    suggestion=self._get_security_suggestion(vuln_name),
                    code_snippet=lines[line_no-1].strip() if line_no <= len(lines) else "",
                    references=self._get_security_references(vuln_name)
                )
                findings.append(finding)
        
        return findings
    
    def _analyze_performance(self, file_path: str, content: str, lines: List[str]) -> List[ReviewFinding]:
        """Analyze performance aspects"""
        findings = []
        
        for perf_issue, pattern in self.performance_patterns.items():
            for match in re.finditer(pattern, content, re.MULTILINE):
                line_no = content[:match.start()].count('\n') + 1
                
                finding = ReviewFinding(
                    file_path=file_path,
                    line_number=line_no,
                    category=ReviewCategory.PERFORMANCE,
                    severity=Severity.MINOR if perf_issue == 'unnecessary_list' else Severity.MAJOR,
                    title=f"Performance Issue: {perf_issue.replace('_', ' ').title()}",
                    description=self._get_performance_description(perf_issue),
                    suggestion=self._get_performance_suggestion(perf_issue),
                    code_snippet=self._get_context_snippet(lines, line_no, 2)
                )
                findings.append(finding)
        
        return findings
    
    def _analyze_maintainability(self, file_path: str, content: str, lines: List[str]) -> List[ReviewFinding]:
        """Analyze maintainability aspects"""
        findings = []
        
        # Check for long methods
        if file_path.endswith('.py'):
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        method_lines = node.end_lineno - node.lineno
                        if method_lines > self.anti_patterns['long_method']['max_lines']:
                            findings.append(ReviewFinding(
                                file_path=file_path,
                                line_number=node.lineno,
                                category=ReviewCategory.MAINTAINABILITY,
                                severity=Severity.MINOR,
                                title="Long Method",
                                description=f"Method '{node.name}' has {method_lines} lines (max recommended: {self.anti_patterns['long_method']['max_lines']})",
                                suggestion="Consider extracting sub-methods or refactoring for better readability",
                                code_snippet=f"def {node.name}(...): # {method_lines} lines"
                            ))
                        
                        # Check for too many parameters
                        if len(node.args.args) > 5:
                            findings.append(ReviewFinding(
                                file_path=file_path,
                                line_number=node.lineno,
                                category=ReviewCategory.MAINTAINABILITY,
                                severity=Severity.MINOR,
                                title="Too Many Parameters",
                                description=f"Method '{node.name}' has {len(node.args.args)} parameters",
                                suggestion="Consider using a configuration object or **kwargs",
                                code_snippet=f"def {node.name}({', '.join(arg.arg for arg in node.args.args[:3])}...)"
                            ))
            except:
                pass
        
        # Check for duplicated code
        duplicate_blocks = self._find_duplicate_code(lines)
        for dup in duplicate_blocks:
            findings.append(ReviewFinding(
                file_path=file_path,
                line_number=dup['line'],
                category=ReviewCategory.MAINTAINABILITY,
                severity=Severity.MINOR,
                title="Duplicated Code",
                description=f"Similar code block found at lines {dup['similar_lines']}",
                suggestion="Extract common code into a reusable function",
                code_snippet=dup['code']
            ))
        
        return findings
    
    def _analyze_business_logic(self, file_path: str, content: str, lines: List[str]) -> List[ReviewFinding]:
        """Analyze business logic correctness"""
        findings = []
        
        # Check for missing validation
        for pattern_name, pattern in self.business_patterns.items():
            if pattern_name == 'validation':
                # Check if methods that should have validation actually do
                method_pattern = r'def\s+(create|update|process|submit)_\w+\([^)]*\):'
                for match in re.finditer(method_pattern, content):
                    method_start = match.start()
                    method_name = match.group(0)
                    
                    # Check next 10 lines for validation
                    method_content = content[method_start:method_start+500]
                    if not re.search(r'if\s+not|validate|raise|assert', method_content):
                        line_no = content[:method_start].count('\n') + 1
                        findings.append(ReviewFinding(
                            file_path=file_path,
                            line_number=line_no,
                            category=ReviewCategory.BUSINESS_LOGIC,
                            severity=Severity.MAJOR,
                            title="Missing Input Validation",
                            description=f"Method '{method_name}' appears to lack input validation",
                            suggestion="Add validation for input parameters before processing",
                            code_snippet=method_name,
                            examples=["if not data: raise ValueError('Data cannot be empty')"]
                        ))
        
        # Check for proper error handling in business operations
        business_methods = re.finditer(r'def\s+(?:process|calculate|transform)_\w+', content)
        for match in business_methods:
            method_start = match.start()
            method_content = content[method_start:method_start+1000]
            
            if not re.search(r'try:|except\s+\w+:', method_content):
                line_no = content[:method_start].count('\n') + 1
                findings.append(ReviewFinding(
                    file_path=file_path,
                    line_number=line_no,
                    category=ReviewCategory.BUSINESS_LOGIC,
                    severity=Severity.MINOR,
                    title="Missing Error Handling",
                    description="Business logic method lacks proper error handling",
                    suggestion="Add try-except blocks to handle potential business logic errors",
                    code_snippet=match.group(0)
                ))
        
        return findings
    
    def _analyze_python_specific(self, file_path: str, content: str) -> List[ReviewFinding]:
        """Python-specific analysis using AST"""
        findings = []
        
        try:
            tree = ast.parse(content)
            
            # Check for missing docstrings
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if not ast.get_docstring(node):
                        findings.append(ReviewFinding(
                            file_path=file_path,
                            line_number=node.lineno,
                            category=ReviewCategory.DOCUMENTATION,
                            severity=Severity.INFO,
                            title="Missing Docstring",
                            description=f"{'Function' if isinstance(node, ast.FunctionDef) else 'Class'} '{node.name}' lacks a docstring",
                            suggestion="Add a docstring explaining purpose, parameters, and return value",
                            code_snippet=f"def {node.name}(...):" if isinstance(node, ast.FunctionDef) else f"class {node.name}:",
                            examples=['"""Brief description of what this function does."""']
                        ))
            
            # Check for proper exception handling
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None:  # Bare except
                        findings.append(ReviewFinding(
                            file_path=file_path,
                            line_number=node.lineno,
                            category=ReviewCategory.BEST_PRACTICES,
                            severity=Severity.MINOR,
                            title="Bare Except Clause",
                            description="Using bare 'except:' catches all exceptions including system exits",
                            suggestion="Catch specific exceptions or use 'except Exception:' at minimum",
                            code_snippet="except:",
                            examples=["except ValueError:", "except (TypeError, KeyError):"]
                        ))
            
        except SyntaxError:
            findings.append(ReviewFinding(
                file_path=file_path,
                line_number=1,
                category=ReviewCategory.BEST_PRACTICES,
                severity=Severity.CRITICAL,
                title="Syntax Error",
                description="File contains syntax errors and cannot be parsed",
                suggestion="Fix syntax errors before review",
                code_snippet=""
            ))
        
        return findings
    
    def _analyze_changes(self, file_path: str, current: str, previous: str) -> List[ReviewFinding]:
        """Analyze changes between versions"""
        findings = []
        
        current_lines = current.split('\n')
        previous_lines = previous.split('\n')
        
        differ = difflib.unified_diff(previous_lines, current_lines, lineterm='')
        
        # Analyze the diff
        added_lines = []
        removed_lines = []
        
        for line in differ:
            if line.startswith('+') and not line.startswith('+++'):
                added_lines.append(line[1:])
            elif line.startswith('-') and not line.startswith('---'):
                removed_lines.append(line[1:])
        
        # Check if error handling was removed
        if any('try:' in line or 'except' in line for line in removed_lines):
            if not any('try:' in line or 'except' in line for line in added_lines):
                findings.append(ReviewFinding(
                    file_path=file_path,
                    line_number=1,
                    category=ReviewCategory.BEST_PRACTICES,
                    severity=Severity.MAJOR,
                    title="Error Handling Removed",
                    description="Error handling code was removed in this change",
                    suggestion="Ensure error handling is preserved or improved",
                    code_snippet=""
                ))
        
        # Check if tests were removed
        if any('test_' in line or 'assert' in line for line in removed_lines):
            findings.append(ReviewFinding(
                file_path=file_path,
                line_number=1,
                category=ReviewCategory.TESTING,
                severity=Severity.MAJOR,
                title="Test Code Removed",
                description="Test code or assertions were removed",
                suggestion="Ensure tests are maintained or replaced with better ones",
                code_snippet=""
            ))
        
        return findings
    
    def calculate_metrics(self, file_path: str) -> CodeMetrics:
        """Calculate code quality metrics"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except:
            return CodeMetrics(0, 0, 0, 0, 0, 0, 0, 0)
        
        # Basic metrics
        loc = len([l for l in lines if l.strip() and not l.strip().startswith('#')])
        comment_lines = len([l for l in lines if l.strip().startswith('#')])
        comment_ratio = comment_lines / max(loc, 1)
        
        # Complexity (simplified - count decision points)
        complexity = len(re.findall(r'\b(?:if|elif|else|for|while|and|or|try|except)\b', content))
        
        # Maintainability index (simplified formula)
        maintainability = max(0, min(100, 171 - 5.2 * np.log(loc) - 0.23 * complexity - 16.2 * np.log(max(loc, 1))))
        
        return CodeMetrics(
            complexity=complexity,
            maintainability_index=maintainability,
            lines_of_code=loc,
            comment_ratio=comment_ratio,
            test_coverage=0.0,  # Would need external tool
            duplication_ratio=0.0,  # Simplified
            coupling=0,  # Would need full project analysis
            cohesion=0.8  # Default
        )
    
    def _find_duplicate_code(self, lines: List[str], min_lines: int = 4) -> List[Dict[str, Any]]:
        """Find duplicated code blocks"""
        duplicates = []
        
        # Simple duplicate detection - could be enhanced
        for i in range(len(lines) - min_lines):
            block = lines[i:i+min_lines]
            block_str = '\n'.join(block).strip()
            
            if not block_str or all(not line.strip() for line in block):
                continue
            
            # Look for similar blocks
            for j in range(i + min_lines, len(lines) - min_lines):
                compare_block = lines[j:j+min_lines]
                compare_str = '\n'.join(compare_block).strip()
                
                if block_str == compare_str:
                    duplicates.append({
                        'line': i + 1,
                        'similar_lines': [j + 1],
                        'code': block_str[:100] + '...' if len(block_str) > 100 else block_str
                    })
                    break
        
        return duplicates[:3]  # Limit to top 3
    
    def _get_context_snippet(self, lines: List[str], line_no: int, context: int = 2) -> str:
        """Get code snippet with context"""
        start = max(0, line_no - context - 1)
        end = min(len(lines), line_no + context)
        
        snippet_lines = []
        for i in range(start, end):
            prefix = ">>>" if i == line_no - 1 else "   "
            snippet_lines.append(f"{prefix} {i+1}: {lines[i]}")
        
        return '\n'.join(snippet_lines)
    
    def _get_security_description(self, vuln_type: str) -> str:
        """Get description for security vulnerability"""
        descriptions = {
            'sql_injection': "User input appears to be directly concatenated into SQL query",
            'command_injection': "User input may be passed to system commands without sanitization",
            'path_traversal': "File paths may be manipulated to access unauthorized files",
            'hardcoded_secrets': "Sensitive information should not be hardcoded in source code",
            'weak_crypto': "Weak cryptographic algorithms are vulnerable to attacks"
        }
        return descriptions.get(vuln_type, "Security vulnerability detected")
    
    def _get_security_suggestion(self, vuln_type: str) -> str:
        """Get suggestion for security vulnerability"""
        suggestions = {
            'sql_injection': "Use parameterized queries or an ORM to prevent SQL injection",
            'command_injection': "Use subprocess with list arguments or validate/sanitize input",
            'path_traversal': "Validate and sanitize file paths, use os.path.join()",
            'hardcoded_secrets': "Use environment variables or secure key management",
            'weak_crypto': "Use strong algorithms like SHA-256, AES-256, or bcrypt"
        }
        return suggestions.get(vuln_type, "Review and fix security issue")
    
    def _get_security_references(self, vuln_type: str) -> List[str]:
        """Get references for security issues"""
        references = {
            'sql_injection': ["https://owasp.org/www-community/attacks/SQL_Injection"],
            'command_injection': ["https://owasp.org/www-community/attacks/Command_Injection"],
            'path_traversal': ["https://owasp.org/www-community/attacks/Path_Traversal"],
            'hardcoded_secrets': ["https://owasp.org/www-community/vulnerabilities/Use_of_hard-coded_password"],
            'weak_crypto': ["https://owasp.org/www-community/vulnerabilities/Weak_Cryptography"]
        }
        return references.get(vuln_type, [])
    
    def _get_performance_description(self, issue_type: str) -> str:
        """Get description for performance issue"""
        descriptions = {
            'n_plus_one': "Database queries inside loops can cause N+1 query problems",
            'inefficient_loop': "Loop operations could be optimized with list comprehensions or built-ins",
            'repeated_computation': "Same computation performed multiple times in loop",
            'unnecessary_list': "Creating a list when only one element is needed wastes memory"
        }
        return descriptions.get(issue_type, "Performance issue detected")
    
    def _get_performance_suggestion(self, issue_type: str) -> str:
        """Get suggestion for performance issue"""
        suggestions = {
            'n_plus_one': "Use select_related() or prefetch_related() for Django, or JOIN queries",
            'inefficient_loop': "Consider using list comprehension or generator expressions",
            'repeated_computation': "Move invariant computations outside the loop",
            'unnecessary_list': "Use next() or itertools.islice() instead of converting to list"
        }
        return suggestions.get(issue_type, "Optimize for better performance")

# Import numpy for metrics calculation
try:
    import numpy as np
except ImportError:
    # Fallback if numpy not available
    class np:
        @staticmethod
        def log(x):
            import math
            return math.log(x)

if __name__ == "__main__":
    # Test the code reviewer
    reviewer = SmartCodeReviewer()
    
    # Create a test file with various issues
    test_code = '''
class UserManager:
    def __init__(self):
        self.password = "admin123"  # Security issue
        self.users = []
    
    def create_user(self, name, email):
        # Missing validation
        user = {"name": name, "email": email}
        self.users.append(user)
        return user
    
    def authenticate(self, username, password):
        query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
        # SQL injection vulnerability
        return self.execute_query(query)
    
    def process_users(self):
        # Performance issue - N+1 queries
        for user in self.users:
            profile = self.get_user_profile(user['id'])
            posts = self.get_user_posts(user['id'])
    
    def long_method_example(self, data):
        # This method is too long
        result = []
        for item in data:
            if item > 0:
                result.append(item)
        
        total = 0
        for item in result:
            total += item
        
        average = total / len(result)
        
        # More processing...
        for i in range(100):
            print(i)
        
        return average
'''
    
    # Write test file
    test_file = "test_review.py"
    with open(test_file, 'w') as f:
        f.write(test_code)
    
    # Perform review
    findings = reviewer.review_code(test_file)
    
    print("Code Review Findings:")
    print("=" * 60)
    
    for finding in findings:
        print(f"\n{finding.severity.value.upper()} - {finding.category.value}")
        print(f"Line {finding.line_number}: {finding.title}")
        print(f"Description: {finding.description}")
        print(f"Suggestion: {finding.suggestion}")
        if finding.code_snippet:
            print(f"Code: {finding.code_snippet}")
    
    # Calculate metrics
    metrics = reviewer.calculate_metrics(test_file)
    print(f"\n\nCode Metrics:")
    print(f"Complexity: {metrics.complexity}")
    print(f"Maintainability: {metrics.maintainability_index:.1f}/100")
    print(f"Lines of Code: {metrics.lines_of_code}")
    print(f"Comment Ratio: {metrics.comment_ratio:.1%}")
    
    # Cleanup
    import os
    os.remove(test_file)