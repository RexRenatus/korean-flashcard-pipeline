"""
Safe filter expression parser for CLI queries.
Replaces unsafe eval() with a secure expression evaluator.
"""

import re
import operator
from typing import Dict, Any, Callable, Optional


class SafeFilterParser:
    """Parse and evaluate filter expressions safely without eval()"""
    
    # Supported operators
    OPERATORS = {
        '==': operator.eq,
        '!=': operator.ne,
        '>': operator.gt,
        '>=': operator.ge,
        '<': operator.lt,
        '<=': operator.le,
        'in': lambda x, y: x in y,
        'not in': lambda x, y: x not in y,
        'contains': lambda x, y: y in x,
        'startswith': lambda x, y: x.startswith(y),
        'endswith': lambda x, y: x.endswith(y),
    }
    
    # Logical operators
    LOGICAL_OPS = {
        'and': operator.and_,
        'or': operator.or_,
    }
    
    def __init__(self):
        # Compile regex patterns
        self.field_pattern = re.compile(r"row\['([^']+)'\]|row\.(\w+)")
        self.string_pattern = re.compile(r"'([^']*)'|\"([^\"]*)\"")
        self.number_pattern = re.compile(r'-?\d+\.?\d*')
        
    def parse_value(self, value_str: str) -> Any:
        """Parse a value from string representation"""
        value_str = value_str.strip()
        
        # Check for string literals
        string_match = self.string_pattern.match(value_str)
        if string_match:
            return string_match.group(1) or string_match.group(2)
        
        # Check for numbers
        if self.number_pattern.match(value_str):
            try:
                if '.' in value_str:
                    return float(value_str)
                return int(value_str)
            except ValueError:
                pass
        
        # Check for boolean
        if value_str.lower() == 'true':
            return True
        elif value_str.lower() == 'false':
            return False
        elif value_str.lower() == 'none' or value_str.lower() == 'null':
            return None
        
        # Return as string if nothing else matches
        return value_str
    
    def get_field_value(self, row: Dict[str, Any], field_expr: str) -> Any:
        """Extract field value from row dictionary"""
        # Match row['field'] or row.field syntax
        match = self.field_pattern.match(field_expr)
        if match:
            field_name = match.group(1) or match.group(2)
            return row.get(field_name)
        
        # Try direct field name
        return row.get(field_expr.strip())
    
    def evaluate_simple_expression(self, expr: str, row: Dict[str, Any]) -> bool:
        """Evaluate a simple comparison expression"""
        expr = expr.strip()
        
        # Find operator
        for op_str, op_func in sorted(self.OPERATORS.items(), key=lambda x: -len(x[0])):
            if op_str in expr:
                parts = expr.split(op_str, 1)
                if len(parts) == 2:
                    left_expr = parts[0].strip()
                    right_expr = parts[1].strip()
                    
                    # Get left value (field)
                    left_value = self.get_field_value(row, left_expr)
                    
                    # Get right value (literal or field)
                    if right_expr.startswith('row'):
                        right_value = self.get_field_value(row, right_expr)
                    else:
                        right_value = self.parse_value(right_expr)
                    
                    # Perform comparison
                    try:
                        return op_func(left_value, right_value)
                    except Exception:
                        return False
        
        # If no operator found, check for boolean field
        field_value = self.get_field_value(row, expr)
        return bool(field_value)
    
    def evaluate(self, filter_expr: str, row: Dict[str, Any]) -> bool:
        """Evaluate a filter expression against a row"""
        if not filter_expr:
            return True
        
        filter_expr = filter_expr.strip()
        
        # Handle parentheses by evaluating innermost first
        while '(' in filter_expr:
            # Find innermost parentheses
            start = filter_expr.rfind('(')
            end = filter_expr.find(')', start)
            if end == -1:
                raise ValueError("Unmatched parentheses in filter expression")
            
            # Evaluate inner expression
            inner_expr = filter_expr[start+1:end]
            inner_result = self.evaluate(inner_expr, row)
            
            # Replace with result
            filter_expr = filter_expr[:start] + str(inner_result) + filter_expr[end+1:]
        
        # Handle logical operators (and/or)
        for log_op in [' and ', ' or ']:
            if log_op in filter_expr.lower():
                parts = filter_expr.split(log_op, 1)
                if len(parts) == 2:
                    left_result = self.evaluate(parts[0].strip(), row)
                    right_result = self.evaluate(parts[1].strip(), row)
                    
                    if log_op.strip() == 'and':
                        return left_result and right_result
                    else:  # or
                        return left_result or right_result
        
        # Handle 'not' operator
        if filter_expr.lower().startswith('not '):
            return not self.evaluate(filter_expr[4:].strip(), row)
        
        # Evaluate simple expression
        return self.evaluate_simple_expression(filter_expr, row)


def create_safe_filter(filter_expr: str) -> Callable[[Dict[str, Any]], bool]:
    """Create a safe filter function from an expression string
    
    Args:
        filter_expr: Filter expression like "row['type'] == 'noun'"
        
    Returns:
        A function that takes a row dict and returns True/False
    """
    parser = SafeFilterParser()
    
    def filter_func(row: Dict[str, Any]) -> bool:
        try:
            return parser.evaluate(filter_expr, row)
        except Exception as e:
            # Log error and return False for invalid expressions
            print(f"Filter error: {e}")
            return False
    
    return filter_func


# Example usage and testing
if __name__ == "__main__":
    # Test cases
    test_row = {
        'type': 'noun',
        'position': 5,
        'term': '학교',
        'difficulty': 'easy'
    }
    
    test_expressions = [
        "row['type'] == 'noun'",
        "row.type == 'noun'",
        "row['position'] > 3",
        "row['position'] >= 5 and row['type'] == 'noun'",
        "row['term'] contains '학'",
        "row['difficulty'] in ['easy', 'medium']",
        "row['type'] == 'verb' or row['position'] < 10",
    ]
    
    parser = SafeFilterParser()
    for expr in test_expressions:
        result = parser.evaluate(expr, test_row)
        print(f"{expr} -> {result}")