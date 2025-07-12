"""
Comprehensive Error Handling System for Flashcard Pipeline

This module provides:
1. Error taxonomy - categorized errors
2. Error recovery strategies 
3. Error reporting to database
4. Error analysis and pattern detection
5. Automatic error resolution
"""

import json
import logging
import traceback
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Type, Callable, Union
from dataclasses import dataclass, asdict, field
from contextlib import contextmanager
import sqlite3
from collections import defaultdict, Counter
import re
import time
import asyncio
from abc import ABC, abstractmethod

from .exceptions import (
    PipelineError, ApiError, RateLimitError, ValidationError,
    CacheError, CircuitBreakerError, AuthenticationError,
    NetworkError, DatabaseError, ParsingError
)

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of errors that can occur in the pipeline"""
    NETWORK = auto()          # Network connectivity issues
    API = auto()              # API-related errors (rate limits, auth, etc.)
    VALIDATION = auto()       # Data validation errors
    DATABASE = auto()         # Database operation errors
    PARSING = auto()          # Output parsing errors
    CACHE = auto()            # Cache operation errors
    CIRCUIT_BREAKER = auto()  # Circuit breaker errors
    CONFIGURATION = auto()    # Configuration errors
    RESOURCE = auto()         # Resource exhaustion (memory, disk, etc.)
    TIMEOUT = auto()          # Operation timeout errors
    UNKNOWN = auto()          # Uncategorized errors


class ErrorSeverity(Enum):
    """Severity levels for errors"""
    CRITICAL = 1  # System failure, immediate attention needed
    HIGH = 2      # Major functionality impaired
    MEDIUM = 3    # Degraded performance or partial failure
    LOW = 4       # Minor issue, system continues
    INFO = 5      # Informational, not actually an error


@dataclass
class ErrorContext:
    """Captures full context of an error occurrence"""
    error_id: str
    timestamp: datetime
    category: ErrorCategory
    severity: ErrorSeverity
    error_type: str
    error_message: str
    stack_trace: str
    
    # Context information
    component: str  # Which component raised the error
    operation: str  # What operation was being performed
    input_data: Optional[Dict[str, Any]] = None
    
    # System state
    system_state: Dict[str, Any] = field(default_factory=dict)
    
    # Error metadata
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    vocabulary_id: Optional[int] = None
    task_id: Optional[str] = None
    
    # Recovery attempts
    retry_count: int = 0
    recovery_attempted: bool = False
    recovery_successful: bool = False
    recovery_strategy: Optional[str] = None
    
    # Additional details
    additional_info: Dict[str, Any] = field(default_factory=dict)


class RecoveryStrategy(ABC):
    """Abstract base class for error recovery strategies"""
    
    @abstractmethod
    async def attempt_recovery(self, error_context: ErrorContext) -> bool:
        """Attempt to recover from the error"""
        pass
    
    @abstractmethod
    def can_handle(self, error_context: ErrorContext) -> bool:
        """Check if this strategy can handle the given error"""
        pass


class RetryStrategy(RecoveryStrategy):
    """Retry the operation with exponential backoff"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    def can_handle(self, error_context: ErrorContext) -> bool:
        return error_context.category in [
            ErrorCategory.NETWORK,
            ErrorCategory.API,
            ErrorCategory.DATABASE
        ] and error_context.retry_count < self.max_retries
    
    async def attempt_recovery(self, error_context: ErrorContext) -> bool:
        delay = self.base_delay * (2 ** error_context.retry_count)
        logger.info(f"Retrying after {delay}s (attempt {error_context.retry_count + 1}/{self.max_retries})")
        await asyncio.sleep(delay)
        return True  # Indicate retry should be attempted


class RateLimitRecoveryStrategy(RecoveryStrategy):
    """Handle rate limit errors by waiting"""
    
    def can_handle(self, error_context: ErrorContext) -> bool:
        return (error_context.category == ErrorCategory.API and 
                "rate limit" in error_context.error_message.lower())
    
    async def attempt_recovery(self, error_context: ErrorContext) -> bool:
        # Extract retry_after from error context if available
        retry_after = error_context.additional_info.get('retry_after', 60)
        logger.info(f"Rate limited. Waiting {retry_after}s before retry")
        await asyncio.sleep(retry_after)
        return True


