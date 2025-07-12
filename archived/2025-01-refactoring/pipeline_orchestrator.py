"""
Enhanced Pipeline Orchestrator with database integration and task queue management.
"""

import asyncio
import uuid
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import logging

from .database import DatabaseManager
from .api_client import OpenRouterClient
from .cache_v2 import ModernCacheService
from .models import VocabularyItem, Stage1Response, Stage2Response
from .exceptions import PipelineError
from .concurrent import (
    ConcurrentPipelineOrchestrator,
    OrderedResultsCollector,
    ConcurrentProcessingMonitor
)

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    NORMAL = 5
    HIGH = 8
    URGENT = 10


class TaskStatus(Enum):
    """Task processing status"""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"


@dataclass
class ProcessingTask:
    """Represents a processing task with metadata"""
    task_id: str
    vocabulary_id: int
    task_type: str  # full_pipeline, stage1_only, stage2_only
    priority: int = TaskPriority.NORMAL.value
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "task_id": self.task_id,
            "vocabulary_id": self.vocabulary_id,
            "task_type": self.task_type,
            "priority": self.priority,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "metadata": self.metadata
        }


class TaskQueue:
    """Database-backed task queue with priority management"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._processing_tasks = {}  # task_id -> Task mapping for active tasks
    
    def create_task(self, vocabulary_id: int, task_type: str = "full_pipeline",
                   priority: int = TaskPriority.NORMAL.value,
                   metadata: Optional[Dict] = None) -> ProcessingTask:
        """Create a new processing task"""
        task = ProcessingTask(
            task_id=f"task_{vocabulary_id}_{uuid.uuid4().hex[:8]}",
            vocabulary_id=vocabulary_id,
            task_type=task_type,
            priority=priority,
            metadata=metadata or {}
        )
        
        # Store in database
        with self.db_manager.get_connection() as conn:
            conn.execute("""
                INSERT INTO processing_tasks (
                    task_id, vocabulary_id, task_type, priority, status,
                    retry_count, max_retries, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                task.task_id,
                task.vocabulary_id,
                task.task_type,
                task.priority,
                task.status.value,
                task.retry_count,
                task.max_retries,
                json.dumps(task.metadata)
            ))
            conn.commit()
        
        logger.info(f"Created task {task.task_id} for vocabulary {vocabulary_id}")
        return task
    
    def get_next_tasks(self, limit: int = 10, task_types: Optional[List[str]] = None) -> List[ProcessingTask]:
        """Get next tasks to process by priority"""
        with self.db_manager.get_connection() as conn:
            query = """
                SELECT 
                    pt.*, 
                    vm.korean, 
                    vm.english,
                    vm.type as vocab_type
                FROM processing_tasks pt
                JOIN vocabulary_master vm ON pt.vocabulary_id = vm.id
                WHERE pt.status IN ('pending', 'retry')
                AND (pt.scheduled_at IS NULL OR pt.scheduled_at <= datetime('now'))
            """
            
            params = []
            if task_types:
                placeholders = ','.join('?' * len(task_types))
                query += f" AND pt.task_type IN ({placeholders})"
                params.extend(task_types)
            
            query += " ORDER BY pt.priority DESC, pt.created_at ASC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            tasks = []
            
            for row in cursor:
                task = ProcessingTask(
                    task_id=row["task_id"],
                    vocabulary_id=row["vocabulary_id"],
                    task_type=row["task_type"],
                    priority=row["priority"],
                    status=TaskStatus(row["status"]),
                    retry_count=row["retry_count"],
                    max_retries=row["max_retries"],
                    scheduled_at=datetime.fromisoformat(row["scheduled_at"]) if row["scheduled_at"] else None,
                    started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
                    completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                    error_message=row["error_message"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {}
                )
                
                # Add vocabulary info to metadata
                task.metadata.update({
                    "korean": row["korean"],
                    "english": row["english"],
                    "vocab_type": row["vocab_type"]
                })
                
                tasks.append(task)
            
            return tasks
    
    def mark_processing(self, task_id: str) -> bool:
        """Mark task as processing"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute("""
                UPDATE processing_tasks
                SET status = 'processing', started_at = CURRENT_TIMESTAMP
                WHERE task_id = ? AND status IN ('pending', 'retry')
            """, (task_id,))
            
            if cursor.rowcount > 0:
                conn.commit()
                logger.info(f"Task {task_id} marked as processing")
                return True
            
            return False
    
    def mark_completed(self, task_id: str, result_data: Optional[Dict] = None) -> bool:
        """Mark task as completed"""
        with self.db_manager.get_connection() as conn:
            # Update task status
            conn.execute("""
                UPDATE processing_tasks
                SET status = 'completed', 
                    completed_at = CURRENT_TIMESTAMP,
                    error_message = NULL
                WHERE task_id = ?
            """, (task_id,))
            
            # Store result if provided
            if result_data:
                conn.execute("""
                    INSERT INTO processing_results (
                        task_id, stage, result_type, result_data, tokens_used
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    task_id,
                    result_data.get("stage", 0),
                    result_data.get("result_type", "complete"),
                    json.dumps(result_data.get("data", {})),
                    result_data.get("tokens_used", 0)
                ))
            
            conn.commit()
            logger.info(f"Task {task_id} completed")
            return True
    
    def mark_failed(self, task_id: str, error_message: str, retry: bool = True) -> bool:
        """Mark task as failed with optional retry"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT retry_count, max_retries FROM processing_tasks
                WHERE task_id = ?
            """, (task_id,))
            
            row = cursor.fetchone()
            if not row:
                return False
            
            retry_count = row["retry_count"]
            max_retries = row["max_retries"]
            
            if retry and retry_count < max_retries:
                # Schedule retry with exponential backoff
                retry_delay = min(300, 30 * (2 ** retry_count))  # Max 5 minutes
                scheduled_at = datetime.now() + timedelta(seconds=retry_delay)
                
                conn.execute("""
                    UPDATE processing_tasks
                    SET status = 'retry',
                        retry_count = retry_count + 1,
                        scheduled_at = ?,
                        error_message = ?
                    WHERE task_id = ?
                """, (scheduled_at, error_message, task_id))
                
                logger.info(f"Task {task_id} scheduled for retry #{retry_count + 1} at {scheduled_at}")
            else:
                # Mark as permanently failed
                conn.execute("""
                    UPDATE processing_tasks
                    SET status = 'failed',
                        completed_at = CURRENT_TIMESTAMP,
                        error_message = ?
                    WHERE task_id = ?
                """, (error_message, task_id))
                
                logger.error(f"Task {task_id} permanently failed: {error_message}")
            
            conn.commit()
            return True
    
    def get_task_status(self, task_id: str) -> Optional[ProcessingTask]:
        """Get current status of a task"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM processing_tasks WHERE task_id = ?
            """, (task_id,))
            
            row = cursor.fetchone()
            if row:
                return ProcessingTask(
                    task_id=row["task_id"],
                    vocabulary_id=row["vocabulary_id"],
                    task_type=row["task_type"],
                    priority=row["priority"],
                    status=TaskStatus(row["status"]),
                    retry_count=row["retry_count"],
                    max_retries=row["max_retries"],
                    scheduled_at=datetime.fromisoformat(row["scheduled_at"]) if row["scheduled_at"] else None,
                    started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
                    completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                    error_message=row["error_message"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {}
                )
        
        return None
    
    def cleanup_old_tasks(self, days: int = 30) -> int:
        """Clean up old completed tasks"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM processing_tasks
                WHERE status IN ('completed', 'cancelled')
                AND completed_at < datetime('now', ? || ' days')
            """, (-days,))
            
            deleted = cursor.rowcount
            conn.commit()
            
            logger.info(f"Cleaned up {deleted} old tasks")
            return deleted


