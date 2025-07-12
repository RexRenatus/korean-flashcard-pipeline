"""
CLI dashboard for real-time monitoring of flashcard pipeline.

This module provides:
- Real-time metrics display
- Processing monitor
- Cost analysis views
- Performance trends visualization
- Alert configuration UI
- ASCII charts using rich
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.columns import Columns
from rich.align import Align
from rich import box
import click

from .metrics_collector import MetricsCollector, AlertRule, CostBudget, MetricCategory
from .analytics_service import AnalyticsService, TrendDirection

logger = logging.getLogger(__name__)


class DashboardView:
    """Base class for dashboard views."""
    
    def __init__(self, metrics: MetricsCollector, analytics: AnalyticsService):
        self.metrics = metrics
        self.analytics = analytics
        self.console = Console()
        
    async def render(self) -> Panel:
        """Render the view as a rich Panel."""
        raise NotImplementedError


class OverviewDashboard(DashboardView):
    """Main overview dashboard showing key metrics."""
    
    async def render(self) -> Panel:
        """Render overview dashboard."""
        # Get live metrics
        live_metrics = self.metrics.get_live_metrics()
        
        # Get recent performance data
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        # Calculate current rates
        api_calls = self._get_metric_value(live_metrics, "api.calls.total", "count", 0)
        api_errors = self._get_metric_value(live_metrics, "api.errors.total", "count", 0)
        processing_words = self._get_metric_value(live_metrics, "processing.words.total", "sum", 0)
        cache_hits = self._get_metric_value(live_metrics, "cache.hits.total", "count", 0)
        cache_misses = self._get_metric_value(live_metrics, "cache.misses.total", "count", 0)
        
        # Calculate rates
        error_rate = (api_errors / api_calls * 100) if api_calls > 0 else 0
        cache_hit_rate = (cache_hits / (cache_hits + cache_misses) * 100) if (cache_hits + cache_misses) > 0 else 0
        
        # Create overview table
        table = Table(title="System Overview", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="green")
        table.add_column("Status", justify="center")
        
        # Add rows
        table.add_row(
            "API Calls (last hour)",
            f"{api_calls:,.0f}",
            self._get_status_icon(error_rate < 5)
        )
        
        table.add_row(
            "Error Rate",
            f"{error_rate:.1f}%",
            self._get_status_icon(error_rate < 5)
        )
        
        table.add_row(
            "Words Processed",
            f"{processing_words:,.0f}",
            self._get_status_icon(True)
        )
        
        table.add_row(
            "Cache Hit Rate",
            f"{cache_hit_rate:.1f}%",
            self._get_status_icon(cache_hit_rate > 80)
        )
        
        # Get current cost
        today_cost = await self.metrics.get_cost_sum(
            datetime.utcnow().replace(hour=0, minute=0, second=0),
            datetime.utcnow()
        )
        
        table.add_row(
            "Today's Cost",
            f"${today_cost:.2f}",
            self._get_status_icon(today_cost < 100)  # Assuming $100 daily threshold
        )
        
        # Add system health
        avg_latency = self._get_metric_value(live_metrics, "api.call.duration", "avg", 0)
        table.add_row(
            "Avg API Latency",
            f"{avg_latency:.0f}ms",
            self._get_status_icon(avg_latency < 1000)
        )
        
        return Panel(table, title="📊 Overview", border_style="blue")
        
    def _get_metric_value(self, live_metrics: Dict[str, Any], metric_name: str,
                         field: str, default: float) -> float:
        """Get a specific value from live metrics."""
        for key, data in live_metrics.items():
            if data["name"] == metric_name:
                return data.get(field, default)
        return default
        
    def _get_status_icon(self, is_good: bool) -> str:
        """Get status icon based on condition."""
        return "✅" if is_good else "⚠️"


class ProcessingMonitor(DashboardView):
    """Real-time processing monitor."""
    
    async def render(self) -> Panel:
        """Render processing monitor."""
        # Get live processing metrics
        live_metrics = self.metrics.get_live_metrics()
        
        # Create progress bars for different stages
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            expand=True
        )
        
        # Add tasks for each processing stage
        flashcard_task = progress.add_task("[cyan]Flashcard Generation", total=100)
        nuance_task = progress.add_task("[green]Nuance Creation", total=100)
        
        # Get processing rates
        flashcard_count = self._get_stage_count(live_metrics, "flashcard")
        nuance_count = self._get_stage_count(live_metrics, "nuance")
        
        # Update progress (simplified - in real implementation would track actual progress)
        progress.update(flashcard_task, completed=min(100, flashcard_count % 100))
        progress.update(nuance_task, completed=min(100, nuance_count % 100))
        
        # Create throughput table
        throughput_table = Table(box=box.SIMPLE)
        throughput_table.add_column("Stage", style="cyan")
        throughput_table.add_column("Words/sec", justify="right")
        throughput_table.add_column("Success Rate", justify="right")
        
        # Get throughput data
        flashcard_throughput = self._get_throughput(live_metrics, "flashcard")
        nuance_throughput = self._get_throughput(live_metrics, "nuance")
        
        flashcard_success = await self._get_success_rate("flashcard")
        nuance_success = await self._get_success_rate("nuance")
        
        throughput_table.add_row(
            "Flashcards",
            f"{flashcard_throughput:.1f}",
            f"{flashcard_success:.1%}"
        )
        
        throughput_table.add_row(
            "Nuances",
            f"{nuance_throughput:.1f}",
            f"{nuance_success:.1%}"
        )
        
        # Combine elements
        content = Columns([progress, throughput_table], expand=True)
        
        return Panel(content, title="⚙️ Processing Monitor", border_style="green")
        
    def _get_stage_count(self, live_metrics: Dict[str, Any], stage: str) -> int:
        """Get processing count for a stage."""
        for key, data in live_metrics.items():
            if "processing.batches.total" in key and stage in data.get("tags", {}).get("stage", ""):
                return int(data.get("count", 0))
        return 0
        
    def _get_throughput(self, live_metrics: Dict[str, Any], stage: str) -> float:
        """Get throughput for a stage."""
        for key, data in live_metrics.items():
            if "processing.throughput" in key and stage in data.get("tags", {}).get("stage", ""):
                return data.get("last_value", 0.0)
        return 0.0
        
    async def _get_success_rate(self, stage: str) -> float:
        """Get success rate for a stage."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        total = await self.metrics.get_metrics(
            "processing.batches.total", start_time, end_time,
            tags={"stage": stage}
        )
        
        success = await self.metrics.get_metrics(
            "processing.batches.total", start_time, end_time,
            tags={"stage": stage, "success": "True"}
        )
        
        total_count = sum(m.value for m in total)
        success_count = sum(m.value for m in success)
        
        return success_count / total_count if total_count > 0 else 0.0


