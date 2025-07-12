"""
Processing Optimizer for concurrent batch processing with checkpoints and recovery.

This module provides optimized processing capabilities for the flashcard pipeline:
- Concurrent processing with configurable worker pools
- Intelligent batching strategies
- Checkpoint saving and recovery
- Metrics collection and reporting
- Error handling and retry logic
"""

import asyncio
import logging
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum
import threading
import queue
import hashlib

from .database.db_manager import DatabaseManager, VocabularyRecord, ProcessingTask
from .models import VocabularyItem, BatchProgress, CacheStats
from .exceptions import ProcessingError, DatabaseError

logger = logging.getLogger(__name__)


class ProcessingStatus(str, Enum):
    """Processing status enum"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CHECKPOINT = "checkpoint"


@dataclass
class ProcessingMetrics:
    """Metrics collected during processing"""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_items: int = 0
    processed_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_api_calls: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    avg_latency_ms: float = 0.0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        """Calculate processing duration in seconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.now() - self.start_time).total_seconds()
    
    @property
    def throughput(self) -> float:
        """Calculate items processed per second"""
        duration = self.duration_seconds
        if duration == 0:
            return 0.0
        return self.processed_items / duration
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.processed_items == 0:
            return 0.0
        return (self.successful_items / self.processed_items) * 100
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate percentage"""
        total_lookups = self.cache_hits + self.cache_misses
        if total_lookups == 0:
            return 0.0
        return (self.cache_hits / total_lookups) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "successful_items": self.successful_items,
            "failed_items": self.failed_items,
            "throughput": self.throughput,
            "success_rate": self.success_rate,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.cache_hit_rate,
            "total_api_calls": self.total_api_calls,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "avg_latency_ms": self.avg_latency_ms,
            "error_count": len(self.errors)
        }


@dataclass
class ProcessingCheckpoint:
    """Checkpoint data for recovery"""
    checkpoint_id: str
    batch_id: str
    timestamp: datetime
    processed_items: List[int]  # vocabulary IDs
    pending_items: List[int]   # vocabulary IDs
    metrics: ProcessingMetrics
    stage: str = "stage1"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        """Serialize checkpoint to JSON"""
        data = {
            "checkpoint_id": self.checkpoint_id,
            "batch_id": self.batch_id,
            "timestamp": self.timestamp.isoformat(),
            "processed_items": self.processed_items,
            "pending_items": self.pending_items,
            "metrics": self.metrics.to_dict(),
            "stage": self.stage,
            "metadata": self.metadata
        }
        return json.dumps(data, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ProcessingCheckpoint':
        """Deserialize checkpoint from JSON"""
        data = json.loads(json_str)
        
        # Reconstruct metrics
        metrics = ProcessingMetrics()
        metrics_data = data.get("metrics", {})
        metrics.start_time = datetime.fromisoformat(metrics_data.get("start_time", datetime.now().isoformat()))
        if metrics_data.get("end_time"):
            metrics.end_time = datetime.fromisoformat(metrics_data["end_time"])
        metrics.total_items = metrics_data.get("total_items", 0)
        metrics.processed_items = metrics_data.get("processed_items", 0)
        metrics.successful_items = metrics_data.get("successful_items", 0)
        metrics.failed_items = metrics_data.get("failed_items", 0)
        metrics.cache_hits = metrics_data.get("cache_hits", 0)
        metrics.cache_misses = metrics_data.get("cache_misses", 0)
        metrics.total_api_calls = metrics_data.get("total_api_calls", 0)
        metrics.total_tokens = metrics_data.get("total_tokens", 0)
        metrics.total_cost = metrics_data.get("total_cost", 0.0)
        metrics.avg_latency_ms = metrics_data.get("avg_latency_ms", 0.0)
        
        return cls(
            checkpoint_id=data["checkpoint_id"],
            batch_id=data["batch_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            processed_items=data["processed_items"],
            pending_items=data["pending_items"],
            metrics=metrics,
            stage=data.get("stage", "stage1"),
            metadata=data.get("metadata", {})
        )


class ProcessingOptimizer:
    """
    Optimizes processing of vocabulary items with concurrent execution,
    intelligent batching, checkpointing, and metrics collection.
    """
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        max_workers: int = 5,
        batch_size: int = 50,
        checkpoint_interval: int = 100,
        enable_metrics: bool = True
    ):
        """
        Initialize the processing optimizer.
        
        Args:
            db_manager: Database manager instance
            max_workers: Maximum concurrent workers
            batch_size: Items per batch
            checkpoint_interval: Items between checkpoints
            enable_metrics: Whether to collect detailed metrics
        """
        self.db_manager = db_manager
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.checkpoint_interval = checkpoint_interval
        self.enable_metrics = enable_metrics
        
        # Processing state
        self._current_batch_id: Optional[str] = None
        self._metrics: Optional[ProcessingMetrics] = None
        self._checkpoint_lock = threading.Lock()
        self._progress_callbacks: List[Callable[[BatchProgress], None]] = []
        self._error_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
        # Metrics collection
        self._latency_samples: List[float] = []
        self._metrics_lock = threading.Lock()
        
        logger.info(
            f"ProcessingOptimizer initialized with {max_workers} workers, "
            f"batch_size={batch_size}, checkpoint_interval={checkpoint_interval}"
        )
    
    def generate_batch_id(self) -> str:
        """Generate unique batch ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        return f"batch_{timestamp}_{random_suffix}"
    
    def add_progress_callback(self, callback: Callable[[BatchProgress], None]):
        """Add a progress callback function"""
        self._progress_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add an error callback function"""
        self._error_callbacks.append(callback)
    
    def _notify_progress(self, progress: BatchProgress):
        """Notify all progress callbacks"""
        for callback in self._progress_callbacks:
            try:
                callback(progress)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
    
    def _notify_error(self, error_info: Dict[str, Any]):
        """Notify all error callbacks"""
        for callback in self._error_callbacks:
            try:
                callback(error_info)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")
    
    def _update_metrics(
        self,
        success: bool = True,
        cache_hit: bool = False,
        api_calls: int = 0,
        tokens: int = 0,
        cost: float = 0.0,
        latency_ms: float = 0.0,
        error: Optional[Exception] = None
    ):
        """Thread-safe metrics update"""
        if not self.enable_metrics or not self._metrics:
            return
        
        with self._metrics_lock:
            self._metrics.processed_items += 1
            
            if success:
                self._metrics.successful_items += 1
            else:
                self._metrics.failed_items += 1
                if error:
                    self._metrics.errors.append({
                        "timestamp": datetime.now().isoformat(),
                        "error": str(error),
                        "type": type(error).__name__
                    })
            
            if cache_hit:
                self._metrics.cache_hits += 1
            else:
                self._metrics.cache_misses += 1
            
            self._metrics.total_api_calls += api_calls
            self._metrics.total_tokens += tokens
            self._metrics.total_cost += cost
            
            if latency_ms > 0:
                self._latency_samples.append(latency_ms)
                # Keep only last 1000 samples for moving average
                if len(self._latency_samples) > 1000:
                    self._latency_samples = self._latency_samples[-1000:]
                self._metrics.avg_latency_ms = sum(self._latency_samples) / len(self._latency_samples)
    
    def _create_checkpoint(
        self,
        processed_ids: List[int],
        pending_ids: List[int],
        stage: str = "stage1"
    ) -> ProcessingCheckpoint:
        """Create a checkpoint for current state"""
        checkpoint = ProcessingCheckpoint(
            checkpoint_id=hashlib.md5(
                f"{self._current_batch_id}_{datetime.now().isoformat()}".encode()
            ).hexdigest(),
            batch_id=self._current_batch_id or "",
            timestamp=datetime.now(),
            processed_items=processed_ids,
            pending_items=pending_ids,
            metrics=self._metrics or ProcessingMetrics(),
            stage=stage,
            metadata={
                "batch_size": self.batch_size,
                "max_workers": self.max_workers,
                "checkpoint_interval": self.checkpoint_interval
            }
        )
        return checkpoint
    
    def _save_checkpoint(self, checkpoint: ProcessingCheckpoint):
        """Save checkpoint to database"""
        try:
            with self._checkpoint_lock:
                # Save checkpoint as system configuration
                self.db_manager.set_system_config(
                    key=f"checkpoint_{checkpoint.batch_id}",
                    value=checkpoint.to_json(),
                    value_type="json",
                    description=f"Processing checkpoint for batch {checkpoint.batch_id}"
                )
                
                # Also save latest checkpoint reference
                self.db_manager.set_system_config(
                    key="latest_checkpoint",
                    value=checkpoint.checkpoint_id,
                    value_type="string",
                    description="Latest processing checkpoint ID"
                )
                
                logger.info(f"Saved checkpoint {checkpoint.checkpoint_id} for batch {checkpoint.batch_id}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            raise ProcessingError(f"Checkpoint save failed: {e}")
    
    def load_checkpoint(self, batch_id: Optional[str] = None) -> Optional[ProcessingCheckpoint]:
        """Load checkpoint from database"""
        try:
            if not batch_id:
                # Get latest checkpoint
                latest_id = self.db_manager.get_system_config("latest_checkpoint")
                if not latest_id:
                    return None
                
                # Find batch_id from checkpoints
                import re
                pattern = re.compile(r"checkpoint_batch_\d{8}_\d{6}_[a-f0-9]{8}")
                
                # This is a simplified approach - in production, you'd query all checkpoint keys
                # For now, we'll assume the batch_id is stored with the latest checkpoint
                logger.warning("Loading latest checkpoint requires batch_id")
                return None
            
            checkpoint_data = self.db_manager.get_system_config(f"checkpoint_{batch_id}")
            if not checkpoint_data:
                return None
            
            if isinstance(checkpoint_data, str):
                checkpoint = ProcessingCheckpoint.from_json(checkpoint_data)
            else:
                checkpoint = ProcessingCheckpoint.from_json(json.dumps(checkpoint_data))
            
            logger.info(f"Loaded checkpoint {checkpoint.checkpoint_id} for batch {batch_id}")
            return checkpoint
            
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None
    
    def _get_vocabulary_batch(
        self,
        limit: int,
        offset: int = 0,
        exclude_ids: Optional[List[int]] = None
    ) -> List[VocabularyRecord]:
        """Get a batch of vocabulary items to process"""
        # Get pending vocabulary items
        items = self.db_manager.get_pending_vocabulary(limit=limit + offset)
        
        # Filter out excluded IDs (already processed)
        if exclude_ids:
            items = [item for item in items if item.id not in exclude_ids]
        
        # Apply offset and limit
        if offset > 0:
            items = items[offset:]
        
        return items[:limit]
    
    def _process_single_item(
        self,
        vocab: VocabularyRecord,
        processor_func: Callable[[VocabularyRecord], Tuple[bool, Dict[str, Any]]]
    ) -> Tuple[int, bool, Dict[str, Any]]:
        """
        Process a single vocabulary item.
        
        Args:
            vocab: Vocabulary record to process
            processor_func: Function that processes the item and returns (success, result_data)
        
        Returns:
            Tuple of (vocab_id, success, result_data)
        """
        start_time = time.time()
        
        try:
            # Call the processor function
            success, result_data = processor_func(vocab)
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Update metrics
            self._update_metrics(
                success=success,
                cache_hit=result_data.get("cache_hit", False),
                api_calls=result_data.get("api_calls", 0),
                tokens=result_data.get("tokens", 0),
                cost=result_data.get("cost", 0.0),
                latency_ms=latency_ms
            )
            
            # Record performance metrics in database
            if self.enable_metrics:
                self.db_manager.record_processing_performance(
                    task_type="vocabulary_processing",
                    processing_time_ms=int(latency_ms),
                    cache_hit=result_data.get("cache_hit", False),
                    success=success
                )
            
            return vocab.id or 0, success, result_data
            
        except Exception as e:
            logger.error(f"Error processing vocabulary item {vocab.id}: {e}")
            
            # Update metrics
            self._update_metrics(
                success=False,
                error=e,
                latency_ms=(time.time() - start_time) * 1000
            )
            
            # Notify error callbacks
            self._notify_error({
                "vocab_id": vocab.id,
                "error": str(e),
                "type": type(e).__name__,
                "timestamp": datetime.now().isoformat()
            })
            
            return vocab.id or 0, False, {"error": str(e)}
    
    def process_batch_concurrent(
        self,
        processor_func: Callable[[VocabularyRecord], Tuple[bool, Dict[str, Any]]],
        total_items: Optional[int] = None,
        resume_from_checkpoint: Optional[str] = None,
        stage: str = "stage1"
    ) -> ProcessingMetrics:
        """
        Process vocabulary items in concurrent batches with checkpointing.
        
        Args:
            processor_func: Function to process each vocabulary item
            total_items: Total number of items to process (None for all pending)
            resume_from_checkpoint: Batch ID to resume from
            stage: Processing stage name
        
        Returns:
            ProcessingMetrics with final results
        """
        # Initialize or resume from checkpoint
        if resume_from_checkpoint:
            checkpoint = self.load_checkpoint(resume_from_checkpoint)
            if not checkpoint:
                raise ProcessingError(f"Checkpoint {resume_from_checkpoint} not found")
            
            self._current_batch_id = checkpoint.batch_id
            self._metrics = checkpoint.metrics
            processed_ids = set(checkpoint.processed_items)
            pending_ids = checkpoint.pending_items
            
            logger.info(
                f"Resuming batch {self._current_batch_id} from checkpoint. "
                f"Processed: {len(processed_ids)}, Pending: {len(pending_ids)}"
            )
        else:
            self._current_batch_id = self.generate_batch_id()
            self._metrics = ProcessingMetrics()
            processed_ids = set()
            pending_ids = []
            
            logger.info(f"Starting new batch {self._current_batch_id}")
        
        # Get items to process
        if not pending_ids:
            # Fresh start - get all pending items
            all_items = self._get_vocabulary_batch(
                limit=total_items or 10000,  # Reasonable max
                exclude_ids=list(processed_ids)
            )
            pending_ids = [item.id for item in all_items if item.id]
            self._metrics.total_items = len(pending_ids)
        
        # Create progress tracker
        progress = BatchProgress(
            batch_id=self._current_batch_id,
            total_items=self._metrics.total_items,
            completed_items=len(processed_ids),
            failed_items=self._metrics.failed_items,
            current_stage=stage,
            started_at=self._metrics.start_time,
            updated_at=datetime.now()
        )
        
        # Process in batches with concurrent execution
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while pending_ids:
                # Get next batch
                batch_ids = pending_ids[:self.batch_size]
                pending_ids = pending_ids[self.batch_size:]
                
                # Load vocabulary records for batch
                batch_items = []
                for vocab_id in batch_ids:
                    vocab = self.db_manager.get_vocabulary_by_id(vocab_id)
                    if vocab:
                        batch_items.append(vocab)
                
                # Submit batch for concurrent processing
                futures = {
                    executor.submit(self._process_single_item, vocab, processor_func): vocab
                    for vocab in batch_items
                }
                
                # Collect results
                batch_results = []
                for future in as_completed(futures):
                    try:
                        vocab_id, success, result_data = future.result()
                        processed_ids.add(vocab_id)
                        batch_results.append((vocab_id, success, result_data))
                        
                        # Update progress
                        progress.completed_items = len(processed_ids)
                        progress.failed_items = self._metrics.failed_items
                        progress.updated_at = datetime.now()
                        
                        # Notify progress
                        if len(processed_ids) % 10 == 0:  # Every 10 items
                            self._notify_progress(progress)
                        
                    except Exception as e:
                        logger.error(f"Future execution failed: {e}")
                        vocab = futures[future]
                        if vocab.id:
                            processed_ids.add(vocab.id)
                            self._metrics.failed_items += 1
                
                # Save checkpoint if needed
                if len(processed_ids) % self.checkpoint_interval == 0:
                    checkpoint = self._create_checkpoint(
                        processed_ids=list(processed_ids),
                        pending_ids=pending_ids,
                        stage=stage
                    )
                    self._save_checkpoint(checkpoint)
                    logger.info(
                        f"Checkpoint saved. Processed: {len(processed_ids)}, "
                        f"Remaining: {len(pending_ids)}"
                    )
        
        # Final metrics
        self._metrics.end_time = datetime.now()
        
        # Save final checkpoint
        final_checkpoint = self._create_checkpoint(
            processed_ids=list(processed_ids),
            pending_ids=[],  # All done
            stage=stage
        )
        self._save_checkpoint(final_checkpoint)
        
        # Clean up old checkpoints (keep only latest 10)
        # This would be implemented in production
        
        logger.info(
            f"Batch {self._current_batch_id} completed. "
            f"Total: {self._metrics.total_items}, "
            f"Success: {self._metrics.successful_items}, "
            f"Failed: {self._metrics.failed_items}, "
            f"Duration: {self._metrics.duration_seconds:.2f}s, "
            f"Throughput: {self._metrics.throughput:.2f} items/s"
        )
        
        return self._metrics
    
    def optimize_batch_size(self, target_latency_ms: float = 1000.0) -> int:
        """
        Dynamically optimize batch size based on performance metrics.
        
        Args:
            target_latency_ms: Target average latency per item
        
        Returns:
            Optimized batch size
        """
        if not self._metrics or not self._latency_samples:
            return self.batch_size
        
        avg_latency = self._metrics.avg_latency_ms
        
        if avg_latency == 0:
            return self.batch_size
        
        # Calculate optimal batch size based on latency
        # If latency is higher than target, reduce batch size
        # If latency is lower, increase batch size
        latency_ratio = target_latency_ms / avg_latency
        
        if latency_ratio > 1.5:
            # Much faster than target, increase batch size
            new_batch_size = min(int(self.batch_size * 1.5), 200)
        elif latency_ratio > 1.1:
            # Slightly faster, small increase
            new_batch_size = min(int(self.batch_size * 1.1), 200)
        elif latency_ratio < 0.7:
            # Much slower than target, decrease batch size
            new_batch_size = max(int(self.batch_size * 0.7), 10)
        elif latency_ratio < 0.9:
            # Slightly slower, small decrease
            new_batch_size = max(int(self.batch_size * 0.9), 10)
        else:
            # Within acceptable range
            new_batch_size = self.batch_size
        
        if new_batch_size != self.batch_size:
            logger.info(
                f"Adjusting batch size from {self.batch_size} to {new_batch_size} "
                f"based on avg latency {avg_latency:.2f}ms (target: {target_latency_ms}ms)"
            )
            self.batch_size = new_batch_size
        
        return self.batch_size
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get current metrics summary"""
        if not self._metrics:
            return {}
        
        return self._metrics.to_dict()
    
    def reset_metrics(self):
        """Reset metrics for new processing run"""
        self._metrics = ProcessingMetrics()
        self._latency_samples = []