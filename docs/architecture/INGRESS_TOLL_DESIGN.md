# Ingress Toll System Design

**Last Updated**: 2025-07-08

## 1. System Overview and Purpose

The Ingress Toll System is a pre-processing validation and queue management layer that sits in front of the Korean Flashcard Pipeline. It acts as a gatekeeper, ensuring that only valid vocabulary items enter the expensive AI processing pipeline while providing robust bulk upload capabilities, validation, and queue management.

### Key Objectives

1. **Cost Optimization**: Prevent invalid items from consuming API credits
2. **Data Quality**: Ensure all inputs meet quality standards before processing
3. **Bulk Operations**: Support efficient upload of thousands of items
4. **Queue Management**: Manage processing workload and prioritization
5. **Error Recovery**: Provide clear feedback and recovery mechanisms
6. **Performance**: Handle large datasets without blocking the main pipeline

### System Position

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│   CSV Upload    │ --> │  Ingress Toll    │ --> │  Flashcard Pipeline │
│   (Bulk Data)   │     │     System       │     │   (AI Processing)   │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
                              │
                              ▼
                        ┌──────────────┐
                        │ Validation   │
                        │   Reports    │
                        └──────────────┘
```

## 2. Architecture for Bulk Upload Processing

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Ingress Toll System                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────────────┐  │
│  │   Upload     │    │  Validation  │    │   Queue Manager    │  │
│  │   Handler    │--->│   Pipeline   │--->│                    │  │
│  └──────────────┘    └──────────────┘    └────────────────────┘  │
│         │                    │                      │              │
│         ▼                    ▼                      ▼              │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────────────┐  │
│  │    Chunk     │    │   Rules      │    │   Priority Queue   │  │
│  │   Processor  │    │   Engine     │    │                    │  │
│  └──────────────┘    └──────────────┘    └────────────────────┘  │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                         Data Layer                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────────────┐  │
│  │   Pending    │    │  Validation  │    │   Processing       │  │
│  │   Items DB   │    │  Results DB  │    │   History DB       │  │
│  └──────────────┘    └──────────────┘    └────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Details

#### Upload Handler
```python
class BulkUploadHandler:
    """Handles large file uploads with streaming and chunking"""
    
    def __init__(self):
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        self.chunk_size = 1000  # Items per chunk
        self.supported_formats = ['.csv', '.tsv', '.xlsx']
    
    async def process_upload(
        self, 
        file_stream: AsyncIterator[bytes],
        filename: str,
        user_id: str
    ) -> UploadResult:
        # Stream processing to handle large files
        upload_id = generate_upload_id()
        
        async for chunk in self.stream_chunks(file_stream):
            await self.queue_chunk_for_validation(
                upload_id, chunk, user_id
            )
        
        return UploadResult(
            upload_id=upload_id,
            status="queued",
            total_items=total_count
        )
```

#### Chunk Processor
```python
class ChunkProcessor:
    """Processes file chunks in parallel"""
    
    async def process_chunk(
        self,
        chunk_data: List[Dict],
        chunk_id: str,
        upload_id: str
    ):
        # Parse and normalize data
        items = []
        for row in chunk_data:
            try:
                item = self.parse_vocabulary_item(row)
                items.append(item)
            except ValidationError as e:
                await self.log_parse_error(row, e, chunk_id)
        
        # Queue for validation
        await self.validation_queue.add_batch(items, upload_id)
```

## 3. Validation Pipeline Design

### Multi-Stage Validation

```
Input → Format Check → Content Check → Duplicate Check → Business Rules → Queue
         │               │                │                  │
         └───────────────┴────────────────┴──────────────────┴──> Error Log
```

### Validation Components

#### 1. Format Validator
```python
class FormatValidator:
    """Validates data format and structure"""
    
    REQUIRED_FIELDS = ['position', 'term']
    OPTIONAL_FIELDS = ['type', 'notes', 'priority']
    
    def validate(self, item: Dict) -> ValidationResult:
        errors = []
        
        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in item or not item[field]:
                errors.append(f"Missing required field: {field}")
        
        # Validate position is numeric
        if 'position' in item:
            try:
                pos = int(item['position'])
                if pos <= 0:
                    errors.append("Position must be positive")
            except ValueError:
                errors.append("Position must be a number")
        
        # Validate Korean text
        if 'term' in item:
            if not self.is_valid_korean(item['term']):
                errors.append("Term must contain Korean characters")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )
