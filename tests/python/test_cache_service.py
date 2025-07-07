import pytest
import tempfile
import json
import os
from pathlib import Path
from datetime import datetime
import hashlib

from flashcard_pipeline.cache import CacheService
from flashcard_pipeline.models import (
    VocabularyItem,
    Stage1Response,
    Stage2Response,
    Comparison
)


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def cache_service(temp_cache_dir):
    """Create a cache service instance"""
    return CacheService(cache_dir=str(temp_cache_dir))


@pytest.fixture
def sample_vocabulary_item():
    """Create a sample vocabulary item"""
    return VocabularyItem(position=1, term="테스트", type="noun")


@pytest.fixture
def sample_stage1_response():
    """Create a sample Stage1 response"""
    return Stage1Response(
        term_number=1,
        term="테스트",
        ipa="[tʰesɯtʰɯ]",
        pos="noun",
        primary_meaning="test",
        other_meanings="exam, trial",
        metaphor="like a challenge",
        metaphor_noun="challenge",
        metaphor_action="testing",
        suggested_location="classroom",
        anchor_object="paper",
        anchor_sensory="white",
        explanation="evaluation method",
        usage_context="academic",
        comparison=Comparison(
            similar_to=["시험"],
            different_from=[],
            commonly_confused_with=[]
        ),
        homonyms=[],
        korean_keywords=["테스트"]
    )


@pytest.fixture
def sample_stage2_response():
    """Create a sample Stage2 response"""
    tsv = "1\t테스트\t[tʰesɯtʰɯ]\tnoun\tTest\tA method of evaluation\t이것은 테스트입니다.\tTest\tteseuteu\tThis is a test.\tThink of testing\tbeginner\tcommon\tstudy,academic\tCommonly used"
    return Stage2Response.from_tsv(tsv)


