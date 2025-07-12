"""Command-line interface for Korean flashcard pipeline"""

import asyncio
import csv
import sys
from pathlib import Path
from typing import Optional, List
import logging
from datetime import datetime
import os

import typer
from rich.console import Console
from dotenv import load_dotenv
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.logging import RichHandler
from rich import print as rprint

from .api_client import OpenRouterClient
from .cache import CacheService
from .rate_limiter import CompositeLimiter
from .circuit_breaker import MultiServiceCircuitBreaker
from .models import VocabularyItem, BatchProgress
from .exceptions import PipelineError, ApiError, RateLimitError
from .concurrent import (
    ConcurrentPipelineOrchestrator,
    OrderedBatchDatabaseWriter,
    ConcurrentProcessingMonitor
)
from .ingress import IngressService


# Load environment variables from .env file
env_path = Path.cwd() / '.env'
if env_path.exists():
    load_dotenv(env_path)

# Set up rich console
console = Console()
app = typer.Typer(
    name="flashcard-pipeline",
    help="Korean Language Flashcard Pipeline - AI-powered flashcard generation"
)

# Configure logging with rich
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Orchestrates the flashcard generation pipeline"""
    
    def __init__(self, 
                 cache_dir: Optional[str] = None,
                 rate_limit: Optional[int] = None,
                 max_concurrent: int = 10,
                 circuit_breaker_threshold: int = 5,
                 circuit_breaker_timeout: int = 60,
                 db_path: Optional[str] = None):
        self.cache_service = CacheService(cache_dir)
        self.rate_limiter = CompositeLimiter()
        # Apply rate limit if specified
        if rate_limit:
            self.rate_limiter.api_limiter.set_rate(rate_limit)
        self._multi_circuit_breaker = MultiServiceCircuitBreaker()
        self._circuit_breaker_threshold = circuit_breaker_threshold
        self._circuit_breaker_timeout = circuit_breaker_timeout
        self.max_concurrent = max_concurrent
        self.db_path = db_path
        self.client: Optional[OpenRouterClient] = None
        self._main_breaker = None  # Will be created on first use
    
    @property
    def circuit_breaker(self):
        """Get the main circuit breaker for compatibility with tests"""
        if self._main_breaker is None:
            # Create a synchronous circuit breaker for test compatibility
            from .circuit_breaker import CircuitBreaker
            self._main_breaker = CircuitBreaker(
                failure_threshold=self._circuit_breaker_threshold,
                recovery_timeout=self._circuit_breaker_timeout,
                name="main"
            )
        return self._main_breaker
    
    async def __aenter__(self):
        self.client = OpenRouterClient()
        await self.client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def process_item(self, item: VocabularyItem, progress: Optional[Progress] = None,
                         task_id: Optional[int] = None) -> tuple[str, bool]:
        """Process a single vocabulary item through both stages
        
        Returns:
            Tuple of (tsv_output, from_cache)
        """
        from_cache = False
        
        try:
            # Stage 1: Check cache first
            stage1_cached = await self.cache_service.get_stage1(item)
            
            if stage1_cached:
                stage1_result, tokens_saved = stage1_cached
                from_cache = True
                logger.debug(f"Stage 1 cache hit for '{item.term}', saved {tokens_saved} tokens")
            else:
                # Rate limit and circuit breaker checks
                await self.rate_limiter.acquire_for_stage(1)
                
                # API call through circuit breaker
                async def stage1_call():
                    return await self.client.process_stage1(item)
                
                # Get or create circuit breaker with configured parameters
                breaker = await self._multi_circuit_breaker.get_breaker(
                    "openrouter_stage1",
                    failure_threshold=self._circuit_breaker_threshold,
                    recovery_timeout=self._circuit_breaker_timeout
                )
                stage1_result, usage = await breaker.call(stage1_call)
                
                # Save to cache
                await self.cache_service.save_stage1(item, stage1_result, usage.total_tokens)
                await self.rate_limiter.api_limiter.on_success()
            
            # Stage 2: Check cache first
            stage2_cached = await self.cache_service.get_stage2(item, stage1_result)
            
            if stage2_cached:
                stage2_result, tokens_saved = stage2_cached
                from_cache = True
                logger.debug(f"Stage 2 cache hit for '{item.term}', saved {tokens_saved} tokens")
            else:
                # Rate limit and circuit breaker checks
                await self.rate_limiter.acquire_for_stage(2)
                
                # API call through circuit breaker
                async def stage2_call():
                    return await self.client.process_stage2(item, stage1_result)
                
                # Get or create circuit breaker with configured parameters
                breaker = await self._multi_circuit_breaker.get_breaker(
                    "openrouter_stage2",
                    failure_threshold=self._circuit_breaker_threshold,
                    recovery_timeout=self._circuit_breaker_timeout
                )
                stage2_result, usage = await breaker.call(stage2_call)
                
                # Save to cache
                await self.cache_service.save_stage2(
                    item, stage1_result, stage2_result, usage.total_tokens
                )
                await self.rate_limiter.api_limiter.on_success()
            
            # Update progress if provided
            if progress and task_id is not None:
                progress.update(task_id, advance=1)
            
            return stage2_result.to_tsv(), from_cache
            
        except RateLimitError as e:
            await self.rate_limiter.api_limiter.on_rate_limit(e.retry_after)
            raise
        except Exception as e:
            logger.error(f"Error processing '{item.term}': {e}")
            raise
    
    async def process_batch(self, items: List[VocabularyItem], 
                          output_file: Path,
                          batch_id: Optional[str] = None) -> BatchProgress:
        """Process a batch of vocabulary items"""
        if not batch_id:
            batch_id = datetime.now().strftime("batch_%Y%m%d_%H%M%S")
        
        batch_progress = BatchProgress(
            batch_id=batch_id,
            total_items=len(items),
            completed_items=0,
            failed_items=0,
            current_stage="stage1",
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Pre-check cache
        cache_status = await self.cache_service.warm_cache_from_batch(items)
        console.print(f"[green]Cache pre-check: {cache_status['stage1_cached']}/{len(items)} items cached[/green]")
        
        # Process items with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task(f"Processing {len(items)} items...", total=len(items))
            
            results = []
            failed_items = []
            
            for item in items:
                try:
                    tsv_output, from_cache = await self.process_item(item, progress, task)
                    
                    # Parse TSV to get individual rows
                    rows = tsv_output.strip().split('\n')
                    if rows[0].startswith('position\tterm'):  # Remove header if present
                        rows = rows[1:]
                    
                    results.extend(rows)
                    batch_progress.completed_items += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process '{item.term}': {e}")
                    failed_items.append((item, str(e)))
                    batch_progress.failed_items += 1
                
                batch_progress.updated_at = datetime.utcnow()
        
        # Write results to file
        if results:
            # Add header
            header = "position\tterm\tterm_number\ttab_name\tprimer\tfront\tback\ttags\thonorific_level"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(header + '\n')
                f.write('\n'.join(results))
            
            console.print(f"[green]✓ Wrote {len(results)} flashcards to {output_file}[/green]")
        
        # Show summary
        self._show_summary(batch_progress, failed_items)
        
        return batch_progress
    
    async def process_batch_concurrent(self, items: List[VocabularyItem], 
                                     output_file: Path,
                                     batch_id: Optional[str] = None,
                                     max_concurrent: int = 50) -> BatchProgress:
        """Process a batch of vocabulary items concurrently"""
        if not batch_id:
            batch_id = datetime.now().strftime("batch_%Y%m%d_%H%M%S")
        
        # Initialize monitoring
        monitor = ConcurrentProcessingMonitor()
        await monitor.start_batch(batch_id, len(items), max_concurrent)
        
        # Initialize concurrent orchestrator with configurable rate limit
        rate_limit_rpm = int(os.getenv('REQUESTS_PER_MINUTE', '600'))
        async with ConcurrentPipelineOrchestrator(
            max_concurrent=max_concurrent,
            api_client=self.client,
            cache_service=self.cache_service,
            rate_limit_rpm=rate_limit_rpm
        ) as orchestrator:
            
            # Set up progress display
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                task = progress.add_task(
                    f"Processing {len(items)} items (up to {max_concurrent} concurrent)...", 
                    total=len(items)
                )
                
                # Register progress callback
                async def update_progress(stats):
                    progress.update(task, completed=stats["completed"] + stats["failed"])
                    await monitor.record_concurrent_count(stats["in_progress"])
                
                orchestrator.progress_tracker.add_callback(update_progress)
                
                # Process concurrently
                results = await orchestrator.process_batch(items)
                
                # Update monitor
                batch_stats = orchestrator.get_statistics()
                await monitor.end_batch(batch_id, batch_stats["orchestrator"])
        
        # Write ordered results
        writer = OrderedBatchDatabaseWriter("pipeline.db")
        flashcard_count = await writer.write_to_file(results, output_file)
        
        # Create batch progress
        successful = sum(1 for r in results if r.is_success)
        failed = sum(1 for r in results if not r.is_success)
        
        batch_progress = BatchProgress(
            batch_id=batch_id,
            total_items=len(items),
            completed_items=successful,
            failed_items=failed,
            current_stage="completed",
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Show enhanced summary
        self._show_concurrent_summary(batch_progress, results, monitor)
        
        return batch_progress
    
    async def process_csv(self, csv_file: str, output_file: str, 
                         progress_callback=None) -> List[tuple]:
        """Process a CSV file and return results"""
        # Read CSV file
        items = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                items.append(VocabularyItem(
                    position=int(row['position']),
                    term=row['term'],
                    type=row.get('type', 'unknown')
                ))
        
        # Process items
        results = []
        total = len(items)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task(f"Processing {total} items...", total=total)
            
            for i, item in enumerate(items):
                try:
                    tsv_output, from_cache = await self.process_item(item, progress, task)
                    results.append((item, tsv_output, from_cache))
                    
                    if progress_callback:
                        progress_callback(i + 1, total)
                        
                except Exception as e:
                    logger.error(f"Failed to process '{item.term}': {e}")
                    results.append((item, None, False))
        
        # Write output
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                # Write header
                f.write("Position\tTerm\tIPA\tPart of Speech\tFront Primary\tFront Secondary\tFront Examples\tBack Primary\tBack Secondary\tBack Examples\tMnemonic Device\tProficiency Level\tFrequency\tTags\tNotes\n")
                
                # Write results
                for item, tsv, _ in results:
                    if tsv:
                        f.write(tsv + '\n')
        
        return results
    
    def get_checkpoint(self, batch_id: int) -> Optional[int]:
        """Get checkpoint for a batch"""
        # Simple implementation - in real system would check database
        # For now, return None to indicate no checkpoint
        return None
    
    async def resume_batch(self, batch_id: int) -> List[tuple]:
        """Resume processing a batch from checkpoint"""
        # Simple implementation - in real system would load from database
        # For now, return empty list
        return []
    
    def _show_summary(self, batch_progress: BatchProgress, failed_items: list):
        """Show processing summary"""
        # Create summary table
        table = Table(title="Processing Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Total Items", str(batch_progress.total_items))
        table.add_row("Completed", str(batch_progress.completed_items))
        table.add_row("Failed", str(batch_progress.failed_items))
        table.add_row("Success Rate", f"{batch_progress.progress_percentage:.1f}%")
        
        # Add cache stats
        cache_stats = self.cache_service.get_stats()
        table.add_row("Cache Hit Rate", f"{cache_stats.overall_hit_rate:.1f}%")
        table.add_row("Tokens Saved", f"{cache_stats.total_tokens_saved:,}")
        table.add_row("Cost Saved", f"${cache_stats.estimated_cost_saved:.2f}")
        
        # Add API stats
        if self.client:
            api_stats = self.client.get_stats()
            table.add_row("API Calls", str(api_stats["successful_requests"]))
            table.add_row("Total Cost", f"${api_stats['total_cost']:.2f}")
        
        console.print(table)
        
        # Show failed items if any
        if failed_items:
            console.print("\n[red]Failed Items:[/red]")
            for item, error in failed_items[:10]:  # Show first 10
                console.print(f"  - {item.term}: {error}")
            if len(failed_items) > 10:
                console.print(f"  ... and {len(failed_items) - 10} more")
    
    def _show_concurrent_summary(self, batch_progress: BatchProgress, 
                               results: list, monitor: ConcurrentProcessingMonitor):
        """Show enhanced summary for concurrent processing"""
        # Create summary table
        table = Table(title="Concurrent Processing Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        
        # Basic stats
        table.add_row("Total Items", str(batch_progress.total_items))
        table.add_row("Completed", str(batch_progress.completed_items))
        table.add_row("Failed", str(batch_progress.failed_items))
        table.add_row("Success Rate", f"{batch_progress.progress_percentage:.1f}%")
        
        # Concurrent processing stats
        monitor_stats = monitor.get_current_stats()
        table.add_row("Max Concurrent", str(monitor_stats["concurrent_high_water_mark"]))
        table.add_row("Avg Processing Time", f"{monitor_stats['average_processing_time_ms']:.0f}ms")
        
        # Cache stats
        cache_stats = self.cache_service.get_stats()
        table.add_row("Cache Hit Rate", f"{cache_stats.overall_hit_rate:.1f}%")
        table.add_row("Tokens Saved", f"{cache_stats.total_tokens_saved:,}")
        table.add_row("Cost Saved", f"${cache_stats.estimated_cost_saved:.2f}")
        
        # Performance improvement
        if monitor_stats["average_processing_time_ms"] > 0:
            speedup = batch_progress.total_items / (monitor_stats["average_processing_time_ms"] / 1000)
            table.add_row("Processing Rate", f"{speedup:.1f} items/second")
        
        console.print(table)
        
        # Show performance report
        console.print("\n" + monitor.get_performance_report())
        
        # Show failed items if any
        failed_results = [r for r in results if not r.is_success]
        if failed_results:
            console.print("\n[red]Failed Items:[/red]")
            for r in failed_results[:10]:
                console.print(f"  - Position {r.position} ({r.term}): {r.error}")
            if len(failed_results) > 10:
                console.print(f"  ... and {len(failed_results) - 10} more")


@app.command()
def process(
    input_file: Optional[Path] = typer.Argument(None, help="Input CSV file with vocabulary"),
    output_file: Path = typer.Option("output.tsv", "--output", "-o", help="Output TSV file"),
    cache_dir: Optional[str] = typer.Option(None, "--cache-dir", help="Cache directory"),
    batch_id: Optional[str] = typer.Option(None, "--batch-id", help="Batch identifier"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limit number of items to process"),
    start_from: Optional[int] = typer.Option(0, "--start-from", help="Start from position N"),
    concurrent: Optional[int] = typer.Option(None, "--concurrent", "-c", help="Process items concurrently (max 50)"),
    source: str = typer.Option("csv", "--source", "-s", help="Data source: 'csv' or 'database'"),
    db_batch_id: Optional[str] = typer.Option(None, "--db-batch-id", help="Database batch ID to process")
):
    """Process vocabulary to generate flashcards (from CSV or database)"""
    
    items = []
    
    if source == "csv":
        # Original CSV processing
        if not input_file:
            console.print("[red]Error: Input file required for CSV source[/red]")
            raise typer.Exit(1)
            
        if not input_file.exists():
            console.print(f"[red]Error: Input file '{input_file}' not found[/red]")
            raise typer.Exit(1)
        
        # Load vocabulary items from CSV
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    item = VocabularyItem(
                        position=int(row.get('position', len(items) + 1)),
                        term=row['term'],
                        type=row.get('type')
                    )
                    items.append(item)
                except Exception as e:
                    logger.warning(f"Skipping invalid row: {row} - {e}")
                    
    elif source == "database":
        # Database processing
        db_path = os.getenv("DATABASE_PATH", "pipeline.db")
        ingress = IngressService(db_path)
        
        # Get pending items from database
        db_items = ingress.get_pending_items(limit=limit or 1000, batch_id=db_batch_id)
        
        if not db_items:
            console.print("[yellow]No pending items in database[/yellow]")
            raise typer.Exit(0)
        
        # Convert to VocabularyItem objects
        for db_item in db_items:
            item = VocabularyItem(
                position=db_item['id'],  # Use database ID as position
                term=db_item['korean'],
                type=db_item['type']
            )
            items.append(item)
            
        console.print(f"[cyan]Loaded {len(items)} pending items from database[/cyan]")
        
        # Mark batch as processing if batch_id provided
        if db_batch_id:
            ingress.mark_batch_for_processing(db_batch_id)
    else:
        console.print(f"[red]Error: Unknown source '{source}'. Use 'csv' or 'database'[/red]")
        raise typer.Exit(1)
    
    # Apply filters
    if start_from > 0:
        items = items[start_from:]
    if limit and source == "csv":  # For database, limit was already applied
        items = items[:limit]
    
    if not items:
        console.print("[yellow]No items to process[/yellow]")
        raise typer.Exit(0)
    
    console.print(f"[cyan]Processing {len(items)} vocabulary items[/cyan]")
    
    # Run async processing
    async def run():
        async with PipelineOrchestrator(cache_dir) as orchestrator:
            if concurrent:
                # Use concurrent processing
                max_concurrent = min(concurrent, 50)  # Cap at 50
                console.print(f"[cyan]Using concurrent processing (max {max_concurrent} concurrent)[/cyan]")
                results = await orchestrator.process_batch_concurrent(items, output_file, batch_id, max_concurrent)
            else:
                # Use sequential processing
                results = await orchestrator.process_batch(items, output_file, batch_id)
                
            # Update database status if using database source
            if source == "database":
                db_path = os.getenv("DATABASE_PATH", "pipeline.db")
                ingress = IngressService(db_path)
                
                # Update item statuses
                for i, item in enumerate(items):
                    if i < results.completed_items:
                        ingress.update_item_status(item.position, 'completed')
                    else:
                        ingress.update_item_status(item.position, 'failed', 'Processing failed')
    
    asyncio.run(run())


@app.command()
def cache_stats(
    cache_dir: Optional[str] = typer.Option(None, "--cache-dir", help="Cache directory")
):
    """Show cache statistics"""
    cache_service = CacheService(cache_dir)
    stats = cache_service.get_stats()
    
    table = Table(title="Cache Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    
    table.add_row("Stage 1 Hits", str(stats.stage1_hits))
    table.add_row("Stage 1 Misses", str(stats.stage1_misses))
    table.add_row("Stage 1 Hit Rate", f"{stats.stage1_hit_rate:.1f}%")
    table.add_row("Stage 2 Hits", str(stats.stage2_hits))
    table.add_row("Stage 2 Misses", str(stats.stage2_misses))
    table.add_row("Stage 2 Hit Rate", f"{stats.stage2_hit_rate:.1f}%")
    table.add_row("Overall Hit Rate", f"{stats.overall_hit_rate:.1f}%")
    table.add_row("Tokens Saved", f"{stats.total_tokens_saved:,}")
    table.add_row("Estimated Cost Saved", f"${stats.estimated_cost_saved:.2f}")
    
    console.print(table)


@app.command()
def clear_cache(
    cache_dir: Optional[str] = typer.Option(None, "--cache-dir", help="Cache directory"),
    stage: Optional[int] = typer.Option(None, "--stage", help="Clear specific stage (1 or 2)"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation")
):
    """Clear cache files"""
    if not confirm:
        if stage:
            message = f"Clear Stage {stage} cache?"
        else:
            message = "Clear all cache files?"
        
        if not typer.confirm(message):
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)
    
    async def run():
        cache_service = CacheService(cache_dir)
        count = await cache_service.clear_cache(stage)
        console.print(f"[green]Cleared {count} cache files[/green]")
    
    asyncio.run(run())


@app.command()
def test_connection():
    """Test OpenRouter API connection"""
    async def run():
        try:
            async with OpenRouterClient() as client:
                # Test with a simple vocabulary item
                test_item = VocabularyItem(
                    position=1,
                    term="테스트",
                    type="noun"
                )
                
                console.print("[cyan]Testing Stage 1 API...[/cyan]")
                stage1_result, usage1 = await client.process_stage1(test_item)
                console.print(f"[green]✓ Stage 1 successful - {usage1.total_tokens} tokens[/green]")
                
                console.print("[cyan]Testing Stage 2 API...[/cyan]")
                stage2_result, usage2 = await client.process_stage2(test_item, stage1_result)
                console.print(f"[green]✓ Stage 2 successful - {usage2.total_tokens} tokens[/green]")
                
                console.print(f"\n[green]Connection test successful![/green]")
                console.print(f"Total tokens used: {usage1.total_tokens + usage2.total_tokens}")
                console.print(f"Estimated cost: ${usage1.estimated_cost + usage2.estimated_cost:.4f}")
                
        except Exception as e:
            console.print(f"[red]Connection test failed: {e}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(run())


# Create a sub-application for ingress commands
ingress_app = typer.Typer(help="Database ingress commands")
app.add_typer(ingress_app, name="ingress")


@ingress_app.command("import")
def import_csv(
    csv_file: Path = typer.Argument(..., help="CSV file to import"),
    batch_id: Optional[str] = typer.Option(None, "--batch-id", help="Custom batch ID"),
    db_path: Optional[str] = typer.Option(None, "--db-path", help="Database path")
):
    """Import CSV vocabulary file into the database"""
    if not csv_file.exists():
        console.print(f"[red]Error: File '{csv_file}' not found[/red]")
        raise typer.Exit(1)
    
    # Use environment variable or default
    database_path = db_path or os.getenv("DATABASE_PATH", "pipeline.db")
    ingress = IngressService(database_path)
    
    try:
        result_batch_id = ingress.import_csv(str(csv_file), batch_id)
        console.print(f"[green]✓ Import successful! Batch ID: {result_batch_id}[/green]")
        
        # Show batch status
        status = ingress.get_batch_status(result_batch_id)
        console.print(f"Total items: {status['total_items']}")
        
    except Exception as e:
        console.print(f"[red]Import failed: {e}[/red]")
        raise typer.Exit(1)


@ingress_app.command("list-batches")
def list_batches(
    status: Optional[str] = typer.Option(None, "--status", help="Filter by status"),
    limit: int = typer.Option(20, "--limit", help="Number of batches to show"),
    db_path: Optional[str] = typer.Option(None, "--db-path", help="Database path")
):
    """List import batches"""
    database_path = db_path or os.getenv("DATABASE_PATH", "pipeline.db")
    ingress = IngressService(database_path)
    
    batches = ingress.list_batches(status, limit)
    
    if not batches:
        console.print("[yellow]No batches found[/yellow]")
        return
    
    table = Table(title="Import Batches")
    table.add_column("Batch ID", style="cyan")
    table.add_column("Source File", style="magenta")
    table.add_column("Total", style="green")
    table.add_column("Processed", style="blue")
    table.add_column("Failed", style="red")
    table.add_column("Status", style="yellow")
    table.add_column("Created", style="dim")
    
    for batch in batches:
        table.add_row(
            batch['id'],
            batch['source_file'],
            str(batch['total_items']),
            str(batch['processed_items']),
            str(batch['failed_items']),
            batch['status'],
            batch['created_at']
        )
    
    console.print(table)


@ingress_app.command("status")
def batch_status(
    batch_id: str = typer.Argument(..., help="Batch ID to check"),
    db_path: Optional[str] = typer.Option(None, "--db-path", help="Database path")
):
    """Check status of a specific batch"""
    database_path = db_path or os.getenv("DATABASE_PATH", "pipeline.db")
    ingress = IngressService(database_path)
    
    status = ingress.get_batch_status(batch_id)
    
    if not status:
        console.print(f"[red]Batch '{batch_id}' not found[/red]")
        raise typer.Exit(1)
    
    table = Table(title=f"Batch Status: {batch_id}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    
    table.add_row("Source File", status['source_file'])
    table.add_row("Total Items", str(status['total_items']))
    table.add_row("Processed", str(status['processed_items']))
    table.add_row("Failed", str(status['failed_items']))
    table.add_row("Status", status['status'])
    table.add_row("Progress", f"{status['progress_percentage']:.1f}%")
    table.add_row("Created", status['created_at'])
    table.add_row("Completed", status['completed_at'] or "N/A")
    
    console.print(table)


def main():
    """Main entry point for the simple CLI"""
    app()


if __name__ == "__main__":
    main()