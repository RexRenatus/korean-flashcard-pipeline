"""
Test file for IntelligentAssistantSystem core module
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path
import json

from src.python.flashcard_pipeline.intelligent_assistant.core import (
    IntelligentAssistantSystem,
    SessionData
)


class TestSessionData(unittest.TestCase):
    """Test cases for SessionData class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.session_data = SessionData()
    
    def test_session_data_creation(self):
        """Test SessionData class instantiation"""
        self.assertIsNotNone(self.session_data)
        self.assertIsNotNone(self.session_data.session_id)
        self.assertIsInstance(self.session_data.start_time, datetime)
        self.assertEqual(self.session_data.metrics["total_tasks"], 0)
    
    def test_update_metric(self):
        """Test metric updating"""
        self.session_data.update_metric("total_tasks", 5)
        self.assertEqual(self.session_data.metrics["total_tasks"], 5)
        
        # Test incremental update
        self.session_data.update_metric("files_created")
        self.assertEqual(self.session_data.metrics["files_created"], 1)
    
    def test_add_task(self):
        """Test adding task to session"""
        task_info = {"id": "test_task", "type": "test"}
        self.session_data.add_task(task_info)
        
        self.assertEqual(len(self.session_data.tasks_completed), 1)
        self.assertEqual(self.session_data.metrics["total_tasks"], 1)
    
    def test_add_error(self):
        """Test error recording"""
        error_info = {"type": "test_error", "message": "Test error"}
        self.session_data.add_error(error_info)
        
        self.assertEqual(len(self.session_data.errors_encountered), 1)
    
    def test_session_summary(self):
        """Test session summary generation"""
        # Add some data
        self.session_data.add_task({"id": "task1"})
        self.session_data.add_error({"type": "error1"})
        
        summary = self.session_data.get_session_summary()
        
        self.assertIn("session_id", summary)
        self.assertIn("duration", summary)
        self.assertIn("metrics", summary)
        self.assertEqual(summary["tasks_completed"], 1)
        self.assertEqual(summary["errors_count"], 1)


