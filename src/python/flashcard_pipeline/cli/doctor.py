"""
System diagnostics and health check command
"""

import os
import sys
import subprocess
import sqlite3
import importlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import platform
import shutil

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box


console = Console()


class SystemDoctor:
    """Diagnose system configuration and health"""
    
    def __init__(self):
        self.checks = []
        self.warnings = []
        self.errors = []
    
    def run_diagnostics(self) -> Dict[str, any]:
        """Run all diagnostic checks"""
        results = {
            "python": self._check_python(),
            "dependencies": self._check_dependencies(),
            "database": self._check_database(),
            "api": self._check_api_config(),
            "cache": self._check_cache(),
            "disk_space": self._check_disk_space(),
            "permissions": self._check_permissions(),
            "configuration": self._check_configuration(),
        }
        
        return results
    
    def _check_python(self) -> Dict[str, any]:
        """Check Python version and environment"""
        result = {
            "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "executable": sys.executable,
            "platform": platform.platform(),
            "venv": hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix),
            "status": "ok"
        }
        
        # Check Python version
        if sys.version_info < (3, 8):
            result["status"] = "error"
            self.errors.append("Python 3.8 or higher is required")
        elif sys.version_info < (3, 9):
            result["status"] = "warning"
            self.warnings.append("Python 3.9+ recommended for best performance")
        
        return result
    
    def _check_dependencies(self) -> Dict[str, any]:
        """Check required dependencies"""
        required_packages = [
            ("httpx", "0.25.0"),
            ("pydantic", "2.0.0"),
            ("typer", "0.9.0"),
            ("rich", "13.0.0"),
            ("aiofiles", "23.0.0"),
            ("aiosqlite", "0.19.0"),
            ("python-dotenv", "1.0.0"),
            ("PyYAML", "6.0"),
        ]
        
        optional_packages = [
            ("genanki", "0.13.0", "Anki export"),
            ("watchdog", "2.0.0", "File watching"),
            ("schedule", "1.0.0", "Task scheduling"),
            ("psutil", "5.9.0", "System monitoring"),
        ]
        
        result = {
            "required": {},
            "optional": {},
            "missing": [],
            "outdated": [],
            "status": "ok"
        }
        
        # Check required packages
        for package, min_version, *_ in required_packages:
            try:
                module = importlib.import_module(package.replace("-", "_").lower())
                version = getattr(module, "__version__", "unknown")
                result["required"][package] = {
                    "installed": True,
                    "version": version,
                    "min_version": min_version
                }
            except ImportError:
                result["required"][package] = {
                    "installed": False,
                    "min_version": min_version
                }
                result["missing"].append(package)
                result["status"] = "error"
                self.errors.append(f"Required package '{package}' is not installed")
        
        # Check optional packages
        for package, min_version, purpose in optional_packages:
            try:
                module = importlib.import_module(package.replace("-", "_").lower())
                version = getattr(module, "__version__", "unknown")
                result["optional"][package] = {
                    "installed": True,
                    "version": version,
                    "purpose": purpose
                }
            except ImportError:
                result["optional"][package] = {
                    "installed": False,
                    "purpose": purpose
                }
                self.warnings.append(f"Optional package '{package}' not installed ({purpose})")
        
        return result
    
    def _check_database(self) -> Dict[str, any]:
        """Check database configuration and health"""
        db_path = os.getenv("DATABASE_PATH", "pipeline.db")
        result = {
            "path": db_path,
            "exists": os.path.exists(db_path),
            "size": 0,
            "tables": [],
            "integrity": "unknown",
            "status": "ok"
        }
        
        if result["exists"]:
            result["size"] = os.path.getsize(db_path)
            
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Check tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                result["tables"] = [row[0] for row in cursor.fetchall()]
                
                # Check integrity
                cursor.execute("PRAGMA integrity_check")
                integrity = cursor.fetchone()[0]
                result["integrity"] = "ok" if integrity == "ok" else integrity
                
                # Check for migrations
                if "schema_migrations" in result["tables"]:
                    cursor.execute("SELECT MAX(version) FROM schema_migrations")
                    result["latest_migration"] = cursor.fetchone()[0]
                
                conn.close()
                
                if result["integrity"] != "ok":
                    result["status"] = "error"
                    self.errors.append(f"Database integrity check failed: {result['integrity']}")
                
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)
                self.errors.append(f"Database error: {e}")
        else:
            result["status"] = "warning"
            self.warnings.append("Database file does not exist (will be created on first use)")
        
        return result
    
    def _check_api_config(self) -> Dict[str, any]:
        """Check API configuration"""
        result = {
            "api_key_set": bool(os.getenv("OPENROUTER_API_KEY")),
            "api_base": os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1"),
            "model": os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet"),
            "rate_limits": {
                "requests_per_minute": os.getenv("REQUESTS_PER_MINUTE", "600"),
                "requests_per_hour": os.getenv("REQUESTS_PER_HOUR", "36000"),
            },
            "status": "ok"
        }
        
        if not result["api_key_set"]:
            result["status"] = "error"
            self.errors.append("OPENROUTER_API_KEY environment variable not set")
        
        return result
    
    def _check_cache(self) -> Dict[str, any]:
        """Check cache directory and health"""
        cache_dir = os.getenv("CACHE_DIR", "cache")
        result = {
            "directory": cache_dir,
            "exists": os.path.exists(cache_dir),
            "writable": False,
            "size": 0,
            "file_count": 0,
            "status": "ok"
        }
        
        if result["exists"]:
            result["writable"] = os.access(cache_dir, os.W_OK)
            
            # Count cache files and size
            for root, dirs, files in os.walk(cache_dir):
                result["file_count"] += len(files)
                for file in files:
                    result["size"] += os.path.getsize(os.path.join(root, file))
            
            if not result["writable"]:
                result["status"] = "error"
                self.errors.append(f"Cache directory '{cache_dir}' is not writable")
        else:
            # Try to create cache directory
            try:
                os.makedirs(cache_dir, exist_ok=True)
                result["exists"] = True
                result["writable"] = True
                self.checks.append(f"Created cache directory: {cache_dir}")
            except Exception as e:
                result["status"] = "error"
                self.errors.append(f"Cannot create cache directory: {e}")
        
        return result
    
    def _check_disk_space(self) -> Dict[str, any]:
        """Check available disk space"""
        result = {
            "path": os.getcwd(),
            "total": 0,
            "used": 0,
            "free": 0,
            "percent": 0,
            "status": "ok"
        }
        
        try:
            stat = shutil.disk_usage(result["path"])
            result["total"] = stat.total
            result["used"] = stat.used
            result["free"] = stat.free
            result["percent"] = (stat.used / stat.total) * 100
            
            # Warning if less than 1GB free
            if result["free"] < 1_000_000_000:
                result["status"] = "warning"
                self.warnings.append(f"Low disk space: {result['free'] / 1_000_000_000:.1f}GB free")
            
            # Error if less than 100MB free
            if result["free"] < 100_000_000:
                result["status"] = "error"
                self.errors.append(f"Critical disk space: {result['free'] / 1_000_000:.0f}MB free")
                
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            self.errors.append(f"Cannot check disk space: {e}")
        
        return result
    
    def _check_permissions(self) -> Dict[str, any]:
        """Check file permissions"""
        paths_to_check = [
            (".", "Current directory"),
            ("data", "Data directory"),
            ("logs", "Logs directory"),
            ("cache", "Cache directory"),
            (".env", "Environment file"),
            ("pipeline.db", "Database file"),
        ]
        
        result = {
            "permissions": {},
            "status": "ok"
        }
        
        for path, description in paths_to_check:
            if os.path.exists(path):
                readable = os.access(path, os.R_OK)
                writable = os.access(path, os.W_OK)
                
                result["permissions"][path] = {
                    "description": description,
                    "exists": True,
                    "readable": readable,
                    "writable": writable
                }
                
                if not readable:
                    result["status"] = "error"
                    self.errors.append(f"{description} is not readable: {path}")
                elif not writable and not path.endswith(".env"):  # .env doesn't need to be writable
                    result["status"] = "warning"
                    self.warnings.append(f"{description} is not writable: {path}")
            else:
                result["permissions"][path] = {
                    "description": description,
                    "exists": False
                }
                
                # Only warn for optional paths
                if path in ["data", "logs", ".env"]:
                    self.checks.append(f"{description} does not exist: {path}")
        
        return result
    
    def _check_configuration(self) -> Dict[str, any]:
        """Check configuration files"""
        result = {
            "env_file": os.path.exists(".env"),
            "env_example": os.path.exists(".env.example"),
            "config_file": os.path.exists("config.yaml"),
            "settings": {},
            "status": "ok"
        }
        
        # Check important environment variables
        important_vars = [
            "OPENROUTER_API_KEY",
            "DATABASE_PATH",
            "CACHE_DIR",
            "LOG_LEVEL",
            "REQUESTS_PER_MINUTE",
        ]
        
        for var in important_vars:
            result["settings"][var] = {
                "set": bool(os.getenv(var)),
                "value": "***" if var == "OPENROUTER_API_KEY" and os.getenv(var) else os.getenv(var)
            }
        
        if not result["env_file"] and not result["config_file"]:
            result["status"] = "warning"
            self.warnings.append("No configuration file found (.env or config.yaml)")
            
            if result["env_example"]:
                self.checks.append("Copy .env.example to .env and configure it")
        
        return result
    
    def format_results(self, results: Dict[str, any]) -> None:
        """Format and display diagnostic results"""
        # Header
        console.print("\n[bold cyan]Korean Flashcard Pipeline - System Diagnostics[/bold cyan]\n")
        
        # Python Environment
        python = results["python"]
        panel_content = f"""
Python Version: {python['version']} [{python['status'].upper()}]
Executable: {python['executable']}
Virtual Env: {'Yes' if python['venv'] else 'No'}
Platform: {python['platform']}
        """
        console.print(Panel(panel_content.strip(), title="Python Environment", 
                          border_style="green" if python["status"] == "ok" else "yellow"))
        
        # Dependencies
        deps = results["dependencies"]
        table = Table(title="Dependencies", box=box.ROUNDED)
        table.add_column("Package", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Version", style="yellow")
        table.add_column("Notes", style="dim")
        
        for pkg, info in deps["required"].items():
            status = "✓" if info["installed"] else "✗"
            style = "green" if info["installed"] else "red"
            version = info.get("version", "-")
            notes = f"Required >= {info['min_version']}"
            table.add_row(pkg, f"[{style}]{status}[/{style}]", version, notes)
        
        for pkg, info in deps["optional"].items():
            status = "✓" if info["installed"] else "○"
            style = "green" if info["installed"] else "dim"
            version = info.get("version", "-")
            notes = info["purpose"]
            table.add_row(pkg, f"[{style}]{status}[/{style}]", version, f"[dim]{notes}[/dim]")
        
        console.print(table)
        
        # Database
        db = results["database"]
        if db["exists"]:
            db_info = f"""
Path: {db['path']}
Size: {db['size'] / 1024 / 1024:.2f} MB
Tables: {len(db['tables'])}
Integrity: {db['integrity']}
Latest Migration: {db.get('latest_migration', 'N/A')}
            """
        else:
            db_info = f"Database not yet created at: {db['path']}"
        
        console.print(Panel(db_info.strip(), title="Database", 
                          border_style="green" if db["status"] == "ok" else "yellow"))
        
        # API Configuration
        api = results["api"]
        api_info = f"""
API Key: {'✓ Set' if api['api_key_set'] else '✗ Not Set'}
API Base: {api['api_base']}
Model: {api['model']}
Rate Limit: {api['rate_limits']['requests_per_minute']} req/min
        """
        console.print(Panel(api_info.strip(), title="API Configuration",
                          border_style="green" if api["status"] == "ok" else "red"))
        
        # Summary
        total_errors = len(self.errors)
        total_warnings = len(self.warnings)
        total_checks = len(self.checks)
        
        summary_style = "green"
        summary_text = "All systems operational"
        
        if total_errors > 0:
            summary_style = "red"
            summary_text = f"{total_errors} error(s) found"
        elif total_warnings > 0:
            summary_style = "yellow"
            summary_text = f"{total_warnings} warning(s) found"
        
        console.print(f"\n[{summary_style}]● {summary_text}[/{summary_style}]")
        
        # Show errors
        if self.errors:
            console.print("\n[red]Errors:[/red]")
            for error in self.errors:
                console.print(f"  ✗ {error}")
        
        # Show warnings
        if self.warnings:
            console.print("\n[yellow]Warnings:[/yellow]")
            for warning in self.warnings:
                console.print(f"  ⚠ {warning}")
        
        # Show checks
        if self.checks:
            console.print("\n[dim]Notes:[/dim]")
            for check in self.checks:
                console.print(f"  ℹ {check}")
        
        # Recommendations
        if total_errors > 0:
            console.print("\n[bold]Recommended Actions:[/bold]")
            
            if not results["api"]["api_key_set"]:
                console.print("  1. Set OPENROUTER_API_KEY environment variable")
                console.print("     export OPENROUTER_API_KEY='your-api-key'")
            
            if results["dependencies"]["missing"]:
                console.print(f"  2. Install missing packages:")
                console.print(f"     pip install {' '.join(results['dependencies']['missing'])}")
            
            if not results["database"]["exists"]:
                console.print("  3. Initialize database:")
                console.print("     flashcard-pipeline db init")


def run_doctor():
    """Run system diagnostics"""
    doctor = SystemDoctor()
    results = doctor.run_diagnostics()
    doctor.format_results(results)
    
    # Return exit code based on errors
    if doctor.errors:
        return 1
    return 0