class CostAnalyzer(DashboardView):
    """Cost analysis dashboard."""
    
    async def render(self) -> Panel:
        """Render cost analysis."""
        # Get cost analysis
        cost_analysis = await self.analytics.analyze_costs(period_days=7)
        
        # Create main cost table
        cost_table = Table(title="Cost Analysis (7 days)", box=box.ROUNDED)
        cost_table.add_column("Metric", style="cyan")
        cost_table.add_column("Value", justify="right", style="green")
        
        cost_table.add_row("Total Cost", f"${cost_analysis.total_cost:.2f}")
        cost_table.add_row("Daily Average", f"${cost_analysis.average_daily_cost:.2f}")
        cost_table.add_row("Projected Monthly", f"${cost_analysis.projected_monthly_cost:.2f}")
        
        if cost_analysis.budget_utilization is not None:
            utilization_color = "green" if cost_analysis.budget_utilization < 0.8 else "red"
            cost_table.add_row(
                "Budget Utilization",
                f"[{utilization_color}]{cost_analysis.budget_utilization:.1%}[/{utilization_color}]"
            )
            
        if cost_analysis.days_until_budget_exceeded is not None:
            cost_table.add_row(
                "Days Until Budget Exceeded",
                f"{cost_analysis.days_until_budget_exceeded}"
            )
            
        # Create model breakdown table
        model_table = Table(title="Cost by Model", box=box.SIMPLE)
        model_table.add_column("Model", style="cyan")
        model_table.add_column("Cost", justify="right")
        model_table.add_column("Percentage", justify="right")
        
        total_model_cost = sum(cost_analysis.cost_by_model.values())
        for model, cost in sorted(cost_analysis.cost_by_model.items(), 
                                 key=lambda x: x[1], reverse=True):
            percentage = (cost / total_model_cost * 100) if total_model_cost > 0 else 0
            model_table.add_row(
                model,
                f"${cost:.2f}",
                f"{percentage:.1f}%"
            )
            
        # Add trend indicator
        trend_icon = {
            TrendDirection.INCREASING: "📈",
            TrendDirection.DECREASING: "📉",
            TrendDirection.STABLE: "➡️",
            TrendDirection.VOLATILE: "📊"
        }.get(cost_analysis.cost_trend, "❓")
        
        trend_text = Text(f"\nCost Trend: {trend_icon} {cost_analysis.cost_trend.value}")
        
        # Combine elements
        layout = Layout()
        layout.split_row(
            Layout(cost_table),
            Layout(model_table)
        )
        
        content = Columns([layout, trend_text], expand=True)
        
        return Panel(content, title="💰 Cost Analysis", border_style="yellow")


