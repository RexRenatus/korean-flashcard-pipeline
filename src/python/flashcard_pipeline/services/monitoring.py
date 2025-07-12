"""Monitoring service for system health and performance tracking"""

import asyncio
import json
import logging
import os
import psutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from ..core.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """System health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Health check result"""
    component: str
    status: HealthStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    checked_at: datetime = None
    
    def __post_init__(self):
        if self.checked_at is None:
            self.checked_at = datetime.now()


@dataclass
class PerformanceMetrics:
    """System performance metrics"""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    active_connections: int
    cache_hit_rate: float
    api_latency_ms: float
    processing_rate: float  # items per second
    error_rate: float
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class MonitoringService:
    """Service for monitoring system health and performance"""
    
    def __init__(
        self,
        db_manager=None,
        cache_service=None,
        api_client=None,
        metrics_dir: str = ".metrics",
        history_days: int = 7,
    ):
        self.db_manager = db_manager
        self.cache_service = cache_service
        self.api_client = api_client
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.history_days = history_days
        
        # Metrics storage
        self.current_metrics = PerformanceMetrics(
            cpu_percent=0, memory_percent=0, disk_usage_percent=0,
            active_connections=0, cache_hit_rate=0, api_latency_ms=0,
            processing_rate=0, error_rate=0
        )
        self.health_checks: List[HealthCheck] = []
        self.metrics_history: List[PerformanceMetrics] = []
        
        # Thresholds
        self.thresholds = {
            "cpu_warning": 70,
            "cpu_critical": 90,
            "memory_warning": 70,
            "memory_critical": 85,
            "disk_warning": 80,
            "disk_critical": 90,
            "error_rate_warning": 0.05,
            "error_rate_critical": 0.10,
            "api_latency_warning": 2000,
            "api_latency_critical": 5000,
        }
    
    async def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        checks = []
        
        # System checks
        checks.append(await self._check_system_resources())
        
        # Database health
        if self.db_manager:
            checks.append(await self._check_database())
        
        # Cache health
        if self.cache_service:
            checks.append(await self._check_cache())
        
        # API health
        if self.api_client:
            checks.append(await self._check_api())
        
        # Disk space
        checks.append(await self._check_disk_space())
        
        # Process health
        checks.append(await self._check_process())
        
        # Store health checks
        self.health_checks = checks
        
        # Determine overall status
        overall_status = HealthStatus.HEALTHY
        critical_count = sum(1 for c in checks if c.status == HealthStatus.CRITICAL)
        warning_count = sum(1 for c in checks if c.status == HealthStatus.WARNING)
        
        if critical_count > 0:
            overall_status = HealthStatus.CRITICAL
        elif warning_count > 0:
            overall_status = HealthStatus.WARNING
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "checks": [asdict(c) for c in checks],
            "summary": {
                "total_checks": len(checks),
                "healthy": sum(1 for c in checks if c.status == HealthStatus.HEALTHY),
                "warnings": warning_count,
                "critical": critical_count,
            }
        }
    
    async def collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics"""
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Process metrics
        process = psutil.Process(os.getpid())
        connections = len(process.connections())
        
        # Cache metrics
        cache_hit_rate = 0.0
        if self.cache_service:
            try:
                stats = await self.cache_service.get_stats()
                cache_hit_rate = stats.get("hit_rate", 0.0)
            except Exception as e:
                logger.error(f"Failed to get cache stats: {e}")
        
        # API metrics
        api_latency_ms = 0.0
        if self.api_client:
            try:
                stats = await self.api_client.get_stats()
                if stats.get("mode") == "advanced" and "health_metrics" in stats:
                    latencies = stats["health_metrics"].get("latency_ms", [])
                    if latencies:
                        api_latency_ms = sum(latencies) / len(latencies)
            except Exception as e:
                logger.error(f"Failed to get API stats: {e}")
        
        # Processing metrics (from database if available)
        processing_rate = 0.0
        error_rate = 0.0
        if self.db_manager:
            try:
                # Get processing stats from last hour
                stats = await self._get_processing_stats()
                processing_rate = stats.get("rate", 0.0)
                error_rate = stats.get("error_rate", 0.0)
            except Exception as e:
                logger.error(f"Failed to get processing stats: {e}")
        
        # Create metrics object
        metrics = PerformanceMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            disk_usage_percent=disk.percent,
            active_connections=connections,
            cache_hit_rate=cache_hit_rate,
            api_latency_ms=api_latency_ms,
            processing_rate=processing_rate,
            error_rate=error_rate,
        )
        
        # Update current metrics
        self.current_metrics = metrics
        
        # Add to history
        self.metrics_history.append(metrics)
        
        # Trim old history
        cutoff = datetime.now() - timedelta(days=self.history_days)
        self.metrics_history = [
            m for m in self.metrics_history
            if m.timestamp > cutoff
        ]
        
        return metrics
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of recent metrics"""
        if not self.metrics_history:
            await self.collect_metrics()
        
        # Calculate averages
        if self.metrics_history:
            avg_cpu = sum(m.cpu_percent for m in self.metrics_history) / len(self.metrics_history)
            avg_memory = sum(m.memory_percent for m in self.metrics_history) / len(self.metrics_history)
            avg_cache_hit = sum(m.cache_hit_rate for m in self.metrics_history) / len(self.metrics_history)
            avg_api_latency = sum(m.api_latency_ms for m in self.metrics_history) / len(self.metrics_history)
            
            # Find peaks
            peak_cpu = max(m.cpu_percent for m in self.metrics_history)
            peak_memory = max(m.memory_percent for m in self.metrics_history)
            peak_connections = max(m.active_connections for m in self.metrics_history)
        else:
            avg_cpu = avg_memory = avg_cache_hit = avg_api_latency = 0
            peak_cpu = peak_memory = peak_connections = 0
        
        return {
            "current": asdict(self.current_metrics),
            "averages": {
                "cpu_percent": round(avg_cpu, 2),
                "memory_percent": round(avg_memory, 2),
                "cache_hit_rate": round(avg_cache_hit, 3),
                "api_latency_ms": round(avg_api_latency, 2),
            },
            "peaks": {
                "cpu_percent": round(peak_cpu, 2),
                "memory_percent": round(peak_memory, 2),
                "active_connections": peak_connections,
            },
            "history_size": len(self.metrics_history),
            "history_period_hours": self.history_days * 24,
        }
    
    async def save_metrics(self) -> None:
        """Save metrics to file"""
        timestamp = datetime.now()
        filename = f"metrics_{timestamp.strftime('%Y%m%d')}.json"
        filepath = self.metrics_dir / filename
        
        # Prepare data
        data = {
            "timestamp": timestamp.isoformat(),
            "current_metrics": asdict(self.current_metrics),
            "health_checks": [asdict(c) for c in self.health_checks],
            "history": [asdict(m) for m in self.metrics_history[-100:]],  # Last 100 entries
        }
        
        # Write to file
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        # Clean old files
        cutoff = timestamp - timedelta(days=self.history_days * 2)
        for file in self.metrics_dir.glob("metrics_*.json"):
            try:
                date_str = file.stem.split('_')[1]
                file_date = datetime.strptime(date_str, '%Y%m%d')
                if file_date < cutoff:
                    file.unlink()
            except Exception as e:
                logger.error(f"Failed to clean old metrics file {file}: {e}")
    
    async def load_metrics(self) -> None:
        """Load metrics from files"""
        for file in sorted(self.metrics_dir.glob("metrics_*.json")):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                
                # Load history
                for m in data.get("history", []):
                    metrics = PerformanceMetrics(
                        cpu_percent=m["cpu_percent"],
                        memory_percent=m["memory_percent"],
                        disk_usage_percent=m["disk_usage_percent"],
                        active_connections=m["active_connections"],
                        cache_hit_rate=m["cache_hit_rate"],
                        api_latency_ms=m["api_latency_ms"],
                        processing_rate=m["processing_rate"],
                        error_rate=m["error_rate"],
                        timestamp=datetime.fromisoformat(m["timestamp"])
                    )
                    self.metrics_history.append(metrics)
                    
            except Exception as e:
                logger.error(f"Failed to load metrics from {file}: {e}")
        
        # Sort by timestamp
        self.metrics_history.sort(key=lambda m: m.timestamp)
    
    # Health check methods
    
    async def _check_system_resources(self) -> HealthCheck:
        """Check system resource usage"""
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        status = HealthStatus.HEALTHY
        issues = []
        
        if cpu >= self.thresholds["cpu_critical"]:
            status = HealthStatus.CRITICAL
            issues.append(f"CPU usage critical: {cpu}%")
        elif cpu >= self.thresholds["cpu_warning"]:
            status = HealthStatus.WARNING
            issues.append(f"CPU usage high: {cpu}%")
        
        if memory.percent >= self.thresholds["memory_critical"]:
            status = HealthStatus.CRITICAL
            issues.append(f"Memory usage critical: {memory.percent}%")
        elif memory.percent >= self.thresholds["memory_warning"]:
            status = HealthStatus.WARNING
            issues.append(f"Memory usage high: {memory.percent}%")
        
        message = "; ".join(issues) if issues else "System resources OK"
        
        return HealthCheck(
            component="system",
            status=status,
            message=message,
            details={
                "cpu_percent": cpu,
                "memory_percent": memory.percent,
                "memory_available_mb": memory.available / (1024 * 1024),
            }
        )
    
    async def _check_database(self) -> HealthCheck:
        """Check database health"""
        try:
            # Simple query to check connection
            result = self.db_manager.execute("SELECT 1").fetchone()
            
            # Check table existence
            tables = self.db_manager.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            
            status = HealthStatus.HEALTHY
            message = "Database connection OK"
            
            return HealthCheck(
                component="database",
                status=status,
                message=message,
                details={
                    "connected": True,
                    "table_count": len(tables),
                }
            )
            
        except Exception as e:
            return HealthCheck(
                component="database",
                status=HealthStatus.CRITICAL,
                message=f"Database error: {str(e)}",
                details={"connected": False}
            )
    
    async def _check_cache(self) -> HealthCheck:
        """Check cache service health"""
        try:
            stats = await self.cache_service.get_stats()
            hit_rate = stats.get("hit_rate", 0.0)
            
            status = HealthStatus.HEALTHY
            if hit_rate < 0.3:
                status = HealthStatus.WARNING
                message = f"Low cache hit rate: {hit_rate:.1%}"
            else:
                message = f"Cache hit rate: {hit_rate:.1%}"
            
            return HealthCheck(
                component="cache",
                status=status,
                message=message,
                details=stats
            )
            
        except Exception as e:
            return HealthCheck(
                component="cache",
                status=HealthStatus.WARNING,
                message=f"Cache error: {str(e)}",
                details={"available": False}
            )
    
    async def _check_api(self) -> HealthCheck:
        """Check API client health"""
        try:
            # Test connection
            connected = await self.api_client.test_connection()
            
            if not connected:
                return HealthCheck(
                    component="api",
                    status=HealthStatus.CRITICAL,
                    message="API connection failed",
                    details={"connected": False}
                )
            
            # Get stats
            stats = await self.api_client.get_stats()
            
            # Check error rate
            total_requests = stats.get("requests", 0)
            errors = stats.get("errors", 0)
            error_rate = errors / total_requests if total_requests > 0 else 0
            
            status = HealthStatus.HEALTHY
            message = "API connection OK"
            
            if error_rate >= self.thresholds["error_rate_critical"]:
                status = HealthStatus.CRITICAL
                message = f"High API error rate: {error_rate:.1%}"
            elif error_rate >= self.thresholds["error_rate_warning"]:
                status = HealthStatus.WARNING
                message = f"Elevated API error rate: {error_rate:.1%}"
            
            return HealthCheck(
                component="api",
                status=status,
                message=message,
                details={
                    "connected": True,
                    "error_rate": error_rate,
                    **stats
                }
            )
            
        except Exception as e:
            return HealthCheck(
                component="api",
                status=HealthStatus.CRITICAL,
                message=f"API check failed: {str(e)}",
                details={"connected": False}
            )
    
    async def _check_disk_space(self) -> HealthCheck:
        """Check disk space"""
        disk = psutil.disk_usage('/')
        
        status = HealthStatus.HEALTHY
        if disk.percent >= self.thresholds["disk_critical"]:
            status = HealthStatus.CRITICAL
            message = f"Disk space critical: {disk.percent}% used"
        elif disk.percent >= self.thresholds["disk_warning"]:
            status = HealthStatus.WARNING
            message = f"Disk space low: {disk.percent}% used"
        else:
            message = f"Disk space OK: {disk.percent}% used"
        
        return HealthCheck(
            component="disk",
            status=status,
            message=message,
            details={
                "percent_used": disk.percent,
                "free_gb": disk.free / (1024**3),
                "total_gb": disk.total / (1024**3),
            }
        )
    
    async def _check_process(self) -> HealthCheck:
        """Check current process health"""
        try:
            process = psutil.Process(os.getpid())
            
            # Get process info
            cpu_percent = process.cpu_percent()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            
            status = HealthStatus.HEALTHY
            message = "Process running normally"
            
            # Check for excessive memory usage
            if memory_mb > 1000:  # 1GB
                status = HealthStatus.WARNING
                message = f"High process memory usage: {memory_mb:.0f}MB"
            
            return HealthCheck(
                component="process",
                status=status,
                message=message,
                details={
                    "pid": process.pid,
                    "cpu_percent": cpu_percent,
                    "memory_mb": memory_mb,
                    "threads": process.num_threads(),
                    "open_files": len(process.open_files()),
                }
            )
            
        except Exception as e:
            return HealthCheck(
                component="process",
                status=HealthStatus.UNKNOWN,
                message=f"Process check failed: {str(e)}",
            )
    
    async def _get_processing_stats(self) -> Dict[str, float]:
        """Get processing statistics from database"""
        if not self.db_manager:
            return {"rate": 0.0, "error_rate": 0.0}
        
        try:
            # Get stats from last hour
            cutoff = (datetime.now() - timedelta(hours=1)).isoformat()
            
            # Total processed
            total = self.db_manager.execute(
                "SELECT COUNT(*) FROM vocabulary WHERE created_at > ?",
                (cutoff,)
            ).fetchone()[0]
            
            # Errors (items with error status)
            errors = self.db_manager.execute(
                "SELECT COUNT(*) FROM vocabulary WHERE created_at > ? AND status = 'error'",
                (cutoff,)
            ).fetchone()[0]
            
            # Calculate rates
            hours = 1.0
            rate = total / (hours * 3600)  # items per second
            error_rate = errors / total if total > 0 else 0.0
            
            return {"rate": rate, "error_rate": error_rate}
            
        except Exception as e:
            logger.error(f"Failed to get processing stats: {e}")
            return {"rate": 0.0, "error_rate": 0.0}
    
    def set_threshold(self, key: str, value: float) -> None:
        """Update a threshold value"""
        if key in self.thresholds:
            self.thresholds[key] = value
        else:
            raise ValueError(f"Unknown threshold: {key}")
    
    def get_thresholds(self) -> Dict[str, float]:
        """Get current thresholds"""
        return self.thresholds.copy()


# Factory function
def create_monitoring_service(**kwargs) -> MonitoringService:
    """Create monitoring service instance"""
    return MonitoringService(**kwargs)