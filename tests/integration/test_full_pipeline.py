"""Full pipeline integration tests for the Korean Flashcard Pipeline.

This module tests the complete end-to-end processing flow,
including database integration, API interactions, and export functionality.
"""

import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import Mock, patch, AsyncMock

import pytest
import aiosqlite
from httpx import Response

from flashcard_pipeline.models import (
    VocabularyItem,
    Stage1Response,
    Stage2Response,
    Flashcard,
    BatchStatus,
)
from flashcard_pipeline.api.client import OpenRouterClient
from flashcard_pipeline.database.manager import DatabaseManager
from flashcard_pipeline.pipeline.orchestrator import PipelineOrchestrator
from flashcard_pipeline.cache import CacheService
from tests.fixtures.factory import (
    VocabularyFactory,
    Stage1ResponseFactory,
    Stage2ResponseFactory,
    FlashcardFactory,
    TestScenarioFactory,
)


class TestFullPipelineIntegration:
    """Test the complete pipeline from input to export."""
    
    @pytest.fixture
    async def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        # Initialize database
        async with aiosqlite.connect(db_path) as db:
            # Create tables
            await db.execute('''
                CREATE TABLE vocabulary_items (
                    id INTEGER PRIMARY KEY,
                    korean TEXT NOT NULL,
                    english TEXT NOT NULL,
                    nuance_level TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await db.execute('''
                CREATE TABLE flashcards (
                    id TEXT PRIMARY KEY,
                    vocabulary_item_id INTEGER,
                    difficulty TEXT NOT NULL,
                    card_type TEXT NOT NULL,
                    front_data TEXT NOT NULL,
                    back_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (vocabulary_item_id) REFERENCES vocabulary_items(id)
                )
            ''')
            
            await db.execute('''
                CREATE TABLE stage1_responses (
                    id INTEGER PRIMARY KEY,
                    vocabulary_item_id INTEGER,
                    response_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (vocabulary_item_id) REFERENCES vocabulary_items(id)
                )
            ''')
            
            await db.execute('''
                CREATE TABLE stage2_responses (
                    id INTEGER PRIMARY KEY,
                    vocabulary_item_id INTEGER,
                    response_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (vocabulary_item_id) REFERENCES vocabulary_items(id)
                )
            ''')
            
            await db.commit()
        
        yield db_path
        
        # Cleanup
        Path(db_path).unlink(missing_ok=True)
    
    @pytest.fixture
    async def pipeline_components(self, temp_db):
        """Create pipeline components with test configuration."""
        config = {
            'api_key': 'test-api-key',
            'database_path': temp_db,
            'cache_enabled': True,
            'batch_size': 5,
            'max_retries': 2,
        }
        
        api_client = OpenRouterClient(api_key=config['api_key'])
        db_manager = DatabaseManager(db_path=config['database_path'])
        cache = CacheService(enabled=config['cache_enabled'])
        
        orchestrator = PipelineOrchestrator(
            api_client=api_client,
            db_manager=db_manager,
            cache=cache,
            config=config
        )
        
        return {
            'api_client': api_client,
            'db_manager': db_manager,
            'cache': cache,
            'orchestrator': orchestrator,
            'config': config
        }
    
    @pytest.mark.asyncio
    async def test_end_to_end_processing_flow(self, pipeline_components):
        """Test complete processing from vocabulary input to flashcard export."""
        orchestrator = pipeline_components['orchestrator']
        db_manager = pipeline_components['db_manager']
        
        # Create test scenario
        scenario = TestScenarioFactory.create_full_pipeline_scenario()
        vocab_items = scenario['vocabulary_items']
        
        # Mock API responses
        with patch.object(orchestrator.api_client, 'process_stage1') as mock_stage1, \
             patch.object(orchestrator.api_client, 'process_stage2') as mock_stage2:
            
            # Setup mock responses
            mock_stage1.side_effect = [
                AsyncMock(return_value=response)()
                for response in scenario['stage1_responses']
            ]
            
            mock_stage2.side_effect = [
                AsyncMock(return_value=response)()
                for response in scenario['stage2_responses']
            ]
            
            # Process vocabulary items
            result = await orchestrator.process_batch(vocab_items)
            
            # Verify results
            assert result.status == BatchStatus.COMPLETED
            assert result.processed_items == len(vocab_items)
            assert result.failed_items == 0
            
            # Verify database entries
            async with db_manager.get_connection() as conn:
                # Check vocabulary items
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM vocabulary_items"
                )
                count = await cursor.fetchone()
                assert count[0] == len(vocab_items)
                
                # Check flashcards
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM flashcards"
                )
                count = await cursor.fetchone()
                assert count[0] > 0  # Should have flashcards created
    
    @pytest.mark.asyncio
    async def test_database_integration(self, pipeline_components):
        """Test database operations throughout the pipeline."""
        db_manager = pipeline_components['db_manager']
        
        # Create and save vocabulary items
        vocab_items = VocabularyFactory.create_batch(3)
        
        async with db_manager.get_connection() as conn:
            for item in vocab_items:
                await conn.execute(
                    '''INSERT INTO vocabulary_items (korean, english, nuance_level)
                       VALUES (?, ?, ?)''',
                    (item.korean, item.english, item.nuance_level.value)
                )
            await conn.commit()
            
            # Verify insertion
            cursor = await conn.execute(
                "SELECT korean, english, nuance_level FROM vocabulary_items"
            )
            rows = await cursor.fetchall()
            assert len(rows) == len(vocab_items)
            
            # Create and save flashcards
            for i, item in enumerate(vocab_items):
                flashcards = FlashcardFactory.create_set(vocabulary_item_id=i+1)
                
                for card in flashcards:
                    await conn.execute(
                        '''INSERT INTO flashcards 
                           (id, vocabulary_item_id, difficulty, card_type, front_data, back_data)
                           VALUES (?, ?, ?, ?, ?, ?)''',
                        (
                            card.id,
                            card.vocabulary_item_id,
                            card.difficulty.value,
                            card.card_type,
                            json.dumps(card.front.model_dump()),
                            json.dumps(card.back.model_dump())
                        )
                    )
            await conn.commit()
            
            # Verify flashcard creation
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM flashcards"
            )
            count = await cursor.fetchone()
            assert count[0] == len(vocab_items) * 3  # 3 cards per item
    
    @pytest.mark.asyncio
    async def test_api_integration_with_mocks(self, pipeline_components):
        """Test API integration with proper mocking."""
        api_client = pipeline_components['api_client']
        
        # Create test data
        vocab_item = VocabularyFactory.create()
        stage1_response = Stage1ResponseFactory.create_detailed()
        stage2_response = Stage2ResponseFactory.create()
        
        # Mock HTTP client
        with patch.object(api_client._client, 'post') as mock_post:
            # Mock Stage 1 response
            mock_post.return_value = Response(
                status_code=200,
                json=stage1_response.model_dump()
            )
            
            # Test Stage 1
            result1 = await api_client.process_stage1(vocab_item)
            assert result1.korean_word == stage1_response.korean_word
            assert len(result1.nuances) == len(stage1_response.nuances)
            
            # Mock Stage 2 response
            mock_post.return_value = Response(
                status_code=200,
                json=stage2_response.model_dump()
            )
            
            # Test Stage 2
            result2 = await api_client.process_stage2(vocab_item, result1)
            assert result2.total_cards_generated == stage2_response.total_cards_generated
            assert len(result2.flashcards) == len(stage2_response.flashcards)
    
    @pytest.mark.asyncio
    async def test_export_format_verification(self, pipeline_components):
        """Test that exported data matches expected formats."""
        orchestrator = pipeline_components['orchestrator']
        
        # Create test flashcards
        flashcards = [
            FlashcardFactory.create() for _ in range(5)
        ]
        
        # Test JSON export
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            export_path = tmp.name
        
        await orchestrator.export_flashcards(flashcards, export_path, format='json')
        
        # Verify JSON structure
        with open(export_path, 'r') as f:
            exported_data = json.load(f)
        
        assert 'flashcards' in exported_data
        assert 'metadata' in exported_data
        assert len(exported_data['flashcards']) == len(flashcards)
        
        # Verify flashcard structure
        for exported_card in exported_data['flashcards']:
            assert 'id' in exported_card
            assert 'front' in exported_card
            assert 'back' in exported_card
            assert 'difficulty' in exported_card
            assert 'card_type' in exported_card
        
        # Cleanup
        Path(export_path).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_error_scenario_handling(self, pipeline_components):
        """Test how the pipeline handles various error scenarios."""
        orchestrator = pipeline_components['orchestrator']
        
        # Create error scenario
        scenario = TestScenarioFactory.create_error_scenario()
        vocab_items = scenario['vocabulary_items']
        
        # Mock API to raise errors
        with patch.object(orchestrator.api_client, 'process_stage1') as mock_stage1:
            # First call succeeds, others fail
            mock_stage1.side_effect = [
                AsyncMock(return_value=Stage1ResponseFactory.create())(),
                Exception("API Error"),
                Exception("Network Error")
            ]
            
            # Process batch
            result = await orchestrator.process_batch(vocab_items)
            
            # Verify partial success handling
            assert result.status == BatchStatus.PARTIAL_SUCCESS
            assert result.processed_items == 1
            assert result.failed_items == 2
            assert len(result.errors) == 2
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, pipeline_components):
        """Test concurrent processing of multiple batches."""
        orchestrator = pipeline_components['orchestrator']
        
        # Create multiple batches
        batches = [
            VocabularyFactory.create_batch(5) for _ in range(3)
        ]
        
        # Mock API responses
        with patch.object(orchestrator.api_client, 'process_stage1') as mock_stage1, \
             patch.object(orchestrator.api_client, 'process_stage2') as mock_stage2:
            
            mock_stage1.return_value = AsyncMock(
                return_value=Stage1ResponseFactory.create()
            )()
            
            mock_stage2.return_value = AsyncMock(
                return_value=Stage2ResponseFactory.create()
            )()
            
            # Process batches concurrently
            tasks = [
                orchestrator.process_batch(batch)
                for batch in batches
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Verify all batches processed
            assert len(results) == len(batches)
            for result in results:
                assert result.status == BatchStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_cache_integration(self, pipeline_components):
        """Test cache integration in the pipeline."""
        orchestrator = pipeline_components['orchestrator']
        cache = pipeline_components['cache']
        
        # Create test data
        vocab_item = VocabularyFactory.create()
        stage1_response = Stage1ResponseFactory.create()
        
        # Mock API
        with patch.object(orchestrator.api_client, 'process_stage1') as mock_stage1:
            mock_stage1.return_value = AsyncMock(return_value=stage1_response)()
            
            # First call - should hit API
            result1 = await orchestrator.process_stage1_with_cache(vocab_item)
            assert mock_stage1.call_count == 1
            
            # Second call - should hit cache
            result2 = await orchestrator.process_stage1_with_cache(vocab_item)
            assert mock_stage1.call_count == 1  # No additional API call
            assert result1 == result2
    
    @pytest.mark.asyncio
    async def test_data_consistency(self, pipeline_components):
        """Test data consistency across pipeline stages."""
        orchestrator = pipeline_components['orchestrator']
        db_manager = pipeline_components['db_manager']
        
        # Create test scenario
        vocab_items = VocabularyFactory.create_batch(3)
        
        # Process with real database
        async with db_manager.get_connection() as conn:
            # Insert vocabulary items
            for item in vocab_items:
                cursor = await conn.execute(
                    '''INSERT INTO vocabulary_items (korean, english, nuance_level)
                       VALUES (?, ?, ?)
                       RETURNING id''',
                    (item.korean, item.english, item.nuance_level.value)
                )
                item_id = await cursor.fetchone()
                item.id = item_id[0]
            await conn.commit()
            
            # Create stage responses
            for item in vocab_items:
                # Save Stage 1 response
                stage1_response = Stage1ResponseFactory.create(
                    korean_word=item.korean,
                    english_translation=item.english
                )
                
                await conn.execute(
                    '''INSERT INTO stage1_responses (vocabulary_item_id, response_data)
                       VALUES (?, ?)''',
                    (item.id, json.dumps(stage1_response.model_dump()))
                )
                
                # Save Stage 2 response
                stage2_response = Stage2ResponseFactory.create(
                    vocabulary_item_id=item.id
                )
                
                await conn.execute(
                    '''INSERT INTO stage2_responses (vocabulary_item_id, response_data)
                       VALUES (?, ?)''',
                    (item.id, json.dumps(stage2_response.model_dump()))
                )
                
                # Save flashcards
                for flashcard in stage2_response.flashcards:
                    await conn.execute(
                        '''INSERT INTO flashcards 
                           (id, vocabulary_item_id, difficulty, card_type, front_data, back_data)
                           VALUES (?, ?, ?, ?, ?, ?)''',
                        (
                            flashcard.id,
                            item.id,
                            flashcard.difficulty.value,
                            flashcard.card_type,
                            json.dumps(flashcard.front.model_dump()),
                            json.dumps(flashcard.back.model_dump())
                        )
                    )
            
            await conn.commit()
            
            # Verify data consistency
            cursor = await conn.execute('''
                SELECT v.id, v.korean, COUNT(f.id) as flashcard_count
                FROM vocabulary_items v
                LEFT JOIN flashcards f ON v.id = f.vocabulary_item_id
                GROUP BY v.id
            ''')
            
            results = await cursor.fetchall()
            assert len(results) == len(vocab_items)
            
            for row in results:
                assert row[2] > 0  # Each item should have flashcards