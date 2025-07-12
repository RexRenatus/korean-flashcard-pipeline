"""
Enhanced CLI for flashcard pipeline with comprehensive ingress commands.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import os

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich import print as rprint
import click

from .database import EnhancedDatabaseManager, ValidatedDatabaseManager, PoolConfig
from .ingress_service_enhanced import IngressServiceEnhanced, ImportProgress
from .utils import get_logger

# Set up console and app
console = Console()
app = typer.Typer(
    name="flashcard-pipeline",
    help="Korean Language Flashcard Pipeline - Enhanced CLI"
)

# Create ingress sub-app
ingress_app = typer.Typer(help="Enhanced ingress commands for vocabulary import")
app.add_typer(ingress_app, name="ingress")

logger = get_logger(__name__)


def create_progress_panel(progress: ImportProgress) -> Panel:
    """Create a rich panel showing import progress"""
    content = f"""
[bold cyan]Import Progress[/bold cyan]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Rows:       {progress.total_rows:,}
Processed:        {progress.processed_rows:,} ({progress.progress_percentage:.1f}%)
Successful:       {progress.successful_rows:,}
Duplicates:       {progress.duplicate_rows:,}
Failed:           {progress.failed_rows:,}

Processing Rate:  {progress.rows_per_second:.1f} rows/sec
Elapsed Time:     {progress.elapsed_seconds:.1f}s
Est. Remaining:   {f"{progress.estimated_remaining_seconds:.1f}s" if progress.estimated_remaining_seconds else "N/A"}