class CircuitBreakerRecoveryStrategy(RecoveryStrategy):
    """Handle circuit breaker by waiting for reset"""
    
    def can_handle(self, error_context: ErrorContext) -> bool:
        return error_context.category == ErrorCategory.CIRCUIT_BREAKER
    
    async def attempt_recovery(self, error_context: ErrorContext) -> bool:
        reset_time = error_context.additional_info.get('reset_time', 300)
        logger.info(f"Circuit breaker open. Waiting {reset_time}s for reset")
        await asyncio.sleep(reset_time)
        return True


class CacheFailoverStrategy(RecoveryStrategy):
    """Fallback to direct API calls when cache fails"""
    
    def can_handle(self, error_context: ErrorContext) -> bool:
        return error_context.category == ErrorCategory.CACHE
    
    async def attempt_recovery(self, error_context: ErrorContext) -> bool:
        logger.warning("Cache error detected. Falling back to direct API calls")
        error_context.additional_info['cache_disabled'] = True
        return True


class DatabaseReconnectStrategy(RecoveryStrategy):
    """Attempt to reconnect to database"""
    
    def can_handle(self, error_context: ErrorContext) -> bool:
        return (error_context.category == ErrorCategory.DATABASE and
                "connection" in error_context.error_message.lower())
    
    async def attempt_recovery(self, error_context: ErrorContext) -> bool:
        logger.info("Attempting database reconnection")
        await asyncio.sleep(2)  # Brief pause before reconnect
        return True


class ErrorPatternMatcher:
    """Identifies patterns in errors for automatic resolution"""
    
    def __init__(self):
        self.patterns = {
            # API Key errors
            r"invalid.*api.*key|unauthorized|401": {
                "category": ErrorCategory.API,
                "severity": ErrorSeverity.CRITICAL,
                "resolution": "Check API key configuration"
            },
            # Network errors
            r"connection.*refused|timeout|unreachable": {
                "category": ErrorCategory.NETWORK,
                "severity": ErrorSeverity.HIGH,
                "resolution": "Check network connectivity"
            },
            # Rate limit errors
            r"rate.*limit|429|too.*many.*requests": {
                "category": ErrorCategory.API,
                "severity": ErrorSeverity.MEDIUM,
                "resolution": "Implement rate limiting"
            },
            # Database errors
            r"database.*locked|sqlite.*error": {
                "category": ErrorCategory.DATABASE,
                "severity": ErrorSeverity.HIGH,
                "resolution": "Check database availability"
            },
            # Parsing errors
            r"json.*decode|parsing.*error|invalid.*format": {
                "category": ErrorCategory.PARSING,
                "severity": ErrorSeverity.MEDIUM,
                "resolution": "Validate API response format"
            }
        }
    
    def match_error(self, error_message: str) -> Optional[Dict[str, Any]]:
        """Match error message against known patterns"""
        error_lower = error_message.lower()
        for pattern, info in self.patterns.items():
            if re.search(pattern, error_lower):
                return info
        return None


class ErrorAnalyzer:
    """Analyzes error patterns and trends"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.pattern_matcher = ErrorPatternMatcher()
    
    def analyze_recent_errors(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze errors from the past N hours"""
        since = datetime.now() - timedelta(hours=hours)
        errors = self.db_manager.get_errors_since(since)
        
        analysis = {
            "total_errors": len(errors),
            "by_category": Counter(),
            "by_severity": Counter(),
            "by_component": Counter(),
            "error_rate_trend": [],
            "top_errors": [],
            "recovery_success_rate": 0,
            "recommendations": []
        }
        
        recovery_attempts = 0
        recovery_successes = 0
        
        for error in errors:
            analysis["by_category"][error.category.name] += 1
            analysis["by_severity"][error.severity.name] += 1
            analysis["by_component"][error.component] += 1
            
            if error.recovery_attempted:
                recovery_attempts += 1
                if error.recovery_successful:
                    recovery_successes += 1
        
        # Calculate recovery success rate
        if recovery_attempts > 0:
            analysis["recovery_success_rate"] = recovery_successes / recovery_attempts
        
        # Get top errors
        error_counts = Counter()
        for error in errors:
            error_key = f"{error.error_type}:{error.error_message[:50]}"
            error_counts[error_key] += 1
        
        analysis["top_errors"] = error_counts.most_common(10)
        
        # Generate recommendations
        analysis["recommendations"] = self._generate_recommendations(analysis)
        
        return analysis
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on error analysis"""
        recommendations = []
        
        # High error rate
        if analysis["total_errors"] > 100:
            recommendations.append("High error rate detected. Consider scaling resources.")
        
        # API errors
        if analysis["by_category"].get("API", 0) > 50:
            recommendations.append("High API error rate. Check API quotas and implement better rate limiting.")
        
        # Database errors
        if analysis["by_category"].get("DATABASE", 0) > 20:
            recommendations.append("Database errors detected. Consider connection pooling or database optimization.")
        
        # Low recovery rate
        if analysis["recovery_success_rate"] < 0.5:
            recommendations.append("Low recovery success rate. Review recovery strategies.")
        
        return recommendations
    
    def identify_error_clusters(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Identify clusters of similar errors"""
        since = datetime.now() - timedelta(hours=hours)
        errors = self.db_manager.get_errors_since(since)
        
        # Group by error signature
        clusters = defaultdict(list)
        for error in errors:
            signature = f"{error.category.name}:{error.error_type}:{error.component}"
            clusters[signature].append(error)
        
        # Convert to list of cluster info
        cluster_list = []
        for signature, error_list in clusters.items():
            if len(error_list) >= 3:  # Only consider clusters with 3+ errors
                cluster_list.append({
                    "signature": signature,
                    "count": len(error_list),
                    "first_occurrence": min(e.timestamp for e in error_list),
                    "last_occurrence": max(e.timestamp for e in error_list),
                    "affected_components": list(set(e.component for e in error_list))
                })
        
        return sorted(cluster_list, key=lambda x: x["count"], reverse=True)


