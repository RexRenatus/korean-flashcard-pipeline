"""Base CLI classes and context management"""

from typing import Optional, Dict, Any, List
from pathlib import Path
import asyncio
from dataclasses import dataclass
from rich.console import Console
import typer
import logging

from .config import Config, load_config
from .errors import ErrorHandler

logger = logging.getLogger(__name__)


@dataclass
class CLIContext:
    """Context object passed to all CLI commands"""
    config: Config
    console: Console
    error_handler: ErrorHandler
    json_output: bool = False
    quiet: bool = False
    verbose: bool = False
    no_color: bool = False
    
    @property
    def is_interactive(self) -> bool:
        """Check if running in interactive mode"""
        return not (self.json_output or self.quiet)


class BaseCLI:
    """Base class for CLI commands"""
    
    def __init__(self, name: str, help: str):
        self.name = name
        self.help = help
        self.app = typer.Typer(name=name, help=help)
        
    def add_command(self, func, name: Optional[str] = None) -> None:
        """Add a command to this CLI group"""
        self.app.command(name=name)(func)
        
    def add_subgroup(self, cli: "BaseCLI") -> None:
        """Add a subgroup CLI"""
        self.app.add_typer(cli.app, name=cli.name)


class AsyncTyper(typer.Typer):
    """Typer with async command support"""
    
    def command(self, *args, **kwargs):
        def decorator(func):
            # If the function is async, wrap it
            if asyncio.iscoroutinefunction(func):
                func = self._wrap_async(func)
            return super(AsyncTyper, self).command(*args, **kwargs)(func)
        return decorator
    
    @staticmethod
    def _wrap_async(func):
        """Wrap async function for typer"""
        def wrapper(*args, **kwargs):
            return asyncio.run(func(*args, **kwargs))
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper


def create_cli_context(
    config_file: Optional[Path] = None,
    log_level: Optional[str] = None,
    no_color: bool = False,
    json: bool = False,
    quiet: bool = False,
    **kwargs
) -> CLIContext:
    """Create CLI context from arguments"""
    
    # Load configuration
    config = load_config(
        config_file=config_file,
        log_level=log_level,
        **kwargs
    )
    
    # Set up console
    console = Console(
        force_terminal=not no_color,
        force_jupyter=False,
        no_color=no_color or json or quiet
    )
    
    # Set up error handler
    error_handler = ErrorHandler(console=console, json_output=json)
    
    # Configure logging
    if log_level:
        logging.getLogger().setLevel(log_level.upper())
    
    return CLIContext(
        config=config,
        console=console,
        error_handler=error_handler,
        json_output=json,
        quiet=quiet,
        verbose=log_level == "DEBUG",
        no_color=no_color
    )


# Global options that can be reused across commands
GLOBAL_OPTIONS = {
    "config": typer.Option(None, "--config", "-c", help="Configuration file path"),
    "log_level": typer.Option(None, "--log-level", help="Log level (DEBUG, INFO, WARNING, ERROR)"),
    "no_color": typer.Option(False, "--no-color", help="Disable colored output"),
    "json": typer.Option(False, "--json", help="Output in JSON format"),
    "quiet": typer.Option(False, "--quiet", "-q", help="Suppress non-error output"),
}


def async_command(app: typer.Typer):
    """Decorator to add async command support"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            def wrapper(*args, **kwargs):
                return asyncio.run(func(*args, **kwargs))
            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            return app.command()(wrapper)
        return app.command()(func)
    return decorator