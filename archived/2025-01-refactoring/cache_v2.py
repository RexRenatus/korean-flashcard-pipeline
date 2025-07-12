"""
Modernized Cache System with Database Integration

This module provides an enhanced caching system with:
- Database-backed cache metadata
- Compression support
- Cache warming strategies
- Automatic invalidation rules
- Performance metrics
"""

import os
import json
import hashlib
import asyncio
import aiofiles
import gzip
import zlib
import lz4.frame
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List, Union
from datetime import datetime, timedelta
from enum import Enum
import logging

from .models import (
    VocabularyItem,
    Stage1Response,
    Stage2Response,
    CacheStats
)
from .exceptions import CacheError
from .database import DatabaseManager

logger = logging.getLogger(__name__)


class CompressionType(Enum):
    """Supported compression algorithms"""
    NONE = "none"
    GZIP = "gzip"
    ZLIB = "zlib"
    LZ4 = "lz4"


class CacheInvalidationRule(Enum):
    """Cache invalidation strategies"""
    TTL = "ttl"  # Time to live
    LRU = "lru"  # Least recently used
    LFU = "lfu"  # Least frequently used
    FIFO = "fifo"  # First in, first out
    SIZE = "size"  # Size-based eviction


class ModernCacheService:
    """Enhanced cache service with database integration"""
    
    def __init__(
        self,
        cache_dir: Optional[str] = None,
        db_path: Optional[str] = None,
        compression: CompressionType = CompressionType.LZ4,
        max_size_mb: int = 1000,
        ttl_hours: int = 168,  # 1 week
        enable_stats: bool = True
    ):
        """
        Initialize modern cache service
        
        Args:
            cache_dir: Directory for cache files
            db_path: Path to database for metadata
            compression: Compression algorithm to use
            max_size_mb: Maximum cache size in MB
            ttl_hours: Time to live for cache entries
            enable_stats: Whether to track statistics
        """
        self.cache_dir = Path(cache_dir or ".cache/flashcards_v2")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Separate directories for each stage
        self.stage1_dir = self.cache_dir / "stage1"
        self.stage2_dir = self.cache_dir / "stage2"
        self.metadata_dir = self.cache_dir / "metadata"
        
        for dir_path in [self.stage1_dir, self.stage2_dir, self.metadata_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # Configuration
        self.compression = compression
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.ttl_seconds = ttl_hours * 3600
        self.enable_stats = enable_stats
        
        # Database for cache metadata
        self.db_manager = DatabaseManager(db_path or "pipeline.db")
        self._init_cache_tables()
        
        # Cache statistics
        self.stats = CacheStats() if enable_stats else None
        
        # Locks for thread-safe operations
        self._locks: Dict[str, asyncio.Lock] = {}
        self._compression_locks: Dict[str, asyncio.Lock] = {}
        
        # Memory cache for hot data
        self._memory_cache: Dict[str, Tuple[Any, datetime]] = {}
        self._memory_cache_max = 100
    
    def _init_cache_tables(self):
        """Initialize cache metadata tables"""
        with self.db_manager.get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS cache_metadata (
                    cache_key TEXT PRIMARY KEY,
                    stage INTEGER NOT NULL,
                    term TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    compression_type TEXT NOT NULL,
                    compression_ratio REAL,
                    created_at DATETIME NOT NULL,
                    accessed_at DATETIME NOT NULL,
                    access_count INTEGER DEFAULT 1,
                    ttl_expires_at DATETIME,
                    is_hot BOOLEAN DEFAULT 0,
                    tokens_saved INTEGER,
                    cost_saved REAL
                );
                
                CREATE INDEX IF NOT EXISTS idx_cache_stage ON cache_metadata(stage);
                CREATE INDEX IF NOT EXISTS idx_cache_term ON cache_metadata(term);
                CREATE INDEX IF NOT EXISTS idx_cache_accessed ON cache_metadata(accessed_at);
                CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache_metadata(ttl_expires_at);
                CREATE INDEX IF NOT EXISTS idx_cache_hot ON cache_metadata(is_hot);
                
                CREATE TABLE IF NOT EXISTS cache_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    stage1_hits INTEGER DEFAULT 0,
                    stage1_misses INTEGER DEFAULT 0,
                    stage2_hits INTEGER DEFAULT 0,
                    stage2_misses INTEGER DEFAULT 0,
                    total_size_bytes INTEGER DEFAULT 0,
                    total_entries INTEGER DEFAULT 0,
                    compression_savings_bytes INTEGER DEFAULT 0,
                    tokens_saved INTEGER DEFAULT 0,
                    cost_saved REAL DEFAULT 0
                );
                
                CREATE TABLE IF NOT EXISTS cache_warming_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    term TEXT NOT NULL,
                    priority INTEGER DEFAULT 0,
                    added_at DATETIME NOT NULL,
                    processed BOOLEAN DEFAULT 0,
                    processed_at DATETIME
                );
            """)
    
    def _get_cache_key(self, stage: int, vocabulary_item: VocabularyItem, 
                      stage1_result: Optional[Stage1Response] = None) -> str:
        """Generate cache key for an item"""
        if stage == 1:
            content = f"{vocabulary_item.term}:{vocabulary_item.type or 'unknown'}"
        else:
            if not stage1_result:
                raise ValueError("stage1_result required for Stage 2 cache key")
            
            stage1_dict = stage1_result.model_dump()
            stage1_json = json.dumps(stage1_dict, sort_keys=True, ensure_ascii=False)
            content = f"{vocabulary_item.term}:{stage1_json}"
        
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _get_cache_path(self, stage: int, cache_key: str) -> Path:
        """Get file path for cache entry"""
        subdir = cache_key[:2]
        cache_dir = self.stage1_dir if stage == 1 else self.stage2_dir
        
        # Add compression extension
        ext = ".json"
        if self.compression != CompressionType.NONE:
            ext += f".{self.compression.value}"
        
        path = cache_dir / subdir / f"{cache_key}{ext}"
        path.parent.mkdir(exist_ok=True)
        
        return path
    
    async def _compress_data(self, data: bytes) -> Tuple[bytes, float]:
        """Compress data using configured algorithm"""
        original_size = len(data)
        
        if self.compression == CompressionType.NONE:
            return data, 1.0
        elif self.compression == CompressionType.GZIP:
            compressed = gzip.compress(data, compresslevel=6)
        elif self.compression == CompressionType.ZLIB:
            compressed = zlib.compress(data, level=6)
        elif self.compression == CompressionType.LZ4:
            compressed = lz4.frame.compress(data, compression_level=9)
        else:
            raise ValueError(f"Unknown compression type: {self.compression}")
        
        ratio = len(compressed) / original_size
        return compressed, ratio
    
    async def _decompress_data(self, data: bytes) -> bytes:
        """Decompress data based on compression type"""
        if self.compression == CompressionType.NONE:
            return data
        elif self.compression == CompressionType.GZIP:
            return gzip.decompress(data)
        elif self.compression == CompressionType.ZLIB:
            return zlib.decompress(data)
        elif self.compression == CompressionType.LZ4:
            return lz4.frame.decompress(data)
        else:
            raise ValueError(f"Unknown compression type: {self.compression}")
    
    async def _get_lock(self, cache_key: str) -> asyncio.Lock:
        """Get lock for a specific cache key"""
        if cache_key not in self._locks:
            self._locks[cache_key] = asyncio.Lock()
        return self._locks[cache_key]
    
    async def _update_access_metadata(self, cache_key: str, tokens_saved: int = 0):
        """Update cache access metadata"""
        with self.db_manager.get_connection() as conn:
            conn.execute("""
                UPDATE cache_metadata 
                SET accessed_at = ?, access_count = access_count + 1
                WHERE cache_key = ?
            """, (datetime.now(), cache_key))
            
            # Mark as hot if accessed frequently
            conn.execute("""
                UPDATE cache_metadata 
                SET is_hot = 1
                WHERE cache_key = ? AND access_count > 5
            """, (cache_key,))
    
    async def get_stage1(self, vocabulary_item: VocabularyItem) -> Optional[Tuple[Stage1Response, int]]:
        """Get Stage 1 result from cache"""
        cache_key = self._get_cache_key(1, vocabulary_item)
        
        # Check memory cache first
        if cache_key in self._memory_cache:
            response, _ = self._memory_cache[cache_key]
            if isinstance(response, Stage1Response):
                logger.debug(f"Stage 1 memory cache hit: {cache_key}")
                return response, 350  # Estimated tokens saved
        
        cache_path = self._get_cache_path(1, cache_key)
        
        lock = await self._get_lock(cache_key)
        async with lock:
            if not cache_path.exists():
                if self.stats:
                    self.stats.stage1_misses += 1
                logger.debug(f"Stage 1 cache miss: {cache_key}")
                return None
            
            try:
                # Read compressed data
                async with aiofiles.open(cache_path, 'rb') as f:
                    compressed_data = await f.read()
                
                # Decompress
                data = await self._decompress_data(compressed_data)
                content = data.decode('utf-8')
                
                # Parse JSON
                cache_data = json.loads(content)
                response = Stage1Response(**cache_data['response'])
                tokens_saved = cache_data.get('tokens', 350)
                
                # Update statistics
                if self.stats:
                    self.stats.stage1_hits += 1
                    self.stats.total_tokens_saved += tokens_saved
                    self.stats.estimated_cost_saved += (tokens_saved / 1_000_000) * 15.0
                
                # Update access metadata
                await self._update_access_metadata(cache_key, tokens_saved)
                
                # Add to memory cache
                if len(self._memory_cache) < self._memory_cache_max:
                    self._memory_cache[cache_key] = (response, datetime.now())
                
                logger.debug(f"Stage 1 cache hit: {cache_key}, saved {tokens_saved} tokens")
                return response, tokens_saved
                
            except Exception as e:
                logger.error(f"Error reading Stage 1 cache {cache_key}: {e}")
                if self.stats:
                    self.stats.stage1_misses += 1
                return None
    
    async def save_stage1(self, vocabulary_item: VocabularyItem, 
                         response: Stage1Response, tokens_used: int) -> None:
        """Save Stage 1 result to cache"""
        cache_key = self._get_cache_key(1, vocabulary_item)
        cache_path = self._get_cache_path(1, cache_key)
        
        lock = await self._get_lock(cache_key)
        async with lock:
            try:
                # Prepare data
                data = {
                    'vocabulary_item': vocabulary_item.model_dump(),
                    'response': response.model_dump(),
                    'tokens': tokens_used,
                    'cached_at': datetime.now().isoformat()
                }
                
                # Convert to JSON and compress
                json_data = json.dumps(data, ensure_ascii=False, indent=2)
                compressed_data, ratio = await self._compress_data(json_data.encode('utf-8'))
                
                # Write compressed data
                async with aiofiles.open(cache_path, 'wb') as f:
                    await f.write(compressed_data)
                
                # Save metadata to database
                with self.db_manager.get_connection() as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO cache_metadata (
                            cache_key, stage, term, file_path, size_bytes,
                            compression_type, compression_ratio, created_at,
                            accessed_at, ttl_expires_at, tokens_saved
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        cache_key, 1, vocabulary_item.term, str(cache_path),
                        len(compressed_data), self.compression.value, ratio,
                        datetime.now(), datetime.now(),
                        datetime.now() + timedelta(seconds=self.ttl_seconds),
                        tokens_used
                    ))
                
                # Add to memory cache
                self._memory_cache[cache_key] = (response, datetime.now())
                
                logger.debug(f"Saved Stage 1 cache: {cache_key}, compression ratio: {ratio:.2f}")
                
            except Exception as e:
                logger.error(f"Error saving Stage 1 cache {cache_key}: {e}")
                raise CacheError(f"Failed to save cache: {e}")
    
    async def get_stage2(self, vocabulary_item: VocabularyItem, 
                        stage1_result: Stage1Response) -> Optional[Tuple[Stage2Response, int]]:
        """Get Stage 2 result from cache"""
        cache_key = self._get_cache_key(2, vocabulary_item, stage1_result)
        
        # Check memory cache first
        if cache_key in self._memory_cache:
            response, _ = self._memory_cache[cache_key]
            if isinstance(response, Stage2Response):
                logger.debug(f"Stage 2 memory cache hit: {cache_key}")
                return response, 1000  # Estimated tokens saved
        
        cache_path = self._get_cache_path(2, cache_key)
        
        lock = await self._get_lock(cache_key)
        async with lock:
            if not cache_path.exists():
                if self.stats:
                    self.stats.stage2_misses += 1
                logger.debug(f"Stage 2 cache miss: {cache_key}")
                return None
            
            try:
                # Read compressed data
                async with aiofiles.open(cache_path, 'rb') as f:
                    compressed_data = await f.read()
                
                # Decompress
                data = await self._decompress_data(compressed_data)
                content = data.decode('utf-8')
                
                # Parse JSON
                cache_data = json.loads(content)
                response = Stage2Response(**cache_data['response'])
                tokens_saved = cache_data.get('tokens', 1000)
                
                # Update statistics
                if self.stats:
                    self.stats.stage2_hits += 1
                    self.stats.total_tokens_saved += tokens_saved
                    self.stats.estimated_cost_saved += (tokens_saved / 1_000_000) * 15.0
                
                # Update access metadata
                await self._update_access_metadata(cache_key, tokens_saved)
                
                # Add to memory cache
                if len(self._memory_cache) < self._memory_cache_max:
                    self._memory_cache[cache_key] = (response, datetime.now())
                
                logger.debug(f"Stage 2 cache hit: {cache_key}, saved {tokens_saved} tokens")
                return response, tokens_saved
                
            except Exception as e:
                logger.error(f"Error reading Stage 2 cache {cache_key}: {e}")
                if self.stats:
                    self.stats.stage2_misses += 1
                return None
    
    async def save_stage2(self, vocabulary_item: VocabularyItem,
                         stage1_result: Stage1Response,
                         response: Stage2Response, 
                         tokens_used: int) -> None:
        """Save Stage 2 result to cache"""
        cache_key = self._get_cache_key(2, vocabulary_item, stage1_result)
        cache_path = self._get_cache_path(2, cache_key)
        
        lock = await self._get_lock(cache_key)
        async with lock:
            try:
                # Prepare data
                data = {
                    'vocabulary_item': vocabulary_item.model_dump(),
                    'stage1_result': stage1_result.model_dump(),
                    'response': response.model_dump(),
                    'tokens': tokens_used,
                    'cached_at': datetime.now().isoformat()
                }
                
                # Convert to JSON and compress
                json_data = json.dumps(data, ensure_ascii=False, indent=2)
                compressed_data, ratio = await self._compress_data(json_data.encode('utf-8'))
                
                # Write compressed data
                async with aiofiles.open(cache_path, 'wb') as f:
                    await f.write(compressed_data)
                
                # Save metadata to database
                with self.db_manager.get_connection() as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO cache_metadata (
                            cache_key, stage, term, file_path, size_bytes,
                            compression_type, compression_ratio, created_at,
                            accessed_at, ttl_expires_at, tokens_saved
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        cache_key, 2, vocabulary_item.term, str(cache_path),
                        len(compressed_data), self.compression.value, ratio,
                        datetime.now(), datetime.now(),
                        datetime.now() + timedelta(seconds=self.ttl_seconds),
                        tokens_used
                    ))
                
                # Add to memory cache
                self._memory_cache[cache_key] = (response, datetime.now())
                
                logger.debug(f"Saved Stage 2 cache: {cache_key}, compression ratio: {ratio:.2f}")
                
            except Exception as e:
                logger.error(f"Error saving Stage 2 cache {cache_key}: {e}")
                raise CacheError(f"Failed to save cache: {e}")
    
    async def invalidate_expired(self) -> int:
        """Remove expired cache entries"""
        count = 0
        
        with self.db_manager.get_connection() as conn:
            # Get expired entries
            expired = conn.execute("""
                SELECT cache_key, file_path FROM cache_metadata
                WHERE ttl_expires_at < ?
            """, (datetime.now(),)).fetchall()
            
            for row in expired:
                cache_key, file_path = row
                try:
                    # Delete file
                    Path(file_path).unlink(missing_ok=True)
                    
                    # Remove from memory cache
                    self._memory_cache.pop(cache_key, None)
                    
                    count += 1
                except Exception as e:
                    logger.error(f"Error deleting expired cache {cache_key}: {e}")
            
            # Remove metadata
            conn.execute("""
                DELETE FROM cache_metadata
                WHERE ttl_expires_at < ?
            """, (datetime.now(),))
        
        logger.info(f"Invalidated {count} expired cache entries")
        return count
    
    async def invalidate_by_size(self, target_size_mb: Optional[int] = None) -> int:
        """Remove cache entries to meet size constraints"""
        target_size = (target_size_mb or self.max_size_bytes // 1024 // 1024) * 1024 * 1024
        count = 0
        
        with self.db_manager.get_connection() as conn:
            # Get current total size
            total_size = conn.execute("""
                SELECT SUM(size_bytes) FROM cache_metadata
            """).fetchone()[0] or 0
            
            if total_size <= target_size:
                return 0
            
            # Get entries ordered by LRU (least recently used)
            entries = conn.execute("""
                SELECT cache_key, file_path, size_bytes
                FROM cache_metadata
                WHERE is_hot = 0
                ORDER BY accessed_at ASC
            """).fetchall()
            
            size_freed = 0
            for cache_key, file_path, size_bytes in entries:
                if total_size - size_freed <= target_size:
                    break
                
                try:
                    # Delete file
                    Path(file_path).unlink(missing_ok=True)
                    
                    # Remove from memory cache
                    self._memory_cache.pop(cache_key, None)
                    
                    # Remove metadata
                    conn.execute("""
                        DELETE FROM cache_metadata WHERE cache_key = ?
                    """, (cache_key,))
                    
                    size_freed += size_bytes
                    count += 1
                except Exception as e:
                    logger.error(f"Error during size-based eviction {cache_key}: {e}")
        
        logger.info(f"Evicted {count} entries to free {size_freed / 1024 / 1024:.2f} MB")
        return count
    
    async def warm_cache(self, terms: List[str], priority_boost: int = 10) -> Dict[str, Any]:
        """Add terms to cache warming queue"""
        results = {"queued": 0, "already_queued": 0}
        
        with self.db_manager.get_connection() as conn:
            for term in terms:
                # Check if already queued
                existing = conn.execute("""
                    SELECT id FROM cache_warming_queue
                    WHERE term = ? AND processed = 0
                """, (term,)).fetchone()
                
                if existing:
                    # Boost priority
                    conn.execute("""
                        UPDATE cache_warming_queue
                        SET priority = priority + ?
                        WHERE id = ?
                    """, (priority_boost, existing[0]))
                    results["already_queued"] += 1
                else:
                    # Add to queue
                    conn.execute("""
                        INSERT INTO cache_warming_queue (term, priority, added_at)
                        VALUES (?, ?, ?)
                    """, (term, priority_boost, datetime.now()))
                    results["queued"] += 1
        
        return results
    
    async def get_warming_candidates(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get high-priority terms for cache warming"""
        with self.db_manager.get_connection() as conn:
            candidates = conn.execute("""
                SELECT term, priority FROM cache_warming_queue
                WHERE processed = 0
                ORDER BY priority DESC, added_at ASC
                LIMIT ?
            """, (limit,)).fetchall()
            
            return [{"term": term, "priority": priority} 
                   for term, priority in candidates]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        with self.db_manager.get_connection() as conn:
            # Get metadata stats
            stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_entries,
                    SUM(size_bytes) as total_size,
                    AVG(compression_ratio) as avg_compression,
                    SUM(tokens_saved) as total_tokens_saved,
                    COUNT(CASE WHEN is_hot = 1 THEN 1 END) as hot_entries,
                    COUNT(CASE WHEN stage = 1 THEN 1 END) as stage1_entries,
                    COUNT(CASE WHEN stage = 2 THEN 1 END) as stage2_entries
                FROM cache_metadata
            """).fetchone()
            
            # Get recent hit/miss stats if available
            if self.stats:
                stats_dict = self.stats.model_dump()
            else:
                stats_dict = {}
            
            # Combine database and runtime stats
            stats_dict.update({
                "total_entries": stats[0] or 0,
                "total_size_mb": (stats[1] or 0) / 1024 / 1024,
                "avg_compression_ratio": stats[2] or 1.0,
                "total_tokens_saved": stats[3] or 0,
                "hot_entries": stats[4] or 0,
                "stage1_entries": stats[5] or 0,
                "stage2_entries": stats[6] or 0,
                "compression_type": self.compression.value,
                "ttl_hours": self.ttl_seconds // 3600
            })
            
            # Calculate hit rates
            if self.stats:
                stage1_total = self.stats.stage1_hits + self.stats.stage1_misses
                stage2_total = self.stats.stage2_hits + self.stats.stage2_misses
                
                stats_dict["stage1_hit_rate"] = (
                    self.stats.stage1_hits / stage1_total if stage1_total > 0 else 0
                )
                stats_dict["stage2_hit_rate"] = (
                    self.stats.stage2_hits / stage2_total if stage2_total > 0 else 0
                )
            
            return stats_dict
    
    async def analyze_cache_performance(self) -> Dict[str, Any]:
        """Analyze cache performance and provide recommendations"""
        stats = self.get_stats()
        
        recommendations = []
        
        # Check hit rates
        if stats.get("stage1_hit_rate", 0) < 0.5:
            recommendations.append(
                "Low Stage 1 hit rate. Consider pre-warming frequently used terms."
            )
        
        if stats.get("stage2_hit_rate", 0) < 0.3:
            recommendations.append(
                "Low Stage 2 hit rate. Stage 2 results are more volatile due to context dependency."
            )
        
        # Check compression effectiveness
        if stats.get("avg_compression_ratio", 1.0) > 0.8:
            recommendations.append(
                "Low compression ratio. Consider using a more aggressive compression algorithm."
            )
        
        # Check cache size
        if stats.get("total_size_mb", 0) > self.max_size_bytes / 1024 / 1024 * 0.9:
            recommendations.append(
                "Cache is near capacity. Consider increasing max size or reducing TTL."
            )
        
        # Check hot entries
        hot_ratio = stats.get("hot_entries", 0) / max(stats.get("total_entries", 1), 1)
        if hot_ratio < 0.1:
            recommendations.append(
                "Few hot entries. Cache may benefit from more aggressive warming strategy."
            )
        
        return {
            "stats": stats,
            "recommendations": recommendations,
            "health_score": self._calculate_health_score(stats)
        }
    
    def _calculate_health_score(self, stats: Dict[str, Any]) -> float:
        """Calculate overall cache health score (0-100)"""
        score = 100.0
        
        # Penalize low hit rates
        score -= (1 - stats.get("stage1_hit_rate", 0)) * 20
        score -= (1 - stats.get("stage2_hit_rate", 0)) * 10
        
        # Penalize near-capacity
        size_ratio = stats.get("total_size_mb", 0) / (self.max_size_bytes / 1024 / 1024)
        if size_ratio > 0.9:
            score -= 20
        elif size_ratio > 0.8:
            score -= 10
        
        # Reward good compression
        if stats.get("avg_compression_ratio", 1.0) < 0.5:
            score += 10
        
        # Reward hot entries
        hot_ratio = stats.get("hot_entries", 0) / max(stats.get("total_entries", 1), 1)
        score += hot_ratio * 10
        
        return max(0, min(100, score))
    
    async def clear_cache(self, stage: Optional[int] = None) -> int:
        """Clear cache files and metadata"""
        count = 0
        
        with self.db_manager.get_connection() as conn:
            # Get entries to delete
            if stage:
                entries = conn.execute("""
                    SELECT cache_key, file_path FROM cache_metadata
                    WHERE stage = ?
                """, (stage,)).fetchall()
            else:
                entries = conn.execute("""
                    SELECT cache_key, file_path FROM cache_metadata
                """).fetchall()
            
            # Delete files
            for cache_key, file_path in entries:
                try:
                    Path(file_path).unlink(missing_ok=True)
                    self._memory_cache.pop(cache_key, None)
                    count += 1
                except Exception as e:
                    logger.error(f"Error deleting cache file {file_path}: {e}")
            
            # Clear metadata
            if stage:
                conn.execute("DELETE FROM cache_metadata WHERE stage = ?", (stage,))
            else:
                conn.execute("DELETE FROM cache_metadata")
            
            # Reset stats
            if self.stats:
                if stage is None:
                    self.stats = CacheStats()
                elif stage == 1:
                    self.stats.stage1_hits = 0
                    self.stats.stage1_misses = 0
                elif stage == 2:
                    self.stats.stage2_hits = 0
                    self.stats.stage2_misses = 0
        
        logger.info(f"Cleared {count} cache entries")
        return count