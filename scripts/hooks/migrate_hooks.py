#!/usr/bin/env python3
"""
Migration script to update hook paths to new structure.
"""
import os
import json
from pathlib import Path

def update_hook_commands():
    """Update hook commands in configuration to use new paths."""
    config_path = Path(__file__).parent / "config" / "hooks.json"
    
    # Path mappings
    path_updates = {
        "python scripts/validators/security_check.py": "python -m scripts.hooks.validators.security",
        "python scripts/validators/syntax_check.py": "python -m scripts.hooks.validators.syntax", 
        "python scripts/solid_enforcer_v2.py": "python -m scripts.hooks.validators.solid",
        "python scripts/mcp_ref_hooks/unified_documentation.py": "python -m scripts.hooks.handlers.documentation"
    }
    
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
            
        # Update commands
        updated = False
        for hook_id, hook_config in config.get('hooks', {}).items():
            old_command = hook_config.get('command', '')
            for old_path, new_path in path_updates.items():
                if old_path in old_command:
                    hook_config['command'] = old_command.replace(old_path, new_path)
                    updated = True
                    print(f"Updated {hook_id}: {old_path} -> {new_path}")
                    
        if updated:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            print("\n✅ Hook configuration updated!")
        else:
            print("No updates needed.")
    else:
        print(f"Configuration file not found: {config_path}")

def create_legacy_symlinks():
    """Create symlinks for backward compatibility."""
    hooks_root = Path(__file__).parent
    
    # Create symlinks in old locations
    symlinks = [
        (hooks_root / "unified_dispatcher.py", hooks_root / "core" / "dispatcher.py"),
        (hooks_root / "context_injector.py", hooks_root / "core" / "context_injector.py"),
        (hooks_root / "performance_monitor.py", hooks_root / "monitors" / "performance.py"),
        (hooks_root / "notification_manager.py", hooks_root / "monitors" / "notifications.py"),
        (hooks_root / "preflight_scanner.py", hooks_root / "scanners" / "security.py"),
    ]
    
    for link_path, target_path in symlinks:
        if not link_path.exists() and target_path.exists():
            try:
                link_path.symlink_to(target_path)
                print(f"Created symlink: {link_path.name} -> {target_path}")
            except Exception as e:
                print(f"Failed to create symlink {link_path.name}: {e}")

if __name__ == "__main__":
    print("Migrating hooks to new structure...")
    print("=" * 50)
    
    # Update configuration
    update_hook_commands()
    
    # Create backward compatibility symlinks (optional)
    # create_legacy_symlinks()
    
    print("\n✅ Migration complete!")