"""CLI error handling system"""

import sys
import json
import traceback
from typing import Optional, Dict, Any, Callable
from enum import Enum
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import logging

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Error categories with exit codes"""
    INPUT_ERROR = 1
    API_ERROR = 2
    PROCESSING_ERROR = 3
    SYSTEM_ERROR = 4
    CONFIGURATION_ERROR = 5
    PLUGIN_ERROR = 6
    NETWORK_ERROR = 7
    PERMISSION_ERROR = 8


class ErrorCode(Enum):
    """Specific error codes"""
    # Input errors (E001-E099)
    E001 = "Invalid file format"
    E002 = "Missing required fields"
    E003 = "Encoding error"
    E004 = "File not found"
    E005 = "Invalid arguments"
    
    # API errors (E100-E199)
    E101 = "Authentication failed"
    E102 = "Rate limit exceeded"
    E103 = "Model unavailable"
    E104 = "API timeout"
    E105 = "Invalid API response"
    
    # Processing errors (E200-E299)
    E201 = "Parsing failed"
    E202 = "Validation error"
    E203 = "Quality check failed"
    E204 = "Batch processing failed"
    E205 = "Resume failed"
    
    # System errors (E300-E399)
    E301 = "Database error"
    E302 = "File system error"
    E303 = "Memory error"
    E304 = "Permission denied"
    E305 = "Configuration error"
    
    # Plugin errors (E400-E499)
    E401 = "Plugin load failed"
    E402 = "Plugin execution error"
    E403 = "Plugin compatibility error"


class CLIError(Exception):
    """Base CLI error with structured information"""
    
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        category: ErrorCategory,
        details: Optional[str] = None,
        suggestion: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.code = code
        self.category = category
        self.details = details
        self.suggestion = suggestion
        self.context = context or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format"""
        return {
            "error": {
                "code": self.code.name,
                "category": self.category.name.lower(),
                "message": str(self),
                "details": self.details,
                "suggestion": self.suggestion,
                **self.context
            }
        }
    
    def to_json(self) -> str:
        """Convert error to JSON format"""
        return json.dumps(self.to_dict(), indent=2)
    
    @property
    def exit_code(self) -> int:
        """Get exit code for this error"""
        return self.category.value


class ErrorHandler:
    """Centralized error handling for the CLI"""
    
    def __init__(self, console: Optional[Console] = None, json_output: bool = False):
        self.console = console or Console()
        self.json_output = json_output
        self.error_hooks: Dict[ErrorCategory, Callable] = {}
        
    def register_hook(self, category: ErrorCategory, hook: Callable) -> None:
        """Register an error hook for a category"""
        self.error_hooks[category] = hook
        
    def handle(self, error: Exception) -> int:
        """Handle an error and return appropriate exit code"""
        if isinstance(error, CLIError):
            return self._handle_cli_error(error)
        elif isinstance(error, KeyboardInterrupt):
            return self._handle_interrupt()
        else:
            return self._handle_unexpected_error(error)
    
    def _handle_cli_error(self, error: CLIError) -> int:
        """Handle a structured CLI error"""
        # Call registered hook if any
        if error.category in self.error_hooks:
            try:
                self.error_hooks[error.category](error)
            except Exception as e:
                logger.error(f"Error hook failed: {e}")
        
        # Output error
        if self.json_output:
            print(error.to_json())
        else:
            self._display_error(error)
        
        # Log error
        logger.error(f"{error.code.name}: {error}", extra=error.context)
        
        return error.exit_code
    
    def _handle_interrupt(self) -> int:
        """Handle keyboard interrupt"""
        if not self.json_output:
            self.console.print("\n[yellow]Operation cancelled by user[/yellow]")
        return 130
    
    def _handle_unexpected_error(self, error: Exception) -> int:
        """Handle unexpected errors"""
        cli_error = CLIError(
            code=ErrorCode.E303,
            message="An unexpected error occurred",
            category=ErrorCategory.SYSTEM_ERROR,
            details=str(error),
            suggestion="Please check the logs or report this issue",
            context={
                "exception_type": type(error).__name__,
                "traceback": traceback.format_exc() if logger.isEnabledFor(logging.DEBUG) else None
            }
        )
        
        return self._handle_cli_error(cli_error)
    
    def _display_error(self, error: CLIError) -> None:
        """Display error in rich format"""
        # Create error panel
        error_text = Text()
        error_text.append(f"{error.code.name}: ", style="bold red")
        error_text.append(error.code.value, style="red")
        
        if error.details:
            error_text.append(f"\n\n{error.details}", style="dim")
        
        if error.suggestion:
            error_text.append("\n\n💡 ", style="yellow")
            error_text.append(error.suggestion, style="yellow")
        
        panel = Panel(
            error_text,
            title=f"[bold red]{error.category.name.replace('_', ' ').title()}[/bold red]",
            border_style="red",
            padding=(1, 2)
        )
        
        self.console.print(panel)
        
        # Show context in debug mode
        if logger.isEnabledFor(logging.DEBUG) and error.context:
            self.console.print("\n[dim]Debug context:[/dim]")
            for key, value in error.context.items():
                if value is not None:
                    self.console.print(f"  [dim]{key}:[/dim] {value}")


# Common error factories
def input_error(
    message: str,
    code: ErrorCode = ErrorCode.E005,
    **kwargs
) -> CLIError:
    """Create an input error"""
    return CLIError(
        code=code,
        message=message,
        category=ErrorCategory.INPUT_ERROR,
        **kwargs
    )


def api_error(
    message: str,
    code: ErrorCode = ErrorCode.E105,
    **kwargs
) -> CLIError:
    """Create an API error"""
    return CLIError(
        code=code,
        message=message,
        category=ErrorCategory.API_ERROR,
        **kwargs
    )


def processing_error(
    message: str,
    code: ErrorCode = ErrorCode.E204,
    **kwargs
) -> CLIError:
    """Create a processing error"""
    return CLIError(
        code=code,
        message=message,
        category=ErrorCategory.PROCESSING_ERROR,
        **kwargs
    )


def system_error(
    message: str,
    code: ErrorCode = ErrorCode.E303,
    **kwargs
) -> CLIError:
    """Create a system error"""
    return CLIError(
        code=code,
        message=message,
        category=ErrorCategory.SYSTEM_ERROR,
        **kwargs
    )