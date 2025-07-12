"""Unit tests for modern CLI implementation"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from click.testing import CliRunner

from flashcard_pipeline.cli.modern_cli import (
    cli, CLIContext, KeyValueParamType,
    format_duration, format_bytes, create_table
)
from flashcard_pipeline.cli.interactive import (
    InteractiveCLI, InteractiveProgress,
    interactive_command, print_boxed, print_tree
)
from flashcard_pipeline.cli.rich_output import (
    RichOutput, ProgressTracker,
    create_status_panel, create_dashboard
)


class TestCLIContext:
    """Test CLI context functionality"""
    
    @pytest.fixture
    def ctx(self):
        """Create test context"""
        return CLIContext()
    
    def test_context_initialization(self, ctx):
        """Test context initialization"""
        assert ctx.verbose is False
        assert ctx.debug is False
        assert ctx.output_format == "human"
        assert ctx.no_color is False
        assert ctx.telemetry_enabled is True
    
    @pytest.mark.asyncio
    async def test_component_initialization(self, ctx):
        """Test async component initialization"""
        ctx.db_path = ":memory:"
        ctx.api_key = "test-key"
        
        with patch('flashcard_pipeline.cli.modern_cli.init_telemetry'):
            await ctx.initialize_components()
        
        assert ctx.db_manager is not None
        assert ctx.cache_manager is not None
        assert ctx.api_client is not None
        assert ctx.error_collector is not None
    
    def test_context_echo_methods(self, ctx):
        """Test context echo methods"""
        # Test with color
        ctx.no_color = False
        ctx.echo("Test message")
        ctx.secho("Styled message", fg='red')
        ctx.success("Success message")
        ctx.error("Error message")
        ctx.warning("Warning message")
        ctx.info("Info message")
        
        # Test without color
        ctx.no_color = True
        ctx.echo("Test message")
        ctx.secho("Styled message", fg='red')
    
    def test_format_output(self, ctx):
        """Test output formatting"""
        data = {"key": "value", "number": 42}
        
        # Human format
        ctx.output_format = "human"
        assert ctx.format_output(data) == str(data)
        
        # JSON format
        ctx.output_format = "json"
        output = ctx.format_output(data)
        assert json.loads(output) == data
        
        # YAML format
        ctx.output_format = "yaml"
        output = ctx.format_output(data)
        assert "key: value" in output


class TestCLICommands:
    """Test CLI commands"""
    
    @pytest.fixture
    def runner(self):
        """Create CLI test runner"""
        return CliRunner()
    
    def test_cli_help(self, runner):
        """Test CLI help output"""
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert "Flashcard Pipeline CLI" in result.output
        assert "process" in result.output
        assert "cache" in result.output
        assert "monitor" in result.output
    
    def test_version_option(self, runner):
        """Test version display"""
        result = runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert "2.0.0" in result.output
    
    @patch('flashcard_pipeline.cli.modern_cli.asyncio.run')
    def test_process_single_command(self, mock_run, runner):
        """Test process single command"""
        result = runner.invoke(cli, ['process', 'single', '안녕하세요'])
        assert result.exit_code == 0
        mock_run.assert_called_once()
    
    @patch('flashcard_pipeline.cli.modern_cli.asyncio.run')
    def test_process_batch_command(self, mock_run, runner):
        """Test process batch command"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("word\n안녕하세요\n감사합니다\n")
            temp_file = f.name
        
        try:
            result = runner.invoke(cli, ['process', 'batch', temp_file])
            assert result.exit_code == 0
            mock_run.assert_called_once()
        finally:
            Path(temp_file).unlink()
    
    @patch('flashcard_pipeline.cli.modern_cli.asyncio.run')
    def test_cache_stats_command(self, mock_run, runner):
        """Test cache stats command"""
        result = runner.invoke(cli, ['cache', 'stats'])
        assert result.exit_code == 0
        mock_run.assert_called_once()
    
    def test_cache_clear_command(self, runner):
        """Test cache clear command"""
        # Should ask for confirmation
        result = runner.invoke(cli, ['cache', 'clear'], input='n\n')
        assert result.exit_code == 1  # Aborted
    
    def test_config_show_command(self, runner):
        """Test config show command"""
        result = runner.invoke(cli, ['config', 'show'])
        assert result.exit_code == 0
        assert "Current Configuration" in result.output
    
    def test_config_set_command(self, runner):
        """Test config set command"""
        result = runner.invoke(cli, ['config', 'set', 'output', 'json'])
        assert result.exit_code == 0
        assert "Set output = json" in result.output