[dim]Press Ctrl+C to cancel[/dim]
"""
    
    return Panel(content, title="Import Status", border_style="blue")


def create_error_table(errors: List[dict], limit: int = 10) -> Table:
    """Create a table showing validation errors"""
    table = Table(title="Validation Errors (Latest)")
    table.add_column("Row", style="cyan", width=6)
    table.add_column("Error", style="red", width=50)
    table.add_column("Data", style="yellow", width=40)
    
    # Show latest errors
    for error in errors[-limit:]:
        row_num = str(error.get("row", "?"))
        error_msg = error.get("error", "Unknown error")
        data_preview = str(error.get("data", {}).get("term", ""))[:40]
        
        table.add_row(row_num, error_msg, data_preview)
    
    if len(errors) > limit:
        table.add_row("...", f"And {len(errors) - limit} more errors", "...")
    
    return table


@ingress_app.command("import")
def import_csv(
    csv_file: Path = typer.Argument(..., help="CSV file to import"),
    batch_size: int = typer.Option(100, "--batch-size", "-b", help="Number of items per batch"),
    skip_duplicates: bool = typer.Option(True, "--skip-duplicates/--allow-duplicates", help="Skip duplicate items"),
    validate_only: bool = typer.Option(False, "--validate-only", "-v", help="Only validate without importing"),
    db_path: str = typer.Option("pipeline.db", "--db", help="Database path"),
    show_errors: bool = typer.Option(False, "--show-errors", "-e", help="Show all validation errors")
):
    """Import vocabulary from CSV file with validation and progress tracking"""
    
    if not csv_file.exists():
        console.print(f"[red]Error: File '{csv_file}' not found[/red]")
        raise typer.Exit(1)
    
    # Initialize database and ingress service
    db_manager = EnhancedDatabaseManager(
        db_path=db_path,
        pool_config=PoolConfig(min_connections=2, max_connections=5)
    )
    
    validated_db = ValidatedDatabaseManager(db_manager)
    ingress = IngressServiceEnhanced(validated_db)
    
    try:
        # Create progress callback
        progress_display = None
        
        def progress_callback(progress: ImportProgress):
            nonlocal progress_display
            if progress_display:
                progress_display.update(create_progress_panel(progress))
        
        # Run import with live progress
        with Live(create_progress_panel(ImportProgress()), refresh_per_second=2) as progress_display:
            # Run import
            batch = ingress.import_csv(
                str(csv_file),
                batch_size=batch_size,
                skip_duplicates=skip_duplicates,
                validate_only=validate_only,
                progress_callback=lambda p: progress_display.update(create_progress_panel(p))
            )
        
        # Show final results
        console.print("\n")
        
        if batch.status == "completed":
            console.print(f"[green]✓ Import completed successfully![/green]")
        elif batch.status == "partial":
            console.print(f"[yellow]⚠ Import completed with errors[/yellow]")
        else:
            console.print(f"[red]✗ Import failed[/red]")
        
        # Create summary table
        table = Table(title=f"Import Summary - Batch {batch.batch_id}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Source File", batch.source_file)
        table.add_row("Total Items", f"{batch.progress.total_rows:,}")
        table.add_row("Successful", f"{batch.progress.successful_rows:,}")
        table.add_row("Duplicates", f"{batch.progress.duplicate_rows:,}")
        table.add_row("Failed", f"{batch.progress.failed_rows:,}")
        table.add_row("Success Rate", f"{(batch.progress.successful_rows / batch.progress.total_rows * 100):.1f}%")
        table.add_row("Processing Time", f"{batch.progress.elapsed_seconds:.1f}s")
        table.add_row("Processing Rate", f"{batch.progress.rows_per_second:.1f} items/sec")
        
        console.print(table)
        
        # Show errors if requested
        if show_errors and batch.progress.validation_errors:
            console.print("\n")
            console.print(create_error_table(batch.progress.validation_errors))
            
            # Option to export full error report
            if typer.confirm("\nExport full error report?"):
                report_path = ingress.export_batch_report(batch.batch_id)
                console.print(f"[green]Error report saved to: {report_path}[/green]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Import cancelled by user[/yellow]")
        if 'batch' in locals() and batch.batch_id:
            ingress.cancel_batch(batch.batch_id)
    except Exception as e:
        console.print(f"[red]Import error: {e}[/red]")
        logger.exception("Import failed")
        raise typer.Exit(1)
    finally:
        db_manager.close()
        ingress.close()


@ingress_app.command("list-batches")
def list_batches(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    limit: int = typer.Option(20, "--limit", "-l", help="Number of batches to show"),
    offset: int = typer.Option(0, "--offset", help="Offset for pagination"),
    db_path: str = typer.Option("pipeline.db", "--db", help="Database path")
):
    """List import batches with detailed information"""
    
    db_manager = EnhancedDatabaseManager(db_path=db_path)
    validated_db = ValidatedDatabaseManager(db_manager)
    ingress = IngressServiceEnhanced(validated_db)
    
    try:
        batches = ingress.list_batches(status, limit, offset)
        
        if not batches:
            console.print("[yellow]No batches found[/yellow]")
            return
        
        # Create detailed table
        table = Table(title="Import Batches")
        table.add_column("Batch ID", style="cyan", width=25)
        table.add_column("Source", style="magenta", width=30)
        table.add_column("Total", style="green", justify="right")
        table.add_column("Success", style="blue", justify="right")
        table.add_column("Dup", style="yellow", justify="right")
        table.add_column("Failed", style="red", justify="right")
        table.add_column("Status", style="bold")
        table.add_column("Created", style="dim")
        
        for batch in batches:
            # Format status with color
            status_color = {
                "completed": "green",
                "partial": "yellow",
                "failed": "red",
                "processing": "blue",
                "pending": "dim"
            }.get(batch.status, "white")
            
            status_text = f"[{status_color}]{batch.status}[/{status_color}]"
            
            # Add row
            table.add_row(
                batch.batch_id[:20] + "...",
                Path(batch.source_file).name,
                str(batch.progress.total_rows),
                str(batch.progress.successful_rows),
                str(batch.progress.duplicate_rows),
                str(batch.progress.failed_rows),
                status_text,
                batch.created_at.strftime("%Y-%m-%d %H:%M")
            )
        
        console.print(table)
        
        # Show pagination info
        if len(batches) == limit:
            console.print(f"\n[dim]Showing {limit} batches starting from offset {offset}[/dim]")
            console.print(f"[dim]Use --offset {offset + limit} to see more[/dim]")
        
    finally:
        db_manager.close()
        ingress.close()


@ingress_app.command("status")
def batch_status(
    batch_id: str = typer.Argument(..., help="Batch ID to check"),
    show_errors: bool = typer.Option(False, "--errors", "-e", help="Show validation errors"),
    export_report: bool = typer.Option(False, "--export", help="Export detailed report"),
    db_path: str = typer.Option("pipeline.db", "--db", help="Database path")
):
    """Get detailed status of a specific batch"""
    
    db_manager = EnhancedDatabaseManager(db_path=db_path)
    validated_db = ValidatedDatabaseManager(db_manager)
    ingress = IngressServiceEnhanced(validated_db)
    
    try:
        batch = ingress.get_batch_status(batch_id)
        
        if not batch:
            console.print(f"[red]Batch '{batch_id}' not found[/red]")
            raise typer.Exit(1)
        
        # Create status panel
        status_color = {
            "completed": "green",
            "partial": "yellow",
            "failed": "red",
            "processing": "blue",
            "pending": "dim"
        }.get(batch.status, "white")
        
        status_panel = Panel(
            f"""
