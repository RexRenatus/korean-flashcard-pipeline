"""Ordered results collector for maintaining order in concurrent processing"""

import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result from processing a single vocabulary item"""
    position: int
    term: str
    flashcard_data: Optional[str] = None
    error: Optional[str] = None
    from_cache: bool = False
    processing_time_ms: float = 0.0
    
    @property
    def is_success(self) -> bool:
        return self.error is None and self.flashcard_data is not None


class OrderedResultsCollector:
    """Maintains order of results despite concurrent processing"""
    
    def __init__(self):
        self.results: Dict[int, ProcessingResult] = {}
        self.lock = asyncio.Lock()
        self.completion_event = asyncio.Event()
        self.expected_count = 0
        self._start_time = None
        self._completion_callbacks = []
    
    def set_expected_count(self, count: int):
        """Set the expected number of results"""
        self.expected_count = count
        self._start_time = asyncio.get_event_loop().time()
        logger.info(f"Expecting {count} results")
    
    async def add_result(self, position: int, result: ProcessingResult):
        """Add a result at the specified position"""
        async with self.lock:
            self.results[position] = result
            completed = len(self.results)
            
            logger.debug(f"Added result for position {position} ({completed}/{self.expected_count})")
            
            # Check if all results are collected
            if completed == self.expected_count:
                self.completion_event.set()
                await self._notify_completion()
    
    async def wait_for_all(self, timeout: float = 300.0) -> bool:
        """Wait for all results to be collected
        
        Returns:
            True if all results collected, False if timeout
        """
        try:
            await asyncio.wait_for(self.completion_event.wait(), timeout)
            return True
        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for results. Got {len(self.results)}/{self.expected_count}")
            return False
    
    def get_ordered_results(self) -> List[ProcessingResult]:
        """Get results in order by position"""
        if not self.results:
            return []
        
        # Sort by position to maintain order
        max_position = max(self.results.keys())
        ordered = []
        
        for i in range(1, max_position + 1):
            if i in self.results:
                ordered.append(self.results[i])
            else:
                # Handle missing positions
                logger.warning(f"Missing result for position {i}")
                ordered.append(ProcessingResult(
                    position=i,
                    term=f"missing_{i}",
                    error="Result not collected"
                ))
        
        return ordered
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get collection statistics"""
        successful = sum(1 for r in self.results.values() if r.is_success)
        failed = sum(1 for r in self.results.values() if not r.is_success)
        from_cache = sum(1 for r in self.results.values() if r.from_cache)
        
        total_time = 0.0
        if self._start_time:
            total_time = (asyncio.get_event_loop().time() - self._start_time) * 1000
        
        avg_time = 0.0
        if self.results:
            processing_times = [r.processing_time_ms for r in self.results.values() if r.processing_time_ms > 0]
            if processing_times:
                avg_time = sum(processing_times) / len(processing_times)
        
        return {
            "total_expected": self.expected_count,
            "total_collected": len(self.results),
            "successful": successful,
            "failed": failed,
            "from_cache": from_cache,
            "cache_hit_rate": (from_cache / len(self.results) * 100) if self.results else 0,
            "total_time_ms": total_time,
            "average_time_ms": avg_time,
            "missing_positions": [i for i in range(1, self.expected_count + 1) if i not in self.results]
        }
    
    def add_completion_callback(self, callback):
        """Add a callback to be called when all results are collected"""
        self._completion_callbacks.append(callback)
    
    async def _notify_completion(self):
        """Notify all completion callbacks"""
        stats = self.get_statistics()
        for callback in self._completion_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(stats)
                else:
                    callback(stats)
            except Exception as e:
                logger.error(f"Error in completion callback: {e}")
    
    def clear(self):
        """Clear all results and reset state"""
        self.results.clear()
        self.completion_event.clear()
        self.expected_count = 0
        self._start_time = None