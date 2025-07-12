"""
Unified CLI that combines cli_v2 (protected) with enhanced ingress features.
This provides a single entry point for all CLI functionality.
"""

import typer
from pathlib import Path
from typing import Optional

# Import the protected cli_v2 implementation
try:
    from .cli_v2 import app as cli_v2_app
    CLI_V2_AVAILABLE = True
except ImportError:
    CLI_V2_AVAILABLE = False
    cli_v2_app = None

# Import enhanced ingress functionality
try:
    from .cli.ingress_enhanced import create_enhanced_ingress_group
    ENHANCED_INGRESS_AVAILABLE = True
except ImportError:
    ENHANCED_INGRESS_AVAILABLE = False

# Create the unified app
app = typer.Typer(
    name="flashcard",
    help="Korean Language Flashcard Pipeline - Unified CLI",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

# Add a note about the protected cli_v2
if CLI_V2_AVAILABLE:
    @app.command("v2", hidden=True)
    def run_cli_v2():
        """Run the protected cli_v2 implementation directly"""
        import sys
        from . import cli_v2
        # Run cli_v2 with the remaining arguments
        cli_v2.main()

# Add enhanced ingress if available
if ENHANCED_INGRESS_AVAILABLE:
    enhanced_ingress = create_enhanced_ingress_group()
    app.add_typer(enhanced_ingress, name="ingress-plus", help="Enhanced ingress commands with batch management")

# Re-export key commands from cli_v2 at the top level for convenience
if CLI_V2_AVAILABLE:
    # Process command (most important)
    @app.command("process")
    def process_vocabulary(
        input_file: Path = typer.Argument(..., help="Input CSV file with vocabulary"),
        output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
        max_concurrent: int = typer.Option(3, "--concurrent", "-c", help="Maximum concurrent requests"),
        cache_ttl: int = typer.Option(86400, "--cache-ttl", help="Cache TTL in seconds"),
        force: bool = typer.Option(False, "--force", "-f", help="Force reprocessing of cached items"),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output")
    ):
        """Process vocabulary file through the pipeline (delegates to cli_v2)"""
        # Import and call cli_v2's process function directly
        from .cli_v2 import process_vocabulary as v2_process
        v2_process(
            input_file=input_file,
            output_file=output_file,
            max_concurrent=max_concurrent,
            cache_ttl=cache_ttl,
            force=force,
            verbose=verbose
        )
    
    # Cache stats command
    @app.command("cache-stats")
    def cache_stats():
        """Show cache statistics (delegates to cli_v2)"""
        from .cli_v2 import cache_stats as v2_cache_stats
        v2_cache_stats()
    
    # Monitor command
    @app.command("monitor")
    def monitor():
        """Monitor processing progress (delegates to cli_v2)"""
        from .cli_v2 import monitor as v2_monitor
        v2_monitor()
    
    # Doctor command
    @app.command("doctor")
    def doctor(verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed diagnostics")):
        """Run system health checks (delegates to cli_v2)"""
        from .cli_v2 import doctor as v2_doctor
        v2_doctor(verbose=verbose)

# Add deprecation notices for old CLIs
@app.command("migrate-from-old", hidden=True)
def migration_guide():
    """Show migration guide from old CLI versions"""
    from rich import print
    from rich.panel import Panel
    
    print(Panel("""
[bold]Migration Guide[/bold]

The CLI has been unified. Here's how to migrate:

[yellow]From pipeline_cli.py:[/yellow]
- Use 'flashcard process' instead of 'pipeline process'
- Use 'flashcard monitor' instead of 'pipeline monitor'
- Use 'flashcard cache-stats' instead of 'pipeline stats'

[yellow]From cli_enhanced.py:[/yellow]
- Use 'flashcard ingress-plus import' instead of 'cli-enhanced ingress import'
- Use 'flashcard ingress-plus list-batches' instead of 'cli-enhanced ingress list-batches'
- All other ingress commands are under 'flashcard ingress-plus'

[green]For full cli_v2 functionality:[/green]
- Run 'flashcard v2 --help' to access all original cli_v2 commands
- Or use cli_v2.py directly (it remains unchanged and protected)
    """, title="CLI Migration Guide"))


def main():
    """Main entry point"""
    app()


if __name__ == "__main__":
    main()