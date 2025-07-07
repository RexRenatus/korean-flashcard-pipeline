# Concurrent Processing Implementation Plan

**Created**: 2025-01-07  
**Purpose**: Step-by-step plan to implement concurrent processing for 50 vocabulary items

## Phase 1: Foundation Components (Week 1)

### 1.1 Create Ordered Results Collector
```python
# src/python/flashcard_pipeline/concurrent/ordered_collector.py
class OrderedResultsCollector:
    """Maintains order of results despite concurrent processing"""
    
    def __init__(self):
        self.results: Dict[int, ProcessingResult] = {}
        self.lock = asyncio.Lock()
        self.completion_event = asyncio.Event()
        self.expected_count = 0
    
    async def add_result(self, position: int, result: ProcessingResult):
        async with self.lock:
            self.results[position] = result
            if len(self.results) == self.expected_count:
                self.completion_event.set()
    
    async def wait_for_all(self, timeout: float = 300.0):
        await asyncio.wait_for(self.completion_event.wait(), timeout)
    
    def get_ordered_results(self) -> List[ProcessingResult]:
        return [self.results[i] for i in sorted(self.results.keys())]
```

### 1.2 Implement Thread-Safe Rate Limiter
```python
# src/python/flashcard_pipeline/concurrent/distributed_rate_limiter.py
class DistributedRateLimiter:
    """Thread-safe rate limiter for concurrent requests"""
    
    def __init__(self, requests_per_minute: int = 600):
        # Use 80% of limit for safety
        safe_limit = int(requests_per_minute * 0.8)
        self.semaphore = asyncio.Semaphore(safe_limit)
        self.tokens = asyncio.Queue(maxsize=safe_limit)
        self.refill_rate = safe_limit / 60.0  # tokens per second
        self._start_refill_task()
    
    async def acquire(self, timeout: float = 30.0):
        """Acquire a token, blocking if necessary"""
        try:
            async with asyncio.timeout(timeout):
                await self.semaphore.acquire()
                token = await self.tokens.get()
                return token
        except asyncio.TimeoutError:
            raise RateLimitError("Rate limit token acquisition timeout")
    
    def _start_refill_task(self):
        """Start background task to refill tokens"""
        asyncio.create_task(self._refill_tokens())
    
    async def _refill_tokens(self):
        """Continuously refill tokens at the specified rate"""
        while True:
            await asyncio.sleep(1.0 / self.refill_rate)
            try:
                await self.tokens.put(1)
                self.semaphore.release()
            except asyncio.QueueFull:
                pass  # Queue is full, skip this refill
```

### 1.3 Create Concurrent Progress Tracker
```python
# src/python/flashcard_pipeline/concurrent/progress_tracker.py
class ConcurrentProgressTracker:
    def __init__(self, total_items: int):
        self.total = total_items
        self.completed = 0
        self.failed = 0
        self.in_progress = set()
        self.lock = asyncio.Lock()
        self.progress_callbacks = []
    
    async def start_item(self, item_id: int):
        async with self.lock:
            self.in_progress.add(item_id)
            await self._notify_progress()
    
    async def complete_item(self, item_id: int, success: bool = True):
        async with self.lock:
            self.in_progress.discard(item_id)
            if success:
                self.completed += 1
            else:
                self.failed += 1
            await self._notify_progress()
    
    async def _notify_progress(self):
        for callback in self.progress_callbacks:
            await callback(self.get_stats())
    
    def get_stats(self):
        return {
            "total": self.total,
            "completed": self.completed,
            "failed": self.failed,
            "in_progress": len(self.in_progress),
            "progress_percent": (self.completed / self.total * 100) if self.total > 0 else 0
        }
```

## Phase 2: Core Concurrent Processor (Week 1-2)

