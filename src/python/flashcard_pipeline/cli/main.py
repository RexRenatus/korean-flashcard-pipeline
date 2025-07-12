"""
Main CLI entry point for the flashcard pipeline.
This module re-exports the protected cli_v2 implementation and adds enhanced ingress commands.
"""

import typer
from typing import Optional
from pathlib import Path

# Import the protected cli_v2 app directly
from ..cli_v2 import app as cli_v2_app

# Create a new app that extends cli_v2
app = typer.Typer(
    name="flashcard-pipeline",
    help="Korean Language Flashcard Pipeline - Complete implementation with all 5 phases",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

# Mount the entire cli_v2 app to preserve all its functionality
# This ensures we don't modify or break the protected implementation
for command in cli_v2_app.registered_commands:
    app.command(
        name=command.name,
        help=command.help,
        epilog=command.epilog,
        short_help=command.short_help,
        hidden=command.hidden,
        deprecated=command.deprecated,
    )(command.callback)

# Import enhanced ingress commands from cli_enhanced
try:
    from .ingress_enhanced import create_enhanced_ingress_group
    
    # Add enhanced ingress commands as a subgroup
    enhanced_ingress = create_enhanced_ingress_group()
    app.add_typer(enhanced_ingress, name="ingress-enhanced", help="Enhanced ingress commands with batch management")
except ImportError:
    # If enhanced ingress is not available, continue without it
    pass


def main():
    """Main entry point for the CLI"""
    app()


if __name__ == "__main__":
    main()