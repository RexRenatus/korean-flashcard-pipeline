"""
Metrics collection system for flashcard pipeline monitoring.

This module provides comprehensive metrics collection for:
- API usage (calls, tokens, costs)
- Processing performance (duration, success rate)
- Cache performance (hit rate, size)
- Database performance
- Cost tracking with budget alerts
"""

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Deque, Union, Callable
import aiosqlite
from decimal import Decimal

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class MetricCategory(Enum):
    """Categories for organizing metrics."""
    API = "api"
    PROCESSING = "processing"
    CACHE = "cache"
    DATABASE = "database"
    COST = "cost"
    SYSTEM = "system"


@dataclass
class MetricPoint:
    """Single metric data point."""
    timestamp: datetime
    name: str
    value: float
    category: MetricCategory
    metric_type: MetricType
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertRule:
    """Alert rule configuration."""
    name: str
    metric_name: str
    threshold: float
    comparison: str  # "gt", "lt", "eq", "gte", "lte"
    window_minutes: int = 5
    cooldown_minutes: int = 15
    enabled: bool = True
    actions: List[str] = field(default_factory=list)  # ["log", "email", "webhook"]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CostBudget:
    """Cost budget configuration."""
    daily_limit: Decimal
    weekly_limit: Decimal
    monthly_limit: Decimal
    alert_thresholds: List[float] = field(default_factory=lambda: [0.5, 0.75, 0.9])
    enabled: bool = True


