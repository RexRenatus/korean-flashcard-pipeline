#!/usr/bin/env python3
"""
Multi-layer cache manager for hook results.
Implements memory -> disk -> Redis caching with intelligent eviction.
"""
import hashlib
import json
import pickle
import time
import os
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
from pathlib import Path
from collections import OrderedDict
import logging

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

class CacheEntry:
    def __init__(self, value: Any, ttl: int = 300):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
        self.access_count = 0
        self.last_accessed = time.time()
        
    def is_valid(self) -> bool:
        """Check if cache entry is still valid."""
        return (time.time() - self.created_at) < self.ttl
        
    def access(self):
        """Record an access to this entry."""
        self.access_count += 1
        self.last_accessed = time.time()

class MemoryCache:
    """LRU memory cache with size limits."""
    def __init__(self, max_size: int = 100, max_memory_mb: int = 100):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.max_memory_mb = max_memory_mb
        self.current_memory = 0
        
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            entry = self.cache.pop(key)
            if entry.is_valid():
                entry.access()
                self.cache[key] = entry  # Move to end
                return entry.value
            else:
                self.current_memory -= self._estimate_size(entry.value)
        return None
        
    def set(self, key: str, value: Any, ttl: int = 300):
        # Check memory limit
        value_size = self._estimate_size(value)
        while (self.current_memory + value_size > self.max_memory_mb * 1024 * 1024 or
               len(self.cache) >= self.max_size):
            if not self.cache:
                break
            # Remove oldest
            oldest_key, oldest_entry = self.cache.popitem(last=False)
            self.current_memory -= self._estimate_size(oldest_entry.value)
            
        entry = CacheEntry(value, ttl)
        self.cache[key] = entry
        self.current_memory += value_size
        
    def _estimate_size(self, obj: Any) -> int:
        """Estimate object size in bytes."""
        try:
            return len(pickle.dumps(obj))
        except:
            return 1024  # Default 1KB

class DiskCache:
    """Persistent disk cache with compression."""
    def __init__(self, cache_dir: str = ".claude/cache/hooks", max_size_mb: int = 1000):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_mb = max_size_mb
        self.index_file = self.cache_dir / "index.json"
        self.index = self._load_index()
        
    def _load_index(self) -> Dict[str, Dict]:
        """Load cache index from disk."""
        if self.index_file.exists():
            try:
                with open(self.index_file) as f:
                    return json.load(f)
            except:
                pass
        return {}
        
    def _save_index(self):
        """Save cache index to disk."""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f)
            
    def get(self, key: str) -> Optional[Any]:
        if key in self.index:
            entry_info = self.index[key]
            if time.time() < entry_info['expires_at']:
                cache_file = self.cache_dir / f"{key}.pkl"
                if cache_file.exists():
                    try:
                        with open(cache_file, 'rb') as f:
                            return pickle.load(f)
                    except:
                        pass
            # Remove expired entry
            self._remove(key)
        return None
        
    def set(self, key: str, value: Any, ttl: int = 3600):
        # Check disk space
        self._ensure_space()
        
        cache_file = self.cache_dir / f"{key}.pkl"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(value, f)
                
            self.index[key] = {
                'expires_at': time.time() + ttl,
                'size': cache_file.stat().st_size,
                'created_at': time.time()
            }
            self._save_index()
        except Exception as e:
            logging.error(f"Failed to write disk cache: {e}")
            
    def _ensure_space(self):
        """Ensure we don't exceed disk space limit."""
        total_size = sum(info['size'] for info in self.index.values())
        
        if total_size > self.max_size_mb * 1024 * 1024:
            # Remove oldest entries
            sorted_entries = sorted(
                self.index.items(),
                key=lambda x: x[1]['created_at']
            )
            
            while total_size > self.max_size_mb * 1024 * 1024 * 0.8:  # 80% threshold
                if not sorted_entries:
                    break
                key, info = sorted_entries.pop(0)
                total_size -= info['size']
                self._remove(key)
                
    def _remove(self, key: str):
        """Remove entry from disk cache."""
        if key in self.index:
            del self.index[key]
            cache_file = self.cache_dir / f"{key}.pkl"
            cache_file.unlink(missing_ok=True)
            self._save_index()

class RedisCache:
    """Redis cache for distributed caching."""
    def __init__(self, connection_str: str = "redis://localhost:6379", namespace: str = "claude_hooks"):
        self.namespace = namespace
        self.client = None
        if REDIS_AVAILABLE:
            try:
                self.client = redis.from_url(connection_str)
                self.client.ping()
            except Exception as e:
                logging.warning(f"Redis connection failed: {e}")
                self.client = None
                
    def get(self, key: str) -> Optional[Any]:
        if not self.client:
            return None
            
        try:
            data = self.client.get(f"{self.namespace}:{key}")
            if data:
                return pickle.loads(data)
        except:
            pass
        return None
        
    def set(self, key: str, value: Any, ttl: int = 604800):
        if not self.client:
            return
            
        try:
            data = pickle.dumps(value)
            self.client.setex(
                f"{self.namespace}:{key}",
                ttl,
                data
            )
        except Exception as e:
            logging.error(f"Redis set failed: {e}")

