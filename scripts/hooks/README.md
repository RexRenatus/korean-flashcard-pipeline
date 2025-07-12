# Hooks System Directory Structure

This directory contains the unified hook system for the Claude Code project.

## Directory Organization

```
hooks/
├── README.md                    # This file
├── config/                      # Configuration files
│   ├── hooks.json              # Main hooks configuration
│   ├── security.json           # Security scanner configuration
│   └── performance.json        # Performance thresholds
├── core/                       # Core hook infrastructure
│   ├── __init__.py
│   ├── dispatcher.py           # Unified hook dispatcher
│   ├── context_injector.py     # Context enrichment
│   ├── cache_manager.py        # Multi-layer cache
│   └── circuit_breaker.py      # Failure prevention
├── monitors/                   # Monitoring systems
│   ├── __init__.py
│   ├── performance.py          # Performance tracking
│   └── notifications.py        # Notification manager
├── scanners/                   # Pre-execution scanners
│   ├── __init__.py
│   └── security.py            # Pre-flight security scanner
├── validators/                 # Validation hooks
│   ├── __init__.py
│   ├── security.py            # Security validation
│   ├── syntax.py              # Syntax checking
│   └── solid.py               # SOLID principles
└── handlers/                   # Operation handlers
    ├── __init__.py
    ├── documentation.py        # Documentation search
    └── error.py               # Error handling
```

## Configuration Files

### hooks.json
Main configuration for the hook system, defining:
- Available hooks
- Execution strategies (parallel/sequential)
- Dependencies between hooks
- Timeout values

### security.json
Security scanner configuration:
- Enabled security checks
- Severity thresholds
- Whitelist patterns
- Custom security rules

### performance.json
Performance monitoring thresholds:
- Execution time limits
- Error rate thresholds
- Cache TTL values
- Notification triggers

## Usage

The hook system is accessed through the unified dispatcher:

```python
from scripts.hooks.core.dispatcher import UnifiedHookDispatcher

dispatcher = UnifiedHookDispatcher()
results = await dispatcher.dispatch(tool_name, operation, context)
```

## Adding New Hooks

1. Create the hook implementation in the appropriate directory
2. Register it in `config/hooks.json`
3. Define any dependencies or special execution requirements
4. Add tests for the new hook

## Key Features

- **Parallel Execution**: Hooks run concurrently when possible
- **Smart Caching**: Results cached based on file content and context
- **Circuit Breaking**: Automatic failure prevention
- **Performance Monitoring**: Real-time performance tracking
- **Security Scanning**: Pre-flight security checks
- **Rich Context**: Automatic context enrichment
- **Notifications**: Non-blocking alerts for issues