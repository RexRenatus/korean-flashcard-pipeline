"""Concurrent progress tracking for batch processing"""

import asyncio
from typing import Set, Dict, Any, List, Callable, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ConcurrentProgressTracker:
    """Track progress of concurrent batch processing"""
    
    def __init__(self, total_items: int):
        """Initialize progress tracker
        
        Args:
            total_items: Total number of items to process
        """
        self.total = total_items
        self.completed = 0
        self.failed = 0
        self.in_progress: Set[int] = set()
        self.lock = asyncio.Lock()
        self.progress_callbacks: List[Callable] = []
        
        # Timing information
        self.start_time = datetime.utcnow()
        self.item_times: Dict[int, float] = {}
        
        # Detailed tracking
        self.successful_items: Set[int] = set()
        self.failed_items: Dict[int, str] = {}
        self.cached_items: Set[int] = set()
        
        logger.info(f"Progress tracker initialized for {total_items} items")
    
    async def start_item(self, item_id: int):
        """Mark an item as started"""
        async with self.lock:
            self.in_progress.add(item_id)
            self.item_times[item_id] = asyncio.get_event_loop().time()
            await self._notify_progress()
            
        logger.debug(f"Started processing item {item_id}")
    
    async def complete_item(self, item_id: int, success: bool = True, 
                          error_msg: Optional[str] = None, from_cache: bool = False):
        """Mark an item as completed
        
        Args:
            item_id: Item position/ID
            success: Whether processing was successful
            error_msg: Error message if failed
            from_cache: Whether result was from cache
        """
        async with self.lock:
            # Remove from in_progress
            self.in_progress.discard(item_id)
            
            # Calculate processing time
            if item_id in self.item_times:
                elapsed = asyncio.get_event_loop().time() - self.item_times[item_id]
                self.item_times[item_id] = elapsed * 1000  # Convert to ms
            
            # Update counters
            if success:
                self.completed += 1
                self.successful_items.add(item_id)
                if from_cache:
                    self.cached_items.add(item_id)
                logger.debug(f"Completed item {item_id} successfully (cache: {from_cache})")
            else:
                self.failed += 1
                self.failed_items[item_id] = error_msg or "Unknown error"
                logger.warning(f"Failed item {item_id}: {error_msg}")
            
            await self._notify_progress()
    
    async def _notify_progress(self):
        """Notify all registered callbacks of progress update"""
        stats = self.get_stats()
        
        for callback in self.progress_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(stats)
                else:
                    # Run sync callbacks in executor to avoid blocking
                    await asyncio.get_event_loop().run_in_executor(None, callback, stats)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current progress statistics"""
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()
        
        # Calculate rates
        completion_rate = self.completed / elapsed if elapsed > 0 else 0
        
        # Calculate ETA
        processed = self.completed + self.failed
        remaining = self.total - processed
        eta_seconds = remaining / completion_rate if completion_rate > 0 else 0
        
        # Calculate average processing time
        completed_times = [t for i, t in self.item_times.items() 
                          if i in self.successful_items and t > 0]
        avg_time_ms = sum(completed_times) / len(completed_times) if completed_times else 0
        
        return {
            "total": self.total,
            "completed": self.completed,
            "failed": self.failed,
            "in_progress": len(self.in_progress),
            "remaining": remaining,
            "progress_percent": (processed / self.total * 100) if self.total > 0 else 0,
            "success_rate": (self.completed / processed * 100) if processed > 0 else 100,
            "cache_hit_rate": (len(self.cached_items) / self.completed * 100) if self.completed > 0 else 0,
            "elapsed_seconds": elapsed,
            "completion_rate": completion_rate,
            "eta_seconds": eta_seconds,
            "average_time_ms": avg_time_ms,
            "concurrent_active": len(self.in_progress),
            "failed_items": list(self.failed_items.keys())[:10]  # First 10 failed
        }
    
    def add_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add a progress callback
        
        Args:
            callback: Function to call with stats dict on progress updates
        """
        self.progress_callbacks.append(callback)
        logger.debug(f"Added progress callback: {callback}")
    
    def remove_callback(self, callback: Callable):
        """Remove a progress callback"""
        if callback in self.progress_callbacks:
            self.progress_callbacks.remove(callback)
    
    def get_summary(self) -> str:
        """Get a formatted summary of progress"""
        stats = self.get_stats()
        
        summary_lines = [
            f"Progress: {stats['progress_percent']:.1f}% ({stats['completed'] + stats['failed']}/{stats['total']})",
            f"Success Rate: {stats['success_rate']:.1f}%",
            f"Cache Hit Rate: {stats['cache_hit_rate']:.1f}%",
            f"Average Time: {stats['average_time_ms']:.0f}ms per item",
            f"Completion Rate: {stats['completion_rate']:.1f} items/second",
        ]
        
        if stats['failed'] > 0:
            summary_lines.append(f"Failed Items: {stats['failed']} ({', '.join(map(str, stats['failed_items']))}...)")
        
        if stats['eta_seconds'] > 0:
            minutes = int(stats['eta_seconds'] / 60)
            seconds = int(stats['eta_seconds'] % 60)
            summary_lines.append(f"ETA: {minutes}m {seconds}s")
        
        return "\n".join(summary_lines)
    
    def reset(self, total_items: int):
        """Reset tracker for a new batch"""
        self.total = total_items
        self.completed = 0
        self.failed = 0
        self.in_progress.clear()
        self.start_time = datetime.utcnow()
        self.item_times.clear()
        self.successful_items.clear()
        self.failed_items.clear()
        self.cached_items.clear()
        
        logger.info(f"Progress tracker reset for {total_items} items")