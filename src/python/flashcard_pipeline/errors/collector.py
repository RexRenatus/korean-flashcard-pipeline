"""Error collection and correlation system"""

import time
import json
import asyncio
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from datetime import datetime, timedelta
import logging

from .base import FlashcardError, ErrorMetadata, ErrorCategory, ErrorSeverity
from ..telemetry import get_trace_id, get_span_id, create_span, record_metric, add_event
from ..database.database_manager_v2 import DatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class ErrorRecord:
    """Record of a collected error"""
    error_id: str
    fingerprint: str
    timestamp: float
    metadata: ErrorMetadata
    
    # Correlation
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_error_id: Optional[str] = None
    
    # Processing
    processed: bool = False
    retry_count: int = 0
    recovery_attempted: bool = False
    recovery_successful: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data["metadata"] = self.metadata.to_dict()
        return data
    
    @classmethod
    def from_error(cls, error: FlashcardError) -> "ErrorRecord":
        """Create record from FlashcardError"""
        return cls(
            error_id=error.metadata.error_id,
            fingerprint=error.metadata.fingerprint,
            timestamp=error.metadata.timestamp,
            metadata=error.metadata,
            trace_id=error.metadata.trace_id,
            span_id=error.metadata.span_id,
            parent_error_id=error.metadata.extra.get("parent_error_id")
        )


