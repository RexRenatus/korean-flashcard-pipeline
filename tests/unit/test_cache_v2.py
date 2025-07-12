"""
Unit tests for the modernized cache system
"""

import pytest
import asyncio
import tempfile
import shutil
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from flashcard_pipeline.cache_v2 import (
    ModernCacheService, CompressionType, CacheInvalidationRule
)
from flashcard_pipeline.models import VocabularyItem, Stage1Response, Stage2Response, FlashcardRow
from flashcard_pipeline.database import DatabaseManager


class TestModernCacheService:
    """Test the modernized cache service"""
    
    @pytest.fixture
    async def cache_service(self):
        """Create a test cache service"""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "test_cache"
            db_path = Path(temp_dir) / "test.db"
            
            service = ModernCacheService(
                cache_dir=str(cache_dir),
                db_path=str(db_path),
                compression=CompressionType.LZ4,
                max_size_mb=10,
                ttl_hours=1
            )
            
            yield service
    
    @pytest.fixture
    def sample_vocab_item(self):
        """Create a sample vocabulary item"""
        return VocabularyItem(
            position=1,
            term="안녕하세요",
            type="phrase"
        )
    
    @pytest.fixture
    def sample_stage1_response(self):
        """Create a sample Stage 1 response"""
        return Stage1Response(
            term="안녕하세요",
            term_number=1,
            term_with_pronunciation="안녕하세요 [an-nyeong-ha-se-yo]",
            ipa="an.njʌŋ.ha.se.jo",
            pos="interjection/phrase",
            primary_meaning="Hello (formal)",
            other_meanings="Good day; How are you",
            metaphor="Wishing peace and well-being",
            metaphor_noun="peaceful greeting",
            metaphor_action="bowing respectfully",
            suggested_location="Traditional Korean house entrance",
            anchor_object="Folded hands in greeting",
            anchor_sensory="Warm voice tone",
            explanation="Formal greeting showing respect",
            usage_context="Used when meeting someone formally",
            comparison=None,
            homonyms=[],
            korean_keywords=["인사", "공손", "만남"]
        )
    
    @pytest.fixture
    def sample_stage2_response(self):
        """Create a sample Stage 2 response"""
        return Stage2Response(
            term="안녕하세요",
            term_number=1,
            rows=[
                FlashcardRow(
                    term_number=1,
                    tab_name="Recognition",
                    primer="Korean greeting",
                    front="안녕하세요",
                    back="Hello (formal)",
                    tags="greeting,formal,basic",
                    honorific_level="formal"
                )
            ]
        )
    
    @pytest.mark.asyncio
    async def test_cache_initialization(self, cache_service):
        """Test cache service initialization"""
        assert cache_service.compression == CompressionType.LZ4
        assert cache_service.max_size_bytes == 10 * 1024 * 1024
        assert cache_service.ttl_seconds == 3600
        
        # Check directories created
        assert cache_service.stage1_dir.exists()
        assert cache_service.stage2_dir.exists()
        assert cache_service.metadata_dir.exists()
    
    @pytest.mark.asyncio
    async def test_stage1_cache_miss(self, cache_service, sample_vocab_item):
        """Test Stage 1 cache miss"""
        result = await cache_service.get_stage1(sample_vocab_item)
        assert result is None
        
        if cache_service.stats:
            assert cache_service.stats.stage1_misses == 1
            assert cache_service.stats.stage1_hits == 0
    
    @pytest.mark.asyncio
    async def test_stage1_cache_save_and_hit(
        self, cache_service, sample_vocab_item, sample_stage1_response
    ):
        """Test saving and retrieving Stage 1 from cache"""
        # Save to cache
        await cache_service.save_stage1(
            sample_vocab_item, sample_stage1_response, tokens_used=350
        )
        
        # Retrieve from cache
        result = await cache_service.get_stage1(sample_vocab_item)
        assert result is not None
        
        response, tokens_saved = result
        assert response.term == sample_stage1_response.term
        assert response.primary_meaning == sample_stage1_response.primary_meaning
        assert tokens_saved == 350
        
        if cache_service.stats:
            assert cache_service.stats.stage1_hits == 1
            assert cache_service.stats.total_tokens_saved == 350
    
    @pytest.mark.asyncio
    async def test_stage2_cache_operations(
        self, cache_service, sample_vocab_item, 
        sample_stage1_response, sample_stage2_response
    ):
        """Test Stage 2 cache operations"""
        # Initially should be a miss
        result = await cache_service.get_stage2(sample_vocab_item, sample_stage1_response)
        assert result is None
        
        # Save to cache
        await cache_service.save_stage2(
            sample_vocab_item, sample_stage1_response, 
            sample_stage2_response, tokens_used=1000
        )
        
        # Retrieve from cache
        result = await cache_service.get_stage2(sample_vocab_item, sample_stage1_response)
        assert result is not None
        
        response, tokens_saved = result
        assert len(response.rows) == 1
        assert response.rows[0].front == "안녕하세요"
        assert tokens_saved == 1000
    
    @pytest.mark.asyncio
    async def test_compression(self, sample_vocab_item, sample_stage1_response):
        """Test different compression algorithms"""
        for compression in [CompressionType.GZIP, CompressionType.ZLIB, CompressionType.LZ4]:
            with tempfile.TemporaryDirectory() as temp_dir:
                service = ModernCacheService(
                    cache_dir=temp_dir,
                    db_path=f"{temp_dir}/test.db",
                    compression=compression
                )
                
                # Save with compression
                await service.save_stage1(
                    sample_vocab_item, sample_stage1_response, tokens_used=350
                )
                
                # Retrieve and verify
                result = await service.get_stage1(sample_vocab_item)
                assert result is not None
                response, _ = result
                assert response.term == sample_stage1_response.term
    
    @pytest.mark.asyncio
    async def test_memory_cache(self, cache_service, sample_vocab_item, sample_stage1_response):
        """Test in-memory cache functionality"""
        # Save to cache
        await cache_service.save_stage1(
            sample_vocab_item, sample_stage1_response, tokens_used=350
        )
        
        # First retrieval - from disk
        result1 = await cache_service.get_stage1(sample_vocab_item)
        assert result1 is not None
        
        # Second retrieval - should be from memory cache
        result2 = await cache_service.get_stage1(sample_vocab_item)
        assert result2 is not None
        
        # Results should be identical
        assert result1[0].term == result2[0].term
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_by_ttl(
        self, cache_service, sample_vocab_item, sample_stage1_response
    ):
        """Test TTL-based cache invalidation"""
        # Save with short TTL
        cache_service.ttl_seconds = 1
        await cache_service.save_stage1(
            sample_vocab_item, sample_stage1_response, tokens_used=350
        )
        
        # Manually set expiration to past
        with cache_service.db_manager.get_connection() as conn:
            conn.execute("""
                UPDATE cache_metadata 
                SET ttl_expires_at = datetime('now', '-1 hour')
                WHERE stage = 1
            """)
        
        # Invalidate expired entries
        count = await cache_service.invalidate_expired()
        assert count == 1
        
        # Should be gone
        result = await cache_service.get_stage1(sample_vocab_item)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_by_size(self, cache_service):
        """Test size-based cache invalidation"""
        # Create multiple entries
        for i in range(5):
            vocab_item = VocabularyItem(
                position=i,
                term=f"단어{i}",
                type="word"
            )
            response = Stage1Response(
                term=f"단어{i}",
                term_number=i,
                term_with_pronunciation=f"단어{i}",
                ipa="dan.eo",
                pos="noun",
                primary_meaning=f"Word {i}",
                other_meanings="",
                metaphor="",
                metaphor_noun="",
                metaphor_action="",
                suggested_location="",
                anchor_object="",
                anchor_sensory="",
                explanation="",
                usage_context="",
                comparison=None,
                homonyms=[],
                korean_keywords=[]
            )
            await cache_service.save_stage1(vocab_item, response, tokens_used=100)
        
        # Invalidate to free space
        count = await cache_service.invalidate_by_size(target_size_mb=0)
        assert count > 0
    
    @pytest.mark.asyncio
    async def test_cache_warming_queue(self, cache_service):
        """Test cache warming queue operations"""
        terms = ["안녕하세요", "감사합니다", "사랑해요"]
        
        # Add to warming queue
        results = await cache_service.warm_cache(terms, priority_boost=5)
        assert results["queued"] == 3
        
        # Get warming candidates
        candidates = await cache_service.get_warming_candidates(limit=2)
        assert len(candidates) == 2
        assert all(c["priority"] == 5 for c in candidates)
        assert all(c["term"] in terms for c in candidates)
    
    @pytest.mark.asyncio
    async def test_cache_statistics(
        self, cache_service, sample_vocab_item, sample_stage1_response
    ):
        """Test cache statistics tracking"""
        # Generate some activity
        await cache_service.save_stage1(
            sample_vocab_item, sample_stage1_response, tokens_used=350
        )
        
        # Hit
        await cache_service.get_stage1(sample_vocab_item)
        
        # Miss
        await cache_service.get_stage1(VocabularyItem(position=99, term="없는단어", type="word"))
        
        # Get stats
        stats = cache_service.get_stats()
        
        assert stats["total_entries"] == 1
        assert stats["stage1_entries"] == 1
        assert stats["stage2_entries"] == 0
        
        if cache_service.stats:
            assert stats["stage1_hit_rate"] == 0.5  # 1 hit, 1 miss
    
    @pytest.mark.asyncio
    async def test_cache_performance_analysis(self, cache_service):
        """Test cache performance analysis"""
        analysis = await cache_service.analyze_cache_performance()
        
        assert "stats" in analysis
        assert "recommendations" in analysis
        assert "health_score" in analysis
        
        # Health score should be reasonable for empty cache
        assert 0 <= analysis["health_score"] <= 100
    
    @pytest.mark.asyncio
    async def test_hot_entry_marking(
        self, cache_service, sample_vocab_item, sample_stage1_response
    ):
        """Test marking frequently accessed entries as hot"""
        # Save entry
        await cache_service.save_stage1(
            sample_vocab_item, sample_stage1_response, tokens_used=350
        )
        
        # Access multiple times
        for _ in range(6):
            await cache_service.get_stage1(sample_vocab_item)
        
        # Check if marked as hot
        with cache_service.db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT is_hot FROM cache_metadata
                WHERE term = ?
            """, (sample_vocab_item.term,))
            
            row = cursor.fetchone()
            assert row and row[0] == 1  # Should be marked as hot
    
    @pytest.mark.asyncio
    async def test_cache_clear(
        self, cache_service, sample_vocab_item, sample_stage1_response
    ):
        """Test clearing cache"""
        # Add some entries
        await cache_service.save_stage1(
            sample_vocab_item, sample_stage1_response, tokens_used=350
        )
        
        # Clear all
        count = await cache_service.clear_cache()
        assert count == 1
        
        # Should be empty
        result = await cache_service.get_stage1(sample_vocab_item)
        assert result is None
        
        # Stats should be reset
        if cache_service.stats:
            assert cache_service.stats.stage1_hits == 0
            assert cache_service.stats.stage1_misses == 1  # From the get above
    
    @pytest.mark.asyncio
    async def test_concurrent_access(
        self, cache_service, sample_vocab_item, sample_stage1_response
    ):
        """Test concurrent cache access"""
        async def save_and_get():
            await cache_service.save_stage1(
                sample_vocab_item, sample_stage1_response, tokens_used=350
            )
            result = await cache_service.get_stage1(sample_vocab_item)
            return result is not None
        
        # Run multiple concurrent operations
        results = await asyncio.gather(
            *[save_and_get() for _ in range(5)],
            return_exceptions=True
        )
        
        # All should succeed
        assert all(r is True for r in results)
    
    @pytest.mark.asyncio
    async def test_cache_key_consistency(self, cache_service):
        """Test cache key generation consistency"""
        vocab1 = VocabularyItem(position=1, term="테스트", type="word")
        vocab2 = VocabularyItem(position=2, term="테스트", type="word")
        
        key1 = cache_service._get_cache_key(1, vocab1)
        key2 = cache_service._get_cache_key(1, vocab2)
        
        # Same term and type should generate same key
        assert key1 == key2
        
        # Different type should generate different key
        vocab3 = VocabularyItem(position=1, term="테스트", type="phrase")
        key3 = cache_service._get_cache_key(1, vocab3)
        assert key1 != key3