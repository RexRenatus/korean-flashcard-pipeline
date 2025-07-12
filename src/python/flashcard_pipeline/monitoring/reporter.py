"""
Reporting system for flashcard pipeline monitoring.

This module provides:
- Daily summary reports
- Weekly performance reports  
- Monthly cost reports
- Custom report builder
- Report scheduling
- Email/webhook notifications
"""

import asyncio
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import aiosqlite
from jinja2 import Template
import aiofiles
import aiohttp
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib

from .metrics_collector import MetricsCollector
from .analytics_service import AnalyticsService

logger = logging.getLogger(__name__)


class ReportType(Enum):
    """Types of reports available."""
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_PERFORMANCE = "weekly_performance"
    MONTHLY_COST = "monthly_cost"
    CUSTOM = "custom"


class ReportFormat(Enum):
    """Report output formats."""
    HTML = "html"
    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"


class NotificationType(Enum):
    """Types of notifications."""
    EMAIL = "email"
    WEBHOOK = "webhook"
    FILE = "file"


@dataclass
class ReportConfig:
    """Configuration for a report."""
    name: str
    report_type: ReportType
    format: ReportFormat
    schedule: Optional[str] = None  # cron expression
    recipients: List[str] = None
    webhook_url: Optional[str] = None
    custom_template: Optional[str] = None
    filters: Dict[str, Any] = None
    enabled: bool = True


@dataclass
class ReportResult:
    """Result of report generation."""
    report_id: str
    report_type: ReportType
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    format: ReportFormat
    content: str
    metadata: Dict[str, Any]


