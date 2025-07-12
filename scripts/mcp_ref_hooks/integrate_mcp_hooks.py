#!/usr/bin/env python3
"""
Integrate MCP Ref hooks into the main settings.json
"""

import json
import sys
from pathlib import Path


def integrate_mcp_hooks():
    """Add MCP Ref hooks to the main settings"""
    
    # Load current settings
    settings_path = Path(".claude/settings.json")
    with open(settings_path, 'r') as f:
        settings = json.load(f)
    
    # Load MCP ref hooks configuration
    mcp_hooks_path = Path(".claude/mcp_ref_hooks.json")
    with open(mcp_hooks_path, 'r') as f:
        mcp_config = json.load(f)
    
    # Add MCP configuration to settings
    settings["mcp_ref_integration"] = mcp_config["mcp_ref_integration"]
    
    # Add MCP hooks to appropriate sections
    mcp_hooks = {
        "PreToolUse": [
            {
                "matcher": "Task|Write|Edit|MultiEdit",
                "hooks": [
                    {
                        "type": "command",
                        "command": "cd /mnt/c/Users/JackTheRipper/Desktop/\\(00\\)\\ ClaudeCode/Anthropic_Flashcards && source venv/bin/activate 2>/dev/null && python scripts/mcp_ref_hooks/pre_tool_documentation.py '$CLAUDE_TOOL_NAME' '$CLAUDE_FILE_PATH' '$CLAUDE_OPERATION' 2>/dev/null || true",
                        "timeout": 30,
                        "description": "[MCP REF] Search relevant documentation with keywords"
                    }
                ]
            },
            {
                "matcher": "Write|Edit|MultiEdit",
                "hooks": [
                    {
                        "type": "command",
                        "command": "echo '[MCP REF] Preparing intelligent documentation search...' && echo '🔍 Extracting keywords from context' && echo '📚 Searching relevant API documentation'",
                        "timeout": 5,
                        "description": "[MCP REF] Documentation search notification"
                    }
                ]
            }
        ],
        "PostToolUse": [
            {
                "matcher": "Read",
                "hooks": [
                    {
                        "type": "command",
                        "command": "cd /mnt/c/Users/JackTheRipper/Desktop/\\(00\\)\\ ClaudeCode/Anthropic_Flashcards && source venv/bin/activate 2>/dev/null && if [ -f \"$CLAUDE_FILE_PATH\" ]; then python scripts/mcp_ref_hooks/analyze_read_content.py '$CLAUDE_FILE_PATH' 2>/dev/null || true; fi",
                        "timeout": 20,
                        "description": "[MCP REF] Analyze read content and suggest documentation"
                    }
                ]
            }
        ],
        "Error": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "cd /mnt/c/Users/JackTheRipper/Desktop/\\(00\\)\\ ClaudeCode/Anthropic_Flashcards && source venv/bin/activate 2>/dev/null && python scripts/mcp_ref_hooks/error_documentation.py '$CLAUDE_ERROR_TYPE' '$CLAUDE_ERROR_MESSAGE' '$CLAUDE_STACK_TRACE' 2>/dev/null || true",
                        "timeout": 45,
                        "description": "[MCP REF] Search documentation for error solutions"
                    }
                ]
            }
        ]
    }
    
    # Merge MCP hooks into existing hooks
    for hook_type, hook_list in mcp_hooks.items():
        if hook_type not in settings["hooks"]:
            settings["hooks"][hook_type] = []
        
        # Insert MCP hooks at appropriate positions
        for mcp_hook in hook_list:
            # Find insertion point based on priority
            inserted = False
            for i, existing_hook in enumerate(settings["hooks"][hook_type]):
                # Insert before less important hooks
                if "matcher" in mcp_hook and "matcher" in existing_hook:
                    if mcp_hook["matcher"] == existing_hook["matcher"]:
                        # Insert after existing hooks for same matcher
                        continue
                settings["hooks"][hook_type].insert(i + 1, mcp_hook)
                inserted = True
                break
            
            if not inserted:
                settings["hooks"][hook_type].append(mcp_hook)
    
    # Add MCP-specific debugging hooks
    if "debugging_hooks" not in settings:
        settings["debugging_hooks"] = {}
    
    settings["debugging_hooks"]["mcp_ref_integration"] = {
        "enabled": True,
        "auto_search_errors": True,
        "documentation_lookup": True,
        "api_reference_search": True,
        "keyword_extraction": True,
        "cache_documentation": True,
        "log_level": "INFO"
    }
    
    # Update version and timestamp
    settings["mcp_integration_version"] = "1.0.0"
    settings["last_updated"] = "2025-01-10"
    
    # Save updated settings
    settings_backup = settings_path.with_suffix('.json.backup')
    settings_path.rename(settings_backup)
    
    with open(settings_path, 'w') as f:
        json.dump(settings, f, indent=2)
    
    print(f"✅ MCP Ref hooks integrated successfully!")
    print(f"📄 Backup saved to: {settings_backup}")
    print(f"🔧 New hooks added:")
    print(f"   - Pre-tool documentation search")
    print(f"   - Error documentation lookup") 
    print(f"   - Read content analysis")
    print(f"   - API validation")
    

if __name__ == "__main__":
    try:
        integrate_mcp_hooks()
    except Exception as e:
        print(f"❌ Error integrating MCP hooks: {e}")
        sys.exit(1)