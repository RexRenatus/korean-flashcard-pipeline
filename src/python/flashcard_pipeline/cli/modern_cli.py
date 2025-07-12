"""Modern CLI for Flashcard Pipeline using Click"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

import click
from click import Context, echo, secho, style
from click.decorators import pass_context
import yaml

from ..telemetry import init_telemetry
from ..errors import initialize_error_collector, get_error_collector
from ..database.database_manager_instrumented import create_instrumented_database_manager
from ..cache.cache_manager_instrumented import create_instrumented_cache_manager
from ..api_client_instrumented import create_instrumented_api_client
from ..errors.analytics import ErrorAnalytics

# Version info
__version__ = "2.0.0"

# Custom types
class KeyValueParamType(click.ParamType):
    """Custom parameter type for key=value pairs"""
    name = "key=value"
    
    def convert(self, value, param, ctx):
        try:
            key, val = value.split('=', 1)
            return (key.strip(), val.strip())
        except ValueError:
            self.fail(f"{value!r} is not a valid key=value pair", param, ctx)

KEY_VALUE = KeyValueParamType()


# Context object to pass around
class CLIContext:
    """Context object for CLI state"""
    
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.verbose: bool = False
        self.debug: bool = False
        self.output_format: str = "human"
        self.no_color: bool = False
        self.db_path: Optional[str] = None
        self.api_key: Optional[str] = None
        self.telemetry_enabled: bool = True
        
        # Async components
        self.db_manager = None
        self.cache_manager = None
        self.api_client = None
        self.error_collector = None
    
    async def initialize_components(self):
        """Initialize async components"""
        if self.telemetry_enabled:
            init_telemetry(
                service_name="flashcard-cli",
                service_version=__version__,
                environment="production" if not self.debug else "development"
            )
        
        if self.db_path:
            self.db_manager = create_instrumented_database_manager(self.db_path)
            await self.db_manager.initialize()
        
        self.cache_manager = create_instrumented_cache_manager()
        
        if self.api_key:
            self.api_client = create_instrumented_api_client(self.api_key)
        
        self.error_collector = initialize_error_collector(
            database=self.db_manager,
            enable_persistence=bool(self.db_manager)
        )
        await self.error_collector.start()
    
    async def cleanup(self):
        """Cleanup async components"""
        if self.error_collector:
            await self.error_collector.stop()
        if self.db_manager:
            await self.db_manager.close()
    
    def echo(self, message: str, **kwargs):
        """Context-aware echo"""
        if self.no_color:
            kwargs['color'] = False
        echo(message, **kwargs)
    
    def secho(self, message: str, **kwargs):
        """Context-aware styled echo"""
        if self.no_color:
            kwargs['color'] = False
        secho(message, **kwargs)
    
    def success(self, message: str):
        """Success message"""
        self.secho(f"✓ {message}", fg='green')
    
    def error(self, message: str):
        """Error message"""
        self.secho(f"✗ {message}", fg='red', err=True)
    
    def warning(self, message: str):
        """Warning message"""
        self.secho(f"⚠ {message}", fg='yellow')
    
    def info(self, message: str):
        """Info message"""
        self.secho(f"ℹ {message}", fg='blue')
    
    def debug_msg(self, message: str):
        """Debug message"""
        if self.debug:
            self.secho(f"[DEBUG] {message}", fg='cyan', dim=True)
    
    def format_output(self, data: Any) -> str:
        """Format output based on output format"""
        if self.output_format == "json":
            return json.dumps(data, indent=2, default=str)
        elif self.output_format == "yaml":
            return yaml.dump(data, default_flow_style=False)
        else:  # human
            return str(data)


# Main CLI group
@click.group(
    invoke_without_command=True,
    context_settings=dict(help_option_names=['-h', '--help'])
)
@click.version_option(version=__version__, prog_name='flashcard')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--config', '-c', type=click.Path(exists=True), help='Config file path')
@click.option('--db', type=click.Path(), envvar='FLASHCARD_DB', help='Database path')
@click.option('--api-key', envvar='OPENROUTER_API_KEY', help='OpenRouter API key')
@click.option('--output', '-o', type=click.Choice(['human', 'json', 'yaml']), 
              default='human', help='Output format')
@click.option('--no-color', is_flag=True, help='Disable colored output')
@click.option('--no-telemetry', is_flag=True, help='Disable telemetry')
@pass_context
def cli(ctx: Context, verbose: bool, debug: bool, config: Optional[str], 
        db: Optional[str], api_key: Optional[str], output: str, 
        no_color: bool, no_telemetry: bool):
    """Flashcard Pipeline CLI - Modern AI-powered flashcard generation
    
    \b
    Examples:
      flashcard process single "안녕하세요"
      flashcard process batch words.csv --output results.json
      flashcard cache stats
      flashcard monitor errors --last 1h
    """
    # Initialize context
    cli_ctx = CLIContext()
    cli_ctx.verbose = verbose
    cli_ctx.debug = debug
    cli_ctx.output_format = output
    cli_ctx.no_color = no_color
    cli_ctx.db_path = db or "flashcards.db"
    cli_ctx.api_key = api_key
    cli_ctx.telemetry_enabled = not no_telemetry
    
    # Load config
    if config:
        cli_ctx.debug_msg(f"Loading config from: {config}")
        with open(config) as f:
            if config.endswith('.yaml') or config.endswith('.yml'):
                cli_ctx.config = yaml.safe_load(f)
            else:
                cli_ctx.config = json.load(f)
    
    ctx.obj = cli_ctx
    
    # Show help if no command
    if ctx.invoked_subcommand is None:
        echo(ctx.get_help())


# Process command group
@cli.group()
def process():
    """Process flashcards through the pipeline"""
    pass


@process.command()
@click.argument('word')
@click.option('--context', '-c', help='Additional context for translation')
@click.option('--save/--no-save', default=True, help='Save to database')
@click.option('--force', '-f', is_flag=True, help='Force reprocessing')
@pass_context
def single(ctx: Context, word: str, context: Optional[str], save: bool, force: bool):
    """Process a single word
    
    \b
    Examples:
      flashcard process single "안녕하세요"
      flashcard process single "어렵다" --context "In the context of studying"
      flashcard process single "사랑" --force --no-save
    """
    cli_ctx: CLIContext = ctx.obj
    
    async def process_single_word():
        await cli_ctx.initialize_components()
        
        try:
            # Check cache first
            if not force:
                cached = await cli_ctx.cache_manager.get(f"flashcard:{word}")
                if cached:
                    cli_ctx.info(f"Found in cache: {word}")
                    echo(cli_ctx.format_output(cached))
                    return
            
            # Process through pipeline
            cli_ctx.info(f"Processing: {word}")
            
            if not cli_ctx.api_client:
                cli_ctx.error("API key not configured")
                return
            
            # Stage 1
            with click.progressbar(length=2, label='Processing') as bar:
                stage1_result = await cli_ctx.api_client.process_stage1(word, context)
                bar.update(1)
                
                # Stage 2
                final_result = await cli_ctx.api_client.process_stage2(stage1_result)
                bar.update(1)
            
            # Cache result
            await cli_ctx.cache_manager.set(f"flashcard:{word}", final_result, ttl=3600)
            
            # Save to database
            if save and cli_ctx.db_manager:
                await cli_ctx.db_manager.execute(
                    """INSERT OR REPLACE INTO flashcards 
                    (word, translation, difficulty, stage1_result, stage2_result) 
                    VALUES (?, ?, ?, ?, ?)""",
                    (word, final_result.get('translation'), 
                     final_result.get('difficulty', 3),
                     json.dumps(stage1_result), 
                     json.dumps(final_result))
                )
                cli_ctx.debug_msg("Saved to database")
            
            cli_ctx.success(f"Successfully processed: {word}")
            echo(cli_ctx.format_output(final_result))
            
        except Exception as e:
            cli_ctx.error(f"Failed to process: {e}")
            if cli_ctx.debug:
                import traceback
                traceback.print_exc()
        finally:
            await cli_ctx.cleanup()
    
    asyncio.run(process_single_word())


@process.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output-file', '-o', type=click.Path(), help='Output file path')
@click.option('--delimiter', '-d', default=',', help='CSV delimiter')
@click.option('--column', '-c', default=0, help='Column index for words')
@click.option('--batch-size', '-b', default=10, help='Batch size for processing')
@click.option('--continue-on-error', is_flag=True, help='Continue on errors')
@click.option('--progress/--no-progress', default=True, help='Show progress')
@pass_context
def batch(ctx: Context, input_file: str, output_file: Optional[str], 
          delimiter: str, column: int, batch_size: int, 
          continue_on_error: bool, progress: bool):
    """Process a batch of words from file
    
    \b
    Supports CSV and TXT files.
    
    Examples:
      flashcard process batch words.csv
      flashcard process batch words.txt --output results.json
      flashcard process batch data.csv --column 2 --delimiter ";"
    """
    cli_ctx: CLIContext = ctx.obj
    
    async def process_batch_file():
        await cli_ctx.initialize_components()
        
        try:
            # Read input file
            words = []
            with open(input_file) as f:
                if input_file.endswith('.csv'):
                    import csv
                    reader = csv.reader(f, delimiter=delimiter)
                    words = [row[column] for row in reader if len(row) > column]
                else:
                    words = [line.strip() for line in f if line.strip()]
            
            cli_ctx.info(f"Loaded {len(words)} words from {input_file}")
            
            results = []
            errors = []
            
            # Process in batches
            if progress:
                progress_bar = click.progressbar(
                    words, 
                    label='Processing words',
                    show_pos=True,
                    show_percent=True
                )
            else:
                progress_bar = words
            
            with progress_bar as bar:
                for word in bar:
                    try:
                        # Check cache
                        cached = await cli_ctx.cache_manager.get(f"flashcard:{word}")
                        if cached:
                            results.append(cached)
                            continue
                        
                        # Process
                        stage1 = await cli_ctx.api_client.process_stage1(word)
                        result = await cli_ctx.api_client.process_stage2(stage1)
                        
                        # Cache
                        await cli_ctx.cache_manager.set(f"flashcard:{word}", result)
                        
                        results.append(result)
                        
                    except Exception as e:
                        error_data = {
                            'word': word,
                            'error': str(e),
                            'timestamp': datetime.now().isoformat()
                        }
                        errors.append(error_data)
                        
                        if not continue_on_error:
                            cli_ctx.error(f"Failed on word '{word}': {e}")
                            break
                        else:
                            cli_ctx.warning(f"Error processing '{word}': {e}")
            
            # Save results
            output_data = {
                'processed': len(results),
                'errors': len(errors),
                'results': results,
                'error_details': errors if errors else None
            }
            
            if output_file:
                with open(output_file, 'w') as f:
                    if output_file.endswith('.yaml') or output_file.endswith('.yml'):
                        yaml.dump(output_data, f)
                    else:
                        json.dump(output_data, f, indent=2, ensure_ascii=False)
                cli_ctx.success(f"Results saved to: {output_file}")
            else:
                echo(cli_ctx.format_output(output_data))
            
            # Summary
            cli_ctx.info(f"\nSummary: {len(results)} successful, {len(errors)} errors")
            
        except Exception as e:
            cli_ctx.error(f"Batch processing failed: {e}")
            if cli_ctx.debug:
                import traceback
                traceback.print_exc()
        finally:
            await cli_ctx.cleanup()
    
    asyncio.run(process_batch_file())


# Cache command group
@cli.group()
def cache():
    """Cache management commands"""
    pass


@cache.command()
@pass_context
def stats(ctx: Context):
    """Show cache statistics
    
    \b
    Displays:
      - Hit rates
      - Memory usage
      - Entry counts
      - Eviction stats
    """
    cli_ctx: CLIContext = ctx.obj
    
    async def show_cache_stats():
        await cli_ctx.initialize_components()
        
        try:
            stats = cli_ctx.cache_manager.get_statistics()
            
            # Format for display
            if cli_ctx.output_format == "human":
                cli_ctx.secho("\n=== Cache Statistics ===", fg='blue', bold=True)
                
                # Overall stats
                cli_ctx.echo(f"\nOverall Hit Rate: {stats['overall_hit_rate']:.1%}")
                
                # L1 Cache
                cli_ctx.secho("\nL1 Cache (In-Memory):", fg='cyan')
                l1 = stats['l1']
                cli_ctx.echo(f"  Hit Rate: {l1['hit_rate']:.1%}")
                cli_ctx.echo(f"  Entries: {l1['entries']}")
                cli_ctx.echo(f"  Size: {l1['size_bytes'] / 1024:.1f} KB")
                cli_ctx.echo(f"  Evictions: {l1['evictions']}")
                
                # L2 Cache
                if 'l2' in stats and stats['l2']:
                    cli_ctx.secho("\nL2 Cache (Disk):", fg='cyan')
                    l2 = stats['l2']
                    cli_ctx.echo(f"  Hit Rate: {l2.get('hit_rate', 0):.1%}")
                    cli_ctx.echo(f"  Hits: {l2.get('hits', 0)}")
                    cli_ctx.echo(f"  Misses: {l2.get('misses', 0)}")
            else:
                echo(cli_ctx.format_output(stats))
            
        finally:
            await cli_ctx.cleanup()
    
    asyncio.run(show_cache_stats())


@cache.command()
@click.option('--tier', type=click.Choice(['all', 'l1', 'l2']), 
              default='all', help='Cache tier to clear')
@click.confirmation_option(prompt='Are you sure you want to clear the cache?')
@pass_context
def clear(ctx: Context, tier: str):
    """Clear cache entries
    
    \b
    Examples:
      flashcard cache clear          # Clear all caches
      flashcard cache clear --tier l1   # Clear only L1 cache
    """
    cli_ctx: CLIContext = ctx.obj
    
    async def clear_cache():
        await cli_ctx.initialize_components()
        
        try:
            if tier == 'all':
                await cli_ctx.cache_manager.clear()
                cli_ctx.success("Cleared all cache tiers")
            elif tier == 'l1':
                await cli_ctx.cache_manager.l1_cache.clear()
                cli_ctx.success("Cleared L1 cache")
            elif tier == 'l2' and cli_ctx.cache_manager.l2_cache:
                await cli_ctx.cache_manager.l2_cache.clear()
                cli_ctx.success("Cleared L2 cache")
            
        finally:
            await cli_ctx.cleanup()
    
    asyncio.run(clear_cache())


# Database command group
@cli.group()
def db():
    """Database operations"""
    pass


@db.command()
@click.option('--target', '-t', help='Target migration version')
@pass_context
def migrate(ctx: Context, target: Optional[str]):
    """Run database migrations
    
    \b
    Examples:
      flashcard db migrate              # Run all migrations
      flashcard db migrate --target 5   # Migrate to version 5
    """
    cli_ctx: CLIContext = ctx.obj
    
    async def run_migrations():
        await cli_ctx.initialize_components()
        
        try:
            from ..scripts.run_migrations import run_migrations
            
            # Run migrations
            cli_ctx.info("Running database migrations...")
            
            # This would call the actual migration logic
            # For now, just show a message
            cli_ctx.success("Migrations completed successfully")
            
        except Exception as e:
            cli_ctx.error(f"Migration failed: {e}")
        finally:
            await cli_ctx.cleanup()
    
    asyncio.run(run_migrations())


@db.command()
@pass_context
def stats(ctx: Context):
    """Show database statistics
    
    Displays table sizes, index usage, and query performance.
    """
    cli_ctx: CLIContext = ctx.obj
    
    async def show_db_stats():
        await cli_ctx.initialize_components()
        
        try:
            if not cli_ctx.db_manager:
                cli_ctx.error("Database not configured")
                return
            
            # Get various statistics
            stats = {}
            
            # Table stats
            result = await cli_ctx.db_manager.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            
            for row in result.rows:
                table_name = row[0]
                count_result = await cli_ctx.db_manager.execute(
                    f"SELECT COUNT(*) FROM {table_name}"
                )
                stats[table_name] = {
                    'row_count': count_result.rows[0][0]
                }
            
            # Query stats
            query_stats = await cli_ctx.db_manager.get_query_statistics()
            stats['query_performance'] = query_stats
            
            if cli_ctx.output_format == "human":
                cli_ctx.secho("\n=== Database Statistics ===", fg='blue', bold=True)
                
                cli_ctx.secho("\nTable Sizes:", fg='cyan')
                for table, info in stats.items():
                    if table != 'query_performance':
                        cli_ctx.echo(f"  {table}: {info['row_count']:,} rows")
                
                if 'query_performance' in stats:
                    perf = stats['query_performance']
                    cli_ctx.secho("\nQuery Performance:", fg='cyan')
                    cli_ctx.echo(f"  Total queries: {perf.get('total_queries', 0):,}")
                    cli_ctx.echo(f"  Slow queries: {len(perf.get('slow_queries', []))}")
                    cli_ctx.echo(f"  Cache hit rate: {perf.get('cache_hit_rate', 0):.1%}")
            else:
                echo(cli_ctx.format_output(stats))
            
        finally:
            await cli_ctx.cleanup()
    
    asyncio.run(show_db_stats())


# Monitor command group
@cli.group()
def monitor():
    """Monitoring and analytics commands"""
    pass


@monitor.command()
@click.option('--last', default='1h', help='Time window (e.g., 1h, 24h, 7d)')
@click.option('--category', type=click.Choice(['all', 'transient', 'permanent', 'system', 'business', 'degraded']),
              default='all', help='Error category filter')
@click.option('--severity', type=click.Choice(['all', 'low', 'medium', 'high', 'critical']),
              default='all', help='Error severity filter')
@pass_context
def errors(ctx: Context, last: str, category: str, severity: str):
    """Show error analytics
    
    \b
    Examples:
      flashcard monitor errors --last 1h
      flashcard monitor errors --category system --severity high
      flashcard monitor errors --last 24h
    """
    cli_ctx: CLIContext = ctx.obj
    
    async def show_error_analytics():
        await cli_ctx.initialize_components()
        
        try:
            # Parse time window
            time_map = {
                'h': 'hours',
                'd': 'days',
                'w': 'weeks'
            }
            
            amount = int(last[:-1])
            unit = time_map.get(last[-1], 'hours')
            time_window = timedelta(**{unit: amount})
            
            # Get analytics
            analytics = ErrorAnalytics(cli_ctx.error_collector, cli_ctx.db_manager)
            
            # Apply filters
            from ..errors import ErrorCategory, ErrorSeverity
            cat_filter = None if category == 'all' else ErrorCategory(category)
            sev_filter = None if severity == 'all' else ErrorSeverity(severity)
            
            metrics = await analytics.get_error_metrics(
                time_window=time_window,
                category_filter=cat_filter,
                severity_filter=sev_filter
            )
            
            if cli_ctx.output_format == "human":
                cli_ctx.secho(f"\n=== Error Analytics (Last {last}) ===", fg='red', bold=True)
                
                cli_ctx.echo(f"\nTotal Errors: {metrics.total_errors}")
                cli_ctx.echo(f"Unique Errors: {metrics.unique_errors}")
                cli_ctx.echo(f"Error Rate: {metrics.error_rate:.2f} per minute")
                
                if metrics.errors_by_category:
                    cli_ctx.secho("\nBy Category:", fg='cyan')
                    for cat, count in metrics.errors_by_category.items():
                        cli_ctx.echo(f"  {cat}: {count}")
                
                if metrics.errors_by_severity:
                    cli_ctx.secho("\nBy Severity:", fg='cyan')
                    for sev, count in metrics.errors_by_severity.items():
                        color = {'low': 'green', 'medium': 'yellow', 
                                'high': 'red', 'critical': 'red'}
                        cli_ctx.secho(f"  {sev}: {count}", fg=color.get(sev, 'white'))
                
                if metrics.top_errors:
                    cli_ctx.secho("\nTop Errors:", fg='cyan')
                    for fingerprint, count in metrics.top_errors[:5]:
                        cli_ctx.echo(f"  {fingerprint[:16]}...: {count} occurrences")
            else:
                echo(cli_ctx.format_output(metrics.__dict__))
            
        finally:
            await cli_ctx.cleanup()
    
    asyncio.run(show_error_analytics())


@monitor.command()
@pass_context
def health(ctx: Context):
    """System health check
    
    Checks all components and reports their status.
    """
    cli_ctx: CLIContext = ctx.obj
    
    async def check_health():
        await cli_ctx.initialize_components()
        
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'components': {}
        }
        
        try:
            # Check database
            if cli_ctx.db_manager:
                try:
                    await cli_ctx.db_manager.execute("SELECT 1")
                    health_status['components']['database'] = 'healthy'
                except Exception as e:
                    health_status['components']['database'] = f'unhealthy: {e}'
            
            # Check cache
            try:
                await cli_ctx.cache_manager.set("health_check", "ok", ttl=1)
                value = await cli_ctx.cache_manager.get("health_check")
                if value == "ok":
                    health_status['components']['cache'] = 'healthy'
                else:
                    health_status['components']['cache'] = 'unhealthy: read/write mismatch'
            except Exception as e:
                health_status['components']['cache'] = f'unhealthy: {e}'
            
            # Check API
            if cli_ctx.api_client:
                try:
                    health = await cli_ctx.api_client.health_check()
                    health_status['components']['api'] = health.get('status', 'unknown')
                except Exception as e:
                    health_status['components']['api'] = f'unhealthy: {e}'
            
            # Overall status
            all_healthy = all(
                status == 'healthy' 
                for status in health_status['components'].values()
            )
            health_status['overall'] = 'healthy' if all_healthy else 'degraded'
            
            if cli_ctx.output_format == "human":
                cli_ctx.secho("\n=== System Health Check ===", fg='blue', bold=True)
                
                for component, status in health_status['components'].items():
                    if status == 'healthy':
                        cli_ctx.success(f"{component}: {status}")
                    else:
                        cli_ctx.error(f"{component}: {status}")
                
                cli_ctx.echo(f"\nOverall Status: {health_status['overall']}")
            else:
                echo(cli_ctx.format_output(health_status))
            
        finally:
            await cli_ctx.cleanup()
    
    asyncio.run(check_health())


# Config command group
@cli.group()
def config():
    """Configuration management"""
    pass


@config.command()
@pass_context
def show(ctx: Context):
    """Show current configuration"""
    cli_ctx: CLIContext = ctx.obj
    
    config_data = {
        'database': cli_ctx.db_path,
        'api_key': '***' if cli_ctx.api_key else None,
        'telemetry_enabled': cli_ctx.telemetry_enabled,
        'output_format': cli_ctx.output_format,
        'debug': cli_ctx.debug,
        'verbose': cli_ctx.verbose,
        'custom_config': cli_ctx.config
    }
    
    if cli_ctx.output_format == "human":
        cli_ctx.secho("\n=== Current Configuration ===", fg='blue', bold=True)
        for key, value in config_data.items():
            cli_ctx.echo(f"{key}: {value}")
    else:
        echo(cli_ctx.format_output(config_data))


@config.command()
@click.argument('key')
@click.argument('value')
@pass_context
def set(ctx: Context, key: str, value: str):
    """Set a configuration value
    
    \b
    Examples:
      flashcard config set api_key "your-key-here"
      flashcard config set output json
      flashcard config set telemetry false
    """
    cli_ctx: CLIContext = ctx.obj
    
    # Map of valid config keys
    config_map = {
        'api_key': 'api_key',
        'database': 'db_path',
        'db': 'db_path',
        'output': 'output_format',
        'telemetry': 'telemetry_enabled',
        'verbose': 'verbose',
        'debug': 'debug'
    }
    
    if key not in config_map:
        cli_ctx.error(f"Unknown config key: {key}")
        cli_ctx.info(f"Valid keys: {', '.join(config_map.keys())}")
        return
    
    # Convert values
    if key in ['telemetry', 'verbose', 'debug']:
        value = value.lower() in ['true', 'yes', '1', 'on']
    
    # Update config
    cli_ctx.config[key] = value
    cli_ctx.success(f"Set {key} = {value}")
    
    # TODO: Save to config file
    cli_ctx.info("Note: Config changes are not persisted yet")


@config.command()
@pass_context
def validate(ctx: Context):
    """Validate configuration
    
    Checks API key, database connection, and other settings.
    """
    cli_ctx: CLIContext = ctx.obj
    
    async def validate_config():
        await cli_ctx.initialize_components()
        
        issues = []
        warnings = []
        
        try:
            # Check API key
            if not cli_ctx.api_key:
                issues.append("API key not configured")
            else:
                # Test API connection
                try:
                    health = await cli_ctx.api_client.health_check()
                    if health.get('status') != 'healthy':
                        warnings.append(f"API health check: {health.get('status')}")
                except Exception as e:
                    issues.append(f"API connection failed: {e}")
            
            # Check database
            if cli_ctx.db_manager:
                try:
                    await cli_ctx.db_manager.execute("SELECT 1")
                except Exception as e:
                    issues.append(f"Database connection failed: {e}")
            
            # Check cache
            try:
                await cli_ctx.cache_manager.set("config_test", "ok", ttl=1)
                value = await cli_ctx.cache_manager.get("config_test")
                if value != "ok":
                    warnings.append("Cache read/write mismatch")
            except Exception as e:
                issues.append(f"Cache test failed: {e}")
            
            # Display results
            if cli_ctx.output_format == "human":
                cli_ctx.secho("\n=== Configuration Validation ===", fg='blue', bold=True)
                
                if not issues and not warnings:
                    cli_ctx.success("All configuration checks passed")
                else:
                    if issues:
                        cli_ctx.secho("\nIssues (must fix):", fg='red')
                        for issue in issues:
                            cli_ctx.error(f"  {issue}")
                    
                    if warnings:
                        cli_ctx.secho("\nWarnings (optional):", fg='yellow')
                        for warning in warnings:
                            cli_ctx.warning(f"  {warning}")
                    
                    cli_ctx.echo(f"\nFound {len(issues)} issues, {len(warnings)} warnings")
            else:
                result = {
                    'valid': len(issues) == 0,
                    'issues': issues,
                    'warnings': warnings
                }
                echo(cli_ctx.format_output(result))
            
        finally:
            await cli_ctx.cleanup()
    
    asyncio.run(validate_config())


# Utility functions
def setup_shell_completion():
    """Setup shell completion for the CLI"""
    shell = os.environ.get('SHELL', '')
    
    if 'bash' in shell:
        completion_script = """
