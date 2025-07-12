"""
Core Intelligent Assistant System

Master coordinator for all intelligent features in Claude Code.
"""

import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class SessionData:
    """Manages session-wide data and state."""
    
    def __init__(self):
        self.session_id = f"session_{int(time.time())}"
        self.start_time = datetime.now()
        self.tasks_completed = []
        self.files_modified = []
        self.errors_encountered = []
        self.metrics = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "files_created": 0,
            "files_modified": 0,
            "tests_run": 0,
            "tests_passed": 0,
            "lint_issues_found": 0,
            "lint_issues_fixed": 0
        }
    
    def update_metric(self, metric: str, value: int = 1):
        """Update a specific metric."""
        if metric in self.metrics:
            self.metrics[metric] += value
    
    def add_task(self, task_info: Dict[str, Any]):
        """Record a completed task."""
        self.tasks_completed.append({
            "timestamp": datetime.now().isoformat(),
            "task": task_info
        })
        self.update_metric("total_tasks")
    
    def add_error(self, error_info: Dict[str, Any]):
        """Record an error."""
        self.errors_encountered.append({
            "timestamp": datetime.now().isoformat(),
            "error": error_info
        })
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Generate session summary."""
        duration = datetime.now() - self.start_time
        return {
            "session_id": self.session_id,
            "duration": str(duration),
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "metrics": self.metrics,
            "tasks_completed": len(self.tasks_completed),
            "errors_count": len(self.errors_encountered)
        }


class IntelligentAssistantSystem:
    """
    Master system coordinating all intelligent features.
    
    Integrates:
    - Intelligent Organizer
    - TimeKeeper
    - Smart Linter
    - Test Guardian
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config = self._load_config(config_path)
        self.session_data = SessionData()
        self._initialized = False
        
        # Component placeholders - lazy loading
        self._organizer = None
        self._timekeeper = None
        self._linter = None
        self._test_guardian = None
        
        # State tracking
        self.active_tasks = {}
        self.notifications = []
        
        logger.info(f"Intelligent Assistant System initialized - Session: {self.session_data.session_id}")
    
    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """Load configuration from file or use defaults."""
        default_config = {
            "features": {
                "organizer": {"enabled": True, "auto_organize": True},
                "timekeeper": {"enabled": True, "pomodoro_duration": 25},
                "linter": {"enabled": True, "auto_fix": False},
                "test_guardian": {"enabled": True, "coverage_target": 80}
            },
            "notifications": {
                "break_reminders": True,
                "test_failures": True,
                "lint_errors": True,
                "organization_suggestions": True
            },
            "performance": {
                "max_concurrent_tasks": 5,
                "cache_size_mb": 100,
                "log_level": "INFO"
            }
        }
        
        if config_path and config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                # Merge with defaults
                return {**default_config, **user_config}
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
        
        return default_config
    
    @property
    def organizer(self):
        """Lazy load organizer component."""
        if self._organizer is None and self.config["features"]["organizer"]["enabled"]:
            from .organizer import IntelligentOrganizer
            self._organizer = IntelligentOrganizer(self.config["features"]["organizer"])
        return self._organizer
    
    @property
    def timekeeper(self):
        """Lazy load timekeeper component."""
        if self._timekeeper is None and self.config["features"]["timekeeper"]["enabled"]:
            from .timekeeper import TimeKeeper
            self._timekeeper = TimeKeeper(self.config["features"]["timekeeper"])
        return self._timekeeper
    
    @property
    def linter(self):
        """Lazy load linter component."""
        if self._linter is None and self.config["features"]["linter"]["enabled"]:
            from .linter import SmartLinter
            self._linter = SmartLinter(self.config["features"]["linter"])
        return self._linter
    
    @property
    def test_guardian(self):
        """Lazy load test guardian component."""
        if self._test_guardian is None and self.config["features"]["test_guardian"]["enabled"]:
            from .test_guardian import TestGuardian
            self._test_guardian = TestGuardian(self.config["features"]["test_guardian"])
        return self._test_guardian
    
    def initialize(self):
        """Initialize all enabled components."""
        if self._initialized:
            return
        
        logger.info("Initializing Intelligent Assistant components...")
        
        # Initialize enabled components
        if self.organizer:
            self.organizer.initialize()
        if self.timekeeper:
            self.timekeeper.initialize()
        if self.linter:
            self.linter.initialize()
        if self.test_guardian:
            self.test_guardian.initialize()
        
        self._initialized = True
        logger.info("All components initialized successfully")
    
    def hook_pre_task(self, task_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pre-task hook combining all systems.
        
        Args:
            task_info: Information about the task to be executed
            
        Returns:
            Enhanced task info with pre-processing data
        """
        self.initialize()
        
        task_id = task_info.get("id", f"task_{int(time.time())}")
        self.active_tasks[task_id] = {
            "start_time": datetime.now(),
            "info": task_info,
            "status": "preparing"
        }
        
        enhanced_info = task_info.copy()
        
        # Timekeeper checks
        if self.timekeeper:
            time_check = self.timekeeper.check_work_session()
            if time_check.get("break_needed"):
                self._add_notification("break_reminder", time_check)
            
            timing_suggestion = self.timekeeper.suggest_task_timing(task_info)
            enhanced_info["timing_suggestion"] = timing_suggestion
        
        # Organizer prepares workspace
        if self.organizer:
            workspace_prep = self.organizer.prepare_workspace(task_info)
            enhanced_info["workspace_preparation"] = workspace_prep
            
            dependency_check = self.organizer.check_dependencies(task_info)
            if dependency_check.get("missing_dependencies"):
                self._add_notification("missing_dependencies", dependency_check)
        
        # Linter prepares rules
        if self.linter:
            self.linter.load_project_rules()
            enhanced_info["lint_rules_loaded"] = True
        
        self.active_tasks[task_id]["status"] = "ready"
        logger.info(f"Pre-task processing complete for task {task_id}")
        
        return enhanced_info
    
    def hook_post_task(self, task_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post-task hook for all systems.
        
        Args:
            task_result: Result from task execution
            
        Returns:
            Enhanced result with post-processing data
        """
        task_id = task_result.get("id", "unknown")
        
        if task_id in self.active_tasks:
            self.active_tasks[task_id]["end_time"] = datetime.now()
            self.active_tasks[task_id]["status"] = "completed"
        
        enhanced_result = task_result.copy()
        
        # Organizer updates
        if self.organizer:
            org_updates = self.organizer.update_project_structure(task_result)
            doc_updates = self.organizer.update_documentation(task_result)
            enhanced_result["organization_updates"] = {
                "structure": org_updates,
                "documentation": doc_updates
            }
        
        # Timekeeper records
        if self.timekeeper:
            self.timekeeper.record_task_completion(task_result)
            time_metrics = self.timekeeper.get_task_metrics(task_id)
            enhanced_result["time_metrics"] = time_metrics
        
        # Linter checks
        if self.linter:
            lint_results = self.linter.check_modified_files(task_result)
            enhanced_result["lint_results"] = lint_results
            
            if lint_results.get("errors"):
                self._add_notification("lint_errors", lint_results)
            
            # Auto-fix if enabled
            if self.config["features"]["linter"]["auto_fix"]:
                fixes = self.linter.auto_fix_issues(lint_results)
                enhanced_result["auto_fixes"] = fixes
        
        # Test Guardian ensures tests run
        if self.test_guardian:
            test_results = self.test_guardian.handle_test_files(task_result)
            enhanced_result["test_results"] = test_results
            
            if test_results.get("failures"):
                self._add_notification("test_failures", test_results)
        
        # Update session data
        self.session_data.add_task(task_result)
        if task_result.get("files_modified"):
            self.session_data.files_modified.extend(task_result["files_modified"])
        
        logger.info(f"Post-task processing complete for task {task_id}")
        
        return enhanced_result
    
    def hook_error(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handle errors intelligently."""
        self.session_data.add_error(error_info)
        
        enhanced_error = error_info.copy()
        
        # Analyze error for common patterns
        error_type = error_info.get("type", "unknown")
        error_message = error_info.get("message", "")
        
        suggestions = []
        
        # Common error patterns and suggestions
        if "permission denied" in error_message.lower():
            suggestions.append("Check file permissions and ownership")
        elif "module not found" in error_message.lower():
            suggestions.append("Verify dependencies are installed")
            suggestions.append("Check virtual environment activation")
        elif "syntax error" in error_message.lower():
            if self.linter:
                lint_check = self.linter.quick_syntax_check(error_info.get("file"))
                suggestions.extend(lint_check.get("suggestions", []))
        
        enhanced_error["suggestions"] = suggestions
        
        return enhanced_error
    
    def get_status_report(self) -> Dict[str, Any]:
        """Generate comprehensive status report."""
        report = {
            "session": self.session_data.get_session_summary(),
            "active_tasks": len(self.active_tasks),
            "notifications": len(self.notifications),
            "component_status": {}
        }
        
        # Component status
        if self.organizer:
            report["component_status"]["organizer"] = self.organizer.get_status()
        if self.timekeeper:
            report["component_status"]["timekeeper"] = self.timekeeper.get_status()
        if self.linter:
            report["component_status"]["linter"] = self.linter.get_status()
        if self.test_guardian:
            report["component_status"]["test_guardian"] = self.test_guardian.get_status()
        
        return report
    
    def _add_notification(self, notification_type: str, data: Dict[str, Any]):
        """Add a notification to the queue."""
        if self.config["notifications"].get(notification_type, True):
            self.notifications.append({
                "type": notification_type,
                "timestamp": datetime.now().isoformat(),
                "data": data
            })
    
    def get_notifications(self, clear: bool = True) -> List[Dict[str, Any]]:
        """Get pending notifications."""
        notifications = self.notifications.copy()
        if clear:
            self.notifications.clear()
        return notifications
    
    def shutdown(self):
        """Clean shutdown of all components."""
        logger.info("Shutting down Intelligent Assistant System...")
        
        # Save session data
        session_summary = self.session_data.get_session_summary()
        
        # Shutdown components
        if self._organizer:
            self._organizer.shutdown()
        if self._timekeeper:
            self._timekeeper.shutdown()
        if self._linter:
            self._linter.shutdown()
        if self._test_guardian:
            self._test_guardian.shutdown()
        
        logger.info(f"Session {self.session_data.session_id} ended - Duration: {session_summary['duration']}")
        
        return session_summary