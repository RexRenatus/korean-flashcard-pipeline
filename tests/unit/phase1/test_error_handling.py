"""Phase 1: Error Handling Tests

Tests for structured error handling, error recovery mechanisms, and user-friendly error messages.
"""

import pytest
import json
import sys
from unittest.mock import Mock, patch
from rich.console import Console

from flashcard_pipeline.cli.errors import (
    CLIError, ErrorCode, ErrorCategory, ErrorHandler,
    input_error, api_error, processing_error, system_error
)


class TestStructuredErrors:
    """Test CLIError system and error categorization"""
    
    def test_error_code_enum_values(self):
        """Test error codes have correct values"""
        # Input errors (E001-E099)
        assert ErrorCode.E001.value == "Invalid file format"
        assert ErrorCode.E002.value == "Missing required fields"
        assert ErrorCode.E003.value == "Encoding error"
        assert ErrorCode.E004.value == "File not found"
        assert ErrorCode.E005.value == "Invalid arguments"
        
        # API errors (E100-E199)
        assert ErrorCode.E101.value == "Authentication failed"
        assert ErrorCode.E102.value == "Rate limit exceeded"
        assert ErrorCode.E103.value == "Model unavailable"
        assert ErrorCode.E104.value == "API timeout"
        assert ErrorCode.E105.value == "Invalid API response"
        
        # Processing errors (E200-E299)
        assert ErrorCode.E201.value == "Parsing failed"
        assert ErrorCode.E202.value == "Validation error"
        assert ErrorCode.E203.value == "Quality check failed"
        assert ErrorCode.E204.value == "Batch processing failed"
        assert ErrorCode.E205.value == "Resume failed"
        
        # System errors (E300-E399)
        assert ErrorCode.E301.value == "Database error"
        assert ErrorCode.E302.value == "File system error"
        assert ErrorCode.E303.value == "Memory error"
        assert ErrorCode.E304.value == "Permission denied"
        assert ErrorCode.E305.value == "Configuration error"
    
    def test_error_categories_meaningful(self):
        """Test error categories provide context"""
        categories = [
            (ErrorCategory.INPUT_ERROR, 1),
            (ErrorCategory.API_ERROR, 2),
            (ErrorCategory.PROCESSING_ERROR, 3),
            (ErrorCategory.SYSTEM_ERROR, 4),
            (ErrorCategory.CONFIGURATION_ERROR, 5),
            (ErrorCategory.PLUGIN_ERROR, 6),
            (ErrorCategory.NETWORK_ERROR, 7),
            (ErrorCategory.PERMISSION_ERROR, 8)
        ]
        
        for category, exit_code in categories:
            assert category.value == exit_code
    
    def test_cli_error_creation(self):
        """Test creating CLIError with all attributes"""
        error = CLIError(
            code=ErrorCode.E001,
            message="Test error message",
            category=ErrorCategory.INPUT_ERROR,
            details="File 'test.csv' has invalid format",
            suggestion="Check that the file is properly formatted CSV",
            context={"file": "test.csv", "line": 42}
        )
        
        assert error.code == ErrorCode.E001
        assert str(error) == "Test error message"
        assert error.category == ErrorCategory.INPUT_ERROR
        assert error.details == "File 'test.csv' has invalid format"
        assert error.suggestion == "Check that the file is properly formatted CSV"
        assert error.context["file"] == "test.csv"
        assert error.exit_code == 1
    
    def test_error_to_dict_format(self):
        """Test converting error to dictionary format"""
        error = CLIError(
            code=ErrorCode.E101,
            message="API authentication failed",
            category=ErrorCategory.API_ERROR,
            details="Invalid API key provided",
            suggestion="Check your OPENROUTER_API_KEY environment variable",
            context={"status_code": 401}
        )
        
        error_dict = error.to_dict()
        
        assert error_dict["error"]["code"] == "E101"
        assert error_dict["error"]["category"] == "api_error"
        assert error_dict["error"]["message"] == "API authentication failed"
        assert error_dict["error"]["details"] == "Invalid API key provided"
        assert error_dict["error"]["suggestion"] == "Check your OPENROUTER_API_KEY environment variable"
        assert error_dict["error"]["status_code"] == 401
    
    def test_error_to_json_format(self):
        """Test JSON output format for errors"""
        error = CLIError(
            code=ErrorCode.E202,
            message="Validation failed",
            category=ErrorCategory.PROCESSING_ERROR,
            details="Term field is empty",
            suggestion="Ensure all vocabulary items have a term"
        )
        
        json_output = error.to_json()
        data = json.loads(json_output)
        
        assert data["error"]["code"] == "E202"
        assert data["error"]["category"] == "processing_error"
        assert data["error"]["message"] == "Validation failed"
        assert data["error"]["details"] == "Term field is empty"