```

#### 2. Content Validator
```python
class ContentValidator:
    """Validates content quality and consistency"""
    
    def __init__(self):
        self.profanity_filter = ProfanityFilter()
        self.script_detector = ScriptDetector()
    
    async def validate(self, item: VocabularyItem) -> ValidationResult:
        errors = []
        warnings = []
        
        # Check for inappropriate content
        if await self.profanity_filter.contains_profanity(item.term):
            warnings.append("Term may contain inappropriate content")
        
        # Detect script (Hangul, Hanja, Mixed)
        script_type = self.script_detector.detect(item.term)
        if script_type == ScriptType.INVALID:
            errors.append("Term contains invalid characters")
        
        # Check term length
        if len(item.term) > 50:
            warnings.append("Term is unusually long")
        elif len(item.term) < 1:
            errors.append("Term cannot be empty")
        
        # Validate type if provided
        if item.type and item.type not in VALID_TYPES:
            warnings.append(f"Unknown type: {item.type}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
```

#### 3. Duplicate Detector
```python
class DuplicateDetector:
    """Detects and handles duplicate entries"""
    
    def __init__(self, db: Database):
        self.db = db
        self.bloom_filter = BloomFilter(expected_items=1000000)
    
    async def check_duplicates(
        self, 
        items: List[VocabularyItem],
        upload_id: str
    ) -> DuplicateReport:
        duplicates = []
        
        # Check within current batch
        seen = set()
        for item in items:
            key = f"{item.term}:{item.type}"
            if key in seen:
                duplicates.append(DuplicateItem(
                    item=item,
                    duplicate_type="batch",
                    first_position=seen[key]
                ))
            seen[key] = item.position
        
        # Check against existing data
        for item in items:
            if await self.exists_in_database(item):
                duplicates.append(DuplicateItem(
                    item=item,
                    duplicate_type="database"
                ))
        
        return DuplicateReport(
            upload_id=upload_id,
            total_duplicates=len(duplicates),
            duplicates=duplicates
        )
```

#### 4. Business Rules Engine
```python
class BusinessRulesEngine:
    """Applies configurable business rules"""
    
    def __init__(self):
        self.rules = self.load_rules()
    
    async def validate(self, item: VocabularyItem) -> RuleValidationResult:
        violations = []
        
        for rule in self.rules:
            if not await rule.evaluate(item):
                violations.append(RuleViolation(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    message=rule.get_violation_message(item)
                ))
        
        return RuleValidationResult(
            passed=len(violations) == 0,
            violations=violations
        )

# Example Rules
class MinimumTermLengthRule(Rule):
    def __init__(self):
        self.min_length = 1
    
    async def evaluate(self, item: VocabularyItem) -> bool:
        return len(item.term) >= self.min_length

class ValidTypeRule(Rule):
    def __init__(self):
        self.valid_types = {'noun', 'verb', 'adjective', 'adverb', 
                           'phrase', 'interjection', 'particle'}
    
    async def evaluate(self, item: VocabularyItem) -> bool:
        return item.type.lower() in self.valid_types
```

## 4. Queue Management System

### Priority Queue Implementation

```python
class PriorityQueueManager:
    """Manages processing queue with priority levels"""
    
    def __init__(self, db: Database):
        self.db = db
        self.queues = {
            Priority.URGENT: asyncio.Queue(maxsize=1000),
            Priority.HIGH: asyncio.Queue(maxsize=5000),
            Priority.NORMAL: asyncio.Queue(maxsize=10000),
            Priority.LOW: asyncio.Queue(maxsize=20000)
        }
    
    async def enqueue(
        self, 
        item: QueueItem,
        priority: Priority = Priority.NORMAL
    ):
        # Add to in-memory queue
        await self.queues[priority].put(item)
        
        # Persist to database
        await self.db.insert_queue_item(
            item_id=item.id,
            vocabulary_item=item.vocabulary_item,
            priority=priority,
            upload_id=item.upload_id,
            status=QueueStatus.PENDING
        )
    
    async def dequeue(self) -> Optional[QueueItem]:
        """Get next item respecting priorities"""
        for priority in [Priority.URGENT, Priority.HIGH, 
                        Priority.NORMAL, Priority.LOW]:
            queue = self.queues[priority]
            if not queue.empty():
                item = await queue.get()
                await self.db.update_queue_status(
                    item.id, QueueStatus.PROCESSING
                )
                return item
        return None
```

### Queue Monitoring

```python
class QueueMonitor:
    """Monitors queue health and performance"""
    
    async def get_queue_stats(self) -> QueueStats:
        stats = QueueStats()
        
        # Get queue depths
        for priority, queue in self.queue_manager.queues.items():
            stats.depths[priority] = queue.qsize()
        
        # Calculate processing rates
        stats.items_per_minute = await self.calculate_throughput()
        
        # Estimate completion times
        stats.estimated_completion = self.estimate_completion_time()
        
        # Check for stalled items
        stats.stalled_items = await self.find_stalled_items()
        
        return stats
```

## 5. Database Schema for Pending Items

### Core Tables

```sql
-- Uploads table
CREATE TABLE uploads (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    total_items INTEGER,
    processed_items INTEGER DEFAULT 0,
    valid_items INTEGER DEFAULT 0,
    invalid_items INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'uploading',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_uploads_user ON uploads(user_id);
CREATE INDEX idx_uploads_status ON uploads(status);
CREATE INDEX idx_uploads_created ON uploads(created_at);

-- Pending items queue
CREATE TABLE pending_items (
    id TEXT PRIMARY KEY,
    upload_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    term TEXT NOT NULL,
    type TEXT,
    priority INTEGER DEFAULT 2, -- 0=urgent, 1=high, 2=normal, 3=low
    status TEXT NOT NULL DEFAULT 'pending',
    validation_status TEXT,
    validation_errors TEXT, -- JSON array
    enqueued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_started_at TIMESTAMP,
    processing_completed_at TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    FOREIGN KEY (upload_id) REFERENCES uploads(id)
);

CREATE INDEX idx_pending_priority ON pending_items(priority, status);
CREATE INDEX idx_pending_upload ON pending_items(upload_id);
CREATE INDEX idx_pending_status ON pending_items(status);
CREATE INDEX idx_pending_term ON pending_items(term);

-- Validation results
CREATE TABLE validation_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL,
    upload_id TEXT NOT NULL,
    validation_type TEXT NOT NULL, -- 'format', 'content', 'duplicate', 'rules'
    is_valid BOOLEAN NOT NULL,
    errors TEXT, -- JSON array
    warnings TEXT, -- JSON array
    metadata TEXT, -- JSON object
    validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES pending_items(id),
    FOREIGN KEY (upload_id) REFERENCES uploads(id)
);

CREATE INDEX idx_validation_item ON validation_results(item_id);
CREATE INDEX idx_validation_upload ON validation_results(upload_id);
CREATE INDEX idx_validation_type ON validation_results(validation_type);

-- Processing history
CREATE TABLE processing_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL,
    upload_id TEXT NOT NULL,
    action TEXT NOT NULL, -- 'enqueued', 'processing', 'completed', 'failed'
    details TEXT, -- JSON object
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES pending_items(id),
    FOREIGN KEY (upload_id) REFERENCES uploads(id)
);

