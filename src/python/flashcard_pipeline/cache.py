"""Cache service for API responses"""

import os
import json
import hashlib
import asyncio
import aiofiles
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
import logging

from .models import (
    VocabularyItem,
    Stage1Response,
    Stage2Response,
    CacheStats
)
from .exceptions import CacheError


logger = logging.getLogger(__name__)


class CacheService:
    """File-based cache service for API responses"""
    
    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize cache service
        
        Args:
            cache_dir: Directory for cache files (defaults to .cache/flashcards)
        """
        self.cache_dir = Path(cache_dir or ".cache/flashcards")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Separate directories for each stage
        self.stage1_dir = self.cache_dir / "stage1"
        self.stage2_dir = self.cache_dir / "stage2"
        self.stage1_dir.mkdir(exist_ok=True)
        self.stage2_dir.mkdir(exist_ok=True)
        
        # Cache statistics
        self.stats = CacheStats()
        
        # Lock for thread-safe operations
        self._locks: Dict[str, asyncio.Lock] = {}
    
    def _get_cache_key(self, stage: int, vocabulary_item: VocabularyItem, 
                      stage1_result: Optional[Stage1Response] = None) -> str:
        """Generate cache key for an item
        
        Args:
            stage: Processing stage (1 or 2)
            vocabulary_item: Input vocabulary item
            stage1_result: Stage 1 result (required for stage 2)
            
        Returns:
            SHA256 hash as cache key
        """
        if stage == 1:
            # For Stage 1: hash term and type
            content = f"{vocabulary_item.term}:{vocabulary_item.type or 'unknown'}"
        else:
            # For Stage 2: hash term and stage1 result
            if not stage1_result:
                raise ValueError("stage1_result required for Stage 2 cache key")
            
            stage1_dict = stage1_result.dict()
            # Sort keys for consistent hashing
            stage1_json = json.dumps(stage1_dict, sort_keys=True, ensure_ascii=False)
            content = f"{vocabulary_item.term}:{stage1_json}"
        
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _get_cache_path(self, stage: int, cache_key: str) -> Path:
        """Get file path for cache entry
        
        Args:
            stage: Processing stage
            cache_key: Cache key
            
        Returns:
            Path to cache file
        """
        # Use subdirectories to avoid too many files in one directory
        subdir = cache_key[:2]
        cache_dir = self.stage1_dir if stage == 1 else self.stage2_dir
        
        path = cache_dir / subdir / f"{cache_key}.json"
        path.parent.mkdir(exist_ok=True)
        
        return path
    
    async def _get_lock(self, cache_key: str) -> asyncio.Lock:
        """Get lock for a specific cache key"""
        if cache_key not in self._locks:
            self._locks[cache_key] = asyncio.Lock()
        return self._locks[cache_key]
    
    async def get_stage1(self, vocabulary_item: VocabularyItem) -> Optional[Tuple[Stage1Response, int]]:
        """Get Stage 1 result from cache
        
        Args:
            vocabulary_item: Input vocabulary item
            
        Returns:
            Tuple of (Stage1Response, tokens_saved) if found, None otherwise
        """
        cache_key = self._get_cache_key(1, vocabulary_item)
        cache_path = self._get_cache_path(1, cache_key)
        
        lock = await self._get_lock(cache_key)
        async with lock:
            if not cache_path.exists():
                self.stats.stage1_misses += 1
                logger.debug(f"Stage 1 cache miss: {cache_key}")
                return None
            
            try:
                async with aiofiles.open(cache_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    data = json.loads(content)
                
                response = Stage1Response(**data['response'])
                tokens_saved = data.get('tokens', 350)  # Default estimate
                
                self.stats.stage1_hits += 1
                self.stats.total_tokens_saved += tokens_saved
                self.stats.estimated_cost_saved += (tokens_saved / 1_000_000) * 15.0
                
                logger.debug(f"Stage 1 cache hit: {cache_key}, saved {tokens_saved} tokens")
                return response, tokens_saved
                
            except Exception as e:
                logger.error(f"Error reading Stage 1 cache {cache_key}: {e}")
                self.stats.stage1_misses += 1
                return None
    
    async def save_stage1(self, vocabulary_item: VocabularyItem, 
                         response: Stage1Response, tokens_used: int) -> None:
        """Save Stage 1 result to cache
        
        Args:
            vocabulary_item: Input vocabulary item
            response: Stage 1 response
            tokens_used: Number of tokens used
        """
        cache_key = self._get_cache_key(1, vocabulary_item)
        cache_path = self._get_cache_path(1, cache_key)
        
        lock = await self._get_lock(cache_key)
        async with lock:
            try:
                data = {
                    'vocabulary_item': vocabulary_item.dict(),
                    'response': response.dict(),
                    'tokens': tokens_used,
                    'cached_at': datetime.utcnow().isoformat()
                }
                
                async with aiofiles.open(cache_path, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(data, ensure_ascii=False, indent=2))
                
                logger.debug(f"Saved Stage 1 cache: {cache_key}")
                
            except Exception as e:
                logger.error(f"Error saving Stage 1 cache {cache_key}: {e}")
                raise CacheError(f"Failed to save cache: {e}")
    
    async def get_stage2(self, vocabulary_item: VocabularyItem, 
                        stage1_result: Stage1Response) -> Optional[Tuple[Stage2Response, int]]:
        """Get Stage 2 result from cache
        
        Args:
            vocabulary_item: Input vocabulary item
            stage1_result: Stage 1 result
            
        Returns:
            Tuple of (Stage2Response, tokens_saved) if found, None otherwise
        """
        cache_key = self._get_cache_key(2, vocabulary_item, stage1_result)
        cache_path = self._get_cache_path(2, cache_key)
        
        lock = await self._get_lock(cache_key)
        async with lock:
            if not cache_path.exists():
                self.stats.stage2_misses += 1
                logger.debug(f"Stage 2 cache miss: {cache_key}")
                return None
            
            try:
                async with aiofiles.open(cache_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    data = json.loads(content)
                
                response = Stage2Response(**data['response'])
                tokens_saved = data.get('tokens', 1000)  # Default estimate
                
                self.stats.stage2_hits += 1
                self.stats.total_tokens_saved += tokens_saved
                self.stats.estimated_cost_saved += (tokens_saved / 1_000_000) * 15.0
                
                logger.debug(f"Stage 2 cache hit: {cache_key}, saved {tokens_saved} tokens")
                return response, tokens_saved
                
            except Exception as e:
                logger.error(f"Error reading Stage 2 cache {cache_key}: {e}")
                self.stats.stage2_misses += 1
                return None
    
    async def save_stage2(self, vocabulary_item: VocabularyItem,
                         stage1_result: Stage1Response,
                         response: Stage2Response, 
                         tokens_used: int) -> None:
        """Save Stage 2 result to cache
        
        Args:
            vocabulary_item: Input vocabulary item
            stage1_result: Stage 1 result used
            response: Stage 2 response
            tokens_used: Number of tokens used
        """
        cache_key = self._get_cache_key(2, vocabulary_item, stage1_result)
        cache_path = self._get_cache_path(2, cache_key)
        
        lock = await self._get_lock(cache_key)
        async with lock:
            try:
                data = {
                    'vocabulary_item': vocabulary_item.dict(),
                    'stage1_result': stage1_result.dict(),
                    'response': response.dict(),
                    'tokens': tokens_used,
                    'cached_at': datetime.utcnow().isoformat()
                }
                
                async with aiofiles.open(cache_path, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(data, ensure_ascii=False, indent=2))
                
                logger.debug(f"Saved Stage 2 cache: {cache_key}")
                
            except Exception as e:
                logger.error(f"Error saving Stage 2 cache {cache_key}: {e}")
                raise CacheError(f"Failed to save cache: {e}")
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics"""
        return self.stats
    
    async def clear_cache(self, stage: Optional[int] = None) -> int:
        """Clear cache files
        
        Args:
            stage: Specific stage to clear (1 or 2), or None for all
            
        Returns:
            Number of files deleted
        """
        count = 0
        
        dirs_to_clear = []
        if stage is None or stage == 1:
            dirs_to_clear.append(self.stage1_dir)
        if stage is None or stage == 2:
            dirs_to_clear.append(self.stage2_dir)
        
        for cache_dir in dirs_to_clear:
            for subdir in cache_dir.iterdir():
                if subdir.is_dir():
                    for cache_file in subdir.glob("*.json"):
                        try:
                            cache_file.unlink()
                            count += 1
                        except Exception as e:
                            logger.error(f"Error deleting cache file {cache_file}: {e}")
        
        # Reset stats if clearing all
        if stage is None:
            self.stats = CacheStats()
        elif stage == 1:
            self.stats.stage1_hits = 0
            self.stats.stage1_misses = 0
        elif stage == 2:
            self.stats.stage2_hits = 0
            self.stats.stage2_misses = 0
        
        logger.info(f"Cleared {count} cache files")
        return count
    
    async def warm_cache_from_batch(self, items: list[VocabularyItem]) -> Dict[str, Any]:
        """Pre-check cache for a batch of items
        
        Args:
            items: List of vocabulary items to check
            
        Returns:
            Dictionary with cache status for each item
        """
        results = {
            "total_items": len(items),
            "stage1_cached": 0,
            "stage2_potential": 0,
            "cache_keys": []
        }
        
        for item in items:
            # Check Stage 1 cache
            cache_key = self._get_cache_key(1, item)
            cache_path = self._get_cache_path(1, cache_key)
            
            if cache_path.exists():
                results["stage1_cached"] += 1
                
                # If Stage 1 is cached, check if Stage 2 might be cached too
                try:
                    async with aiofiles.open(cache_path, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        data = json.loads(content)
                        stage1_response = Stage1Response(**data['response'])
                    
                    stage2_key = self._get_cache_key(2, item, stage1_response)
                    stage2_path = self._get_cache_path(2, stage2_key)
                    
                    if stage2_path.exists():
                        results["stage2_potential"] += 1
                except Exception:
                    pass
            
            results["cache_keys"].append({
                "term": item.term,
                "stage1_key": cache_key,
                "stage1_cached": cache_path.exists()
            })
        
        return results


class MemoryCache:
    """In-memory LRU cache for frequently accessed items"""
    
    def __init__(self, max_size: int = 1000):
        """Initialize memory cache
        
        Args:
            max_size: Maximum number of items to cache
        """
        self.max_size = max_size
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.access_counts: Dict[str, int] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        async with self._lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                self.access_counts[key] = self.access_counts.get(key, 0) + 1
                return value
            return None
    
    async def set(self, key: str, value: Any) -> None:
        """Set item in cache"""
        async with self._lock:
            # If at capacity, remove least recently accessed item
            if len(self.cache) >= self.max_size and key not in self.cache:
                # Find item with lowest access count
                min_key = min(self.access_counts.keys(), 
                            key=lambda k: self.access_counts[k])
                del self.cache[min_key]
                del self.access_counts[min_key]
            
            self.cache[key] = (value, datetime.utcnow())
            self.access_counts[key] = 1
    
    async def clear(self) -> None:
        """Clear all cached items"""
        async with self._lock:
            self.cache.clear()
            self.access_counts.clear()