class PerformanceTrends(DashboardView):
    """Performance trends visualization."""
    
    async def render(self) -> Panel:
        """Render performance trends."""
        # Get performance data
        perf = await self.analytics.analyze_performance(period_days=7)
        
        # Create performance table
        perf_table = Table(title="Performance Metrics (7 days)", box=box.ROUNDED)
        perf_table.add_column("Component", style="cyan")
        perf_table.add_column("Avg Latency", justify="right")
        perf_table.add_column("P95 Latency", justify="right")
        perf_table.add_column("Success Rate", justify="right")
        
        # API performance
        api_perf = perf["api_performance"]
        perf_table.add_row(
            "API Calls",
            f"{api_perf['avg_latency_ms']:.0f}ms",
            f"{api_perf['p95_latency_ms']:.0f}ms",
            f"{api_perf['success_rate']:.1%}"
        )
        
        # Processing performance
        proc_perf = perf["processing_performance"]
        perf_table.add_row(
            "Processing",
            f"{proc_perf['avg_latency_ms']:.0f}ms",
            f"{proc_perf['p95_latency_ms']:.0f}ms",
            f"{proc_perf['success_rate']:.1%}"
        )
        
        # Database performance
        db_perf = perf["database_performance"]
        perf_table.add_row(
            "Database",
            f"{db_perf['avg_latency_ms']:.0f}ms",
            f"{db_perf['p95_latency_ms']:.0f}ms",
            "N/A"
        )
        
        # Add cache performance
        cache_text = Text(f"\nCache Hit Rate: {perf['cache_performance']['hit_rate']:.1%}")
        throughput_text = Text(f"Processing Throughput: {proc_perf['throughput_words_per_sec']:.1f} words/sec")
        
        # Create simple ASCII trend chart
        trend_chart = await self._create_trend_chart()
        
        content = Columns([
            perf_table,
            Text.from_markup(trend_chart)
        ], expand=True)
        
        return Panel(content, title="📈 Performance Trends", border_style="magenta")
        
    async def _create_trend_chart(self) -> str:
        """Create simple ASCII trend chart."""
        # Get hourly API call data for last 24 hours
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)
        
        hourly_data = await self.metrics.get_aggregated_metrics(
            "api.calls.total", start_time, end_time,
            interval_minutes=60,
            aggregation="count"
        )
        
        if not hourly_data:
            return "[dim]No data available[/dim]"
            
        # Normalize values for display
        values = [d["count"] for d in hourly_data]
        max_val = max(values) if values else 1
        
        # Create simple bar chart
        chart_lines = ["API Calls (hourly):", ""]
        chart_height = 10
        
        for i, val in enumerate(values[-12:]):  # Last 12 hours
            bar_height = int((val / max_val) * chart_height)
            hour = (datetime.utcnow() - timedelta(hours=12-i)).hour
            bar = "█" * bar_height
            chart_lines.append(f"{hour:02d}h: {bar} {val}")
            
        return "\n".join(chart_lines)


class AlertConfiguration(DashboardView):
    """Alert configuration interface."""
    
    async def render(self) -> Panel:
        """Render alert configuration."""
        # Get current alerts
        alerts = list(self.metrics._alert_rules.values())
        
        # Create alerts table
        alerts_table = Table(title="Active Alerts", box=box.ROUNDED)
        alerts_table.add_column("Name", style="cyan")
        alerts_table.add_column("Metric", style="yellow")
        alerts_table.add_column("Condition", justify="center")
        alerts_table.add_column("Status", justify="center")
        
        for alert in alerts:
            condition = f"{alert.comparison} {alert.threshold}"
            status = "🟢 Active" if alert.enabled else "🔴 Disabled"
            alerts_table.add_row(
                alert.name,
                alert.metric_name,
                condition,
                status
            )
            
        # Get recent alert history
        alert_history = await self._get_recent_alerts()
        
        # Create history table
        history_table = Table(title="Recent Alerts", box=box.SIMPLE)
        history_table.add_column("Time", style="dim")
        history_table.add_column("Alert", style="red")
        history_table.add_column("Value")
        
        for alert in alert_history[:5]:  # Show last 5 alerts
            history_table.add_row(
                alert["time"],
                alert["name"],
                alert["value"]
            )
            
        content = Columns([alerts_table, history_table], expand=True)
        
        return Panel(content, title="🚨 Alert Configuration", border_style="red")
        
    async def _get_recent_alerts(self) -> List[Dict[str, str]]:
        """Get recent alert history."""
        # In a real implementation, query from database
        # For now, return mock data
        return [
            {
                "time": "10:45",
                "name": "High API Cost",
                "value": "$125.50"
            },
            {
                "time": "09:30",
                "name": "Low Cache Hit Rate",
                "value": "65%"
            }
        ]


