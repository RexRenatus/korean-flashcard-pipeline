#!/usr/bin/env python3
"""
SOLID Principle Enforcer for Code Hooks
Automatically checks code for SOLID principle violations and suggests improvements
"""

import sys
import ast
import re
import json
from typing import List, Dict, Any, Optional, Tuple, Set
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from flashcard_pipeline.utils import get_logger
    logger = get_logger(__name__)
except ImportError:
    # Fallback to basic logging
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


class SOLIDPrinciple(Enum):
    """SOLID principles enumeration"""
    SRP = "Single Responsibility Principle"
    OCP = "Open/Closed Principle"
    LSP = "Liskov Substitution Principle"
    ISP = "Interface Segregation Principle"
    DIP = "Dependency Inversion Principle"


@dataclass
class SOLIDViolation:
    """Represents a SOLID principle violation"""
    principle: SOLIDPrinciple
    severity: str  # "warning", "error"
    line_number: int
    message: str
    suggestion: str
    code_snippet: Optional[str] = None
    documentation_link: Optional[str] = None


class SOLIDEnforcer:
    """Enforces SOLID principles in Python code"""
    
    def __init__(self):
        self.current_year = datetime.now().year
        self.max_class_methods = 7  # SRP threshold
        self.max_method_lines = 30  # SRP threshold
        self.max_parameters = 4  # ISP threshold
        self.max_dependencies = 5  # DIP threshold
        
    def check_file(self, file_path: str, content: Optional[str] = None) -> List[SOLIDViolation]:
        """Check a file for SOLID principle violations"""
        violations = []
        
        try:
            if content is None:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            # Only check Python files
            if not file_path.endswith('.py'):
                return violations
            
            # Parse AST
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                logger.warning(f"Syntax error in {file_path}: {e}")
                return violations
            
            # Check each principle
            violations.extend(self._check_srp(tree, content))
            violations.extend(self._check_ocp(tree, content))
            violations.extend(self._check_lsp(tree, content))
            violations.extend(self._check_isp(tree, content))
            violations.extend(self._check_dip(tree, content))
            
            # Add documentation links with current year
            for violation in violations:
                violation.documentation_link = self._get_documentation_link(violation.principle)
            
        except Exception as e:
            logger.error(f"Error checking SOLID principles in {file_path}: {e}")
        
        return violations
    
    def _check_srp(self, tree: ast.AST, content: str) -> List[SOLIDViolation]:
        """Check Single Responsibility Principle"""
        violations = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Count responsibilities based on method categories
                method_categories = self._categorize_methods(node)
                if len(method_categories) > 1:
                    violations.append(SOLIDViolation(
                        principle=SOLIDPrinciple.SRP,
                        severity="warning",
                        line_number=node.lineno,
                        message=f"Class '{node.name}' has multiple responsibilities: {', '.join(method_categories)}",
                        suggestion="Consider splitting this class into separate classes, each handling a single responsibility",
                        code_snippet=f"class {node.name}:  # {len(method_categories)} responsibilities"
                    ))
                
                # Check for too many methods
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                if len(methods) > self.max_class_methods:
                    violations.append(SOLIDViolation(
                        principle=SOLIDPrinciple.SRP,
                        severity="error",
                        line_number=node.lineno,
                        message=f"Class '{node.name}' has {len(methods)} methods (max: {self.max_class_methods})",
                        suggestion="Break down this class into smaller, focused classes",
                        code_snippet=f"class {node.name}:  # {len(methods)} methods"
                    ))
            
            elif isinstance(node, ast.FunctionDef):
                # Check for long methods
                method_lines = self._count_function_lines(node)
                if method_lines > self.max_method_lines:
                    violations.append(SOLIDViolation(
                        principle=SOLIDPrinciple.SRP,
                        severity="warning",
                        line_number=node.lineno,
                        message=f"Method '{node.name}' has {method_lines} lines (max: {self.max_method_lines})",
                        suggestion="Extract sub-methods to reduce complexity",
                        code_snippet=f"def {node.name}(...):  # {method_lines} lines"
                    ))
        
        return violations
    
    def _check_ocp(self, tree: ast.AST, content: str) -> List[SOLIDViolation]:
        """Check Open/Closed Principle"""
        violations = []
        
        # Look for hardcoded type checks and isinstance chains
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Check for type checking patterns
                if self._is_type_checking_chain(node):
                    violations.append(SOLIDViolation(
                        principle=SOLIDPrinciple.OCP,
                        severity="warning",
                        line_number=node.lineno,
                        message="Multiple isinstance/type checks suggest violation of OCP",
                        suggestion="Use polymorphism or strategy pattern instead of type checking",
                        code_snippet="if isinstance(obj, TypeA): ... elif isinstance(obj, TypeB): ..."
                    ))
        
        # Check for switch-like patterns
        switch_patterns = re.findall(r'if\s+\w+\s*==\s*["\'].*?["\']\s*:.*?elif\s+\w+\s*==\s*["\'].*?["\']\s*:', content, re.DOTALL)
        if switch_patterns:
            violations.append(SOLIDViolation(
                principle=SOLIDPrinciple.OCP,
                severity="warning",
                line_number=1,
                message="Switch-like if/elif chains detected",
                suggestion="Consider using dictionary dispatch or strategy pattern",
                code_snippet="if x == 'a': ... elif x == 'b': ..."
            ))
        
        return violations
    
    def _check_lsp(self, tree: ast.AST, content: str) -> List[SOLIDViolation]:
        """Check Liskov Substitution Principle"""
        violations = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check for methods that raise NotImplementedError in child classes
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        if self._raises_not_implemented(item):
                            violations.append(SOLIDViolation(
                                principle=SOLIDPrinciple.LSP,
                                severity="error",
                                line_number=item.lineno,
                                message=f"Method '{item.name}' raises NotImplementedError in derived class",
                                suggestion="Ensure derived classes can substitute base classes without breaking functionality",
                                code_snippet=f"def {item.name}(...): raise NotImplementedError"
                            ))
                
                # Check for overridden methods with different signatures
                if node.bases:
                    for method in [n for n in node.body if isinstance(n, ast.FunctionDef)]:
                        if self._has_different_signature(method, node.bases):
                            violations.append(SOLIDViolation(
                                principle=SOLIDPrinciple.LSP,
                                severity="warning",
                                line_number=method.lineno,
                                message=f"Method '{method.name}' may have different signature than parent",
                                suggestion="Maintain consistent method signatures in inheritance hierarchy",
                                code_snippet=f"def {method.name}(...):  # Check parent signature"
                            ))
        
        return violations
    
    def _check_isp(self, tree: ast.AST, content: str) -> List[SOLIDViolation]:
        """Check Interface Segregation Principle"""
        violations = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check for ABC classes with too many abstract methods
                abstract_methods = self._count_abstract_methods(node)
                if abstract_methods > 5:
                    violations.append(SOLIDViolation(
                        principle=SOLIDPrinciple.ISP,
                        severity="warning",
                        line_number=node.lineno,
                        message=f"Interface '{node.name}' has {abstract_methods} abstract methods",
                        suggestion="Split into smaller, more focused interfaces",
                        code_snippet=f"class {node.name}(ABC):  # {abstract_methods} abstract methods"
                    ))
                
            elif isinstance(node, ast.FunctionDef):
                # Check for methods with too many parameters
                param_count = len(node.args.args) + len(node.args.kwonlyargs)
                if param_count > self.max_parameters:
                    violations.append(SOLIDViolation(
                        principle=SOLIDPrinciple.ISP,
                        severity="warning",
                        line_number=node.lineno,
                        message=f"Method '{node.name}' has {param_count} parameters (max: {self.max_parameters})",
                        suggestion="Consider using parameter objects or builder pattern",
                        code_snippet=f"def {node.name}({param_count} params):"
                    ))
        
        return violations
    
    def _check_dip(self, tree: ast.AST, content: str) -> List[SOLIDViolation]:
        """Check Dependency Inversion Principle"""
        violations = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check for concrete dependencies in __init__
                concrete_deps = self._find_concrete_dependencies(node)
                if len(concrete_deps) > self.max_dependencies:
                    violations.append(SOLIDViolation(
                        principle=SOLIDPrinciple.DIP,
                        severity="warning",
                        line_number=node.lineno,
                        message=f"Class '{node.name}' has {len(concrete_deps)} concrete dependencies",
                        suggestion="Depend on abstractions (interfaces/protocols) instead of concrete classes",
                        code_snippet=f"class {node.name}:  # {len(concrete_deps)} concrete deps"
                    ))
                
                # Check for direct instantiation of dependencies
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                        if self._has_direct_instantiation(item):
                            violations.append(SOLIDViolation(
                                principle=SOLIDPrinciple.DIP,
                                severity="error",
                                line_number=item.lineno,
                                message="Direct instantiation of dependencies in __init__",
                                suggestion="Inject dependencies instead of creating them",
                                code_snippet="self.dep = ConcreteClass()  # Should inject"
                            ))
        
        return violations
    
    def _categorize_methods(self, class_node: ast.ClassDef) -> Set[str]:
        """Categorize methods to detect multiple responsibilities"""
        categories = set()
        
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                name = node.name.lower()
                if any(prefix in name for prefix in ['get_', 'fetch_', 'load_', 'read_']):
                    categories.add("data_access")
                elif any(prefix in name for prefix in ['save_', 'store_', 'write_', 'persist_']):
                    categories.add("persistence")
                elif any(prefix in name for prefix in ['validate_', 'check_', 'verify_']):
                    categories.add("validation")
                elif any(prefix in name for prefix in ['calculate_', 'compute_', 'process_']):
                    categories.add("business_logic")
                elif any(prefix in name for prefix in ['format_', 'render_', 'display_']):
                    categories.add("presentation")
                elif any(prefix in name for prefix in ['send_', 'notify_', 'publish_']):
                    categories.add("communication")
        
        return categories
    
    def _count_function_lines(self, func_node: ast.FunctionDef) -> int:
        """Count actual lines of code in a function"""
        if hasattr(func_node, 'end_lineno'):
            return func_node.end_lineno - func_node.lineno
        return 0
    
    def _is_type_checking_chain(self, if_node: ast.If) -> bool:
        """Check if an if statement is a type checking chain"""
        isinstance_count = 0
        node = if_node
        
        while node:
            if isinstance(node.test, ast.Call) and isinstance(node.test.func, ast.Name):
                if node.test.func.id == 'isinstance':
                    isinstance_count += 1
            
            if hasattr(node, 'orelse') and node.orelse:
                if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                    node = node.orelse[0]
                else:
                    break
            else:
                break
        
        return isinstance_count > 2
    
    def _raises_not_implemented(self, func_node: ast.FunctionDef) -> bool:
        """Check if function raises NotImplementedError"""
        for node in ast.walk(func_node):
            if isinstance(node, ast.Raise):
                if isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name):
                    if node.exc.func.id == 'NotImplementedError':
                        return True
                elif isinstance(node.exc, ast.Name) and node.exc.id == 'NotImplementedError':
                    return True
        return False
    
    def _has_different_signature(self, method: ast.FunctionDef, bases: List[ast.expr]) -> bool:
        """Check if method might have different signature than parent"""
        # This is a simplified check - in practice would need to analyze parent classes
        return method.name not in ['__init__', '__str__', '__repr__'] and len(method.args.args) > 2
    
    def _count_abstract_methods(self, class_node: ast.ClassDef) -> int:
        """Count abstract methods in a class"""
        count = 0
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == 'abstractmethod':
                        count += 1
                        break
                    elif isinstance(decorator, ast.Attribute) and decorator.attr == 'abstractmethod':
                        count += 1
                        break
        return count
    
    def _find_concrete_dependencies(self, class_node: ast.ClassDef) -> List[str]:
        """Find concrete class dependencies"""
        deps = []
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef) and node.name == "__init__":
                for stmt in node.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Attribute) and isinstance(stmt.value, ast.Call):
                                if isinstance(stmt.value.func, ast.Name):
                                    # Check if it's a concrete class (capitalized)
                                    class_name = stmt.value.func.id
                                    if class_name[0].isupper() and class_name not in ['List', 'Dict', 'Set', 'Tuple']:
                                        deps.append(class_name)
        return deps
    
    def _has_direct_instantiation(self, init_node: ast.FunctionDef) -> bool:
        """Check if __init__ directly instantiates dependencies"""
        for stmt in init_node.body:
            if isinstance(stmt, ast.Assign):
                if isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name):
                    # Check if it's instantiating a class (not a function call)
                    if stmt.value.func.id[0].isupper():
                        return True
        return False
    
    def _get_documentation_link(self, principle: SOLIDPrinciple) -> str:
        """Get documentation link for SOLID principle with current year"""
        base_url = "https://docs.example.com"
        principle_paths = {
            SOLIDPrinciple.SRP: "single-responsibility",
            SOLIDPrinciple.OCP: "open-closed",
            SOLIDPrinciple.LSP: "liskov-substitution",
            SOLIDPrinciple.ISP: "interface-segregation",
            SOLIDPrinciple.DIP: "dependency-inversion"
        }
        path = principle_paths.get(principle, "solid-principles")
        return f"{base_url}/best-practices/{self.current_year}/{path}"
    
    def format_violations(self, violations: List[SOLIDViolation]) -> str:
        """Format violations for output"""
        if not violations:
            return "[SOLID] ✅ No SOLID principle violations detected"
        
        output = f"[SOLID] ⚠️  Found {len(violations)} SOLID principle violations:\n"
        
        for i, violation in enumerate(violations, 1):
            output += f"\n{i}. {violation.principle.value}\n"
            output += f"   Line {violation.line_number}: {violation.message}\n"
            output += f"   Suggestion: {violation.suggestion}\n"
            if violation.code_snippet:
                output += f"   Code: {violation.code_snippet}\n"
            if violation.documentation_link:
                output += f"   Learn more: {violation.documentation_link}\n"
        
        return output
    
    def suggest_mcp_search(self, violations: List[SOLIDViolation]) -> Dict[str, Any]:
        """Suggest MCP Ref searches for violations"""
        if not violations:
            return {}
        
        # Group violations by principle
        principles = {}
        for v in violations:
            if v.principle not in principles:
                principles[v.principle] = []
            principles[v.principle].append(v)
        
        # Generate search suggestions
        searches = []
        for principle, viols in principles.items():
            searches.append({
                "query": f"How to fix {principle.value} violations in Python {self.current_year}",
                "keywords": [
                    principle.name,
                    "SOLID",
                    "Python",
                    "best practices",
                    str(self.current_year)
                ],
                "source": "public"
            })
        
        return {
            "suggested_searches": searches,
            "violation_count": len(violations),
            "principles_violated": list(principles.keys())
        }