### 2.1 Implement Concurrent Pipeline Orchestrator
```python
# src/python/flashcard_pipeline/concurrent/orchestrator.py
class ConcurrentPipelineOrchestrator:
    def __init__(self, 
                 max_concurrent: int = 50,
                 api_client: OpenRouterClient = None,
                 cache_service: CacheService = None):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.rate_limiter = DistributedRateLimiter()
        self.circuit_breaker = CircuitBreaker()
        self.results_collector = OrderedResultsCollector()
        self.progress_tracker = ConcurrentProgressTracker(0)
        self.api_client = api_client
        self.cache_service = cache_service
    
    async def process_batch(self, items: List[VocabularyItem]) -> List[ProcessingResult]:
        """Process items concurrently while maintaining order"""
        self.results_collector.expected_count = len(items)
        self.progress_tracker = ConcurrentProgressTracker(len(items))
        
        # Create processing tasks
        tasks = []
        for item in items:
            task = self._create_processing_task(item)
            tasks.append(task)
        
        # Execute concurrently with error handling
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions and collect results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to process item {items[i].position}: {result}")
                await self.results_collector.add_result(
                    items[i].position, 
                    ProcessingResult(error=str(result))
                )
        
        # Wait for all results
        await self.results_collector.wait_for_all()
        
        return self.results_collector.get_ordered_results()
    
    async def _create_processing_task(self, item: VocabularyItem):
        """Create a processing task with proper error handling"""
        async with self.semaphore:
            return await self._process_single_item(item)
    
    async def _process_single_item(self, item: VocabularyItem):
        """Process a single item with all safety checks"""
        await self.progress_tracker.start_item(item.position)
        
        try:
            # Rate limiting
            await self.rate_limiter.acquire()
            
            # Check cache first
            cached_result = await self._check_cache(item)
            if cached_result:
                await self.results_collector.add_result(item.position, cached_result)
                await self.progress_tracker.complete_item(item.position, True)
                return cached_result
            
            # Process through circuit breaker
            result = await self.circuit_breaker.call(
                f"process_item_{item.position}",
                lambda: self._api_process_item(item)
            )
            
            # Cache the result
            await self._cache_result(item, result)
            
            # Add to collector
            await self.results_collector.add_result(item.position, result)
            await self.progress_tracker.complete_item(item.position, True)
            
            return result
            
        except Exception as e:
            await self.progress_tracker.complete_item(item.position, False)
            raise
```

### 2.2 Update CLI Integration
```python
# Modify src/python/flashcard_pipeline/cli.py
async def process_batch_concurrent(self, items: List[VocabularyItem], 
                                 output_file: Path,
                                 batch_id: Optional[str] = None,
                                 max_concurrent: int = 50) -> BatchProgress:
    """Process a batch of vocabulary items concurrently"""
    
    # Initialize concurrent orchestrator
    orchestrator = ConcurrentPipelineOrchestrator(
        max_concurrent=max_concurrent,
        api_client=self.client,
        cache_service=self.cache_service
    )
    
    # Set up progress display
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task(
            f"Processing {len(items)} items (up to {max_concurrent} concurrent)...", 
            total=len(items)
        )
        
        # Register progress callback
        async def update_progress(stats):
            progress.update(task, completed=stats["completed"])
            progress.console.print(
                f"[green]✓ {stats['completed']}[/green] | "
                f"[red]✗ {stats['failed']}[/red] | "
                f"[yellow]⟳ {stats['in_progress']}[/yellow]",
                end="\r"
            )
        
        orchestrator.progress_tracker.progress_callbacks.append(update_progress)
        
        # Process concurrently
        results = await orchestrator.process_batch(items)
        
    # Write ordered results
    await self._write_ordered_results(results, output_file)
    
    return self._create_batch_progress(results)
```

## Phase 3: Database Integration (Week 2)

### 3.1 Update Database Schema
```sql
-- migrations/002_concurrent_processing.sql
-- Add indexes for efficient ordered operations
CREATE INDEX IF NOT EXISTS idx_vocabulary_position 
    ON vocabulary_items(position);

CREATE INDEX IF NOT EXISTS idx_stage1_cache_position 
    ON stage1_cache(vocabulary_id, position);

CREATE INDEX IF NOT EXISTS idx_stage2_cache_position 
    ON stage2_cache(vocabulary_id, position);

-- Add concurrent processing metadata
ALTER TABLE processing_batches ADD COLUMN max_concurrent INTEGER DEFAULT 1;
ALTER TABLE processing_batches ADD COLUMN actual_concurrent INTEGER;
ALTER TABLE processing_batches ADD COLUMN processing_order TEXT;

-- Add performance tracking
CREATE TABLE concurrent_processing_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    concurrent_count INTEGER,
    total_duration_ms INTEGER,
    average_item_duration_ms REAL,
    rate_limit_hits INTEGER,
    circuit_breaker_trips INTEGER,
    cache_hit_rate REAL
);
```

### 3.2 Implement Batch Database Writer
```python
# src/python/flashcard_pipeline/concurrent/batch_writer.py
class OrderedBatchDatabaseWriter:
    """Write results to database while preserving order"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def write_batch(self, results: List[ProcessingResult], batch_id: str):
        """Write batch results in order"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("BEGIN TRANSACTION")
            
            try:
                for result in results:
                    await self._write_single_result(db, result, batch_id)
                
                await db.commit()
                logger.info(f"Successfully wrote {len(results)} ordered results")
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to write batch: {e}")
                raise
    
    async def _write_single_result(self, db, result: ProcessingResult, batch_id: str):
        """Write a single result maintaining position order"""
        await db.execute("""
            INSERT INTO flashcards (
                batch_id, position, term, flashcard_data, 
                processing_timestamp, processing_order
            ) VALUES (?, ?, ?, ?, datetime('now'), ?)
        """, (
            batch_id,
            result.position,
            result.term,
            json.dumps(result.flashcard_data),
            result.position  # Ensure order is preserved
        ))
```

