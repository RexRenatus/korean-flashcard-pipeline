#!/usr/bin/env python3
"""
CLI tool for monitoring flashcard pipeline.

This script provides:
- Live monitoring dashboard
- Metric queries and analysis
- Alert management
- Cost budget configuration
"""

import asyncio
import click
import json
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
from rich.console import Console
from rich.table import Table
from rich import box
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.python.flashcard_pipeline.monitoring import (
    MetricsCollector,
    AnalyticsService,
    Dashboard,
    AlertRule,
    CostBudget,
    MetricCategory
)

console = Console()


@click.group()
@click.option('--db', '-d', default='metrics.db', help='Metrics database path')
@click.pass_context
def cli(ctx, db):
    """Flashcard Pipeline Monitoring Dashboard"""
    ctx.ensure_object(dict)
    ctx.obj['db_path'] = Path(db)


@cli.command()
@click.option('--refresh', '-r', default=5, help='Refresh interval in seconds')
@click.option('--view', '-v', default='overview', 
              type=click.Choice(['overview', 'processing', 'cost', 'performance', 'alerts']))
@click.pass_context
def dashboard(ctx, refresh, view):
    """Run live monitoring dashboard"""
    async def run():
        db_path = ctx.obj['db_path']
        
        # Initialize components
        metrics = MetricsCollector(db_path)
        await metrics.initialize()
        
        analytics = AnalyticsService(metrics)
        dashboard_instance = Dashboard(metrics, analytics)
        dashboard_instance.current_view = view
        
        try:
            await dashboard_instance.run(refresh_interval=refresh)
        finally:
            await metrics.shutdown()
            
    asyncio.run(run())


@cli.command()
@click.argument('metric_name')
@click.option('--hours', '-h', default=24, help='Hours of history')
@click.option('--interval', '-i', default=60, help='Aggregation interval in minutes')
@click.option('--aggregation', '-a', default='avg',
              type=click.Choice(['avg', 'sum', 'min', 'max', 'count']))
@click.pass_context
def metric(ctx, metric_name, hours, interval, aggregation):
    """Display specific metric data"""
    async def run():
        db_path = ctx.obj['db_path']
        
        metrics = MetricsCollector(db_path)
        await metrics.initialize()
        
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            # Get aggregated data
            data = await metrics.get_aggregated_metrics(
                metric_name, start_time, end_time,
                interval_minutes=interval,
                aggregation=aggregation
            )
            
            if not data:
                console.print(f"[yellow]No data found for metric: {metric_name}[/yellow]")
                return
                
            # Display data in table
            table = Table(
                title=f"{metric_name} ({aggregation}) - Last {hours} hours",
                box=box.ROUNDED
            )
            table.add_column("Time", style="cyan")
            table.add_column("Value", justify="right")
            table.add_column("Count", justify="right", style="dim")
            
            for point in data:
                table.add_row(
                    point["timestamp"].strftime("%Y-%m-%d %H:%M"),
                    f"{point['value']:.2f}",
                    str(point["count"])
                )
                
            console.print(table)
            
            # Show summary statistics
            values = [p["value"] for p in data]
            if values:
                import numpy as np
                console.print("\n[bold]Summary Statistics:[/bold]")
                console.print(f"  Mean: {np.mean(values):.2f}")
                console.print(f"  Std Dev: {np.std(values):.2f}")
                console.print(f"  Min: {min(values):.2f}")
                console.print(f"  Max: {max(values):.2f}")
                
        finally:
            await metrics.shutdown()
            
    asyncio.run(run())


