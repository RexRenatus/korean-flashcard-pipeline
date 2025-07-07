"""Monitoring and metrics for concurrent processing"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict
import json
import logging
from pathlib import Path
import aiosqlite

logger = logging.getLogger(__name__)


class ConcurrentProcessingMonitor:
    """Monitor concurrent processing performance"""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize monitor
        
        Args:
            db_path: Optional database path for persisting metrics
        """
        self.db_path = db_path
        self.metrics = defaultdict(int)
        self.timings = defaultdict(list)
        self.batch_metrics = {}
        self._lock = asyncio.Lock()
        
        # Real-time metrics
        self.current_batch_id = None
        self.current_batch_start = None
        self.concurrent_high_water_mark = 0
        
        logger.info("Concurrent processing monitor initialized")
    
    async def start_batch(self, batch_id: str, total_items: int, max_concurrent: int):
        """Record batch start"""
        async with self._lock:
            self.current_batch_id = batch_id
            self.current_batch_start = datetime.utcnow()
            
            self.batch_metrics[batch_id] = {
                "batch_id": batch_id,
                "total_items": total_items,
                "max_concurrent": max_concurrent,
                "start_time": self.current_batch_start,
                "concurrent_high_water_mark": 0,
                "rate_limit_hits": 0,
                "circuit_breaker_trips": 0,
                "cache_hits": 0,
                "total_requests": 0,
                "successful_items": 0,
                "failed_items": 0
            }
        
        logger.info(f"Started monitoring batch {batch_id} ({total_items} items, max {max_concurrent} concurrent)")
    
    async def record_concurrent_count(self, count: int):
        """Record current concurrent processing count"""
        async with self._lock:
            self.concurrent_high_water_mark = max(self.concurrent_high_water_mark, count)
            
            if self.current_batch_id and self.current_batch_id in self.batch_metrics:
                current_max = self.batch_metrics[self.current_batch_id]["concurrent_high_water_mark"]
                self.batch_metrics[self.current_batch_id]["concurrent_high_water_mark"] = max(current_max, count)
    
    async def record_rate_limit_hit(self):
        """Record a rate limit hit"""
        async with self._lock:
            self.metrics["total_rate_limit_hits"] += 1
            
            if self.current_batch_id and self.current_batch_id in self.batch_metrics:
                self.batch_metrics[self.current_batch_id]["rate_limit_hits"] += 1
    
    async def record_circuit_breaker_trip(self):
        """Record a circuit breaker trip"""
        async with self._lock:
            self.metrics["total_circuit_breaker_trips"] += 1
            
            if self.current_batch_id and self.current_batch_id in self.batch_metrics:
                self.batch_metrics[self.current_batch_id]["circuit_breaker_trips"] += 1
    
    async def record_cache_hit(self):
        """Record a cache hit"""
        async with self._lock:
            self.metrics["total_cache_hits"] += 1
            
            if self.current_batch_id and self.current_batch_id in self.batch_metrics:
                self.batch_metrics[self.current_batch_id]["cache_hits"] += 1
    
    async def record_item_processing(self, position: int, success: bool, 
                                   processing_time_ms: float, from_cache: bool = False):
        """Record individual item processing"""
        async with self._lock:
            # Update global metrics
            self.metrics["total_items_processed"] += 1
            if success:
                self.metrics["total_successful"] += 1
            else:
                self.metrics["total_failed"] += 1
            
            if from_cache:
                await self.record_cache_hit()
            
            # Record timing
            self.timings["processing_times_ms"].append(processing_time_ms)
            
            # Update batch metrics
            if self.current_batch_id and self.current_batch_id in self.batch_metrics:
                batch = self.batch_metrics[self.current_batch_id]
                batch["total_requests"] += 1
                if success:
                    batch["successful_items"] += 1
                else:
                    batch["failed_items"] += 1
    
    async def end_batch(self, batch_id: str, stats: Dict[str, Any]):
        """Record batch completion"""
        async with self._lock:
            if batch_id in self.batch_metrics:
                batch = self.batch_metrics[batch_id]
                batch["end_time"] = datetime.utcnow()
                batch["total_duration_ms"] = (
                    (batch["end_time"] - batch["start_time"]).total_seconds() * 1000
                )
                
                # Calculate derived metrics
                if batch["total_items"] > 0:
                    batch["success_rate"] = batch["successful_items"] / batch["total_items"] * 100
                    batch["cache_hit_rate"] = batch["cache_hits"] / batch["total_items"] * 100
                    batch["average_item_duration_ms"] = batch["total_duration_ms"] / batch["total_items"]
                
                # Add stats from orchestrator
                batch.update(stats)
                
                # Persist to database if configured
                if self.db_path:
                    await self._save_to_database(batch)
        
        logger.info(f"Completed monitoring batch {batch_id}")
    
    async def _save_to_database(self, batch_metrics: Dict[str, Any]):
        """Save batch metrics to database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO concurrent_processing_metrics (
                        batch_id, timestamp, concurrent_count, total_duration_ms,
                        average_item_duration_ms, rate_limit_hits, circuit_breaker_trips,
                        cache_hit_rate
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    batch_metrics["batch_id"],
                    batch_metrics["start_time"].isoformat(),
                    batch_metrics.get("concurrent_high_water_mark", 0),
                    batch_metrics.get("total_duration_ms", 0),
                    batch_metrics.get("average_item_duration_ms", 0),
                    batch_metrics.get("rate_limit_hits", 0),
                    batch_metrics.get("circuit_breaker_trips", 0),
                    batch_metrics.get("cache_hit_rate", 0)
                ))
                await db.commit()
                
        except Exception as e:
            logger.error(f"Failed to save metrics to database: {e}")
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current monitoring statistics"""
        stats = {
            "global_metrics": dict(self.metrics),
            "concurrent_high_water_mark": self.concurrent_high_water_mark,
            "average_processing_time_ms": 0.0,
            "total_batches": len(self.batch_metrics)
        }
        
        # Calculate average processing time
        if self.timings["processing_times_ms"]:
            stats["average_processing_time_ms"] = (
                sum(self.timings["processing_times_ms"]) / 
                len(self.timings["processing_times_ms"])
            )
        
        # Add current batch info if available
        if self.current_batch_id and self.current_batch_id in self.batch_metrics:
            stats["current_batch"] = {
                "batch_id": self.current_batch_id,
                "progress": self.batch_metrics[self.current_batch_id]
            }
        
        return stats
    
    def get_batch_summary(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get summary for a specific batch"""
        return self.batch_metrics.get(batch_id)
    
    async def export_metrics(self, output_path: Path):
        """Export all metrics to JSON file"""
        async with self._lock:
            metrics_data = {
                "export_time": datetime.utcnow().isoformat(),
                "global_metrics": dict(self.metrics),
                "batch_metrics": {
                    bid: {k: v.isoformat() if isinstance(v, datetime) else v 
                          for k, v in batch.items()}
                    for bid, batch in self.batch_metrics.items()
                },
                "statistics": self.get_current_stats()
            }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metrics_data, f, indent=2)
        
        logger.info(f"Exported metrics to {output_path}")
    
    def get_performance_report(self) -> str:
        """Generate a human-readable performance report"""
        stats = self.get_current_stats()
        
        report_lines = [
            "=== Concurrent Processing Performance Report ===",
            f"Total Batches Processed: {stats['total_batches']}",
            f"Total Items Processed: {stats['global_metrics'].get('total_items_processed', 0)}",
            f"Success Rate: {stats['global_metrics'].get('total_successful', 0) / max(stats['global_metrics'].get('total_items_processed', 1), 1) * 100:.1f}%",
            f"Average Processing Time: {stats['average_processing_time_ms']:.0f}ms",
            f"Max Concurrent Processing: {stats['concurrent_high_water_mark']}",
            f"Total Cache Hits: {stats['global_metrics'].get('total_cache_hits', 0)}",
            f"Total Rate Limit Hits: {stats['global_metrics'].get('total_rate_limit_hits', 0)}",
            f"Total Circuit Breaker Trips: {stats['global_metrics'].get('total_circuit_breaker_trips', 0)}",
        ]
        
        # Add recent batch summaries
        recent_batches = sorted(
            self.batch_metrics.items(),
            key=lambda x: x[1].get("start_time", datetime.min),
            reverse=True
        )[:5]
        
        if recent_batches:
            report_lines.append("\n=== Recent Batches ===")
            for batch_id, batch in recent_batches:
                report_lines.append(
                    f"- {batch_id}: {batch.get('successful_items', 0)}/{batch.get('total_items', 0)} items, "
                    f"{batch.get('total_duration_ms', 0):.0f}ms, "
                    f"{batch.get('cache_hit_rate', 0):.1f}% cache hits"
                )
        
        return "\n".join(report_lines)