## Phase 4: Testing Strategy (Week 2-3)

### 4.1 Unit Tests
```python
# tests/python/test_concurrent_processing.py
class TestConcurrentProcessing:
    @pytest.mark.asyncio
    async def test_order_preservation(self):
        """Test that items maintain order despite concurrent processing"""
        items = [VocabularyItem(position=i, term=f"word{i}") for i in range(50)]
        orchestrator = ConcurrentPipelineOrchestrator(max_concurrent=10)
        
        results = await orchestrator.process_batch(items)
        
        # Verify order
        positions = [r.position for r in results]
        assert positions == list(range(50))
    
    @pytest.mark.asyncio
    async def test_concurrent_rate_limiting(self):
        """Test rate limiting with concurrent requests"""
        limiter = DistributedRateLimiter(requests_per_minute=60)
        
        # Try to acquire 100 tokens concurrently
        tasks = [limiter.acquire() for _ in range(100)]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time
        
        # Should take at least 40 seconds (40 tokens over limit)
        assert duration >= 40.0
```

### 4.2 Integration Tests
```python
@pytest.mark.asyncio
async def test_end_to_end_concurrent_processing():
    """Test full pipeline with concurrent processing"""
    # Create test data
    test_items = [
        VocabularyItem(position=i, term=f"test{i}", type="noun")
        for i in range(50)
    ]
    
    # Process concurrently
    orchestrator = ConcurrentPipelineOrchestrator(max_concurrent=50)
    results = await orchestrator.process_batch(test_items)
    
    # Verify all processed
    assert len(results) == 50
    
    # Verify order maintained
    for i, result in enumerate(results):
        assert result.position == i
        assert result.term == f"test{i}"
```

## Phase 5: Deployment and Monitoring (Week 3)

### 5.1 Configuration Management
```python
# src/python/flashcard_pipeline/config.py
@dataclass
class ConcurrentProcessingConfig:
    max_concurrent: int = 50
    rate_limit_buffer: float = 0.8
    semaphore_timeout: float = 30.0
    circuit_breaker_threshold: int = 10
    circuit_breaker_timeout: int = 60
    retry_max_attempts: int = 3
    retry_base_delay: float = 1.0
    batch_timeout: float = 300.0
    
    @classmethod
    def from_env(cls):
        return cls(
            max_concurrent=int(os.getenv("CONCURRENT_MAX", "50")),
            rate_limit_buffer=float(os.getenv("RATE_LIMIT_BUFFER", "0.8"))
        )
```

### 5.2 Monitoring Implementation
```python
# src/python/flashcard_pipeline/concurrent/monitoring.py
class ConcurrentProcessingMonitor:
    """Monitor concurrent processing performance"""
    
    def __init__(self):
        self.metrics = defaultdict(int)
        self.timings = defaultdict(list)
    
    async def record_batch_processing(self, batch_id: str, stats: dict):
        """Record batch processing metrics"""
        await self._save_to_database({
            "batch_id": batch_id,
            "timestamp": datetime.utcnow(),
            "concurrent_count": stats["max_concurrent"],
            "total_duration_ms": stats["duration_ms"],
            "average_item_duration_ms": stats["avg_item_ms"],
            "rate_limit_hits": stats["rate_limit_hits"],
            "circuit_breaker_trips": stats["circuit_breaker_trips"],
            "cache_hit_rate": stats["cache_hit_rate"]
        })
```

## Rollout Plan

### Week 1: Foundation
- [ ] Implement OrderedResultsCollector
- [ ] Implement DistributedRateLimiter
- [ ] Create unit tests for components

### Week 2: Integration
- [ ] Implement ConcurrentPipelineOrchestrator
- [ ] Update CLI to support concurrent processing
- [ ] Add database schema updates

### Week 3: Testing & Deployment
- [ ] Complete integration testing
- [ ] Add monitoring and metrics
- [ ] Deploy with gradual rollout:
  - Day 1-2: 5 concurrent
  - Day 3-4: 10 concurrent
  - Day 5-6: 25 concurrent
  - Day 7: 50 concurrent

### Performance Targets
- 50x throughput improvement for large batches
- < 1% order violation rate
- < 5% additional error rate vs sequential
- 80% cache hit rate maintained

## Risk Mitigation

1. **Gradual Rollout**: Start with low concurrency and increase
2. **Feature Flag**: Easy enable/disable of concurrent processing
3. **Fallback**: Automatic fallback to sequential on errors
4. **Monitoring**: Real-time metrics and alerting
5. **Testing**: Comprehensive test coverage before production