class TestCacheService:
    def test_cache_key_generation(self, cache_service, sample_vocabulary_item):
        """Test that cache keys are generated consistently"""
        key1 = cache_service._get_cache_key(1, sample_vocabulary_item)
        key2 = cache_service._get_cache_key(1, sample_vocabulary_item)
        
        assert key1 == key2
        assert len(key1) == 64  # SHA256 hex length
        
        # Different stage should produce different key
        key_stage2 = cache_service._get_cache_key(2, sample_vocabulary_item)
        assert key1 != key_stage2
    
    def test_stage1_cache_operations(self, cache_service, sample_vocabulary_item, sample_stage1_response):
        """Test Stage 1 cache set and get operations"""
        # Initially not cached
        cached = cache_service.get_stage1_cache(sample_vocabulary_item)
        assert cached is None
        
        # Cache the response
        cache_service.set_stage1_cache(sample_vocabulary_item, sample_stage1_response)
        
        # Retrieve from cache
        cached = cache_service.get_stage1_cache(sample_vocabulary_item)
        assert cached is not None
        assert cached.term == sample_stage1_response.term
        assert cached.primary_meaning == sample_stage1_response.primary_meaning
        assert cached.comparison.similar_to == sample_stage1_response.comparison.similar_to
    
    def test_stage2_cache_operations(
        self, 
        cache_service, 
        sample_vocabulary_item, 
        sample_stage1_response,
        sample_stage2_response
    ):
        """Test Stage 2 cache set and get operations"""
        # Initially not cached
        cached = cache_service.get_stage2_cache(sample_vocabulary_item, sample_stage1_response)
        assert cached is None
        
        # Cache the response
        cache_service.set_stage2_cache(sample_vocabulary_item, sample_stage1_response, sample_stage2_response)
        
        # Retrieve from cache
        cached = cache_service.get_stage2_cache(sample_vocabulary_item, sample_stage1_response)
        assert cached is not None
        assert cached.flashcard_row.term == sample_stage2_response.flashcard_row.term
        assert cached.flashcard_row.difficulty == sample_stage2_response.flashcard_row.difficulty
    
    def test_cache_persistence(self, temp_cache_dir, sample_vocabulary_item, sample_stage1_response):
        """Test that cache persists across service instances"""
        # First service instance
        service1 = CacheService(cache_dir=str(temp_cache_dir))
        service1.set_stage1_cache(sample_vocabulary_item, sample_stage1_response)
        
        # Create new service instance
        service2 = CacheService(cache_dir=str(temp_cache_dir))
        
        # Should be able to retrieve cached data
        cached = service2.get_stage1_cache(sample_vocabulary_item)
        assert cached is not None
        assert cached.term == sample_stage1_response.term
    
    def test_cache_file_structure(self, cache_service, temp_cache_dir, sample_vocabulary_item, sample_stage1_response):
        """Test the cache file structure and naming"""
        cache_service.set_stage1_cache(sample_vocabulary_item, sample_stage1_response)
        
        # Check file exists
        cache_key = cache_service._get_cache_key(1, sample_vocabulary_item)
        cache_file = temp_cache_dir / f"{cache_key}.json"
        assert cache_file.exists()
        
        # Check file content
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data['term'] == sample_stage1_response.term
        assert data['primary_meaning'] == sample_stage1_response.primary_meaning
    
    def test_cache_stats(self, cache_service, sample_vocabulary_item, sample_stage1_response, sample_stage2_response):
        """Test cache statistics collection"""
        # Initially empty
        stats = cache_service.get_stats()
        assert stats['total_entries'] == 0
        assert stats['stage1_entries'] == 0
        assert stats['stage2_entries'] == 0
        assert stats['total_size'] == 0
        
        # Add stage 1 cache
        cache_service.set_stage1_cache(sample_vocabulary_item, sample_stage1_response)
        
        stats = cache_service.get_stats()
        assert stats['total_entries'] == 1
        assert stats['stage1_entries'] == 1
        assert stats['stage2_entries'] == 0
        assert stats['total_size'] > 0
        
        # Add stage 2 cache
        cache_service.set_stage2_cache(sample_vocabulary_item, sample_stage1_response, sample_stage2_response)
        
        stats = cache_service.get_stats()
        assert stats['total_entries'] == 2
        assert stats['stage1_entries'] == 1
        assert stats['stage2_entries'] == 1
        assert stats['total_size'] > 0
    
    def test_clear_cache(self, cache_service, sample_vocabulary_item, sample_stage1_response):
        """Test clearing the cache"""
        # Add some entries
        cache_service.set_stage1_cache(sample_vocabulary_item, sample_stage1_response)
        
        # Verify entries exist
        assert cache_service.get_stage1_cache(sample_vocabulary_item) is not None
        
        # Clear cache
        cleared = cache_service.clear_cache()
        assert cleared >= 1
        
        # Verify cache is empty
        assert cache_service.get_stage1_cache(sample_vocabulary_item) is None
        
        stats = cache_service.get_stats()
        assert stats['total_entries'] == 0
    
    def test_memory_cache_functionality(self, cache_service, sample_vocabulary_item, sample_stage1_response):
        """Test that memory cache improves performance"""
        import time
        
        # First access - from disk
        cache_service.set_stage1_cache(sample_vocabulary_item, sample_stage1_response)
        
        # Clear memory cache
        cache_service._memory_cache.clear()
        
        # Time disk access
        start = time.time()
        result1 = cache_service.get_stage1_cache(sample_vocabulary_item)
        disk_time = time.time() - start
        
        # Time memory cache access
        start = time.time()
        result2 = cache_service.get_stage1_cache(sample_vocabulary_item)
        memory_time = time.time() - start
        
        # Memory access should be faster (though timing can be unreliable in tests)
        assert result1 == result2
        assert memory_time <= disk_time * 2  # Allow some variance
    
    def test_cache_with_different_vocabulary_types(self, cache_service):
        """Test caching with different vocabulary types"""
        items = [
            VocabularyItem(position=1, term="명사", type="noun"),
            VocabularyItem(position=2, term="동사", type="verb"),
            VocabularyItem(position=3, term="형용사", type="adjective"),
            VocabularyItem(position=4, term="부사", type=None),  # No type
        ]
        
        responses = []
        for item in items:
            response = Stage1Response(
                term_number=item.position,
                term=item.term,
                ipa=f"[{item.term}]",
                pos=item.type or "unknown",
                primary_meaning=f"Meaning of {item.term}",
                other_meanings="",
                metaphor="",
                metaphor_noun="",
                metaphor_action="",
                suggested_location="",
                anchor_object="",
                anchor_sensory="",
                explanation="",
                comparison=Comparison(similar_to=[], different_from=[], commonly_confused_with=[]),
                homonyms=[],
                korean_keywords=[]
            )
            responses.append(response)
            cache_service.set_stage1_cache(item, response)
        
        # Verify all cached correctly
        for item, expected_response in zip(items, responses):
            cached = cache_service.get_stage1_cache(item)
            assert cached is not None
            assert cached.term == expected_response.term
            assert cached.pos == expected_response.pos
    
    def test_cache_key_uniqueness(self, cache_service):
        """Test that different items produce different cache keys"""
        items = [
            VocabularyItem(position=1, term="test1", type="noun"),
            VocabularyItem(position=1, term="test2", type="noun"),  # Same position, different term
            VocabularyItem(position=2, term="test1", type="noun"),  # Same term, different position
            VocabularyItem(position=1, term="test1", type="verb"),  # Same term/position, different type
            VocabularyItem(position=1, term="test1", type=None),    # Same term/position, no type
        ]
        
        keys = [cache_service._get_cache_key(1, item) for item in items]
        
        # All keys should be unique
        assert len(set(keys)) == len(keys)
    
    def test_invalid_cache_file_handling(self, cache_service, temp_cache_dir, sample_vocabulary_item):
        """Test handling of corrupted cache files"""
        # Create an invalid cache file
        cache_key = cache_service._get_cache_key(1, sample_vocabulary_item)
        cache_file = temp_cache_dir / f"{cache_key}.json"
        
        # Write invalid JSON
        with open(cache_file, 'w') as f:
            f.write("{invalid json")
        
        # Should return None for corrupted cache
        cached = cache_service.get_stage1_cache(sample_vocabulary_item)
        assert cached is None
        
        # Should be able to overwrite with valid data
        response = Stage1Response(
            term_number=1,
            term="test",
            ipa="[test]",
            pos="noun",
            primary_meaning="test",
            other_meanings="",
            metaphor="",
            metaphor_noun="",
            metaphor_action="",
            suggested_location="",
            anchor_object="",
            anchor_sensory="",
            explanation="",
            comparison=Comparison(similar_to=[], different_from=[], commonly_confused_with=[]),
            homonyms=[],
            korean_keywords=[]
        )
        cache_service.set_stage1_cache(sample_vocabulary_item, response)
        
        # Now should work
        cached = cache_service.get_stage1_cache(sample_vocabulary_item)
        assert cached is not None
        assert cached.term == "test"
    
    def test_concurrent_cache_access(self, cache_service, sample_vocabulary_item, sample_stage1_response):
        """Test concurrent access to cache (simulated)"""
        import threading
        
        results = []
        errors = []
        
        def cache_operation(i):
            try:
                # Modified item for each thread
                item = VocabularyItem(position=i, term=f"concurrent_{i}", type="noun")
                response = Stage1Response(
                    term_number=i,
                    term=f"concurrent_{i}",
                    ipa=f"[concurrent_{i}]",
                    pos="noun",
                    primary_meaning=f"Meaning {i}",
                    other_meanings="",
                    metaphor="",
                    metaphor_noun="",
                    metaphor_action="",
                    suggested_location="",
                    anchor_object="",
                    anchor_sensory="",
                    explanation="",
                    comparison=Comparison(similar_to=[], different_from=[], commonly_confused_with=[]),
                    homonyms=[],
                    korean_keywords=[]
                )
                
                # Set and get
                cache_service.set_stage1_cache(item, response)
                cached = cache_service.get_stage1_cache(item)
                
                results.append((i, cached is not None))
            except Exception as e:
                errors.append((i, str(e)))
        
        # Run multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=cache_operation, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # All operations should succeed
        assert len(errors) == 0
        assert all(success for _, success in results)