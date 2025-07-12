#!/usr/bin/env python3
"""
Proactive Error Prevention System
Predicts and prevents errors before they occur based on patterns and static analysis
"""
import re
import ast
import json
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import sqlite3
from datetime import datetime
from collections import defaultdict

class ErrorCategory(Enum):
    """Categories of errors we can prevent"""
    SYNTAX = "syntax"
    RUNTIME = "runtime"
    LOGIC = "logic"
    PERFORMANCE = "performance"
    SECURITY = "security"
    INTEGRATION = "integration"
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"

class RiskLevel(Enum):
    """Risk levels for potential errors"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ErrorPattern:
    """Pattern that indicates potential error"""
    pattern: str
    category: ErrorCategory
    risk_level: RiskLevel
    description: str
    prevention: str
    examples: List[str] = field(default_factory=list)
    false_positive_rate: float = 0.1

@dataclass
class PotentialError:
    """Detected potential error"""
    file_path: str
    line_number: int
    category: ErrorCategory
    risk_level: RiskLevel
    description: str
    code_snippet: str
    prevention_suggestion: str
    confidence: float
    similar_past_errors: List[Dict[str, Any]] = field(default_factory=list)

class ErrorPreventionSystem:
    """Proactive error detection and prevention"""
    
    def __init__(self, error_history_db: Optional[str] = ".claude/error_history.db"):
        self.error_history_db = error_history_db
        self._init_database()
        
        # Initialize error patterns
        self.error_patterns = self._load_error_patterns()
        
        # Code smell patterns
        self.code_smells = {
            'unused_variable': re.compile(r'^(\s*)(\w+)\s*=.*(?!.*\2)', re.MULTILINE),
            'hardcoded_values': re.compile(r'["\'](?:localhost|127\.0\.0\.1|password|secret|api_key)["\']'),
            'broad_except': re.compile(r'except\s*:'),
            'missing_error_handling': re.compile(r'(open|requests\.|urlopen)\s*\([^)]*\)(?!\s*\.close)'),
            'sql_injection': re.compile(r'(execute|query)\s*\([^)]*%[^)]*\)'),
            'infinite_loop_risk': re.compile(r'while\s+True:|while\s+1:'),
            'missing_validation': re.compile(r'def\s+\w+\([^)]+\):\s*\n(?!\s*(?:if|assert|try))'),
        }
        
        # Common error contexts from history
        self.error_contexts = defaultdict(list)
        self._load_error_history()
        
    def _init_database(self):
        """Initialize error history database"""
        if not self.error_history_db:
            return
            
        conn = sqlite3.connect(self.error_history_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP,
                file_path TEXT,
                line_number INTEGER,
                error_type TEXT,
                error_message TEXT,
                code_context TEXT,
                fix_applied TEXT,
                prevented BOOLEAN
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_patterns (
                pattern_id TEXT PRIMARY KEY,
                pattern TEXT,
                category TEXT,
                risk_level TEXT,
                description TEXT,
                prevention TEXT,
                occurrence_count INTEGER,
                success_rate REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_error_patterns(self) -> List[ErrorPattern]:
        """Load error patterns"""
        patterns = [
            # Syntax patterns
            ErrorPattern(
                pattern=r'^\s*def\s+\w+\([^)]*\)\s*$',
                category=ErrorCategory.SYNTAX,
                risk_level=RiskLevel.HIGH,
                description="Function definition missing colon",
                prevention="Add ':' at end of function definition"
            ),
            
            # Runtime patterns
            ErrorPattern(
                pattern=r'(\w+)\[(["\w]+)\](?!\s*=)',
                category=ErrorCategory.RUNTIME,
                risk_level=RiskLevel.MEDIUM,
                description="Dictionary key access without checking existence",
                prevention="Use .get() method or check if key exists"
            ),
            
            ErrorPattern(
                pattern=r'int\s*\(\s*input\s*\(',
                category=ErrorCategory.RUNTIME,
                risk_level=RiskLevel.HIGH,
                description="Direct int conversion of user input",
                prevention="Add try-except for ValueError"
            ),
            
            # Logic patterns
            ErrorPattern(
                pattern=r'if\s+\w+\s*=\s*',
                category=ErrorCategory.LOGIC,
                risk_level=RiskLevel.CRITICAL,
                description="Assignment in if condition (should be ==)",
                prevention="Use == for comparison, not ="
            ),
            
            # Performance patterns
            ErrorPattern(
                pattern=r'for\s+\w+\s+in\s+.*:\s*\n\s*.*\.append\(',
                category=ErrorCategory.PERFORMANCE,
                risk_level=RiskLevel.LOW,
                description="Appending in loop (consider list comprehension)",
                prevention="Use list comprehension for better performance"
            ),
            
            # Security patterns
            ErrorPattern(
                pattern=r'eval\s*\(',
                category=ErrorCategory.SECURITY,
                risk_level=RiskLevel.CRITICAL,
                description="Use of eval() is dangerous",
                prevention="Use ast.literal_eval() or json.loads() instead"
            ),
            
            ErrorPattern(
                pattern=r'pickle\.load[s]?\s*\(',
                category=ErrorCategory.SECURITY,
                risk_level=RiskLevel.HIGH,
                description="Unpickling untrusted data is dangerous",
                prevention="Validate source or use JSON instead"
            ),
            
            # Integration patterns
            ErrorPattern(
                pattern=r'requests\.(get|post|put|delete)\s*\([^)]*\)(?!\s*\.raise_for_status)',
                category=ErrorCategory.INTEGRATION,
                risk_level=RiskLevel.MEDIUM,
                description="HTTP request without error checking",
                prevention="Add .raise_for_status() or check response.status_code"
            ),
            
            # Configuration patterns
            ErrorPattern(
                pattern=r'["\'](?:C:\\|/home/|/Users/)[^"\']*["\']',
                category=ErrorCategory.CONFIGURATION,
                risk_level=RiskLevel.MEDIUM,
                description="Hardcoded absolute path",
                prevention="Use os.path.join() or pathlib for portable paths"
            ),
            
            # Dependency patterns
            ErrorPattern(
                pattern=r'import\s+(\w+)(?!\s*#\s*type:\s*ignore)',
                category=ErrorCategory.DEPENDENCY,
                risk_level=RiskLevel.LOW,
                description="Import without error handling",
                prevention="Consider try-except ImportError for optional dependencies"
            ),
        ]
        
        # Load additional patterns from database
        if self.error_history_db:
            conn = sqlite3.connect(self.error_history_db)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM error_patterns')
            for row in cursor.fetchall():
                patterns.append(ErrorPattern(
                    pattern=row[1],
                    category=ErrorCategory(row[2]),
                    risk_level=RiskLevel(row[3]),
                    description=row[4],
                    prevention=row[5]
                ))
            conn.close()
        
        return patterns
    
    def _load_error_history(self):
        """Load error history for context"""
        if not self.error_history_db:
            return
            
        conn = sqlite3.connect(self.error_history_db)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT file_path, error_type, code_context, fix_applied
            FROM error_history
            WHERE prevented = 0
            ORDER BY timestamp DESC
            LIMIT 1000
        ''')
        
        for row in cursor.fetchall():
            file_path, error_type, code_context, fix_applied = row
            self.error_contexts[error_type].append({
                'file_path': file_path,
                'context': code_context,
                'fix': fix_applied
            })
        
        conn.close()
    
    def analyze_file(self, file_path: str) -> List[PotentialError]:
        """Analyze a file for potential errors"""
        potential_errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            return []
        
        # Check against error patterns
        for pattern_obj in self.error_patterns:
            pattern = re.compile(pattern_obj.pattern, re.MULTILINE)
            for match in pattern.finditer(content):
                line_no = content[:match.start()].count('\n') + 1
                
                # Get code snippet
                start_line = max(0, line_no - 2)
                end_line = min(len(lines), line_no + 2)
                snippet = '\n'.join(f"{i+1}: {lines[i]}" 
                                  for i in range(start_line, end_line))
                
                # Find similar past errors
                similar_errors = self._find_similar_errors(
                    pattern_obj.category.value, 
                    snippet
                )
                
                potential_errors.append(PotentialError(
                    file_path=file_path,
                    line_number=line_no,
                    category=pattern_obj.category,
                    risk_level=pattern_obj.risk_level,
                    description=pattern_obj.description,
                    code_snippet=snippet,
                    prevention_suggestion=pattern_obj.prevention,
                    confidence=1.0 - pattern_obj.false_positive_rate,
                    similar_past_errors=similar_errors
                ))
        
        # Python-specific analysis
        if file_path.endswith('.py'):
            python_errors = self._analyze_python_ast(file_path, content)
            potential_errors.extend(python_errors)
        
        # Check for code smells
        smell_errors = self._check_code_smells(file_path, content, lines)
        potential_errors.extend(smell_errors)
        
        # Sort by risk level and confidence
        potential_errors.sort(
            key=lambda e: (
                ['low', 'medium', 'high', 'critical'].index(e.risk_level.value),
                -e.confidence
            ),
            reverse=True
        )
        
        return potential_errors
    
    def _analyze_python_ast(self, file_path: str, content: str) -> List[PotentialError]:
        """Use AST analysis for Python-specific errors"""
        errors = []
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            # Syntax error itself
            return [PotentialError(
                file_path=file_path,
                line_number=e.lineno or 1,
                category=ErrorCategory.SYNTAX,
                risk_level=RiskLevel.CRITICAL,
                description=f"Syntax error: {e.msg}",
                code_snippet=f"{e.lineno}: {e.text}" if e.text else "",
                prevention_suggestion="Fix syntax error before proceeding",
                confidence=1.0
            )]
        
        # Check for common AST patterns
        for node in ast.walk(tree):
            # Undefined name usage (simplified check)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                # This is a simplified check - real implementation would track scope
                pass
            
            # Function with too many arguments
            if isinstance(node, ast.FunctionDef):
                if len(node.args.args) > 7:
                    errors.append(PotentialError(
                        file_path=file_path,
                        line_number=node.lineno,
                        category=ErrorCategory.LOGIC,
                        risk_level=RiskLevel.MEDIUM,
                        description=f"Function '{node.name}' has too many parameters ({len(node.args.args)})",
                        code_snippet=f"{node.lineno}: def {node.name}(...)",
                        prevention_suggestion="Consider using **kwargs or a configuration object",
                        confidence=0.9
                    ))
        
        return errors
    
    def _check_code_smells(self, file_path: str, content: str, 
                          lines: List[str]) -> List[PotentialError]:
        """Check for code smells"""
        errors = []
        
        for smell_name, pattern in self.code_smells.items():
            for match in pattern.finditer(content):
                line_no = content[:match.start()].count('\n') + 1
                
                if smell_name == 'unused_variable':
                    # Skip if it's actually used later
                    var_name = match.group(2)
                    if var_name in content[match.end():]:
                        continue
                
                risk_level = RiskLevel.HIGH if smell_name in ['hardcoded_values', 'sql_injection'] else RiskLevel.MEDIUM
                
                errors.append(PotentialError(
                    file_path=file_path,
                    line_number=line_no,
                    category=ErrorCategory.LOGIC if smell_name != 'hardcoded_values' else ErrorCategory.SECURITY,
                    risk_level=risk_level,
                    description=f"Code smell: {smell_name.replace('_', ' ')}",
                    code_snippet=lines[line_no-1] if line_no <= len(lines) else "",
                    prevention_suggestion=self._get_smell_prevention(smell_name),
                    confidence=0.8
                ))
        
        return errors
    
    def _get_smell_prevention(self, smell_name: str) -> str:
        """Get prevention suggestion for code smell"""
        suggestions = {
            'unused_variable': "Remove unused variable or use _ for intentionally unused",
            'hardcoded_values': "Move to configuration file or environment variables",
            'broad_except': "Catch specific exceptions instead of bare except",
            'missing_error_handling': "Add try-except or use context manager",
            'sql_injection': "Use parameterized queries to prevent SQL injection",
            'infinite_loop_risk': "Add break condition or use for loop with range",
            'missing_validation': "Add input validation at function start"
        }
        return suggestions.get(smell_name, "Review and refactor this code")
    
    def _find_similar_errors(self, error_type: str, context: str) -> List[Dict[str, Any]]:
        """Find similar errors from history"""
        similar = []
        
        if error_type in self.error_contexts:
            # Simple similarity check - could be enhanced with better algorithms
            context_words = set(context.lower().split())
            for past_error in self.error_contexts[error_type][:3]:
                past_words = set(past_error['context'].lower().split())
                similarity = len(context_words & past_words) / max(len(context_words), len(past_words))
                if similarity > 0.3:
                    similar.append(past_error)
        
        return similar
    
    def suggest_fixes(self, errors: List[PotentialError]) -> Dict[str, Any]:
        """Suggest fixes for detected errors"""
        fixes = {
            'immediate': [],  # Must fix now
            'important': [],  # Should fix soon
            'consider': []    # Nice to fix
        }
        
        for error in errors:
            fix = {
                'file': error.file_path,
                'line': error.line_number,
                'issue': error.description,
                'fix': error.prevention_suggestion,
                'category': error.category.value,
                'confidence': error.confidence
            }
            
            if error.risk_level == RiskLevel.CRITICAL:
                fixes['immediate'].append(fix)
            elif error.risk_level == RiskLevel.HIGH:
                fixes['important'].append(fix)
            else:
                fixes['consider'].append(fix)
        
        return fixes
    
    def learn_from_error(self, error_info: Dict[str, Any]):
        """Learn from an error that occurred"""
        if not self.error_history_db:
            return
            
        conn = sqlite3.connect(self.error_history_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO error_history 
            (timestamp, file_path, line_number, error_type, 
             error_message, code_context, fix_applied, prevented)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now(),
            error_info.get('file_path'),
            error_info.get('line_number', 0),
            error_info.get('error_type'),
            error_info.get('error_message'),
            error_info.get('code_context'),
            error_info.get('fix_applied'),
            error_info.get('prevented', False)
        ))
        
        conn.commit()
        conn.close()
        
        # Update error contexts
        self.error_contexts[error_info.get('error_type', 'unknown')].append({
            'file_path': error_info.get('file_path'),
            'context': error_info.get('code_context'),
            'fix': error_info.get('fix_applied')
        })

def analyze_project_for_errors(project_path: str) -> Dict[str, Any]:
    """Analyze entire project for potential errors"""
    prevention_system = ErrorPreventionSystem()
    all_errors = []
    
    # Analyze Python files
    for py_file in Path(project_path).rglob("*.py"):
        if 'venv' in str(py_file) or '__pycache__' in str(py_file):
            continue
        errors = prevention_system.analyze_file(str(py_file))
        all_errors.extend(errors)
    
    # Generate report
    report = {
        'total_issues': len(all_errors),
        'by_category': defaultdict(int),
        'by_risk': defaultdict(int),
        'critical_issues': [],
        'files_analyzed': len(set(e.file_path for e in all_errors))
    }
    
    for error in all_errors:
        report['by_category'][error.category.value] += 1
        report['by_risk'][error.risk_level.value] += 1
        
        if error.risk_level == RiskLevel.CRITICAL:
            report['critical_issues'].append({
                'file': error.file_path,
                'line': error.line_number,
                'issue': error.description,
                'fix': error.prevention_suggestion
            })
    
    # Get suggested fixes
    fixes = prevention_system.suggest_fixes(all_errors)
    report['suggested_fixes'] = fixes
    
    return report

if __name__ == "__main__":
    # Test the error prevention system
    prevention = ErrorPreventionSystem()
    
    # Analyze a sample file
    test_code = '''
def process_data(data):
    result = []
    for item in data:
        result.append(item * 2)
    
    config = {"host": "localhost", "password": "secret123"}
    
    try:
        value = data["key"]
    except:
        pass
    
    user_input = input("Enter number: ")
    number = int(user_input)
    
    return result
'''
    
    # Write test code to temp file
    test_file = "test_error_check.py"
    with open(test_file, 'w') as f:
        f.write(test_code)
    
    # Analyze
    errors = prevention.analyze_file(test_file)
    
    print("Potential Errors Found:")
    print("=" * 50)
    
    for error in errors:
        print(f"\n{error.risk_level.value.upper()} - {error.category.value}")
        print(f"Line {error.line_number}: {error.description}")
        print(f"Fix: {error.prevention_suggestion}")
        print(f"Confidence: {error.confidence:.1%}")
    
    # Cleanup
    import os
    os.remove(test_file)
    
    # Get fix suggestions
    fixes = prevention.suggest_fixes(errors)
    print("\n\nSuggested Fix Priority:")
    print("=" * 50)
    for priority, fix_list in fixes.items():
        if fix_list:
            print(f"\n{priority.upper()}:")
            for fix in fix_list:
                print(f"  - Line {fix['line']}: {fix['fix']}")