@cli.command()
@click.option('--period', '-p', default=7, help='Analysis period in days')
@click.pass_context
def analyze(ctx, period):
    """Run comprehensive analysis"""
    async def run():
        db_path = ctx.obj['db_path']
        
        metrics = MetricsCollector(db_path)
        await metrics.initialize()
        
        analytics = AnalyticsService(metrics)
        
        try:
            console.print("[bold cyan]Running comprehensive analysis...[/bold cyan]\n")
            
            # Cost analysis
            console.print("[bold]Cost Analysis:[/bold]")
            cost_analysis = await analytics.analyze_costs(period)
            
            table = Table(box=box.SIMPLE)
            table.add_column("Metric", style="cyan")
            table.add_column("Value", justify="right")
            
            table.add_row("Total Cost", f"${cost_analysis.total_cost:.2f}")
            table.add_row("Daily Average", f"${cost_analysis.average_daily_cost:.2f}")
            table.add_row("Projected Monthly", f"${cost_analysis.projected_monthly_cost:.2f}")
            table.add_row("Cost Trend", cost_analysis.cost_trend.value)
            
            if cost_analysis.budget_utilization:
                table.add_row("Budget Utilization", f"{cost_analysis.budget_utilization:.1%}")
                
            console.print(table)
            
            # Performance analysis
            console.print("\n[bold]Performance Analysis:[/bold]")
            performance = await analytics.analyze_performance(period)
            
            perf_table = Table(box=box.SIMPLE)
            perf_table.add_column("Component", style="cyan")
            perf_table.add_column("Avg Latency", justify="right")
            perf_table.add_column("P95 Latency", justify="right")
            perf_table.add_column("Success Rate", justify="right")
            
            api_perf = performance["api_performance"]
            perf_table.add_row(
                "API",
                f"{api_perf['avg_latency_ms']:.0f}ms",
                f"{api_perf['p95_latency_ms']:.0f}ms",
                f"{api_perf['success_rate']:.1%}"
            )
            
            proc_perf = performance["processing_performance"]
            perf_table.add_row(
                "Processing",
                f"{proc_perf['avg_latency_ms']:.0f}ms",
                f"{proc_perf['p95_latency_ms']:.0f}ms",
                f"{proc_perf['success_rate']:.1%}"
            )
            
            console.print(perf_table)
            
            # Usage patterns
            console.print("\n[bold]Usage Patterns:[/bold]")
            usage = await analytics.detect_usage_patterns(period)
            
            console.print(f"  Pattern Type: {usage.pattern_type}")
            console.print(f"  Description: {usage.description}")
            console.print(f"  Peak Hours: {', '.join(map(str, usage.peak_hours))}")
            console.print(f"  Average Load: {usage.average_load['calls_per_hour']:.1f} calls/hour")
            
            if usage.recommendations:
                console.print("\n[bold]Recommendations:[/bold]")
                for rec in usage.recommendations:
                    console.print(f"  • {rec}")
                    
            # Anomalies
            console.print("\n[bold]Anomaly Detection:[/bold]")
            anomalies = await analytics.detect_anomalies("api.calls.total", period)
            
            if anomalies:
                anomaly_table = Table(box=box.SIMPLE)
                anomaly_table.add_column("Time", style="cyan")
                anomaly_table.add_column("Type", style="yellow")
                anomaly_table.add_column("Severity", justify="right")
                anomaly_table.add_column("Value", justify="right")
                
                for anomaly in anomalies[:5]:  # Show top 5
                    anomaly_table.add_row(
                        anomaly.timestamp.strftime("%Y-%m-%d %H:%M"),
                        anomaly.anomaly_type.value,
                        f"{anomaly.severity:.1%}",
                        f"{anomaly.actual_value:.1f}"
                    )
                    
                console.print(anomaly_table)
            else:
                console.print("  No anomalies detected")
                
        finally:
            await metrics.shutdown()
            
    asyncio.run(run())


@cli.group()
def alerts():
    """Manage alert rules"""
    pass


@alerts.command('add')
@click.option('--name', '-n', required=True, help='Alert name')
@click.option('--metric', '-m', required=True, help='Metric to monitor')
@click.option('--threshold', '-t', required=True, type=float, help='Alert threshold')
@click.option('--comparison', '-c', required=True,
              type=click.Choice(['gt', 'lt', 'eq', 'gte', 'lte']),
              help='Comparison operator')
@click.option('--window', '-w', default=5, help='Window in minutes')
@click.option('--cooldown', default=15, help='Cooldown in minutes')
@click.pass_context
def add_alert(ctx, name, metric, threshold, comparison, window, cooldown):
    """Add a new alert rule"""
    async def run():
        db_path = ctx.obj['db_path']
        
        metrics = MetricsCollector(db_path)
        await metrics.initialize()
        
        try:
            rule = AlertRule(
                name=name,
                metric_name=metric,
                threshold=threshold,
                comparison=comparison,
                window_minutes=window,
                cooldown_minutes=cooldown,
                actions=["log"]
            )
            
            await metrics.add_alert_rule(rule)
            console.print(f"[green]✓ Alert rule '{name}' added successfully[/green]")
            
        finally:
            await metrics.shutdown()
            
    asyncio.run(run())


