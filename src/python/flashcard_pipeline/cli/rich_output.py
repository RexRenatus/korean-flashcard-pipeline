"""Rich output formatting for Flashcard Pipeline CLI"""

import json
import sys
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from io import StringIO

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, BarColumn, TextColumn
from rich.syntax import Syntax
from rich.tree import Tree
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.columns import Columns
from rich.markdown import Markdown
from rich import box
import pygments
from pygments.lexers import JsonLexer, YamlLexer, PythonLexer
from pygments.formatters import TerminalFormatter


class RichOutput:
    """Rich output formatting utilities"""
    
    def __init__(self, no_color: bool = False):
        self.console = Console(no_color=no_color, force_terminal=not no_color)
        self.no_color = no_color
    
    def print_flashcard(self, flashcard: Dict[str, Any], detailed: bool = False):
        """Print a flashcard with rich formatting"""
        # Create main panel
        title = f"[bold blue]{flashcard.get('word', 'Unknown')}[/bold blue]"
        
        # Basic info
        content = []
        content.append(f"[green]Translation:[/green] {flashcard.get('translation', 'N/A')}")
        content.append(f"[yellow]Pronunciation:[/yellow] {flashcard.get('pronunciation', 'N/A')}")
        content.append(f"[cyan]Difficulty:[/cyan] {'⭐' * flashcard.get('difficulty', 0)}")
        
        if detailed:
            # Add detailed information
            if 'definition' in flashcard:
                content.append("")
                content.append(f"[magenta]Definition:[/magenta]\n{flashcard['definition']}")
            
            if 'examples' in flashcard:
                content.append("")
                content.append("[magenta]Examples:[/magenta]")
                for i, example in enumerate(flashcard['examples'][:3]):
                    content.append(f"  {i+1}. {example}")
            
            if 'mnemonics' in flashcard:
                content.append("")
                content.append(f"[magenta]Mnemonic:[/magenta]\n{flashcard['mnemonics']}")
        
        panel = Panel(
            "\n".join(content),
            title=title,
            border_style="blue",
            box=box.ROUNDED
        )
        
        self.console.print(panel)
    
    def print_flashcard_table(self, flashcards: List[Dict[str, Any]]):
        """Print flashcards in a table format"""
        table = Table(
            title="Flashcard Results",
            show_header=True,
            header_style="bold magenta",
            box=box.ROUNDED
        )
        
        # Add columns
        table.add_column("Word", style="cyan", no_wrap=True)
        table.add_column("Translation", style="green")
        table.add_column("Pronunciation", style="yellow")
        table.add_column("Difficulty", justify="center")
        table.add_column("Status", justify="center")
        
        # Add rows
        for card in flashcards:
            difficulty = "⭐" * card.get('difficulty', 0)
            status = "[green]✓[/green]" if card.get('status') == 'success' else "[red]✗[/red]"
            
            table.add_row(
                card.get('word', ''),
                card.get('translation', ''),
                card.get('pronunciation', ''),
                difficulty,
                status
            )
        
        self.console.print(table)
    
    def print_error_table(self, errors: List[Dict[str, Any]]):
        """Print errors in a formatted table"""
        if not errors:
            self.console.print("[green]No errors found![/green]")
            return
        
        table = Table(
            title=f"[red]Error Report ({len(errors)} errors)[/red]",
            show_header=True,
            header_style="bold red",
            box=box.HEAVY
        )
        
        table.add_column("Time", style="dim", width=19)
        table.add_column("Type", style="red")
        table.add_column("Message", style="yellow")
        table.add_column("Context", style="cyan")
        
        for error in errors[:20]:  # Show max 20 errors
            timestamp = error.get('timestamp', '')
            if isinstance(timestamp, (int, float)):
                timestamp = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            
            table.add_row(
                timestamp,
                error.get('type', 'Unknown'),
                error.get('message', 'No message')[:50] + "...",
                json.dumps(error.get('context', {}))[:30] + "..."
            )
        
        self.console.print(table)
        
        if len(errors) > 20:
            self.console.print(f"[dim]... and {len(errors) - 20} more errors[/dim]")
    
    def print_statistics(self, stats: Dict[str, Any]):
        """Print statistics in a dashboard layout"""
        # Create layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        # Header
        layout["header"].update(
            Panel(
                "[bold blue]Flashcard Pipeline Statistics[/bold blue]",
                box=box.DOUBLE
            )
        )
        
        # Body - split into columns
        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        # Performance stats
        perf_table = Table(
            title="Performance Metrics",
            show_header=True,
            box=box.SIMPLE
        )
        perf_table.add_column("Metric", style="cyan")
        perf_table.add_column("Value", justify="right")
        
        perf_stats = stats.get('performance', {})
        perf_table.add_row("Total Processed", str(perf_stats.get('total', 0)))
        perf_table.add_row("Success Rate", f"{perf_stats.get('success_rate', 0):.1%}")
        perf_table.add_row("Avg Time/Card", f"{perf_stats.get('avg_time', 0):.2f}s")
        perf_table.add_row("Cache Hit Rate", f"{perf_stats.get('cache_hit_rate', 0):.1%}")
        
        layout["body"]["left"].update(Panel(perf_table))
        
        # Error stats
        error_table = Table(
            title="Error Summary",
            show_header=True,
            box=box.SIMPLE
        )
        error_table.add_column("Category", style="red")
        error_table.add_column("Count", justify="right")
        
        error_stats = stats.get('errors', {})
        for category, count in error_stats.items():
            error_table.add_row(category, str(count))
        
        layout["body"]["right"].update(Panel(error_table))
        
        # Footer
        layout["footer"].update(
            Panel(
                f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                style="dim"
            )
        )
        
        self.console.print(layout)
    
    def create_progress_bar(self, total: int, description: str = "Processing"):
        """Create a rich progress bar"""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console
        )
    
    def print_json_syntax(self, data: Any, theme: str = "monokai"):
        """Print JSON with syntax highlighting"""
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        syntax = Syntax(json_str, "json", theme=theme, line_numbers=False)
        self.console.print(syntax)
    
    def print_yaml_syntax(self, data: Any, theme: str = "monokai"):
        """Print YAML with syntax highlighting"""
        import yaml
        yaml_str = yaml.dump(data, default_flow_style=False, allow_unicode=True)
        syntax = Syntax(yaml_str, "yaml", theme=theme, line_numbers=False)
        self.console.print(syntax)
    
    def print_diff(self, before: str, after: str, title: str = "Changes"):
        """Print a diff with colors"""
        from difflib import unified_diff
        
        diff_lines = list(unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile="before",
            tofile="after"
        ))
        
        if not diff_lines:
            self.console.print("[yellow]No changes[/yellow]")
            return
        
        # Create colored diff
        colored_diff = []
        for line in diff_lines:
            if line.startswith('+'):
                colored_diff.append(f"[green]{line}[/green]")
            elif line.startswith('-'):
                colored_diff.append(f"[red]{line}[/red]")
            elif line.startswith('@'):
                colored_diff.append(f"[blue]{line}[/blue]")
            else:
                colored_diff.append(line)
        
        panel = Panel(
            "".join(colored_diff),
            title=title,
            border_style="blue"
        )
        self.console.print(panel)
    
    def print_tree_structure(self, data: Dict[str, Any], title: str = "Structure"):
        """Print data as a tree"""
        tree = Tree(f"[bold blue]{title}[/bold blue]")
        
        def add_branch(node: Tree, data: Any, name: str = ""):
            if isinstance(data, dict):
                branch = node.add(f"[bold cyan]{name}[/bold cyan]" if name else "")
                for key, value in data.items():
                    add_branch(branch, value, str(key))
            elif isinstance(data, list):
                branch = node.add(f"[bold cyan]{name}[/bold cyan] [dim]({len(data)} items)[/dim]")
                for i, item in enumerate(data[:5]):  # Show first 5
                    add_branch(branch, item, f"[{i}]")
                if len(data) > 5:
                    branch.add("[dim]...[/dim]")
            else:
                node.add(f"[green]{name}[/green]: {data}")
        
        add_branch(tree, data)
        self.console.print(tree)
    
    def create_live_display(self) -> Live:
        """Create a live display for real-time updates"""
        return Live(console=self.console, refresh_per_second=4)
    
    def format_duration(self, seconds: float) -> str:
        """Format duration with color"""
        if seconds < 1:
            return f"[green]{seconds*1000:.0f}ms[/green]"
        elif seconds < 60:
            return f"[yellow]{seconds:.1f}s[/yellow]"
        else:
            return f"[red]{seconds/60:.1f}m[/red]"
    
    def format_size(self, bytes_val: int) -> str:
        """Format file size with color"""
        for unit, color in [('B', 'green'), ('KB', 'green'), 
                           ('MB', 'yellow'), ('GB', 'red'), ('TB', 'red')]:
            if bytes_val < 1024.0:
                return f"[{color}]{bytes_val:.1f}{unit}[/{color}]"
            bytes_val /= 1024.0
        return f"[red]{bytes_val:.1f}PB[/red]"


