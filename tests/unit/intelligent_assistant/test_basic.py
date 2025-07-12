"""
Basic tests for Intelligent Assistant System
"""

import unittest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.python.flashcard_pipeline.intelligent_assistant import (
    IntelligentAssistantSystem,
    SessionData
)


class TestBasicFunctionality(unittest.TestCase):
    """Basic tests that should work without complex dependencies"""
    
    def test_session_data_creation(self):
        """Test basic SessionData creation"""
        session = SessionData()
        self.assertIsNotNone(session.session_id)
        self.assertIsNotNone(session.start_time)
        self.assertEqual(len(session.tasks_completed), 0)
        self.assertEqual(len(session.errors_encountered), 0)
    
    def test_session_data_metrics(self):
        """Test metric tracking"""
        session = SessionData()
        
        # Test initial state
        self.assertEqual(session.metrics["total_tasks"], 0)
        
        # Test metric update
        session.update_metric("total_tasks", 5)
        self.assertEqual(session.metrics["total_tasks"], 5)
        
        # Test increment
        session.update_metric("files_created")
        self.assertEqual(session.metrics["files_created"], 1)
    
    def test_assistant_creation(self):
        """Test basic assistant creation"""
        assistant = IntelligentAssistantSystem()
        self.assertIsNotNone(assistant)
        self.assertIsNotNone(assistant.session_data)
        self.assertIsNotNone(assistant.config)
    
    def test_assistant_config(self):
        """Test configuration structure"""
        assistant = IntelligentAssistantSystem()
        
        # Check config has expected keys
        self.assertIn("features", assistant.config)
        self.assertIn("notifications", assistant.config)
        self.assertIn("performance", assistant.config)
        
        # Check features
        features = assistant.config["features"]
        self.assertIn("organizer", features)
        self.assertIn("timekeeper", features)
        self.assertIn("linter", features)
        self.assertIn("test_guardian", features)
    
    def test_notification_system(self):
        """Test notification management"""
        assistant = IntelligentAssistantSystem()
        
        # Add notifications
        assistant._add_notification("test_type", {"message": "test"})
        self.assertEqual(len(assistant.notifications), 1)
        
        # Get notifications with clear
        notifications = assistant.get_notifications(clear=True)
        self.assertEqual(len(notifications), 1)
        self.assertEqual(len(assistant.notifications), 0)
    
    def test_error_handling(self):
        """Test basic error handling"""
        assistant = IntelligentAssistantSystem()
        
        error_info = {
            "type": "test_error",
            "message": "This is a test error"
        }
        
        result = assistant.hook_error(error_info)
        
        self.assertIn("suggestions", result)
        self.assertIsInstance(result["suggestions"], list)
        self.assertEqual(len(assistant.session_data.errors_encountered), 1)
    
    def test_status_report_structure(self):
        """Test status report generation"""
        assistant = IntelligentAssistantSystem()
        
        report = assistant.get_status_report()
        
        self.assertIn("session", report)
        self.assertIn("active_tasks", report)
        self.assertIn("notifications", report)
        self.assertIn("component_status", report)


if __name__ == '__main__':
    unittest.main()