class ErrorCollector:
    """Collects and manages errors across the application"""
    
    def __init__(
        self,
        max_buffer_size: int = 10000,
        flush_interval: float = 60.0,
        database: Optional[DatabaseManager] = None,
        enable_persistence: bool = True
    ):
        self.max_buffer_size = max_buffer_size
        self.flush_interval = flush_interval
        self.database = database
        self.enable_persistence = enable_persistence
        
        # In-memory buffers
        self._error_buffer: deque = deque(maxlen=max_buffer_size)
        self._error_index: Dict[str, ErrorRecord] = {}  # By error_id
        self._fingerprint_index: Dict[str, List[str]] = defaultdict(list)  # By fingerprint
        self._trace_index: Dict[str, List[str]] = defaultdict(list)  # By trace_id
        
        # Statistics
        self._stats = {
            "total_collected": 0,
            "total_processed": 0,
            "total_persisted": 0,
            "errors_by_category": defaultdict(int),
            "errors_by_severity": defaultdict(int),
            "errors_by_type": defaultdict(int),
        }
        
        # Background tasks
        self._flush_task = None
        self._running = False
        self._lock = threading.Lock()
        
        # Handlers
        self._error_handlers: List[Callable[[ErrorRecord], None]] = []
        
        # Initialize database schema if needed
        if self.database and self.enable_persistence:
            asyncio.create_task(self._initialize_database())
    
    async def _initialize_database(self):
        """Initialize database schema for error tracking"""
        await self.database.execute("""
            CREATE TABLE IF NOT EXISTS error_records (
                error_id TEXT PRIMARY KEY,
                fingerprint TEXT NOT NULL,
                timestamp REAL NOT NULL,
                trace_id TEXT,
                span_id TEXT,
                parent_error_id TEXT,
                category TEXT NOT NULL,
                severity TEXT NOT NULL,
                error_type TEXT NOT NULL,
                error_message TEXT,
                stack_trace TEXT,
                metadata TEXT,
                processed BOOLEAN DEFAULT FALSE,
                recovery_attempted BOOLEAN DEFAULT FALSE,
                recovery_successful BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                INDEX idx_errors_fingerprint (fingerprint),
                INDEX idx_errors_trace (trace_id),
                INDEX idx_errors_timestamp (timestamp),
                INDEX idx_errors_category_severity (category, severity)
            )
        """)
        
        await self.database.execute("""
            CREATE TABLE IF NOT EXISTS error_aggregates (
                fingerprint TEXT PRIMARY KEY,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP,
                occurrence_count INTEGER DEFAULT 1,
                affected_users INTEGER DEFAULT 0,
                affected_traces INTEGER DEFAULT 0,
                category TEXT,
                severity TEXT,
                error_type TEXT,
                sample_message TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    def collect(self, error: Exception) -> ErrorRecord:
        """Collect an error
        
        Args:
            error: The error to collect
            
        Returns:
            ErrorRecord created from the error
        """
        with create_span("error.collect") as span:
            # Convert to FlashcardError if needed
            if not isinstance(error, FlashcardError):
                error = FlashcardError(
                    str(error),
                    category=ErrorCategory.SYSTEM,
                    cause=error
                )
            
            # Create record
            record = ErrorRecord.from_error(error)
            
            # Add to buffer
            with self._lock:
                self._error_buffer.append(record)
                self._error_index[record.error_id] = record
                self._fingerprint_index[record.fingerprint].append(record.error_id)
                if record.trace_id:
                    self._trace_index[record.trace_id].append(record.error_id)
                
                # Update statistics
                self._stats["total_collected"] += 1
                self._stats["errors_by_category"][error.category.value] += 1
                self._stats["errors_by_severity"][error.severity.value] += 1
                self._stats["errors_by_type"][error.metadata.error_type] += 1
            
            # Set span attributes
            span.set_attributes({
                "error.id": record.error_id,
                "error.fingerprint": record.fingerprint,
                "error.category": error.category.value,
                "error.severity": error.severity.value
            })
            
            # Record metrics
            record_metric(
                "error_collector.collected",
                1,
                metric_type="counter",
                attributes={
                    "category": error.category.value,
                    "severity": error.severity.value,
                    "type": error.metadata.error_type
                }
            )
            
            # Notify handlers
            for handler in self._error_handlers:
                try:
                    handler(record)
                except Exception as e:
                    logger.error(f"Error handler failed: {e}")
            
            # Check if immediate action needed
            if error.severity == ErrorSeverity.CRITICAL:
                add_event(
                    "critical_error_collected",
                    attributes={
                        "error_id": record.error_id,
                        "error_type": error.metadata.error_type,
                        "message": str(error)[:200]
                    }
                )
            
            return record
    
    def get_error(self, error_id: str) -> Optional[ErrorRecord]:
        """Get error by ID"""
        with self._lock:
            return self._error_index.get(error_id)
    
    def get_errors_by_trace(self, trace_id: str) -> List[ErrorRecord]:
        """Get all errors for a trace"""
        with self._lock:
            error_ids = self._trace_index.get(trace_id, [])
            return [self._error_index[eid] for eid in error_ids if eid in self._error_index]
    
    def get_errors_by_fingerprint(self, fingerprint: str) -> List[ErrorRecord]:
        """Get all errors with same fingerprint"""
        with self._lock:
            error_ids = self._fingerprint_index.get(fingerprint, [])
            return [self._error_index[eid] for eid in error_ids if eid in self._error_index]
    
    def get_similar_errors(self, error: FlashcardError, limit: int = 10) -> List[ErrorRecord]:
        """Get similar errors based on fingerprint"""
        similar = self.get_errors_by_fingerprint(error.metadata.fingerprint)
        return sorted(similar, key=lambda e: e.timestamp, reverse=True)[:limit]
    
    def mark_processed(self, error_id: str, recovery_attempted: bool = False, recovery_successful: bool = False):
        """Mark an error as processed"""
        with self._lock:
            if error_id in self._error_index:
                record = self._error_index[error_id]
                record.processed = True
                record.recovery_attempted = recovery_attempted
                record.recovery_successful = recovery_successful
                
                self._stats["total_processed"] += 1
    
    async def flush(self):
        """Flush error buffer to persistent storage"""
        if not self.database or not self.enable_persistence:
            return
        
        with create_span("error_collector.flush") as span:
            errors_to_persist = []
            
            with self._lock:
                # Get unprocessed errors
                errors_to_persist = [
                    record for record in self._error_buffer
                    if not record.processed
                ]
                
                # Clear old processed errors from buffer
                self._error_buffer = deque(
                    (r for r in self._error_buffer if not r.processed or 
                     (time.time() - r.timestamp) < 3600),  # Keep for 1 hour
                    maxlen=self.max_buffer_size
                )
            
            if not errors_to_persist:
                return
            
            span.set_attribute("error.flush_count", len(errors_to_persist))
            
            # Persist to database
            for record in errors_to_persist:
                try:
                    await self._persist_error(record)
                    self._stats["total_persisted"] += 1
                except Exception as e:
                    logger.error(f"Failed to persist error {record.error_id}: {e}")
            
            # Update aggregates
            await self._update_aggregates(errors_to_persist)
            
            record_metric(
                "error_collector.flushed",
                len(errors_to_persist),
                metric_type="counter"
            )
    
    async def _persist_error(self, record: ErrorRecord):
        """Persist error record to database"""
        metadata_json = json.dumps(record.metadata.to_dict())
        
        await self.database.execute("""
            INSERT OR IGNORE INTO error_records (
                error_id, fingerprint, timestamp, trace_id, span_id,
                parent_error_id, category, severity, error_type,
                error_message, stack_trace, metadata, processed,
                recovery_attempted, recovery_successful
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.error_id,
            record.fingerprint,
            record.timestamp,
            record.trace_id,
            record.span_id,
            record.parent_error_id,
            record.metadata.category.value,
            record.metadata.severity.value,
            record.metadata.error_type,
            record.metadata.error_message,
            record.metadata.stack_trace,
            metadata_json,
            record.processed,
            record.recovery_attempted,
            record.recovery_successful
        ))
    
    async def _update_aggregates(self, records: List[ErrorRecord]):
        """Update error aggregates"""
        # Group by fingerprint
        by_fingerprint = defaultdict(list)
        for record in records:
            by_fingerprint[record.fingerprint].append(record)
        
        for fingerprint, fingerprint_records in by_fingerprint.items():
            # Get aggregate stats
            first_record = min(fingerprint_records, key=lambda r: r.timestamp)
            last_record = max(fingerprint_records, key=lambda r: r.timestamp)
            
            unique_users = len(set(
                r.metadata.user_id for r in fingerprint_records 
                if r.metadata.user_id
            ))
            unique_traces = len(set(
                r.trace_id for r in fingerprint_records 
                if r.trace_id
            ))
            
            # Update aggregate
            await self.database.execute("""
                INSERT INTO error_aggregates (
                    fingerprint, first_seen, last_seen, occurrence_count,
                    affected_users, affected_traces, category, severity,
                    error_type, sample_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(fingerprint) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    occurrence_count = occurrence_count + excluded.occurrence_count,
                    affected_users = affected_users + excluded.affected_users,
                    affected_traces = affected_traces + excluded.affected_traces,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                fingerprint,
                datetime.fromtimestamp(first_record.timestamp),
                datetime.fromtimestamp(last_record.timestamp),
                len(fingerprint_records),
                unique_users,
                unique_traces,
                first_record.metadata.category.value,
                first_record.metadata.severity.value,
                first_record.metadata.error_type,
                first_record.metadata.error_message[:500]
            ))
    
    def add_handler(self, handler: Callable[[ErrorRecord], None]):
        """Add error handler callback"""
        self._error_handlers.append(handler)
    
    def remove_handler(self, handler: Callable[[ErrorRecord], None]):
        """Remove error handler"""
        if handler in self._error_handlers:
            self._error_handlers.remove(handler)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get collector statistics"""
        with self._lock:
            return {
                "buffer_size": len(self._error_buffer),
                "unique_errors": len(self._error_index),
                "unique_fingerprints": len(self._fingerprint_index),
                **self._stats
            }
    
    async def start(self):
        """Start background tasks"""
        self._running = True
        self._flush_task = asyncio.create_task(self._periodic_flush())
    
    async def stop(self):
        """Stop background tasks"""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Final flush
        await self.flush()
    
    async def _periodic_flush(self):
        """Periodically flush error buffer"""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error during periodic flush: {e}")


# Global error collector instance
_error_collector: Optional[ErrorCollector] = None


def get_error_collector() -> ErrorCollector:
    """Get global error collector instance"""
    global _error_collector
    if _error_collector is None:
        _error_collector = ErrorCollector()
    return _error_collector


def initialize_error_collector(
    database: Optional[DatabaseManager] = None,
    **kwargs
) -> ErrorCollector:
    """Initialize global error collector"""
    global _error_collector
    _error_collector = ErrorCollector(database=database, **kwargs)
    return _error_collector