def main():
    """Main entry point for hook"""
    if len(sys.argv) < 3:
        print("Usage: solid_enforcer.py <file_path> <operation>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    operation = sys.argv[2] if len(sys.argv) > 2 else "check"
    
    enforcer = SOLIDEnforcer()
    
    # Check for violations
    violations = enforcer.check_file(file_path)
    
    # Output results
    print(enforcer.format_violations(violations))
    
    # Save results for other hooks
    results = {
        "file_path": file_path,
        "operation": operation,
        "violations": [
            {
                "principle": v.principle.name,
                "severity": v.severity,
                "line": v.line_number,
                "message": v.message,
                "suggestion": v.suggestion
            }
            for v in violations
        ],
        "mcp_suggestions": enforcer.suggest_mcp_search(violations),
        "solid_principles_checked": True,
        "timestamp": datetime.now().isoformat()
    }
    
    results_file = Path(".claude/solid_check_results.json")
    results_file.parent.mkdir(exist_ok=True)
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Determine exit code based on operation and violations
    critical_violations = [v for v in violations if v.severity == "error"]
    
    if operation == "pre-check":
        # Pre-check: warn but don't block
        if critical_violations:
            print(f"\n⚠️  WARNING: {len(critical_violations)} critical SOLID violations detected!")
            print("These violations should be fixed before proceeding.")
        sys.exit(0)  # Don't block pre-check
    
    elif operation == "post-check":
        # Post-check: block on critical violations
        if critical_violations:
            print(f"\n❌ ERROR: {len(critical_violations)} critical SOLID violations detected!")
            print("File modifications blocked due to SOLID principle violations.")
            print("Please fix the violations before committing changes.")
            sys.exit(1)  # Block on post-check
    
    # Default behavior for other operations
    if any(v.severity == "error" for v in violations):
        sys.exit(1)


if __name__ == "__main__":
    main()