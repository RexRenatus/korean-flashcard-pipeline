"""
Unit tests for data validation layer.
"""

import pytest
from datetime import datetime
import json

from flashcard_pipeline.database.validation import (
    DataValidator, ValidationRule, ValidationType, FieldValidation,
    ConstraintValidator, TransactionValidator, create_validation_schema
)
from flashcard_pipeline.exceptions import ValidationError


class TestDataValidator:
    """Test data validator functionality"""
    
    @pytest.fixture
    def validator(self):
        return DataValidator()
    
    def test_required_field_validation(self, validator):
        """Test required field validation"""
        rules = [ValidationRule(type=ValidationType.REQUIRED, required=True)]
        
        # Should raise for None
        with pytest.raises(ValidationError, match="required"):
            validator.validate_field(None, rules, "test_field")
        
        # Should raise for empty string
        with pytest.raises(ValidationError, match="required"):
            validator.validate_field("", rules, "test_field")
        
        # Should pass for valid value
        result = validator.validate_field("value", rules, "test_field")
        assert result == "value"
    
    def test_string_validation(self, validator):
        """Test string type validation"""
        rules = [ValidationRule(type=ValidationType.STRING)]
        
        # Should convert non-string to string
        result = validator.validate_field(123, rules, "test_field")
        assert result == "123"
        
        # Should pass for string
        result = validator.validate_field("test", rules, "test_field")
        assert result == "test"
    
    def test_integer_validation(self, validator):
        """Test integer validation"""
        rules = [ValidationRule(type=ValidationType.INTEGER)]
        
        # Should convert string to int
        result = validator.validate_field("42", rules, "test_field")
        assert result == 42
        
        # Should raise for invalid integer
        with pytest.raises(ValidationError, match="must be an integer"):
            validator.validate_field("not_a_number", rules, "test_field")
    
    def test_float_validation(self, validator):
        """Test float validation"""
        rules = [ValidationRule(type=ValidationType.FLOAT)]
        
        # Should convert string to float
        result = validator.validate_field("3.14", rules, "test_field")
        assert result == 3.14
        
        # Should convert int to float
        result = validator.validate_field(42, rules, "test_field")
        assert result == 42.0
    
    def test_boolean_validation(self, validator):
        """Test boolean validation"""
        rules = [ValidationRule(type=ValidationType.BOOLEAN)]
        
        # Test various true values
        for value in [True, "true", "True", "1", "yes", "on"]:
            result = validator.validate_field(value, rules, "test_field")
            assert result is True
        
        # Test various false values
        for value in [False, "false", "False", "0", "no", "off"]:
            result = validator.validate_field(value, rules, "test_field")
            assert result is False
        
        # Should raise for invalid boolean
        with pytest.raises(ValidationError, match="must be a boolean"):
            validator.validate_field("maybe", rules, "test_field")
    
    def test_datetime_validation(self, validator):
        """Test datetime validation"""
        rules = [ValidationRule(type=ValidationType.DATETIME)]
        
        # Should pass datetime object
        now = datetime.now()
        result = validator.validate_field(now, rules, "test_field")
        assert result == now
        
        # Should parse ISO format
        iso_string = "2024-01-01T12:00:00"
        result = validator.validate_field(iso_string, rules, "test_field")
        assert isinstance(result, datetime)
        
        # Should handle Z suffix
        iso_with_z = "2024-01-01T12:00:00Z"
        result = validator.validate_field(iso_with_z, rules, "test_field")
        assert isinstance(result, datetime)
    
    def test_json_validation(self, validator):
        """Test JSON validation"""
        rules = [ValidationRule(type=ValidationType.JSON)]
        
        # Should parse JSON string
        json_string = '{"key": "value"}'
        result = validator.validate_field(json_string, rules, "test_field")
        assert result == {"key": "value"}
        
        # Should pass through dict/list
        data = {"test": 123}
        result = validator.validate_field(data, rules, "test_field")
        assert result == data
        
        # Should raise for invalid JSON
        with pytest.raises(ValidationError, match="must be valid JSON"):
            validator.validate_field("{invalid json}", rules, "test_field")
    
    def test_enum_validation(self, validator):
        """Test enum validation"""
        rules = [ValidationRule(
            type=ValidationType.ENUM,
            enum_values=["pending", "processing", "completed"]
        )]
        
        # Should pass for valid enum
        result = validator.validate_field("pending", rules, "status")
        assert result == "pending"
        
        # Should raise for invalid enum
        with pytest.raises(ValidationError, match="must be one of"):
            validator.validate_field("invalid", rules, "status")
    
    def test_regex_validation(self, validator):
        """Test regex pattern validation"""
        rules = [ValidationRule(
            type=ValidationType.REGEX,
            pattern=r"^[A-Z][a-z]+$",
            error_message="Must start with capital letter"
        )]
        
        # Should pass for matching pattern
        result = validator.validate_field("Hello", rules, "name")
        assert result == "Hello"
        
        # Should raise for non-matching pattern
        with pytest.raises(ValidationError, match="Must start with capital"):
            validator.validate_field("hello", rules, "name")
    
    def test_length_validation(self, validator):
        """Test length validation"""
        rules = [ValidationRule(
            type=ValidationType.LENGTH,
            min_length=3,
            max_length=10
        )]
        
        # Should pass for valid length
        result = validator.validate_field("test", rules, "field")
        assert result == "test"
        
        # Should raise for too short
        with pytest.raises(ValidationError, match="at least 3"):
            validator.validate_field("ab", rules, "field")
        
        # Should raise for too long
        with pytest.raises(ValidationError, match="at most 10"):
            validator.validate_field("this is too long", rules, "field")
    
    def test_range_validation(self, validator):
        """Test numeric range validation"""
        rules = [ValidationRule(
            type=ValidationType.RANGE,
            min_value=1,
            max_value=10
        )]
        
        # Should pass for valid range
        result = validator.validate_field(5, rules, "level")
        assert result == 5
        
        # Should raise for too small
        with pytest.raises(ValidationError, match="at least 1"):
            validator.validate_field(0, rules, "level")
        
        # Should raise for too large
        with pytest.raises(ValidationError, match="at most 10"):
            validator.validate_field(11, rules, "level")
    
    def test_sql_safe_validation(self, validator):
        """Test SQL injection detection"""
        rules = [ValidationRule(type=ValidationType.SQL_SAFE)]
        
        # Should pass for safe strings
        safe_strings = [
            "normal text",
            "Korean 한글",
            "user@example.com",
            "path/to/file.txt"
        ]
        
        for safe in safe_strings:
            result = validator.validate_field(safe, rules, "field")
            assert result == safe
        
        # Should raise for SQL injection attempts
        unsafe_strings = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "UNION SELECT * FROM passwords",
            "1; DELETE FROM data"
        ]
        
        for unsafe in unsafe_strings:
            with pytest.raises(ValidationError, match="unsafe SQL"):
                validator.validate_field(unsafe, rules, "field")
    
    def test_html_safe_validation(self, validator):
        """Test XSS detection"""
        rules = [ValidationRule(type=ValidationType.HTML_SAFE)]
        
        # Should pass for safe strings
        safe_strings = [
            "normal text",
            "Hello World!",
            "user@example.com"
        ]
        
        for safe in safe_strings:
            result = validator.validate_field(safe, rules, "field")
            assert result == safe
        
        # Should raise for XSS attempts
        unsafe_strings = [
            "<script>alert('xss')</script>",
            "javascript:alert(1)",
            "<img src=x onerror=alert(1)>",
            "<iframe src='evil.com'></iframe>"
        ]
        
        for unsafe in unsafe_strings:
            with pytest.raises(ValidationError, match="unsafe HTML"):
                validator.validate_field(unsafe, rules, "field")
    
    def test_custom_validator(self, validator):
        """Test custom validation function"""
        def uppercase_validator(value, field_name):
            if isinstance(value, str):
                return value.upper()
            return value
        
        rules = [ValidationRule(
            type=ValidationType.STRING,
            custom_validator=uppercase_validator
        )]
        
        result = validator.validate_field("hello", rules, "field")
        assert result == "HELLO"
    
    def test_sanitize_string(self, validator):
        """Test string sanitization"""
        # Test whitespace stripping
        result = validator.sanitize_string("  hello  ", strip_whitespace=True)
        assert result == "hello"
        
        # Test unicode normalization
        result = validator.sanitize_string("café", normalize_unicode=True)
        assert len(result) == 4  # Normalized form
        
        # Test HTML escaping
        result = validator.sanitize_string("<script>alert()</script>", escape_html=True)
        assert result == "&lt;script&gt;alert()&lt;/script&gt;"
    
    def test_validate_vocabulary_item(self, validator):
        """Test vocabulary item validation"""
        # Valid item
        item = {
            "term": "안녕하세요",
            "meaning": "Hello",
            "position": 1
        }
        
        result = validator.validate_vocabulary_item(item)
        assert result["term"] == "안녕하세요"
        assert result["meaning"] == "Hello"
        assert result["position"] == 1
        
        # Missing required field
        with pytest.raises(ValidationError, match="required"):
            validator.validate_vocabulary_item({"meaning": "Hello"})
        
        # SQL injection in term
        with pytest.raises(ValidationError, match="unsafe SQL"):
            validator.validate_vocabulary_item({
                "term": "'; DROP TABLE vocabulary; --",
                "meaning": "Evil"
            })
        
        # XSS in meaning
        with pytest.raises(ValidationError, match="unsafe HTML"):
            validator.validate_vocabulary_item({
                "term": "test",
                "meaning": "<script>alert('xss')</script>"
            })


