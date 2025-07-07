"""CLI utility functions"""

import json
import csv
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
import yaml


def format_output(
    data: Any,
    format: str = "table",
    console: Optional[Console] = None
) -> str:
    """Format data for output in various formats"""
    
    if format == "json":
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    elif format == "yaml":
        return yaml.dump(data, default_flow_style=False, allow_unicode=True)
    
    elif format == "csv":
        if isinstance(data, list) and data and isinstance(data[0], dict):
            output = []
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            return '\n'.join(output)
    
    elif format == "table" and console:
        if isinstance(data, list) and data and isinstance(data[0], dict):
            table = Table()
            
            # Add columns
            for key in data[0].keys():
                table.add_column(key.replace("_", " ").title())
            
            # Add rows
            for item in data:
                table.add_row(*[str(v) for v in item.values()])
            
            console.print(table)
            return ""
    
    # Default to string representation
    return str(data)


def validate_input(
    input_path: Path,
    expected_format: str = "csv",
    required_fields: Optional[List[str]] = None
) -> None:
    """Validate input file format and content"""
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    if expected_format == "csv":
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                first_row = next(reader, None)
                
                if not first_row:
                    raise ValueError("CSV file is empty")
                
                if required_fields:
                    missing = set(required_fields) - set(first_row.keys())
                    if missing:
                        raise ValueError(f"Missing required fields: {missing}")
                        
        except Exception as e:
            raise ValueError(f"Invalid CSV file: {e}")
    
    elif expected_format == "json":
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                if required_fields and isinstance(data, list) and data:
                    missing = set(required_fields) - set(data[0].keys())
                    if missing:
                        raise ValueError(f"Missing required fields: {missing}")
                        
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON file: {e}")


def parse_filter_expression(expr: str) -> Dict[str, Any]:
    """Parse a filter expression into a query dict"""
    # Simple implementation - could be expanded
    filters = {}
    
    # Parse key=value pairs
    for part in expr.split(","):
        if "=" in part:
            key, value = part.split("=", 1)
            filters[key.strip()] = value.strip()
        elif ">" in part:
            key, value = part.split(">", 1)
            filters[f"{key.strip()}__gt"] = float(value.strip())
        elif "<" in part:
            key, value = part.split("<", 1)
            filters[f"{key.strip()}__lt"] = float(value.strip())
    
    return filters


def display_code(
    code: str,
    language: str = "python",
    console: Optional[Console] = None
) -> None:
    """Display syntax-highlighted code"""
    if not console:
        console = Console()
    
    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
    console.print(syntax)


def confirm_action(
    message: str,
    default: bool = False,
    console: Optional[Console] = None
) -> bool:
    """Ask for user confirmation"""
    if not console:
        console = Console()
    
    if default:
        prompt = f"{message} [Y/n]: "
    else:
        prompt = f"{message} [y/N]: "
    
    response = console.input(prompt).lower().strip()
    
    if not response:
        return default
    
    return response in ['y', 'yes']


def truncate_text(text: str, max_length: int = 80, suffix: str = "...") -> str:
    """Truncate text to maximum length"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def format_size(size_bytes: int) -> str:
    """Format byte size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    
    return f"{size_bytes:.1f} PB"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def load_preset(preset_name: str, presets_dir: Path = Path("presets")) -> Dict[str, Any]:
    """Load a configuration preset"""
    preset_file = presets_dir / f"{preset_name}.yml"
    
    if not preset_file.exists():
        raise ValueError(f"Preset not found: {preset_name}")
    
    with open(preset_file, 'r') as f:
        return yaml.safe_load(f)


def create_progress_callback(progress, task):
    """Create a progress callback function"""
    def callback(current: int, total: int, message: str = ""):
        progress.update(task, completed=current, total=total, description=message)
    
    return callback