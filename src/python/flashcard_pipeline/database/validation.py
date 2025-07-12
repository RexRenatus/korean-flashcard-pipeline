"""
Data validation layer for database operations.
Provides input validation, sanitization, and constraint checking.
"""

import re
from typing import Any, Dict, List, Optional, Union, Type
from datetime import datetime
from enum import Enum
import html
import json
from pydantic import BaseModel, Field, field_validator, ConfigDict

from ..models import VocabularyItem
from ..exceptions import ValidationError


class ValidationType(str, Enum):
    """Types of validation to perform"""
    REQUIRED = "required"
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    JSON = "json"
    ENUM = "enum"
    REGEX = "regex"
    LENGTH = "length"
    RANGE = "range"
    SQL_SAFE = "sql_safe"
    HTML_SAFE = "html_safe"
    UNIQUE = "unique"
    FOREIGN_KEY = "foreign_key"


class ValidationRule(BaseModel):
    """Defines a validation rule"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    type: ValidationType
    required: bool = False
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    pattern: Optional[str] = None
    enum_values: Optional[List[Any]] = None
    custom_validator: Optional[callable] = None
    error_message: Optional[str] = None
    
    @field_validator('pattern')
    def validate_pattern(cls, v):
        """Validate regex pattern"""
        if v:
            try:
                re.compile(v)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
        return v


class FieldValidation(BaseModel):
    """Validation configuration for a field"""
    name: str
    rules: List[ValidationRule]
    sanitize: bool = True
    strip_whitespace: bool = True
    normalize_unicode: bool = True


class DataValidator:
    """Main data validation class"""
    
    # Common SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(union|select|insert|update|delete|drop|create|alter|exec|execute|script|javascript)",
        r"(--|#|\/\*|\*\/|;)",
        r"(xp_|sp_|0x)",
        r"(char|nchar|varchar|nvarchar|cast|convert|concat)",
    ]
    
    # HTML/XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
    ]
    
    def __init__(self):
        self.compiled_sql_patterns = [re.compile(p, re.IGNORECASE) for p in self.SQL_INJECTION_PATTERNS]
        self.compiled_xss_patterns = [re.compile(p, re.IGNORECASE) for p in self.XSS_PATTERNS]
    
    def validate_field(self, value: Any, rules: List[ValidationRule], field_name: str) -> Any:
        """Validate a single field against rules"""
        # Check required
        if value is None or value == "":
            for rule in rules:
                if rule.type == ValidationType.REQUIRED and rule.required:
                    raise ValidationError(
                        rule.error_message or f"Field '{field_name}' is required"
                    )
            return None
        
        # Apply each validation rule
        for rule in rules:
            try:
                if rule.type == ValidationType.STRING:
                    self._validate_string(value, rule, field_name)
                elif rule.type == ValidationType.INTEGER:
                    value = self._validate_integer(value, rule, field_name)
                elif rule.type == ValidationType.FLOAT:
                    value = self._validate_float(value, rule, field_name)
                elif rule.type == ValidationType.BOOLEAN:
                    value = self._validate_boolean(value, rule, field_name)
                elif rule.type == ValidationType.DATETIME:
                    value = self._validate_datetime(value, rule, field_name)
                elif rule.type == ValidationType.JSON:
                    value = self._validate_json(value, rule, field_name)
                elif rule.type == ValidationType.ENUM:
                    self._validate_enum(value, rule, field_name)
                elif rule.type == ValidationType.REGEX:
                    self._validate_regex(value, rule, field_name)
                elif rule.type == ValidationType.LENGTH:
                    self._validate_length(value, rule, field_name)
                elif rule.type == ValidationType.RANGE:
                    self._validate_range(value, rule, field_name)
                elif rule.type == ValidationType.SQL_SAFE:
                    self._validate_sql_safe(value, rule, field_name)
                elif rule.type == ValidationType.HTML_SAFE:
                    self._validate_html_safe(value, rule, field_name)
                
                # Custom validator
                if rule.custom_validator:
                    value = rule.custom_validator(value, field_name)
                    
            except ValidationError:
                raise
            except Exception as e:
                raise ValidationError(f"Validation error for field '{field_name}': {str(e)}")
        
        return value
    
    def _validate_string(self, value: Any, rule: ValidationRule, field_name: str) -> str:
        """Validate string type"""
        if not isinstance(value, str):
            try:
                value = str(value)
            except:
                raise ValidationError(f"Field '{field_name}' must be a string")
        return value
    
    def _validate_integer(self, value: Any, rule: ValidationRule, field_name: str) -> int:
        """Validate integer type"""
        try:
            return int(value)
        except:
            raise ValidationError(f"Field '{field_name}' must be an integer")
    
    def _validate_float(self, value: Any, rule: ValidationRule, field_name: str) -> float:
        """Validate float type"""
        try:
            return float(value)
        except:
            raise ValidationError(f"Field '{field_name}' must be a number")
    
    def _validate_boolean(self, value: Any, rule: ValidationRule, field_name: str) -> bool:
        """Validate boolean type"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            if value.lower() in ['true', '1', 'yes', 'on']:
                return True
            elif value.lower() in ['false', '0', 'no', 'off']:
                return False
        raise ValidationError(f"Field '{field_name}' must be a boolean")
    
    def _validate_datetime(self, value: Any, rule: ValidationRule, field_name: str) -> datetime:
        """Validate datetime type"""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except:
                pass
        raise ValidationError(f"Field '{field_name}' must be a valid datetime")
    
    def _validate_json(self, value: Any, rule: ValidationRule, field_name: str) -> Any:
        """Validate JSON type"""
        if isinstance(value, str):
            try:
                return json.loads(value)
            except:
                raise ValidationError(f"Field '{field_name}' must be valid JSON")
        return value
    
    def _validate_enum(self, value: Any, rule: ValidationRule, field_name: str):
        """Validate enum values"""
        if rule.enum_values and value not in rule.enum_values:
            raise ValidationError(
                f"Field '{field_name}' must be one of: {', '.join(str(v) for v in rule.enum_values)}"
            )
    
    def _validate_regex(self, value: Any, rule: ValidationRule, field_name: str):
        """Validate against regex pattern"""
        if rule.pattern and isinstance(value, str):
            if not re.match(rule.pattern, value):
                raise ValidationError(
                    rule.error_message or f"Field '{field_name}' does not match required pattern"
                )
    
    def _validate_length(self, value: Any, rule: ValidationRule, field_name: str):
        """Validate length constraints"""
        if hasattr(value, '__len__'):
            length = len(value)
            if rule.min_length is not None and length < rule.min_length:
                raise ValidationError(
                    f"Field '{field_name}' must be at least {rule.min_length} characters"
                )
            if rule.max_length is not None and length > rule.max_length:
                raise ValidationError(
                    f"Field '{field_name}' must be at most {rule.max_length} characters"
                )
    
    def _validate_range(self, value: Any, rule: ValidationRule, field_name: str):
        """Validate numeric range"""
        if isinstance(value, (int, float)):
            if rule.min_value is not None and value < rule.min_value:
                raise ValidationError(
                    f"Field '{field_name}' must be at least {rule.min_value}"
                )
            if rule.max_value is not None and value > rule.max_value:
                raise ValidationError(
                    f"Field '{field_name}' must be at most {rule.max_value}"
                )
    
    def _validate_sql_safe(self, value: Any, rule: ValidationRule, field_name: str):
        """Check for SQL injection patterns"""
        if isinstance(value, str):
            for pattern in self.compiled_sql_patterns:
                if pattern.search(value):
                    raise ValidationError(
                        f"Field '{field_name}' contains potentially unsafe SQL patterns"
                    )
    
    def _validate_html_safe(self, value: Any, rule: ValidationRule, field_name: str):
        """Check for XSS patterns"""
        if isinstance(value, str):
            for pattern in self.compiled_xss_patterns:
                if pattern.search(value):
                    raise ValidationError(
                        f"Field '{field_name}' contains potentially unsafe HTML/script patterns"
                    )
    
    def sanitize_string(self, value: str, strip_whitespace: bool = True, 
                       normalize_unicode: bool = True, escape_html: bool = False) -> str:
        """Sanitize string value"""
        if not isinstance(value, str):
            return value
        
        # Strip whitespace
        if strip_whitespace:
            value = value.strip()
        
        # Normalize unicode
        if normalize_unicode:
            import unicodedata
            value = unicodedata.normalize('NFKC', value)
        
        # Escape HTML
        if escape_html:
            value = html.escape(value)
        
        return value
    
    def validate_vocabulary_item(self, item: Union[Dict, VocabularyItem]) -> Dict:
        """Validate vocabulary item data"""
        if isinstance(item, VocabularyItem):
            data = item.model_dump()
        else:
            data = item
        
        # Define validation rules
        validations = [
            FieldValidation(
                name="term",
                rules=[
                    ValidationRule(type=ValidationType.REQUIRED, required=True),
                    ValidationRule(type=ValidationType.STRING),
                    ValidationRule(type=ValidationType.LENGTH, min_length=1, max_length=100),
                    ValidationRule(type=ValidationType.SQL_SAFE),
                ]
            ),
            FieldValidation(
                name="meaning",
                rules=[
                    ValidationRule(type=ValidationType.STRING),
                    ValidationRule(type=ValidationType.LENGTH, max_length=500),
                    ValidationRule(type=ValidationType.SQL_SAFE),
                    ValidationRule(type=ValidationType.HTML_SAFE),
                ]
            ),
            FieldValidation(
                name="position",
                rules=[
                    ValidationRule(type=ValidationType.INTEGER),
                    ValidationRule(type=ValidationType.RANGE, min_value=0),
                ]
            ),
        ]
        
        # Validate each field
        validated_data = {}
        for field_validation in validations:
            if field_validation.name in data:
                value = data[field_validation.name]
                
                # Sanitize if enabled
                if field_validation.sanitize and isinstance(value, str):
                    value = self.sanitize_string(
                        value, 
                        field_validation.strip_whitespace,
                        field_validation.normalize_unicode
                    )
                
                # Validate
                validated_data[field_validation.name] = self.validate_field(
                    value, field_validation.rules, field_validation.name
                )
        
        # Copy over unvalidated fields
        for key, value in data.items():
            if key not in validated_data:
                validated_data[key] = value
        
        return validated_data
    
    def validate_database_input(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generic database input validation"""
        validated = {}
        
        for key, value in data.items():
            # Basic sanitization for all string values
            if isinstance(value, str):
                # Check for SQL injection
                for pattern in self.compiled_sql_patterns:
                    if pattern.search(value):
                        raise ValidationError(
                            f"Field '{key}' contains potentially unsafe SQL patterns"
                        )
                
                # Sanitize
                value = self.sanitize_string(value)
            
            validated[key] = value
        
        return validated


class ConstraintValidator:
    """Validates database constraints"""
    
    def __init__(self, db_connection):
        self.conn = db_connection
    
    def check_unique_constraint(self, table: str, column: str, value: Any, 
                               exclude_id: Optional[int] = None) -> bool:
        """Check if value violates unique constraint"""
        query = f"SELECT COUNT(*) FROM {table} WHERE {column} = ?"
        params = [value]
        
        if exclude_id:
            query += " AND id != ?"
            params.append(exclude_id)
        
        cursor = self.conn.execute(query, params)
        count = cursor.fetchone()[0]
        
        return count == 0
    
    def check_foreign_key(self, table: str, column: str, value: Any) -> bool:
        """Check if foreign key exists"""
        # Extract referenced table and column from schema
        cursor = self.conn.execute(f"PRAGMA foreign_key_list({table})")
        for row in cursor:
            if row[3] == column:  # from column
                ref_table = row[2]  # referenced table
                ref_column = row[4]  # referenced column
                
                query = f"SELECT COUNT(*) FROM {ref_table} WHERE {ref_column} = ?"
                count_cursor = self.conn.execute(query, [value])
                count = count_cursor.fetchone()[0]
                
                return count > 0
        
        return True  # No foreign key constraint found
    
    def get_constraint_message(self, error: Exception) -> str:
        """Get user-friendly message for constraint violation"""
        error_str = str(error).lower()
        
        if "unique constraint" in error_str:
            # Extract column name if possible
            if "column" in error_str:
                return "This value already exists. Please use a different value."
            return "Duplicate value detected. This field must be unique."
        
        elif "foreign key constraint" in error_str:
            return "Referenced item does not exist. Please check your selection."
        
        elif "not null constraint" in error_str:
            return "This field is required and cannot be empty."
        
        elif "check constraint" in error_str:
            return "Value does not meet validation requirements."
        
        else:
            return "Database constraint violation. Please check your input."


class TransactionValidator:
    """Validates and manages database transactions"""
    
    def __init__(self, db_connection):
        self.conn = db_connection
        self.in_transaction = False
        self.savepoint_counter = 0
    
    def begin_transaction(self):
        """Start a new transaction"""
        if not self.in_transaction:
            self.conn.execute("BEGIN")
            self.in_transaction = True
    
    def create_savepoint(self) -> str:
        """Create a savepoint for nested transactions"""
        self.savepoint_counter += 1
        savepoint_name = f"sp_{self.savepoint_counter}"
        self.conn.execute(f"SAVEPOINT {savepoint_name}")
        return savepoint_name
    
    def rollback_to_savepoint(self, savepoint_name: str):
        """Rollback to a specific savepoint"""
        self.conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
    
    def release_savepoint(self, savepoint_name: str):
        """Release a savepoint"""
        self.conn.execute(f"RELEASE SAVEPOINT {savepoint_name}")
    
    def commit(self):
        """Commit the transaction"""
        if self.in_transaction:
            self.conn.execute("COMMIT")
            self.in_transaction = False
    
    def rollback(self):
        """Rollback the entire transaction"""
        if self.in_transaction:
            self.conn.execute("ROLLBACK")
            self.in_transaction = False


def create_validation_schema(table: str) -> List[FieldValidation]:
    """Create validation schema for a table"""
    schemas = {
        "vocabulary": [
            FieldValidation(
                name="korean",
                rules=[
                    ValidationRule(type=ValidationType.REQUIRED, required=True),
                    ValidationRule(type=ValidationType.STRING),
                    ValidationRule(type=ValidationType.LENGTH, min_length=1, max_length=100),
                    ValidationRule(type=ValidationType.SQL_SAFE),
                ]
            ),
            FieldValidation(
                name="english",
                rules=[
                    ValidationRule(type=ValidationType.STRING),
                    ValidationRule(type=ValidationType.LENGTH, max_length=200),
                    ValidationRule(type=ValidationType.SQL_SAFE),
                ]
            ),
            FieldValidation(
                name="difficulty_level",
                rules=[
                    ValidationRule(type=ValidationType.INTEGER),
                    ValidationRule(type=ValidationType.RANGE, min_value=1, max_value=10),
                ]
            ),
            FieldValidation(
                name="frequency_rank",
                rules=[
                    ValidationRule(type=ValidationType.INTEGER),
                    ValidationRule(type=ValidationType.RANGE, min_value=1),
                ]
            ),
        ],
        "processing_tasks": [
            FieldValidation(
                name="task_id",
                rules=[
                    ValidationRule(type=ValidationType.REQUIRED, required=True),
                    ValidationRule(type=ValidationType.STRING),
                    ValidationRule(type=ValidationType.REGEX, pattern=r"^[a-zA-Z0-9\-_]+$"),
                ]
            ),
            FieldValidation(
                name="priority",
                rules=[
                    ValidationRule(type=ValidationType.INTEGER),
                    ValidationRule(type=ValidationType.RANGE, min_value=1, max_value=10),
                ]
            ),
            FieldValidation(
                name="status",
                rules=[
                    ValidationRule(type=ValidationType.ENUM, 
                                 enum_values=["pending", "processing", "completed", "failed", "cancelled"]),
                ]
            ),
        ],
        "cache_entries": [
            FieldValidation(
                name="cache_key",
                rules=[
                    ValidationRule(type=ValidationType.REQUIRED, required=True),
                    ValidationRule(type=ValidationType.STRING),
                    ValidationRule(type=ValidationType.LENGTH, max_length=255),
                    ValidationRule(type=ValidationType.SQL_SAFE),
                ]
            ),
            FieldValidation(
                name="cache_value",
                rules=[
                    ValidationRule(type=ValidationType.REQUIRED, required=True),
                    ValidationRule(type=ValidationType.JSON),
                ]
            ),
            FieldValidation(
                name="ttl_seconds",
                rules=[
                    ValidationRule(type=ValidationType.INTEGER),
                    ValidationRule(type=ValidationType.RANGE, min_value=0),
                ]
            ),
        ]
    }
    
    return schemas.get(table, [])