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
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_service = CacheService(cache_dir)
        self.rate_limiter = CompositeLimiter()
        self.circuit_breaker = MultiServiceCircuitBreaker()
        self.client: Optional[OpenRouterClient] = None
    
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
                
                stage1_result, usage = await self.circuit_breaker.call(
                    "openrouter_stage1", stage1_call
                )
                
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
                
                stage2_result, usage = await self.circuit_breaker.call(
                    "openrouter_stage2", stage2_call
                )
                
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
        
        # Initialize concurrent orchestrator
        async with ConcurrentPipelineOrchestrator(
            max_concurrent=max_concurrent,
            api_client=self.client,
            cache_service=self.cache_service
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
    input_file: Path = typer.Argument(..., help="Input CSV file with vocabulary"),
    output_file: Path = typer.Option("output.tsv", "--output", "-o", help="Output TSV file"),
    cache_dir: Optional[str] = typer.Option(None, "--cache-dir", help="Cache directory"),
    batch_id: Optional[str] = typer.Option(None, "--batch-id", help="Batch identifier"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limit number of items to process"),
    start_from: Optional[int] = typer.Option(0, "--start-from", help="Start from position N"),
    concurrent: Optional[int] = typer.Option(None, "--concurrent", "-c", help="Process items concurrently (max 50)")
):
    """Process vocabulary CSV file to generate flashcards"""
    
    # Validate input file
    if not input_file.exists():
        console.print(f"[red]Error: Input file '{input_file}' not found[/red]")
        raise typer.Exit(1)
    
    # Load vocabulary items
    items = []
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
    
    # Apply filters
    if start_from > 0:
        items = items[start_from:]
    if limit:
        items = items[:limit]
    
    if not items:
        console.print("[yellow]No items to process[/yellow]")
        raise typer.Exit(0)
    
    console.print(f"[cyan]Loaded {len(items)} vocabulary items[/cyan]")
    
    # Run async processing
    async def run():
        async with PipelineOrchestrator(cache_dir) as orchestrator:
            if concurrent:
                # Use concurrent processing
                max_concurrent = min(concurrent, 50)  # Cap at 50
                console.print(f"[cyan]Using concurrent processing (max {max_concurrent} concurrent)[/cyan]")
                await orchestrator.process_batch_concurrent(items, output_file, batch_id, max_concurrent)
            else:
                # Use sequential processing
                await orchestrator.process_batch(items, output_file, batch_id)
    
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


if __name__ == "__main__":
    app()