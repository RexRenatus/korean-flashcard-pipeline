"""Examples of using the enhanced database manager with connection pooling"""

import asyncio
import time
from pathlib import Path
import tempfile
from datetime import datetime

from flashcard_pipeline.database.database_manager_v2 import (
    DatabaseManager,
    ConnectionPool,
)


async def basic_connection_pool_example():
    """Basic usage of connection pooling"""
    print("\n=== Basic Connection Pool Example ===")
    
    # Create temporary database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "example.db"
        
        # Initialize pool with custom configuration
        pool = ConnectionPool(
            str(db_path),
            min_size=2,      # Minimum 2 connections
            max_size=10,     # Maximum 10 connections
            connection_timeout=5.0,  # 5 second timeout
            idle_timeout=300.0,      # Close idle connections after 5 minutes
        )
        
        await pool.initialize()
        
        print(f"Pool initialized with {pool.min_size} connections")
        
        # Use connections
        async def worker(worker_id: int):
            async with pool.acquire() as conn:
                # Each worker gets its own connection from the pool
                cursor = await conn.execute(
                    "SELECT datetime('now'), ?",
                    (f"Worker {worker_id}",)
                )
                result = await cursor.fetchone()
                print(f"Worker {worker_id}: {result}")
        
        # Run multiple workers concurrently
        workers = [worker(i) for i in range(5)]
        await asyncio.gather(*workers)
        
        # Check pool statistics
        stats = pool.get_statistics()
        print(f"\nPool Statistics:")
        print(f"  Total connections: {stats['current_size']}")
        print(f"  Available: {stats['available']}")
        print(f"  In use: {stats['in_use']}")
        print(f"  Connections reused: {stats['connections_reused']}")
        
        await pool.close()


