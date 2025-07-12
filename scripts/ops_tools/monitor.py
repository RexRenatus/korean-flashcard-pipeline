#!/usr/bin/env python3
"""
Unified Monitoring and Health Check Tool
Combines system health checks with monitoring dashboard
"""

import argparse
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List
import psutil
from rich.console import Console
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.python.flashcard_pipeline.services.monitoring import MonitoringService
from src.python.flashcard_pipeline.database import DatabaseManager
from src.python.flashcard_pipeline.cache import CacheService
from src.python.flashcard_pipeline.utils import setup_logging, get_logger, format_file_size

logger = get_logger(__name__)
console = Console()


class SystemMonitor:
    """Comprehensive system monitoring and health check tool"""
    
    def __init__(self):
        self.monitoring_service = MonitoringService()
        self.db_manager = DatabaseManager()
        self.cache_service = CacheService()
    
    async def check_health(self, detailed: bool = False) -> Dict[str, Any]:
        """Run comprehensive health check"""
        logger.info("Running system health check...")
        
        health_status = await self.monitoring_service.check_health()
        
        if detailed:
            # Add detailed system information
            health_status["system"] = self._get_system_info()
            health_status["processes"] = self._get_process_info()
        
        return health_status
    
    def monitor_live(self, refresh_interval: int = 5):
        """Live monitoring dashboard"""
        logger.info("Starting live monitoring dashboard...")
        
        layout = self._create_layout()
        
        with Live(layout, refresh_per_second=1/refresh_interval, console=console) as live:
            try:
                while True:
                    asyncio.run(self._update_dashboard(layout))
                    asyncio.run(asyncio.sleep(refresh_interval))
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
    
    async def generate_report(self, format: str = "text") -> str:
        """Generate system health report"""
        health_data = await self.check_health(detailed=True)
        metrics = await self.monitoring_service.get_metrics()
        
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "health": health_data,
            "metrics": metrics,
            "recommendations": self._generate_recommendations(health_data, metrics)
        }
        
        if format == "json":
            return json.dumps(report_data, indent=2)
        elif format == "markdown":
            return self._format_markdown_report(report_data)
        else:
            return self._format_text_report(report_data)
    
    def _create_layout(self) -> Layout:
        """Create dashboard layout"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        layout["left"].split_column(
            Layout(name="system", ratio=1),
            Layout(name="database", ratio=1)
        )
        
        layout["right"].split_column(
            Layout(name="api", ratio=1),
            Layout(name="cache", ratio=1)
        )
        
        return layout
    
    async def _update_dashboard(self, layout: Layout):
        """Update dashboard with latest data"""
        # Get latest health data
        health = await self.check_health()
        
        # Update header
        layout["header"].update(
            Panel(
                f"[bold]Flashcard Pipeline Monitor[/bold]\n"
                f"Status: {self._get_overall_status(health)} | "
                f"Updated: {datetime.now().strftime('%H:%M:%S')}",
                style="blue"
            )
        )
        
        # Update system panel
        system_info = self._get_system_info()
        system_table = Table(show_header=False, box=None)
        system_table.add_column("Metric", style="cyan")
        system_table.add_column("Value", style="white")
        
        system_table.add_row("CPU Usage", f"{system_info['cpu_percent']}%")
        system_table.add_row("Memory", f"{system_info['memory_percent']}%")
        system_table.add_row("Disk", f"{system_info['disk_percent']}%")
        
        layout["system"].update(
            Panel(system_table, title="System Resources", border_style="green")
        )
        
        # Update database panel
        db_health = health["components"].get("database", {})
        db_table = Table(show_header=False, box=None)
        db_table.add_column("Metric", style="cyan")
        db_table.add_column("Value", style="white")
        
        if db_health.get("healthy"):
            stats = db_health.get("details", {}).get("statistics", {})
            db_table.add_row("Status", "[green]Healthy[/green]")
            db_table.add_row("Vocabulary", str(stats.get("vocabulary_count", 0)))
            db_table.add_row("Tasks", str(stats.get("processing_tasks_count", 0)))
            db_table.add_row("Flashcards", str(stats.get("flashcards_count", 0)))
        else:
            db_table.add_row("Status", "[red]Unhealthy[/red]")
            db_table.add_row("Error", str(db_health.get("error", "Unknown")))
        
        layout["database"].update(
            Panel(db_table, title="Database", border_style="blue")
        )
        
        # Update API panel
        api_health = health["components"].get("api", {})
        api_table = Table(show_header=False, box=None)
        api_table.add_column("Metric", style="cyan")
        api_table.add_column("Value", style="white")
        
        if api_health.get("healthy"):
            api_table.add_row("Status", "[green]Connected[/green]")
            api_table.add_row("Response Time", f"{api_health.get('response_time_ms', 0):.0f}ms")
        else:
            api_table.add_row("Status", "[red]Disconnected[/red]")
            api_table.add_row("Error", str(api_health.get("error", "Unknown")))
        
        layout["api"].update(
            Panel(api_table, title="API Status", border_style="yellow")
        )
        
        # Update cache panel
        cache_health = health["components"].get("cache", {})
        cache_table = Table(show_header=False, box=None)
        cache_table.add_column("Metric", style="cyan")
        cache_table.add_column("Value", style="white")
        
        if cache_health.get("healthy"):
            stats = cache_health.get("details", {})
            cache_table.add_row("Status", "[green]Active[/green]")
            cache_table.add_row("Items", str(stats.get("total_items", 0)))
            cache_table.add_row("Size", format_file_size(stats.get("total_size", 0)))
        else:
            cache_table.add_row("Status", "[red]Error[/red]")
            cache_table.add_row("Error", str(cache_health.get("error", "Unknown")))
        
        layout["cache"].update(
            Panel(cache_table, title="Cache", border_style="magenta")
        )
        
        # Update footer
        layout["footer"].update(
            Panel(
                "[dim]Press Ctrl+C to exit[/dim]",
                style="dim"
            )
        )
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system resource information"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used": psutil.virtual_memory().used,
            "memory_total": psutil.virtual_memory().total,
            "disk_percent": psutil.disk_usage('/').percent,
            "disk_used": psutil.disk_usage('/').used,
            "disk_total": psutil.disk_usage('/').total,
            "process_count": len(psutil.pids())
        }
    
    def _get_process_info(self) -> Dict[str, Any]:
        """Get current process information"""
        process = psutil.Process()
        return {
            "pid": process.pid,
            "cpu_percent": process.cpu_percent(),
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "threads": process.num_threads(),
            "open_files": len(process.open_files()),
            "connections": len(process.connections())
        }
    
    def _get_overall_status(self, health: Dict[str, Any]) -> str:
        """Determine overall system status"""
        if health["overall_health"] == "healthy":
            return "[green]✓ Healthy[/green]"
        elif health["overall_health"] == "degraded":
            return "[yellow]⚠ Degraded[/yellow]"
        else:
            return "[red]✗ Unhealthy[/red]"
    
    def _generate_recommendations(
        self, 
        health: Dict[str, Any], 
        metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate system optimization recommendations"""
        recommendations = []
        
        # Check system resources
        system_info = self._get_system_info()
        if system_info["cpu_percent"] > 80:
            recommendations.append(
                "High CPU usage detected. Consider optimizing concurrent operations."
            )
        
        if system_info["memory_percent"] > 80:
            recommendations.append(
                "High memory usage. Consider increasing cache cleanup frequency."
            )
        
        # Check database health
        db_health = health["components"].get("database", {})
        if db_health.get("details", {}).get("statistics", {}).get("processing_tasks_count", 0) > 1000:
            recommendations.append(
                "Large number of pending tasks. Consider increasing processing workers."
            )
        
        # Check cache efficiency
        cache_metrics = metrics.get("cache", {})
        hit_rate = cache_metrics.get("hit_rate", 0)
        if hit_rate < 0.7:
            recommendations.append(
                f"Low cache hit rate ({hit_rate:.1%}). Consider cache warming for frequent terms."
            )
        
        return recommendations
    
    def _format_text_report(self, report_data: Dict[str, Any]) -> str:
        """Format report as text"""
        lines = []
        lines.append("=" * 60)
        lines.append("SYSTEM HEALTH REPORT")
        lines.append(f"Generated: {report_data['timestamp']}")
        lines.append("=" * 60)
        lines.append("")
        
        # Overall health
        health = report_data["health"]
        lines.append(f"Overall Status: {health['overall_health'].upper()}")
        lines.append("")
        
        # Component health
        lines.append("Component Health:")
        lines.append("-" * 40)
        for component, status in health["components"].items():
            health_status = "✓" if status.get("healthy") else "✗"
            lines.append(f"{health_status} {component}: {status.get('status', 'unknown')}")
        lines.append("")
        
        # System resources
        system = report_data["health"].get("system", {})
        if system:
            lines.append("System Resources:")
            lines.append("-" * 40)
            lines.append(f"CPU Usage: {system['cpu_percent']}%")
            lines.append(f"Memory Usage: {system['memory_percent']}%")
            lines.append(f"Disk Usage: {system['disk_percent']}%")
            lines.append("")
        
        # Recommendations
        if report_data["recommendations"]:
            lines.append("Recommendations:")
            lines.append("-" * 40)
            for i, rec in enumerate(report_data["recommendations"], 1):
                lines.append(f"{i}. {rec}")
        
        return "\n".join(lines)
    
    def _format_markdown_report(self, report_data: Dict[str, Any]) -> str:
        """Format report as markdown"""
        lines = []
        lines.append("# System Health Report")
        lines.append("")
        lines.append(f"Generated: {report_data['timestamp']}")
        lines.append("")
        
        # Overall health
        health = report_data["health"]
        lines.append(f"## Overall Status: **{health['overall_health'].upper()}**")
        lines.append("")
        
        # Component health
        lines.append("## Component Health")
        lines.append("")
        lines.append("| Component | Status | Health |")
        lines.append("|-----------|--------|--------|")
        
        for component, status in health["components"].items():
            health_icon = "✅" if status.get("healthy") else "❌"
            lines.append(
                f"| {component} | {status.get('status', 'unknown')} | {health_icon} |"
            )
        lines.append("")
        
        # System resources
        system = report_data["health"].get("system", {})
        if system:
            lines.append("## System Resources")
            lines.append("")
            lines.append(f"- **CPU Usage**: {system['cpu_percent']}%")
            lines.append(f"- **Memory Usage**: {system['memory_percent']}%")
            lines.append(f"- **Disk Usage**: {system['disk_percent']}%")
            lines.append("")
        
        # Recommendations
        if report_data["recommendations"]:
            lines.append("## Recommendations")
            lines.append("")
            for rec in report_data["recommendations"]:
                lines.append(f"- {rec}")
        
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="System Monitor - Health checks and live monitoring"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Health check command
    health_parser = subparsers.add_parser("health", help="Run health check")
    health_parser.add_argument(
        "--detailed",
        action="store_true",
        help="Include detailed system information"
    )
    health_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format"
    )
    
    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Live monitoring dashboard")
    monitor_parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Refresh interval in seconds"
    )
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate health report")
    report_parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Report format"
    )
    
    # Global options
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Setup logging
    setup_logging(verbose=args.verbose)
    
    # Create monitor
    monitor = SystemMonitor()
    
    try:
        if args.command == "health":
            health = asyncio.run(monitor.check_health(detailed=args.detailed))
            
            if args.format == "json":
                print(json.dumps(health, indent=2))
            else:
                # Simple text output
                print(f"\nOverall Health: {health['overall_health'].upper()}")
                print("\nComponent Status:")
                for component, status in health["components"].items():
                    icon = "✓" if status.get("healthy") else "✗"
                    print(f"  {icon} {component}: {status.get('status', 'unknown')}")
            
            return 0 if health["overall_health"] == "healthy" else 1
        
        elif args.command == "monitor":
            monitor.monitor_live(refresh_interval=args.interval)
            return 0
        
        elif args.command == "report":
            report = asyncio.run(monitor.generate_report(format=args.format))
            print(report)
            return 0
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 0
    except Exception as e:
        logger.error(f"Command failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())