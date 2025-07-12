#!/usr/bin/env python3
"""
Performance monitoring for hooks with threshold alerts.
Enhanced with notification system integration.
"""
import time
import json
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
import statistics
import logging
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from scripts.hooks.notification_manager import get_notification_manager, NotificationType, NotificationPriority
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False

class HookPerformanceMonitor:
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.thresholds = {
            'execution_time_p95': 10.0,
            'error_rate': 0.1,
            'timeout_rate': 0.05
        }
        self.logger = logging.getLogger(__name__)
        self.metrics_file = Path(".claude/logs/hook_metrics.json")
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize notification manager if available
        self.notification_manager = None
        if NOTIFICATIONS_AVAILABLE:
            self.notification_manager = get_notification_manager()
            self.logger.info("Notification system integrated with performance monitor")
        
    def record_execution(self, hook_id: str, execution_time: float, 
                        success: bool, timeout: bool = False):
        """Record hook execution metrics."""
        self.metrics[hook_id].append({
            'timestamp': datetime.now().isoformat(),
            'execution_time': execution_time,
            'success': success,
            'timeout': timeout
        })
        
        # Check for threshold violations
        self._check_thresholds(hook_id)
        
        # Persist metrics periodically
        if len(self.metrics[hook_id]) % 10 == 0:
            self._persist_metrics()
        
    def get_stats(self, hook_id: str) -> Dict[str, Any]:
        """Get performance statistics for a hook."""
        if hook_id not in self.metrics or not self.metrics[hook_id]:
            return {}
            
        executions = list(self.metrics[hook_id])
        execution_times = [e['execution_time'] for e in executions if e['success']]
        
        if not execution_times:
            return {}
            
        return {
            'count': len(executions),
            'success_rate': sum(1 for e in executions if e['success']) / len(executions),
            'timeout_rate': sum(1 for e in executions if e['timeout']) / len(executions),
            'execution_time': {
                'mean': statistics.mean(execution_times),
                'median': statistics.median(execution_times),
                'p95': self._percentile(execution_times, 95),
                'p99': self._percentile(execution_times, 99),
                'min': min(execution_times),
                'max': max(execution_times)
            }
        }
        
    def get_slow_hooks(self, threshold: float = 5.0) -> List[tuple]:
        """Get hooks that are consistently slow."""
        slow_hooks = []
        
        for hook_id in self.metrics:
            stats = self.get_stats(hook_id)
            if stats and stats['execution_time']['p95'] > threshold:
                slow_hooks.append((hook_id, stats['execution_time']['p95']))
                
        return sorted(slow_hooks, key=lambda x: x[1], reverse=True)
        
    def get_failing_hooks(self, threshold: float = 0.1) -> List[tuple]:
        """Get hooks with high failure rates."""
        failing_hooks = []
        
        for hook_id in self.metrics:
            stats = self.get_stats(hook_id)
            if stats and (1 - stats['success_rate']) > threshold:
                failing_hooks.append((hook_id, 1 - stats['success_rate']))
                
        return sorted(failing_hooks, key=lambda x: x[1], reverse=True)
        
    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics for external monitoring."""
        return {
            hook_id: self.get_stats(hook_id)
            for hook_id in self.metrics
        }
        
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile."""
        if not data:
            return 0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * percentile / 100
        f = int(k)
        c = k - f
        if f + 1 < len(sorted_data):
            return sorted_data[f] * (1 - c) + sorted_data[f + 1] * c
        return sorted_data[f]
        
    def _check_thresholds(self, hook_id: str):
        """Check if hook violates performance thresholds."""
        stats = self.get_stats(hook_id)
        if not stats:
            return
            
        violations = []
        
        if stats['execution_time']['p95'] > self.thresholds['execution_time_p95']:
            violations.append(f"P95 execution time: {stats['execution_time']['p95']:.2f}s")
            
        if (1 - stats['success_rate']) > self.thresholds['error_rate']:
            violations.append(f"Error rate: {(1 - stats['success_rate']):.2%}")
            
        if stats['timeout_rate'] > self.thresholds['timeout_rate']:
            violations.append(f"Timeout rate: {stats['timeout_rate']:.2%}")
            
        if violations:
            self.logger.warning(f"Performance violations for {hook_id}: {', '.join(violations)}")
            
            # Send notification if available
            if self.notification_manager:
                self.notification_manager.notify_performance_violation(hook_id, violations)
            
    def _persist_metrics(self):
        """Save metrics to disk for persistence."""
        try:
            metrics_data = {
                hook_id: list(metrics)
                for hook_id, metrics in self.metrics.items()
            }
            with open(self.metrics_file, 'w') as f:
                json.dump(metrics_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to persist metrics: {e}")
            
    def load_metrics(self):
        """Load persisted metrics from disk."""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file) as f:
                    metrics_data = json.load(f)
                for hook_id, metrics in metrics_data.items():
                    self.metrics[hook_id] = deque(metrics, maxlen=self.window_size)
            except Exception as e:
                self.logger.error(f"Failed to load metrics: {e}")
                
    def generate_report(self) -> str:
        """Generate performance report."""
        report = ["Hook Performance Report", "=" * 50, ""]
        
        # Overall statistics
        all_metrics = self.export_metrics()
        if not all_metrics:
            return "No metrics available"
            
        # Slow hooks
        slow_hooks = self.get_slow_hooks()
        if slow_hooks:
            report.append("Slow Hooks (P95 > 5s):")
            for hook_id, p95 in slow_hooks:
                report.append(f"  - {hook_id}: {p95:.2f}s")
            report.append("")
            
        # Failing hooks
        failing_hooks = self.get_failing_hooks()
        if failing_hooks:
            report.append("Failing Hooks (Error Rate > 10%):")
            for hook_id, error_rate in failing_hooks:
                report.append(f"  - {hook_id}: {error_rate:.2%}")
            report.append("")
            
        # Detailed stats for each hook
        report.append("Detailed Statistics:")
        for hook_id, stats in all_metrics.items():
            if stats:
                report.append(f"\n{hook_id}:")
                report.append(f"  Executions: {stats['count']}")
                report.append(f"  Success Rate: {stats['success_rate']:.2%}")
                report.append(f"  Execution Time (ms):")
                report.append(f"    Mean: {stats['execution_time']['mean']*1000:.0f}")
                report.append(f"    P95: {stats['execution_time']['p95']*1000:.0f}")
                report.append(f"    Max: {stats['execution_time']['max']*1000:.0f}")
                
        return "\n".join(report)

# Global monitor instance
_monitor = None

def get_monitor() -> HookPerformanceMonitor:
    """Get global performance monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = HookPerformanceMonitor()
        _monitor.load_metrics()
    return _monitor

if __name__ == "__main__":
    # Test performance monitor
    logging.basicConfig(level=logging.INFO)
    monitor = HookPerformanceMonitor()
    
    # Simulate hook executions
    import random
    
    for i in range(50):
        hook_id = random.choice(["security_check", "syntax_check", "solid_check"])
        execution_time = random.uniform(0.1, 2.0)
        if hook_id == "solid_check":
            execution_time *= 3  # SOLID check is slower
        success = random.random() > 0.1  # 90% success rate
        timeout = execution_time > 10
        
        monitor.record_execution(hook_id, execution_time, success, timeout)
    
    # Print report
    print(monitor.generate_report())