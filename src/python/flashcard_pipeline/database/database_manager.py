"""
Unified Database Manager combining features from all database implementations.
Provides core CRUD operations, connection pooling, performance monitoring, and optional validation.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Tuple, ContextManager
from datetime import datetime
from contextlib import contextmanager
import time
import json
from dataclasses import dataclass, asdict

from .connection_pool import ConnectionPool
from .performance_monitor import PerformanceMonitor
from .validation import ValidationRule, ValidationError, Validator

logger = logging.getLogger(__name__)


@dataclass
class VocabularyRecord:
    """Represents a vocabulary item in the database"""
    id: Optional[int] = None
    term: Optional[str] = None
    pronunciation: Optional[str] = None
    definition: Optional[str] = None
    difficulty: Optional[str] = None
    tags: Optional[str] = None
    example_sentence: Optional[str] = None
    cultural_note: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class ProcessingTask:
    """Represents a processing task in the database"""
    id: Optional[int] = None
    vocabulary_id: Optional[int] = None
    task_id: Optional[str] = None
    stage: Optional[int] = None
    status: Optional[str] = None
    priority: int = 5
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class FlashcardRecord:
    """Represents a flashcard in the database"""
    id: Optional[int] = None
    vocabulary_id: Optional[int] = None
    task_id: Optional[int] = None
    card_number: Optional[int] = None
    deck_name: Optional[str] = None
    front_content: Optional[str] = None
    back_content: Optional[str] = None
    pronunciation_guide: Optional[str] = None
    tags: Optional[str] = None
    honorific_level: Optional[str] = None
    position: Optional[int] = None
    primer: Optional[str] = None
    tab_name: Optional[str] = None
    is_published: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DatabaseManager:
    """
    Unified database manager with all features:
    - Core CRUD operations
    - Connection pooling (optional)
    - Performance monitoring (optional)
    - Input validation (optional)
    """
    
    def __init__(
        self,
        db_path: Union[str, Path] = "flashcard_pipeline.db",
        use_connection_pool: bool = True,
        pool_size: int = 5,
        enable_monitoring: bool = True,
        enable_validation: bool = False,
        validation_rules: Optional[List[ValidationRule]] = None
    ):
        """
        Initialize database manager with optional features.
        
        Args:
            db_path: Path to SQLite database
            use_connection_pool: Enable connection pooling
            pool_size: Size of connection pool
            enable_monitoring: Enable performance monitoring
            enable_validation: Enable input validation
            validation_rules: Custom validation rules
        """
        self.db_path = Path(db_path)
        self.enable_validation = enable_validation
        
        # Initialize connection pool if enabled
        if use_connection_pool:
            self.connection_pool = ConnectionPool(
                db_path=str(self.db_path),
                pool_size=pool_size
            )
        else:
            self.connection_pool = None
        
        # Initialize performance monitor if enabled
        if enable_monitoring:
            self.monitor = PerformanceMonitor()
        else:
            self.monitor = None
        
        # Initialize validator if enabled
        if enable_validation:
            self.validator = Validator(custom_rules=validation_rules)
        else:
            self.validator = None
        
        # Ensure database exists and has schema
        self._ensure_database()
    
    def _ensure_database(self):
        """Ensure database exists with proper schema"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with self.get_connection() as conn:
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Create tables if they don't exist
            # (Schema creation code would go here - omitted for brevity)
            logger.info(f"Database initialized at {self.db_path}")
    
    @contextmanager
    def get_connection(self) -> ContextManager[sqlite3.Connection]:
        """
        Get a database connection from pool or create new one.
        
        Yields:
            Database connection
        """
        start_time = time.time()
        
        try:
            if self.connection_pool:
                # Use connection from pool
                conn = self.connection_pool.get_connection()
                try:
                    yield conn
                finally:
                    self.connection_pool.return_connection(conn)
            else:
                # Create direct connection
                conn = sqlite3.connect(str(self.db_path))
                conn.row_factory = sqlite3.Row
                try:
                    yield conn
                finally:
                    conn.close()
        finally:
            # Record performance metrics
            if self.monitor:
                elapsed = time.time() - start_time
                self.monitor.record_operation('get_connection', elapsed)
    
    @contextmanager
    def transaction(self) -> ContextManager[sqlite3.Connection]:
        """
        Execute operations in a transaction.
        
        Yields:
            Database connection in transaction
        """
        with self.get_connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    
    def _validate_input(self, data: Dict[str, Any], entity_type: str):
        """Validate input data if validation is enabled"""
        if self.validator and self.enable_validation:
            validation_result = self.validator.validate(data, entity_type)
            if not validation_result.is_valid:
                raise ValidationError(f"Validation failed: {validation_result.errors}")
    
    def insert_vocabulary(
        self,
        term: str,
        pronunciation: Optional[str] = None,
        definition: Optional[str] = None,
        difficulty: Optional[str] = None,
        tags: Optional[str] = None,
        example_sentence: Optional[str] = None,
        cultural_note: Optional[str] = None
    ) -> int:
        """
        Insert a new vocabulary item.
        
        Args:
            term: Korean term
            pronunciation: Romanization
            definition: English definition
            difficulty: Difficulty level
            tags: Comma-separated tags
            example_sentence: Example usage
            cultural_note: Cultural context
            
        Returns:
            ID of inserted vocabulary item
        """
        # Validate input if enabled
        if self.enable_validation:
            self._validate_input({
                'term': term,
                'pronunciation': pronunciation,
                'definition': definition,
                'difficulty': difficulty,
                'tags': tags
            }, 'vocabulary')
        
        with self.transaction() as conn:
            cursor = conn.execute("""
                INSERT INTO vocabulary (
                    term, pronunciation, definition, difficulty,
                    tags, example_sentence, cultural_note, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                term, pronunciation, definition, difficulty,
                tags, example_sentence, cultural_note
            ))
            
            vocabulary_id = cursor.lastrowid
            
            # Record metrics
            if self.monitor:
                self.monitor.record_operation('insert_vocabulary', 0)
            
            logger.info(f"Inserted vocabulary: {term} (ID: {vocabulary_id})")
            return vocabulary_id
    
    def get_vocabulary(self, vocabulary_id: int) -> Optional[VocabularyRecord]:
        """Get a vocabulary record by ID"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM vocabulary WHERE id = ?",
                (vocabulary_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return VocabularyRecord(**dict(row))
            return None
    
    def get_pending_tasks(
        self,
        stage: Optional[int] = None,
        limit: int = 10
    ) -> List[ProcessingTask]:
        """
        Get pending processing tasks.
        
        Args:
            stage: Filter by stage (1 or 2)
            limit: Maximum number of tasks
            
        Returns:
            List of pending tasks
        """
        with self.get_connection() as conn:
            query = """
                SELECT * FROM processing_tasks
                WHERE status = 'pending'
                AND retry_count < max_retries
            """
            params = []
            
            if stage is not None:
                query += " AND stage = ?"
                params.append(stage)
            
            query += " ORDER BY priority DESC, created_at ASC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            tasks = []
            
            for row in cursor:
                tasks.append(ProcessingTask(**dict(row)))
            
            # Record metrics
            if self.monitor:
                self.monitor.record_operation('get_pending_tasks', 0)
            
            return tasks
    
    def update_task_status(
        self,
        task_id: int,
        status: str,
        error_message: Optional[str] = None
    ):
        """Update task status"""
        with self.transaction() as conn:
            if status == 'failed':
                conn.execute("""
                    UPDATE processing_tasks
                    SET status = ?, error_message = ?, retry_count = retry_count + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, error_message, task_id))
            elif status == 'completed':
                conn.execute("""
                    UPDATE processing_tasks
                    SET status = ?, completed_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, task_id))
            else:
                conn.execute("""
                    UPDATE processing_tasks
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, task_id))
    
    def get_flashcards(
        self,
        vocabulary_id: Optional[int] = None,
        limit: int = 100
    ) -> List[FlashcardRecord]:
        """Get flashcards, optionally filtered by vocabulary ID"""
        with self.get_connection() as conn:
            if vocabulary_id:
                cursor = conn.execute(
                    "SELECT * FROM flashcards WHERE vocabulary_id = ? ORDER BY position",
                    (vocabulary_id,)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM flashcards ORDER BY vocabulary_id, position LIMIT ?",
                    (limit,)
                )
            
            flashcards = []
            for row in cursor:
                flashcards.append(FlashcardRecord(**dict(row)))
            
            return flashcards
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on database.
        
        Returns:
            Health status dictionary
        """
        health = {
            'status': 'healthy',
            'database': str(self.db_path),
            'checks': {}
        }
        
        try:
            # Check connection
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT 1")
                cursor.fetchone()
                health['checks']['connection'] = 'ok'
            
            # Check tables exist
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name IN ('vocabulary', 'processing_tasks', 'flashcards')
                """)
                tables = [row['name'] for row in cursor]
                health['checks']['tables'] = len(tables) == 3
            
            # Get statistics
            with self.get_connection() as conn:
                stats = {}
                for table in ['vocabulary', 'processing_tasks', 'flashcards']:
                    cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")
                    stats[table] = cursor.fetchone()['count']
                health['statistics'] = stats
            
            # Add connection pool stats if available
            if self.connection_pool:
                health['connection_pool'] = self.connection_pool.get_stats()
            
            # Add performance metrics if available
            if self.monitor:
                health['performance'] = self.monitor.get_summary()
            
        except Exception as e:
            health['status'] = 'unhealthy'
            health['error'] = str(e)
            logger.error(f"Health check failed: {e}")
        
        return health
    
    def close(self):
        """Close database connections and cleanup resources"""
        if self.connection_pool:
            self.connection_pool.close()
        
        if self.monitor:
            # Save any final metrics
            summary = self.monitor.get_summary()
            logger.info(f"Performance summary: {summary}")


# Factory function for backward compatibility
def create_database_manager(
    db_path: Union[str, Path] = "flashcard_pipeline.db",
    enhanced: bool = False,
    validated: bool = False,
    **kwargs
) -> DatabaseManager:
    """
    Factory function to create database manager with specific features.
    
    Args:
        db_path: Database path
        enhanced: Enable enhanced features (pooling, monitoring)
        validated: Enable validation
        **kwargs: Additional configuration
        
    Returns:
        Configured DatabaseManager instance
    """
    return DatabaseManager(
        db_path=db_path,
        use_connection_pool=enhanced or kwargs.get('use_connection_pool', True),
        enable_monitoring=enhanced or kwargs.get('enable_monitoring', True),
        enable_validation=validated or kwargs.get('enable_validation', False),
        **{k: v for k, v in kwargs.items() if k not in ['use_connection_pool', 'enable_monitoring', 'enable_validation']}
    )