CREATE INDEX idx_history_item ON processing_history(item_id);
CREATE INDEX idx_history_action ON processing_history(action);
CREATE INDEX idx_history_timestamp ON processing_history(timestamp);

-- Duplicate tracking
CREATE TABLE duplicate_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_term TEXT NOT NULL,
    original_type TEXT,
    duplicate_item_id TEXT NOT NULL,
    duplicate_upload_id TEXT NOT NULL,
    duplicate_type TEXT NOT NULL, -- 'exact', 'similar', 'batch'
    similarity_score REAL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (duplicate_item_id) REFERENCES pending_items(id)
);

CREATE INDEX idx_duplicates_term ON duplicate_items(original_term);
CREATE INDEX idx_duplicates_upload ON duplicate_items(duplicate_upload_id);
```

### Views for Monitoring

```sql
-- Queue depth by priority
CREATE VIEW queue_depth AS
SELECT 
    priority,
    COUNT(*) as item_count,
    MIN(enqueued_at) as oldest_item,
    AVG(JULIANDAY('now') - JULIANDAY(enqueued_at)) * 24 * 60 as avg_wait_minutes
FROM pending_items
WHERE status = 'pending'
GROUP BY priority;

-- Upload progress
CREATE VIEW upload_progress AS
SELECT 
    u.id,
    u.filename,
    u.total_items,
    u.processed_items,
    u.valid_items,
    u.invalid_items,
    CASE 
        WHEN u.total_items > 0 
        THEN u.processed_items * 100.0 / u.total_items 
        ELSE 0 
    END as progress_percent,
    u.status,
    u.created_at
FROM uploads u
ORDER BY u.created_at DESC;

-- Validation summary
CREATE VIEW validation_summary AS
SELECT 
    upload_id,
    validation_type,
    COUNT(*) as total_validations,
    SUM(CASE WHEN is_valid THEN 1 ELSE 0 END) as passed,
    SUM(CASE WHEN NOT is_valid THEN 1 ELSE 0 END) as failed,
    AVG(CASE WHEN is_valid THEN 100.0 ELSE 0 END) as pass_rate