async def database_manager_example():
    """Example using the enhanced database manager"""
    print("\n\n=== Database Manager Example ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "flashcards.db"
        
        # Create database manager with optimized settings
        db_manager = DatabaseManager(
            str(db_path),
            pool_config={
                "min_size": 3,
                "max_size": 10,
            },
            slow_query_threshold=0.1,  # Log queries slower than 100ms
            enable_query_cache=True,
            cache_ttl=300.0,  # 5 minute cache
        )
        
        await db_manager.initialize()
        
        # Create schema
        await db_manager.execute("""
            CREATE TABLE flashcards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                translation TEXT NOT NULL,
                difficulty INTEGER DEFAULT 3,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_reviewed TIMESTAMP
            )
        """)
        
        await db_manager.execute("""
            CREATE INDEX idx_flashcards_word ON flashcards(word)
        """)
        
        print("Database schema created")
        
        # Insert sample data
        flashcards = [
            ("안녕하세요", "Hello", 1),
            ("감사합니다", "Thank you", 2),
            ("사랑해요", "I love you", 3),
            ("미안합니다", "I'm sorry", 2),
            ("잘 먹겠습니다", "I will eat well", 4),
        ]
        
        for word, translation, difficulty in flashcards:
            await db_manager.execute(
                "INSERT INTO flashcards (word, translation, difficulty) VALUES (?, ?, ?)",
                (word, translation, difficulty)
            )
        
        print(f"Inserted {len(flashcards)} flashcards")
        
        # Query with caching
        print("\nQuerying flashcards (first time - no cache):")
        result1 = await db_manager.execute(
            "SELECT * FROM flashcards WHERE difficulty <= ?",
            (3,)
        )
        print(f"  Found {len(result1.rows)} flashcards")
        print(f"  Execution time: {result1.execution_time:.3f}s")
        print(f"  Cached: {result1.cached}")
        
        # Same query - should be cached
        print("\nSame query (should be cached):")
        result2 = await db_manager.execute(
            "SELECT * FROM flashcards WHERE difficulty <= ?",
            (3,)
        )
        print(f"  Execution time: {result2.execution_time:.3f}s")
        print(f"  Cached: {result2.cached}")
        
        # Get query statistics
        stats = db_manager.get_query_statistics()
        print(f"\nQuery Statistics:")
        print(f"  Total queries: {stats['total_queries']}")
        print(f"  Cache size: {stats['cache_size']}")
        
        await db_manager.close()


async def transaction_example():
    """Example of transaction management"""
    print("\n\n=== Transaction Example ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "transactions.db"
        
        db_manager = DatabaseManager(str(db_path))
        await db_manager.initialize()
        
        # Create tables
        await db_manager.execute("""
            CREATE TABLE accounts (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                balance DECIMAL(10, 2) DEFAULT 0
            )
        """)
        
        await db_manager.execute("""
            CREATE TABLE transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_account INTEGER,
                to_account INTEGER,
                amount DECIMAL(10, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (from_account) REFERENCES accounts(id),
                FOREIGN KEY (to_account) REFERENCES accounts(id)
            )
        """)
        
        # Create accounts
        await db_manager.execute(
            "INSERT INTO accounts (id, name, balance) VALUES (?, ?, ?)",
            (1, "Alice", 1000.00)
        )
        await db_manager.execute(
            "INSERT INTO accounts (id, name, balance) VALUES (?, ?, ?)",
            (2, "Bob", 500.00)
        )
        
        print("Initial balances:")
        result = await db_manager.execute("SELECT * FROM accounts")
        for row in result.rows:
            print(f"  {row[1]}: ${row[2]:.2f}")
        
        # Transfer money with transaction
        transfer_amount = 250.00
        
        try:
            async with db_manager.transaction():
                # Deduct from Alice
                await db_manager.execute(
                    "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                    (transfer_amount, 1)
                )
                
                # Add to Bob
                await db_manager.execute(
                    "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                    (transfer_amount, 2)
                )
                
                # Record transaction
                await db_manager.execute(
                    "INSERT INTO transactions (from_account, to_account, amount) VALUES (?, ?, ?)",
                    (1, 2, transfer_amount)
                )
                
                print(f"\nTransferred ${transfer_amount} from Alice to Bob")
                
        except Exception as e:
            print(f"Transaction failed: {e}")
        
        # Check final balances
        print("\nFinal balances:")
        result = await db_manager.execute("SELECT * FROM accounts")
        for row in result.rows:
            print(f"  {row[1]}: ${row[2]:.2f}")
        
        # Test failed transaction (insufficient funds)
        print("\nAttempting invalid transfer...")
        try:
            async with db_manager.transaction():
                # Try to transfer more than available
                await db_manager.execute(
                    "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                    (2000.00, 1)
                )
                
                # Check constraint (manual validation)
                result = await db_manager.execute(
                    "SELECT balance FROM accounts WHERE id = ?",
                    (1,)
                )
                if result.rows[0][0] < 0:
                    raise ValueError("Insufficient funds")
                
        except ValueError as e:
            print(f"Transaction rolled back: {e}")
        
        # Verify rollback
        print("\nBalances after failed transaction:")
        result = await db_manager.execute("SELECT * FROM accounts")
        for row in result.rows:
            print(f"  {row[1]}: ${row[2]:.2f}")
        
        await db_manager.close()


async def batch_operations_example():
    """Example of batch operations"""
    print("\n\n=== Batch Operations Example ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "batch.db"
        
        db_manager = DatabaseManager(str(db_path))
        await db_manager.initialize()
        
        # Create table
        await db_manager.execute("""
            CREATE TABLE metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Prepare batch data
        metrics_data = [
            ("cpu_usage", 45.2),
            ("memory_usage", 62.8),
            ("disk_usage", 78.1),
            ("network_in", 1024.5),
            ("network_out", 512.3),
            ("response_time", 0.125),
            ("error_rate", 0.02),
            ("requests_per_sec", 150.7),
        ]
        
        # Insert batch data
        print("Inserting batch metrics...")
        start_time = time.time()
        
        params_list = [(name, value) for name, value in metrics_data]
        results = await db_manager.execute_many(
            "INSERT INTO metrics (metric_name, value) VALUES (?, ?)",
            params_list
        )
        
        batch_time = time.time() - start_time
        print(f"Inserted {len(results)} metrics in {batch_time:.3f}s")
        print(f"Average time per insert: {batch_time/len(results)*1000:.1f}ms")
        
        # Compare with individual inserts
        print("\nComparing with individual inserts...")
        start_time = time.time()
        
        for name, value in metrics_data:
            await db_manager.execute(
                "INSERT INTO metrics (metric_name, value) VALUES (?, ?)",
                (name + "_individual", value)
            )
        
        individual_time = time.time() - start_time
        print(f"Individual inserts took {individual_time:.3f}s")
        print(f"Batch operation was {individual_time/batch_time:.1f}x faster")
        
        await db_manager.close()


async def query_optimization_example():
    """Example of query optimization and analysis"""
    print("\n\n=== Query Optimization Example ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "optimization.db"
        
        db_manager = DatabaseManager(str(db_path))
        await db_manager.initialize()
        
        # Create table with and without indexes
        await db_manager.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT NOT NULL,
                status INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert sample data
        print("Inserting sample data...")
        for i in range(1000):
            await db_manager.execute(
                "INSERT INTO users (username, email, status) VALUES (?, ?, ?)",
                (f"user{i}", f"user{i}@example.com", i % 3)
            )
        
        # Analyze query without index
        print("\nAnalyzing query WITHOUT index:")
        analysis1 = await db_manager.optimize_query(
            "SELECT * FROM users WHERE status = 1 ORDER BY created_at"
        )
        
        print(f"Query plan: {analysis1['plan']}")
        print(f"Suggestions:")
        for suggestion in analysis1['suggestions']:
            print(f"  - [{suggestion['severity']}] {suggestion['message']}")
        
        # Create index
        print("\nCreating index on status column...")
        await db_manager.execute("CREATE INDEX idx_users_status ON users(status)")
        
        # Analyze same query with index
        print("\nAnalyzing query WITH index:")
        analysis2 = await db_manager.optimize_query(
            "SELECT * FROM users WHERE status = 1 ORDER BY created_at"
        )
        
        print(f"Query plan: {analysis2['plan']}")
        print(f"Estimated cost reduced: {analysis1['estimated_cost']} -> {analysis2['estimated_cost']}")
        
        await db_manager.close()


async def monitoring_example():
    """Example of performance monitoring"""
    print("\n\n=== Performance Monitoring Example ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "monitoring.db"
        
        # Create manager with low slow query threshold
        db_manager = DatabaseManager(
            str(db_path),
            slow_query_threshold=0.01,  # 10ms
            enable_query_cache=True
        )
        await db_manager.initialize()
        
        # Create test table
        await db_manager.execute("""
            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                data JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Simulate various queries
        print("Executing various queries...")
        
        # Fast query
        await db_manager.execute(
            "INSERT INTO events (event_type, data) VALUES (?, ?)",
            ("click", '{"button": "submit"}')
        )
        
        # Slower query (full table scan)
        await db_manager.execute(
            "SELECT * FROM events WHERE json_extract(data, '$.button') = 'submit'"
        )
        
        # Cached query
        for i in range(3):
            await db_manager.execute("SELECT COUNT(*) FROM events")
        
        # Get performance statistics
        print("\nConnection Pool Statistics:")
        pool_stats = db_manager.pool.get_statistics()
        print(f"  Connections: {pool_stats['current_size']} (available: {pool_stats['available']})")
        print(f"  Avg acquisition time: {pool_stats['avg_acquisition_time']*1000:.1f}ms")
        print(f"  Timeouts: {pool_stats['timeouts']}")
        
        print("\nQuery Statistics:")
        query_stats = db_manager.get_query_statistics()
        print(f"  Total queries: {query_stats['total_queries']}")
        print(f"  Cache size: {query_stats['cache_size']}")
        
        print("\nTop queries by time:")
        for i, query in enumerate(query_stats['queries'][:3]):
            print(f"  {i+1}. Query hash: {query['query_hash'][:8]}...")
            print(f"     Count: {query['count']}, Avg time: {query['avg_time']*1000:.1f}ms")
            print(f"     Error rate: {query['error_rate']:.1%}")
        
        await db_manager.close()


async def main():
    """Run all examples"""
    examples = [
        basic_connection_pool_example,
        database_manager_example,
        transaction_example,
        batch_operations_example,
        query_optimization_example,
        monitoring_example,
    ]
    
    for example in examples:
        await example()
        print("\n" + "="*60)
    
    print("\nAll examples completed!")
    print("\nKey takeaways:")
    print("1. Connection pooling reduces overhead and improves performance")
    print("2. Query caching eliminates redundant database hits")
    print("3. Transactions ensure data consistency")
    print("4. Batch operations are significantly faster than individual queries")
    print("5. Proper indexing is crucial for query performance")
    print("6. Monitoring helps identify bottlenecks and optimization opportunities")


if __name__ == "__main__":
    asyncio.run(main())