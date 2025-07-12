"""Interactive CLI features for Flashcard Pipeline"""

import os
import sys
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

import click
from click import prompt, confirm, echo, secho, style
from click.types import Choice
import questionary
from questionary import Style

# Custom style for questionary
custom_style = Style([
    ('qmark', 'fg:#673ab7 bold'),
    ('question', 'bold'),
    ('answer', 'fg:#f44336 bold'),
    ('pointer', 'fg:#673ab7 bold'),
    ('highlighted', 'fg:#673ab7 bold'),
    ('selected', 'fg:#cc5454'),
    ('separator', 'fg:#cc5454'),
    ('instruction', ''),
    ('text', ''),
    ('disabled', 'fg:#858585 italic')
])


class InteractiveCLI:
    """Interactive CLI helper functions"""
    
    @staticmethod
    def guided_setup() -> Dict[str, Any]:
        """Interactive setup wizard"""
        secho("\n🚀 Flashcard Pipeline Setup Wizard", fg='blue', bold=True)
        secho("Let's configure your flashcard pipeline!\n", fg='cyan')
        
        config = {}
        
        # API Configuration
        secho("📡 API Configuration", fg='yellow', bold=True)
        
        config['api_key'] = questionary.password(
            "Enter your OpenRouter API key:",
            validate=lambda x: len(x) > 0 or "API key is required"
        ).ask()
        
        config['model'] = questionary.select(
            "Select AI model:",
            choices=[
                "claude-3-haiku",
                "claude-3-sonnet", 
                "claude-3-opus",
                "gpt-4",
                "gpt-3.5-turbo"
            ],
            default="claude-3-haiku"
        ).ask()
        
        # Database Configuration
        secho("\n💾 Database Configuration", fg='yellow', bold=True)
        
        config['db_path'] = questionary.path(
            "Database file path:",
            default="flashcards.db",
            validate=lambda x: True  # Allow any path
        ).ask()
        
        # Cache Configuration
        secho("\n🚄 Cache Configuration", fg='yellow', bold=True)
        
        config['cache_enabled'] = questionary.confirm(
            "Enable caching?",
            default=True
        ).ask()
        
        if config['cache_enabled']:
            config['cache_type'] = questionary.select(
                "Cache type:",
                choices=["memory", "disk", "redis"],
                default="memory"
            ).ask()
            
            if config['cache_type'] == "redis":
                config['redis_url'] = questionary.text(
                    "Redis URL:",
                    default="redis://localhost:6379"
                ).ask()
        
        # Telemetry Configuration
        secho("\n📊 Telemetry Configuration", fg='yellow', bold=True)
        
        config['telemetry_enabled'] = questionary.confirm(
            "Enable telemetry?",
            default=True
        ).ask()
        
        if config['telemetry_enabled']:
            config['telemetry_endpoint'] = questionary.text(
                "Telemetry endpoint (leave empty for default):",
                default=""
            ).ask()
        
        # Output Configuration
        secho("\n📝 Output Configuration", fg='yellow', bold=True)
        
        config['output_format'] = questionary.select(
            "Default output format:",
            choices=["human", "json", "yaml"],
            default="human"
        ).ask()
        
        config['color_output'] = questionary.confirm(
            "Enable colored output?",
            default=True
        ).ask()
        
        # Summary
        secho("\n✅ Configuration Summary", fg='green', bold=True)
        for key, value in config.items():
            if key == 'api_key':
                value = '***' + value[-4:] if len(value) > 4 else '***'
            secho(f"  {key}: {value}", fg='white')
        
        if questionary.confirm("\nSave this configuration?", default=True).ask():
            return config
        else:
            return None
    
    @staticmethod
    def select_words_interactive(words: List[str], 
                                purpose: str = "processing") -> List[str]:
        """Interactive word selection"""
        if not words:
            return []
        
        secho(f"\n📋 Select words for {purpose}", fg='blue', bold=True)
        
        choices = questionary.checkbox(
            f"Select words (space to select, enter to confirm):",
            choices=words,
            style=custom_style
        ).ask()
        
        return choices or []
    
    @staticmethod
    def batch_processing_wizard() -> Dict[str, Any]:
        """Interactive batch processing configuration"""
        secho("\n📦 Batch Processing Configuration", fg='blue', bold=True)
        
        options = {}
        
        # Input file
        options['input_file'] = questionary.path(
            "Input file path:",
            validate=lambda x: Path(x).exists() or "File does not exist"
        ).ask()
        
        # File type detection
        file_ext = Path(options['input_file']).suffix.lower()
        
        if file_ext == '.csv':
            options['delimiter'] = questionary.text(
                "CSV delimiter:",
                default=","
            ).ask()
            
            # Preview file
            with open(options['input_file'], 'r', encoding='utf-8') as f:
                preview_lines = [f.readline().strip() for _ in range(3)]
            
            secho("\nFile preview:", fg='cyan')
            for line in preview_lines:
                echo(f"  {line}")
            
            options['column'] = questionary.text(
                "Column index (0-based) or name:",
                default="0"
            ).ask()
            
            options['has_header'] = questionary.confirm(
                "File has header row?",
                default=True
            ).ask()
        
        # Processing options
        options['batch_size'] = int(questionary.text(
            "Batch size:",
            default="10",
            validate=lambda x: x.isdigit() and int(x) > 0 or "Must be positive number"
        ).ask())
        
        options['continue_on_error'] = questionary.confirm(
            "Continue processing on errors?",
            default=True
        ).ask()
        
        # Output options
        options['save_output'] = questionary.confirm(
            "Save results to file?",
            default=True
        ).ask()
        
        if options['save_output']:
            default_output = str(Path(options['input_file']).with_suffix('.results.json'))
            options['output_file'] = questionary.path(
                "Output file path:",
                default=default_output
            ).ask()
        
        return options
    
    @staticmethod
    def error_investigation_wizard(errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Interactive error investigation"""
        if not errors:
            secho("No errors to investigate", fg='green')
            return None
        
        secho(f"\n🔍 Error Investigation ({len(errors)} errors)", fg='red', bold=True)
        
        # Group errors by type
        error_types = {}
        for error in errors:
            error_type = error.get('type', 'Unknown')
            if error_type not in error_types:
                error_types[error_type] = []
            error_types[error_type].append(error)
        
        # Select error type to investigate
        error_type = questionary.select(
            "Select error type to investigate:",
            choices=[f"{k} ({len(v)} errors)" for k, v in error_types.items()]
        ).ask()
        
        if not error_type:
            return None
        
        error_type = error_type.split(' (')[0]
        selected_errors = error_types[error_type]
        
        # Show error details
        for i, error in enumerate(selected_errors[:5]):  # Show first 5
            secho(f"\nError {i+1}:", fg='yellow')
            echo(f"  Message: {error.get('message', 'No message')}")
            echo(f"  Context: {error.get('context', 'No context')}")
            echo(f"  Time: {error.get('timestamp', 'Unknown')}")
        
        # Action selection
        action = questionary.select(
            "\nWhat would you like to do?",
            choices=[
                "Retry failed items",
                "Export error report", 
                "View detailed traces",
                "Skip and continue",
                "Exit"
            ]
        ).ask()
        
        return {
            'error_type': error_type,
            'errors': selected_errors,
            'action': action
        }
    
    @staticmethod
    def progress_monitor(total: int, desc: str = "Processing") -> 'InteractiveProgress':
        """Create interactive progress monitor"""
        return InteractiveProgress(total, desc)
    
    @staticmethod
    def confirm_destructive_action(action: str, details: str = None) -> bool:
        """Confirm destructive actions with extra safety"""
        secho(f"\n⚠️  Warning: {action}", fg='red', bold=True)
        
        if details:
            secho(f"\nDetails: {details}", fg='yellow')
        
        secho("\nThis action cannot be undone!", fg='red')
        
        # First confirmation
        if not questionary.confirm(
            "Are you sure you want to proceed?",
            default=False
        ).ask():
            return False
        
        # Second confirmation for extra safety
        confirmation_text = questionary.text(
            f"Type 'yes' to confirm {action}:",
            validate=lambda x: x.lower() == 'yes' or "Type 'yes' to confirm"
        ).ask()
        
        return confirmation_text.lower() == 'yes'
    
    @staticmethod
    def multi_step_process(steps: List[Tuple[str, callable]]) -> List[Any]:
        """Execute multi-step process with interactive feedback"""
        results = []
        
        secho(f"\n🔄 Executing {len(steps)} steps", fg='blue', bold=True)
        
        for i, (step_name, step_func) in enumerate(steps):
            secho(f"\nStep {i+1}/{len(steps)}: {step_name}", fg='cyan')
            
            try:
                result = step_func()
                results.append(result)
                secho(f"  ✓ Completed", fg='green')
                
            except Exception as e:
                secho(f"  ✗ Failed: {e}", fg='red')
                
                action = questionary.select(
                    "What would you like to do?",
                    choices=[
                        "Retry this step",
                        "Skip and continue",
                        "Abort process"
                    ]
                ).ask()
                
                if action == "Retry this step":
                    try:
                        result = step_func()
                        results.append(result)
                        secho(f"  ✓ Retry successful", fg='green')
                    except Exception as e2:
                        secho(f"  ✗ Retry failed: {e2}", fg='red')
                        results.append(None)
                elif action == "Skip and continue":
                    results.append(None)
                else:
                    break
        
        return results


class InteractiveProgress:
    """Interactive progress indicator with live updates"""
    
    def __init__(self, total: int, desc: str = "Processing"):
        self.total = total
        self.desc = desc
        self.current = 0
        self.start_time = None
        self.errors = []
        
    def __enter__(self):
        self.start_time = click.get_text_stream('stderr').isatty()
        if self.start_time:
            self.bar = click.progressbar(
                length=self.total,
                label=self.desc,
                show_eta=True,
                show_percent=True,
                show_pos=True
            )
            self.bar.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, 'bar'):
            self.bar.__exit__(exc_type, exc_val, exc_tb)
        
        # Show summary
        if self.errors:
            secho(f"\n⚠️  Completed with {len(self.errors)} errors", fg='yellow')
        else:
            secho(f"\n✅ Completed successfully", fg='green')
    
    def update(self, n: int = 1, error: Optional[str] = None):
        """Update progress"""
        self.current += n
        
        if error:
            self.errors.append(error)
        
        if hasattr(self, 'bar'):
            self.bar.update(n)
    
    def set_description(self, desc: str):
        """Update description"""
        self.desc = desc
        if hasattr(self, 'bar'):
            self.bar.label = desc


# Interactive command decorators
def interactive_command(func):
    """Decorator to make commands interactive when no args provided"""
    def wrapper(*args, **kwargs):
        ctx = click.get_current_context()
        
        # Check if running in interactive mode
        if not sys.stdin.isatty():
            return func(*args, **kwargs)
        
        # Check if required args are missing
        missing_args = []
        for param in ctx.command.params:
            if param.required and param.name not in kwargs:
                missing_args.append(param)
        
        if missing_args:
            secho("\n🎯 Interactive Mode", fg='blue', bold=True)
            secho("Missing required arguments. Let's fill them in!\n", fg='cyan')
            
            for param in missing_args:
                if param.type == click.STRING:
                    value = questionary.text(
                        f"{param.name.replace('_', ' ').title()}:",
                        validate=lambda x: len(x) > 0 or f"{param.name} is required"
                    ).ask()
                elif param.type == click.Path:
                    value = questionary.path(
                        f"{param.name.replace('_', ' ').title()}:"
                    ).ask()
                elif isinstance(param.type, click.Choice):
                    value = questionary.select(
                        f"{param.name.replace('_', ' ').title()}:",
                        choices=param.type.choices
                    ).ask()
                else:
                    value = prompt(f"{param.name.replace('_', ' ').title()}:")
                
                kwargs[param.name] = value
        
        return func(*args, **kwargs)
    
    return wrapper


# Utility functions for rich output
def create_spinner(text: str = "Processing..."):
    """Create a spinner for long operations"""
    if sys.stdout.isatty():
        return click.progressbar(
            length=100,
            label=text,
            bar_template='%(label)s  %(bar)s',
            show_eta=False,
            show_percent=False,
            show_pos=False,
            width=0
        )
    return None


def print_boxed(text: str, color: str = 'blue', width: int = 60):
    """Print text in a box"""
    lines = text.split('\n')
    max_len = max(len(line) for line in lines)
    width = max(width, max_len + 4)
    
    border = "+" + "-" * (width - 2) + "+"
    secho(border, fg=color)
    
    for line in lines:
        padded = f"| {line:<{width-4}} |"
        secho(padded, fg=color)
    
    secho(border, fg=color)


def print_tree(data: Dict[str, Any], indent: int = 0, prefix: str = ""):
    """Print data as a tree structure"""
    items = list(data.items())
    
    for i, (key, value) in enumerate(items):
        is_last = i == len(items) - 1
        
        # Print key
        if indent == 0:
            connector = ""
        else:
            connector = "└── " if is_last else "├── "
        
        secho(f"{prefix}{connector}{key}", fg='cyan', bold=True)
        
        # Print value
        if isinstance(value, dict):
            extension = "    " if is_last else "│   "
            print_tree(value, indent + 1, prefix + extension)
        elif isinstance(value, list):
            extension = "    " if is_last else "│   "
            for j, item in enumerate(value):
                item_connector = "└── " if j == len(value) - 1 else "├── "
                echo(f"{prefix}{extension}{item_connector}{item}")
        else:
            extension = "    " if is_last else "│   "
            echo(f"{prefix}{extension}    {value}")