FROM validation_results
GROUP BY upload_id, validation_type;
```

## 6. API Endpoints for Bulk Operations

### RESTful API Design

#### Upload Endpoints

```python
# POST /api/v1/ingress/upload
@app.post("/api/v1/ingress/upload")
async def upload_vocabulary(
    file: UploadFile,
    priority: Priority = Priority.NORMAL,
    user: User = Depends(get_current_user)
) -> UploadResponse:
    """
    Upload vocabulary file for processing
    
    Accepts: CSV, TSV, XLSX
    Max size: 100MB
    Returns: Upload ID and initial validation status
    """
    # Validate file
    if not file.filename.endswith(('.csv', '.tsv', '.xlsx')):
        raise HTTPException(400, "Unsupported file format")
    
    # Create upload record
    upload_id = await create_upload_record(
        user_id=user.id,
        filename=file.filename,
        file_size=file.size
    )
    
    # Process asynchronously
    background_tasks.add_task(
        process_upload,
        upload_id=upload_id,
        file=file,
        priority=priority
    )
    
    return UploadResponse(
        upload_id=upload_id,
        status="processing",
        message="File uploaded successfully"
    )

# GET /api/v1/ingress/upload/{upload_id}
@app.get("/api/v1/ingress/upload/{upload_id}")
async def get_upload_status(
    upload_id: str,
    user: User = Depends(get_current_user)
) -> UploadStatusResponse:
    """Get detailed upload status and validation results"""
    
    upload = await get_upload(upload_id, user.id)
    if not upload:
        raise HTTPException(404, "Upload not found")
    
    return UploadStatusResponse(
        upload_id=upload_id,
        status=upload.status,
        total_items=upload.total_items,
        processed_items=upload.processed_items,
        valid_items=upload.valid_items,
        invalid_items=upload.invalid_items,
        progress_percent=upload.progress_percent,
        validation_summary=await get_validation_summary(upload_id),
        errors=await get_validation_errors(upload_id, limit=10)
    )

# GET /api/v1/ingress/upload/{upload_id}/errors
@app.get("/api/v1/ingress/upload/{upload_id}/errors")
async def get_upload_errors(
    upload_id: str,
    page: int = 1,
    per_page: int = 50,
    user: User = Depends(get_current_user)
) -> ValidationErrorsResponse:
    """Get paginated validation errors"""
    
    errors = await get_validation_errors(
        upload_id=upload_id,
        user_id=user.id,
        offset=(page - 1) * per_page,
        limit=per_page
    )
    
    return ValidationErrorsResponse(
        upload_id=upload_id,
        errors=errors,
        total_errors=await count_validation_errors(upload_id),
        page=page,
        per_page=per_page
    )

# POST /api/v1/ingress/upload/{upload_id}/retry
@app.post("/api/v1/ingress/upload/{upload_id}/retry")
async def retry_failed_items(
    upload_id: str,
    retry_options: RetryOptions,
    user: User = Depends(get_current_user)
) -> RetryResponse:
    """Retry failed validation items"""
    
    # Get failed items
    failed_items = await get_failed_items(
        upload_id=upload_id,
        user_id=user.id,
        types=retry_options.error_types
    )
    
    # Re-queue for validation
    retry_count = 0
    for item in failed_items:
        if item.retry_count < retry_options.max_retries:
            await queue_for_revalidation(item)
            retry_count += 1
    
    return RetryResponse(
        upload_id=upload_id,
        items_retried=retry_count,
        message=f"Queued {retry_count} items for retry"
    )
```

#### Queue Management Endpoints

```python
# GET /api/v1/ingress/queue/stats
@app.get("/api/v1/ingress/queue/stats")
async def get_queue_statistics(
    user: User = Depends(get_current_user)
) -> QueueStatsResponse:
    """Get current queue statistics"""
    
    stats = await queue_monitor.get_stats()
    
    return QueueStatsResponse(
        queue_depths={
            "urgent": stats.depths[Priority.URGENT],
            "high": stats.depths[Priority.HIGH],
            "normal": stats.depths[Priority.NORMAL],
            "low": stats.depths[Priority.LOW]
        },
        processing_rate=stats.items_per_minute,
        estimated_completion=stats.estimated_completion,
        stalled_items=stats.stalled_items,
        total_pending=sum(stats.depths.values())
    )