class TestKeyValueParamType:
    """Test custom parameter type"""
    
    def test_key_value_parsing(self):
        """Test key=value parsing"""
        param_type = KeyValueParamType()
        
        # Valid input
        result = param_type.convert("key=value", None, None)
        assert result == ("key", "value")
        
        # With spaces
        result = param_type.convert(" key = value ", None, None)
        assert result == ("key", "value")
        
        # With equals in value
        result = param_type.convert("key=value=with=equals", None, None)
        assert result == ("key", "value=with=equals")
    
    def test_invalid_key_value(self):
        """Test invalid key=value input"""
        param_type = KeyValueParamType()
        
        with pytest.raises(Exception):
            param_type.convert("invalid", None, None)


class TestHelperFunctions:
    """Test helper functions"""
    
    def test_format_duration(self):
        """Test duration formatting"""
        assert format_duration(0.5) == "500ms"
        assert format_duration(30) == "30.0s"
        assert format_duration(90) == "1.5m"
        assert format_duration(3700) == "1.0h"
    
    def test_format_bytes(self):
        """Test bytes formatting"""
        assert format_bytes(512) == "512.0B"
        assert format_bytes(1536) == "1.5KB"
        assert format_bytes(1024 * 1024 * 2.5) == "2.5MB"
        assert format_bytes(1024 ** 3 * 1.5) == "1.5GB"
    
    def test_create_table(self):
        """Test table creation"""
        headers = ["Name", "Value"]
        rows = [["Item1", "10"], ["Item2", "20"]]
        
        table = create_table(headers, rows)
        assert "Name" in table
        assert "Value" in table
        assert "Item1" in table
        assert "10" in table


class TestInteractiveCLI:
    """Test interactive CLI features"""
    
    @patch('questionary.password')
    @patch('questionary.select')
    @patch('questionary.path')
    @patch('questionary.confirm')
    @patch('questionary.text')
    def test_guided_setup(self, mock_text, mock_confirm, mock_path, 
                         mock_select, mock_password):
        """Test guided setup wizard"""
        # Mock responses
        mock_password.return_value.ask.return_value = "test-api-key"
        mock_select.return_value.ask.return_value = "claude-3-haiku"
        mock_path.return_value.ask.return_value = "test.db"
        mock_confirm.return_value.ask.side_effect = [True, True, True, True]
        mock_text.return_value.ask.return_value = ""
        
        config = InteractiveCLI.guided_setup()
        
        assert config is not None
        assert config['api_key'] == "test-api-key"
        assert config['model'] == "claude-3-haiku"
        assert config['db_path'] == "test.db"
    
    @patch('questionary.checkbox')
    def test_select_words_interactive(self, mock_checkbox):
        """Test interactive word selection"""
        words = ["word1", "word2", "word3"]
        mock_checkbox.return_value.ask.return_value = ["word1", "word3"]
        
        selected = InteractiveCLI.select_words_interactive(words)
        
        assert selected == ["word1", "word3"]
        mock_checkbox.assert_called_once()
    
    def test_interactive_progress(self):
        """Test interactive progress tracker"""
        with InteractiveProgress(100, "Testing") as progress:
            progress.update(10)
            progress.update(20, error="Some error")
            progress.set_description("Updated description")
            
            assert progress.current == 30
            assert len(progress.errors) == 1