@alerts.command('list')
@click.pass_context
def list_alerts(ctx):
    """List all alert rules"""
    async def run():
        db_path = ctx.obj['db_path']
        
        metrics = MetricsCollector(db_path)
        await metrics.initialize()
        
        try:
            # In real implementation, would load from database
            # For now, show from in-memory rules
            rules = metrics._alert_rules.values()
            
            if not rules:
                console.print("[yellow]No alert rules configured[/yellow]")
                return
                
            table = Table(title="Alert Rules", box=box.ROUNDED)
            table.add_column("Name", style="cyan")
            table.add_column("Metric", style="yellow")
            table.add_column("Condition")
            table.add_column("Window")
            table.add_column("Status")
            
            for rule in rules:
                status = "[green]Active[/green]" if rule.enabled else "[red]Disabled[/red]"
                table.add_row(
                    rule.name,
                    rule.metric_name,
                    f"{rule.comparison} {rule.threshold}",
                    f"{rule.window_minutes}m",
                    status
                )
                
            console.print(table)
            
        finally:
            await metrics.shutdown()
            
    asyncio.run(run())


@alerts.command('remove')
@click.argument('name')
@click.pass_context
def remove_alert(ctx, name):
    """Remove an alert rule"""
    async def run():
        db_path = ctx.obj['db_path']
        
        metrics = MetricsCollector(db_path)
        await metrics.initialize()
        
        try:
            await metrics.remove_alert_rule(name)
            console.print(f"[green]✓ Alert rule '{name}' removed[/green]")
            
        finally:
            await metrics.shutdown()
            
    asyncio.run(run())


@cli.group()
def budget():
    """Manage cost budgets"""
    pass


@budget.command('set')
@click.option('--daily', '-d', required=True, type=float, help='Daily limit in USD')
@click.option('--weekly', '-w', required=True, type=float, help='Weekly limit in USD')
@click.option('--monthly', '-m', required=True, type=float, help='Monthly limit in USD')
@click.pass_context
def set_budget(ctx, daily, weekly, monthly):
    """Set cost budget limits"""
    async def run():
        db_path = ctx.obj['db_path']
        
        metrics = MetricsCollector(db_path)
        await metrics.initialize()
        
        try:
            budget = CostBudget(
                daily_limit=Decimal(str(daily)),
                weekly_limit=Decimal(str(weekly)),
                monthly_limit=Decimal(str(monthly))
            )
            
            await metrics.set_cost_budget(budget)
            console.print("[green]✓ Cost budget set successfully[/green]")
            console.print(f"  Daily: ${daily:.2f}")
            console.print(f"  Weekly: ${weekly:.2f}")
            console.print(f"  Monthly: ${monthly:.2f}")
            
        finally:
            await metrics.shutdown()
            
    asyncio.run(run())


@budget.command('status')
@click.pass_context
def budget_status(ctx):
    """Show current budget status"""
    async def run():
        db_path = ctx.obj['db_path']
        
        metrics = MetricsCollector(db_path)
        await metrics.initialize()
        
        analytics = AnalyticsService(metrics)
        
        try:
            if not metrics._cost_budget:
                console.print("[yellow]No budget configured[/yellow]")
                return
                
            budget = metrics._cost_budget
            
            # Get current costs
            now = datetime.utcnow()
            daily_cost = await metrics.get_cost_sum(
                now.replace(hour=0, minute=0, second=0),
                now
            )
            weekly_cost = await metrics.get_cost_sum(
                now - timedelta(days=now.weekday()),
                now
            )
            monthly_cost = await metrics.get_cost_sum(
                now.replace(day=1, hour=0, minute=0, second=0),
                now
            )
            
            # Display budget status
            table = Table(title="Budget Status", box=box.ROUNDED)
            table.add_column("Period", style="cyan")
            table.add_column("Spent", justify="right")
            table.add_column("Limit", justify="right")
            table.add_column("Utilization", justify="right")
            table.add_column("Status", justify="center")
            
            # Daily
            daily_util = daily_cost / float(budget.daily_limit)
            daily_status = _get_budget_status_icon(daily_util)
            table.add_row(
                "Daily",
                f"${daily_cost:.2f}",
                f"${budget.daily_limit:.2f}",
                f"{daily_util:.1%}",
                daily_status
            )
            
            # Weekly
            weekly_util = weekly_cost / float(budget.weekly_limit)
            weekly_status = _get_budget_status_icon(weekly_util)
            table.add_row(
                "Weekly",
                f"${weekly_cost:.2f}",
                f"${budget.weekly_limit:.2f}",
                f"{weekly_util:.1%}",
                weekly_status
            )
            
            # Monthly
            monthly_util = monthly_cost / float(budget.monthly_limit)
            monthly_status = _get_budget_status_icon(monthly_util)
            table.add_row(
                "Monthly",
                f"${monthly_cost:.2f}",
                f"${budget.monthly_limit:.2f}",
                f"{monthly_util:.1%}",
                monthly_status
            )
            
            console.print(table)
            
            # Show warnings
            if daily_util > 0.9:
                console.print("\n[red]⚠️  Daily budget nearly exceeded![/red]")
            if weekly_util > 0.9:
                console.print("[red]⚠️  Weekly budget nearly exceeded![/red]")
            if monthly_util > 0.9:
                console.print("[red]⚠️  Monthly budget nearly exceeded![/red]")
                
        finally:
            await metrics.shutdown()
            
    asyncio.run(run())