# POST /api/v1/ingress/queue/priority
@app.post("/api/v1/ingress/queue/priority")
async def update_item_priority(
    request: UpdatePriorityRequest,
    user: User = Depends(get_current_user)
) -> UpdatePriorityResponse:
    """Update priority for pending items"""
    
    updated_count = 0
    for item_id in request.item_ids:
        if await user_owns_item(user.id, item_id):
            await update_item_priority(item_id, request.new_priority)
            updated_count += 1
    
    return UpdatePriorityResponse(
        items_updated=updated_count,
        new_priority=request.new_priority
    )

# DELETE /api/v1/ingress/queue/{item_id}
@app.delete("/api/v1/ingress/queue/{item_id}")
async def cancel_pending_item(
    item_id: str,
    user: User = Depends(get_current_user)
) -> CancelResponse:
    """Cancel a pending item"""
    
    if not await user_owns_item(user.id, item_id):
        raise HTTPException(403, "Access denied")
    
    await cancel_item(item_id)
    
    return CancelResponse(
        item_id=item_id,
        status="cancelled"
    )
```

#### Validation Endpoints

```python
# POST /api/v1/ingress/validate
@app.post("/api/v1/ingress/validate")
async def validate_single_item(
    item: VocabularyItem,
    user: User = Depends(get_current_user)
) -> ValidationResponse:
    """Validate a single vocabulary item"""
    
    results = {}
    
    # Run all validators
    results['format'] = format_validator.validate(item.dict())
    results['content'] = await content_validator.validate(item)
    results['duplicates'] = await duplicate_detector.check_single(item)
    results['rules'] = await rules_engine.validate(item)
    
    is_valid = all(r.is_valid for r in results.values())
    
    return ValidationResponse(
        is_valid=is_valid,
        results=results,
        recommendations=generate_recommendations(results)
    )

# GET /api/v1/ingress/rules
@app.get("/api/v1/ingress/rules")
async def get_validation_rules() -> RulesResponse:
    """Get current validation rules"""
    
    return RulesResponse(
        rules=[
            {
                "id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "severity": rule.severity,
                "enabled": rule.enabled
            }
            for rule in rules_engine.get_rules()
        ]
    )
```

## 7. Error Handling and Recovery

### Error Classification

```python
class ErrorClassifier:
    """Classifies errors for appropriate handling"""
    
    ERROR_CATEGORIES = {
        'FORMAT_ERROR': {
            'recoverable': True,
            'user_actionable': True,
            'retry_strategy': 'immediate'
        },
        'CONTENT_ERROR': {
            'recoverable': True,
            'user_actionable': True,
            'retry_strategy': 'after_fix'
        },
        'DUPLICATE_ERROR': {
            'recoverable': True,
            'user_actionable': True,
            'retry_strategy': 'skip_or_merge'
        },
        'SYSTEM_ERROR': {
            'recoverable': True,
            'user_actionable': False,
            'retry_strategy': 'exponential_backoff'
        },
        'FATAL_ERROR': {
            'recoverable': False,
            'user_actionable': False,
            'retry_strategy': 'none'
        }
    }
    
    def classify(self, error: Exception) -> ErrorCategory:
        if isinstance(error, ValidationError):
            return self.ERROR_CATEGORIES['FORMAT_ERROR']
        elif isinstance(error, ContentError):
            return self.ERROR_CATEGORIES['CONTENT_ERROR']
        elif isinstance(error, DuplicateError):
            return self.ERROR_CATEGORIES['DUPLICATE_ERROR']
        elif isinstance(error, (IOError, NetworkError)):
            return self.ERROR_CATEGORIES['SYSTEM_ERROR']
        else:
            return self.ERROR_CATEGORIES['FATAL_ERROR']
```

### Recovery Strategies

```python
class RecoveryManager:
    """Manages error recovery strategies"""
    
    async def handle_error(
        self,
        error: Exception,
        context: ProcessingContext
    ) -> RecoveryAction:
        category = self.error_classifier.classify(error)
        
        if category['retry_strategy'] == 'immediate':
            return await self.immediate_retry(context)
        
        elif category['retry_strategy'] == 'exponential_backoff':
            return await self.backoff_retry(context)
        
        elif category['retry_strategy'] == 'after_fix':
            return await self.queue_for_user_action(context, error)
        
        elif category['retry_strategy'] == 'skip_or_merge':
            return await self.handle_duplicate(context)
        
        else:
            return await self.mark_as_failed(context, error)
    
    async def immediate_retry(self, context: ProcessingContext):
        if context.retry_count < 3:
            await self.queue_manager.enqueue(
                context.item,
                priority=Priority.HIGH
            )
            return RecoveryAction.RETRIED
        else:
            return await self.escalate_to_user(context)
    
    async def backoff_retry(self, context: ProcessingContext):
        delay = min(60 * (2 ** context.retry_count), 3600)  # Max 1 hour
        await self.scheduled_queue.enqueue_with_delay(
            context.item,
            delay_seconds=delay
        )
        return RecoveryAction.SCHEDULED_RETRY