class TestRichOutput:
    """Test rich output formatting"""
    
    @pytest.fixture
    def rich_output(self):
        """Create rich output instance"""
        return RichOutput(no_color=True)
    
    def test_print_flashcard(self, rich_output):
        """Test flashcard printing"""
        flashcard = {
            "word": "안녕하세요",
            "translation": "Hello",
            "pronunciation": "annyeonghaseyo",
            "difficulty": 3,
            "definition": "A greeting",
            "examples": ["Example 1", "Example 2"]
        }
        
        # Should not raise
        rich_output.print_flashcard(flashcard, detailed=True)
        rich_output.print_flashcard(flashcard, detailed=False)
    
    def test_print_flashcard_table(self, rich_output):
        """Test flashcard table printing"""
        flashcards = [
            {"word": "word1", "translation": "trans1", "difficulty": 2},
            {"word": "word2", "translation": "trans2", "difficulty": 3}
        ]
        
        # Should not raise
        rich_output.print_flashcard_table(flashcards)
    
    def test_print_error_table(self, rich_output):
        """Test error table printing"""
        errors = [
            {"type": "NetworkError", "message": "Connection failed", "timestamp": 1234567890},
            {"type": "ValidationError", "message": "Invalid input", "timestamp": 1234567891}
        ]
        
        # Should not raise
        rich_output.print_error_table(errors)
        rich_output.print_error_table([])  # Empty list
    
    def test_format_helpers(self, rich_output):
        """Test formatting helpers"""
        assert "[green]" in rich_output.format_duration(0.5)
        assert "[yellow]" in rich_output.format_duration(30)
        assert "[red]" in rich_output.format_duration(120)
        
        assert "[green]" in rich_output.format_size(100)
        assert "[yellow]" in rich_output.format_size(1024 * 1024 * 100)
        assert "[red]" in rich_output.format_size(1024 ** 3 * 100)


class TestProgressTracker:
    """Test progress tracker"""
    
    def test_progress_tracker(self):
        """Test progress tracking functionality"""
        console = MagicMock()
        
        with ProgressTracker(console) as tracker:
            # Add tasks
            task1 = tracker.add_task("Task 1", 100, "Processing")
            assert "Task 1" in tracker.tasks
            
            # Update progress
            tracker.update("Task 1", advance=10, status="Working")
            
            # Finish task
            tracker.finish("Task 1", "Done")


class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_print_boxed(self, capsys):
        """Test boxed text printing"""
        print_boxed("Test Message", color='blue', width=30)
        captured = capsys.readouterr()
        assert "Test Message" in captured.out
        assert "+" in captured.out
        assert "-" in captured.out
    
    def test_print_tree(self, capsys):
        """Test tree printing"""
        data = {
            "root": {
                "child1": "value1",
                "child2": ["item1", "item2"],
                "child3": {"nested": "value"}
            }
        }
        
        print_tree(data)
        captured = capsys.readouterr()
        assert "root" in captured.out
        assert "child1" in captured.out
        assert "value1" in captured.out
    
    def test_create_status_panel(self):
        """Test status panel creation"""
        items = [
            ("Status", "Active", "green"),
            ("Count", 42, "yellow"),
            ("Rate", "95%", None)
        ]
        
        panel = create_status_panel("Test Panel", items)
        assert panel is not None


class TestShellCompletion:
    """Test shell completion setup"""
    
    @patch.dict('os.environ', {'SHELL': '/bin/bash'})
    def test_bash_completion(self):
        """Test bash completion script"""
        from flashcard_pipeline.cli.modern_cli import setup_shell_completion
        
        script = setup_shell_completion()
        assert script is not None
        assert "_flashcard_completion" in script
        assert "COMP_WORDS" in script
    
    @patch.dict('os.environ', {'SHELL': '/bin/zsh'})
    def test_zsh_completion(self):
        """Test zsh completion script"""
        from flashcard_pipeline.cli.modern_cli import setup_shell_completion
        
        script = setup_shell_completion()
        assert script is not None
        assert "_flashcard_completion" in script
        assert "compdef" in script
    
    @patch.dict('os.environ', {'SHELL': '/bin/fish'})
    def test_fish_completion(self):
        """Test fish completion script"""
        from flashcard_pipeline.cli.modern_cli import setup_shell_completion
        
        script = setup_shell_completion()
        assert script is not None
        assert "_flashcard_completion" in script
        assert "commandline" in script


class TestInteractiveDecorator:
    """Test interactive command decorator"""
    
    def test_interactive_decorator(self):
        """Test interactive command decorator behavior"""
        @interactive_command
        def test_command(required_arg, optional_arg=None):
            return f"{required_arg},{optional_arg}"
        
        # With all args provided
        result = test_command(required_arg="test", optional_arg="opt")
        assert result == "test,opt"
        
        # Note: Testing interactive prompts requires more complex mocking
        # of stdin/questionary which is beyond basic unit tests