class DatabasePipelineOrchestrator:
    """Pipeline orchestrator with database integration"""
    
    def __init__(self, db_manager: DatabaseManager,
                 api_client: OpenRouterClient,
                 cache_service: ModernCacheService,
                 max_concurrent: int = 10):
        self.db_manager = db_manager
        self.api_client = api_client
        self.cache_service = cache_service
        self.max_concurrent = max_concurrent
        self.task_queue = TaskQueue(db_manager)
        self.monitor = ConcurrentProcessingMonitor()
        self._shutdown = False
    
    async def process_vocabulary_item(self, task: ProcessingTask) -> Tuple[bool, Optional[Dict]]:
        """Process a single vocabulary item"""
        try:
            # Create VocabularyItem
            vocab_item = VocabularyItem(
                position=task.vocabulary_id,
                term=task.metadata.get("korean", ""),
                type=task.metadata.get("vocab_type", "word")
            )
            
            result_data = {
                "task_id": task.task_id,
                "vocabulary_id": task.vocabulary_id,
                "stages": {}
            }
            
            # Stage 1 processing
            if task.task_type in ["full_pipeline", "stage1_only"]:
                # Check cache
                cached_stage1 = await self.cache_service.get_stage1(vocab_item)
                
                if cached_stage1:
                    stage1_response, tokens_saved = cached_stage1
                    result_data["stages"]["stage1"] = {
                        "from_cache": True,
                        "tokens_saved": tokens_saved
                    }
                else:
                    # Call API
                    stage1_response, usage = await self.api_client.process_stage1(vocab_item)
                    
                    # Save to cache
                    await self.cache_service.save_stage1(vocab_item, stage1_response, usage.total_tokens)
                    
                    result_data["stages"]["stage1"] = {
                        "from_cache": False,
                        "tokens_used": usage.total_tokens,
                        "cost": usage.estimated_cost
                    }
                
                # Store stage 1 result
                self._store_stage1_result(task.task_id, task.vocabulary_id, stage1_response)
            
            # Stage 2 processing
            if task.task_type in ["full_pipeline", "stage2_only"]:
                # Get stage 1 result if doing stage 2 only
                if task.task_type == "stage2_only":
                    stage1_response = self._get_stage1_result(task.vocabulary_id)
                    if not stage1_response:
                        raise PipelineError("Stage 1 result not found for stage 2 processing")
                
                # Check cache
                cached_stage2 = await self.cache_service.get_stage2(vocab_item, stage1_response)
                
                if cached_stage2:
                    stage2_response, tokens_saved = cached_stage2
                    result_data["stages"]["stage2"] = {
                        "from_cache": True,
                        "tokens_saved": tokens_saved
                    }
                else:
                    # Call API
                    stage2_response, usage = await self.api_client.process_stage2(vocab_item, stage1_response)
                    
                    # Save to cache
                    await self.cache_service.save_stage2(
                        vocab_item, stage1_response, stage2_response, usage.total_tokens
                    )
                    
                    result_data["stages"]["stage2"] = {
                        "from_cache": False,
                        "tokens_used": usage.total_tokens,
                        "cost": usage.estimated_cost
                    }
                
                # Store stage 2 result (flashcards)
                self._store_stage2_result(task.task_id, task.vocabulary_id, stage2_response)
            
            # Calculate totals
            total_tokens = sum(
                stage.get("tokens_used", 0)
                for stage in result_data["stages"].values()
            )
            total_cost = sum(
                stage.get("cost", 0)
                for stage in result_data["stages"].values()
            )
            
            result_data["total_tokens"] = total_tokens
            result_data["total_cost"] = total_cost
            result_data["completed_at"] = datetime.now().isoformat()
            
            return True, result_data
            
        except Exception as e:
            logger.error(f"Error processing task {task.task_id}: {e}")
            return False, {"error": str(e)}
    
    def _store_stage1_result(self, task_id: str, vocabulary_id: int, response: Stage1Response):
        """Store Stage 1 result in database"""
        with self.db_manager.get_connection() as conn:
            # Store in nuance_data table
            comparison_data = json.dumps([c.model_dump() for c in response.comparison]) if response.comparison else None
            homonyms_data = json.dumps([h.model_dump() for h in response.homonyms]) if response.homonyms else None
            
            conn.execute("""
                INSERT OR REPLACE INTO nuance_data (
                    vocabulary_id, task_id, term, term_with_pronunciation, ipa, pos,
                    primary_meaning, other_meanings, metaphor, metaphor_noun,
                    metaphor_action, suggested_location, anchor_object, anchor_sensory,
                    explanation, usage_context, comparison_data, homonyms_data,
                    korean_keywords
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                vocabulary_id,
                self._get_task_db_id(task_id),
                response.term,
                response.term_with_pronunciation,
                response.ipa,
                response.pos,
                response.primary_meaning,
                response.other_meanings,
                response.metaphor,
                response.metaphor_noun,
                response.metaphor_action,
                response.suggested_location,
                response.anchor_object,
                response.anchor_sensory,
                response.explanation,
                response.usage_context,
                comparison_data,
                homonyms_data,
                json.dumps(response.korean_keywords)
            ))
            
            conn.commit()
    
    def _store_stage2_result(self, task_id: str, vocabulary_id: int, response: Stage2Response):
        """Store Stage 2 result (flashcards) in database"""
        with self.db_manager.get_connection() as conn:
            # Get next position
            cursor = conn.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM flashcards")
            next_position = cursor.fetchone()[0]
            
            # Store each flashcard
            for idx, row in enumerate(response.flashcard_rows):
                conn.execute("""
                    INSERT INTO flashcards (
                        vocabulary_id, deck_name, front_content, back_content,
                        tags, position, tab_name, primer, honorific_level,
                        is_published
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    vocabulary_id,
                    row.tab_name,  # Use tab_name as deck_name
                    row.front,
                    row.back,
                    row.tags,
                    next_position + idx,
                    row.tab_name,
                    row.primer,
                    row.honorific_level
                ))
            
            conn.commit()
    
    def _get_stage1_result(self, vocabulary_id: int) -> Optional[Stage1Response]:
        """Retrieve Stage 1 result from database"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM nuance_data
                WHERE vocabulary_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (vocabulary_id,))
            
            row = cursor.fetchone()
            if row:
                # Reconstruct Stage1Response
                comparison = []
                if row["comparison_data"]:
                    comparison_data = json.loads(row["comparison_data"])
                    from .models import Comparison
                    comparison = [Comparison(**c) for c in comparison_data]
                
                homonyms = []
                if row["homonyms_data"]:
                    homonyms_data = json.loads(row["homonyms_data"])
                    from .models import Homonym
                    homonyms = [Homonym(**h) for h in homonyms_data]
                
                return Stage1Response(
                    term=row["term"],
                    term_with_pronunciation=row["term_with_pronunciation"],
                    ipa=row["ipa"],
                    pos=row["pos"],
                    primary_meaning=row["primary_meaning"],
                    other_meanings=row["other_meanings"],
                    metaphor=row["metaphor"],
                    metaphor_noun=row["metaphor_noun"],
                    metaphor_action=row["metaphor_action"],
                    suggested_location=row["suggested_location"],
                    anchor_object=row["anchor_object"],
                    anchor_sensory=row["anchor_sensory"],
                    explanation=row["explanation"],
                    usage_context=row["usage_context"],
                    comparison=comparison,
                    homonyms=homonyms,
                    korean_keywords=json.loads(row["korean_keywords"])
                )
        
        return None
    
    def _get_task_db_id(self, task_id: str) -> int:
        """Get database ID for task"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute("SELECT id FROM processing_tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            return row["id"] if row else None
    
    async def process_batch(self, batch_size: int = 10, task_types: Optional[List[str]] = None):
        """Process a batch of tasks"""
        # Get next tasks
        tasks = self.task_queue.get_next_tasks(batch_size, task_types)
        
        if not tasks:
            logger.info("No tasks available for processing")
            return
        
        logger.info(f"Processing batch of {len(tasks)} tasks")
        
        # Mark tasks as processing
        for task in tasks:
            self.task_queue.mark_processing(task.task_id)
        
        # Process concurrently
        results = await asyncio.gather(
            *[self.process_vocabulary_item(task) for task in tasks],
            return_exceptions=True
        )
        
        # Update task statuses
        for task, result in zip(tasks, results):
            if isinstance(result, Exception):
                self.task_queue.mark_failed(task.task_id, str(result))
            elif result[0]:  # Success
                self.task_queue.mark_completed(task.task_id, result[1])
            else:  # Failed
                self.task_queue.mark_failed(task.task_id, result[1].get("error", "Unknown error"))
    
    async def run_continuous(self, batch_size: int = 10, poll_interval: int = 5):
        """Run continuous processing with polling"""
        logger.info(f"Starting continuous processing (batch_size={batch_size}, poll_interval={poll_interval}s)")
        
        while not self._shutdown:
            try:
                # Process batch
                await self.process_batch(batch_size)
                
                # Wait before next poll
                await asyncio.sleep(poll_interval)
                
            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
                break
            except Exception as e:
                logger.error(f"Error in continuous processing: {e}")
                await asyncio.sleep(poll_interval)
    
    def shutdown(self):
        """Signal shutdown"""
        self._shutdown = True