class Dashboard:
    """Main dashboard controller."""
    
    def __init__(self, metrics: MetricsCollector, analytics: AnalyticsService):
        self.metrics = metrics
        self.analytics = analytics
        self.console = Console()
        self.views = {
            "overview": OverviewDashboard(metrics, analytics),
            "processing": ProcessingMonitor(metrics, analytics),
            "cost": CostAnalyzer(metrics, analytics),
            "performance": PerformanceTrends(metrics, analytics),
            "alerts": AlertConfiguration(metrics, analytics)
        }
        self.current_view = "overview"
        
    async def run(self, refresh_interval: int = 5):
        """Run the dashboard with live updates."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        # Create header
        header = self._create_header()
        layout["header"].update(header)
        
        # Create footer with controls
        footer = self._create_footer()
        layout["footer"].update(footer)
        
        with Live(layout, refresh_per_second=1, screen=True) as live:
            while True:
                try:
                    # Update main content
                    view = self.views[self.current_view]
                    content = await view.render()
                    layout["main"].update(content)
                    
                    # Update timestamp in header
                    header = self._create_header()
                    layout["header"].update(header)
                    
                    # Wait for refresh interval
                    await asyncio.sleep(refresh_interval)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"Dashboard error: {e}")
                    error_panel = Panel(
                        f"[red]Error: {str(e)}[/red]",
                        title="⚠️ Dashboard Error",
                        border_style="red"
                    )
                    layout["main"].update(error_panel)
                    await asyncio.sleep(refresh_interval)
                    
    def _create_header(self) -> Panel:
        """Create dashboard header."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header_text = Text(f"Flashcard Pipeline Monitor - {timestamp}", justify="center")
        header_text.stylize("bold cyan")
        return Panel(header_text, box=box.DOUBLE)
        
    def _create_footer(self) -> Panel:
        """Create dashboard footer with controls."""
        controls = Text(
            "Views: [O]verview | [P]rocessing | [C]ost | [T]rends | [A]lerts | [Q]uit",
            justify="center"
        )
        controls.stylize("dim")
        return Panel(controls, box=box.DOUBLE)
        
    def switch_view(self, view_name: str):
        """Switch to a different view."""
        if view_name in self.views:
            self.current_view = view_name


# CLI commands for dashboard
@click.group()
def cli():
    """Flashcard Pipeline Monitoring Dashboard"""
    pass


@cli.command()
@click.option('--refresh', '-r', default=5, help='Refresh interval in seconds')
@click.option('--view', '-v', default='overview', 
              type=click.Choice(['overview', 'processing', 'cost', 'performance', 'alerts']))
async def live(refresh: int, view: str):
    """Run live monitoring dashboard"""
    # Initialize components (would load from config in real implementation)
    from pathlib import Path
    
    db_path = Path("metrics.db")
    metrics = MetricsCollector(db_path)
    await metrics.initialize()
    
    analytics = AnalyticsService(metrics)
    dashboard = Dashboard(metrics, analytics)
    dashboard.current_view = view
    
    try:
        await dashboard.run(refresh_interval=refresh)
    finally:
        await metrics.shutdown()


@cli.command()
@click.option('--metric', '-m', required=True, help='Metric name to display')
@click.option('--hours', '-h', default=24, help='Hours of history to show')
async def metric(metric: str, hours: int):
    """Display specific metric details"""
    from pathlib import Path
    
    db_path = Path("metrics.db")
    metrics = MetricsCollector(db_path)
    await metrics.initialize()
    
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        data = await metrics.get_aggregated_metrics(
            metric, start_time, end_time,
            interval_minutes=60,
            aggregation="avg"
        )
        
        console = Console()
        table = Table(title=f"{metric} (last {hours} hours)")
        table.add_column("Time", style="cyan")
        table.add_column("Value", justify="right")
        
        for point in data:
            table.add_row(
                point["timestamp"].strftime("%H:%M"),
                f"{point['value']:.2f}"
            )
            
        console.print(table)
        
    finally:
        await metrics.shutdown()


if __name__ == "__main__":
    asyncio.run(cli())