```

### Error Reporting

```python
class ErrorReporter:
    """Generates detailed error reports"""
    
    async def generate_error_report(
        self,
        upload_id: str
    ) -> ErrorReport:
        errors = await self.get_all_errors(upload_id)
        
        # Group by error type
        error_groups = {}
        for error in errors:
            error_type = error.validation_type
            if error_type not in error_groups:
                error_groups[error_type] = []
            error_groups[error_type].append(error)
        
        # Generate suggestions
        suggestions = {}
        for error_type, errors in error_groups.items():
            suggestions[error_type] = self.generate_suggestions(
                error_type, errors
            )
        
        return ErrorReport(
            upload_id=upload_id,
            total_errors=len(errors),
            error_summary=self.summarize_errors(error_groups),
            suggestions=suggestions,
            downloadable_formats=['csv', 'json', 'xlsx']
        )
    
    def generate_suggestions(
        self,
        error_type: str,
        errors: List[ValidationError]
    ) -> List[str]:
        suggestions = []
        
        if error_type == 'format':
            suggestions.append(
                "Ensure all rows have 'position' and 'term' columns"
            )
            suggestions.append(
                "Check that position values are positive integers"
            )
        
        elif error_type == 'content':
            if any('korean' in str(e) for e in errors):
                suggestions.append(
                    "Verify that terms contain valid Korean characters"
                )
            if any('length' in str(e) for e in errors):
                suggestions.append(
                    "Terms should be between 1-50 characters"
                )
        
        elif error_type == 'duplicate':
            suggestions.append(
                "Remove duplicate entries from your file"
            )
            suggestions.append(
                "Use the deduplication tool to merge duplicates"
            )
        
        return suggestions
```

## 8. Performance Considerations

### Optimization Strategies

#### 1. Streaming Processing
```python
class StreamProcessor:
    """Processes large files without loading into memory"""
    
    async def process_csv_stream(
        self,
        file_stream: AsyncIterator[bytes],
        batch_size: int = 1000
    ):
        buffer = []
        decoder = codecs.getincrementaldecoder('utf-8')()
        csv_buffer = io.StringIO()
        
        async for chunk in file_stream:
            # Decode chunk
            text = decoder.decode(chunk, False)
            csv_buffer.write(text)
            
            # Process complete lines
            csv_buffer.seek(0)
            reader = csv.DictReader(csv_buffer)
            
            for row in reader:
                buffer.append(row)
                
                if len(buffer) >= batch_size:
                    await self.process_batch(buffer)
                    buffer = []
            
            # Keep incomplete line for next iteration
            csv_buffer = io.StringIO(csv_buffer.read())
        
        # Process remaining items
        if buffer:
            await self.process_batch(buffer)
```

#### 2. Database Optimization
```python
# Connection pooling configuration
DATABASE_CONFIG = {
    "pool_size": 20,
    "max_overflow": 10,
    "pool_timeout": 30,
    "pool_recycle": 3600,
    "pool_pre_ping": True
}