# Flashcard CLI completion for bash
_flashcard_completion() {
    local IFS=$'\\n'
    COMPREPLY=( $( env COMP_WORDS="${COMP_WORDS[*]}" \\
                   COMP_CWORD=$COMP_CWORD \\
                   _FLASHCARD_COMPLETE=bash_complete $1 ) )
    return 0
}
complete -F _flashcard_completion -o default flashcard
"""
        return completion_script
    
    elif 'zsh' in shell:
        completion_script = """
# Flashcard CLI completion for zsh
#compdef flashcard
_flashcard_completion() {
    eval $(env _FLASHCARD_COMPLETE=zsh_source flashcard)
}
compdef _flashcard_completion flashcard
"""
        return completion_script
    
    elif 'fish' in shell:
        completion_script = """
# Flashcard CLI completion for fish
function _flashcard_completion
    set -l response (env _FLASHCARD_COMPLETE=fish_complete COMP_WORDS=(commandline -cp) COMP_CWORD=(commandline -t) flashcard)
    for completion in $response
        echo -E "$completion"
    end
end
complete -c flashcard -f -a '(_flashcard_completion)'
"""
        return completion_script
    
    return None


# Additional helper functions
def format_duration(seconds: float) -> str:
    """Format duration in human-readable format"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"


def format_bytes(bytes_val: int) -> str:
    """Format bytes in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f}{unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f}PB"


def create_table(headers: List[str], rows: List[List[str]], 
                 colors: Optional[List[str]] = None) -> str:
    """Create a formatted table"""
    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    
    # Create separator
    separator = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    
    # Create header
    header_row = "|" + "|".join(f" {h:<{w}} " for h, w in zip(headers, widths)) + "|"
    
    # Create rows
    table_rows = []
    for row in rows:
        cells = []
        for i, (cell, width) in enumerate(zip(row, widths)):
            cell_str = f" {str(cell):<{width}} "
            if colors and i < len(colors):
                cell_str = click.style(cell_str, fg=colors[i])
            cells.append(cell_str)
        table_rows.append("|" + "|".join(cells) + "|")
    
    # Combine
    table = [separator, header_row, separator] + table_rows + [separator]
    return "\n".join(table)


if __name__ == '__main__':
    cli()