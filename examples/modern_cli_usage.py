"""Examples of using the modern CLI features"""

import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta

# Example 1: Basic CLI Usage
print("=" * 60)
print("Example 1: Basic CLI Commands")
print("=" * 60)

# Single word processing
print("\n# Process a single word:")
print('flashcard process single "안녕하세요"')
print('flashcard process single "어렵다" --context "studying Korean"')

# Batch processing
print("\n# Process batch from file:")
print("flashcard process batch words.csv")
print("flashcard process batch words.txt --output results.json --batch-size 20")

# Cache management
print("\n# Cache operations:")
print("flashcard cache stats")
print("flashcard cache clear --tier l1")

# Database operations
print("\n# Database operations:")
print("flashcard db migrate")
print("flashcard db stats")

# Monitoring
print("\n# Monitoring commands:")
print("flashcard monitor errors --last 1h")
print("flashcard monitor health")

# Configuration
print("\n# Configuration:")
print("flashcard config show")
print("flashcard config set api_key YOUR_KEY")
print("flashcard config validate")


# Example 2: Using Interactive Features
print("\n\n" + "=" * 60)
print("Example 2: Interactive Features")
print("=" * 60)

from flashcard_pipeline.cli.interactive import InteractiveCLI

# Guided setup
print("\n# Interactive setup wizard:")
print("config = InteractiveCLI.guided_setup()")

# Word selection
print("\n# Interactive word selection:")
words = ["안녕하세요", "감사합니다", "미안합니다", "사랑해요", "잘자요"]
print(f"words = {words}")
print("selected = InteractiveCLI.select_words_interactive(words)")

# Batch processing wizard
print("\n# Batch processing configuration:")
print("options = InteractiveCLI.batch_processing_wizard()")

# Error investigation
print("\n# Error investigation wizard:")
errors = [
    {"type": "NetworkError", "message": "Connection timeout", "timestamp": datetime.now()},
    {"type": "RateLimitError", "message": "API limit exceeded", "timestamp": datetime.now()},
]
print("result = InteractiveCLI.error_investigation_wizard(errors)")

# Confirm destructive action
print("\n# Confirm destructive actions:")
print('confirmed = InteractiveCLI.confirm_destructive_action("Clear all cache")')


# Example 3: Rich Output Formatting
print("\n\n" + "=" * 60)
print("Example 3: Rich Output")
print("=" * 60)

from flashcard_pipeline.cli.rich_output import RichOutput, ProgressTracker

# Initialize rich output
rich = RichOutput()

# Print flashcard
print("\n# Display flashcard:")
flashcard = {
    "word": "안녕하세요",
    "translation": "Hello",
    "pronunciation": "annyeonghaseyo",
    "difficulty": 2,
    "definition": "A polite greeting used in Korean",
    "examples": [
        "안녕하세요, 저는 김민수입니다.",
        "아침에 선생님께 안녕하세요라고 인사했어요."
    ],
    "mnemonics": "An (안) young (녕) person says hello (하세요)"
}
print("rich.print_flashcard(flashcard, detailed=True)")

# Print flashcard table
print("\n# Display flashcard table:")
flashcards = [
    {"word": "안녕하세요", "translation": "Hello", "pronunciation": "annyeonghaseyo", "difficulty": 2, "status": "success"},
    {"word": "감사합니다", "translation": "Thank you", "pronunciation": "gamsahamnida", "difficulty": 2, "status": "success"},
    {"word": "미안합니다", "translation": "Sorry", "pronunciation": "mianhamnida", "difficulty": 3, "status": "success"},
]
print("rich.print_flashcard_table(flashcards)")

# Print statistics
print("\n# Display statistics dashboard:")
stats = {
    "performance": {
        "total": 1000,
        "success_rate": 0.95,
        "avg_time": 1.2,
        "cache_hit_rate": 0.78
    },
    "errors": {
        "NetworkError": 15,
        "RateLimitError": 5,
        "ValidationError": 30
    }
}
print("rich.print_statistics(stats)")


# Example 4: Progress Tracking
print("\n\n" + "=" * 60)
print("Example 4: Progress Tracking")
print("=" * 60)

print("\n# Using progress tracker:")
print("""
with ProgressTracker(rich.console) as tracker:
    # Add multiple tasks
    task1 = tracker.add_task("Processing words", total=100)
    task2 = tracker.add_task("Updating cache", total=50)
    
    # Update progress
    for i in range(100):
        tracker.update("Processing words", status=f"Word {i+1}/100")
        if i % 2 == 0:
            tracker.update("Updating cache", advance=1)
        time.sleep(0.01)
    
    # Finish tasks
    tracker.finish("Processing words")
    tracker.finish("Updating cache")
""")


# Example 5: Advanced CLI Patterns
print("\n\n" + "=" * 60)
print("Example 5: Advanced CLI Patterns")
print("=" * 60)