# Batch insert optimization
class BatchInserter:
    async def insert_items(self, items: List[PendingItem]):
        # Use prepared statements
        stmt = """
            INSERT INTO pending_items 
            (id, upload_id, position, term, type, priority)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        
        # Batch in transactions
        batch_size = 1000
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            async with self.db.transaction():
                await self.db.executemany(
                    stmt,
                    [(item.id, item.upload_id, item.position,
                      item.term, item.type, item.priority)
                     for item in batch]
                )
```

#### 3. Caching Strategy
```python
class ValidationCache:
    """Caches validation results for repeated items"""
    
    def __init__(self):
        self.cache = LRUCache(maxsize=10000)
        self.bloom_filter = BloomFilter(
            expected_items=1000000,
            false_positive_rate=0.001
        )
    
    async def get_or_validate(
        self,
        item: VocabularyItem,
        validator: Validator
    ) -> ValidationResult:
        cache_key = f"{item.term}:{item.type}"
        
        # Quick bloom filter check
        if cache_key not in self.bloom_filter:
            # Definitely not in cache
            result = await validator.validate(item)
            self.cache[cache_key] = result
            self.bloom_filter.add(cache_key)
            return result
        
        # Might be in cache
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # False positive, validate and cache
        result = await validator.validate(item)
        self.cache[cache_key] = result
        return result
```

#### 4. Parallel Processing
```python
class ParallelValidator:
    """Runs validators in parallel"""
    
    def __init__(self, max_workers: int = 10):
        self.executor = ProcessPoolExecutor(max_workers=max_workers)
        self.validators = [
            FormatValidator(),
            ContentValidator(),
            DuplicateDetector(),
            BusinessRulesEngine()
        ]
    
    async def validate_batch(
        self,
        items: List[VocabularyItem]
    ) -> List[ValidationResult]:
        # Split items into chunks
        chunk_size = max(1, len(items) // self.executor._max_workers)
        chunks = [
            items[i:i + chunk_size]
            for i in range(0, len(items), chunk_size)
        ]
        
        # Process chunks in parallel
        futures = []
        for chunk in chunks:
            future = self.executor.submit(
                self._validate_chunk,
                chunk
            )
            futures.append(future)
        
        # Collect results
        results = []
        for future in asyncio.as_completed(futures):
            chunk_results = await future
            results.extend(chunk_results)
        
        return results
```

### Performance Metrics

```python
class PerformanceMonitor:
    """Monitors system performance"""
    
    async def collect_metrics(self) -> PerformanceMetrics:
        return PerformanceMetrics(
            # Throughput metrics
            uploads_per_minute=await self.calculate_upload_rate(),
            items_per_second=await self.calculate_processing_rate(),
            validation_latency_ms=await self.measure_validation_latency(),
            
            # Resource metrics
            memory_usage_mb=self.get_memory_usage(),
            cpu_usage_percent=self.get_cpu_usage(),
            database_connections=await self.count_db_connections(),
            
            # Queue metrics
            queue_depth=await self.get_total_queue_depth(),
            average_wait_time_seconds=await self.calculate_avg_wait_time(),
            
            # Error metrics
            error_rate=await self.calculate_error_rate(),
            retry_rate=await self.calculate_retry_rate()
        )
```

## 9. Integration with Existing Pipeline

### Integration Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Ingress Toll   │────>│   Message    │────>│    Flashcard    │
│     System      │     │    Queue     │     │    Pipeline     │
└─────────────────┘     └──────────────┘     └─────────────────┘
         │                                              ▲
         │                                              │
         └──────────────  Status Updates  ──────────────┘
```

### Integration Points

#### 1. Pipeline Interface
```python
class PipelineIntegration:
    """Integrates with existing flashcard pipeline"""
    
    def __init__(self):
        self.pipeline = PipelineOrchestrator()
        self.message_queue = MessageQueue()
    
    async def send_to_pipeline(
        self,
        validated_item: ValidatedItem
    ):
        # Convert to pipeline format
        pipeline_item = VocabularyItem(
            position=validated_item.position,
            term=validated_item.term,
            type=validated_item.type
        )
        
        # Send via message queue
        await self.message_queue.publish(
            topic="flashcard.process",
            message={
                "item": pipeline_item.dict(),
                "metadata": {
                    "upload_id": validated_item.upload_id,
                    "ingress_id": validated_item.id,
                    "priority": validated_item.priority
                }
            }
        )
    
    async def receive_pipeline_result(
        self,
        result: PipelineResult
    ):
        # Update ingress records
        await self.update_item_status(
            ingress_id=result.metadata['ingress_id'],
            status='completed',
            result=result
        )
        
        # Update upload progress
        await self.increment_upload_progress(
            upload_id=result.metadata['upload_id']
        )
```

#### 2. Status Synchronization
```python
class StatusSynchronizer:
    """Keeps status in sync between systems"""
    
    async def sync_pipeline_status(self):
        # Subscribe to pipeline events
        async for event in self.pipeline_events.subscribe():
            if event.type == 'item.completed':
                await self.mark_item_completed(event.item_id)
            
            elif event.type == 'item.failed':
                await self.handle_pipeline_failure(
                    event.item_id,
                    event.error
                )
            
            elif event.type == 'cache.hit':
                await self.update_cache_stats(event.item_id)
```

#### 3. Unified API
```python
class UnifiedAPI:
    """Provides unified API for both systems"""
    
    @app.post("/api/v1/flashcards/process")
    async def process_vocabulary(
        request: ProcessRequest,
        user: User = Depends(get_current_user)
    ):
        if request.bulk_upload:
            # Route to ingress system
            return await ingress_api.upload_vocabulary(
                file=request.file,
                priority=request.priority,
                user=user
            )
        else:
            # Direct pipeline processing for small requests
            return await pipeline_api.process_items(
                items=request.items,
                user=user
            )
```

## 10. Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Objectives**:
- Set up database schema
- Implement basic upload handling
- Create validation framework

**Deliverables**:
1. Database migrations
2. Upload API endpoint
3. Format validator
4. Basic queue structure

**Code Structure**:
```
ingress_toll/
├── __init__.py
├── models.py           # Pydantic models
├── database.py         # Database connection and queries
├── upload/
│   ├── __init__.py
│   ├── handler.py      # Upload handling
│   └── chunker.py      # Chunk processing
└── validation/
    ├── __init__.py
    ├── base.py         # Base validator class
    └── format.py       # Format validation
```

### Phase 2: Validation Pipeline (Week 3-4)

**Objectives**:
- Implement all validators
- Create validation pipeline
- Add error reporting

**Deliverables**:
1. Content validator
2. Duplicate detector
3. Business rules engine
4. Validation API endpoints

**New Components**:
```
validation/
├── content.py          # Content validation
├── duplicates.py       # Duplicate detection
├── rules.py           # Business rules
└── pipeline.py        # Validation orchestration

errors/
├── __init__.py
├── classifier.py      # Error classification
└── reporter.py        # Error reporting
```

### Phase 3: Queue Management (Week 5-6)

**Objectives**:
- Implement priority queue
- Add queue monitoring
- Create queue API

**Deliverables**:
1. Priority queue manager
2. Queue monitoring dashboard
3. Queue management endpoints
4. Performance metrics

**New Components**:
```
queue/
├── __init__.py
├── manager.py         # Queue management
├── monitor.py         # Queue monitoring
└── scheduler.py       # Scheduled retries

monitoring/
├── __init__.py
├── metrics.py         # Performance metrics
└── dashboard.py       # Monitoring dashboard
```

### Phase 4: Integration (Week 7-8)

**Objectives**:
- Integrate with flashcard pipeline
- Implement status synchronization
- Create unified API

**Deliverables**:
1. Pipeline integration layer
2. Message queue setup
3. Status synchronization
4. Unified API endpoints

**New Components**:
```
integration/
├── __init__.py
├── pipeline.py        # Pipeline integration
├── messaging.py       # Message queue client
└── synchronizer.py    # Status sync

api/
├── __init__.py
├── unified.py         # Unified API
└── middleware.py      # Auth and rate limiting
```

### Phase 5: Optimization & Polish (Week 9-10)

**Objectives**:
- Performance optimization
- Add caching layer
- Implement monitoring
- Complete documentation

**Deliverables**:
1. Performance optimizations
2. Caching implementation
3. Comprehensive monitoring
4. Production deployment guide

**Final Components**:
```
optimization/
├── __init__.py
├── cache.py          # Validation caching
├── parallel.py       # Parallel processing
└── streaming.py      # Stream processing

deployment/
├── docker/           # Docker configuration
├── kubernetes/       # K8s manifests
└── terraform/        # Infrastructure as code
```

### Testing Strategy

```python
# Test structure
tests/
├── unit/
│   ├── test_validators.py
│   ├── test_queue.py
│   └── test_upload.py
├── integration/
│   ├── test_pipeline_integration.py
│   ├── test_api.py
│   └── test_error_recovery.py
└── performance/
    ├── test_bulk_upload.py
    ├── test_queue_throughput.py
    └── test_validation_speed.py
```

### Monitoring & Observability

```python
# Metrics to track
METRICS = {
    # Performance
    "ingress.upload.duration": "histogram",
    "ingress.validation.duration": "histogram",
    "ingress.queue.depth": "gauge",
    "ingress.processing.rate": "counter",
    
    # Errors
    "ingress.validation.errors": "counter",
    "ingress.system.errors": "counter",
    
    # Business
    "ingress.items.processed": "counter",
    "ingress.uploads.completed": "counter"
}

# Logging configuration
LOGGING = {
    "version": 1,
    "handlers": {
        "json": {
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["json"]
    }
}
```

## Conclusion

The Ingress Toll System provides a robust, scalable solution for handling bulk vocabulary uploads while ensuring data quality and preventing unnecessary API costs. By implementing comprehensive validation, intelligent queue management, and seamless integration with the existing pipeline, it creates a production-ready system capable of handling enterprise-scale vocabulary processing needs.

The phased implementation approach ensures that each component is thoroughly tested before moving to the next, while the monitoring and error recovery mechanisms provide the observability and reliability required for production use.