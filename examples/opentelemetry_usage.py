"""Examples of using OpenTelemetry instrumentation in the Flashcard Pipeline"""

import asyncio
import logging
import os
from pathlib import Path

# Import telemetry components
from flashcard_pipeline.telemetry import (
    init_telemetry,
    create_span,
    record_metric,
    set_span_attributes,
    add_event,
    get_trace_id,
    set_trace_baggage,
    get_trace_baggage,
)
from flashcard_pipeline.telemetry.exporters import (
    ExporterConfig,
    ExporterType,
    configure_exporters,
    create_default_exporters,
)
from flashcard_pipeline.telemetry.instrumentation import instrument_all

# Import instrumented components
from flashcard_pipeline.database.database_manager_instrumented import (
    create_instrumented_database_manager
)
from flashcard_pipeline.cache.cache_manager_instrumented import (
    create_instrumented_cache_manager
)
from flashcard_pipeline.api_client_instrumented import (
    create_instrumented_api_client
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def basic_telemetry_example():
    """Basic example of manual instrumentation"""
    print("\n=== Basic Telemetry Example ===")
    
    # Initialize telemetry
    init_telemetry(
        service_name="flashcard-pipeline-example",
        service_version="1.0.0",
        environment="development",
        enable_console_export=True
    )
    
    # Create a span
    with create_span("example.process_word") as span:
        # Set attributes
        set_span_attributes({
            "word": "안녕하세요",
            "language": "korean",
            "difficulty": 3
        })
        
        # Add an event
        add_event(
            "processing_started",
            attributes={"timestamp": "2025-01-11T10:00:00Z"}
        )
        
        # Simulate some work
        await asyncio.sleep(0.1)
        
        # Record a metric
        record_metric(
            "words.processed",
            1,
            metric_type="counter",
            attributes={"language": "korean"}
        )
        
        # Get trace ID for correlation
        trace_id = get_trace_id()
        print(f"Trace ID: {trace_id}")
        
        # Set baggage for cross-cutting concerns
        set_trace_baggage("user.id", "user123")
        set_trace_baggage("session.id", "session456")
        
        print(f"User ID from baggage: {get_trace_baggage('user.id')}")


async def database_instrumentation_example():
    """Example of instrumented database operations"""
    print("\n\n=== Database Instrumentation Example ===")
    
    # Create instrumented database manager
    db = create_instrumented_database_manager(
        ":memory:",  # In-memory database for example
        enable_query_cache=True
    )
    
    await db.initialize()
    
    # Create schema
    with create_span("example.setup_database"):
        await db.execute("""
            CREATE TABLE flashcards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                translation TEXT,
                difficulty INTEGER DEFAULT 3,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.execute("""
            CREATE INDEX idx_flashcards_word ON flashcards(word)
        """)
    
    # Insert data with automatic instrumentation
    print("\nInserting flashcards...")
    
    with create_span("example.insert_flashcards"):
        flashcards = [
            ("안녕하세요", "Hello", 1),
            ("감사합니다", "Thank you", 2),
            ("사랑해요", "I love you", 3),
            ("미안해요", "I'm sorry", 2),
            ("잘 가요", "Goodbye", 1),
        ]
        
        await db.execute_many(
            "INSERT INTO flashcards (word, translation, difficulty) VALUES (?, ?, ?)",
            flashcards
        )
        
        print(f"Inserted {len(flashcards)} flashcards")
    
    # Query with instrumentation
    print("\nQuerying flashcards...")
    
    with create_span("example.query_flashcards"):
        # Simple query
        result = await db.execute(
            "SELECT * FROM flashcards WHERE difficulty = ?",
            (2,)
        )
        print(f"Found {len(result.rows)} flashcards with difficulty 2")
        
        # Query that will be marked as slow
        await asyncio.sleep(0.2)  # Simulate slow query
        result = await db.execute(
            "SELECT * FROM flashcards WHERE word LIKE ?",
            ("%사%",)
        )
        print(f"Found {len(result.rows)} flashcards containing '사'")
    
    # Transaction with instrumentation
    print("\nExecuting transaction...")
    
    async with db.transaction():
        await db.execute(
            "UPDATE flashcards SET difficulty = difficulty + 1 WHERE difficulty < 5"
        )
        print("Updated flashcard difficulties")
    
    # Get statistics
    stats = await db.get_query_statistics_with_telemetry()
    print(f"\nDatabase statistics:")
    print(f"  Total queries: {stats['total_queries']}")
    print(f"  Slow queries: {len(stats['slow_queries'])}")
    print(f"  Cache hit rate: {stats.get('cache_hit_rate', 0):.1%}")
    
    await db.close()


async def cache_instrumentation_example():
    """Example of instrumented cache operations"""
    print("\n\n=== Cache Instrumentation Example ===")
    
    # Create instrumented cache manager
    cache = create_instrumented_cache_manager(
        l1_config={"max_size": 100},
        stampede_protection=True
    )
    
    # Basic cache operations
    with create_span("example.cache_operations"):
        # Set values
        await cache.set("user:123", {"name": "John", "role": "admin"})
        await cache.set("user:456", {"name": "Jane", "role": "user"})
        
        print("Cached user data")
        
        # Get values (cache hit)
        user = await cache.get("user:123")
        print(f"Retrieved user: {user}")
        
        # Get with compute function (cache miss)
        async def fetch_user(user_id: str):
            print(f"  Fetching user {user_id} from database...")
            await asyncio.sleep(0.1)
            return {"name": f"User {user_id}", "role": "guest"}
        
        user = await cache.get("user:789", lambda: fetch_user("789"))
        print(f"Retrieved user: {user}")
        
        # Second call should hit cache
        user = await cache.get("user:789", lambda: fetch_user("789"))
        print(f"Retrieved user (cached): {user}")
    
    # Demonstrate cache stampede protection
    print("\nDemonstrating stampede protection...")
    
    with create_span("example.stampede_test"):
        async def expensive_operation():
            print("  Running expensive operation...")
            await asyncio.sleep(0.5)
            return "expensive_result"
        
        # Launch multiple concurrent requests
        tasks = [
            cache.get("expensive_key", expensive_operation)
            for _ in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        print(f"All requests got: {results[0]}")
        print("Expensive operation was called only once!")
    
    # Tag-based operations
    print("\nDemonstrating tag-based cache management...")
    
    with create_span("example.tag_operations"):
        # Cache with tags
        await cache.set("session:123", "data1", tags=["session", "user:123"])
        await cache.set("profile:123", "data2", tags=["profile", "user:123"])
        await cache.set("session:456", "data3", tags=["session", "user:456"])
        
        # Delete by tag
        deleted = await cache.delete_by_tag("user:123")
        print(f"Deleted {deleted} entries for user:123")
    
    # Get cache statistics
    stats = cache.get_statistics()
    print(f"\nCache statistics:")
    print(f"  L1 hit rate: {stats['l1']['hit_rate']:.1%}")
    print(f"  Overall hit rate: {stats['overall_hit_rate']:.1%}")
    print(f"  L1 entries: {stats['l1']['entries']}")
    print(f"  L1 evictions: {stats['l1']['evictions']}")


async def api_instrumentation_example():
    """Example of instrumented API client operations"""
    print("\n\n=== API Client Instrumentation Example ===")
    
    # Note: This requires a valid API key
    api_key = os.getenv("OPENROUTER_API_KEY", "test-key")
    
    if api_key == "test-key":
        print("Skipping API example (no API key set)")
        return
    
    # Create instrumented API client
    client = create_instrumented_api_client(
        api_key=api_key,
        default_model="anthropic/claude-3-haiku"
    )
    
    # Process a flashcard
    with create_span("example.process_flashcard"):
        try:
            # Stage 1
            stage1_result = await client.process_stage1(
                word="안녕하세요",
                context="Greeting someone in the morning"
            )
            print(f"Stage 1 result: {stage1_result}")
            
            # Stage 2
            stage2_result = await client.process_stage2(stage1_result)
            print(f"Stage 2 result: {stage2_result}")
            
        except Exception as e:
            print(f"API error: {e}")


async def distributed_tracing_example():
    """Example of distributed tracing across components"""
    print("\n\n=== Distributed Tracing Example ===")
    
    # Initialize components
    db = create_instrumented_database_manager(":memory:")
    cache = create_instrumented_cache_manager()
    
    await db.initialize()
    
    # Create schema
    await db.execute("""
        CREATE TABLE words (
            id INTEGER PRIMARY KEY,
            word TEXT NOT NULL,
            processed BOOLEAN DEFAULT FALSE
        )
    """)
    
    # Simulate a distributed operation
    with create_span("pipeline.process_batch") as parent_span:
        # Set baggage for the entire operation
        set_trace_baggage("batch.id", "batch123")
        set_trace_baggage("batch.size", "10")
        
        # Step 1: Fetch words from database
        with create_span("pipeline.fetch_words"):
            await db.execute_many(
                "INSERT INTO words (word) VALUES (?)",
                [("word1",), ("word2",), ("word3",)]
            )
            
            result = await db.execute("SELECT * FROM words WHERE processed = 0")
            words = result.rows
            print(f"Fetched {len(words)} unprocessed words")
        
        # Step 2: Process each word
        for word_row in words:
            word_id, word, _ = word_row
            
            with create_span(
                "pipeline.process_word",
                attributes={"word.id": word_id, "word.text": word}
            ):
                # Check cache first
                cached_result = await cache.get(f"word:{word}")
                
                if cached_result:
                    add_event("cache_hit", {"word": word})
                    print(f"  {word}: Retrieved from cache")
                else:
                    # Simulate API processing
                    add_event("api_call", {"word": word})
                    await asyncio.sleep(0.1)
                    
                    # Cache result
                    result = {"word": word, "translation": f"Translation of {word}"}
                    await cache.set(f"word:{word}", result, ttl=3600)
                    print(f"  {word}: Processed and cached")
                
                # Update database
                await db.execute(
                    "UPDATE words SET processed = TRUE WHERE id = ?",
                    (word_id,)
                )
        
        # Step 3: Report completion
        with create_span("pipeline.report"):
            add_event(
                "batch_completed",
                attributes={
                    "batch.id": get_trace_baggage("batch.id"),
                    "batch.size": get_trace_baggage("batch.size"),
                    "words_processed": len(words)
                }
            )
            print(f"\nBatch {get_trace_baggage('batch.id')} completed!")
            print(f"Trace ID for correlation: {get_trace_id()}")
    
    await db.close()


async def metrics_example():
    """Example of custom metrics recording"""
    print("\n\n=== Custom Metrics Example ===")
    
    # Initialize telemetry
    init_telemetry(enable_console_export=True)
    
    # Business metrics
    with create_span("example.business_metrics"):
        # Counter - track events
        record_metric(
            "flashcards.created",
            5,
            metric_type="counter",
            attributes={"difficulty": "medium"}
        )
        
        # Histogram - track distributions
        for i in range(10):
            processing_time = 100 + (i * 10)  # 100-190ms
            record_metric(
                "flashcard.processing_time",
                processing_time,
                metric_type="histogram",
                attributes={"stage": "translation"},
                unit="ms"
            )
        
        # Up/Down Counter - track values that can increase/decrease
        record_metric(
            "flashcards.queue_size",
            10,
            metric_type="up_down_counter"
        )
        
        record_metric(
            "flashcards.queue_size",
            -3,  # Processed 3 items
            metric_type="up_down_counter"
        )
        
        print("Recorded custom business metrics")


async def error_handling_example():
    """Example of error instrumentation"""
    print("\n\n=== Error Handling Example ===")
    
    # Simulated error scenarios
    with create_span("example.error_scenarios"):
        # Handled error
        try:
            with create_span("operation.with_error") as span:
                # Simulate work
                await asyncio.sleep(0.1)
                
                # Simulate error
                raise ValueError("Something went wrong")
                
        except ValueError as e:
            print(f"Caught error: {e}")
            # Error was automatically recorded by span
        
        # Error with custom handling
        with create_span("operation.with_recovery") as span:
            try:
                # Simulate failure
                raise ConnectionError("Database unavailable")
                
            except ConnectionError as e:
                # Record error but mark as recovered
                span.record_exception(e, attributes={"recovered": True})
                span.set_status(trace.Status(trace.StatusCode.OK))
                
                add_event(
                    "fallback_used",
                    attributes={"fallback": "cache", "reason": str(e)}
                )
                
                print("Used cache fallback due to database error")


async def main():
    """Run all examples"""
    print("OpenTelemetry Instrumentation Examples")
    print("=" * 50)
    
    # Set up exporters based on environment
    environment = os.getenv("ENVIRONMENT", "development")
    
    if environment == "development":
        print("Running in development mode - traces will be printed to console")
        print("To use Jaeger, run: docker run -p 16686:16686 -p 6831:6831/udp jaegertracing/all-in-one")
    
    # Run examples
    await basic_telemetry_example()
    await database_instrumentation_example()
    await cache_instrumentation_example()
    await api_instrumentation_example()
    await distributed_tracing_example()
    await metrics_example()
    await error_handling_example()
    
    print("\n" + "=" * 50)
    print("Examples completed!")
    print("\nNext steps:")
    print("1. Set up Jaeger: docker run -p 16686:16686 -p 6831:6831/udp jaegertracing/all-in-one")
    print("2. View traces at: http://localhost:16686")
    print("3. For production, configure OTLP exporter with your observability backend")


if __name__ == "__main__":
    asyncio.run(main())