class TestIntelligentAssistantSystem(unittest.TestCase):
    """Test cases for IntelligentAssistantSystem"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.assistant = IntelligentAssistantSystem()
    
    def tearDown(self):
        """Clean up after tests"""
        # Ensure assistant is shut down
        if hasattr(self, 'assistant') and self.assistant:
            self.assistant.shutdown()
    
    def test_assistant_creation(self):
        """Test IntelligentAssistantSystem instantiation"""
        self.assertIsNotNone(self.assistant)
        self.assertIsNotNone(self.assistant.session_data)
        self.assertFalse(self.assistant._initialized)
    
    def test_load_config_default(self):
        """Test default configuration loading"""
        config = self.assistant._load_config(None)
        
        self.assertIn("features", config)
        self.assertIn("notifications", config)
        self.assertIn("performance", config)
        self.assertTrue(config["features"]["organizer"]["enabled"])
    
    def test_load_config_from_file(self):
        """Test configuration loading from file"""
        # Create a temporary config file
        test_config = {
            "features": {
                "organizer": {"enabled": False}
            }
        }
        
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(test_config)
            
            config_path = Path("test_config.json")
            with patch.object(Path, "exists", return_value=True):
                config = self.assistant._load_config(config_path)
                
                # Should merge with defaults
                self.assertFalse(config["features"]["organizer"]["enabled"])
                self.assertIn("notifications", config)  # From defaults
    
    @patch('src.python.flashcard_pipeline.intelligent_assistant.organizer.IntelligentOrganizer')
    def test_lazy_loading_organizer(self, mock_organizer_class):
        """Test lazy loading of organizer component"""
        mock_organizer = Mock()
        mock_organizer_class.return_value = mock_organizer
        
        # Should be None initially
        self.assertIsNone(self.assistant._organizer)
        
        # Access property
        organizer = self.assistant.organizer
        
        # Should create instance
        self.assertIsNotNone(organizer)
        mock_organizer_class.assert_called_once()
    
    def test_initialize(self):
        """Test system initialization"""
        with patch.object(self.assistant, 'organizer') as mock_organizer:
            with patch.object(self.assistant, 'timekeeper') as mock_timekeeper:
                with patch.object(self.assistant, 'linter') as mock_linter:
                    with patch.object(self.assistant, 'test_guardian') as mock_guardian:
                        self.assistant.initialize()
                        
                        self.assertTrue(self.assistant._initialized)
                        mock_organizer.initialize.assert_called_once()
                        mock_timekeeper.initialize.assert_called_once()
                        mock_linter.initialize.assert_called_once()
                        mock_guardian.initialize.assert_called_once()
    
    def test_hook_pre_task(self):
        """Test pre-task hook processing"""
        task_info = {
            "id": "test_task",
            "type": "test",
            "parameters": {"test": True}
        }
        
        with patch.object(self.assistant, 'timekeeper') as mock_timekeeper:
            with patch.object(self.assistant, 'organizer') as mock_organizer:
                mock_timekeeper.check_work_session.return_value = {"break_needed": False}
                mock_timekeeper.suggest_task_timing.return_value = {"recommendation": "PROCEED"}
                mock_organizer.prepare_workspace.return_value = {"directories_created": []}
                mock_organizer.check_dependencies.return_value = {"missing_dependencies": []}
                
                result = self.assistant.hook_pre_task(task_info)
                
                self.assertIn("timing_suggestion", result)
                self.assertIn("workspace_preparation", result)
                self.assertTrue(self.assistant._initialized)
    
    def test_hook_post_task(self):
        """Test post-task hook processing"""
        task_result = {
            "id": "test_task",
            "success": True,
            "modified_files": ["test.py"],
            "new_files": []
        }
        
        with patch.object(self.assistant, 'organizer') as mock_organizer:
            with patch.object(self.assistant, 'timekeeper') as mock_timekeeper:
                with patch.object(self.assistant, 'linter') as mock_linter:
                    with patch.object(self.assistant, 'test_guardian') as mock_guardian:
                        mock_organizer.update_project_structure.return_value = {}
                        mock_organizer.update_documentation.return_value = {}
                        mock_linter.check_modified_files.return_value = {"errors": [], "warnings": []}
                        mock_guardian.handle_test_files.return_value = {"tests_run": [], "failures": []}
                        
                        result = self.assistant.hook_post_task(task_result)
                        
                        self.assertIn("lint_results", result)
                        self.assertIn("test_results", result)
                        self.assertIn("organization_updates", result)
                        self.assertEqual(self.assistant.session_data.metrics["total_tasks"], 1)
    
    def test_hook_error(self):
        """Test error hook processing"""
        error_info = {
            "type": "permission_error",
            "message": "Permission denied accessing file"
        }
        
        result = self.assistant.hook_error(error_info)
        
        self.assertIn("suggestions", result)
        self.assertGreater(len(result["suggestions"]), 0)
        self.assertEqual(len(self.assistant.session_data.errors_encountered), 1)
    
    def test_get_status_report(self):
        """Test status report generation"""
        # Add some data
        self.assistant.session_data.add_task({"id": "task1"})
        
        with patch.object(self.assistant, 'organizer') as mock_organizer:
            mock_organizer.get_status.return_value = {"total_files": 10}
            
            report = self.assistant.get_status_report()
            
            self.assertIn("session", report)
            self.assertIn("active_tasks", report)
            self.assertIn("component_status", report)
            self.assertEqual(report["session"]["tasks_completed"], 1)
    
    def test_add_notification(self):
        """Test notification system"""
        self.assistant._add_notification("test_notification", {"data": "test"})
        
        self.assertEqual(len(self.assistant.notifications), 1)
        self.assertEqual(self.assistant.notifications[0]["type"], "test_notification")
    
    def test_get_notifications(self):
        """Test getting and clearing notifications"""
        self.assistant._add_notification("test1", {})
        self.assistant._add_notification("test2", {})
        
        # Get with clear
        notifications = self.assistant.get_notifications(clear=True)
        self.assertEqual(len(notifications), 2)
        self.assertEqual(len(self.assistant.notifications), 0)
        
        # Get without clear
        self.assistant._add_notification("test3", {})
        notifications = self.assistant.get_notifications(clear=False)
        self.assertEqual(len(notifications), 1)
        self.assertEqual(len(self.assistant.notifications), 1)
    
    def test_shutdown(self):
        """Test system shutdown"""
        with patch.object(self.assistant, '_organizer') as mock_organizer:
            self.assistant._organizer = mock_organizer  # Set it as initialized
            
            summary = self.assistant.shutdown()
            
            self.assertIn("session", summary)
            self.assertIn("duration", summary["session"])
            mock_organizer.shutdown.assert_called_once()


if __name__ == '__main__':
    unittest.main()