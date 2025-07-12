#!/usr/bin/env python3
"""
Notification Manager for Hook System
Provides non-blocking notifications for hook events.
Inspired by Claude Code Development Kit's notification approach.
"""
import os
import sys
import json
import asyncio
import subprocess
import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from datetime import datetime
from enum import Enum
import threading
import queue

class NotificationType(Enum):
    """Types of notifications."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    PERFORMANCE = "performance"
    TASK_COMPLETE = "task_complete"
    HOOK_VIOLATION = "hook_violation"

class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class NotificationManager:
    """
    Manages notifications for the hook system.
    Provides async, non-blocking notifications with multiple channels.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._load_default_config()
        self.logger = logging.getLogger(__name__)
        self.notification_queue = queue.Queue()
        self.enabled = self.config.get('enabled', True)
        
        # Start background notification worker
        if self.enabled:
            self._start_notification_worker()
            
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default notification configuration."""
        return {
            'enabled': True,
            'channels': {
                'console': {'enabled': True, 'min_priority': 'medium'},
                'sound': {'enabled': False, 'min_priority': 'high'},
                'file': {'enabled': True, 'path': '.claude/logs/notifications.log'},
                'system': {'enabled': False, 'min_priority': 'critical'}
            },
            'sound_files': {
                'success': 'scripts/hooks/sounds/success.wav',
                'warning': 'scripts/hooks/sounds/warning.wav',
                'error': 'scripts/hooks/sounds/error.wav',
                'task_complete': 'scripts/hooks/sounds/complete.wav'
            },
            'rate_limit': {
                'enabled': True,
                'max_per_minute': 10,
                'burst_size': 3
            }
        }
        
    def _start_notification_worker(self):
        """Start background thread for processing notifications."""
        self.worker_thread = threading.Thread(
            target=self._notification_worker,
            daemon=True
        )
        self.worker_thread.start()
        
    def _notification_worker(self):
        """Background worker to process notifications."""
        while True:
            try:
                notification = self.notification_queue.get(timeout=1)
                if notification is None:  # Shutdown signal
                    break
                self._process_notification(notification)
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Notification worker error: {e}")
                
    def notify(self, 
              message: str,
              notification_type: NotificationType = NotificationType.INFO,
              priority: NotificationPriority = NotificationPriority.MEDIUM,
              context: Optional[Dict[str, Any]] = None,
              **kwargs):
        """
        Send a notification synchronously.
        """
        if not self.enabled:
            return
            
        notification = {
            'message': message,
            'type': notification_type,
            'priority': priority,
            'context': context or {},
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        
        self._process_notification(notification)
        
    def notify_async(self,
                    message: str,
                    notification_type: Union[NotificationType, str] = NotificationType.INFO,
                    priority: Union[NotificationPriority, str] = NotificationPriority.MEDIUM,
                    context: Optional[Dict[str, Any]] = None,
                    **kwargs):
        """
        Send a notification asynchronously (non-blocking).
        """
        if not self.enabled:
            return
            
        # Convert string types to enums if needed
        if isinstance(notification_type, str):
            notification_type = NotificationType(notification_type)
        if isinstance(priority, str):
            priority = NotificationPriority[priority.upper()]
            
        notification = {
            'message': message,
            'type': notification_type,
            'priority': priority,
            'context': context or {},
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        
        # Add to queue for async processing
        try:
            self.notification_queue.put_nowait(notification)
        except queue.Full:
            self.logger.warning("Notification queue full, dropping notification")
            
    def _process_notification(self, notification: Dict[str, Any]):
        """Process a notification through enabled channels."""
        priority = notification['priority']
        
        # Check each channel
        for channel, config in self.config['channels'].items():
            if not config.get('enabled', False):
                continue
                
            # Check minimum priority
            min_priority = NotificationPriority[config.get('min_priority', 'low').upper()]
            if priority.value < min_priority.value:
                continue
                
            # Route to appropriate handler
            if channel == 'console':
                self._notify_console(notification)
            elif channel == 'sound':
                self._notify_sound(notification)
            elif channel == 'file':
                self._notify_file(notification)
            elif channel == 'system':
                self._notify_system(notification)
                
    def _notify_console(self, notification: Dict[str, Any]):
        """Send notification to console."""
        # Color codes for different types
        colors = {
            NotificationType.INFO: '\033[94m',      # Blue
            NotificationType.SUCCESS: '\033[92m',   # Green
            NotificationType.WARNING: '\033[93m',   # Yellow
            NotificationType.ERROR: '\033[91m',     # Red
            NotificationType.PERFORMANCE: '\033[95m', # Magenta
            NotificationType.TASK_COMPLETE: '\033[92m', # Green
            NotificationType.HOOK_VIOLATION: '\033[91m'  # Red
        }
        
        # Icons for different types
        icons = {
            NotificationType.INFO: 'ℹ️',
            NotificationType.SUCCESS: '✅',
            NotificationType.WARNING: '⚠️',
            NotificationType.ERROR: '❌',
            NotificationType.PERFORMANCE: '📊',
            NotificationType.TASK_COMPLETE: '🎉',
            NotificationType.HOOK_VIOLATION: '🚨'
        }
        
        color = colors.get(notification['type'], '')
        icon = icons.get(notification['type'], '•')
        reset = '\033[0m'
        
        # Format message
        message = f"{color}{icon} {notification['message']}{reset}"
        
        # Add context if verbose
        if os.environ.get('CLAUDE_VERBOSITY') == 'verbose' and notification.get('context'):
            message += f"\n   Context: {json.dumps(notification['context'], indent=2)}"
            
        print(message, file=sys.stderr)
        
    def _notify_sound(self, notification: Dict[str, Any]):
        """Play notification sound."""
        sound_files = self.config.get('sound_files', {})
        sound_file = sound_files.get(notification['type'].value)
        
        if not sound_file or not Path(sound_file).exists():
            return
            
        try:
            # Try different sound players based on platform
            if sys.platform == 'darwin':  # macOS
                subprocess.run(['afplay', sound_file], capture_output=True)
            elif sys.platform == 'linux':
                # Try multiple players
                for player in ['aplay', 'paplay', 'play']:
                    if subprocess.run(['which', player], capture_output=True).returncode == 0:
                        subprocess.run([player, sound_file], capture_output=True)
                        break
            elif sys.platform == 'win32':
                import winsound
                winsound.PlaySound(sound_file, winsound.SND_FILENAME)
        except Exception as e:
            self.logger.debug(f"Failed to play sound: {e}")
            
    def _notify_file(self, notification: Dict[str, Any]):
        """Write notification to log file."""
        log_path = Path(self.config['channels']['file'].get('path', '.claude/logs/notifications.log'))
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                log_entry = {
                    'timestamp': notification['timestamp'],
                    'type': notification['type'].value,
                    'priority': notification['priority'].name,
                    'message': notification['message'],
                    'context': notification.get('context', {})
                }
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to write notification to file: {e}")
            
    def _notify_system(self, notification: Dict[str, Any]):
        """Send system notification (OS-specific)."""
        try:
            message = notification['message']
            title = f"Claude Code - {notification['type'].value.title()}"
            
            if sys.platform == 'darwin':  # macOS
                script = f'display notification "{message}" with title "{title}"'
                subprocess.run(['osascript', '-e', script], capture_output=True)
            elif sys.platform == 'linux':
                subprocess.run(['notify-send', title, message], capture_output=True)
            elif sys.platform == 'win32':
                # Windows notifications require additional setup
                pass
        except Exception as e:
            self.logger.debug(f"Failed to send system notification: {e}")
            
    def notify_hook_start(self, hook_id: str, context: Dict[str, Any]):
        """Notify when a hook starts execution."""
        if os.environ.get('CLAUDE_VERBOSITY') == 'verbose':
            self.notify_async(
                f"Starting hook: {hook_id}",
                NotificationType.INFO,
                NotificationPriority.LOW,
                context={'hook_id': hook_id, 'file': context.get('file_path')}
            )
            
    def notify_hook_complete(self, hook_id: str, success: bool, execution_time: float):
        """Notify when a hook completes."""
        if execution_time > 5.0:  # Long-running hook
            self.notify_async(
                f"Hook {hook_id} completed in {execution_time:.1f}s",
                NotificationType.SUCCESS if success else NotificationType.WARNING,
                NotificationPriority.MEDIUM,
                context={'hook_id': hook_id, 'execution_time': execution_time}
            )
            
    def notify_performance_violation(self, hook_id: str, violations: List[str]):
        """Notify about performance violations."""
        self.notify_async(
            f"Performance violations in {hook_id}: {', '.join(violations)}",
            NotificationType.PERFORMANCE,
            NotificationPriority.HIGH,
            context={'hook_id': hook_id, 'violations': violations}
        )
        
    def notify_security_issue(self, file_path: str, issues: List[Dict[str, Any]]):
        """Notify about security issues found."""
        critical_count = sum(1 for i in issues if i.get('severity') == 'critical')
        if critical_count > 0:
            self.notify_async(
                f"🚨 {critical_count} critical security issues found in {Path(file_path).name}",
                NotificationType.HOOK_VIOLATION,
                NotificationPriority.CRITICAL,
                context={'file': file_path, 'issues': issues[:3]}  # First 3 issues
            )
            
    def notify_task_complete(self, task_description: str, duration: float):
        """Notify when a major task completes."""
        self.notify_async(
            f"Task completed: {task_description} ({duration:.1f}s)",
            NotificationType.TASK_COMPLETE,
            NotificationPriority.MEDIUM,
            context={'task': task_description, 'duration': duration},
            sound='task_complete'
        )
        
    def shutdown(self):
        """Shutdown the notification manager."""
        if self.enabled:
            self.notification_queue.put(None)  # Signal worker to stop
            self.worker_thread.join(timeout=2)

# Global notification manager instance
_notification_manager = None

def get_notification_manager(config: Optional[Dict[str, Any]] = None) -> NotificationManager:
    """Get global notification manager instance."""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager(config)
    return _notification_manager

# Example usage
if __name__ == "__main__":
    # Test notifications
    manager = NotificationManager({
        'channels': {
            'console': {'enabled': True, 'min_priority': 'low'},
            'file': {'enabled': True, 'path': 'test_notifications.log'}
        }
    })
    
    # Test different notification types
    manager.notify("This is an info message", NotificationType.INFO)
    manager.notify("Task completed successfully!", NotificationType.SUCCESS)
    manager.notify("Performance threshold exceeded", NotificationType.WARNING)
    manager.notify("Critical error detected", NotificationType.ERROR, NotificationPriority.CRITICAL)
    
    # Test async notifications
    manager.notify_async("Async notification 1", NotificationType.INFO)
    manager.notify_async("Async notification 2", NotificationType.SUCCESS)
    
    # Test specific notifications
    manager.notify_hook_complete("test_hook", True, 6.5)
    manager.notify_performance_violation("slow_hook", ["Execution time: 15s", "Memory: 500MB"])
    
    # Wait for async notifications
    import time
    time.sleep(1)
    
    # Shutdown
    manager.shutdown()
    print("\nNotification test complete!")