class HookCacheManager:
    """
    Multi-layer cache manager with intelligent routing.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize cache layers
        self.memory_cache = MemoryCache(
            max_size=self.config.get('memory_max_items', 100),
            max_memory_mb=self.config.get('memory_max_mb', 100)
        )
        
        self.disk_cache = DiskCache(
            cache_dir=self.config.get('disk_cache_dir', '.claude/cache/hooks'),
            max_size_mb=self.config.get('disk_max_mb', 1000)
        )
        
        self.redis_cache = None
        if self.config.get('redis_enabled', False):
            self.redis_cache = RedisCache(
                connection_str=self.config.get('redis_connection', 'redis://localhost:6379'),
                namespace=self.config.get('redis_namespace', 'claude_hooks')
            )
            
        # Cache strategies
        self.strategies = self._load_strategies()
        
    def _load_strategies(self) -> Dict[str, Dict]:
        """Load cache strategies from config."""
        return self.config.get('strategies', {
            'default': {
                'layers': ['memory', 'disk'],
                'ttl': {'memory': 300, 'disk': 3600}
            }
        })
        
    def get_cache_key(self, hook_id: str, context: Dict[str, Any], 
                     key_pattern: Optional[str] = None) -> str:
        """Generate deterministic cache key."""
        if key_pattern:
            # Use custom pattern
            key_data = {
                'hook_id': hook_id,
                'file': context.get('file_path', ''),
                'hash': context.get('file_hash', ''),
                'query': context.get('query', ''),
                'keywords': context.get('keywords', [])
            }
            
            # Replace placeholders
            key = key_pattern
            for k, v in key_data.items():
                if isinstance(v, list):
                    v = ','.join(sorted(v))
                key = key.replace(f"{{{k}}}", str(v))
            return hashlib.sha256(key.encode()).hexdigest()
        else:
            # Default key generation
            content = json.dumps({
                'hook_id': hook_id,
                'context': context
            }, sort_keys=True)
            return hashlib.sha256(content.encode()).hexdigest()
            
    def get(self, hook_id: str, context: Dict[str, Any], 
           strategy: str = 'default') -> Optional[Any]:
        """Get from cache using specified strategy."""
        strategy_config = self.strategies.get(strategy, self.strategies['default'])
        layers = strategy_config.get('layers', ['memory'])
        
        key = self.get_cache_key(
            hook_id, 
            context, 
            strategy_config.get('key_pattern')
        )
        
        # Try each layer
        for layer in layers:
            value = None
            
            if layer == 'memory':
                value = self.memory_cache.get(key)
            elif layer == 'disk':
                value = self.disk_cache.get(key)
            elif layer == 'redis' and self.redis_cache:
                value = self.redis_cache.get(key)
                
            if value is not None:
                # Promote to higher layers
                self._promote_to_higher_layers(key, value, layer, layers, strategy_config)
                return value
                
        return None
        
    def set(self, hook_id: str, context: Dict[str, Any], value: Any,
           strategy: str = 'default'):
        """Set in cache using specified strategy."""
        strategy_config = self.strategies.get(strategy, self.strategies['default'])
        layers = strategy_config.get('layers', ['memory'])
        ttls = strategy_config.get('ttl', {})
        
        key = self.get_cache_key(
            hook_id,
            context,
            strategy_config.get('key_pattern')
        )
        
        # Write to all configured layers
        for layer in layers:
            ttl = ttls.get(layer, 300)
            
            if layer == 'memory':
                self.memory_cache.set(key, value, ttl)
            elif layer == 'disk':
                self.disk_cache.set(key, value, ttl)
            elif layer == 'redis' and self.redis_cache:
                self.redis_cache.set(key, value, ttl)
                
    def _promote_to_higher_layers(self, key: str, value: Any, found_layer: str,
                                 layers: List[str], strategy_config: Dict):
        """Promote value to higher cache layers."""
        ttls = strategy_config.get('ttl', {})
        found_index = layers.index(found_layer)
        
        # Promote to all higher layers
        for i in range(found_index):
            layer = layers[i]
            ttl = ttls.get(layer, 300)
            
            if layer == 'memory':
                self.memory_cache.set(key, value, ttl)
                
    def invalidate(self, pattern: str):
        """Invalidate cache entries matching pattern."""
        # For now, this is a placeholder
        # In production, implement pattern matching
        self.logger.info(f"Invalidating cache entries matching: {pattern}")
        
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            'memory': {
                'entries': len(self.memory_cache.cache),
                'memory_mb': self.memory_cache.current_memory / (1024 * 1024)
            },
            'disk': {
                'entries': len(self.disk_cache.index)
            }
        }
        
        if self.redis_cache and self.redis_cache.client:
            try:
                info = self.redis_cache.client.info()
                stats['redis'] = {
                    'connected': True,
                    'used_memory_mb': info.get('used_memory', 0) / (1024 * 1024)
                }
            except:
                stats['redis'] = {'connected': False}
                
        return stats

# Global cache instance
_cache_manager = None

def get_cache_manager(config: Optional[Dict[str, Any]] = None) -> HookCacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = HookCacheManager(config)
    return _cache_manager

if __name__ == "__main__":
    # Test cache manager
    logging.basicConfig(level=logging.INFO)
    
    config = {
        'memory_max_items': 10,
        'memory_max_mb': 10,
        'disk_max_mb': 100,
        'strategies': {
            'test': {
                'layers': ['memory', 'disk'],
                'ttl': {'memory': 5, 'disk': 60}
            }
        }
    }
    
    cache = HookCacheManager(config)
    
    # Test set/get
    context = {'file': 'test.py', 'operation': 'validate'}
    cache.set('test_hook', context, {'result': 'success'}, strategy='test')
    
    result = cache.get('test_hook', context, strategy='test')
    print(f"Cache hit: {result}")
    
    # Test memory eviction
    for i in range(15):
        cache.set(f'test_hook_{i}', {'n': i}, {'result': i}, strategy='test')
        
    print(f"Cache stats: {cache.get_stats()}")
    
    # Test expiration
    import time
    time.sleep(6)
    
    result = cache.get('test_hook', context, strategy='test')
    print(f"After expiry (memory): {result}")  # Should be None from memory
    
    # But still in disk
    result = cache.disk_cache.get(cache.get_cache_key('test_hook', context))
    print(f"Still in disk: {result}")