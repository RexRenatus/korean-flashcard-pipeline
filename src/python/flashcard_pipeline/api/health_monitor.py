"""API Health Monitoring Service

Tracks API performance, manages alerts, and provides health reports.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path

from .database import ValidatedDatabaseManager
from .api_client_enhanced import EnhancedOpenRouterClient, ApiHealthStatus

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of alerts"""
    HIGH_ERROR_RATE = "high_error_rate"
    SLOW_RESPONSE = "slow_response"
    RATE_LIMIT_APPROACHING = "rate_limit_approaching"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    QUOTA_EXCEEDED = "quota_exceeded"
    CONSECUTIVE_FAILURES = "consecutive_failures"
    DEGRADED_PERFORMANCE = "degraded_performance"


@dataclass
class Alert:
    """Represents a health alert"""
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "acknowledged": self.acknowledged,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by
        }


@dataclass
class HealthThresholds:
    """Configurable health thresholds"""
    error_rate_warning: float = 0.1  # 10%
    error_rate_critical: float = 0.25  # 25%
    latency_warning_ms: float = 3000  # 3 seconds
    latency_critical_ms: float = 10000  # 10 seconds
    consecutive_failures_warning: int = 5
    consecutive_failures_critical: int = 10
    rate_limit_warning_percent: float = 80  # 80% of limit
    rate_limit_critical_percent: float = 95  # 95% of limit
    quota_warning_percent: float = 75  # 75% of quota
    quota_critical_percent: float = 90  # 90% of quota