class ProgressTracker:
    """Enhanced progress tracking with rich output"""
    
    def __init__(self, console: Console):
        self.console = console
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TextColumn("[cyan]{task.fields[status]}"),
            console=console,
            expand=True
        )
        self.tasks = {}
    
    def add_task(self, name: str, total: int, description: str = "") -> int:
        """Add a new progress task"""
        task_id = self.progress.add_task(
            description or name,
            total=total,
            status="Starting..."
        )
        self.tasks[name] = task_id
        return task_id
    
    def update(self, name: str, advance: int = 1, 
               status: Optional[str] = None, **kwargs):
        """Update progress task"""
        if name in self.tasks:
            task_id = self.tasks[name]
            if status:
                self.progress.update(task_id, status=status)
            self.progress.advance(task_id, advance)
            if kwargs:
                self.progress.update(task_id, **kwargs)
    
    def finish(self, name: str, status: str = "Complete"):
        """Mark task as finished"""
        if name in self.tasks:
            task_id = self.tasks[name]
            self.progress.update(task_id, status=f"[green]{status}[/green]")
    
    def __enter__(self):
        self.progress.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.progress.__exit__(exc_type, exc_val, exc_tb)


def create_status_panel(title: str, items: List[Tuple[str, Any, str]]) -> Panel:
    """Create a status panel with key-value pairs
    
    Args:
        title: Panel title
        items: List of (label, value, color) tuples
    """
    content = []
    for label, value, color in items:
        if color:
            content.append(f"[{color}]{label}:[/{color}] {value}")
        else:
            content.append(f"{label}: {value}")
    
    return Panel(
        "\n".join(content),
        title=f"[bold]{title}[/bold]",
        border_style="blue"
    )