# Pipeline commands
print("\n# Pipeline multiple operations:")
print("flashcard process batch input.csv | flashcard monitor errors --real-time")

# Output formats
print("\n# Different output formats:")
print("flashcard process single '사랑' --output json | jq '.translation'")
print("flashcard cache stats --output yaml > cache_report.yaml")

# Environment variables
print("\n# Using environment variables:")
print("export FLASHCARD_DB=/path/to/custom.db")
print("export OPENROUTER_API_KEY=your-key")
print("flashcard process batch words.csv")

# Config file
print("\n# Using config file:")
print("flashcard --config production.yaml process batch large_dataset.csv")

# Verbose and debug modes
print("\n# Debug and verbose output:")
print("flashcard --verbose process single '어렵다'")
print("flashcard --debug monitor errors --last 24h")


# Example 6: Custom Scripts Using CLI Components
print("\n\n" + "=" * 60)
print("Example 6: Custom Scripts")
print("=" * 60)

print("\n# Custom script using CLI components:")
print("""
#!/usr/bin/env python
'''Custom flashcard processing script'''

import asyncio
from flashcard_pipeline.cli.modern_cli import CLIContext
from flashcard_pipeline.cli.interactive import InteractiveCLI
from flashcard_pipeline.cli.rich_output import RichOutput, ProgressTracker

async def custom_batch_processor():
    # Initialize CLI context
    ctx = CLIContext()
    ctx.api_key = "your-api-key"
    ctx.db_path = "flashcards.db"
    
    await ctx.initialize_components()
    
    # Get input file interactively
    options = InteractiveCLI.batch_processing_wizard()
    
    # Set up rich output
    rich = RichOutput()
    
    # Process with progress tracking
    with ProgressTracker(rich.console) as tracker:
        task = tracker.add_task("Processing", total=len(words))
        
        for word in words:
            try:
                # Process word
                result = await ctx.api_client.process_complete(word)
                
                # Display result
                rich.print_flashcard(result)
                
                # Update progress
                tracker.update("Processing", status=f"Completed: {word}")
                
            except Exception as e:
                tracker.update("Processing", status=f"Error: {word}")
    
    # Cleanup
    await ctx.cleanup()

if __name__ == "__main__":
    asyncio.run(custom_batch_processor())
""")


# Example 7: Shell Completion
print("\n\n" + "=" * 60)
print("Example 7: Shell Completion Setup")
print("=" * 60)

print("\n# Install shell completion:")
print("# For bash:")
print("flashcard --install-completion bash")
print("source ~/.bashrc")

print("\n# For zsh:")
print("flashcard --install-completion zsh")
print("source ~/.zshrc")

print("\n# For fish:")
print("flashcard --install-completion fish")

print("\n# Usage after installation:")
print("flashcard proc<TAB>  # Autocompletes to 'process'")
print("flashcard process s<TAB>  # Shows 'single' option")
print("flashcard monitor --<TAB>  # Shows all options")


# Example 8: Plugin System
print("\n\n" + "=" * 60)
print("Example 8: Plugin System")
print("=" * 60)

print("\n# Create a custom plugin:")
print("""
# ~/.flashcard/plugins/custom_export.py
import click
from flashcard_pipeline.cli.modern_cli import cli

@cli.command()
@click.option('--format', type=click.Choice(['anki', 'quizlet']), default='anki')
@click.argument('output_file')
def export(format, output_file):
    '''Export flashcards to external formats'''
    # Implementation here
    pass

# Register plugin in ~/.flashcard/config.yaml
plugins:
  - custom_export
""")

print("\n# Use the plugin:")
print("flashcard export --format anki my_cards.apkg")


# Example 9: Live Monitoring
print("\n\n" + "=" * 60)
print("Example 9: Live Monitoring")
print("=" * 60)

print("\n# Live monitoring dashboard:")
print("""
from flashcard_pipeline.cli.rich_output import RichOutput, create_dashboard
from rich.live import Live
import asyncio

async def live_monitor():
    rich = RichOutput()
    
    with rich.create_live_display() as live:
        while True:
            # Get current stats
            stats = await get_current_stats()
            
            # Create and update dashboard
            dashboard = create_dashboard(stats)
            live.update(dashboard)
            
            await asyncio.sleep(1)  # Update every second
""")


# Example 10: Error Recovery Patterns
print("\n\n" + "=" * 60)
print("Example 10: Error Recovery in CLI")
print("=" * 60)

print("\n# Automatic retry on errors:")
print("flashcard process batch words.csv --retry-failed --max-retries 3")

print("\n# Resume from checkpoint:")
print("flashcard process batch large_dataset.csv --checkpoint --resume")

print("\n# Fallback to cache on API errors:")
print("flashcard process single '안녕' --fallback-cache")

print("\n# Process with circuit breaker:")
print("flashcard process batch words.csv --circuit-breaker --failure-threshold 5")

print("\n" + "=" * 60)
print("End of Examples")
print("=" * 60)