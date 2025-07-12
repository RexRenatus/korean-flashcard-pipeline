# Intelligent Assistant System for Claude Code

Last Updated: 2025-01-09

## Overview

The Intelligent Assistant System is a comprehensive automation framework that enhances Claude Code with advanced features for project management, code quality, time tracking, and automated testing. It integrates seamlessly with Claude Code's hook system to provide intelligent assistance throughout your development workflow.

## Components

### 1. Intelligent Organizer
Maintains project structure and documentation automatically.

**Features:**
- Automatic file categorization
- Project structure analysis
- Documentation map maintenance
- Dependency tracking
- Organization suggestions
- Orphaned file detection
- Automatic PROJECT_INDEX.md updates

### 2. TimeKeeper
Tracks time and optimizes work sessions for maximum productivity.

**Features:**
- Session time tracking
- Pomodoro timer implementation
- Break reminders (every 90 minutes)
- Productivity score calculation
- Task duration estimation
- Peak productivity hour detection
- Comprehensive time reports

### 3. Smart Linter
Advanced code quality enforcement beyond standard linting.

**Features:**
- Multi-language support (Python, JavaScript, TypeScript, Rust)
- Custom project rules
- Security pattern detection
- Code complexity metrics
- Auto-fix capabilities (configurable)
- Pattern-based issue detection
- Performance metrics calculation

### 4. Test Guardian
Ensures comprehensive test coverage and automated test management.

**Features:**
- Automatic test file creation
- Test execution monitoring
- Coverage tracking and reporting
- Test failure handling
- Framework detection (pytest, jest, mocha, etc.)
- Test generation from source files
- Coverage target enforcement (default: 80%)

## Installation

1. Ensure the flashcard pipeline project is set up with a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install the intelligent assistant as part of the flashcard pipeline:
```bash
pip install -e .
```

3. The intelligent assistant features are configured in `.claude/settings.json`

## Configuration

The system is configured through `.claude/settings.json`. Key configuration options:

```json
{
  "intelligent_assistant": {
    "enabled": true,
    "features": {
      "organizer": {
        "enabled": true,
        "auto_organize": true,
        "suggest_refactoring": true
      },
      "timekeeper": {
        "enabled": true,
        "pomodoro_duration": 25,
        "break_reminders": true,
        "optimal_hours": [10, 11, 14, 15]
      },
      "linter": {
        "enabled": true,
        "auto_fix": false,
        "max_complexity": 10,
        "max_function_length": 50
      },
      "test_guardian": {
        "enabled": true,
        "auto_run_tests": true,
        "coverage_target": 80
      }
    }
  }
}
```

## Usage

Once installed and configured, the Intelligent Assistant works automatically through Claude Code's hook system.

### Pre-Task Actions
- **Workspace Preparation**: Creates necessary directories and files
- **Time Check**: Suggests breaks if you've been working too long
- **Dependency Validation**: Ensures required dependencies are available
- **Task Timing**: Suggests optimal timing for complex tasks

### Post-Task Actions
- **Organization**: Updates project structure and suggests file moves
- **Linting**: Runs code quality checks on modified files
- **Testing**: Creates/updates test files and runs tests automatically
- **Documentation**: Updates PROJECT_INDEX.md and other docs

### Session Management
- **Time Reports**: Generate comprehensive productivity reports
- **Session Summaries**: Track what was accomplished
- **Coverage Reports**: Monitor test coverage trends
- **Break Reminders**: Maintain healthy work patterns

## Hook Integration

The system integrates with Claude Code through these hooks:

- `pre_write`: Prepares workspace before file creation
- `post_write`: Lints, tests, and organizes after file write
- `pre_edit`: Validates dependencies before editing
- `post_edit`: Runs quality checks after editing
- `pre_bash`: Checks work session and command safety
- `post_bash`: Records task completion and timing
- `session_end`: Generates reports and cleanup
- `error`: Provides intelligent error recovery suggestions

## CLI Commands

You can also use the intelligent assistant directly:

```bash
# Run pre-write hook
python -m flashcard_pipeline.intelligent_assistant.hooks pre_write /path/to/file

# Run post-write hook
python -m flashcard_pipeline.intelligent_assistant.hooks post_write /path/to/file

# Generate session report
python -m flashcard_pipeline.intelligent_assistant.hooks session_end

# Handle errors
python -m flashcard_pipeline.intelligent_assistant.hooks error "error_type" "error_message"
```

## Features in Action

### Automatic Test Creation
When you create a new Python file `src/mymodule.py`, Test Guardian automatically:
1. Creates `tests/test_mymodule.py`
2. Generates test cases for all functions and classes
3. Runs the tests immediately
4. Reports coverage

### Smart Organization
When you create files in the wrong location, Intelligent Organizer:
1. Detects misplaced files
2. Suggests better locations
3. Updates PROJECT_INDEX.md
4. Maintains documentation references

### Productivity Optimization
TimeKeeper helps you work efficiently by:
1. Tracking task durations
2. Suggesting breaks at optimal times
3. Identifying your peak productivity hours
4. Generating time usage reports

### Code Quality Enforcement
Smart Linter goes beyond syntax checking:
1. Detects security vulnerabilities
2. Checks code complexity
3. Enforces project-specific rules
4. Suggests auto-fixes where possible

## Troubleshooting

### Component Not Working
Check if the component is enabled in settings:
```json
"features": {
  "component_name": {
    "enabled": true
  }
}
```

### Python Commands Failing
Ensure virtual environment is activated:
```bash
source venv/bin/activate
```

### Hooks Not Triggering
Verify settings.json is properly configured:
```bash
cat .claude/settings.json | grep intelligent_assistant
```

## Advanced Configuration

### Custom Lint Rules
Add custom rules to `.lint/custom_rules.json`:
```json
{
  "python": {
    "no_print_debug": {
      "pattern": "print\\(.*debug",
      "message": "Remove debug print statements",
      "severity": "warning",
      "fixable": true
    }
  }
}
```

### Test Templates
Customize test generation templates in the configuration:
```json
"test_guardian": {
  "templates": {
    "python": "custom_test_template.py"
  }
}
```

### Productivity Patterns
Configure your optimal work patterns:
```json
"timekeeper": {
  "optimal_hours": [9, 10, 11, 14, 15, 16],
  "break_threshold_minutes": 90,
  "session_warning_hours": 4
}
```

## Contributing

To contribute to the Intelligent Assistant System:

1. Follow the existing code patterns
2. Add tests for new features
3. Update documentation
4. Ensure all components remain modular

## Future Enhancements

Planned features:
- Machine learning for productivity pattern detection
- Integration with external project management tools
- Advanced refactoring suggestions
- Automated code review comments
- Team collaboration features

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review hook logs in Claude Code
3. File an issue in the project repository

---

Remember: The Intelligent Assistant is designed to enhance your workflow, not restrict it. All features can be customized or disabled based on your preferences.