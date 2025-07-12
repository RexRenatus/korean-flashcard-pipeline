"""
Enhanced ingress commands extracted from cli_enhanced.py.
Provides advanced import functionality with batch management.
"""

import typer
from typing import Optional, List
from pathlib import Path
from datetime import datetime, timedelta
import asyncio

from rich import print
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live

from ..database import DatabaseManager
from ..services.ingress import IngressService, ImportMode
from ..utils import setup_logging, get_logger

console = Console()
logger = get_logger(__name__)


def create_enhanced_ingress_group() -> typer.Typer:
    """Create the enhanced ingress command group"""
    
    ingress_app = typer.Typer(help="Enhanced vocabulary import commands with batch management")
    
    @ingress_app.command("import")
    def import_vocabulary(
        csv_file: Path = typer.Argument(
            ..., 
            help="Path to CSV file containing vocabulary",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True
        ),
        batch_name: Optional[str] = typer.Option(
            None,
            "--batch-name", "-b",
            help="Name for this import batch"
        ),
        mode: ImportMode = typer.Option(
            ImportMode.STANDARD,
            "--mode", "-m",
            help="Import mode: simple (no validation), standard (default), strict (comprehensive validation)"
        ),
        dry_run: bool = typer.Option(
            False,
            "--dry-run",
            help="Validate without importing"
        ),
        force: bool = typer.Option(
            False,
            "--force", "-f",
            help="Skip confirmation prompts"
        )
    ):
        """Import vocabulary from CSV file with enhanced progress tracking"""
        try:
            # Setup
            db = DatabaseManager()
            ingress = IngressService(db, mode=mode)
            
            # Generate batch name if not provided
            if not batch_name:
                batch_name = f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Show file info
            file_size = csv_file.stat().st_size
            console.print(Panel(
                f"[bold]File:[/bold] {csv_file.name}\n"
                f"[bold]Size:[/bold] {file_size:,} bytes\n"
                f"[bold]Mode:[/bold] {mode.value}\n"
                f"[bold]Batch:[/bold] {batch_name}",
                title="Import Details"
            ))
            
            # Confirmation
            if not force and not dry_run:
                if not typer.confirm("Proceed with import?"):
                    console.print("[yellow]Import cancelled[/yellow]")
                    return
            
            # Progress tracking
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                
                # Validation phase
                validate_task = progress.add_task("Validating CSV...", total=None)
                
                def validation_callback(current: int, total: int, item: str):
                    progress.update(validate_task, total=total, completed=current, description=f"Validating: {item}")
                
                # Import phase
                import_task = progress.add_task("Importing vocabulary...", total=None)
                
                def import_callback(current: int, total: int, item: str):
                    progress.update(import_task, total=total, completed=current, description=f"Importing: {item}")
                
                # Execute import
                result = ingress.import_csv(
                    file_path=csv_file,
                    mode=mode,
                    batch_name=batch_name,
                    progress_callback=import_callback if not dry_run else validation_callback,
                    dry_run=dry_run
                )
                
                progress.update(validate_task, completed=result.total_items)
                if not dry_run:
                    progress.update(import_task, completed=result.imported_count)
            
            # Show results
            if dry_run:
                console.print(Panel(
                    f"[green]✓[/green] Validation complete\n"
                    f"Total items: {result.total_items}\n"
                    f"Valid items: {result.total_items - len(result.validation_errors)}",
                    title="Validation Results"
                ))
            else:
                console.print(Panel(
                    f"[green]✓[/green] Import complete\n"
                    f"Imported: {result.imported_count}/{result.total_items}\n"
                    f"Skipped: {result.skipped_count}\n"
                    f"Failed: {result.failed_count}",
                    title="Import Results"
                ))
            
            # Show errors if any
            if result.validation_errors:
                error_table = Table(title="Validation Errors")
                error_table.add_column("Row", style="cyan")
                error_table.add_column("Error", style="red")
                
                for error in result.validation_errors[:10]:  # Show first 10
                    error_table.add_row(str(error.get("row", "?")), error.get("error", "Unknown error"))
                
                if len(result.validation_errors) > 10:
                    error_table.add_row("...", f"And {len(result.validation_errors) - 10} more errors")
                
                console.print(error_table)
                
        except Exception as e:
            console.print(f"[red]Error during import: {e}[/red]")
            raise typer.Exit(1)
    
    @ingress_app.command("list-batches")
    def list_batches(
        limit: int = typer.Option(10, "--limit", "-n", help="Number of batches to show"),
        days: int = typer.Option(7, "--days", "-d", help="Show batches from last N days")
    ):
        """List recent import batches"""
        try:
            db = DatabaseManager()
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT 
                        batch_id,
                        batch_name,
                        total_items,
                        imported_count,
                        failed_count,
                        status,
                        created_at
                    FROM ingress_batches
                    WHERE created_at >= ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (cutoff_date.isoformat(), limit))
                
                batches = cursor.fetchall()
                
                if not batches:
                    console.print("[yellow]No batches found[/yellow]")
                    return
                
                table = Table(title=f"Import Batches (Last {days} days)")
                table.add_column("Batch ID", style="cyan")
                table.add_column("Name", style="green")
                table.add_column("Total", justify="right")
                table.add_column("Imported", justify="right", style="green")
                table.add_column("Failed", justify="right", style="red")
                table.add_column("Status")
                table.add_column("Created", style="dim")
                
                for batch in batches:
                    status_style = "green" if batch["status"] == "completed" else "yellow"
                    table.add_row(
                        batch["batch_id"][:8],
                        batch["batch_name"],
                        str(batch["total_items"]),
                        str(batch["imported_count"]),
                        str(batch["failed_count"]),
                        f"[{status_style}]{batch['status']}[/{status_style}]",
                        batch["created_at"][:16]
                    )
                
                console.print(table)
                
        except Exception as e:
            console.print(f"[red]Error listing batches: {e}[/red]")
            raise typer.Exit(1)
    
    @ingress_app.command("status")
    def batch_status(
        batch_id: str = typer.Argument(..., help="Batch ID to show details for")
    ):
        """Show detailed status of an import batch"""
        try:
            db = DatabaseManager()
            
            with db.get_connection() as conn:
                # Get batch info
                cursor = conn.execute("""
                    SELECT * FROM ingress_batches
                    WHERE batch_id LIKE ?
                """, (f"{batch_id}%",))
                
                batch = cursor.fetchone()
                if not batch:
                    console.print(f"[red]Batch '{batch_id}' not found[/red]")
                    raise typer.Exit(1)
                
                # Get failed items
                cursor = conn.execute("""
                    SELECT term, error_message
                    FROM ingress_items
                    WHERE batch_id = ? AND status = 'failed'
                    LIMIT 10
                """, (batch["batch_id"],))
                
                failed_items = cursor.fetchall()
                
                # Display batch info
                console.print(Panel(
                    f"[bold]Batch ID:[/bold] {batch['batch_id']}\n"
                    f"[bold]Name:[/bold] {batch['batch_name']}\n"
                    f"[bold]Status:[/bold] {batch['status']}\n"
                    f"[bold]Total Items:[/bold] {batch['total_items']}\n"
                    f"[bold]Imported:[/bold] {batch['imported_count']}\n"
                    f"[bold]Failed:[/bold] {batch['failed_count']}\n"
                    f"[bold]Created:[/bold] {batch['created_at']}\n"
                    f"[bold]Updated:[/bold] {batch['updated_at']}",
                    title="Batch Details"
                ))
                
                # Show failed items if any
                if failed_items:
                    error_table = Table(title="Failed Items (First 10)")
                    error_table.add_column("Term", style="cyan")
                    error_table.add_column("Error", style="red")
                    
                    for item in failed_items:
                        error_table.add_row(item["term"], item["error_message"])
                    
                    console.print(error_table)
                
        except Exception as e:
            console.print(f"[red]Error getting batch status: {e}[/red]")
            raise typer.Exit(1)
    
    @ingress_app.command("retry")
    def retry_failed(
        batch_id: str = typer.Argument(..., help="Batch ID to retry failed items from"),
        force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation")
    ):
        """Retry failed items from a batch"""
        try:
            db = DatabaseManager()
            ingress = IngressService(db)
            
            # Get failed items count
            with db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) as count
                    FROM ingress_items
                    WHERE batch_id LIKE ? AND status = 'failed'
                """, (f"{batch_id}%",))
                
                count = cursor.fetchone()["count"]
                
                if count == 0:
                    console.print("[yellow]No failed items to retry[/yellow]")
                    return
                
                console.print(f"Found [red]{count}[/red] failed items to retry")
                
                if not force and not typer.confirm("Proceed with retry?"):
                    console.print("[yellow]Retry cancelled[/yellow]")
                    return
                
                # Retry failed items
                success_count = ingress.retry_failed_items(batch_id)
                
                console.print(Panel(
                    f"[green]✓[/green] Retry complete\n"
                    f"Successfully imported: {success_count}/{count}",
                    title="Retry Results"
                ))
                
        except Exception as e:
            console.print(f"[red]Error during retry: {e}[/red]")
            raise typer.Exit(1)
    
    @ingress_app.command("cleanup")
    def cleanup_old_batches(
        days: int = typer.Option(30, "--days", "-d", help="Delete batches older than N days"),
        dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be deleted"),
        force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation")
    ):
        """Clean up old import batches"""
        try:
            db = DatabaseManager()
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with db.get_connection() as conn:
                # Count batches to delete
                cursor = conn.execute("""
                    SELECT COUNT(*) as count
                    FROM ingress_batches
                    WHERE created_at < ?
                """, (cutoff_date.isoformat(),))
                
                count = cursor.fetchone()["count"]
                
                if count == 0:
                    console.print("[green]No batches to clean up[/green]")
                    return
                
                console.print(f"Found [yellow]{count}[/yellow] batches older than {days} days")
                
                if dry_run:
                    console.print("[dim]Dry run - no changes will be made[/dim]")
                elif not force and not typer.confirm("Delete these batches?"):
                    console.print("[yellow]Cleanup cancelled[/yellow]")
                    return
                
                if not dry_run:
                    # Delete old batches (cascade will handle items)
                    conn.execute("""
                        DELETE FROM ingress_batches
                        WHERE created_at < ?
                    """, (cutoff_date.isoformat(),))
                    conn.commit()
                    
                    console.print(f"[green]✓[/green] Deleted {count} old batches")
                    
        except Exception as e:
            console.print(f"[red]Error during cleanup: {e}[/red]")
            raise typer.Exit(1)
    
    return ingress_app