class TestErrorFactories:
    """Test error factory functions"""
    
    def test_input_error_factory(self):
        """Test input_error factory function"""
        error = input_error(
            message="Invalid CSV format",
            code=ErrorCode.E001,
            details="Missing 'term' column",
            suggestion="Add a 'term' column to your CSV file"
        )
        
        assert error.category == ErrorCategory.INPUT_ERROR
        assert error.code == ErrorCode.E001
        assert str(error) == "Invalid CSV format"
        assert error.exit_code == 1
    
    def test_api_error_factory(self):
        """Test api_error factory function"""
        error = api_error(
            message="Rate limit exceeded",
            code=ErrorCode.E102,
            details="600 requests per minute limit reached",
            suggestion="Wait 60 seconds before retrying",
            context={"retry_after": 60}
        )
        
        assert error.category == ErrorCategory.API_ERROR
        assert error.code == ErrorCode.E102
        assert error.context["retry_after"] == 60
        assert error.exit_code == 2
    
    def test_processing_error_factory(self):
        """Test processing_error factory function"""
        error = processing_error(
            message="Batch processing failed",
            code=ErrorCode.E204,
            details="5 out of 100 items failed",
            suggestion="Check the error log for details"
        )
        
        assert error.category == ErrorCategory.PROCESSING_ERROR
        assert error.code == ErrorCode.E204
        assert error.exit_code == 3
    
    def test_system_error_factory(self):
        """Test system_error factory function"""
        error = system_error(
            message="Database connection failed",
            code=ErrorCode.E301,
            details="Cannot connect to SQLite database",
            suggestion="Check database file permissions"
        )
        
        assert error.category == ErrorCategory.SYSTEM_ERROR
        assert error.code == ErrorCode.E301
        assert error.exit_code == 4


class TestErrorHandler:
    """Test ErrorHandler for CLI error display"""
    
    def test_error_handler_initialization(self):
        """Test ErrorHandler initialization"""
        console = Console()
        handler = ErrorHandler(console=console, json_output=False)
        
        assert handler.console == console
        assert handler.json_output == False
        assert handler.error_hooks == {}
    
    def test_error_handler_cli_error(self, capsys):
        """Test handling CLIError"""
        handler = ErrorHandler(json_output=True)
        
        error = CLIError(
            code=ErrorCode.E001,
            message="Test error",
            category=ErrorCategory.INPUT_ERROR
        )
        
        exit_code = handler.handle(error)
        
        assert exit_code == 1
        
        # Check JSON output
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["error"]["code"] == "E001"
    
    def test_error_handler_keyboard_interrupt(self):
        """Test handling KeyboardInterrupt"""
        handler = ErrorHandler(json_output=False)
        
        with patch.object(handler.console, 'print') as mock_print:
            exit_code = handler.handle(KeyboardInterrupt())
            
            assert exit_code == 130
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert "cancelled" in call_args.lower()
    
    def test_error_handler_unexpected_error(self):
        """Test handling unexpected exceptions"""
        handler = ErrorHandler(json_output=False)
        
        with patch.object(handler, '_handle_cli_error') as mock_handle:
            error = ValueError("Unexpected error")
            handler.handle(error)
            
            # Should convert to CLIError
            mock_handle.assert_called_once()
            cli_error = mock_handle.call_args[0][0]
            assert isinstance(cli_error, CLIError)
            assert cli_error.code == ErrorCode.E303
            assert "Unexpected error" in cli_error.details
    
    def test_error_handler_hooks(self):
        """Test error handler hooks"""
        handler = ErrorHandler()
        
        # Register a hook
        hook_called = False
        def test_hook(error):
            nonlocal hook_called
            hook_called = True
        
        handler.register_hook(ErrorCategory.API_ERROR, test_hook)
        
        # Create an API error
        error = api_error("Test", code=ErrorCode.E101)
        
        with patch.object(handler, '_display_error'):
            handler.handle(error)
        
        assert hook_called
    
    def test_error_display_format(self):
        """Test error display formatting"""
        console = Console(force_terminal=True, width=80)
        handler = ErrorHandler(console=console, json_output=False)
        
        error = CLIError(
            code=ErrorCode.E001,
            message="File not found",
            category=ErrorCategory.INPUT_ERROR,
            details="The file 'vocab.csv' does not exist",
            suggestion="Check the file path and try again"
        )
        
        with patch.object(console, 'print') as mock_print:
            handler._display_error(error)
            
            # Should create a panel with error info
            mock_print.assert_called_once()
            panel = mock_print.call_args[0][0]
            # Panel content would be complex Rich formatting