class ApiHealthMonitor:
    """Monitors API health and generates alerts"""
    
    def __init__(self, db_manager: ValidatedDatabaseManager,
                 api_client: EnhancedOpenRouterClient,
                 thresholds: Optional[HealthThresholds] = None,
                 alert_callbacks: Optional[List[Callable[[Alert], None]]] = None):
        self.db_manager = db_manager
        self.api_client = api_client
        self.thresholds = thresholds or HealthThresholds()
        self.alert_callbacks = alert_callbacks or []
        
        # Alert management
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        self._max_history_size = 1000
        
        # Monitoring state
        self._last_check = datetime.now()
        self._monitoring_enabled = True
        self._check_interval = 60  # seconds
        
        # Cost tracking
        self._daily_costs: Dict[str, float] = {}
        self._monthly_budget = float(os.environ.get('OPENROUTER_MONTHLY_BUDGET', '100.0'))
        
        # Initialize database tables
        self._init_database()
    
    def _init_database(self):
        """Initialize health monitoring tables"""
        with self.db_manager.db_manager.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_health_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL,
                    success_rate REAL,
                    error_rate REAL,
                    average_latency_ms REAL,
                    consecutive_failures INTEGER,
                    total_requests INTEGER,
                    successful_requests INTEGER,
                    failed_requests INTEGER,
                    cache_hits INTEGER,
                    total_tokens INTEGER,
                    total_cost REAL,
                    details TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT UNIQUE NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    acknowledged BOOLEAN DEFAULT 0,
                    acknowledged_at TIMESTAMP,
                    acknowledged_by TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_cost_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    stage INTEGER,
                    tokens_used INTEGER,
                    requests_made INTEGER,
                    cost REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, stage)
                )
            """)
            
            conn.commit()
    
    async def start_monitoring(self):
        """Start continuous health monitoring"""
        logger.info("Starting API health monitoring")
        self._monitoring_enabled = True
        
        while self._monitoring_enabled:
            try:
                await self.check_health()
                await asyncio.sleep(self._check_interval)
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(self._check_interval)
    
    def stop_monitoring(self):
        """Stop health monitoring"""
        logger.info("Stopping API health monitoring")
        self._monitoring_enabled = False
    
    async def check_health(self) -> Dict[str, Any]:
        """Perform health check and generate alerts"""
        # Get current health metrics
        health_metrics = await self.api_client.get_health_status()
        stats = self.api_client.get_stats()
        
        # Store health check
        self._store_health_check(health_metrics, stats)
        
        # Check for alert conditions
        await self._check_error_rate(health_metrics, stats)
        await self._check_latency(health_metrics)
        await self._check_consecutive_failures(health_metrics)
        await self._check_rate_limits()
        await self._check_quota_usage(stats)
        await self._check_circuit_breaker()
        
        # Update last check time
        self._last_check = datetime.now()
        
        return {
            "status": health_metrics.status.value,
            "metrics": health_metrics.to_dict(),
            "stats": stats,
            "active_alerts": len(self._active_alerts),
            "last_check": self._last_check.isoformat()
        }
    
    def _store_health_check(self, health_metrics, stats):
        """Store health check in database"""
        with self.db_manager.db_manager.get_connection() as conn:
            conn.execute("""
                INSERT INTO api_health_checks (
                    status, success_rate, error_rate, average_latency_ms,
                    consecutive_failures, total_requests, successful_requests,
                    failed_requests, cache_hits, total_tokens, total_cost, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                health_metrics.status.value,
                health_metrics.success_rate,
                health_metrics.error_rate,
                health_metrics.average_latency_ms,
                health_metrics.consecutive_failures,
                stats.get("total_requests", 0),
                stats.get("successful_requests", 0),
                stats.get("failed_requests", 0),
                stats.get("cache_hits", 0),
                stats.get("total_tokens", 0),
                stats.get("total_cost", 0),
                json.dumps({"health": health_metrics.to_dict(), "stats": stats})
            ))
            conn.commit()
    
    async def _check_error_rate(self, health_metrics, stats):
        """Check error rate and generate alerts"""
        error_rate = health_metrics.error_rate
        
        if error_rate >= self.thresholds.error_rate_critical:
            await self._create_alert(
                AlertType.HIGH_ERROR_RATE,
                AlertSeverity.CRITICAL,
                f"Critical error rate: {error_rate:.1%}",
                {"error_rate": error_rate, "threshold": self.thresholds.error_rate_critical}
            )
        elif error_rate >= self.thresholds.error_rate_warning:
            await self._create_alert(
                AlertType.HIGH_ERROR_RATE,
                AlertSeverity.WARNING,
                f"High error rate: {error_rate:.1%}",
                {"error_rate": error_rate, "threshold": self.thresholds.error_rate_warning}
            )
        else:
            # Clear error rate alerts if back to normal
            self._clear_alert_type(AlertType.HIGH_ERROR_RATE)
    
    async def _check_latency(self, health_metrics):
        """Check response latency and generate alerts"""
        latency = health_metrics.average_latency_ms
        
        if latency >= self.thresholds.latency_critical_ms:
            await self._create_alert(
                AlertType.SLOW_RESPONSE,
                AlertSeverity.CRITICAL,
                f"Critical response latency: {latency:.0f}ms",
                {"latency_ms": latency, "threshold": self.thresholds.latency_critical_ms}
            )
        elif latency >= self.thresholds.latency_warning_ms:
            await self._create_alert(
                AlertType.SLOW_RESPONSE,
                AlertSeverity.WARNING,
                f"High response latency: {latency:.0f}ms",
                {"latency_ms": latency, "threshold": self.thresholds.latency_warning_ms}
            )
        else:
            self._clear_alert_type(AlertType.SLOW_RESPONSE)
    
    async def _check_consecutive_failures(self, health_metrics):
        """Check consecutive failures and generate alerts"""
        failures = health_metrics.consecutive_failures
        
        if failures >= self.thresholds.consecutive_failures_critical:
            await self._create_alert(
                AlertType.CONSECUTIVE_FAILURES,
                AlertSeverity.CRITICAL,
                f"Critical: {failures} consecutive failures",
                {"failures": failures, "threshold": self.thresholds.consecutive_failures_critical}
            )
        elif failures >= self.thresholds.consecutive_failures_warning:
            await self._create_alert(
                AlertType.CONSECUTIVE_FAILURES,
                AlertSeverity.WARNING,
                f"Warning: {failures} consecutive failures",
                {"failures": failures, "threshold": self.thresholds.consecutive_failures_warning}
            )
        else:
            self._clear_alert_type(AlertType.CONSECUTIVE_FAILURES)
    
    async def _check_rate_limits(self):
        """Check API rate limits and generate alerts"""
        rate_limit_info = await self.api_client.check_rate_limit()
        
        if not rate_limit_info:
            return
        
        usage_percent = ((rate_limit_info.limit - rate_limit_info.remaining) / 
                        rate_limit_info.limit * 100) if rate_limit_info.limit > 0 else 0
        
        if usage_percent >= self.thresholds.rate_limit_critical_percent:
            await self._create_alert(
                AlertType.RATE_LIMIT_APPROACHING,
                AlertSeverity.CRITICAL,
                f"Critical: Rate limit {usage_percent:.0f}% used",
                {
                    "usage_percent": usage_percent,
                    "remaining": rate_limit_info.remaining,
                    "limit": rate_limit_info.limit,
                    "reset_at": rate_limit_info.reset_at.isoformat()
                }
            )
        elif usage_percent >= self.thresholds.rate_limit_warning_percent:
            await self._create_alert(
                AlertType.RATE_LIMIT_APPROACHING,
                AlertSeverity.WARNING,
                f"Warning: Rate limit {usage_percent:.0f}% used",
                {
                    "usage_percent": usage_percent,
                    "remaining": rate_limit_info.remaining,
                    "limit": rate_limit_info.limit,
                    "reset_at": rate_limit_info.reset_at.isoformat()
                }
            )
        else:
            self._clear_alert_type(AlertType.RATE_LIMIT_APPROACHING)
    
    async def _check_quota_usage(self, stats):
        """Check cost quota usage and generate alerts"""
        # Update daily cost tracking
        today = datetime.now().date()
        self._daily_costs[str(today)] = stats.get("total_cost", 0)
        
        # Calculate monthly cost
        current_month = datetime.now().replace(day=1).date()
        monthly_cost = sum(
            cost for date_str, cost in self._daily_costs.items()
            if datetime.fromisoformat(date_str).date() >= current_month
        )
        
        # Store cost tracking
        self._store_cost_tracking(stats)
        
        # Check against budget
        if self._monthly_budget > 0:
            usage_percent = (monthly_cost / self._monthly_budget) * 100
            
            if usage_percent >= self.thresholds.quota_critical_percent:
                await self._create_alert(
                    AlertType.QUOTA_EXCEEDED,
                    AlertSeverity.CRITICAL,
                    f"Critical: Monthly budget {usage_percent:.0f}% used (${monthly_cost:.2f}/${self._monthly_budget:.2f})",
                    {
                        "monthly_cost": monthly_cost,
                        "monthly_budget": self._monthly_budget,
                        "usage_percent": usage_percent
                    }
                )
            elif usage_percent >= self.thresholds.quota_warning_percent:
                await self._create_alert(
                    AlertType.QUOTA_EXCEEDED,
                    AlertSeverity.WARNING,
                    f"Warning: Monthly budget {usage_percent:.0f}% used (${monthly_cost:.2f}/${self._monthly_budget:.2f})",
                    {
                        "monthly_cost": monthly_cost,
                        "monthly_budget": self._monthly_budget,
                        "usage_percent": usage_percent
                    }
                )
            else:
                self._clear_alert_type(AlertType.QUOTA_EXCEEDED)
    
    def _store_cost_tracking(self, stats):
        """Store cost tracking data"""
        today = datetime.now().date()
        
        with self.db_manager.db_manager.get_connection() as conn:
            # Update or insert cost tracking
            conn.execute("""
                INSERT OR REPLACE INTO api_cost_tracking (
                    date, stage, tokens_used, requests_made, cost
                ) VALUES (?, 0, ?, ?, ?)
            """, (
                today,
                stats.get("total_tokens", 0),
                stats.get("total_requests", 0),
                stats.get("total_cost", 0)
            ))
            conn.commit()
    
    async def _check_circuit_breaker(self):
        """Check circuit breaker status"""
        # This would check the actual circuit breaker status
        # For now, we'll clear any existing circuit breaker alerts
        self._clear_alert_type(AlertType.CIRCUIT_BREAKER_OPEN)
    
    async def _create_alert(self, alert_type: AlertType, severity: AlertSeverity,
                          message: str, details: Dict[str, Any]):
        """Create or update an alert"""
        alert_id = f"{alert_type.value}_{severity.value}"
        
        # Check if alert already exists
        if alert_id in self._active_alerts:
            # Update existing alert
            alert = self._active_alerts[alert_id]
            alert.details = details
            alert.timestamp = datetime.now()
        else:
            # Create new alert
            alert = Alert(
                alert_id=alert_id,
                alert_type=alert_type,
                severity=severity,
                message=message,
                details=details
            )
            
            self._active_alerts[alert_id] = alert
            self._alert_history.append(alert)
            
            # Trim history
            if len(self._alert_history) > self._max_history_size:
                self._alert_history = self._alert_history[-self._max_history_size:]
            
            # Store in database
            self._store_alert(alert)
            
            # Trigger callbacks
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")
            
            logger.warning(f"Alert created: {alert.message}")
    
    def _store_alert(self, alert: Alert):
        """Store alert in database"""
        with self.db_manager.db_manager.get_connection() as conn:
            conn.execute("""
                INSERT INTO api_alerts (
                    alert_id, alert_type, severity, message, details
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                alert.alert_id,
                alert.alert_type.value,
                alert.severity.value,
                alert.message,
                json.dumps(alert.details)
            ))
            conn.commit()
    
    def _clear_alert_type(self, alert_type: AlertType):
        """Clear all alerts of a specific type"""
        alerts_to_remove = [
            alert_id for alert_id, alert in self._active_alerts.items()
            if alert.alert_type == alert_type
        ]
        
        for alert_id in alerts_to_remove:
            del self._active_alerts[alert_id]
            logger.info(f"Alert cleared: {alert_id}")
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system"):
        """Acknowledge an alert"""
        if alert_id in self._active_alerts:
            alert = self._active_alerts[alert_id]
            alert.acknowledged = True
            alert.acknowledged_at = datetime.now()
            alert.acknowledged_by = acknowledged_by
            
            # Update database
            with self.db_manager.db_manager.get_connection() as conn:
                conn.execute("""
                    UPDATE api_alerts
                    SET acknowledged = 1, acknowledged_at = ?, acknowledged_by = ?
                    WHERE alert_id = ?
                """, (alert.acknowledged_at, acknowledged_by, alert_id))
                conn.commit()
            
            logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return list(self._active_alerts.values())
    
    def get_health_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get health check history"""
        since = datetime.now() - timedelta(hours=hours)
        
        with self.db_manager.db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM api_health_checks
                WHERE check_time > ?
                ORDER BY check_time DESC
            """, (since,))
            
            return [dict(row) for row in cursor]
    
    def get_cost_report(self, days: int = 30) -> Dict[str, Any]:
        """Get cost report for specified period"""
        since = datetime.now().date() - timedelta(days=days)
        
        with self.db_manager.db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    date,
                    SUM(tokens_used) as total_tokens,
                    SUM(requests_made) as total_requests,
                    SUM(cost) as total_cost
                FROM api_cost_tracking
                WHERE date >= ?
                GROUP BY date
                ORDER BY date DESC
            """, (since,))
            
            daily_costs = [dict(row) for row in cursor]
            
            # Calculate totals
            total_cost = sum(day["total_cost"] for day in daily_costs)
            total_tokens = sum(day["total_tokens"] for day in daily_costs)
            total_requests = sum(day["total_requests"] for day in daily_costs)
            
            return {
                "period_days": days,
                "total_cost": total_cost,
                "total_tokens": total_tokens,
                "total_requests": total_requests,
                "average_daily_cost": total_cost / days if days > 0 else 0,
                "daily_breakdown": daily_costs,
                "monthly_budget": self._monthly_budget,
                "budget_remaining": max(0, self._monthly_budget - total_cost)
            }
    
    def set_thresholds(self, thresholds: HealthThresholds):
        """Update monitoring thresholds"""
        self.thresholds = thresholds
        logger.info("Health monitoring thresholds updated")
    
    def add_alert_callback(self, callback: Callable[[Alert], None]):
        """Add a callback for alert notifications"""
        self.alert_callbacks.append(callback)
    
    async def generate_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        # Current health
        current_health = await self.check_health()
        
        # Historical data
        history_24h = self.get_health_history(24)
        history_7d = self.get_health_history(24 * 7)
        
        # Cost analysis
        cost_30d = self.get_cost_report(30)
        
        # Alert summary
        active_alerts = self.get_active_alerts()
        recent_alerts = self._alert_history[-20:]  # Last 20 alerts
        
        return {
            "report_time": datetime.now().isoformat(),
            "current_status": current_health,
            "health_trends": {
                "last_24h": self._calculate_trends(history_24h),
                "last_7d": self._calculate_trends(history_7d)
            },
            "cost_analysis": cost_30d,
            "alerts": {
                "active": [alert.to_dict() for alert in active_alerts],
                "recent": [alert.to_dict() for alert in recent_alerts]
            },
            "recommendations": self._generate_recommendations(current_health, cost_30d)
        }
    
    def _calculate_trends(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate trends from historical data"""
        if not history:
            return {}
        
        # Calculate averages and trends
        success_rates = [h["success_rate"] for h in history if h["success_rate"] is not None]
        latencies = [h["average_latency_ms"] for h in history if h["average_latency_ms"] is not None]
        
        return {
            "average_success_rate": sum(success_rates) / len(success_rates) if success_rates else 0,
            "average_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "total_requests": sum(h["total_requests"] for h in history),
            "total_failures": sum(h["failed_requests"] for h in history),
            "cache_hit_rate": (
                sum(h["cache_hits"] for h in history) / 
                sum(h["total_requests"] + h["cache_hits"] for h in history)
                if sum(h["total_requests"] for h in history) > 0 else 0
            )
        }
    
    def _generate_recommendations(self, current_health: Dict[str, Any],
                                cost_report: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on current state"""
        recommendations = []
        
        # Check error rate
        if current_health["metrics"]["error_rate"] > 0.1:
            recommendations.append("High error rate detected. Consider implementing retry logic or checking API status.")
        
        # Check latency
        if current_health["metrics"]["average_latency_ms"] > 3000:
            recommendations.append("High latency detected. Consider optimizing request payloads or using caching.")
        
        # Check cost
        if cost_report["budget_remaining"] < cost_report["monthly_budget"] * 0.2:
            recommendations.append("Monthly budget nearly exhausted. Consider reducing API usage or increasing budget.")
        
        # Check cache usage
        cache_hit_rate = current_health["stats"].get("cache_hit_rate", 0)
        if cache_hit_rate < 0.3:
            recommendations.append("Low cache hit rate. Consider pre-warming cache or adjusting cache TTL.")
        
        return recommendations