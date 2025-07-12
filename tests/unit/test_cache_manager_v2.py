"""Unit tests for advanced cache manager"""

import asyncio
import pytest
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from flashcard_pipeline.cache.cache_manager_v2 import (
    CacheManager,
    L1Cache,
    L2Cache,
    CacheEntry,
    CacheStrategy,
    EvictionPolicy,
    CacheStatistics,
)


class TestL1Cache:
    """Test L1 (in-memory) cache functionality"""
    
    @pytest.fixture
    def cache(self):
        """Create test L1 cache"""
        return L1Cache(
            max_size=5,
            max_memory_mb=1,
            eviction_policy=EvictionPolicy.LRU,
            default_ttl=60.0
        )
    
    @pytest.mark.asyncio
    async def test_basic_operations(self, cache):
        """Test basic get/set/delete operations"""
        # Set value
        await cache.set("key1", "value1")
        
        # Get value
        value = await cache.get("key1")
        assert value == "value1"
        assert cache.stats.hits == 1
        
        # Get non-existent key
        value = await cache.get("key2")
        assert value is None
        assert cache.stats.misses == 1
        
        # Delete key
        result = await cache.delete("key1")
        assert result is True
        
        # Verify deleted
        value = await cache.get("key1")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self, cache):
        """Test TTL-based expiration"""
        # Set with short TTL
        await cache.set("key1", "value1", ttl=0.1)
        
        # Should be available immediately
        value = await cache.get("key1")
        assert value == "value1"
        
        # Wait for expiration
        await asyncio.sleep(0.2)
        
        # Should be expired
        value = await cache.get("key1")
        assert value is None
        assert cache.stats.expirations == 1
    
    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Test LRU eviction policy"""
        cache = L1Cache(max_size=3, eviction_policy=EvictionPolicy.LRU)
        
        # Fill cache
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        # Access key1 to make it recently used
        await cache.get("key1")
        
        # Add new key - should evict key2 (least recently used)
        await cache.set("key4", "value4")
        
        assert await cache.get("key1") == "value1"  # Still there
        assert await cache.get("key2") is None      # Evicted
        assert await cache.get("key3") == "value3"  # Still there
        assert await cache.get("key4") == "value4"  # New key
        assert cache.stats.evictions == 1
    
    @pytest.mark.asyncio
    async def test_lfu_eviction(self):
        """Test LFU eviction policy"""
        cache = L1Cache(max_size=3, eviction_policy=EvictionPolicy.LFU)
        
        # Fill cache
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        # Access keys different number of times
        await cache.get("key1")  # 1 access
        await cache.get("key1")  # 2 accesses
        await cache.get("key2")  # 1 access
        # key3 has 0 accesses
        
        # Add new key - should evict key3 (least frequently used)
        await cache.set("key4", "value4")
        
        assert await cache.get("key1") == "value1"  # Most frequently used
        assert await cache.get("key2") == "value2"  # Some usage
        assert await cache.get("key3") is None      # Evicted (no usage)
        assert await cache.get("key4") == "value4"  # New key
    
    @pytest.mark.asyncio
    async def test_memory_limit_eviction(self, cache):
        """Test eviction based on memory limit"""
        # Set small memory limit
        cache.max_memory_bytes = 1000  # 1KB
        
        # Add large values
        large_value = "x" * 500  # ~500 bytes each
        
        await cache.set("key1", large_value)
        await cache.set("key2", large_value)
        
        # Should trigger memory-based eviction
        await cache.set("key3", large_value)
        
        # At least one key should be evicted
        assert cache.stats.evictions >= 1
        assert cache.stats.total_size_bytes <= cache.max_memory_bytes
    
    @pytest.mark.asyncio
    async def test_tags(self, cache):
        """Test cache entry tags"""
        await cache.set("key1", "value1", tags=["tag1", "tag2"])
        await cache.set("key2", "value2", tags=["tag2", "tag3"])
        
        # Verify tags are stored
        entry1 = cache._storage.get("key1")
        assert "tag1" in entry1.tags
        assert "tag2" in entry1.tags
    
    @pytest.mark.asyncio
    async def test_clear(self, cache):
        """Test clearing cache"""
        # Add multiple entries
        for i in range(3):
            await cache.set(f"key{i}", f"value{i}")
        
        assert cache.stats.entry_count == 3
        
        # Clear cache
        await cache.clear()
        
        assert cache.stats.entry_count == 0
        assert len(cache._storage) == 0
        assert cache.stats.total_size_bytes == 0


class TestL2Cache:
    """Test L2 cache functionality"""
    
    @pytest.fixture
    async def disk_cache(self, tmp_path):
        """Create test disk-based L2 cache"""
        cache = L2Cache(
            backend="disk",
            disk_path=str(tmp_path / "cache"),
            max_size_mb=10,
            compression=True
        )
        yield cache
        await cache.clear()
    
    @pytest.mark.asyncio
    async def test_disk_cache_operations(self, disk_cache):
        """Test disk cache basic operations"""
        # Set value
        await disk_cache.set("key1", {"data": "value1"})
        
        # Get value
        value = await disk_cache.get("key1")
        assert value == {"data": "value1"}
        assert disk_cache.stats.hits == 1
        
        # Delete value
        result = await disk_cache.delete("key1")
        assert result is True
        
        # Verify deleted
        value = await disk_cache.get("key1")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_disk_cache_persistence(self, tmp_path):
        """Test disk cache persistence across instances"""
        cache_path = str(tmp_path / "cache")
        
        # First instance
        cache1 = L2Cache(backend="disk", disk_path=cache_path)
        await cache1.set("persistent", "data")
        
        # Second instance should see the data
        cache2 = L2Cache(backend="disk", disk_path=cache_path)
        value = await cache2.get("persistent")
        assert value == "data"
    
    @pytest.mark.asyncio
    async def test_disk_cache_compression(self, disk_cache):
        """Test compression functionality"""
        # Large compressible data
        large_data = {"text": "x" * 10000}
        
        await disk_cache.set("compressed", large_data)
        
        # Check that file exists and is compressed
        file_name = list(disk_cache._disk_index.values())[0]["file"]
        file_path = disk_cache.disk_path / file_name
        
        assert file_path.exists()
        # Compressed size should be much smaller
        assert file_path.stat().st_size < 5000
        
        # Verify data integrity
        value = await disk_cache.get("compressed")
        assert value == large_data
    
    @pytest.mark.asyncio
    async def test_disk_cache_expiration(self, disk_cache):
        """Test TTL expiration in disk cache"""
        await disk_cache.set("expiring", "value", ttl=0.1)
        
        # Should exist immediately
        assert await disk_cache.get("expiring") == "value"
        
        # Wait for expiration
        await asyncio.sleep(0.2)
        
        # Should be expired
        assert await disk_cache.get("expiring") is None
        assert disk_cache.stats.expirations == 1
    
    @pytest.mark.asyncio
    async def test_disk_cache_size_limit(self, disk_cache):
        """Test disk cache size limit enforcement"""
        # Set very small limit
        disk_cache.max_size_bytes = 1000  # 1KB
        
        # Add data until limit exceeded
        for i in range(10):
            await disk_cache.set(f"key{i}", "x" * 200)
        
        # Should have evicted some entries
        assert disk_cache.stats.evictions > 0
        
        # Total size should be under limit
        total_size = sum(meta["size"] for meta in disk_cache._disk_index.values())
        assert total_size <= disk_cache.max_size_bytes
    
    @pytest.mark.asyncio
    async def test_namespace_isolation(self, tmp_path):
        """Test namespace isolation"""
        cache_path = str(tmp_path / "cache")
        
        cache1 = L2Cache(backend="disk", disk_path=cache_path, namespace="app1")
        cache2 = L2Cache(backend="disk", disk_path=cache_path, namespace="app2")
        
        await cache1.set("key", "value1")
        await cache2.set("key", "value2")
        
        # Same key but different namespaces
        assert await cache1.get("key") == "value1"
        assert await cache2.get("key") == "value2"


class TestCacheManager:
    """Test multi-tier cache manager"""
    
    @pytest.fixture
    async def manager(self, tmp_path):
        """Create test cache manager"""
        manager = CacheManager(
            l1_config={"max_size": 10},
            l2_config={
                "backend": "disk",
                "disk_path": str(tmp_path / "l2_cache")
            },
            enable_l2=True,
            strategy=CacheStrategy.CACHE_ASIDE,
            stampede_protection=True
        )
        yield manager
        await manager.clear()
    
    @pytest.mark.asyncio
    async def test_multi_tier_caching(self, manager):
        """Test L1/L2 cache interaction"""
        # Set value - should go to both L1 and L2
        await manager.set("key1", "value1")
        
        # Get from L1 (should hit)
        value = await manager.get("key1")
        assert value == "value1"
        assert manager.l1_cache.stats.hits == 1
        
        # Remove from L1
        await manager.l1_cache.delete(manager._make_versioned_key("key1"))
        
        # Get should hit L2 and promote to L1
        value = await manager.get("key1")
        assert value == "value1"
        assert manager.l1_cache.stats.misses == 1
        assert manager.l2_cache.stats.hits == 1
        
        # Should now be in L1
        value = await manager.get("key1")
        assert value == "value1"
        assert manager.l1_cache.stats.hits == 2
    
    @pytest.mark.asyncio
    async def test_compute_function(self, manager):
        """Test cache-aside with compute function"""
        compute_count = 0
        
        async def compute_value():
            nonlocal compute_count
            compute_count += 1
            await asyncio.sleep(0.1)  # Simulate expensive computation
            return f"computed_{compute_count}"
        
        # First call should compute
        value = await manager.get("key1", compute_value)
        assert value == "computed_1"
        assert compute_count == 1
        
        # Second call should use cache
        value = await manager.get("key1", compute_value)
        assert value == "computed_1"
        assert compute_count == 1  # Not called again
    
    @pytest.mark.asyncio
    async def test_stampede_protection(self, manager):
        """Test cache stampede protection"""
        compute_count = 0
        
        async def slow_compute():
            nonlocal compute_count
            compute_count += 1
            await asyncio.sleep(0.2)
            return f"result_{compute_count}"
        
        # Launch multiple concurrent requests for same key
        tasks = [
            manager.get("stampede_key", slow_compute)
            for _ in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should get same result
        assert all(r == "result_1" for r in results)
        # Compute should only be called once
        assert compute_count == 1
    
    @pytest.mark.asyncio
    async def test_versioning(self, manager):
        """Test cache versioning"""
        await manager.set("key1", "value1")
        
        # Change version
        manager.version = 2
        
        # Should not find old version
        value = await manager.get("key1")
        assert value is None
        
        # Set with new version
        await manager.set("key1", "value2")
        value = await manager.get("key1")
        assert value == "value2"
    
    @pytest.mark.asyncio
    async def test_tag_based_deletion(self, manager):
        """Test deleting entries by tag"""
        await manager.set("key1", "value1", tags=["tag1", "tag2"])
        await manager.set("key2", "value2", tags=["tag2", "tag3"])
        await manager.set("key3", "value3", tags=["tag3"])
        
        # Delete by tag
        await manager.delete_by_tag("tag2")
        
        # key1 and key2 should be deleted from L1
        assert await manager.l1_cache.get(manager._make_versioned_key("key1")) is None
        assert await manager.l1_cache.get(manager._make_versioned_key("key2")) is None
        assert await manager.l1_cache.get(manager._make_versioned_key("key3")) == "value3"
    
    @pytest.mark.asyncio
    async def test_cache_warming(self, manager):
        """Test cache warming functionality"""
        def compute_fn(key: str):
            return f"warmed_{key}"
        
        keys = ["warm1", "warm2", "warm3"]
        
        # Warm cache
        await manager.warm_cache(keys, compute_fn, ttl=60.0, batch_size=2)
        
        # All keys should be cached
        for key in keys:
            value = await manager.get(key)
            assert value == f"warmed_{key}"
    
    @pytest.mark.asyncio
    async def test_refresh_ahead(self, manager):
        """Test refresh-ahead strategy"""
        refresh_count = 0
        
        async def compute_fn():
            nonlocal refresh_count
            refresh_count += 1
            return f"refresh_{refresh_count}"
        
        # Start refresh-ahead
        await manager.start_refresh_ahead(
            "refresh_key",
            compute_fn,
            ttl=0.3,
            refresh_before=0.1
        )
        
        # Initial value
        value = await manager.get("refresh_key")
        assert value == "refresh_1"
        
        # Wait for refresh
        await asyncio.sleep(0.25)
        
        # Should have refreshed
        value = await manager.get("refresh_key")
        assert value == "refresh_2"
        
        # Cancel task
        if "refresh_key" in manager._warm_tasks:
            manager._warm_tasks["refresh_key"].cancel()
    
    @pytest.mark.asyncio
    async def test_statistics(self, manager):
        """Test cache statistics"""
        # Generate some activity
        await manager.set("key1", "value1")
        await manager.get("key1")  # L1 hit
        await manager.get("key2")  # Miss
        
        stats = manager.get_statistics()
        
        assert "l1" in stats
        assert "l2" in stats
        assert "overall_hit_rate" in stats
        
        assert stats["l1"]["hit_rate"] == 0.5  # 1 hit, 1 miss
        assert stats["l1"]["entries"] == 1
        assert stats["l1"]["evictions"] == 0
    
    @pytest.mark.asyncio
    async def test_write_through_strategy(self):
        """Test write-through caching strategy"""
        storage = {}
        
        async def compute_fn():
            return storage.get("key1", "not_found")
        
        # Simulate write-through
        manager = CacheManager(strategy=CacheStrategy.WRITE_THROUGH)
        
        # Write should go to cache
        await manager.set("key1", "value1")
        
        # In real implementation, this would also write to storage
        storage["key1"] = "value1"
        
        # Read should come from cache
        value = await manager.get("key1", compute_fn)
        assert value == "value1"


class TestCacheEntry:
    """Test cache entry functionality"""
    
    def test_entry_creation(self):
        """Test cache entry creation"""
        entry = CacheEntry(
            key="test",
            value="data",
            expires_at=time.time() + 60
        )
        
        assert entry.key == "test"
        assert entry.value == "data"
        assert not entry.is_expired()
        assert entry.access_count == 0
    
    def test_entry_expiration(self):
        """Test entry expiration check"""
        # Already expired
        entry = CacheEntry(
            key="test",
            value="data",
            expires_at=time.time() - 1
        )
        
        assert entry.is_expired()
        
        # No expiration
        entry = CacheEntry(
            key="test",
            value="data",
            expires_at=None
        )
        
        assert not entry.is_expired()
    
    def test_entry_access(self):
        """Test entry access tracking"""
        entry = CacheEntry(key="test", value="data")
        original_time = entry.accessed_at
        
        time.sleep(0.01)
        entry.access()
        
        assert entry.access_count == 1
        assert entry.accessed_at > original_time