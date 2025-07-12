"""Database package for flashcard pipeline"""

# Import from consolidated managers
from .database_manager import (
    DatabaseManager,
    VocabularyRecord,
    ProcessingTask,
    FlashcardRecord,
)

from .async_database_manager import (
    AsyncDatabaseManager,
)

# Legacy imports for backward compatibility
LegacyDatabaseManager = DatabaseManager
EnhancedDatabaseManager = DatabaseManager
ValidatedDatabaseManager = DatabaseManager

# Import supporting components
from .connection_pool import (
    ConnectionPool,
    PoolConfig,
    RetryableDatabase
)

from .performance_monitor import (
    PerformanceMonitor,
    PerformanceThresholds,
    DatabaseHealthChecker
)

from .validation import (
    DataValidator,
    ValidationRule,
    ValidationType,
    FieldValidation,
    ConstraintValidator,
    TransactionValidator,
    create_validation_schema,
    ValidationError,
    Validator
)

from .backup_manager import (
    BackupManager
)

__all__ = [
    # Original components
    'DatabaseManager',
    'VocabularyRecord',
    'ProcessingTask',
    'FlashcardRecord',
    
    # Enhanced components
    'EnhancedDatabaseManager',
    'AsyncDatabaseManager',
    
    # Connection pooling
    'ConnectionPool',
    'PoolConfig',
    'RetryableDatabase',
    
    # Performance monitoring
    'PerformanceMonitor',
    'PerformanceThresholds',
    'DatabaseHealthChecker',
    
    # Validation components
    'DataValidator',
    'ValidationRule',
    'ValidationType',
    'FieldValidation',
    'ConstraintValidator',
    'TransactionValidator',
    'create_validation_schema',
    
    # Validated database manager
    'ValidatedDatabaseManager',
    
    # Backup management
    'BackupManager'
]