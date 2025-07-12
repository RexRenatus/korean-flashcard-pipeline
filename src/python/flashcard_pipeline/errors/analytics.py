"""Error analytics and reporting"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from dataclasses import dataclass, field
import json

from .base import ErrorCategory, ErrorSeverity
from .collector import ErrorCollector, ErrorRecord
from ..database.database_manager_v2 import DatabaseManager
from ..telemetry import create_span, record_metric, add_event

@dataclass
class ErrorTrend:
    """Trend data for errors"""
    timestamp: datetime
    count: int
    category: Optional[str] = None
    severity: Optional[str] = None
    error_type: Optional[str] = None
    
    @property
    def hourly_bucket(self) -> datetime:
        """Get hourly bucket for this timestamp"""
        return self.timestamp.replace(minute=0, second=0, microsecond=0)
    
    @property
    def daily_bucket(self) -> datetime:
        """Get daily bucket for this timestamp"""
        return self.timestamp.replace(hour=0, minute=0, second=0, microsecond=0)


@dataclass
class ErrorImpact:
    """Impact analysis for errors"""
    error_fingerprint: str
    total_occurrences: int
    affected_users: int
    affected_traces: int
    first_seen: datetime
    last_seen: datetime
    severity: ErrorSeverity
    category: ErrorCategory
    estimated_impact_score: float = 0.0
    
    def calculate_impact_score(self) -> float:
        """Calculate impact score based on various factors"""
        # Base score from severity
        severity_scores = {
            ErrorSeverity.LOW: 1.0,
            ErrorSeverity.MEDIUM: 5.0,
            ErrorSeverity.HIGH: 10.0,
            ErrorSeverity.CRITICAL: 20.0
        }
        base_score = severity_scores.get(self.severity, 5.0)
        
        # Multiply by occurrence frequency
        frequency_multiplier = min(self.total_occurrences / 10, 10.0)  # Cap at 10x
        
        # Multiply by user impact
        user_impact = min(self.affected_users / 10, 5.0)  # Cap at 5x
        
        # Recency factor (errors in last hour get 2x score)
        recency_factor = 2.0 if (datetime.now() - self.last_seen).seconds < 3600 else 1.0
        
        self.estimated_impact_score = base_score * frequency_multiplier * user_impact * recency_factor
        return self.estimated_impact_score


@dataclass
class ErrorMetrics:
    """Aggregated error metrics"""
    time_window: timedelta
    total_errors: int = 0
    unique_errors: int = 0
    affected_users: int = 0
    affected_traces: int = 0
    
    errors_by_category: Dict[str, int] = field(default_factory=dict)
    errors_by_severity: Dict[str, int] = field(default_factory=dict)
    errors_by_type: Dict[str, int] = field(default_factory=dict)
    
    error_rate: float = 0.0  # Errors per minute
    critical_error_rate: float = 0.0
    
    top_errors: List[Tuple[str, int]] = field(default_factory=list)
    
    def calculate_rates(self):
        """Calculate error rates"""
        minutes = self.time_window.total_seconds() / 60
        if minutes > 0:
            self.error_rate = self.total_errors / minutes
            critical_count = self.errors_by_severity.get(ErrorSeverity.CRITICAL.value, 0)
            self.critical_error_rate = critical_count / minutes


class ErrorAnalytics:
    """Analytics engine for error data"""
    
    def __init__(
        self,
        collector: ErrorCollector,
        database: Optional[DatabaseManager] = None
    ):
        self.collector = collector
        self.database = database
    
    async def get_error_metrics(
        self,
        time_window: timedelta = timedelta(hours=1),
        category_filter: Optional[ErrorCategory] = None,
        severity_filter: Optional[ErrorSeverity] = None
    ) -> ErrorMetrics:
        """Get error metrics for time window"""
        with create_span(
            "analytics.get_metrics",
            attributes={
                "time_window_hours": time_window.total_seconds() / 3600,
                "has_category_filter": category_filter is not None,
                "has_severity_filter": severity_filter is not None
            }
        ):
            metrics = ErrorMetrics(time_window=time_window)
            
            if not self.database:
                # Use in-memory data
                return self._get_metrics_from_memory(
                    time_window, category_filter, severity_filter
                )
            
            # Query database
            start_time = datetime.now() - time_window
            
            # Base query
            query = """
                SELECT 
                    COUNT(*) as total_errors,
                    COUNT(DISTINCT fingerprint) as unique_errors,
                    COUNT(DISTINCT metadata->>'$.user_id') as affected_users,
                    COUNT(DISTINCT trace_id) as affected_traces,
                    category,
                    severity,
                    error_type
                FROM error_records
                WHERE timestamp >= ?
            """
            
            params = [start_time.timestamp()]
            
            # Add filters
            if category_filter:
                query += " AND category = ?"
                params.append(category_filter.value)
            
            if severity_filter:
                query += " AND severity = ?"
                params.append(severity_filter.value)
            
            query += " GROUP BY category, severity, error_type"
            
            result = await self.database.execute(query, tuple(params))
            
            # Aggregate results
            for row in result.rows:
                (total, unique, users, traces, category, severity, error_type) = row
                
                metrics.total_errors += total
                metrics.unique_errors = max(metrics.unique_errors, unique)
                metrics.affected_users = max(metrics.affected_users, users or 0)
                metrics.affected_traces = max(metrics.affected_traces, traces or 0)
                
                metrics.errors_by_category[category] = metrics.errors_by_category.get(category, 0) + total
                metrics.errors_by_severity[severity] = metrics.errors_by_severity.get(severity, 0) + total
                metrics.errors_by_type[error_type] = metrics.errors_by_type.get(error_type, 0) + total
            
            # Get top errors
            top_errors_query = """
                SELECT fingerprint, COUNT(*) as count
                FROM error_records
                WHERE timestamp >= ?
                GROUP BY fingerprint
                ORDER BY count DESC
                LIMIT 10
            """
            
            top_result = await self.database.execute(top_errors_query, (start_time.timestamp(),))
            metrics.top_errors = [(row[0], row[1]) for row in top_result.rows]
            
            # Calculate rates
            metrics.calculate_rates()
            
            # Record metrics
            self._record_analytics_metrics(metrics)
            
            return metrics
    
    def _get_metrics_from_memory(
        self,
        time_window: timedelta,
        category_filter: Optional[ErrorCategory],
        severity_filter: Optional[ErrorSeverity]
    ) -> ErrorMetrics:
        """Get metrics from in-memory collector data"""
        metrics = ErrorMetrics(time_window=time_window)
        start_time = datetime.now() - time_window
        
        # Get stats from collector
        stats = self.collector.get_statistics()
        
        # Filter recent errors
        for error_id, record in self.collector._error_index.items():
            if datetime.fromtimestamp(record.timestamp) < start_time:
                continue
            
            if category_filter and record.metadata.category != category_filter:
                continue
            
            if severity_filter and record.metadata.severity != severity_filter:
                continue
            
            metrics.total_errors += 1
            
            # Update category/severity counts
            metrics.errors_by_category[record.metadata.category.value] = \
                metrics.errors_by_category.get(record.metadata.category.value, 0) + 1
            metrics.errors_by_severity[record.metadata.severity.value] = \
                metrics.errors_by_severity.get(record.metadata.severity.value, 0) + 1
            metrics.errors_by_type[record.metadata.error_type] = \
                metrics.errors_by_type.get(record.metadata.error_type, 0) + 1
        
        # Get unique counts
        unique_fingerprints = set()
        unique_users = set()
        unique_traces = set()
        
        for error_id, record in self.collector._error_index.items():
            if datetime.fromtimestamp(record.timestamp) >= start_time:
                unique_fingerprints.add(record.fingerprint)
                if record.metadata.user_id:
                    unique_users.add(record.metadata.user_id)
                if record.trace_id:
                    unique_traces.add(record.trace_id)
        
        metrics.unique_errors = len(unique_fingerprints)
        metrics.affected_users = len(unique_users)
        metrics.affected_traces = len(unique_traces)
        
        # Calculate rates
        metrics.calculate_rates()
        
        return metrics
    
    async def get_error_trends(
        self,
        time_window: timedelta = timedelta(hours=24),
        granularity: str = "hour",  # hour or day
        category_filter: Optional[ErrorCategory] = None
    ) -> List[ErrorTrend]:
        """Get error trends over time"""
        with create_span(
            "analytics.get_trends",
            attributes={
                "time_window_hours": time_window.total_seconds() / 3600,
                "granularity": granularity
            }
        ):
            if not self.database:
                return []
            
            start_time = datetime.now() - time_window
            
            # Build query based on granularity
            if granularity == "hour":
                time_bucket = "strftime('%Y-%m-%d %H:00:00', datetime(timestamp, 'unixepoch'))"
            else:
                time_bucket = "strftime('%Y-%m-%d', datetime(timestamp, 'unixepoch'))"
            
            query = f"""
                SELECT 
                    {time_bucket} as time_bucket,
                    COUNT(*) as error_count,
                    category,
                    severity
                FROM error_records
                WHERE timestamp >= ?
            """
            
            params = [start_time.timestamp()]
            
            if category_filter:
                query += " AND category = ?"
                params.append(category_filter.value)
            
            query += f" GROUP BY {time_bucket}, category, severity"
            query += " ORDER BY time_bucket"
            
            result = await self.database.execute(query, tuple(params))
            
            trends = []
            for row in result.rows:
                bucket_str, count, category, severity = row
                
                # Parse timestamp
                if granularity == "hour":
                    timestamp = datetime.strptime(bucket_str, "%Y-%m-%d %H:%M:%S")
                else:
                    timestamp = datetime.strptime(bucket_str, "%Y-%m-%d")
                
                trends.append(ErrorTrend(
                    timestamp=timestamp,
                    count=count,
                    category=category,
                    severity=severity
                ))
            
            return trends
    
    async def get_error_impact_analysis(
        self,
        limit: int = 20,
        time_window: Optional[timedelta] = None
    ) -> List[ErrorImpact]:
        """Get impact analysis for top errors"""
        with create_span("analytics.impact_analysis"):
            if not self.database:
                return []
            
            query = """
                SELECT 
                    fingerprint,
                    occurrence_count,
                    affected_users,
                    affected_traces,
                    first_seen,
                    last_seen,
                    category,
                    severity,
                    error_type,
                    sample_message
                FROM error_aggregates
            """
            
            if time_window:
                query += " WHERE last_seen >= ?"
                params = [(datetime.now() - time_window).isoformat()]
            else:
                params = []
            
            query += " ORDER BY occurrence_count DESC LIMIT ?"
            params.append(limit)
            
            result = await self.database.execute(query, tuple(params))
            
            impacts = []
            for row in result.rows:
                impact = ErrorImpact(
                    error_fingerprint=row[0],
                    total_occurrences=row[1],
                    affected_users=row[2],
                    affected_traces=row[3],
                    first_seen=datetime.fromisoformat(row[4]),
                    last_seen=datetime.fromisoformat(row[5]),
                    category=ErrorCategory(row[6]),
                    severity=ErrorSeverity(row[7])
                )
                
                # Calculate impact score
                impact.calculate_impact_score()
                impacts.append(impact)
            
            # Sort by impact score
            impacts.sort(key=lambda x: x.estimated_impact_score, reverse=True)
            
            return impacts
    
    async def get_error_correlation_analysis(
        self,
        error_fingerprint: str,
        time_window: timedelta = timedelta(hours=1)
    ) -> Dict[str, Any]:
        """Analyze correlations for a specific error"""
        with create_span(
            "analytics.correlation_analysis",
            attributes={"fingerprint": error_fingerprint}
        ):
            if not self.database:
                return {}
            
            # Get all occurrences of this error
            query = """
                SELECT trace_id, timestamp, metadata
                FROM error_records
                WHERE fingerprint = ?
                AND timestamp >= ?
                ORDER BY timestamp DESC
            """
            
            start_time = datetime.now() - time_window
            result = await self.database.execute(
                query,
                (error_fingerprint, start_time.timestamp())
            )
            
            # Analyze patterns
            trace_ids = []
            user_ids = []
            timestamps = []
            
            for row in result.rows:
                trace_id, timestamp, metadata_json = row
                
                if trace_id:
                    trace_ids.append(trace_id)
                
                timestamps.append(timestamp)
                
                try:
                    metadata = json.loads(metadata_json)
                    if metadata.get("user_id"):
                        user_ids.append(metadata["user_id"])
                except:
                    pass
            
            # Find correlated errors
            correlated_errors = defaultdict(int)
            
            if trace_ids:
                correlated_query = """
                    SELECT fingerprint, COUNT(*) as count
                    FROM error_records
                    WHERE trace_id IN ({})
                    AND fingerprint != ?
                    GROUP BY fingerprint
                    ORDER BY count DESC
                    LIMIT 10
                """.format(",".join("?" * len(trace_ids)))
                
                correlated_result = await self.database.execute(
                    correlated_query,
                    tuple(trace_ids) + (error_fingerprint,)
                )
                
                for row in correlated_result.rows:
                    correlated_errors[row[0]] = row[1]
            
            # Calculate time patterns
            time_distribution = Counter()
            for ts in timestamps:
                hour = datetime.fromtimestamp(ts).hour
                time_distribution[hour] += 1
            
            return {
                "total_occurrences": len(timestamps),
                "affected_traces": len(set(trace_ids)),
                "affected_users": len(set(user_ids)),
                "correlated_errors": dict(correlated_errors),
                "hourly_distribution": dict(time_distribution),
                "peak_hour": max(time_distribution.items(), key=lambda x: x[1])[0] if time_distribution else None
            }
    
    def _record_analytics_metrics(self, metrics: ErrorMetrics):
        """Record analytics metrics to telemetry"""
        # Error rates
        record_metric(
            "analytics.error_rate",
            metrics.error_rate,
            metric_type="gauge",
            attributes={"window": str(metrics.time_window)}
        )
        
        record_metric(
            "analytics.critical_error_rate",
            metrics.critical_error_rate,
            metric_type="gauge"
        )
        
        # Category breakdown
        for category, count in metrics.errors_by_category.items():
            record_metric(
                "analytics.errors_by_category",
                count,
                metric_type="gauge",
                attributes={"category": category}
            )
        
        # Severity breakdown
        for severity, count in metrics.errors_by_severity.items():
            record_metric(
                "analytics.errors_by_severity",
                count,
                metric_type="gauge",
                attributes={"severity": severity}
            )
    
    async def generate_error_report(
        self,
        time_window: timedelta = timedelta(hours=24)
    ) -> Dict[str, Any]:
        """Generate comprehensive error report"""
        with create_span("analytics.generate_report"):
            # Get metrics
            metrics = await self.get_error_metrics(time_window)
            
            # Get trends
            trends = await self.get_error_trends(time_window, granularity="hour")
            
            # Get impact analysis
            impacts = await self.get_error_impact_analysis(limit=10, time_window=time_window)
            
            # Build report
            report = {
                "generated_at": datetime.now().isoformat(),
                "time_window": str(time_window),
                "summary": {
                    "total_errors": metrics.total_errors,
                    "unique_errors": metrics.unique_errors,
                    "affected_users": metrics.affected_users,
                    "affected_traces": metrics.affected_traces,
                    "error_rate_per_minute": round(metrics.error_rate, 2),
                    "critical_error_rate_per_minute": round(metrics.critical_error_rate, 2)
                },
                "breakdown": {
                    "by_category": metrics.errors_by_category,
                    "by_severity": metrics.errors_by_severity,
                    "top_error_types": sorted(
                        metrics.errors_by_type.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[:10]
                },
                "trends": {
                    "hourly_counts": [
                        {"time": t.timestamp.isoformat(), "count": t.count}
                        for t in trends
                    ]
                },
                "top_impact_errors": [
                    {
                        "fingerprint": impact.error_fingerprint,
                        "occurrences": impact.total_occurrences,
                        "affected_users": impact.affected_users,
                        "severity": impact.severity.value,
                        "impact_score": round(impact.estimated_impact_score, 2)
                    }
                    for impact in impacts[:5]
                ]
            }
            
            # Add alerts if needed
            alerts = []
            
            if metrics.critical_error_rate > 0.1:  # More than 0.1 critical errors per minute
                alerts.append({
                    "level": "critical",
                    "message": f"High critical error rate: {metrics.critical_error_rate:.2f} per minute"
                })
            
            if metrics.error_rate > 10:  # More than 10 errors per minute
                alerts.append({
                    "level": "warning",
                    "message": f"High overall error rate: {metrics.error_rate:.2f} per minute"
                })
            
            if alerts:
                report["alerts"] = alerts
            
            add_event(
                "error_report_generated",
                attributes={
                    "total_errors": metrics.total_errors,
                    "alert_count": len(alerts)
                }
            )
            
            return report