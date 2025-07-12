# Modern Cache System Guide

## Overview

The flashcard pipeline includes a modernized cache system that provides:

1. **Database-backed metadata** - Track cache usage and performance
2. **Compression support** - LZ4, GZIP, ZLIB compression algorithms
3. **Cache warming** - Proactive caching of high-priority terms
4. **Automatic invalidation** - TTL and size-based eviction
5. **Performance analytics** - Detailed cache statistics and recommendations

## Architecture

### Core Components

```python
from flashcard_pipeline.cache_v2 import (
    ModernCacheService,     # Main cache service
    CompressionType,        # Compression options
    CacheInvalidationRule   # Invalidation strategies
)
```

### Storage Structure

```
.cache/flashcards_v2/
├── stage1/            # Stage 1 cache files
│   ├── 00/           # Subdirectory (first 2 chars of hash)
│   ├── 01/
│   └── ...
├── stage2/            # Stage 2 cache files
│   └── ...
└── metadata/          # Cache metadata
```

### Database Schema

```sql
-- Cache metadata tracking
CREATE TABLE cache_metadata (
    cache_key TEXT PRIMARY KEY,
    stage INTEGER,
    term TEXT,
    file_path TEXT,
    size_bytes INTEGER,
    compression_type TEXT,
    compression_ratio REAL,
    created_at DATETIME,
    accessed_at DATETIME,
    access_count INTEGER,
    ttl_expires_at DATETIME,
    is_hot BOOLEAN,
    tokens_saved INTEGER,
    cost_saved REAL
);

-- Cache warming queue
CREATE TABLE cache_warming_queue (
    id INTEGER PRIMARY KEY,
    term TEXT,
    priority INTEGER,
    added_at DATETIME,
    processed BOOLEAN,
    processed_at DATETIME
);
```

## Usage

### Basic Setup

```python
from flashcard_pipeline.cache_v2 import ModernCacheService, CompressionType

# Initialize with LZ4 compression (recommended)
cache = ModernCacheService(
    cache_dir=".cache/flashcards_v2",
    db_path="pipeline.db",
    compression=CompressionType.LZ4,
    max_size_mb=1000,  # 1GB max cache size
    ttl_hours=168      # 1 week TTL
)
```

### Compression Options

- **LZ4** (Default) - Fast compression/decompression, good ratio
- **GZIP** - Better compression ratio, slower
- **ZLIB** - Similar to GZIP, different algorithm
- **NONE** - No compression (not recommended)

### Cache Operations

```python
# Stage 1 caching
cached = await cache.get_stage1(vocab_item)
if cached:
    response, tokens_saved = cached
else:
    # Process and save
    response, usage = await api_client.process_stage1(vocab_item)
    await cache.save_stage1(vocab_item, response, usage.total_tokens)

# Stage 2 caching
cached = await cache.get_stage2(vocab_item, stage1_response)
if cached:
    response, tokens_saved = cached
else:
    # Process and save
    response, usage = await api_client.process_stage2(vocab_item, stage1_response)
    await cache.save_stage2(vocab_item, stage1_response, response, usage.total_tokens)
```

## Cache Maintenance

### Command Line Tool

```bash
# Analyze cache performance
python scripts/cache_maintenance.py analyze

# Clean expired entries
python scripts/cache_maintenance.py clean

# Manage cache size (evict to 500MB)
python scripts/cache_maintenance.py size --target 500

# Show warming queue
python scripts/cache_maintenance.py queue --limit 20

# Generate detailed report
python scripts/cache_maintenance.py report --output cache_report.json

# Clear specific stage
python scripts/cache_maintenance.py clear --stage 1
```

### Performance Analysis

The analyze command provides:
- Cache hit rates by stage
- Token and cost savings
- Size and compression statistics
- Health score (0-100)
- Recommendations for optimization

Example output:
```
=== Cache Performance Analysis ===

Basic Statistics:
Total Entries     12,456
Total Size        245.3 MB
Stage 1 Entries   8,234
Stage 2 Entries   4,222
Hot Entries       1,823
Compression Type  lz4
Average Compression  42%

Cache Hit Rates:
Stage 1  78.3%
Stage 2  45.2%

Token Savings:
Tokens Saved      3,456,789
Cost Saved        $52.34

Overall Health Score: 85.2/100

Recommendations:
1. Stage 2 hit rate below 50%. Consider pre-warming frequently used terms.
2. Cache is at 25% capacity. No action needed.
```

## Cache Warming

### Manual Warming

```bash
# Warm from queue
python scripts/cache_warmup.py queue --limit 50

# Warm from vocabulary
python scripts/cache_warmup.py vocabulary --limit 100

# Warm from file
python scripts/cache_warmup.py file --path priority_terms.txt
```

### Automatic Warming Service

```bash
# Run continuous warming (every 30 minutes, 10 terms per batch)
python scripts/cache_warmup.py continuous --interval 30 --batch 10
```

### Adding Terms to Queue

```python
# Add high-priority terms
results = await cache.warm_cache(
    ["안녕하세요", "감사합니다", "사랑해요"],
    priority_boost=10
)

# Check queue
candidates = await cache.get_warming_candidates(limit=10)
for candidate in candidates:
    print(f"{candidate['term']}: priority {candidate['priority']}")
```

## Migration from Old Cache

