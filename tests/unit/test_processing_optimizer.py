"""Unit tests for the ProcessingOptimizer class"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import time
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any

from src.python.flashcard_pipeline.processing_optimizer import (
    ProcessingOptimizer,
    ProcessingMetrics,
    ProcessingCheckpoint,
    ProcessingStatus
)
from src.python.flashcard_pipeline.database.db_manager import VocabularyRecord
from src.python.flashcard_pipeline.models import BatchProgress
from src.python.flashcard_pipeline.exceptions import ProcessingError


class TestProcessingMetrics(unittest.TestCase):
    """Test the ProcessingMetrics dataclass"""
    
    def test_metrics_initialization(self):
        """Test metrics initialization with default values"""
        metrics = ProcessingMetrics()
        
        self.assertIsInstance(metrics.start_time, datetime)
        self.assertIsNone(metrics.end_time)
        self.assertEqual(metrics.total_items, 0)
        self.assertEqual(metrics.processed_items, 0)
        self.assertEqual(metrics.successful_items, 0)
        self.assertEqual(metrics.failed_items, 0)
        self.assertEqual(metrics.cache_hits, 0)
        self.assertEqual(metrics.cache_misses, 0)
        self.assertEqual(metrics.total_api_calls, 0)
        self.assertEqual(metrics.total_tokens, 0)
        self.assertEqual(metrics.total_cost, 0.0)
        self.assertEqual(metrics.avg_latency_ms, 0.0)
        self.assertEqual(len(metrics.errors), 0)
    
    def test_duration_calculation(self):
        """Test duration calculation"""
        metrics = ProcessingMetrics()
        time.sleep(0.1)  # Sleep for 100ms
        
        duration = metrics.duration_seconds
        self.assertGreater(duration, 0.09)  # Should be at least 90ms
        
        # Test with end time
        metrics.end_time = metrics.start_time + timedelta(seconds=5)
        self.assertEqual(metrics.duration_seconds, 5.0)
    
    def test_throughput_calculation(self):
        """Test throughput calculation"""
        metrics = ProcessingMetrics()
        metrics.start_time = datetime.now() - timedelta(seconds=10)
        metrics.processed_items = 100
        
        self.assertAlmostEqual(metrics.throughput, 10.0, places=1)
        
        # Test zero duration
        metrics.start_time = datetime.now()
        self.assertEqual(metrics.throughput, 0.0)
    
    def test_success_rate_calculation(self):
        """Test success rate calculation"""
        metrics = ProcessingMetrics()
        
        # Test zero processed
        self.assertEqual(metrics.success_rate, 0.0)
        
        # Test with data
        metrics.processed_items = 100
        metrics.successful_items = 95
        self.assertEqual(metrics.success_rate, 95.0)
    
    def test_cache_hit_rate_calculation(self):
        """Test cache hit rate calculation"""
        metrics = ProcessingMetrics()
        
        # Test zero lookups
        self.assertEqual(metrics.cache_hit_rate, 0.0)
        
        # Test with data
        metrics.cache_hits = 30
        metrics.cache_misses = 70
        self.assertEqual(metrics.cache_hit_rate, 30.0)
    
    def test_to_dict(self):
        """Test conversion to dictionary"""
        metrics = ProcessingMetrics()
        metrics.processed_items = 10
        metrics.successful_items = 8
        metrics.failed_items = 2
        
        result = metrics.to_dict()
        
        self.assertIsInstance(result, dict)
        self.assertIn("start_time", result)
        self.assertIn("duration_seconds", result)
        self.assertEqual(result["processed_items"], 10)
        self.assertEqual(result["successful_items"], 8)
        self.assertEqual(result["failed_items"], 2)
        self.assertEqual(result["success_rate"], 80.0)


class TestProcessingCheckpoint(unittest.TestCase):
    """Test the ProcessingCheckpoint dataclass"""
    
    def test_checkpoint_serialization(self):
        """Test checkpoint to/from JSON"""
        metrics = ProcessingMetrics()
        metrics.processed_items = 50
        metrics.successful_items = 48
        
        checkpoint = ProcessingCheckpoint(
            checkpoint_id="test_checkpoint_123",
            batch_id="batch_20240101_120000_abcdef12",
            timestamp=datetime.now(),
            processed_items=[1, 2, 3, 4, 5],
            pending_items=[6, 7, 8, 9, 10],
            metrics=metrics,
            stage="stage1",
            metadata={"test": "data"}
        )
        
        # Serialize to JSON
        json_str = checkpoint.to_json()
        self.assertIsInstance(json_str, str)
        
        # Deserialize from JSON
        restored = ProcessingCheckpoint.from_json(json_str)
        
        self.assertEqual(restored.checkpoint_id, checkpoint.checkpoint_id)
        self.assertEqual(restored.batch_id, checkpoint.batch_id)
        self.assertEqual(restored.processed_items, checkpoint.processed_items)
        self.assertEqual(restored.pending_items, checkpoint.pending_items)
        self.assertEqual(restored.stage, checkpoint.stage)
        self.assertEqual(restored.metadata, checkpoint.metadata)
        self.assertEqual(restored.metrics.processed_items, 50)
        self.assertEqual(restored.metrics.successful_items, 48)


class TestProcessingOptimizer(unittest.TestCase):
    """Test the ProcessingOptimizer class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock()
        self.optimizer = ProcessingOptimizer(
            db_manager=self.mock_db_manager,
            max_workers=2,
            batch_size=5,
            checkpoint_interval=10,
            enable_metrics=True
        )
    
    def test_initialization(self):
        """Test optimizer initialization"""
        self.assertEqual(self.optimizer.max_workers, 2)
        self.assertEqual(self.optimizer.batch_size, 5)
        self.assertEqual(self.optimizer.checkpoint_interval, 10)
        self.assertTrue(self.optimizer.enable_metrics)
        self.assertIsNone(self.optimizer._current_batch_id)
        self.assertIsNone(self.optimizer._metrics)
        self.assertEqual(len(self.optimizer._progress_callbacks), 0)
        self.assertEqual(len(self.optimizer._error_callbacks), 0)
    
    def test_generate_batch_id(self):
        """Test batch ID generation"""
        batch_id = self.optimizer.generate_batch_id()
        
        self.assertIsInstance(batch_id, str)
        self.assertTrue(batch_id.startswith("batch_"))
        self.assertGreater(len(batch_id), 20)
        
        # Test uniqueness
        batch_id2 = self.optimizer.generate_batch_id()
        self.assertNotEqual(batch_id, batch_id2)
    
    def test_callback_management(self):
        """Test adding and calling callbacks"""
        progress_called = False
        error_called = False
        
        def progress_callback(progress: BatchProgress):
            nonlocal progress_called
            progress_called = True
        
        def error_callback(error_info: Dict[str, Any]):
            nonlocal error_called
            error_called = True
        
        self.optimizer.add_progress_callback(progress_callback)
        self.optimizer.add_error_callback(error_callback)
        
        self.assertEqual(len(self.optimizer._progress_callbacks), 1)
        self.assertEqual(len(self.optimizer._error_callbacks), 1)
        
        # Test notifications
        progress = BatchProgress(
            batch_id="test",
            total_items=10,
            completed_items=5,
            failed_items=0,
            current_stage="stage1",
            started_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.optimizer._notify_progress(progress)
        self.assertTrue(progress_called)
        
        self.optimizer._notify_error({"error": "test error"})
        self.assertTrue(error_called)
    
    def test_metrics_update(self):
        """Test metrics update functionality"""
        self.optimizer._metrics = ProcessingMetrics()
        
        # Test successful update
        self.optimizer._update_metrics(
            success=True,
            cache_hit=False,
            api_calls=1,
            tokens=1000,
            cost=0.05,
            latency_ms=150.0
        )
        
        self.assertEqual(self.optimizer._metrics.processed_items, 1)
        self.assertEqual(self.optimizer._metrics.successful_items, 1)
        self.assertEqual(self.optimizer._metrics.failed_items, 0)
        self.assertEqual(self.optimizer._metrics.cache_hits, 0)
        self.assertEqual(self.optimizer._metrics.cache_misses, 1)
        self.assertEqual(self.optimizer._metrics.total_api_calls, 1)
        self.assertEqual(self.optimizer._metrics.total_tokens, 1000)
        self.assertEqual(self.optimizer._metrics.total_cost, 0.05)
        self.assertEqual(self.optimizer._metrics.avg_latency_ms, 150.0)
        
        # Test failed update
        self.optimizer._update_metrics(
            success=False,
            error=Exception("Test error")
        )
        
        self.assertEqual(self.optimizer._metrics.processed_items, 2)
        self.assertEqual(self.optimizer._metrics.successful_items, 1)
        self.assertEqual(self.optimizer._metrics.failed_items, 1)
        self.assertEqual(len(self.optimizer._metrics.errors), 1)
    
    def test_checkpoint_creation(self):
        """Test checkpoint creation"""
        self.optimizer._current_batch_id = "test_batch_123"
        self.optimizer._metrics = ProcessingMetrics()
        
        checkpoint = self.optimizer._create_checkpoint(
            processed_ids=[1, 2, 3],
            pending_ids=[4, 5, 6],
            stage="stage1"
        )
        
        self.assertIsInstance(checkpoint, ProcessingCheckpoint)
        self.assertEqual(checkpoint.batch_id, "test_batch_123")
        self.assertEqual(checkpoint.processed_items, [1, 2, 3])
        self.assertEqual(checkpoint.pending_items, [4, 5, 6])
        self.assertEqual(checkpoint.stage, "stage1")
        self.assertIn("batch_size", checkpoint.metadata)
        self.assertIn("max_workers", checkpoint.metadata)
    
    def test_checkpoint_save_and_load(self):
        """Test checkpoint saving and loading"""
        self.optimizer._current_batch_id = "test_batch_123"
        self.optimizer._metrics = ProcessingMetrics()
        
        checkpoint = self.optimizer._create_checkpoint(
            processed_ids=[1, 2, 3],
            pending_ids=[4, 5, 6],
            stage="stage1"
        )
        
        # Test save
        self.optimizer._save_checkpoint(checkpoint)
        
        # Verify database calls
        self.mock_db_manager.set_system_config.assert_called()
        call_args = self.mock_db_manager.set_system_config.call_args_list
        
        # Should have two calls - one for checkpoint, one for latest reference
        self.assertEqual(len(call_args), 2)
        
        # Test load
        self.mock_db_manager.get_system_config.return_value = checkpoint.to_json()
        
        loaded = self.optimizer.load_checkpoint("test_batch_123")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.batch_id, checkpoint.batch_id)
        self.assertEqual(loaded.processed_items, checkpoint.processed_items)
    
    def test_process_single_item(self):
        """Test processing a single vocabulary item"""
        vocab = VocabularyRecord(id=1, korean="안녕", english="hello")
        
        def mock_processor(v: VocabularyRecord) -> Tuple[bool, Dict[str, Any]]:
            return True, {
                "cache_hit": False,
                "api_calls": 1,
                "tokens": 500,
                "cost": 0.01
            }
        
        self.optimizer._metrics = ProcessingMetrics()
        
        vocab_id, success, result = self.optimizer._process_single_item(
            vocab, mock_processor
        )
        
        self.assertEqual(vocab_id, 1)
        self.assertTrue(success)
        self.assertIn("cache_hit", result)
        self.assertEqual(self.optimizer._metrics.processed_items, 1)
        self.assertEqual(self.optimizer._metrics.successful_items, 1)
        
        # Test with failure
        def failing_processor(v: VocabularyRecord) -> Tuple[bool, Dict[str, Any]]:
            raise Exception("Processing failed")
        
        vocab_id, success, result = self.optimizer._process_single_item(
            vocab, failing_processor
        )
        
        self.assertEqual(vocab_id, 1)
        self.assertFalse(success)
        self.assertIn("error", result)
        self.assertEqual(self.optimizer._metrics.failed_items, 1)
    
    def test_batch_size_optimization(self):
        """Test dynamic batch size optimization"""
        self.optimizer._metrics = ProcessingMetrics()
        self.optimizer._latency_samples = [50.0] * 100  # 50ms average
        self.optimizer._metrics.avg_latency_ms = 50.0
        
        # Target is 100ms, current is 50ms - should increase batch size
        new_size = self.optimizer.optimize_batch_size(target_latency_ms=100.0)
        self.assertGreater(new_size, self.optimizer.batch_size)
        
        # Reset and test slow performance
        self.optimizer.batch_size = 5
        self.optimizer._latency_samples = [200.0] * 100  # 200ms average
        self.optimizer._metrics.avg_latency_ms = 200.0
        
        # Target is 100ms, current is 200ms - should decrease batch size
        new_size = self.optimizer.optimize_batch_size(target_latency_ms=100.0)
        self.assertLess(new_size, 5)
    
    def test_metrics_summary(self):
        """Test getting metrics summary"""
        # Test with no metrics
        summary = self.optimizer.get_metrics_summary()
        self.assertEqual(summary, {})
        
        # Test with metrics
        self.optimizer._metrics = ProcessingMetrics()
        self.optimizer._metrics.processed_items = 100
        self.optimizer._metrics.successful_items = 95
        
        summary = self.optimizer.get_metrics_summary()
        self.assertIsInstance(summary, dict)
        self.assertEqual(summary["processed_items"], 100)
        self.assertEqual(summary["successful_items"], 95)
        self.assertEqual(summary["success_rate"], 95.0)
    
    def test_reset_metrics(self):
        """Test resetting metrics"""
        self.optimizer._metrics = ProcessingMetrics()
        self.optimizer._metrics.processed_items = 100
        self.optimizer._latency_samples = [100.0, 200.0, 300.0]
        
        self.optimizer.reset_metrics()
        
        self.assertEqual(self.optimizer._metrics.processed_items, 0)
        self.assertEqual(len(self.optimizer._latency_samples), 0)


if __name__ == "__main__":
    unittest.main()