class MetricsCollector:
    """Main metrics collection system."""
    
    def __init__(self, db_path: Path, retention_days: int = 30):
        self.db_path = db_path
        self.retention_days = retention_days
        self._metrics_buffer: Deque[MetricPoint] = deque(maxlen=10000)
        self._aggregation_cache: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._alert_rules: Dict[str, AlertRule] = {}
        self._cost_budget: Optional[CostBudget] = None
        self._alert_history: Dict[str, datetime] = {}
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def initialize(self):
        """Initialize the metrics collector."""
        await self._create_tables()
        await self._load_alert_rules()
        await self._load_cost_budget()
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Metrics collector initialized")
        
    async def shutdown(self):
        """Shutdown the metrics collector."""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        await self._flush_metrics()
        logger.info("Metrics collector shutdown")
        
    async def _create_tables(self):
        """Create database tables for metrics storage."""
        async with aiosqlite.connect(str(self.db_path)) as db:
            # Time-series metrics table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    name TEXT NOT NULL,
                    value REAL NOT NULL,
                    category TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    tags TEXT,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Indexes for efficient querying
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp 
                ON metrics(timestamp)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_name_timestamp 
                ON metrics(name, timestamp)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_category_timestamp 
                ON metrics(category, timestamp)
            """)
            
            # Alert rules table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS alert_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    metric_name TEXT NOT NULL,
                    threshold REAL NOT NULL,
                    comparison TEXT NOT NULL,
                    window_minutes INTEGER DEFAULT 5,
                    cooldown_minutes INTEGER DEFAULT 15,
                    enabled BOOLEAN DEFAULT 1,
                    actions TEXT,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Cost budget table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS cost_budgets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    daily_limit DECIMAL(10,2) NOT NULL,
                    weekly_limit DECIMAL(10,2) NOT NULL,
                    monthly_limit DECIMAL(10,2) NOT NULL,
                    alert_thresholds TEXT,
                    enabled BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Alert history table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_name TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    threshold REAL NOT NULL,
                    triggered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    actions_taken TEXT,
                    metadata TEXT
                )
            """)
            
            await db.commit()
            
    # Core metric recording methods
    
    async def record_counter(self, name: str, value: float = 1.0, 
                           category: MetricCategory = MetricCategory.SYSTEM,
                           tags: Optional[Dict[str, str]] = None,
                           metadata: Optional[Dict[str, Any]] = None):
        """Record a counter metric (cumulative value)."""
        await self._record_metric(
            name=name,
            value=value,
            category=category,
            metric_type=MetricType.COUNTER,
            tags=tags or {},
            metadata=metadata or {}
        )
        
    async def record_gauge(self, name: str, value: float,
                         category: MetricCategory = MetricCategory.SYSTEM,
                         tags: Optional[Dict[str, str]] = None,
                         metadata: Optional[Dict[str, Any]] = None):
        """Record a gauge metric (point-in-time value)."""
        await self._record_metric(
            name=name,
            value=value,
            category=category,
            metric_type=MetricType.GAUGE,
            tags=tags or {},
            metadata=metadata or {}
        )
        
    async def record_timer(self, name: str, duration_ms: float,
                         category: MetricCategory = MetricCategory.SYSTEM,
                         tags: Optional[Dict[str, str]] = None,
                         metadata: Optional[Dict[str, Any]] = None):
        """Record a timer metric (duration in milliseconds)."""
        await self._record_metric(
            name=name,
            value=duration_ms,
            category=category,
            metric_type=MetricType.TIMER,
            tags=tags or {},
            metadata=metadata or {}
        )
        
    async def record_histogram(self, name: str, value: float,
                             category: MetricCategory = MetricCategory.SYSTEM,
                             tags: Optional[Dict[str, str]] = None,
                             metadata: Optional[Dict[str, Any]] = None):
        """Record a histogram metric (distribution of values)."""
        await self._record_metric(
            name=name,
            value=value,
            category=category,
            metric_type=MetricType.HISTOGRAM,
            tags=tags or {},
            metadata=metadata or {}
        )
        
    # Specialized metric recording methods
    
    async def record_api_call(self, model: str, tokens_used: int, 
                            cost: Decimal, duration_ms: float,
                            success: bool, error: Optional[str] = None):
        """Record API call metrics."""
        tags = {"model": model, "success": str(success)}
        
        # Record call count
        await self.record_counter(
            "api.calls.total",
            category=MetricCategory.API,
            tags=tags
        )
        
        # Record tokens
        await self.record_counter(
            "api.tokens.total",
            value=float(tokens_used),
            category=MetricCategory.API,
            tags=tags
        )
        
        # Record cost
        await self.record_counter(
            "api.cost.total",
            value=float(cost),
            category=MetricCategory.COST,
            tags=tags,
            metadata={"cost": str(cost), "tokens": tokens_used}
        )
        
        # Record duration
        await self.record_timer(
            "api.call.duration",
            duration_ms=duration_ms,
            category=MetricCategory.API,
            tags=tags
        )
        
        # Check cost budget
        await self._check_cost_budget(cost)
        
        if error:
            await self.record_counter(
                "api.errors.total",
                category=MetricCategory.API,
                tags={**tags, "error_type": error}
            )
            
    async def record_processing(self, word_count: int, duration_ms: float,
                              success: bool, stage: str, 
                              error: Optional[str] = None):
        """Record processing metrics."""
        tags = {"stage": stage, "success": str(success)}
        
        # Record processing count
        await self.record_counter(
            "processing.batches.total",
            category=MetricCategory.PROCESSING,
            tags=tags
        )
        
        # Record word count
        await self.record_counter(
            "processing.words.total",
            value=float(word_count),
            category=MetricCategory.PROCESSING,
            tags=tags
        )
        
        # Record duration
        await self.record_timer(
            "processing.duration",
            duration_ms=duration_ms,
            category=MetricCategory.PROCESSING,
            tags=tags
        )
        
        # Record throughput
        if duration_ms > 0:
            throughput = (word_count / duration_ms) * 1000  # words per second
            await self.record_gauge(
                "processing.throughput",
                value=throughput,
                category=MetricCategory.PROCESSING,
                tags=tags
            )
            
        if error:
            await self.record_counter(
                "processing.errors.total",
                category=MetricCategory.PROCESSING,
                tags={**tags, "error_type": error}
            )
            
    async def record_cache_operation(self, operation: str, hit: bool,
                                   size_bytes: Optional[int] = None):
        """Record cache operation metrics."""
        tags = {"operation": operation, "hit": str(hit)}
        
        # Record operation count
        await self.record_counter(
            "cache.operations.total",
            category=MetricCategory.CACHE,
            tags=tags
        )
        
        # Record hit/miss
        if hit:
            await self.record_counter(
                "cache.hits.total",
                category=MetricCategory.CACHE,
                tags={"operation": operation}
            )
        else:
            await self.record_counter(
                "cache.misses.total",
                category=MetricCategory.CACHE,
                tags={"operation": operation}
            )
            
        # Record size if provided
        if size_bytes is not None:
            await self.record_gauge(
                "cache.size.bytes",
                value=float(size_bytes),
                category=MetricCategory.CACHE
            )
            
    async def record_database_operation(self, operation: str, table: str,
                                      duration_ms: float, rows_affected: int = 0):
        """Record database operation metrics."""
        tags = {"operation": operation, "table": table}
        
        # Record operation count
        await self.record_counter(
            "database.operations.total",
            category=MetricCategory.DATABASE,
            tags=tags
        )
        
        # Record duration
        await self.record_timer(
            "database.operation.duration",
            duration_ms=duration_ms,
            category=MetricCategory.DATABASE,
            tags=tags
        )
        
        # Record rows affected
        if rows_affected > 0:
            await self.record_histogram(
                "database.rows.affected",
                value=float(rows_affected),
                category=MetricCategory.DATABASE,
                tags=tags
            )
            
    # Alert management
    
    async def add_alert_rule(self, rule: AlertRule):
        """Add or update an alert rule."""
        self._alert_rules[rule.name] = rule
        await self._save_alert_rule(rule)
        
    async def remove_alert_rule(self, name: str):
        """Remove an alert rule."""
        if name in self._alert_rules:
            del self._alert_rules[name]
            async with aiosqlite.connect(str(self.db_path)) as db:
                await db.execute("DELETE FROM alert_rules WHERE name = ?", (name,))
                await db.commit()
                
    async def set_cost_budget(self, budget: CostBudget):
        """Set cost budget configuration."""
        self._cost_budget = budget
        await self._save_cost_budget(budget)
        
    # Internal methods
    
    async def _record_metric(self, name: str, value: float,
                           category: MetricCategory, metric_type: MetricType,
                           tags: Dict[str, str], metadata: Dict[str, Any]):
        """Internal method to record a metric."""
        metric = MetricPoint(
            timestamp=datetime.utcnow(),
            name=name,
            value=value,
            category=category,
            metric_type=metric_type,
            tags=tags,
            metadata=metadata
        )
        
        self._metrics_buffer.append(metric)
        
        # Check alerts
        await self._check_alerts(metric)
        
        # Update aggregation cache
        self._update_aggregation_cache(metric)
        
    def _update_aggregation_cache(self, metric: MetricPoint):
        """Update in-memory aggregation cache for fast queries."""
        key = f"{metric.name}:{metric.category.value}"
        cache = self._aggregation_cache[key]
        
        # Initialize cache if needed
        if not cache:
            cache.update({
                "count": 0,
                "sum": 0.0,
                "min": float('inf'),
                "max": float('-inf'),
                "last_value": 0.0,
                "last_timestamp": None
            })
            
        # Update cache
        cache["count"] += 1
        cache["sum"] += metric.value
        cache["min"] = min(cache["min"], metric.value)
        cache["max"] = max(cache["max"], metric.value)
        cache["last_value"] = metric.value
        cache["last_timestamp"] = metric.timestamp
        
    async def _check_alerts(self, metric: MetricPoint):
        """Check if metric triggers any alerts."""
        for rule in self._alert_rules.values():
            if not rule.enabled or rule.metric_name != metric.name:
                continue
                
            # Check cooldown
            last_alert = self._alert_history.get(rule.name)
            if last_alert:
                cooldown_end = last_alert + timedelta(minutes=rule.cooldown_minutes)
                if datetime.utcnow() < cooldown_end:
                    continue
                    
            # Check threshold
            if self._evaluate_alert_condition(metric.value, rule.threshold, rule.comparison):
                await self._trigger_alert(rule, metric)
                
    def _evaluate_alert_condition(self, value: float, threshold: float, 
                                comparison: str) -> bool:
        """Evaluate alert condition."""
        comparisons = {
            "gt": value > threshold,
            "lt": value < threshold,
            "eq": value == threshold,
            "gte": value >= threshold,
            "lte": value <= threshold
        }
        return comparisons.get(comparison, False)
        
    async def _trigger_alert(self, rule: AlertRule, metric: MetricPoint):
        """Trigger an alert."""
        self._alert_history[rule.name] = datetime.utcnow()
        
        # Log alert
        logger.warning(
            f"Alert triggered: {rule.name} - {metric.name}={metric.value} "
            f"{rule.comparison} {rule.threshold}"
        )
        
        # Record alert in database
        async with aiosqlite.connect(str(self.db_path)) as db:
            await db.execute("""
                INSERT INTO alert_history 
                (alert_name, metric_name, metric_value, threshold, actions_taken, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                rule.name, metric.name, metric.value, rule.threshold,
                json.dumps(rule.actions), json.dumps(rule.metadata)
            ))
            await db.commit()
            
        # Execute alert actions
        for action in rule.actions:
            if action == "log":
                logger.critical(f"ALERT: {rule.name} - {rule.metadata}")
            # Add email, webhook, etc. implementations as needed
            
    async def _check_cost_budget(self, cost: Decimal):
        """Check if cost exceeds budget thresholds."""
        if not self._cost_budget or not self._cost_budget.enabled:
            return
            
        # Get current costs
        now = datetime.utcnow()
        daily_cost = await self.get_cost_sum(now - timedelta(days=1), now)
        weekly_cost = await self.get_cost_sum(now - timedelta(days=7), now)
        monthly_cost = await self.get_cost_sum(now - timedelta(days=30), now)
        
        # Check thresholds
        for threshold in self._cost_budget.alert_thresholds:
            if daily_cost > float(self._cost_budget.daily_limit) * threshold:
                await self._trigger_cost_alert(
                    "daily", daily_cost, self._cost_budget.daily_limit, threshold
                )
            if weekly_cost > float(self._cost_budget.weekly_limit) * threshold:
                await self._trigger_cost_alert(
                    "weekly", weekly_cost, self._cost_budget.weekly_limit, threshold
                )
            if monthly_cost > float(self._cost_budget.monthly_limit) * threshold:
                await self._trigger_cost_alert(
                    "monthly", monthly_cost, self._cost_budget.monthly_limit, threshold
                )
                
    async def _trigger_cost_alert(self, period: str, current: float, 
                                limit: Decimal, threshold: float):
        """Trigger a cost budget alert."""
        alert_name = f"cost_budget_{period}_{int(threshold * 100)}"
        
        # Check cooldown
        last_alert = self._alert_history.get(alert_name)
        if last_alert:
            cooldown_end = last_alert + timedelta(hours=1)
            if datetime.utcnow() < cooldown_end:
                return
                
        self._alert_history[alert_name] = datetime.utcnow()
        
        logger.warning(
            f"Cost budget alert: {period} cost ${current:.2f} "
            f"exceeds {threshold*100}% of limit ${limit}"
        )
        
    async def _flush_loop(self):
        """Background task to flush metrics to database."""
        while self._running:
            try:
                await asyncio.sleep(10)  # Flush every 10 seconds
                await self._flush_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in flush loop: {e}")
                
    async def _flush_metrics(self):
        """Flush buffered metrics to database."""
        if not self._metrics_buffer:
            return
            
        metrics_to_save = []
        while self._metrics_buffer:
            try:
                metric = self._metrics_buffer.popleft()
                metrics_to_save.append(metric)
            except IndexError:
                break
                
        if metrics_to_save:
            async with aiosqlite.connect(str(self.db_path)) as db:
                for metric in metrics_to_save:
                    await db.execute("""
                        INSERT INTO metrics 
                        (timestamp, name, value, category, metric_type, tags, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        metric.timestamp.isoformat(),
                        metric.name,
                        metric.value,
                        metric.category.value,
                        metric.metric_type.value,
                        json.dumps(metric.tags),
                        json.dumps(metric.metadata)
                    ))
                await db.commit()
                
    async def _cleanup_loop(self):
        """Background task to clean up old metrics."""
        while self._running:
            try:
                await asyncio.sleep(3600)  # Run hourly
                await self._cleanup_old_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                
    async def _cleanup_old_metrics(self):
        """Remove metrics older than retention period."""
        cutoff = datetime.utcnow() - timedelta(days=self.retention_days)
        
        async with aiosqlite.connect(str(self.db_path)) as db:
            await db.execute(
                "DELETE FROM metrics WHERE timestamp < ?",
                (cutoff.isoformat(),)
            )
            await db.commit()
            
    async def _load_alert_rules(self):
        """Load alert rules from database."""
        async with aiosqlite.connect(str(self.db_path)) as db:
            async with db.execute("SELECT * FROM alert_rules WHERE enabled = 1") as cursor:
                async for row in cursor:
                    rule = AlertRule(
                        name=row[1],
                        metric_name=row[2],
                        threshold=row[3],
                        comparison=row[4],
                        window_minutes=row[5],
                        cooldown_minutes=row[6],
                        enabled=bool(row[7]),
                        actions=json.loads(row[8]) if row[8] else [],
                        metadata=json.loads(row[9]) if row[9] else {}
                    )
                    self._alert_rules[rule.name] = rule
                    
    async def _load_cost_budget(self):
        """Load cost budget from database."""
        async with aiosqlite.connect(str(self.db_path)) as db:
            async with db.execute("SELECT * FROM cost_budgets ORDER BY id DESC LIMIT 1") as cursor:
                row = await cursor.fetchone()
                if row:
                    self._cost_budget = CostBudget(
                        daily_limit=Decimal(str(row[1])),
                        weekly_limit=Decimal(str(row[2])),
                        monthly_limit=Decimal(str(row[3])),
                        alert_thresholds=json.loads(row[4]) if row[4] else [0.5, 0.75, 0.9],
                        enabled=bool(row[5])
                    )
                    
    async def _save_alert_rule(self, rule: AlertRule):
        """Save alert rule to database."""
        async with aiosqlite.connect(str(self.db_path)) as db:
            await db.execute("""
                INSERT OR REPLACE INTO alert_rules 
                (name, metric_name, threshold, comparison, window_minutes, 
                 cooldown_minutes, enabled, actions, metadata, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                rule.name, rule.metric_name, rule.threshold, rule.comparison,
                rule.window_minutes, rule.cooldown_minutes, int(rule.enabled),
                json.dumps(rule.actions), json.dumps(rule.metadata)
            ))
            await db.commit()
            
    async def _save_cost_budget(self, budget: CostBudget):
        """Save cost budget to database."""
        async with aiosqlite.connect(str(self.db_path)) as db:
            await db.execute("""
                INSERT INTO cost_budgets 
                (daily_limit, weekly_limit, monthly_limit, alert_thresholds, enabled)
                VALUES (?, ?, ?, ?, ?)
            """, (
                str(budget.daily_limit), str(budget.weekly_limit), 
                str(budget.monthly_limit), json.dumps(budget.alert_thresholds),
                int(budget.enabled)
            ))
            await db.commit()
            
    # Query methods
    
    async def get_metrics(self, name: str, start_time: datetime, 
                        end_time: datetime, tags: Optional[Dict[str, str]] = None) -> List[MetricPoint]:
        """Get metrics for a time range."""
        async with aiosqlite.connect(str(self.db_path)) as db:
            query = """
                SELECT timestamp, name, value, category, metric_type, tags, metadata
                FROM metrics
                WHERE name = ? AND timestamp >= ? AND timestamp <= ?
            """
            params = [name, start_time.isoformat(), end_time.isoformat()]
            
            if tags:
                # Add tag filtering
                for key, value in tags.items():
                    query += f" AND json_extract(tags, '$.{key}') = ?"
                    params.append(value)
                    
            query += " ORDER BY timestamp"
            
            metrics = []
            async with db.execute(query, params) as cursor:
                async for row in cursor:
                    metric = MetricPoint(
                        timestamp=datetime.fromisoformat(row[0]),
                        name=row[1],
                        value=row[2],
                        category=MetricCategory(row[3]),
                        metric_type=MetricType(row[4]),
                        tags=json.loads(row[5]) if row[5] else {},
                        metadata=json.loads(row[6]) if row[6] else {}
                    )
                    metrics.append(metric)
                    
            return metrics
            
    async def get_cost_sum(self, start_time: datetime, end_time: datetime) -> float:
        """Get total cost for a time range."""
        async with aiosqlite.connect(str(self.db_path)) as db:
            async with db.execute("""
                SELECT SUM(value) FROM metrics
                WHERE name = 'api.cost.total' 
                AND timestamp >= ? AND timestamp <= ?
            """, (start_time.isoformat(), end_time.isoformat())) as cursor:
                result = await cursor.fetchone()
                return result[0] if result[0] else 0.0
                
    async def get_aggregated_metrics(self, name: str, start_time: datetime,
                                   end_time: datetime, interval_minutes: int = 60,
                                   aggregation: str = "avg") -> List[Dict[str, Any]]:
        """Get aggregated metrics over time intervals."""
        async with aiosqlite.connect(str(self.db_path)) as db:
            # SQLite datetime functions for grouping
            interval_seconds = interval_minutes * 60
            
            aggregation_func = {
                "avg": "AVG(value)",
                "sum": "SUM(value)",
                "min": "MIN(value)",
                "max": "MAX(value)",
                "count": "COUNT(*)"
            }.get(aggregation, "AVG(value)")
            
            query = f"""
                SELECT 
                    datetime((strftime('%s', timestamp) / {interval_seconds}) * {interval_seconds}, 'unixepoch') as interval,
                    {aggregation_func} as value,
                    COUNT(*) as count
                FROM metrics
                WHERE name = ? AND timestamp >= ? AND timestamp <= ?
                GROUP BY interval
                ORDER BY interval
            """
            
            results = []
            async with db.execute(query, (name, start_time.isoformat(), end_time.isoformat())) as cursor:
                async for row in cursor:
                    results.append({
                        "timestamp": datetime.fromisoformat(row[0]),
                        "value": row[1],
                        "count": row[2]
                    })
                    
            return results
            
    def get_live_metrics(self) -> Dict[str, Any]:
        """Get current live metrics from cache."""
        live_data = {}
        
        for key, cache in self._aggregation_cache.items():
            if cache.get("last_timestamp"):
                # Only include recent metrics (last 5 minutes)
                if datetime.utcnow() - cache["last_timestamp"] < timedelta(minutes=5):
                    metric_name, category = key.split(":", 1)
                    live_data[key] = {
                        "name": metric_name,
                        "category": category,
                        "last_value": cache["last_value"],
                        "count": cache["count"],
                        "sum": cache["sum"],
                        "min": cache["min"],
                        "max": cache["max"],
                        "avg": cache["sum"] / cache["count"] if cache["count"] > 0 else 0,
                        "last_updated": cache["last_timestamp"].isoformat()
                    }
                    
        return live_data


# Context manager for timing operations
class MetricTimer:
    """Context manager for timing operations."""
    
    def __init__(self, collector: MetricsCollector, name: str, 
                 category: MetricCategory = MetricCategory.SYSTEM,
                 tags: Optional[Dict[str, str]] = None):
        self.collector = collector
        self.name = name
        self.category = category
        self.tags = tags or {}
        self.start_time = None
        
    async def __aenter__(self):
        self.start_time = time.time()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        await self.collector.record_timer(
            self.name,
            duration_ms,
            category=self.category,
            tags=self.tags
        )