class Reporter:
    """Main reporting system."""
    
    def __init__(self, metrics: MetricsCollector, analytics: AnalyticsService,
                 reports_dir: Path = Path("reports")):
        self.metrics = metrics
        self.analytics = analytics
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(exist_ok=True)
        self._report_configs: Dict[str, ReportConfig] = {}
        self._scheduled_tasks: Dict[str, asyncio.Task] = {}
        
        # Email configuration (would be loaded from config)
        self.smtp_host = None
        self.smtp_port = None
        self.smtp_user = None
        self.smtp_password = None
        self.from_email = None
        
    async def initialize(self):
        """Initialize the reporter."""
        await self._create_tables()
        await self._load_report_configs()
        logger.info("Reporter initialized")
        
    async def shutdown(self):
        """Shutdown the reporter."""
        # Cancel scheduled tasks
        for task in self._scheduled_tasks.values():
            task.cancel()
        logger.info("Reporter shutdown")
        
    async def _create_tables(self):
        """Create database tables for report tracking."""
        async with aiosqlite.connect(str(self.metrics.db_path)) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS report_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    report_type TEXT NOT NULL,
                    format TEXT NOT NULL,
                    schedule TEXT,
                    recipients TEXT,
                    webhook_url TEXT,
                    custom_template TEXT,
                    filters TEXT,
                    enabled BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS report_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id TEXT UNIQUE NOT NULL,
                    report_name TEXT NOT NULL,
                    report_type TEXT NOT NULL,
                    format TEXT NOT NULL,
                    period_start DATETIME NOT NULL,
                    period_end DATETIME NOT NULL,
                    file_path TEXT,
                    notifications_sent TEXT,
                    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            await db.commit()
            
    # Report Generation
    
    async def generate_daily_summary(self, date: Optional[datetime] = None,
                                   format: ReportFormat = ReportFormat.HTML) -> ReportResult:
        """Generate daily summary report."""
        if date is None:
            date = datetime.utcnow().date()
        else:
            date = date.date()
            
        # Define report period
        period_start = datetime.combine(date, datetime.min.time())
        period_end = datetime.combine(date, datetime.max.time())
        
        # Gather data
        summary_data = await self._gather_daily_data(period_start, period_end)
        
        # Generate report content
        content = await self._format_report(
            "daily_summary",
            summary_data,
            format
        )
        
        # Create report result
        report_id = f"daily_{date.strftime('%Y%m%d')}_{datetime.utcnow().timestamp()}"
        result = ReportResult(
            report_id=report_id,
            report_type=ReportType.DAILY_SUMMARY,
            generated_at=datetime.utcnow(),
            period_start=period_start,
            period_end=period_end,
            format=format,
            content=content,
            metadata=summary_data
        )
        
        # Save report
        await self._save_report(result)
        
        return result
        
    async def generate_weekly_performance(self, week_ending: Optional[datetime] = None,
                                        format: ReportFormat = ReportFormat.HTML) -> ReportResult:
        """Generate weekly performance report."""
        if week_ending is None:
            week_ending = datetime.utcnow().date()
        else:
            week_ending = week_ending.date()
            
        # Define report period (7 days ending on week_ending)
        period_end = datetime.combine(week_ending, datetime.max.time())
        period_start = datetime.combine(week_ending - timedelta(days=6), datetime.min.time())
        
        # Gather performance data
        performance_data = await self._gather_weekly_performance(period_start, period_end)
        
        # Generate report content
        content = await self._format_report(
            "weekly_performance",
            performance_data,
            format
        )
        
        # Create report result
        report_id = f"weekly_{week_ending.strftime('%Y%m%d')}_{datetime.utcnow().timestamp()}"
        result = ReportResult(
            report_id=report_id,
            report_type=ReportType.WEEKLY_PERFORMANCE,
            generated_at=datetime.utcnow(),
            period_start=period_start,
            period_end=period_end,
            format=format,
            content=content,
            metadata=performance_data
        )
        
        # Save report
        await self._save_report(result)
        
        return result
        
    async def generate_monthly_cost(self, year: int, month: int,
                                  format: ReportFormat = ReportFormat.HTML) -> ReportResult:
        """Generate monthly cost report."""
        # Define report period
        period_start = datetime(year, month, 1)
        if month == 12:
            period_end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            period_end = datetime(year, month + 1, 1) - timedelta(seconds=1)
            
        # Gather cost data
        cost_data = await self._gather_monthly_cost(period_start, period_end)
        
        # Generate report content
        content = await self._format_report(
            "monthly_cost",
            cost_data,
            format
        )
        
        # Create report result
        report_id = f"monthly_cost_{year}{month:02d}_{datetime.utcnow().timestamp()}"
        result = ReportResult(
            report_id=report_id,
            report_type=ReportType.MONTHLY_COST,
            generated_at=datetime.utcnow(),
            period_start=period_start,
            period_end=period_end,
            format=format,
            content=content,
            metadata=cost_data
        )
        
        # Save report
        await self._save_report(result)
        
        return result
        
    async def generate_custom_report(self, config: ReportConfig,
                                   period_start: datetime,
                                   period_end: datetime) -> ReportResult:
        """Generate custom report based on configuration."""
        # Gather data based on filters
        custom_data = await self._gather_custom_data(
            period_start, 
            period_end,
            config.filters or {}
        )
        
        # Generate report content
        if config.custom_template:
            content = await self._format_custom_report(
                config.custom_template,
                custom_data,
                config.format
            )
        else:
            content = await self._format_report(
                "custom",
                custom_data,
                config.format
            )
            
        # Create report result
        report_id = f"custom_{config.name}_{datetime.utcnow().timestamp()}"
        result = ReportResult(
            report_id=report_id,
            report_type=ReportType.CUSTOM,
            generated_at=datetime.utcnow(),
            period_start=period_start,
            period_end=period_end,
            format=config.format,
            content=content,
            metadata=custom_data
        )
        
        # Save report
        await self._save_report(result)
        
        return result
        
    # Data Gathering Methods
    
    async def _gather_daily_data(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """Gather data for daily summary report."""
        # Get basic metrics
        total_api_calls = await self._count_metric("api.calls.total", start, end)
        total_errors = await self._count_metric("api.errors.total", start, end)
        total_words = await self._count_metric("processing.words.total", start, end)
        total_cost = await self.metrics.get_cost_sum(start, end)
        
        # Get performance metrics
        api_latency = await self._get_latency_stats("api.call.duration", start, end)
        processing_latency = await self._get_latency_stats("processing.duration", start, end)
        
        # Get cache performance
        cache_hits = await self._count_metric("cache.hits.total", start, end)
        cache_misses = await self._count_metric("cache.misses.total", start, end)
        cache_hit_rate = cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0
        
        # Get hourly breakdown
        hourly_breakdown = await self._get_hourly_breakdown(start, end)
        
        # Detect anomalies
        anomalies = await self.analytics.detect_anomalies("api.calls.total", period_days=1)
        
        return {
            "date": start.date().isoformat(),
            "summary": {
                "total_api_calls": total_api_calls,
                "total_errors": total_errors,
                "error_rate": (total_errors / total_api_calls) if total_api_calls > 0 else 0,
                "total_words_processed": total_words,
                "total_cost": float(total_cost),
                "cache_hit_rate": cache_hit_rate
            },
            "performance": {
                "api_latency": api_latency,
                "processing_latency": processing_latency
            },
            "hourly_breakdown": hourly_breakdown,
            "anomalies": [asdict(a) for a in anomalies],
            "top_errors": await self._get_top_errors(start, end)
        }
        
    async def _gather_weekly_performance(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """Gather data for weekly performance report."""
        # Get performance analysis
        performance = await self.analytics.analyze_performance(period_days=7)
        
        # Get trend analysis
        trends = await self.analytics.analyze_multiple_trends(
            ["api.calls.total", "api.cost.total", "processing.words.total", "api.call.duration"],
            period_days=7
        )
        
        # Get usage patterns
        usage_pattern = await self.analytics.detect_usage_patterns(period_days=7)
        
        # Get daily summaries
        daily_summaries = []
        current_date = start.date()
        while current_date <= end.date():
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = datetime.combine(current_date, datetime.max.time())
            
            daily_summaries.append({
                "date": current_date.isoformat(),
                "api_calls": await self._count_metric("api.calls.total", day_start, day_end),
                "words_processed": await self._count_metric("processing.words.total", day_start, day_end),
                "cost": float(await self.metrics.get_cost_sum(day_start, day_end)),
                "avg_latency": await self._get_avg_metric("api.call.duration", day_start, day_end)
            })
            
            current_date += timedelta(days=1)
            
        return {
            "period": f"{start.date().isoformat()} to {end.date().isoformat()}",
            "performance": performance,
            "trends": {name: asdict(trend) for name, trend in trends.items()},
            "usage_pattern": asdict(usage_pattern),
            "daily_summaries": daily_summaries,
            "improvements": await self._suggest_improvements(performance, trends)
        }
        
    async def _gather_monthly_cost(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """Gather data for monthly cost report."""
        # Get cost analysis
        days_in_period = (end - start).days + 1
        cost_analysis = await self.analytics.analyze_costs(period_days=days_in_period)
        
        # Get daily costs
        daily_costs = []
        current_date = start.date()
        while current_date <= end.date():
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = datetime.combine(current_date, datetime.max.time())
            
            daily_costs.append({
                "date": current_date.isoformat(),
                "cost": float(await self.metrics.get_cost_sum(day_start, day_end))
            })
            
            current_date += timedelta(days=1)
            
        # Get cost by model for the month
        cost_by_model = await self._get_cost_by_model_detailed(start, end)
        
        # Get cost trends
        cost_trend = await self.analytics.analyze_trend("api.cost.total", period_days=days_in_period)
        
        # Calculate projections
        remaining_days = 30 - days_in_period
        projected_total = float(cost_analysis.total_cost) + (
            float(cost_analysis.average_daily_cost) * remaining_days
        )
        
        return {
            "month": f"{start.year}-{start.month:02d}",
            "cost_analysis": asdict(cost_analysis),
            "daily_costs": daily_costs,
            "cost_by_model": cost_by_model,
            "cost_trend": asdict(cost_trend),
            "projections": {
                "projected_total": projected_total,
                "days_remaining": remaining_days,
                "budget_status": self._get_budget_status(cost_analysis)
            },
            "recommendations": self._get_cost_recommendations(cost_analysis, cost_by_model)
        }
        
    async def _gather_custom_data(self, start: datetime, end: datetime,
                                filters: Dict[str, Any]) -> Dict[str, Any]:
        """Gather data for custom report based on filters."""
        data = {
            "period": f"{start.isoformat()} to {end.isoformat()}",
            "filters": filters
        }
        
        # Get metrics specified in filters
        if "metrics" in filters:
            metrics_data = {}
            for metric_name in filters["metrics"]:
                metrics = await self.metrics.get_metrics(metric_name, start, end)
                metrics_data[metric_name] = {
                    "count": len(metrics),
                    "sum": sum(m.value for m in metrics),
                    "avg": sum(m.value for m in metrics) / len(metrics) if metrics else 0,
                    "min": min(m.value for m in metrics) if metrics else 0,
                    "max": max(m.value for m in metrics) if metrics else 0
                }
            data["metrics"] = metrics_data
            
        # Get aggregations if specified
        if "aggregations" in filters:
            aggregations_data = {}
            for agg_config in filters["aggregations"]:
                metric_name = agg_config["metric"]
                interval = agg_config.get("interval", 60)
                agg_type = agg_config.get("type", "avg")
                
                agg_data = await self.metrics.get_aggregated_metrics(
                    metric_name, start, end,
                    interval_minutes=interval,
                    aggregation=agg_type
                )
                aggregations_data[f"{metric_name}_{agg_type}_{interval}m"] = agg_data
            data["aggregations"] = aggregations_data
            
        # Include trends if requested
        if filters.get("include_trends", False):
            trend_metrics = filters.get("trend_metrics", ["api.calls.total", "api.cost.total"])
            trends = await self.analytics.analyze_multiple_trends(
                trend_metrics,
                period_days=(end - start).days
            )
            data["trends"] = {name: asdict(trend) for name, trend in trends.items()}
            
        # Include anomalies if requested
        if filters.get("include_anomalies", False):
            anomaly_metrics = filters.get("anomaly_metrics", ["api.calls.total"])
            all_anomalies = []
            for metric_name in anomaly_metrics:
                anomalies = await self.analytics.detect_anomalies(
                    metric_name,
                    period_days=(end - start).days
                )
                all_anomalies.extend(anomalies)
            data["anomalies"] = [asdict(a) for a in all_anomalies]
            
        return data
        
    # Formatting Methods
    
    async def _format_report(self, template_name: str, data: Dict[str, Any],
                           format: ReportFormat) -> str:
        """Format report data into specified format."""
        if format == ReportFormat.JSON:
            return json.dumps(data, indent=2, default=str)
            
        elif format == ReportFormat.HTML:
            template = self._get_html_template(template_name)
            return template.render(**data)
            
        elif format == ReportFormat.MARKDOWN:
            template = self._get_markdown_template(template_name)
            return template.render(**data)
            
        elif format == ReportFormat.TEXT:
            template = self._get_text_template(template_name)
            return template.render(**data)
            
        else:
            raise ValueError(f"Unsupported format: {format}")
            
    async def _format_custom_report(self, template_str: str, data: Dict[str, Any],
                                  format: ReportFormat) -> str:
        """Format custom report with user-provided template."""
        if format == ReportFormat.JSON:
            return json.dumps(data, indent=2, default=str)
        else:
            template = Template(template_str)
            return template.render(**data)
            
    def _get_html_template(self, template_name: str) -> Template:
        """Get HTML template for report type."""
        templates = {
            "daily_summary": """
<!DOCTYPE html>
<html>
<head>
    <title>Daily Summary Report - {{ date }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1, h2 { color: #333; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .metric { font-size: 24px; font-weight: bold; color: #2196F3; }
        .error { color: #f44336; }
        .success { color: #4CAF50; }
    </style>
</head>
<body>
    <h1>Daily Summary Report - {{ date }}</h1>
    
    <h2>Key Metrics</h2>
    <table>
        <tr>
            <td>Total API Calls</td>
            <td class="metric">{{ summary.total_api_calls|int }}</td>
        </tr>
        <tr>
            <td>Error Rate</td>
            <td class="metric {% if summary.error_rate > 0.05 %}error{% else %}success{% endif %}">
                {{ "%.1f"|format(summary.error_rate * 100) }}%
            </td>
        </tr>
        <tr>
            <td>Words Processed</td>
            <td class="metric">{{ summary.total_words_processed|int }}</td>
        </tr>
        <tr>
            <td>Total Cost</td>
            <td class="metric">${{ "%.2f"|format(summary.total_cost) }}</td>
        </tr>
        <tr>
            <td>Cache Hit Rate</td>
            <td class="metric">{{ "%.1f"|format(summary.cache_hit_rate * 100) }}%</td>
        </tr>
    </table>
    
    <h2>Performance</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Average</th>
            <th>P95</th>
            <th>P99</th>
        </tr>
        <tr>
            <td>API Latency</td>
            <td>{{ "%.0f"|format(performance.api_latency.avg) }}ms</td>
            <td>{{ "%.0f"|format(performance.api_latency.p95) }}ms</td>
            <td>{{ "%.0f"|format(performance.api_latency.p99) }}ms</td>
        </tr>
        <tr>
            <td>Processing Latency</td>
            <td>{{ "%.0f"|format(performance.processing_latency.avg) }}ms</td>
            <td>{{ "%.0f"|format(performance.processing_latency.p95) }}ms</td>
            <td>{{ "%.0f"|format(performance.processing_latency.p99) }}ms</td>
        </tr>
    </table>
    
    {% if anomalies %}
    <h2>Anomalies Detected</h2>
    <table>
        <tr>
            <th>Time</th>
            <th>Metric</th>
            <th>Type</th>
            <th>Severity</th>
        </tr>
        {% for anomaly in anomalies %}
        <tr>
            <td>{{ anomaly.timestamp }}</td>
            <td>{{ anomaly.metric_name }}</td>
            <td>{{ anomaly.anomaly_type }}</td>
            <td class="{% if anomaly.severity > 0.8 %}error{% endif %}">
                {{ "%.1f"|format(anomaly.severity * 100) }}%
            </td>
        </tr>
        {% endfor %}
    </table>
    {% endif %}
</body>
</html>
""",
            "weekly_performance": """
<!DOCTYPE html>
<html>
<head>
    <title>Weekly Performance Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1, h2, h3 { color: #333; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .trend-up { color: #4CAF50; }
        .trend-down { color: #f44336; }
        .recommendation { background-color: #e3f2fd; padding: 10px; margin: 10px 0; }
    </style>
</head>
<body>
    <h1>Weekly Performance Report</h1>
    <p>Period: {{ period }}</p>
    
    <h2>Performance Summary</h2>
    <table>
        <tr>
            <th>Component</th>
            <th>Avg Latency</th>
            <th>P95 Latency</th>
            <th>Success Rate</th>
        </tr>
        <tr>
            <td>API</td>
            <td>{{ "%.0f"|format(performance.api_performance.avg_latency_ms) }}ms</td>
            <td>{{ "%.0f"|format(performance.api_performance.p95_latency_ms) }}ms</td>
            <td>{{ "%.1f"|format(performance.api_performance.success_rate * 100) }}%</td>
        </tr>
        <tr>
            <td>Processing</td>
            <td>{{ "%.0f"|format(performance.processing_performance.avg_latency_ms) }}ms</td>
            <td>{{ "%.0f"|format(performance.processing_performance.p95_latency_ms) }}ms</td>
            <td>{{ "%.1f"|format(performance.processing_performance.success_rate * 100) }}%</td>
        </tr>
    </table>
    
    <h2>Trends</h2>
    {% for metric_name, trend in trends.items() %}
    <h3>{{ metric_name }}</h3>
    <p>
        Direction: <span class="{% if trend.direction == 'increasing' %}trend-up{% elif trend.direction == 'decreasing' %}trend-down{% endif %}">
            {{ trend.direction }}
        </span><br>
        Change: {{ "%.1f"|format(trend.change_percent) }}%<br>
        R²: {{ "%.3f"|format(trend.r_squared) }}
    </p>
    {% endfor %}
    
    <h2>Daily Summary</h2>
    <table>
        <tr>
            <th>Date</th>
            <th>API Calls</th>
            <th>Words Processed</th>
            <th>Cost</th>
            <th>Avg Latency</th>
        </tr>
        {% for day in daily_summaries %}
        <tr>
            <td>{{ day.date }}</td>
            <td>{{ day.api_calls|int }}</td>
            <td>{{ day.words_processed|int }}</td>
            <td>${{ "%.2f"|format(day.cost) }}</td>
            <td>{{ "%.0f"|format(day.avg_latency) }}ms</td>
        </tr>
        {% endfor %}
    </table>
    
    {% if improvements %}
    <h2>Recommendations</h2>
    {% for improvement in improvements %}
    <div class="recommendation">{{ improvement }}</div>
    {% endfor %}
    {% endif %}
</body>
</html>
""",
            "monthly_cost": """
<!DOCTYPE html>
<html>
<head>
    <title>Monthly Cost Report - {{ month }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1, h2 { color: #333; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .cost { font-size: 24px; font-weight: bold; color: #2196F3; }
        .warning { color: #ff9800; }
        .danger { color: #f44336; }
        .chart { margin: 20px 0; }
    </style>
</head>
<body>
    <h1>Monthly Cost Report - {{ month }}</h1>
    
    <h2>Cost Summary</h2>
    <table>
        <tr>
            <td>Total Cost</td>
            <td class="cost">${{ "%.2f"|format(cost_analysis.total_cost) }}</td>
        </tr>
        <tr>
            <td>Daily Average</td>
            <td class="cost">${{ "%.2f"|format(cost_analysis.average_daily_cost) }}</td>
        </tr>
        <tr>
            <td>Projected Monthly Total</td>
            <td class="cost">${{ "%.2f"|format(projections.projected_total) }}</td>
        </tr>
        {% if cost_analysis.budget_utilization %}
        <tr>
            <td>Budget Utilization</td>
            <td class="cost {% if cost_analysis.budget_utilization > 0.9 %}danger{% elif cost_analysis.budget_utilization > 0.75 %}warning{% endif %}">
                {{ "%.1f"|format(cost_analysis.budget_utilization * 100) }}%
            </td>
        </tr>
        {% endif %}
    </table>
    
    <h2>Cost by Model</h2>
    <table>
        <tr>
            <th>Model</th>
            <th>Total Cost</th>
            <th>Percentage</th>
            <th>Avg per Call</th>
        </tr>
        {% for model in cost_by_model %}
        <tr>
            <td>{{ model.name }}</td>
            <td>${{ "%.2f"|format(model.total_cost) }}</td>
            <td>{{ "%.1f"|format(model.percentage) }}%</td>
            <td>${{ "%.4f"|format(model.avg_per_call) }}</td>
        </tr>
        {% endfor %}
    </table>
    
    <h2>Cost Trend</h2>
    <p>
        Direction: {{ cost_trend.direction }}<br>
        Change: {{ "%.1f"|format(cost_trend.change_percent) }}%<br>
        Forecast next period: {% if cost_trend.forecast_next_period %}${{ "%.2f"|format(cost_trend.forecast_next_period) }}{% else %}N/A{% endif %}
    </p>
    
    {% if recommendations %}
    <h2>Cost Optimization Recommendations</h2>
    <ul>
    {% for rec in recommendations %}
        <li>{{ rec }}</li>
    {% endfor %}
    </ul>
    {% endif %}
</body>
</html>
"""
        }
        
        template_str = templates.get(template_name, templates["daily_summary"])
        return Template(template_str)
        
    def _get_markdown_template(self, template_name: str) -> Template:
        """Get Markdown template for report type."""
        templates = {
            "daily_summary": """# Daily Summary Report - {{ date }}

## Key Metrics

| Metric | Value |
|--------|-------|
| Total API Calls | {{ summary.total_api_calls|int }} |
| Error Rate | {{ "%.1f"|format(summary.error_rate * 100) }}% |
| Words Processed | {{ summary.total_words_processed|int }} |
| Total Cost | ${{ "%.2f"|format(summary.total_cost) }} |
| Cache Hit Rate | {{ "%.1f"|format(summary.cache_hit_rate * 100) }}% |

## Performance

| Metric | Average | P95 | P99 |
|--------|---------|-----|-----|
| API Latency | {{ "%.0f"|format(performance.api_latency.avg) }}ms | {{ "%.0f"|format(performance.api_latency.p95) }}ms | {{ "%.0f"|format(performance.api_latency.p99) }}ms |
| Processing Latency | {{ "%.0f"|format(performance.processing_latency.avg) }}ms | {{ "%.0f"|format(performance.processing_latency.p95) }}ms | {{ "%.0f"|format(performance.processing_latency.p99) }}ms |

{% if anomalies %}
## Anomalies Detected

| Time | Metric | Type | Severity |
|------|--------|------|----------|
{% for anomaly in anomalies %}
| {{ anomaly.timestamp }} | {{ anomaly.metric_name }} | {{ anomaly.anomaly_type }} | {{ "%.1f"|format(anomaly.severity * 100) }}% |
{% endfor %}
{% endif %}
"""
        }
        
        template_str = templates.get(template_name, templates["daily_summary"])
        return Template(template_str)
        
    def _get_text_template(self, template_name: str) -> Template:
        """Get plain text template for report type."""
        templates = {
            "daily_summary": """DAILY SUMMARY REPORT - {{ date }}
=====================================

KEY METRICS:
- Total API Calls: {{ summary.total_api_calls|int }}
- Error Rate: {{ "%.1f"|format(summary.error_rate * 100) }}%
- Words Processed: {{ summary.total_words_processed|int }}
- Total Cost: ${{ "%.2f"|format(summary.total_cost) }}
- Cache Hit Rate: {{ "%.1f"|format(summary.cache_hit_rate * 100) }}%

PERFORMANCE:
- API Latency: {{ "%.0f"|format(performance.api_latency.avg) }}ms avg, {{ "%.0f"|format(performance.api_latency.p95) }}ms P95
- Processing Latency: {{ "%.0f"|format(performance.processing_latency.avg) }}ms avg, {{ "%.0f"|format(performance.processing_latency.p95) }}ms P95

{% if anomalies %}
ANOMALIES DETECTED:
{% for anomaly in anomalies %}
- {{ anomaly.timestamp }}: {{ anomaly.metric_name }} {{ anomaly.anomaly_type }} ({{ "%.1f"|format(anomaly.severity * 100) }}% severity)
{% endfor %}
{% endif %}
"""
        }
        
        template_str = templates.get(template_name, templates["daily_summary"])
        return Template(template_str)
        
    # Notification Methods
    
    async def send_report(self, result: ReportResult, config: ReportConfig):
        """Send report via configured channels."""
        notifications_sent = []
        
        # Send email if configured
        if config.recipients and self.smtp_host:
            try:
                await self._send_email_report(result, config.recipients)
                notifications_sent.append("email")
            except Exception as e:
                logger.error(f"Failed to send email report: {e}")
                
        # Send webhook if configured
        if config.webhook_url:
            try:
                await self._send_webhook_report(result, config.webhook_url)
                notifications_sent.append("webhook")
            except Exception as e:
                logger.error(f"Failed to send webhook report: {e}")
                
        # Update report history
        await self._update_report_notifications(result.report_id, notifications_sent)
        
    async def _send_email_report(self, result: ReportResult, recipients: List[str]):
        """Send report via email."""
        msg = MIMEMultipart()
        msg['From'] = self.from_email
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = f"{result.report_type.value} - {result.generated_at.strftime('%Y-%m-%d')}"
        
        # Attach report content
        if result.format == ReportFormat.HTML:
            msg.attach(MIMEText(result.content, 'html'))
        else:
            msg.attach(MIMEText(result.content, 'plain'))
            
        # Send email
        async with aiosmtplib.SMTP(hostname=self.smtp_host, port=self.smtp_port) as smtp:
            await smtp.login(self.smtp_user, self.smtp_password)
            await smtp.send_message(msg)
            
    async def _send_webhook_report(self, result: ReportResult, webhook_url: str):
        """Send report via webhook."""
        payload = {
            "report_id": result.report_id,
            "report_type": result.report_type.value,
            "generated_at": result.generated_at.isoformat(),
            "period_start": result.period_start.isoformat(),
            "period_end": result.period_end.isoformat(),
            "format": result.format.value,
            "content": result.content if result.format == ReportFormat.JSON else None,
            "metadata": result.metadata
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                response.raise_for_status()
                
    # Helper Methods
    
    async def _count_metric(self, metric_name: str, start: datetime, end: datetime) -> int:
        """Count total occurrences of a metric."""
        metrics = await self.metrics.get_metrics(metric_name, start, end)
        return int(sum(m.value for m in metrics))
        
    async def _get_avg_metric(self, metric_name: str, start: datetime, end: datetime) -> float:
        """Get average value of a metric."""
        metrics = await self.metrics.get_metrics(metric_name, start, end)
        if not metrics:
            return 0.0
        return sum(m.value for m in metrics) / len(metrics)
        
    async def _get_latency_stats(self, metric_name: str, start: datetime, end: datetime) -> Dict[str, float]:
        """Get latency statistics for a metric."""
        metrics = await self.metrics.get_metrics(metric_name, start, end)
        if not metrics:
            return {"avg": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0}
            
        import numpy as np
        values = [m.value for m in metrics]
        
        return {
            "avg": np.mean(values),
            "p50": np.percentile(values, 50),
            "p95": np.percentile(values, 95),
            "p99": np.percentile(values, 99)
        }
        
    async def _get_hourly_breakdown(self, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        """Get hourly breakdown of key metrics."""
        hourly_data = await self.metrics.get_aggregated_metrics(
            "api.calls.total", start, end,
            interval_minutes=60,
            aggregation="count"
        )
        
        breakdown = []
        for data_point in hourly_data:
            hour_start = data_point["timestamp"]
            hour_end = hour_start + timedelta(hours=1)
            
            breakdown.append({
                "hour": data_point["timestamp"].hour,
                "api_calls": data_point["count"],
                "cost": float(await self.metrics.get_cost_sum(hour_start, hour_end))
            })
            
        return breakdown
        
    async def _get_top_errors(self, start: datetime, end: datetime, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top errors by frequency."""
        # In a real implementation, would query errors with grouping
        # For now, return empty list
        return []
        
    async def _get_cost_by_model_detailed(self, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        """Get detailed cost breakdown by model."""
        cost_by_model = await self.analytics._get_cost_by_model(start, end)
        
        # Get call counts by model
        model_details = []
        total_cost = sum(cost_by_model.values())
        
        for model, cost in cost_by_model.items():
            # Get call count for this model
            calls = await self.metrics.get_metrics(
                "api.calls.total", start, end,
                tags={"model": model}
            )
            call_count = sum(m.value for m in calls)
            
            model_details.append({
                "name": model,
                "total_cost": float(cost),
                "percentage": (float(cost) / float(total_cost) * 100) if total_cost > 0 else 0,
                "call_count": int(call_count),
                "avg_per_call": float(cost) / call_count if call_count > 0 else 0
            })
            
        return sorted(model_details, key=lambda x: x["total_cost"], reverse=True)
        
    def _get_budget_status(self, cost_analysis: Any) -> str:
        """Get budget status description."""
        if not cost_analysis.budget_utilization:
            return "No budget configured"
            
        if cost_analysis.budget_utilization >= 1.0:
            return "OVER BUDGET"
        elif cost_analysis.budget_utilization >= 0.9:
            return "Critical - 90% of budget used"
        elif cost_analysis.budget_utilization >= 0.75:
            return "Warning - 75% of budget used"
        else:
            return "Within budget"
            
    def _get_cost_recommendations(self, cost_analysis: Any, cost_by_model: List[Dict[str, Any]]) -> List[str]:
        """Generate cost optimization recommendations."""
        recommendations = []
        
        # Check if costs are increasing
        if cost_analysis.cost_trend == TrendDirection.INCREASING:
            recommendations.append("Costs are trending upward. Consider reviewing usage patterns.")
            
        # Check for expensive models
        if cost_by_model:
            top_model = cost_by_model[0]
            if top_model["percentage"] > 80:
                recommendations.append(
                    f"{top_model['name']} accounts for {top_model['percentage']:.0f}% of costs. "
                    "Consider using a more cost-effective model for some tasks."
                )
                
        # Check budget utilization
        if cost_analysis.budget_utilization and cost_analysis.budget_utilization > 0.9:
            recommendations.append("Approaching budget limit. Review and optimize API usage.")
            
        # Check for high average cost per call
        for model in cost_by_model:
            if model["avg_per_call"] > 0.1:  # $0.10 per call threshold
                recommendations.append(
                    f"{model['name']} has high average cost per call (${model['avg_per_call']:.3f}). "
                    "Consider batching requests or caching results."
                )
                
        return recommendations
        
    async def _suggest_improvements(self, performance: Dict[str, Any], trends: Dict[str, Any]) -> List[str]:
        """Suggest performance improvements based on analysis."""
        improvements = []
        
        # Check API latency
        if performance["api_performance"]["p95_latency_ms"] > 2000:
            improvements.append("High API latency detected. Consider implementing request pooling.")
            
        # Check success rates
        if performance["api_performance"]["success_rate"] < 0.95:
            improvements.append("API success rate below 95%. Review error patterns and implement retry logic.")
            
        # Check cache performance
        if performance["cache_performance"]["hit_rate"] < 0.8:
            improvements.append("Cache hit rate below 80%. Review cache key strategy and TTL settings.")
            
        # Check processing throughput
        if performance["processing_performance"]["throughput_words_per_sec"] < 10:
            improvements.append("Low processing throughput. Consider parallel processing or optimization.")
            
        return improvements
        
    async def _save_report(self, result: ReportResult):
        """Save report to file and database."""
        # Save to file
        timestamp = result.generated_at.strftime("%Y%m%d_%H%M%S")
        filename = f"{result.report_type.value}_{timestamp}.{result.format.value}"
        file_path = self.reports_dir / filename
        
        async with aiofiles.open(file_path, 'w') as f:
            await f.write(result.content)
            
        # Save to database
        async with aiosqlite.connect(str(self.metrics.db_path)) as db:
            await db.execute("""
                INSERT INTO report_history 
                (report_id, report_name, report_type, format, period_start, 
                 period_end, file_path, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.report_id,
                result.report_type.value,
                result.report_type.value,
                result.format.value,
                result.period_start.isoformat(),
                result.period_end.isoformat(),
                str(file_path),
                json.dumps(result.metadata, default=str)
            ))
            await db.commit()
            
    async def _update_report_notifications(self, report_id: str, notifications: List[str]):
        """Update report with notification status."""
        async with aiosqlite.connect(str(self.metrics.db_path)) as db:
            await db.execute("""
                UPDATE report_history 
                SET notifications_sent = ?
                WHERE report_id = ?
            """, (json.dumps(notifications), report_id))
            await db.commit()
            
    async def _load_report_configs(self):
        """Load report configurations from database."""
        async with aiosqlite.connect(str(self.metrics.db_path)) as db:
            async with db.execute("SELECT * FROM report_configs WHERE enabled = 1") as cursor:
                async for row in cursor:
                    config = ReportConfig(
                        name=row[1],
                        report_type=ReportType(row[2]),
                        format=ReportFormat(row[3]),
                        schedule=row[4],
                        recipients=json.loads(row[5]) if row[5] else None,
                        webhook_url=row[6],
                        custom_template=row[7],
                        filters=json.loads(row[8]) if row[8] else None,
                        enabled=bool(row[9])
                    )
                    self._report_configs[config.name] = config
                    
    # Report Configuration Management
    
    async def add_report_config(self, config: ReportConfig):
        """Add or update a report configuration."""
        self._report_configs[config.name] = config
        
        async with aiosqlite.connect(str(self.metrics.db_path)) as db:
            await db.execute("""
                INSERT OR REPLACE INTO report_configs 
                (name, report_type, format, schedule, recipients, webhook_url, 
                 custom_template, filters, enabled, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                config.name,
                config.report_type.value,
                config.format.value,
                config.schedule,
                json.dumps(config.recipients) if config.recipients else None,
                config.webhook_url,
                config.custom_template,
                json.dumps(config.filters) if config.filters else None,
                int(config.enabled)
            ))
            await db.commit()
            
        # Schedule if needed
        if config.schedule and config.enabled:
            await self._schedule_report(config)
            
    async def remove_report_config(self, name: str):
        """Remove a report configuration."""
        if name in self._report_configs:
            del self._report_configs[name]
            
            # Cancel scheduled task
            if name in self._scheduled_tasks:
                self._scheduled_tasks[name].cancel()
                del self._scheduled_tasks[name]
                
            async with aiosqlite.connect(str(self.metrics.db_path)) as db:
                await db.execute("DELETE FROM report_configs WHERE name = ?", (name,))
                await db.commit()
                
    async def _schedule_report(self, config: ReportConfig):
        """Schedule a report based on configuration."""
        # In a real implementation, would use a proper scheduler like APScheduler
        # For now, just create a simple periodic task
        
        if config.name in self._scheduled_tasks:
            self._scheduled_tasks[config.name].cancel()
            
        async def run_scheduled_report():
            while True:
                try:
                    # Wait for next scheduled time
                    # Simple daily schedule for demo
                    await asyncio.sleep(86400)  # 24 hours
                    
                    # Generate report based on type
                    if config.report_type == ReportType.DAILY_SUMMARY:
                        result = await self.generate_daily_summary(format=config.format)
                    elif config.report_type == ReportType.WEEKLY_PERFORMANCE:
                        result = await self.generate_weekly_performance(format=config.format)
                    elif config.report_type == ReportType.MONTHLY_COST:
                        now = datetime.utcnow()
                        result = await self.generate_monthly_cost(now.year, now.month, format=config.format)
                    else:
                        # Custom report
                        end_time = datetime.utcnow()
                        start_time = end_time - timedelta(days=1)
                        result = await self.generate_custom_report(config, start_time, end_time)
                        
                    # Send report
                    await self.send_report(result, config)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in scheduled report {config.name}: {e}")
                    
        task = asyncio.create_task(run_scheduled_report())
        self._scheduled_tasks[config.name] = task