[bold]Batch ID:[/bold] {batch.batch_id}
[bold]Source:[/bold] {batch.source_file}
[bold]Status:[/bold] [{status_color}]{batch.status}[/{status_color}]
[bold]Created:[/bold] {batch.created_at.strftime("%Y-%m-%d %H:%M:%S")}
[bold]Completed:[/bold] {batch.completed_at.strftime("%Y-%m-%d %H:%M:%S") if batch.completed_at else "N/A"}

[bold cyan]Progress[/bold cyan]
Total Items:     {batch.progress.total_rows:,}
Processed:       {batch.progress.processed_rows:,} ({batch.progress.progress_percentage:.1f}%)
Successful:      {batch.progress.successful_rows:,}
Duplicates:      {batch.progress.duplicate_rows:,}
Failed:          {batch.progress.failed_rows:,}

[bold cyan]Performance[/bold cyan]
Processing Time: {batch.progress.elapsed_seconds:.1f}s
Processing Rate: {batch.progress.rows_per_second:.1f} items/sec
""",
            title=f"Batch Status",
            border_style=status_color
        )
        
        console.print(status_panel)
        
        # Show errors if requested
        if show_errors and batch.progress.validation_errors:
            console.print("\n")
            errors = ingress.get_batch_errors(batch_id, limit=20)
            console.print(create_error_table(errors, limit=20))
        
        # Export report if requested
        if export_report:
            report_path = ingress.export_batch_report(batch_id)
            console.print(f"\n[green]Detailed report exported to: {report_path}[/green]")
        
    finally:
        db_manager.close()
        ingress.close()


@ingress_app.command("retry")
def retry_failed(
    batch_id: str = typer.Argument(..., help="Batch ID with failed items"),
    db_path: str = typer.Option("pipeline.db", "--db", help="Database path")
):
    """Retry failed items from a batch"""
    
    db_manager = EnhancedDatabaseManager(db_path=db_path)
    validated_db = ValidatedDatabaseManager(db_manager)
    ingress = IngressServiceEnhanced(validated_db)
    
    try:
        console.print(f"[cyan]Retrying failed items from batch {batch_id}...[/cyan]")
        
        retry_batch = ingress.retry_failed_items(batch_id)
        
        # Show results
        if retry_batch.status == "completed":
            console.print(f"[green]✓ Retry completed successfully![/green]")
        else:
            console.print(f"[yellow]⚠ Retry completed with errors[/yellow]")
        
        # Summary
        table = Table(title="Retry Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Retry Batch ID", retry_batch.batch_id)
        table.add_row("Items Retried", str(retry_batch.progress.total_rows))
        table.add_row("Successful", str(retry_batch.progress.successful_rows))
        table.add_row("Still Failed", str(retry_batch.progress.failed_rows))
        table.add_row("Success Rate", f"{(retry_batch.progress.successful_rows / retry_batch.progress.total_rows * 100):.1f}%")
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Retry failed: {e}[/red]")
        raise typer.Exit(1)
    finally:
        db_manager.close()
        ingress.close()


@ingress_app.command("cleanup")
def cleanup_batches(
    days: int = typer.Option(30, "--days", "-d", help="Delete batches older than N days"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be deleted without deleting"),
    db_path: str = typer.Option("pipeline.db", "--db", help="Database path")
):
    """Clean up old import batches"""
    
    db_manager = EnhancedDatabaseManager(db_path=db_path)
    validated_db = ValidatedDatabaseManager(db_manager)
    ingress = IngressServiceEnhanced(validated_db)
    
    try:
        if dry_run:
            # Get old batches to show what would be deleted
            old_batches = ingress.list_batches(limit=1000)
            
            # Filter by age
            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
            
            batches_to_delete = [
                b for b in old_batches 
                if b.completed_at and b.completed_at < cutoff_date
            ]
            
            if not batches_to_delete:
                console.print(f"[green]No batches older than {days} days found[/green]")
                return
            
            console.print(f"[yellow]Would delete {len(batches_to_delete)} batches:[/yellow]")
            
            table = Table()
            table.add_column("Batch ID", style="cyan")
            table.add_column("Source", style="magenta")
            table.add_column("Completed", style="dim")
            
            for batch in batches_to_delete[:10]:
                table.add_row(
                    batch.batch_id[:30] + "...",
                    Path(batch.source_file).name,
                    batch.completed_at.strftime("%Y-%m-%d")
                )
            
            if len(batches_to_delete) > 10:
                table.add_row("...", f"and {len(batches_to_delete) - 10} more", "...")
            
            console.print(table)
            
        else:
            # Actually delete
            if not typer.confirm(f"Delete all batches older than {days} days?"):
                console.print("[yellow]Cancelled[/yellow]")
                return
            
            deleted = ingress.cleanup_old_batches(days)
            console.print(f"[green]✓ Deleted {deleted} old batches[/green]")
        
    finally:
        db_manager.close()
        ingress.close()


@ingress_app.command("validate")
def validate_csv(
    csv_file: Path = typer.Argument(..., help="CSV file to validate"),
    show_all: bool = typer.Option(False, "--all", "-a", help="Show all errors, not just first 100"),
    export: bool = typer.Option(False, "--export", "-e", help="Export validation report")
):
    """Validate CSV file without importing"""
    
    if not csv_file.exists():
        console.print(f"[red]Error: File '{csv_file}' not found[/red]")
        raise typer.Exit(1)
    
    # Use in-memory database for validation
    db_manager = EnhancedDatabaseManager(db_path=":memory:")
    validated_db = ValidatedDatabaseManager(db_manager)
    ingress = IngressServiceEnhanced(validated_db)
    
    try:
        console.print(f"[cyan]Validating {csv_file}...[/cyan]")
        
        # Run validation only
        batch = ingress.import_csv(
            str(csv_file),
            validate_only=True,
            skip_duplicates=False  # Don't check duplicates in validation mode
        )
        
        # Show results
        if batch.progress.failed_rows == 0:
            console.print(f"[green]✓ Validation passed! All {batch.progress.total_rows} rows are valid.[/green]")
        else:
            console.print(f"[red]✗ Validation failed! {batch.progress.failed_rows} errors found.[/red]")
            
            # Show errors
            errors_to_show = batch.progress.validation_errors
            if not show_all:
                errors_to_show = errors_to_show[:100]
            
            if errors_to_show:
                console.print(create_error_table(errors_to_show, limit=20 if not show_all else len(errors_to_show)))
            
            if export:
                report_path = f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(report_path, 'w', encoding='utf-8') as f:
                    import json
                    json.dump({
                        "file": str(csv_file),
                        "total_rows": batch.progress.total_rows,
                        "valid_rows": batch.progress.successful_rows,
                        "invalid_rows": batch.progress.failed_rows,
                        "errors": batch.progress.validation_errors
                    }, f, indent=2, ensure_ascii=False)
                
                console.print(f"\n[green]Validation report saved to: {report_path}[/green]")
        
    finally:
        db_manager.close()
        ingress.close()


# Add database health check command
@app.command("db-health")
def database_health(
    db_path: str = typer.Option("pipeline.db", "--db", help="Database path"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Check database health and performance"""
    
    db_manager = EnhancedDatabaseManager(db_path=db_path)
    
    try:
        health = db_manager.check_health()
        
        if json_output:
            import json
            console.print(json.dumps(health, indent=2))
        else:
            # Create health panel
            health_color = "green" if health["healthy"] else "red"
            
            content = f"""
[bold]Database:[/bold] {db_path}
[bold]Status:[/bold] [{"green" if health["healthy"] else "red"}]{"Healthy" if health["healthy"] else "Unhealthy"}[/]

[bold cyan]Health Checks[/bold cyan]
"""
            
            for check, status in health["checks"].items():
                emoji = "✅" if status == "OK" else "❌"
                content += f"{emoji} {check}: {status}\n"
            
            if "pool_health" in health:
                content += f"\n[bold cyan]Connection Pool[/bold cyan]\n"
                pool = health["pool_health"]
                content += f"Total Connections: {pool['total_connections']}\n"
                content += f"Active: {pool['active_connections']}\n"
                content += f"Available: {pool['available_connections']}\n"
            
            if "performance_summary" in health:
                content += f"\n[bold cyan]Performance[/bold cyan]\n"
                perf = health["performance_summary"]
                content += f"Total Queries: {perf['total_queries']:,}\n"
                content += f"Error Rate: {perf['error_rate']:.2%}\n"
                content += f"Avg Duration: {perf['avg_duration_ms']:.2f}ms\n"
                content += f"Slow Queries: {perf['slow_queries']}\n"
            
            panel = Panel(content, title="Database Health", border_style=health_color)
            console.print(panel)
        
    finally:
        db_manager.close()


def main():
    """Main entry point for the enhanced CLI"""
    app()


if __name__ == "__main__":
    main()