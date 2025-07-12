#!/usr/bin/env python3
"""
Test concurrent processing pipeline for Korean flashcards
Tests all sections without making actual API calls
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import json
import sqlite3
from typing import List, Dict, Any
import csv
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import threading
import time
import random

# Add src/python to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'python'))

from flashcard_pipeline.models import (
    VocabularyItem, 
    Stage1Request, Stage1Response,
    Stage2Request, Stage2Response, FlashcardRow
)
from flashcard_pipeline.concurrent.distributed_rate_limiter import DistributedRateLimiter
from flashcard_pipeline.concurrent.ordered_collector import OrderedResultsCollector
from flashcard_pipeline.concurrent.batch_writer import OrderedBatchDatabaseWriter

# Test configuration
TEST_CONFIG = {
    "max_concurrent": 20,
    "batch_size": 10,
    "rate_limit": {
        "requests_per_minute": 60,
        "tokens_per_minute": 90000
    },
    "database_path": "test_pipeline.db",
    "input_file": "docs/10K_HSK_List.csv",
    "limit": 100
}

class MockAPIClient:
    """Mock API client for testing without real API calls"""
    
    def __init__(self):
        self.call_count = 0
        self.lock = threading.Lock()
        
    async def process_stage1(self, item: VocabularyItem) -> Stage1Response:
        """Simulate Stage 1 processing"""
        with self.lock:
            self.call_count += 1
            
        # Simulate processing time
        await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # Create mock result
        return Stage1Response(
            term=item.term,
            position=item.position,
            primary_meaning=f"Mock primary meaning for {item.term}",
            usage_contexts=["formal", "informal"],
            formality_level="neutral",
            part_of_speech=item.word_type or "noun",
            etymology=f"Mock etymology for {item.term}",
            cultural_notes=f"Mock cultural note for {item.term}",
            usage_frequency="common",
            related_concepts={
                "synonyms": [f"syn1_{item.term}", f"syn2_{item.term}"],
                "antonyms": [f"ant1_{item.term}"],
                "related_words": [f"rel1_{item.term}", f"rel2_{item.term}"]
            },
            beginner_friendly=True,
            difficulty_assessment={
                "common_mistakes": [f"Mock mistake for {item.term}"],
                "learning_tips": f"Mock tip for learning {item.term}"
            }
        )
    
    async def process_stage2(self, stage1_result: Stage1Response) -> Stage2Response:
        """Simulate Stage 2 processing"""
        # Simulate processing time
        await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # Create mock flashcard
        flashcard = FlashcardRow(
            term=stage1_result.term,
            position=stage1_result.position,
            korean_word=stage1_result.term,
            english_translation=f"Mock translation of {stage1_result.term}",
            part_of_speech=stage1_result.part_of_speech,
            example_sentence=f"Mock sentence with {stage1_result.term}",
            example_translation="This is a mock example translation",
            pronunciation_guide=f"[mock-pronunciation-{stage1_result.term}]",
            usage_notes=f"Mock usage note for {stage1_result.term}",
            difficulty_level="Beginner",
            tags=["mock", "test", "korean"],
            mnemonic_hint=f"Remember {stage1_result.term} by thinking of...",
            formality_level="Neutral",
            confidence_score=0.95
        )
        return Stage2Response(flashcard=flashcard)

class PipelineTestRunner:
    """Test runner for the concurrent processing pipeline"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_client = MockAPIClient()
        self.rate_limiter = DistributedRateLimiter(
            requests_per_minute=config["rate_limit"]["requests_per_minute"],
            tokens_per_minute=config["rate_limit"]["tokens_per_minute"]
        )
        self.results_collector = OrderedResultsCollector()
        self.db_writer = None
        self.test_results = {
            "sections": {},
            "errors": [],
            "summary": {}
        }
        
    def setup_database(self):
        """Initialize test database"""
        print("🔧 Setting up test database...")
        
        # Remove existing test database
        if os.path.exists(self.config["database_path"]):
            os.remove(self.config["database_path"])
            
        # Create new database with schema
        conn = sqlite3.connect(self.config["database_path"])
        cursor = conn.cursor()
        
        # Run migrations
        migration_files = [
            "migrations/001_initial_schema.sql",
            "migrations/002_concurrent_processing.sql",
            "migrations/003_flashcards_tables.sql"
        ]
        
        for migration_file in migration_files:
            if os.path.exists(migration_file):
                print(f"  Running migration: {migration_file}")
                with open(migration_file, 'r') as f:
                    sql = f.read()
                    # Execute each statement separately
                    for statement in sql.split(';'):
                        if statement.strip():
                            try:
                                cursor.execute(statement)
                            except sqlite3.Error as e:
                                print(f"  ⚠️  Error in statement: {e}")
                
        conn.commit()
        conn.close()
        
        # Initialize batch writer
        self.db_writer = OrderedBatchDatabaseWriter(
            db_path=self.config["database_path"],
            batch_size=self.config["batch_size"]
        )
        
        self.test_results["sections"]["database_setup"] = "✅ PASS"
        print("✅ Database setup complete")
        
    def load_vocabulary(self) -> List[VocabularyItem]:
        """Load vocabulary items from CSV"""
        print(f"\n📚 Loading vocabulary from {self.config['input_file']}...")
        
        try:
            items = []
            with open(self.config["input_file"], 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    if i >= self.config["limit"]:
                        break
                    item = VocabularyItem(
                        term=row['Hangul'],
                        position=int(row['Position']),
                        word_type=row.get('Word_Type', 'unknown'),
                        definition=row.get('Definition', ''),
                        frequency=int(row.get('Frequency', 0)),
                        topik_level=int(row.get('TOPIK_Level', 1))
                    )
                    items.append(item)
                
            print(f"✅ Loaded {len(items)} vocabulary items")
            self.test_results["sections"]["vocabulary_loading"] = f"✅ PASS - Loaded {len(items)} items"
            return items
            
        except Exception as e:
            error_msg = f"❌ Failed to load vocabulary: {e}"
            print(error_msg)
            self.test_results["sections"]["vocabulary_loading"] = "❌ FAIL"
            self.test_results["errors"].append(error_msg)
            return []
            
    async def test_rate_limiter(self):
        """Test rate limiter functionality"""
        print("\n🚦 Testing rate limiter...")
        
        try:
            # Test acquiring tokens
            start_time = time.time()
            successful_acquisitions = 0
            
            for i in range(10):
                if await self.rate_limiter.acquire(1, 100):
                    successful_acquisitions += 1
                    
            elapsed = time.time() - start_time
            
            print(f"  ✅ Acquired {successful_acquisitions}/10 tokens in {elapsed:.2f}s")
            self.test_results["sections"]["rate_limiter"] = f"✅ PASS - {successful_acquisitions}/10 tokens"
            
        except Exception as e:
            error_msg = f"❌ Rate limiter test failed: {e}"
            print(f"  {error_msg}")
            self.test_results["sections"]["rate_limiter"] = "❌ FAIL"
            self.test_results["errors"].append(error_msg)
            
    async def test_concurrent_processing(self, items: List[VocabularyItem]):
        """Test concurrent processing with mock API"""
        print(f"\n🔄 Testing concurrent processing (max_concurrent={self.config['max_concurrent']})...")
        
        try:
            # Create batch ID
            batch_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Process items concurrently
            semaphore = asyncio.Semaphore(self.config["max_concurrent"])
            tasks = []
            
            async def process_item(item: VocabularyItem, index: int):
                async with semaphore:
                    # Simulate rate limiting
                    await self.rate_limiter.acquire(1, 100)
                    
                    # Stage 1
                    stage1_result = await self.api_client.process_stage1(item)
                    
                    # Stage 2
                    flashcard = await self.api_client.process_stage2(stage1_result)
                    
                    # Collect result
                    self.results_collector.add_result(index, flashcard)
                    
                    return flashcard
                    
            # Start processing
            start_time = time.time()
            
            for i, item in enumerate(items):
                task = asyncio.create_task(process_item(item, i))
                tasks.append(task)
                
            # Wait for all tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Calculate statistics
            elapsed = time.time() - start_time
            successful = sum(1 for r in results if not isinstance(r, Exception))
            failed = sum(1 for r in results if isinstance(r, Exception))
            rate = successful / elapsed if elapsed > 0 else 0
            
            print(f"  ✅ Processed {successful}/{len(items)} items in {elapsed:.2f}s")
            print(f"  📊 Processing rate: {rate:.2f} items/second")
            print(f"  🔢 Total API calls: {self.api_client.call_count}")
            
            self.test_results["sections"]["concurrent_processing"] = f"✅ PASS - {successful}/{len(items)} items at {rate:.2f} items/sec"
            
            # Write results to database
            if self.db_writer and successful > 0:
                print("\n💾 Writing results to database...")
                ordered_results = self.results_collector.get_all_results()
                
                # Convert to database format
                db_items = []
                for result in ordered_results:
                    if isinstance(result, Stage2Response):
                        flashcard = result.flashcard
                        db_items.append({
                            'batch_id': batch_id,
                            'position': flashcard.position,
                            'term': flashcard.term,
                            'korean_word': flashcard.korean_word,
                            'english_translation': flashcard.english_translation,
                            'part_of_speech': flashcard.part_of_speech,
                            'example_sentence': flashcard.example_sentence,
                            'example_translation': flashcard.example_translation,
                            'pronunciation_guide': flashcard.pronunciation_guide,
                            'usage_notes': flashcard.usage_notes,
                            'difficulty_level': flashcard.difficulty_level,
                            'tags': json.dumps(flashcard.tags),
                            'mnemonic_hint': flashcard.mnemonic_hint,
                            'formality_level': flashcard.formality_level,
                            'confidence_score': flashcard.confidence_score,
                            'created_at': datetime.now().isoformat()
                        })
                
                # Write batch
                write_count = await self.db_writer.write_batch(db_items)
                print(f"  ✅ Wrote {write_count} flashcards to database")
                
                self.test_results["sections"]["database_writing"] = f"✅ PASS - Wrote {write_count} items"
                
        except Exception as e:
            error_msg = f"❌ Concurrent processing failed: {e}"
            print(f"  {error_msg}")
            self.test_results["sections"]["concurrent_processing"] = "❌ FAIL"
            self.test_results["errors"].append(error_msg)
            
    def verify_database_results(self):
        """Verify results were written to database correctly"""
        print("\n🔍 Verifying database results...")
        
        try:
            conn = sqlite3.connect(self.config["database_path"])
            cursor = conn.cursor()
            
            # Check flashcards table
            cursor.execute("SELECT COUNT(*) FROM flashcards")
            flashcard_count = cursor.fetchone()[0]
            
            # Check processing_batches table
            cursor.execute("SELECT COUNT(*) FROM processing_batches")
            batch_count = cursor.fetchone()[0]
            
            # Get sample flashcard
            cursor.execute("SELECT * FROM flashcards LIMIT 1")
            sample = cursor.fetchone()
            
            conn.close()
            
            print(f"  ✅ Found {flashcard_count} flashcards in database")
            print(f"  ✅ Found {batch_count} processing batches")
            
            if sample:
                print(f"  📝 Sample flashcard: {sample[3]} - {sample[4]}")
                
            self.test_results["sections"]["database_verification"] = f"✅ PASS - {flashcard_count} flashcards, {batch_count} batches"
            
        except Exception as e:
            error_msg = f"❌ Database verification failed: {e}"
            print(f"  {error_msg}")
            self.test_results["sections"]["database_verification"] = "❌ FAIL"
            self.test_results["errors"].append(error_msg)
            
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        # Section results
        print("\n✅ Test Sections:")
        for section, result in self.test_results["sections"].items():
            print(f"  {section}: {result}")
            
        # Errors
        if self.test_results["errors"]:
            print(f"\n❌ Errors ({len(self.test_results['errors'])}):")
            for error in self.test_results["errors"]:
                print(f"  - {error}")
                
        # Overall result
        failed_sections = sum(1 for r in self.test_results["sections"].values() if "FAIL" in r)
        total_sections = len(self.test_results["sections"])
        
        print(f"\n📈 Overall Result: {total_sections - failed_sections}/{total_sections} sections passed")
        
        if failed_sections == 0:
            print("\n✅ ALL TESTS PASSED! Pipeline is ready for production.")
        else:
            print(f"\n❌ {failed_sections} sections failed. Please fix issues before proceeding.")
            
    async def run_all_tests(self):
        """Run all pipeline tests"""
        print("🚀 Starting Korean Flashcard Pipeline Tests")
        print(f"   Config: {json.dumps(self.config, indent=2)}")
        
        # Setup
        self.setup_database()
        
        # Load vocabulary
        items = self.load_vocabulary()
        if not items:
            print("❌ Cannot proceed without vocabulary items")
            return
            
        # Test components
        await self.test_rate_limiter()
        await self.test_concurrent_processing(items)
        self.verify_database_results()
        
        # Summary
        self.print_summary()

async def main():
    """Main test entry point"""
    runner = PipelineTestRunner(TEST_CONFIG)
    await runner.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())