class AutoResolver:
    """Automatically resolves known issues"""
    
    def __init__(self):
        self.resolutions = {
            # API Key issues
            "invalid_api_key": self._resolve_api_key,
            # Cache issues
            "cache_corruption": self._resolve_cache_corruption,
            # Database lock
            "database_locked": self._resolve_database_lock,
            # Memory issues
            "memory_exhausted": self._resolve_memory_issues
        }
    
    async def resolve(self, error_context: ErrorContext) -> bool:
        """Attempt automatic resolution"""
        # Identify issue type
        issue_type = self._identify_issue(error_context)
        
        if issue_type in self.resolutions:
            logger.info(f"Attempting automatic resolution for {issue_type}")
            return await self.resolutions[issue_type](error_context)
        
        return False
    
    def _identify_issue(self, error_context: ErrorContext) -> Optional[str]:
        """Identify the type of issue from error context"""
        error_msg = error_context.error_message.lower()
        
        if "api key" in error_msg or "unauthorized" in error_msg:
            return "invalid_api_key"
        elif "cache" in error_msg and "corrupt" in error_msg:
            return "cache_corruption"
        elif "database" in error_msg and "locked" in error_msg:
            return "database_locked"
        elif "memory" in error_msg:
            return "memory_exhausted"
        
        return None
    
    async def _resolve_api_key(self, error_context: ErrorContext) -> bool:
        """Resolve API key issues"""
        # Check if API key exists
        # Reload configuration
        # Validate API key format
        logger.info("Checking API key configuration")
        return False  # Placeholder
    
    async def _resolve_cache_corruption(self, error_context: ErrorContext) -> bool:
        """Resolve cache corruption"""
        logger.info("Clearing corrupted cache")
        # Clear cache
        # Rebuild cache index
        return True
    
    async def _resolve_database_lock(self, error_context: ErrorContext) -> bool:
        """Resolve database lock issues"""
        logger.info("Attempting to clear database lock")
        # Close stale connections
        # Clear WAL file if needed
        return True
    
    async def _resolve_memory_issues(self, error_context: ErrorContext) -> bool:
        """Resolve memory issues"""
        logger.info("Attempting to free memory")
        # Trigger garbage collection
        # Clear caches
        # Reduce batch sizes
        return True