def print_comparison_table(console: Console, 
                          data: List[Dict[str, Any]], 
                          key_field: str,
                          compare_fields: List[str],
                          title: str = "Comparison"):
    """Print a comparison table"""
    table = Table(
        title=title,
        show_header=True,
        header_style="bold magenta",
        box=box.ROUNDED
    )
    
    # Add key column
    table.add_column(key_field.title(), style="cyan", no_wrap=True)
    
    # Add comparison columns
    for field in compare_fields:
        table.add_column(field.title(), justify="center")
    
    # Add rows
    for item in data:
        row = [str(item.get(key_field, ''))]
        
        for field in compare_fields:
            value = item.get(field, '')
            
            # Apply conditional formatting
            if isinstance(value, bool):
                cell = "[green]✓[/green]" if value else "[red]✗[/red]"
            elif isinstance(value, (int, float)):
                if value > 0.8:
                    cell = f"[green]{value:.2f}[/green]"
                elif value > 0.5:
                    cell = f"[yellow]{value:.2f}[/yellow]"
                else:
                    cell = f"[red]{value:.2f}[/red]"
            else:
                cell = str(value)
            
            row.append(cell)
        
        table.add_row(*row)
    
    console.print(table)


def create_dashboard(stats: Dict[str, Any]) -> Layout:
    """Create a comprehensive dashboard layout"""
    layout = Layout()
    
    # Main split
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=3)
    )
    
    # Header
    layout["header"].update(
        Panel(
            Text("Flashcard Pipeline Dashboard", style="bold blue", justify="center"),
            box=box.DOUBLE
        )
    )
    
    # Main area - 2x2 grid
    layout["main"].split_row(
        Layout(name="left"),
        Layout(name="right")
    )
    
    layout["left"].split_column(
        Layout(name="top_left"),
        Layout(name="bottom_left")
    )
    
    layout["right"].split_column(
        Layout(name="top_right"),
        Layout(name="bottom_right")
    )
    
    # Populate panels
    layout["top_left"].update(
        create_status_panel(
            "Processing Stats",
            [
                ("Total Processed", stats.get('total', 0), "green"),
                ("Success Rate", f"{stats.get('success_rate', 0):.1%}", "yellow"),
                ("Cache Hits", stats.get('cache_hits', 0), "cyan"),
                ("API Calls", stats.get('api_calls', 0), "magenta")
            ]
        )
    )
    
    layout["top_right"].update(
        create_status_panel(
            "Performance",
            [
                ("Avg Response Time", f"{stats.get('avg_time', 0):.2f}s", "green"),
                ("P95 Latency", f"{stats.get('p95_latency', 0):.2f}s", "yellow"),
                ("Throughput", f"{stats.get('throughput', 0):.1f}/s", "cyan"),
                ("Queue Size", stats.get('queue_size', 0), "magenta")
            ]
        )
    )
    
    # Error summary
    error_content = []
    for category, count in stats.get('errors', {}).items():
        color = "red" if count > 10 else "yellow" if count > 0 else "green"
        error_content.append(f"[{color}]{category}: {count}[/{color}]")
    
    layout["bottom_left"].update(
        Panel(
            "\n".join(error_content) or "[green]No errors[/green]",
            title="[bold]Error Summary[/bold]",
            border_style="red" if stats.get('errors') else "green"
        )
    )
    
    # Recent activity
    activity = stats.get('recent_activity', [])
    activity_text = "\n".join([
        f"[dim]{item['time']}[/dim] {item['action']}"
        for item in activity[-5:]  # Last 5 items
    ])
    
    layout["bottom_right"].update(
        Panel(
            activity_text or "[dim]No recent activity[/dim]",
            title="[bold]Recent Activity[/bold]",
            border_style="blue"
        )
    )
    
    # Footer
    layout["footer"].update(
        Panel(
            f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            f"Uptime: {stats.get('uptime', 'N/A')}",
            style="dim",
            box=box.SIMPLE
        )
    )
    
    return layout