class TestValidationSchema:
    """Test validation schema creation"""
    
    def test_vocabulary_schema(self):
        """Test vocabulary table schema"""
        schema = create_validation_schema("vocabulary")
        
        # Check required fields
        field_names = [f.name for f in schema]
        assert "korean" in field_names
        assert "english" in field_names
        assert "difficulty_level" in field_names
        
        # Check korean field rules
        korean_field = next(f for f in schema if f.name == "korean")
        rule_types = [r.type for r in korean_field.rules]
        assert ValidationType.REQUIRED in rule_types
        assert ValidationType.STRING in rule_types
        assert ValidationType.LENGTH in rule_types
        assert ValidationType.SQL_SAFE in rule_types
    
    def test_processing_tasks_schema(self):
        """Test processing tasks schema"""
        schema = create_validation_schema("processing_tasks")
        
        field_names = [f.name for f in schema]
        assert "task_id" in field_names
        assert "priority" in field_names
        assert "status" in field_names
        
        # Check status enum
        status_field = next(f for f in schema if f.name == "status")
        enum_rule = next(r for r in status_field.rules if r.type == ValidationType.ENUM)
        assert "pending" in enum_rule.enum_values
        assert "completed" in enum_rule.enum_values
    
    def test_cache_entries_schema(self):
        """Test cache entries schema"""
        schema = create_validation_schema("cache_entries")
        
        field_names = [f.name for f in schema]
        assert "cache_key" in field_names
        assert "cache_value" in field_names
        assert "ttl_seconds" in field_names


