#!/usr/bin/env python3
"""
Update hooks configuration in settings.json with optimized configurations.
This script properly integrates our optimizations into the existing settings.json structure.
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

def load_settings(settings_path: Path) -> Dict[str, Any]:
    """Load settings.json file."""
    if not settings_path.exists():
        print(f"Error: Settings file not found at {settings_path}")
        sys.exit(1)
    
    with open(settings_path, 'r') as f:
        return json.load(f)

def save_settings(settings_path: Path, settings: Dict[str, Any]) -> None:
    """Save settings.json file with proper formatting."""
    with open(settings_path, 'w') as f:
        json.dump(settings, f, indent=2)
    print(f"✅ Updated {settings_path}")

def create_optimized_hook(
    command: str,
    timeout: int,
    description: str,
    hook_type: str = "command"
) -> Dict[str, Any]:
    """Create an optimized hook configuration."""
    return {
        "type": hook_type,
        "command": command,
        "timeout": timeout,
        "description": description
    }

def get_optimized_hooks() -> Dict[str, List[Dict[str, Any]]]:
    """Get optimized hook configurations using our new dispatcher."""
    base_path = "/mnt/c/Users/JackTheRipper/Desktop/\\(00\\)\\ ClaudeCode/Anthropic_Flashcards"
    
    return {
        "PreToolUse": [
            {
                "matcher": "Write|Edit|MultiEdit",
                "hooks": [
                    create_optimized_hook(
                        f"cd {base_path} && source venv/bin/activate 2>/dev/null && python scripts/hooks/core/dispatcher_v2.py validate --tool '$CLAUDE_TOOL_NAME' --file '$CLAUDE_FILE_PATH' --config-dir scripts/hooks/.settings 2>/dev/null || true",
                        timeout=8,
                        description="[OPTIMIZED V2] Context-aware validation with smart hook selection"
                    )
                ]
            },
            {
                "matcher": "Task|Write|Edit|MultiEdit",
                "hooks": [
                    create_optimized_hook(
                        f"cd {base_path} && source venv/bin/activate 2>/dev/null && python scripts/hooks/core/dispatcher_v2.py documentation --tool '$CLAUDE_TOOL_NAME' --file '$CLAUDE_FILE_PATH' --config-dir scripts/hooks/.settings 2>/dev/null || true",
                        timeout=6,
                        description="[OPTIMIZED V2] Enhanced documentation search with caching"
                    )
                ]
            },
            {
                "matcher": "Bash",
                "hooks": [
                    create_optimized_hook(
                        f"cd {base_path} && source venv/bin/activate 2>/dev/null && python scripts/hooks/scanners/security.py preflight --command '$CLAUDE_COMMAND' 2>/dev/null || true",
                        timeout=3,
                        description="[NEW] Pre-flight security scanner for bash commands"
                    ),
                    create_optimized_hook(
                        f"if echo \"$CLAUDE_COMMAND\" | grep -E '^(python|pip|pytest)' > /dev/null && [ \"$CLAUDE_VENV_CHECKED\" != \"true\" ]; then export CLAUDE_COMMAND=\"source {base_path}/venv/bin/activate && $CLAUDE_COMMAND\" && export CLAUDE_VENV_CHECKED=true; fi",
                        timeout=1,
                        description="Fast venv activation with session caching"
                    )
                ]
            }
        ],
        "PostToolUse": [
            {
                "matcher": "Write|Edit|MultiEdit",
                "hooks": [
                    create_optimized_hook(
                        f"cd {base_path} && source venv/bin/activate 2>/dev/null && python scripts/hooks/monitors/performance.py record --hook-id post_write --file '$CLAUDE_FILE_PATH' 2>/dev/null || true",
                        timeout=2,
                        description="[NEW] Performance monitoring for write operations"
                    )
                ]
            }
        ],
        "Error": [
            {
                "hooks": [
                    create_optimized_hook(
                        f"cd {base_path} && source venv/bin/activate 2>/dev/null && python scripts/hooks/core/dispatcher_v2.py error --tool '$CLAUDE_TOOL_NAME' --context '{{\"error_type\": \"$CLAUDE_ERROR_TYPE\", \"error_message\": \"$CLAUDE_ERROR_MESSAGE\"}}' --config-dir scripts/hooks/.settings 2>/dev/null || true",
                        timeout=8,
                        description="[OPTIMIZED V2] Unified error analysis with circuit breaker"
                    )
                ]
            }
        ],
        "Debug": [
            {
                "matcher": "*",
                "hooks": [
                    create_optimized_hook(
                        f"cd {base_path} && source venv/bin/activate 2>/dev/null && python scripts/hooks/monitors/performance.py report --format json 2>/dev/null || true",
                        timeout=3,
                        description="[ENHANCED] Detailed performance metrics with p95/p99"
                    )
                ]
            }
        ]
    }

def create_hook_settings_config() -> None:
    """Create configuration files in .settings directory for dispatcher_v2."""
    settings_dir = Path(__file__).parent / ".settings"
    settings_dir.mkdir(exist_ok=True)
    
    # Create hooks.json for dispatcher_v2
    hooks_config = {
        "global": {
            "max_workers": 5,
            "default_timeout": 5
        },
        "hooks": {
            "security_check": {
                "command": "python scripts/validators/security_check.py",
                "parallel": True,
                "timeout": 3,
                "file_patterns": ["*"],
                "exclude_patterns": []
            },
            "syntax_check": {
                "command": "python scripts/validators/syntax_check.py",
                "parallel": True,
                "timeout": 2,
                "file_patterns": ["*.py", "*.js", "*.json", "*.yml", "*.yaml", "*.md", "*.sh"],
                "exclude_patterns": []
            },
            "solid_check": {
                "command": "python scripts/solid_enforcer_v2.py",
                "parallel": True,
                "timeout": 5,
                "file_patterns": ["*.py"],
                "exclude_patterns": ["test_*.py", "*_test.py", "*/tests/*"]
            },
            "doc_search": {
                "command": "python scripts/mcp_ref_hooks/unified_documentation.py",
                "parallel": True,
                "timeout": 8,
                "file_patterns": ["*"]
            }
        },
        "operations": {
            "validate": {
                "hooks": ["security_check", "syntax_check", "solid_check"]
            },
            "documentation": {
                "hooks": ["doc_search"]
            },
            "error": {
                "hooks": ["security_check"]
            }
        },
        "dependencies": {
            "solid_check": {
                "depends_on": ["syntax_check"]
            }
        }
    }
    
    # Create security.json
    security_config = {
        "enabled": True,
        "patterns": {
            "hardcoded_secrets": [
                r"(api[_-]?key|apikey|secret[_-]?key|password|passwd|pwd)\\s*=\\s*[\"'][^\"']+[\"']",
                r"(token|auth|credential)\\s*=\\s*[\"'][^\"']+[\"']"
            ],
            "unsafe_commands": [
                r"eval\\s*\\(",
                r"exec\\s*\\(",
                r"\\$\\(",
                r"subprocess\\.call\\s*\\(.*shell\\s*=\\s*True"
            ],
            "sensitive_paths": [
                r"/etc/passwd",
                r"~/.ssh/",
                r"~/.aws/credentials"
            ]
        },
        "file_checks": {
            "max_file_size_mb": 100,
            "allowed_extensions": ["py", "js", "json", "yml", "yaml", "md", "txt", "sh", "rs", "toml"],
            "blocked_extensions": ["exe", "dll", "so", "dylib", "bin"]
        }
    }
    
    # Create performance.json
    performance_config = {
        "window_size": 100,
        "thresholds": {
            "execution_time_p95": 10.0,
            "execution_time_p99": 15.0,
            "error_rate": 0.1,
            "timeout_rate": 0.05
        },
        "cache": {
            "ttl": {
                "default": 300,
                "by_hook": {
                    "security_check": 600,
                    "syntax_check": 300,
                    "solid_check": 900,
                    "doc_search": 1800
                }
            }
        },
        "notifications": {
            "enabled": True,
            "channels": ["console"],
            "thresholds": {
                "slow_execution": 10.0,
                "high_error_rate": 0.2
            }
        }
    }
    
    # Save configuration files
    with open(settings_dir / "hooks.json", 'w') as f:
        json.dump(hooks_config, f, indent=2)
    
    with open(settings_dir / "security.json", 'w') as f:
        json.dump(security_config, f, indent=2)
    
    with open(settings_dir / "performance.json", 'w') as f:
        json.dump(performance_config, f, indent=2)
    
    print(f"✅ Created configuration files in {settings_dir}")

def update_hook_optimization_settings(settings: Dict[str, Any]) -> None:
    """Update the hook_optimization section with our enhancements."""
    if "hook_optimization" not in settings:
        settings["hook_optimization"] = {}
    
    settings["hook_optimization"].update({
        "enabled": True,
        "version": "3.0.0",
        "performance_targets": {
            "max_hook_timeout": 8,
            "parallel_execution": True,
            "cache_hit_target": 85,
            "circuit_breaker_enabled": True
        },
        "unified_dispatcher": {
            "enabled": True,
            "version": "v2",
            "config_dir": "scripts/hooks/.settings",
            "cache_layers": ["memory", "disk"],
            "parallel_workers": 5,
            "context_injection": True,
            "smart_hook_selection": True
        },
        "context_enrichment": {
            "enabled": True,
            "features": ["project_type", "file_metadata", "git_info", "dependencies"]
        },
        "pre_flight_security": {
            "enabled": True,
            "block_on_critical": True,
            "scan_timeout": 3
        },
        "notification_system": {
            "enabled": True,
            "channels": ["console", "file"],
            "async_delivery": True
        }
    })

def main():
    """Main function to update settings.json with optimized hooks."""
    settings_path = Path(__file__).parent.parent.parent / ".claude" / "settings.json"
    
    # Load current settings
    settings = load_settings(settings_path)
    
    # Create backup
    backup_path = settings_path.with_suffix('.json.backup')
    save_settings(backup_path, settings)
    print(f"✅ Created backup at {backup_path}")
    
    # Get optimized hooks
    optimized_hooks = get_optimized_hooks()
    
    # Update specific hook sections
    for hook_type, matchers in optimized_hooks.items():
        if hook_type in settings["hooks"]:
            # Find and update matching matchers
            for new_matcher in matchers:
                matcher_pattern = new_matcher.get("matcher", "")
                updated = False
                
                # Look for existing matcher
                for i, existing_matcher in enumerate(settings["hooks"][hook_type]):
                    if existing_matcher.get("matcher", "") == matcher_pattern:
                        # Merge hooks, preferring optimized ones
                        settings["hooks"][hook_type][i] = new_matcher
                        updated = True
                        break
                
                # Add if not found
                if not updated:
                    settings["hooks"][hook_type].append(new_matcher)
    
    # Update hook optimization settings
    update_hook_optimization_settings(settings)
    
    # Create configuration files for dispatcher_v2
    create_hook_settings_config()
    
    # Save updated settings
    save_settings(settings_path, settings)
    
    print("\n✅ Hook optimization complete!")
    print("📝 Updated hooks:")
    print("  - Enhanced unified dispatcher (v2) with context injection")
    print("  - Pre-flight security scanner for bash commands")
    print("  - Performance monitoring with detailed metrics")
    print("  - Smart hook selection based on file type and context")
    print("  - Improved caching with TTL configuration")
    print("\n🔧 Configuration files created in scripts/hooks/.settings/")

if __name__ == "__main__":
    main()