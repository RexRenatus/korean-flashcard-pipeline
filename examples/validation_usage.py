#!/usr/bin/env python3
"""
Example usage of the data validation layer.
Demonstrates input validation, sanitization, and constraint checking.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flashcard_pipeline.database import (
    EnhancedDatabaseManager,
    ValidatedDatabaseManager,
    PoolConfig,
    ValidationRule,
    ValidationType
)
from flashcard_pipeline.exceptions import ValidationError


def example_basic_validation():
    """Basic validation example"""
    print("\n=== Basic Validation Example ===")
    
    # Create database manager
    db_manager = EnhancedDatabaseManager(
        db_path="pipeline.db",
        pool_config=PoolConfig(min_connections=1, max_connections=3)
    )
    
    # Wrap with validation
    validated_db = ValidatedDatabaseManager(db_manager)
    
    try:
        # Valid vocabulary item
        print("\n1. Creating valid vocabulary item...")
        vocab_id = validated_db.create_vocabulary_validated({
            "term": "안녕하세요",
            "meaning": "Hello (formal)",
            "romanization": "annyeonghaseyo",
            "type": "greeting",
            "difficulty_level": 1
        })
        print(f"✅ Created vocabulary item with ID: {vocab_id}")
        
        # Invalid: Missing required field
        print("\n2. Testing missing required field...")
        try:
            validated_db.create_vocabulary_validated({
                "meaning": "Test"  # Missing 'term'
            })
        except ValidationError as e:
            print(f"❌ Validation failed (expected): {e}")
        
        # Invalid: SQL injection attempt
        print("\n3. Testing SQL injection prevention...")
        try:
            validated_db.create_vocabulary_validated({
                "term": "'; DROP TABLE vocabulary; --",
                "meaning": "Evil attempt"
            })
        except ValidationError as e:
            print(f"❌ Validation failed (expected): {e}")
        
        # Invalid: XSS attempt
        print("\n4. Testing XSS prevention...")
        try:
            validated_db.create_vocabulary_validated({
                "term": "test",
                "meaning": "<script>alert('xss')</script>"
            })
        except ValidationError as e:
            print(f"❌ Validation failed (expected): {e}")
        
        # Invalid: Duplicate entry
        print("\n5. Testing duplicate prevention...")
        try:
            validated_db.create_vocabulary_validated({
                "term": "안녕하세요",  # Already exists
                "meaning": "Another hello"
            })
        except ValidationError as e:
            print(f"❌ Validation failed (expected): {e}")
        
        # Invalid: Out of range value
        print("\n6. Testing range validation...")
        try:
            validated_db.create_vocabulary_validated({
                "term": "어려운단어",
                "meaning": "Difficult word",
                "difficulty_level": 15  # Max is 10
            })
        except ValidationError as e:
            print(f"❌ Validation failed (expected): {e}")
        
    finally:
        db_manager.close()


def example_custom_validation():
    """Custom validation rules example"""
    print("\n\n=== Custom Validation Example ===")
    
    db_manager = EnhancedDatabaseManager(
        db_path="pipeline.db",
        pool_config=PoolConfig(min_connections=1, max_connections=3)
    )
    
    validated_db = ValidatedDatabaseManager(db_manager)
    
    # Register custom validator
    def korean_script_validator(value, field_name):
        """Ensure value contains Korean characters"""
        if isinstance(value, str) and not any('\uAC00' <= c <= '\uD7AF' for c in value):
            raise ValidationError(f"{field_name} must contain Korean characters")
        return value
    
    validated_db.register_custom_validator("vocabulary", "korean", korean_script_validator)
    
    try:
        # This should fail - no Korean characters
        print("\n1. Testing custom Korean validator...")
        try:
            validated_db.create_vocabulary_validated({
                "term": "hello",  # Not Korean
                "meaning": "Hello"
            })
        except ValidationError as e:
            print(f"❌ Custom validation failed (expected): {e}")
        
    finally:
        db_manager.close()


def example_task_validation():
    """Task creation validation example"""
    print("\n\n=== Task Validation Example ===")
    
    db_manager = EnhancedDatabaseManager(
        db_path="pipeline.db",
        pool_config=PoolConfig(min_connections=1, max_connections=3)
    )
    
    validated_db = ValidatedDatabaseManager(db_manager)
    
    try:
        # Valid task
        print("\n1. Creating valid task...")
        task_id = validated_db.create_task_validated(
            vocabulary_id=1,  # Assuming this exists
            task_type="full_pipeline",
            priority=5
        )
        print(f"✅ Created task with ID: {task_id}")
        
        # Invalid: Bad vocabulary ID
        print("\n2. Testing foreign key validation...")
        try:
            validated_db.create_task_validated(
                vocabulary_id=99999,  # Doesn't exist
                task_type="full_pipeline"
            )
        except ValidationError as e:
            print(f"❌ Validation failed (expected): {e}")
        
        # Invalid: Bad task type
        print("\n3. Testing enum validation...")
        try:
            validated_db.create_task_validated(
                vocabulary_id=1,
                task_type="invalid_type"
            )
        except ValidationError as e:
            print(f"❌ Validation failed (expected): {e}")
        
        # Invalid: Bad priority
        print("\n4. Testing range validation...")
        try:
            validated_db.create_task_validated(
                vocabulary_id=1,
                priority=20  # Max is 10
            )
        except ValidationError as e:
            print(f"❌ Validation failed (expected): {e}")
        
    finally:
        db_manager.close()


def example_cache_validation():
    """Cache entry validation example"""
    print("\n\n=== Cache Validation Example ===")
    
    db_manager = EnhancedDatabaseManager(
        db_path="pipeline.db",
        pool_config=PoolConfig(min_connections=1, max_connections=3)
    )
    
    validated_db = ValidatedDatabaseManager(db_manager)
    
    try:
        # Valid cache entry
        print("\n1. Creating valid cache entry...")
        validated_db.save_cache_entry_validated(
            cache_key="api_response_12345",
            cache_value={"result": "test data"},
            cache_type="api_response",
            ttl_seconds=3600
        )
        print("✅ Cache entry saved successfully")
        
        # Invalid: SQL injection in cache key
        print("\n2. Testing cache key validation...")
        try:
            validated_db.save_cache_entry_validated(
                cache_key="key'; DELETE FROM cache; --",
                cache_value="data"
            )
        except ValidationError as e:
            print(f"❌ Validation failed (expected): {e}")
        
        # Invalid: Bad cache type
        print("\n3. Testing cache type validation...")
        try:
            validated_db.save_cache_entry_validated(
                cache_key="test_key",
                cache_value="data",
                cache_type="invalid_type"
            )
        except ValidationError as e:
            print(f"❌ Validation failed (expected): {e}")
        
        # Invalid: TTL too long
        print("\n4. Testing TTL validation...")
        try:
            validated_db.save_cache_entry_validated(
                cache_key="test_key",
                cache_value="data",
                ttl_seconds=86400 * 365  # 1 year - too long
            )
        except ValidationError as e:
            print(f"❌ Validation failed (expected): {e}")
        
    finally:
        db_manager.close()


def example_bulk_validation():
    """Bulk insert validation example"""
    print("\n\n=== Bulk Insert Validation Example ===")
    
    db_manager = EnhancedDatabaseManager(
        db_path="pipeline.db",
        pool_config=PoolConfig(min_connections=1, max_connections=3)
    )
    
    validated_db = ValidatedDatabaseManager(db_manager)
    
    try:
        # Prepare bulk data
        records = [
            {
                "korean": "안녕",
                "english": "Hi (informal)",
                "difficulty_level": 1
            },
            {
                "korean": "감사합니다",
                "english": "Thank you",
                "difficulty_level": 1
            },
            {
                "korean": "미안합니다",
                "english": "I'm sorry",
                "difficulty_level": 2
            }
        ]
        
        print("\n1. Bulk inserting valid records...")
        count = validated_db.bulk_insert_validated("vocabulary", records)
        print(f"✅ Successfully inserted {count} records")
        
        # Invalid bulk data
        bad_records = [
            {
                "korean": "좋아요",
                "english": "Good/Like",
                "difficulty_level": 1
            },
            {
                # Missing required field
                "english": "Test"
            },
            {
                "korean": "나쁘다",
                "english": "Bad",
                "difficulty_level": 15  # Out of range
            }
        ]
        
        print("\n2. Testing bulk validation with errors...")
        try:
            validated_db.bulk_insert_validated("vocabulary", bad_records)
        except ValidationError as e:
            print(f"❌ Bulk validation failed (expected): {e}")
        
    finally:
        db_manager.close()


def example_transaction_validation():
    """Transaction with validation example"""
    print("\n\n=== Transaction Validation Example ===")
    
    db_manager = EnhancedDatabaseManager(
        db_path="pipeline.db",
        pool_config=PoolConfig(min_connections=1, max_connections=3)
    )
    
    validated_db = ValidatedDatabaseManager(db_manager)
    
    try:
        print("\n1. Testing transaction with validation...")
        
        # This will rollback on validation error
        with validated_db.validated_transaction() as (conn, constraint_validator):
            # Insert valid data
            conn.execute(
                "INSERT INTO vocabulary (korean, english) VALUES (?, ?)",
                ("테스트", "Test")
            )
            print("✅ First insert successful")
            
            # This will cause rollback
            try:
                # Simulate constraint violation
                conn.execute(
                    "INSERT INTO vocabulary (korean, english) VALUES (?, ?)",
                    ("테스트", "Duplicate Test")  # Duplicate korean
                )
            except Exception as e:
                print(f"❌ Constraint violation detected: {e}")
                raise ValidationError(constraint_validator.get_constraint_message(e))
        
    except ValidationError as e:
        print(f"❌ Transaction rolled back: {e}")
    
    finally:
        db_manager.close()


def main():
    """Run all validation examples"""
    print("Data Validation Layer Examples")
    print("=" * 50)
    
    examples = [
        ("Basic Validation", example_basic_validation),
        ("Custom Validation", example_custom_validation),
        ("Task Validation", example_task_validation),
        ("Cache Validation", example_cache_validation),
        ("Bulk Validation", example_bulk_validation),
        ("Transaction Validation", example_transaction_validation)
    ]
    
    for name, func in examples:
        try:
            func()
        except Exception as e:
            print(f"\n⚠️ Example '{name}' encountered an error: {e}")
    
    print("\n\n✅ All validation examples completed!")
    print("\nKey takeaways:")
    print("- All inputs are validated before database operations")
    print("- SQL injection and XSS attempts are blocked")
    print("- Constraints are checked with user-friendly messages")
    print("- Transactions rollback automatically on validation errors")
    print("- Custom validators can be registered for specific needs")


if __name__ == "__main__":
    main()