class TestSpecificErrorScenarios:
    """Test specific error scenarios and handling"""
    
    def test_file_not_found_error(self):
        """Test file not found error scenario"""
        error = input_error(
            message="File not found",
            code=ErrorCode.E004,
            details="Cannot find file: vocab.csv",
            suggestion="Check if the file exists in the current directory",
            context={"filename": "vocab.csv", "cwd": "/home/user"}
        )
        
        assert error.code == ErrorCode.E004
        assert "vocab.csv" in error.details
        assert "current directory" in error.suggestion
        assert error.context["filename"] == "vocab.csv"
    
    def test_api_authentication_error(self):
        """Test API authentication error scenario"""
        error = api_error(
            message="Authentication failed",
            code=ErrorCode.E101,
            details="Invalid or missing API key",
            suggestion="Set the OPENROUTER_API_KEY environment variable",
            context={"status": 401, "endpoint": "/chat/completions"}
        )
        
        assert error.code == ErrorCode.E101
        assert error.context["status"] == 401
        assert "OPENROUTER_API_KEY" in error.suggestion
    
    def test_rate_limit_error(self):
        """Test rate limit exceeded error"""
        error = api_error(
            message="Rate limit exceeded",
            code=ErrorCode.E102,
            details="You have exceeded the rate limit of 600 requests per minute",
            suggestion="Wait 60 seconds before retrying",
            context={
                "limit": 600,
                "remaining": 0,
                "retry_after": 60
            }
        )
        
        assert error.code == ErrorCode.E102
        assert error.context["retry_after"] == 60
        assert "600 requests" in error.details
    
    def test_validation_error(self):
        """Test validation error scenario"""
        error = processing_error(
            message="Validation error",
            code=ErrorCode.E202,
            details="Invalid term at position 5: empty string",
            suggestion="Ensure all vocabulary items have non-empty terms",
            context={
                "position": 5,
                "field": "term",
                "value": ""
            }
        )
        
        assert error.code == ErrorCode.E202
        assert error.context["position"] == 5
        assert "empty string" in error.details
    
    def test_database_error(self):
        """Test database error scenario"""
        error = system_error(
            message="Database error",
            code=ErrorCode.E301,
            details="Cannot write to database: disk full",
            suggestion="Free up disk space and try again",
            context={"operation": "insert", "table": "vocabulary_items"}
        )
        
        assert error.code == ErrorCode.E301
        assert "disk full" in error.details
        assert error.context["table"] == "vocabulary_items"
    
    def test_configuration_error(self):
        """Test configuration error scenario"""
        error = CLIError(
            code=ErrorCode.E305,
            message="Configuration error",
            category=ErrorCategory.CONFIGURATION_ERROR,
            details="Invalid configuration: negative timeout value",
            suggestion="Check your configuration file for errors",
            context={"field": "api.timeout", "value": -1}
        )
        
        assert error.code == ErrorCode.E305
        assert error.exit_code == 5
        assert error.context["value"] == -1


class TestErrorAggregation:
    """Test error aggregation for batch processing"""
    
    def test_batch_error_collection(self):
        """Test collecting errors during batch processing"""
        errors = []
        
        # Simulate processing 10 items with some failures
        for i in range(10):
            if i % 3 == 0:  # Fail every 3rd item
                error = processing_error(
                    message=f"Failed to process item {i}",
                    code=ErrorCode.E202,
                    context={"position": i}
                )
                errors.append(error)
        
        assert len(errors) == 4  # Items 0, 3, 6, 9
        assert all(e.code == ErrorCode.E202 for e in errors)
        assert errors[0].context["position"] == 0
        assert errors[1].context["position"] == 3
    
    def test_error_summary_generation(self):
        """Test generating summary for multiple errors"""
        error_counts = {
            ErrorCode.E202: 5,  # Validation errors
            ErrorCode.E101: 2,  # API errors
            ErrorCode.E301: 1   # Database error
        }
        
        total_errors = sum(error_counts.values())
        
        # Create summary message
        summary_parts = []
        for code, count in error_counts.items():
            summary_parts.append(f"{count} × {code.name}: {code.value}")
        
        summary = f"Batch completed with {total_errors} errors:\n" + "\n".join(summary_parts)
        
        assert "8 errors" in summary
        assert "5 × E202" in summary
        assert "Validation error" in summary