class TaskScheduler:
    """Schedules tasks based on various criteria"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.task_queue = TaskQueue(db_manager)
    
    def schedule_vocabulary_batch(self, vocabulary_ids: List[int],
                                 priority: int = TaskPriority.NORMAL.value,
                                 task_type: str = "full_pipeline") -> List[ProcessingTask]:
        """Schedule a batch of vocabulary items for processing"""
        tasks = []
        
        for vocab_id in vocabulary_ids:
            task = self.task_queue.create_task(
                vocabulary_id=vocab_id,
                task_type=task_type,
                priority=priority
            )
            tasks.append(task)
        
        logger.info(f"Scheduled {len(tasks)} tasks for processing")
        return tasks
    
    def schedule_failed_retry(self, max_age_hours: int = 24) -> int:
        """Schedule retry for recently failed tasks"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute("""
                UPDATE processing_tasks
                SET status = 'retry',
                    scheduled_at = datetime('now', '+5 minutes')
                WHERE status = 'failed'
                AND retry_count < max_retries
                AND completed_at > datetime('now', ? || ' hours')
            """, (-max_age_hours,))
            
            updated = cursor.rowcount
            conn.commit()
        
        logger.info(f"Scheduled {updated} failed tasks for retry")
        return updated
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics"""
        with self.db_manager.get_connection() as conn:
            # Overall stats
            cursor = conn.execute("""
                SELECT 
                    status,
                    COUNT(*) as count
                FROM processing_tasks
                GROUP BY status
            """)
            
            status_counts = {row["status"]: row["count"] for row in cursor}
            
            # Recent performance
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as completed_count,
                    AVG(CAST((julianday(completed_at) - julianday(started_at)) * 86400 AS REAL)) as avg_duration_seconds
                FROM processing_tasks
                WHERE status = 'completed'
                AND completed_at > datetime('now', '-1 hour')
            """)
            
            recent = cursor.fetchone()
            
            # Failed tasks
            cursor = conn.execute("""
                SELECT 
                    error_message,
                    COUNT(*) as count
                FROM processing_tasks
                WHERE status = 'failed'
                AND completed_at > datetime('now', '-24 hours')
                GROUP BY error_message
                ORDER BY count DESC
                LIMIT 10
            """)
            
            top_errors = [
                {"error": row["error_message"], "count": row["count"]}
                for row in cursor
            ]
            
            return {
                "status_counts": status_counts,
                "recent_performance": {
                    "completed_last_hour": recent["completed_count"] or 0,
                    "avg_duration_seconds": recent["avg_duration_seconds"] or 0
                },
                "top_errors": top_errors,
                "timestamp": datetime.now().isoformat()
            }