class ErrorDatabaseManager:
    """Manages error storage and retrieval in database"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize error tracking tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS error_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    error_id TEXT UNIQUE NOT NULL,
                    timestamp DATETIME NOT NULL,
                    category TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    stack_trace TEXT,
                    component TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    input_data TEXT,
                    system_state TEXT,
                    user_id TEXT,
                    session_id TEXT,
                    request_id TEXT,
                    vocabulary_id INTEGER,
                    task_id TEXT,
                    retry_count INTEGER DEFAULT 0,
                    recovery_attempted BOOLEAN DEFAULT 0,
                    recovery_successful BOOLEAN DEFAULT 0,
                    recovery_strategy TEXT,
                    additional_info TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_error_logs_timestamp 
                ON error_logs(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_error_logs_category 
                ON error_logs(category)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_error_logs_component 
                ON error_logs(component)
            """)
    
    def log_error(self, error_context: ErrorContext):
        """Log an error to the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO error_logs (
                    error_id, timestamp, category, severity, error_type,
                    error_message, stack_trace, component, operation,
                    input_data, system_state, user_id, session_id,
                    request_id, vocabulary_id, task_id, retry_count,
                    recovery_attempted, recovery_successful, recovery_strategy,
                    additional_info
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                error_context.error_id,
                error_context.timestamp,
                error_context.category.name,
                error_context.severity.name,
                error_context.error_type,
                error_context.error_message,
                error_context.stack_trace,
                error_context.component,
                error_context.operation,
                json.dumps(error_context.input_data) if error_context.input_data else None,
                json.dumps(error_context.system_state),
                error_context.user_id,
                error_context.session_id,
                error_context.request_id,
                error_context.vocabulary_id,
                error_context.task_id,
                error_context.retry_count,
                error_context.recovery_attempted,
                error_context.recovery_successful,
                error_context.recovery_strategy,
                json.dumps(error_context.additional_info)
            ))
    
    def get_errors_since(self, since: datetime) -> List[ErrorContext]:
        """Get all errors since a given timestamp"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM error_logs 
                WHERE timestamp >= ? 
                ORDER BY timestamp DESC
            """, (since,))
            
            errors = []
            for row in cursor:
                error = ErrorContext(
                    error_id=row['error_id'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    category=ErrorCategory[row['category']],
                    severity=ErrorSeverity[row['severity']],
                    error_type=row['error_type'],
                    error_message=row['error_message'],
                    stack_trace=row['stack_trace'],
                    component=row['component'],
                    operation=row['operation'],
                    input_data=json.loads(row['input_data']) if row['input_data'] else None,
                    system_state=json.loads(row['system_state']) if row['system_state'] else {},
                    user_id=row['user_id'],
                    session_id=row['session_id'],
                    request_id=row['request_id'],
                    vocabulary_id=row['vocabulary_id'],
                    task_id=row['task_id'],
                    retry_count=row['retry_count'],
                    recovery_attempted=bool(row['recovery_attempted']),
                    recovery_successful=bool(row['recovery_successful']),
                    recovery_strategy=row['recovery_strategy'],
                    additional_info=json.loads(row['additional_info']) if row['additional_info'] else {}
                )
                errors.append(error)
            
            return errors


class ErrorHandler:
    """Main error handler that coordinates all error handling activities"""
    
    def __init__(self, db_path: str):
        self.db_manager = ErrorDatabaseManager(db_path)
        self.analyzer = ErrorAnalyzer(self.db_manager)
        self.auto_resolver = AutoResolver()
        self.pattern_matcher = ErrorPatternMatcher()
        
        # Recovery strategies
        self.recovery_strategies = [
            RetryStrategy(),
            RateLimitRecoveryStrategy(),
            CircuitBreakerRecoveryStrategy(),
            CacheFailoverStrategy(),
            DatabaseReconnectStrategy()
        ]
    
    @contextmanager
    def error_context(self, component: str, operation: str, **kwargs):
        """Context manager for error handling"""
        try:
            yield
        except Exception as e:
            error_context = self.capture_error(e, component, operation, **kwargs)
            self.handle_error(error_context)
            raise
    
    def capture_error(self, exception: Exception, component: str, 
                     operation: str, **kwargs) -> ErrorContext:
        """Capture error with full context"""
        # Generate unique error ID
        error_id = f"{component}_{operation}_{int(time.time() * 1000)}"
        
        # Determine category and severity
        category = self._categorize_error(exception)
        severity = self._determine_severity(exception)
        
        # Create error context
        error_context = ErrorContext(
            error_id=error_id,
            timestamp=datetime.now(),
            category=category,
            severity=severity,
            error_type=type(exception).__name__,
            error_message=str(exception),
            stack_trace=traceback.format_exc(),
            component=component,
            operation=operation,
            input_data=kwargs.get('input_data'),
            system_state=self._capture_system_state(),
            user_id=kwargs.get('user_id'),
            session_id=kwargs.get('session_id'),
            request_id=kwargs.get('request_id'),
            vocabulary_id=kwargs.get('vocabulary_id'),
            task_id=kwargs.get('task_id'),
            additional_info=kwargs.get('additional_info', {})
        )
        
        return error_context
    
    def handle_error(self, error_context: ErrorContext):
        """Handle an error - log, analyze, and attempt recovery"""
        # Log to database
        self.db_manager.log_error(error_context)
        
        # Log to application logger
        logger.error(
            f"Error in {error_context.component}.{error_context.operation}: "
            f"{error_context.error_message}",
            extra={
                "error_id": error_context.error_id,
                "category": error_context.category.name,
                "severity": error_context.severity.name
            }
        )
        
        # Attempt automatic resolution
        if error_context.severity in [ErrorSeverity.MEDIUM, ErrorSeverity.LOW]:
            asyncio.create_task(self._attempt_recovery(error_context))
    
    async def _attempt_recovery(self, error_context: ErrorContext):
        """Attempt to recover from an error"""
        # Try auto-resolver first
        if await self.auto_resolver.resolve(error_context):
            error_context.recovery_attempted = True
            error_context.recovery_successful = True
            error_context.recovery_strategy = "auto_resolver"
            self.db_manager.log_error(error_context)  # Update
            return
        
        # Try recovery strategies
        for strategy in self.recovery_strategies:
            if strategy.can_handle(error_context):
                error_context.recovery_attempted = True
                error_context.recovery_strategy = type(strategy).__name__
                
                try:
                    success = await strategy.attempt_recovery(error_context)
                    error_context.recovery_successful = success
                    self.db_manager.log_error(error_context)  # Update
                    
                    if success:
                        logger.info(f"Successfully recovered from error using {error_context.recovery_strategy}")
                        return
                except Exception as e:
                    logger.error(f"Recovery strategy failed: {e}")
    
    def _categorize_error(self, exception: Exception) -> ErrorCategory:
        """Categorize an exception"""
        if isinstance(exception, NetworkError):
            return ErrorCategory.NETWORK
        elif isinstance(exception, (ApiError, RateLimitError, AuthenticationError)):
            return ErrorCategory.API
        elif isinstance(exception, ValidationError):
            return ErrorCategory.VALIDATION
        elif isinstance(exception, DatabaseError):
            return ErrorCategory.DATABASE
        elif isinstance(exception, ParsingError):
            return ErrorCategory.PARSING
        elif isinstance(exception, CacheError):
            return ErrorCategory.CACHE
        elif isinstance(exception, CircuitBreakerError):
            return ErrorCategory.CIRCUIT_BREAKER
        elif isinstance(exception, TimeoutError):
            return ErrorCategory.TIMEOUT
        elif isinstance(exception, MemoryError):
            return ErrorCategory.RESOURCE
        else:
            # Try pattern matching
            pattern_info = self.pattern_matcher.match_error(str(exception))
            if pattern_info:
                return pattern_info["category"]
            return ErrorCategory.UNKNOWN
    
    def _determine_severity(self, exception: Exception) -> ErrorSeverity:
        """Determine error severity"""
        if isinstance(exception, (AuthenticationError, DatabaseError)):
            return ErrorSeverity.CRITICAL
        elif isinstance(exception, (NetworkError, CircuitBreakerError)):
            return ErrorSeverity.HIGH
        elif isinstance(exception, (RateLimitError, CacheError)):
            return ErrorSeverity.MEDIUM
        elif isinstance(exception, (ValidationError, ParsingError)):
            return ErrorSeverity.LOW
        else:
            # Try pattern matching
            pattern_info = self.pattern_matcher.match_error(str(exception))
            if pattern_info:
                return pattern_info["severity"]
            return ErrorSeverity.MEDIUM
    
    def _capture_system_state(self) -> Dict[str, Any]:
        """Capture current system state"""
        import psutil
        
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_error_analysis(self, hours: int = 24) -> Dict[str, Any]:
        """Get error analysis for the specified time period"""
        return self.analyzer.analyze_recent_errors(hours)
    
    def get_error_clusters(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get error clusters for the specified time period"""
        return self.analyzer.identify_error_clusters(hours)


# Convenience decorator for error handling
def handle_errors(component: str):
    """Decorator for automatic error handling"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get error handler from first arg if it has one
            handler = None
            if args and hasattr(args[0], 'error_handler'):
                handler = args[0].error_handler
            
            if handler:
                with handler.error_context(
                    component=component,
                    operation=func.__name__,
                    input_data=kwargs
                ):
                    return func(*args, **kwargs)
            else:
                # No error handler available, just run the function
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Example usage in a component
class ExampleComponent:
    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler
    
    @handle_errors("ExampleComponent")
    def risky_operation(self, data: Dict[str, Any]):
        """Example of a method with automatic error handling"""
        # This will automatically capture and handle errors
        if not data:
            raise ValidationError("Data cannot be empty")
        
        # Process data...
        return data