class TestConstraintValidator:
    """Test constraint validation"""
    
    def test_get_constraint_message(self):
        """Test user-friendly constraint messages"""
        validator = ConstraintValidator(None)
        
        # Unique constraint
        error = Exception("UNIQUE constraint failed: vocabulary.korean")
        message = validator.get_constraint_message(error)
        assert "already exists" in message or "must be unique" in message
        
        # Foreign key constraint
        error = Exception("FOREIGN KEY constraint failed")
        message = validator.get_constraint_message(error)
        assert "does not exist" in message
        
        # Not null constraint
        error = Exception("NOT NULL constraint failed")
        message = validator.get_constraint_message(error)
        assert "required" in message
        
        # Generic constraint
        error = Exception("CHECK constraint failed")
        message = validator.get_constraint_message(error)
        assert "validation requirements" in message


class TestTransactionValidator:
    """Test transaction validation"""
    
    def test_savepoint_management(self):
        """Test savepoint creation and naming"""
        import sqlite3
        conn = sqlite3.connect(":memory:")
        
        tx_validator = TransactionValidator(conn)
        
        # Create savepoints
        sp1 = tx_validator.create_savepoint()
        assert sp1 == "sp_1"
        
        sp2 = tx_validator.create_savepoint()
        assert sp2 == "sp_2"
        
        # Counter should increment
        assert tx_validator.savepoint_counter == 2
        
        conn.close()