def _get_budget_status_icon(utilization: float) -> str:
    """Get status icon based on budget utilization."""
    if utilization >= 1.0:
        return "[red]❌ OVER[/red]"
    elif utilization >= 0.9:
        return "[red]⚠️  Critical[/red]"
    elif utilization >= 0.75:
        return "[yellow]⚠️  Warning[/yellow]"
    else:
        return "[green]✅ OK[/green]"


@cli.command()
@click.pass_context
def live_metrics(ctx):
    """Show live metrics summary"""
    async def run():
        db_path = ctx.obj['db_path']
        
        metrics = MetricsCollector(db_path)
        await metrics.initialize()
        
        try:
            # Get live metrics
            live_data = metrics.get_live_metrics()
            
            if not live_data:
                console.print("[yellow]No live metrics available[/yellow]")
                return
                
            # Group by category
            by_category = {}
            for key, data in live_data.items():
                category = data["category"]
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(data)
                
            # Display each category
            for category, metrics_list in by_category.items():
                table = Table(title=f"{category.upper()} Metrics", box=box.SIMPLE)
                table.add_column("Metric", style="cyan")
                table.add_column("Last Value", justify="right")
                table.add_column("Average", justify="right")
                table.add_column("Count", justify="right", style="dim")
                
                for metric in sorted(metrics_list, key=lambda x: x["name"]):
                    table.add_row(
                        metric["name"],
                        f"{metric['last_value']:.2f}",
                        f"{metric['avg']:.2f}",
                        str(metric["count"])
                    )
                    
                console.print(table)
                console.print()
                
        finally:
            await metrics.shutdown()
            
    asyncio.run(run())


@cli.command()
@click.option('--output', '-o', default='-', help='Output file (- for stdout)')
@click.pass_context
def export_metrics(ctx, output):
    """Export metrics data"""
    async def run():
        db_path = ctx.obj['db_path']
        
        metrics = MetricsCollector(db_path)
        await metrics.initialize()
        
        try:
            # Get last 24 hours of data
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)
            
            # Export key metrics
            export_data = {
                "export_time": end_time.isoformat(),
                "period": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "metrics": {}
            }
            
            # Get data for each key metric
            key_metrics = [
                "api.calls.total",
                "api.cost.total",
                "api.call.duration",
                "processing.words.total",
                "processing.duration",
                "cache.hits.total",
                "cache.misses.total"
            ]
            
            for metric_name in key_metrics:
                data = await metrics.get_aggregated_metrics(
                    metric_name, start_time, end_time,
                    interval_minutes=60,
                    aggregation="avg"
                )
                
                export_data["metrics"][metric_name] = [
                    {
                        "timestamp": point["timestamp"].isoformat(),
                        "value": point["value"],
                        "count": point["count"]
                    }
                    for point in data
                ]
                
            # Write output
            json_output = json.dumps(export_data, indent=2)
            
            if output == '-':
                console.print(json_output)
            else:
                with open(output, 'w') as f:
                    f.write(json_output)
                console.print(f"[green]✓ Metrics exported to {output}[/green]")
                
        finally:
            await metrics.shutdown()
            
    asyncio.run(run())


if __name__ == '__main__':
    cli()