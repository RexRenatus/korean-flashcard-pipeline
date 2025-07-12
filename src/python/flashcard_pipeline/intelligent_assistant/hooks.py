"""
Intelligent Hook System

Integration layer for Claude Code hooks with the Intelligent Assistant System.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from .core import IntelligentAssistantSystem

logger = logging.getLogger(__name__)


class IntelligentHookSystem:
    """
    Integration of all intelligent components into Claude Code hooks.
    
    This class provides the bridge between Claude Code's hook system
    and the Intelligent Assistant components.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the hook system with optional configuration."""
        self.config_path = config_path or Path(".claude") / "intelligent_assistant.json"
        self.config = self._load_config()
        
        # Initialize the assistant system
        self.assistant = IntelligentAssistantSystem(self.config_path)
        
        # Hook state tracking
        self.active_hooks = set()
        self.hook_history = []
        
        logger.info("Intelligent Hook System initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load hook configuration."""
        default_config = {
            "enabled": True,
            "hooks": {
                "pre_tool_use": True,
                "post_tool_use": True,
                "error_handler": True,
                "session_end": True,
                "notification": True
            },
            "features": {
                "organizer": {"enabled": True, "auto_organize": True},
                "timekeeper": {"enabled": True, "break_reminders": True},
                "linter": {"enabled": True, "auto_fix": False},
                "test_guardian": {"enabled": True, "auto_run_tests": True}
            }
        }
        
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                return {**default_config, **user_config}
            except Exception as e:
                logger.warning(f"Failed to load config: {e}")
        
        return default_config
    
    # Main hook methods
    
    def pre_tool_use_hook(self, tool_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pre-execution hook called before any tool use.
        
        Args:
            tool_info: Information about the tool being called
            
        Returns:
            Enhanced tool info with pre-processing data
        """
        if not self.config["hooks"]["pre_tool_use"]:
            return tool_info
        
        logger.debug(f"Pre-tool hook: {tool_info.get('tool_name', 'unknown')}")
        
        # Track hook activation
        self.active_hooks.add("pre_tool_use")
        
        # Convert tool info to task format for assistant
        task_info = self._tool_to_task_info(tool_info)
        
        # Process through assistant
        enhanced_info = self.assistant.hook_pre_task(task_info)
        
        # Convert back to tool format
        enhanced_tool_info = self._task_to_tool_info(enhanced_info, tool_info)
        
        # Add any notifications
        self._process_notifications()
        
        return enhanced_tool_info
    
    def post_tool_use_hook(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post-execution hook called after tool use.
        
        Args:
            result: Result from tool execution
            
        Returns:
            Enhanced result with post-processing data
        """
        if not self.config["hooks"]["post_tool_use"]:
            return result
        
        logger.debug(f"Post-tool hook: {result.get('tool_name', 'unknown')}")
        
        # Track hook activation
        self.active_hooks.add("post_tool_use")
        
        # Convert to task result format
        task_result = self._tool_result_to_task_result(result)
        
        # Process through assistant
        enhanced_result = self.assistant.hook_post_task(task_result)
        
        # Handle component results
        self._handle_component_results(enhanced_result)
        
        # Convert back to tool result format
        final_result = self._task_result_to_tool_result(enhanced_result, result)
        
        # Record in history
        self.hook_history.append({
            "timestamp": datetime.now().isoformat(),
            "type": "post_tool_use",
            "tool": result.get("tool_name"),
            "success": result.get("success", True)
        })
        
        return final_result
    
    def error_handler_hook(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Error handling hook.
        
        Args:
            error_info: Information about the error
            
        Returns:
            Enhanced error info with suggestions
        """
        if not self.config["hooks"]["error_handler"]:
            return error_info
        
        logger.debug(f"Error handler hook: {error_info.get('type', 'unknown')}")
        
        # Process through assistant
        enhanced_error = self.assistant.hook_error(error_info)
        
        # Add recovery suggestions
        if "suggestions" in enhanced_error:
            self._display_error_suggestions(enhanced_error["suggestions"])
        
        return enhanced_error
    
    def session_end_hook(self) -> Dict[str, Any]:
        """
        Session end hook for cleanup and reporting.
        
        Returns:
            Session summary data
        """
        if not self.config["hooks"]["session_end"]:
            return {}
        
        logger.info("Session end hook triggered")
        
        # Get final status report
        status_report = self.assistant.get_status_report()
        
        # Generate session summary
        summary = {
            "session": status_report["session"],
            "hooks_triggered": list(self.active_hooks),
            "notifications_sent": len(self.assistant.notifications),
            "component_summaries": status_report["component_status"]
        }
        
        # Display session summary
        self._display_session_summary(summary)
        
        # Shutdown assistant
        self.assistant.shutdown()
        
        return summary
    
    def notification_hook(self, notification: Dict[str, Any]) -> None:
        """
        Handle system notifications.
        
        Args:
            notification: Notification data
        """
        if not self.config["hooks"]["notification"]:
            return
        
        notification_type = notification.get("type", "unknown")
        
        # Route to appropriate handler
        handlers = {
            "test_failure": self._handle_test_failure_notification,
            "lint_error": self._handle_lint_error_notification,
            "break_reminder": self._handle_break_reminder,
            "organization_suggestion": self._handle_organization_suggestion
        }
        
        handler = handlers.get(notification_type)
        if handler:
            handler(notification)
        else:
            logger.warning(f"Unknown notification type: {notification_type}")
    
    # Claude Code settings.json hook functions
    
    def generate_hook_commands(self) -> Dict[str, Any]:
        """
        Generate hook commands for .claude/settings.json
        
        Returns:
            Dictionary of hook configurations
        """
        python_cmd = "python -m flashcard_pipeline.intelligent_assistant.hooks"
        
        hooks = {
            "pre_write": [
                {
                    "command": f"{python_cmd} pre_write $CLAUDE_FILE_PATH",
                    "description": "Intelligent organization before file write"
                }
            ],
            "post_write": [
                {
                    "command": f"{python_cmd} post_write $CLAUDE_FILE_PATH",
                    "description": "Update documentation and run tests after write"
                }
            ],
            "pre_edit": [
                {
                    "command": f"{python_cmd} pre_edit $CLAUDE_FILE_PATH",
                    "description": "Check dependencies and prepare for edit"
                }
            ],
            "post_edit": [
                {
                    "command": f"{python_cmd} post_edit $CLAUDE_FILE_PATH",
                    "description": "Lint, test, and organize after edit"
                }
            ],
            "post_read": [
                {
                    "command": f"{python_cmd} post_read $CLAUDE_FILE_PATH",
                    "description": "Track file access patterns"
                }
            ],
            "pre_bash": [
                {
                    "command": f"{python_cmd} pre_bash '$CLAUDE_COMMAND'",
                    "description": "Time tracking and command validation"
                }
            ],
            "post_bash": [
                {
                    "command": f"{python_cmd} post_bash '$CLAUDE_COMMAND' $CLAUDE_EXIT_CODE",
                    "description": "Record command results and update tracking"
                }
            ],
            "session_end": [
                {
                    "command": f"{python_cmd} session_end",
                    "description": "Generate reports and clean up"
                }
            ],
            "error": [
                {
                    "command": f"{python_cmd} error '$CLAUDE_ERROR_TYPE' '$CLAUDE_ERROR_MESSAGE'",
                    "description": "Intelligent error handling and recovery"
                }
            ]
        }
        
        return hooks
    
    # Helper methods
    
    def _tool_to_task_info(self, tool_info: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Claude Code tool info to task info format."""
        return {
            "id": tool_info.get("id", f"tool_{datetime.now().timestamp()}"),
            "type": tool_info.get("tool_name", "unknown"),
            "parameters": tool_info.get("parameters", {}),
            "timestamp": datetime.now().isoformat()
        }
    
    def _task_to_tool_info(self, task_info: Dict[str, Any], original: Dict[str, Any]) -> Dict[str, Any]:
        """Convert task info back to tool info format."""
        enhanced = original.copy()
        
        # Add any preparation data
        if "workspace_preparation" in task_info:
            enhanced["preparation"] = task_info["workspace_preparation"]
        
        if "timing_suggestion" in task_info:
            enhanced["timing"] = task_info["timing_suggestion"]
        
        return enhanced
    
    def _tool_result_to_task_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Convert tool result to task result format."""
        task_result = {
            "id": result.get("id", "unknown"),
            "success": result.get("success", True),
            "modified_files": [],
            "new_files": []
        }
        
        # Extract file information based on tool
        tool_name = result.get("tool_name", "")
        
        if tool_name in ["Write", "Edit", "MultiEdit"]:
            file_path = result.get("parameters", {}).get("file_path")
            if file_path:
                if tool_name == "Write" and not Path(file_path).exists():
                    task_result["new_files"].append(file_path)
                else:
                    task_result["modified_files"].append(file_path)
        
        return task_result
    
    def _task_result_to_tool_result(self, task_result: Dict[str, Any], original: Dict[str, Any]) -> Dict[str, Any]:
        """Convert enhanced task result back to tool result format."""
        enhanced = original.copy()
        
        # Add component results
        if "lint_results" in task_result:
            enhanced["lint_results"] = self._format_lint_results(task_result["lint_results"])
        
        if "test_results" in task_result:
            enhanced["test_results"] = self._format_test_results(task_result["test_results"])
        
        if "organization_updates" in task_result:
            enhanced["organization"] = task_result["organization_updates"]
        
        return enhanced
    
    def _handle_component_results(self, result: Dict[str, Any]):
        """Handle results from individual components."""
        # Handle lint results
        if "lint_results" in result:
            lint_results = result["lint_results"]
            if lint_results.get("errors"):
                logger.warning(f"Lint errors found: {len(lint_results['errors'])}")
                if self.config["features"]["linter"]["auto_fix"]:
                    logger.info("Attempting auto-fix...")
        
        # Handle test results
        if "test_results" in result:
            test_results = result["test_results"]
            if test_results.get("failures"):
                logger.error(f"Test failures: {len(test_results['failures'])}")
            if test_results.get("tests_created"):
                logger.info(f"Created {len(test_results['tests_created'])} test files")
        
        # Handle organization updates
        if "organization_updates" in result:
            org_updates = result["organization_updates"]
            if org_updates.get("suggestions"):
                logger.info(f"Organization suggestions: {len(org_updates['suggestions'])}")
    
    def _process_notifications(self):
        """Process and display pending notifications."""
        notifications = self.assistant.get_notifications(clear=True)
        
        for notification in notifications:
            self.notification_hook(notification)
    
    def _display_error_suggestions(self, suggestions: List[str]):
        """Display error recovery suggestions."""
        if suggestions:
            print("\n💡 Suggestions:")
            for suggestion in suggestions:
                print(f"  • {suggestion}")
    
    def _display_session_summary(self, summary: Dict[str, Any]):
        """Display session summary."""
        print("\n" + "="*60)
        print("📊 INTELLIGENT ASSISTANT SESSION SUMMARY")
        print("="*60)
        
        session_info = summary["session"]
        print(f"\n⏱️  Duration: {session_info['duration']}")
        print(f"✅ Tasks Completed: {session_info['tasks_completed']}")
        print(f"❌ Errors: {session_info['errors_count']}")
        
        # Component summaries
        if "component_summaries" in summary:
            print("\n📈 Component Activity:")
            for component, status in summary["component_summaries"].items():
                print(f"\n  {component.title()}:")
                for key, value in status.items():
                    print(f"    • {key}: {value}")
        
        print("\n" + "="*60)
    
    def _format_lint_results(self, lint_results: Dict[str, Any]) -> str:
        """Format lint results for display."""
        total_issues = lint_results["summary"]["total_issues"]
        if total_issues == 0:
            return "✅ No linting issues found"
        
        parts = []
        if lint_results["errors"]:
            parts.append(f"❌ {len(lint_results['errors'])} errors")
        if lint_results["warnings"]:
            parts.append(f"⚠️  {len(lint_results['warnings'])} warnings")
        
        return f"Lint: {', '.join(parts)}"
    
    def _format_test_results(self, test_results: Dict[str, Any]) -> str:
        """Format test results for display."""
        if not test_results["tests_run"]:
            return "No tests run"
        
        total_run = len(test_results["tests_run"])
        failures = len(test_results["failures"])
        
        if failures == 0:
            return f"✅ All {total_run} tests passed"
        else:
            return f"❌ {failures}/{total_run} tests failed"
    
    # Notification handlers
    
    def _handle_test_failure_notification(self, notification: Dict[str, Any]):
        """Handle test failure notifications."""
        data = notification.get("data", {})
        failures = data.get("failures", [])
        
        print(f"\n❌ TEST FAILURES DETECTED ({len(failures)} tests)")
        for failure in failures[:3]:  # Show first 3
            print(f"  • {failure.get('test', 'Unknown test')}")
        
        if len(failures) > 3:
            print(f"  ... and {len(failures) - 3} more")
    
    def _handle_lint_error_notification(self, notification: Dict[str, Any]):
        """Handle lint error notifications."""
        data = notification.get("data", {})
        errors = data.get("errors", [])
        
        print(f"\n⚠️  LINT ERRORS FOUND ({len(errors)} issues)")
        for error in errors[:3]:  # Show first 3
            print(f"  • {error.get('file', 'Unknown')}:{error.get('line', '?')} - {error.get('message', '')}")
        
        if len(errors) > 3:
            print(f"  ... and {len(errors) - 3} more")
    
    def _handle_break_reminder(self, notification: Dict[str, Any]):
        """Handle break reminder notifications."""
        data = notification.get("data", {})
        
        print("\n☕ BREAK REMINDER")
        print(f"You've been working for {data.get('time_since_break', 'a while')}.")
        print("Consider taking a short break to maintain productivity!")
    
    def _handle_organization_suggestion(self, notification: Dict[str, Any]):
        """Handle organization suggestion notifications."""
        data = notification.get("data", {})
        suggestions = data.get("suggestions", [])
        
        if suggestions:
            print("\n📁 ORGANIZATION SUGGESTIONS")
            for suggestion in suggestions[:3]:
                print(f"  • {suggestion.get('message', 'Organization suggestion')}")


# CLI entry point for hook execution
def main():
    """Main entry point for hook execution from command line."""
    if len(sys.argv) < 2:
        print("Usage: python -m flashcard_pipeline.intelligent_assistant.hooks <hook_name> [args...]")
        sys.exit(1)
    
    hook_name = sys.argv[1]
    args = sys.argv[2:] if len(sys.argv) > 2 else []
    
    # Initialize hook system
    hook_system = IntelligentHookSystem()
    
    # Map hook names to methods
    hook_map = {
        "pre_write": lambda: hook_system.pre_tool_use_hook({"tool_name": "Write", "parameters": {"file_path": args[0]}}),
        "post_write": lambda: hook_system.post_tool_use_hook({"tool_name": "Write", "parameters": {"file_path": args[0]}, "success": True}),
        "pre_edit": lambda: hook_system.pre_tool_use_hook({"tool_name": "Edit", "parameters": {"file_path": args[0]}}),
        "post_edit": lambda: hook_system.post_tool_use_hook({"tool_name": "Edit", "parameters": {"file_path": args[0]}, "success": True}),
        "post_read": lambda: hook_system.post_tool_use_hook({"tool_name": "Read", "parameters": {"file_path": args[0]}, "success": True}),
        "pre_bash": lambda: hook_system.pre_tool_use_hook({"tool_name": "Bash", "parameters": {"command": args[0]}}),
        "post_bash": lambda: hook_system.post_tool_use_hook({"tool_name": "Bash", "parameters": {"command": args[0]}, "exit_code": int(args[1]) if len(args) > 1 else 0, "success": True}),
        "session_end": lambda: hook_system.session_end_hook(),
        "error": lambda: hook_system.error_handler_hook({"type": args[0] if args else "unknown", "message": args[1] if len(args) > 1 else ""})
    }
    
    # Execute hook
    if hook_name in hook_map:
        try:
            result = hook_map[hook_name]()
            # Return success
            sys.exit(0)
        except Exception as e:
            logger.error(f"Hook execution failed: {e}")
            sys.exit(1)
    else:
        print(f"Unknown hook: {hook_name}")
        sys.exit(1)


if __name__ == "__main__":
    main()