### One-time Migration

```bash
# Migrate with progress display
python scripts/migrate_cache.py

# Dry run to see what would be migrated
python scripts/migrate_cache.py --dry-run

# Migrate with custom paths
python scripts/migrate_cache.py \
    --old-cache .cache/flashcards \
    --new-cache .cache/flashcards_v2 \
    --compression lz4
```

### Migration Process

1. Reads all entries from old cache
2. Converts to new format with compression
3. Saves metadata to database
4. Verifies sample entries
5. Reports statistics

The old cache is NOT deleted automatically.

## Invalidation Strategies

### Time-based (TTL)

```python
# Entries expire after configured TTL
cache = ModernCacheService(ttl_hours=168)  # 1 week

# Manually clean expired
count = await cache.invalidate_expired()
```

### Size-based

```python
# Evict least recently used when over size limit
count = await cache.invalidate_by_size(target_size_mb=500)
```

### Manual Invalidation

```python
# Clear all cache
await cache.clear_cache()

# Clear specific stage
await cache.clear_cache(stage=1)
```

## Hot Entry Optimization

Entries accessed more than 5 times are marked as "hot" and:
- Protected from size-based eviction
- Kept in memory cache for fast access
- Prioritized in warming operations

## Performance Tips

### 1. Compression Choice
- **LZ4**: Best for most use cases (fast + good ratio)
- **GZIP**: When storage is critical
- **NONE**: Only for debugging

### 2. Memory Cache
- First 100 entries kept in memory
- Automatic for hot entries
- Reduces disk I/O significantly

### 3. Cache Warming
- Run warming during off-peak hours
- Prioritize frequently used terms
- Monitor API rate limits

### 4. Maintenance Schedule
```cron
# Clean expired entries daily at 3 AM
0 3 * * * cd /app && python scripts/cache_maintenance.py clean

# Warm cache every 6 hours
0 */6 * * * cd /app && python scripts/cache_warmup.py queue --limit 20

# Generate weekly report
0 0 * * 0 cd /app && python scripts/cache_maintenance.py report
```

## Monitoring

### Health Metrics

Monitor these key metrics:
- **Hit Rate**: Target >70% for Stage 1, >40% for Stage 2
- **Size Usage**: Keep below 80% of max size
- **Hot Entry Ratio**: Higher is better (>10%)
- **Compression Ratio**: Should be <50% with LZ4

### Database Queries

```sql
-- Cache performance last 24 hours
SELECT 
    stage,
    COUNT(*) as entries,
    AVG(access_count) as avg_accesses,
    SUM(tokens_saved) as total_tokens_saved
FROM cache_metadata
WHERE accessed_at > datetime('now', '-1 day')
GROUP BY stage;

-- Top accessed terms
SELECT term, access_count, is_hot, tokens_saved
FROM cache_metadata
ORDER BY access_count DESC
LIMIT 20;

-- Warming queue status
SELECT COUNT(*) as queued, 
       SUM(CASE WHEN processed = 1 THEN 1 ELSE 0 END) as processed
FROM cache_warming_queue
WHERE added_at > datetime('now', '-1 day');
```

## Troubleshooting

### Common Issues

1. **Low Hit Rate**
   - Add frequently used terms to warming queue
   - Increase TTL if appropriate
   - Check if terms are being normalized consistently

2. **High Memory Usage**
   - Reduce memory cache size
   - Clear old entries more frequently
   - Check for memory leaks in long-running processes

3. **Slow Performance**
   - Enable compression if not already
   - Add database indexes if missing
   - Move cache to SSD storage

4. **Corruption Errors**
   - Run integrity check: `python scripts/cache_maintenance.py analyze`
   - Clear corrupted entries: `python scripts/cache_maintenance.py clean`
   - Verify disk has sufficient space

### Debug Mode

```python
import logging

# Enable debug logging
logging.getLogger('flashcard_pipeline.cache_v2').setLevel(logging.DEBUG)

# Track detailed operations
cache = ModernCacheService(
    cache_dir=".cache/flashcards_v2",
    db_path="pipeline.db",
    enable_stats=True  # Enable detailed statistics
)
```

## API Reference

### ModernCacheService

```python
class ModernCacheService:
    async def get_stage1(vocab_item: VocabularyItem) -> Optional[Tuple[Stage1Response, int]]
    async def save_stage1(vocab_item: VocabularyItem, response: Stage1Response, tokens: int)
    async def get_stage2(vocab_item: VocabularyItem, stage1: Stage1Response) -> Optional[Tuple[Stage2Response, int]]
    async def save_stage2(vocab_item: VocabularyItem, stage1: Stage1Response, response: Stage2Response, tokens: int)
    async def invalidate_expired() -> int
    async def invalidate_by_size(target_mb: int) -> int
    async def warm_cache(terms: List[str], priority: int) -> Dict
    async def get_warming_candidates(limit: int) -> List[Dict]
    def get_stats() -> Dict[str, Any]
    async def analyze_cache_performance() -> Dict[str, Any]
    async def clear_cache(stage: Optional[int] = None) -> int
```

## Future Enhancements

Planned improvements:
- Redis backend option for distributed caching
- Machine learning for predictive warming
- Real-time cache analytics dashboard
- Automatic compression algorithm selection
- Multi-level caching (memory → disk → cloud)