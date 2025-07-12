"""Performance tests to measure OpenTelemetry overhead"""

import asyncio
import time
import statistics
import tempfile
from typing import List, Dict, Any
import pytest

from flashcard_pipeline.telemetry import init_telemetry
from flashcard_pipeline.database.database_manager_v2 import DatabaseManager
from flashcard_pipeline.database.database_manager_instrumented import (
    create_instrumented_database_manager
)
from flashcard_pipeline.cache.cache_manager_v2 import CacheManager
from flashcard_pipeline.cache.cache_manager_instrumented import (
    create_instrumented_cache_manager
)


class TelemetryOverheadBenchmark:
    """Benchmark telemetry overhead for various operations"""
    
    def __init__(self):
        self.results = {}
    
    async def setup(self):
        """Initialize components for testing"""
        # Initialize telemetry (no export for benchmarking)
        init_telemetry(
            service_name="benchmark",
            enable_console_export=False
        )
    
    async def benchmark_database_operations(self, iterations: int = 1000):
        """Benchmark database operations with and without instrumentation"""
        print("\n=== Database Operations Benchmark ===")
        
        # Setup databases
        with tempfile.NamedTemporaryFile() as tmp:
            db_path = tmp.name
            
            # Non-instrumented database
            db_plain = DatabaseManager(db_path + "_plain")
            await db_plain.initialize()
            
            # Instrumented database
            db_instrumented = create_instrumented_database_manager(db_path + "_inst")
            await db_instrumented.initialize()
            
            # Create schema
            schema = """
                CREATE TABLE benchmark (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    value TEXT NOT NULL,
                    score INTEGER DEFAULT 0
                )
            """
            await db_plain.execute(schema)
            await db_instrumented.execute(schema)
            
            # Benchmark INSERT operations
            print(f"\nINSERT operations ({iterations} iterations):")
            
            # Plain
            start = time.perf_counter()
            for i in range(iterations):
                await db_plain.execute(
                    "INSERT INTO benchmark (value, score) VALUES (?, ?)",
                    (f"value_{i}", i % 100)
                )
            plain_insert_time = time.perf_counter() - start
            
            # Instrumented
            start = time.perf_counter()
            for i in range(iterations):
                await db_instrumented.execute(
                    "INSERT INTO benchmark (value, score) VALUES (?, ?)",
                    (f"value_{i}", i % 100)
                )
            inst_insert_time = time.perf_counter() - start
            
            # Calculate overhead
            insert_overhead = ((inst_insert_time - plain_insert_time) / plain_insert_time) * 100
            
            print(f"  Plain: {plain_insert_time:.3f}s ({plain_insert_time/iterations*1000:.2f}ms per op)")
            print(f"  Instrumented: {inst_insert_time:.3f}s ({inst_insert_time/iterations*1000:.2f}ms per op)")
            print(f"  Overhead: {insert_overhead:.1f}%")
            
            # Benchmark SELECT operations
            print(f"\nSELECT operations ({iterations} iterations):")
            
            # Plain
            start = time.perf_counter()
            for i in range(iterations):
                await db_plain.execute(
                    "SELECT * FROM benchmark WHERE score = ?",
                    (i % 100,)
                )
            plain_select_time = time.perf_counter() - start
            
            # Instrumented
            start = time.perf_counter()
            for i in range(iterations):
                await db_instrumented.execute(
                    "SELECT * FROM benchmark WHERE score = ?",
                    (i % 100,)
                )
            inst_select_time = time.perf_counter() - start
            
            # Calculate overhead
            select_overhead = ((inst_select_time - plain_select_time) / plain_select_time) * 100
            
            print(f"  Plain: {plain_select_time:.3f}s ({plain_select_time/iterations*1000:.2f}ms per op)")
            print(f"  Instrumented: {inst_select_time:.3f}s ({inst_select_time/iterations*1000:.2f}ms per op)")
            print(f"  Overhead: {select_overhead:.1f}%")
            
            # Store results
            self.results["database"] = {
                "insert": {
                    "plain_ms": plain_insert_time / iterations * 1000,
                    "instrumented_ms": inst_insert_time / iterations * 1000,
                    "overhead_percent": insert_overhead
                },
                "select": {
                    "plain_ms": plain_select_time / iterations * 1000,
                    "instrumented_ms": inst_select_time / iterations * 1000,
                    "overhead_percent": select_overhead
                }
            }
            
            await db_plain.close()
            await db_instrumented.close()
    
    async def benchmark_cache_operations(self, iterations: int = 10000):
        """Benchmark cache operations with and without instrumentation"""
        print("\n\n=== Cache Operations Benchmark ===")
        
        # Setup caches
        cache_plain = CacheManager(l1_config={"max_size": 1000})
        cache_instrumented = create_instrumented_cache_manager(
            l1_config={"max_size": 1000}
        )
        
        # Prepare data
        test_data = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}
        
        # Benchmark SET operations
        print(f"\nSET operations ({iterations} iterations):")
        
        # Plain
        start = time.perf_counter()
        for i in range(iterations):
            key = f"key_{i % 100}"
            await cache_plain.set(key, test_data[key])
        plain_set_time = time.perf_counter() - start
        
        # Instrumented
        start = time.perf_counter()
        for i in range(iterations):
            key = f"key_{i % 100}"
            await cache_instrumented.set(key, test_data[key])
        inst_set_time = time.perf_counter() - start
        
        # Calculate overhead
        set_overhead = ((inst_set_time - plain_set_time) / plain_set_time) * 100
        
        print(f"  Plain: {plain_set_time:.3f}s ({plain_set_time/iterations*1000:.2f}ms per op)")
        print(f"  Instrumented: {inst_set_time:.3f}s ({inst_set_time/iterations*1000:.2f}ms per op)")
        print(f"  Overhead: {set_overhead:.1f}%")
        
        # Benchmark GET operations (cache hits)
        print(f"\nGET operations - hits ({iterations} iterations):")
        
        # Plain
        start = time.perf_counter()
        for i in range(iterations):
            key = f"key_{i % 100}"
            await cache_plain.get(key)
        plain_get_time = time.perf_counter() - start
        
        # Instrumented
        start = time.perf_counter()
        for i in range(iterations):
            key = f"key_{i % 100}"
            await cache_instrumented.get(key)
        inst_get_time = time.perf_counter() - start
        
        # Calculate overhead
        get_overhead = ((inst_get_time - plain_get_time) / plain_get_time) * 100
        
        print(f"  Plain: {plain_get_time:.3f}s ({plain_get_time/iterations*1000:.2f}ms per op)")
        print(f"  Instrumented: {inst_get_time:.3f}s ({inst_get_time/iterations*1000:.2f}ms per op)")
        print(f"  Overhead: {get_overhead:.1f}%")
        
        # Store results
        self.results["cache"] = {
            "set": {
                "plain_ms": plain_set_time / iterations * 1000,
                "instrumented_ms": inst_set_time / iterations * 1000,
                "overhead_percent": set_overhead
            },
            "get_hit": {
                "plain_ms": plain_get_time / iterations * 1000,
                "instrumented_ms": inst_get_time / iterations * 1000,
                "overhead_percent": get_overhead
            }
        }
    
    async def benchmark_concurrent_operations(self, workers: int = 10, operations_per_worker: int = 100):
        """Benchmark concurrent operations"""
        print("\n\n=== Concurrent Operations Benchmark ===")
        print(f"Workers: {workers}, Operations per worker: {operations_per_worker}")
        
        # Setup
        cache_plain = CacheManager()
        cache_instrumented = create_instrumented_cache_manager()
        
        async def worker_plain(worker_id: int):
            """Plain cache worker"""
            for i in range(operations_per_worker):
                key = f"worker_{worker_id}_item_{i}"
                await cache_plain.set(key, f"value_{i}")
                await cache_plain.get(key)
        
        async def worker_instrumented(worker_id: int):
            """Instrumented cache worker"""
            for i in range(operations_per_worker):
                key = f"worker_{worker_id}_item_{i}"
                await cache_instrumented.set(key, f"value_{i}")
                await cache_instrumented.get(key)
        
        # Benchmark plain
        start = time.perf_counter()
        tasks = [worker_plain(i) for i in range(workers)]
        await asyncio.gather(*tasks)
        plain_time = time.perf_counter() - start
        
        # Benchmark instrumented
        start = time.perf_counter()
        tasks = [worker_instrumented(i) for i in range(workers)]
        await asyncio.gather(*tasks)
        inst_time = time.perf_counter() - start
        
        # Calculate metrics
        total_ops = workers * operations_per_worker * 2  # set + get
        plain_ops_per_sec = total_ops / plain_time
        inst_ops_per_sec = total_ops / inst_time
        overhead = ((inst_time - plain_time) / plain_time) * 100
        
        print(f"\nResults:")
        print(f"  Plain: {plain_time:.3f}s ({plain_ops_per_sec:.0f} ops/sec)")
        print(f"  Instrumented: {inst_time:.3f}s ({inst_ops_per_sec:.0f} ops/sec)")
        print(f"  Overhead: {overhead:.1f}%")
        
        self.results["concurrent"] = {
            "plain_ops_per_sec": plain_ops_per_sec,
            "instrumented_ops_per_sec": inst_ops_per_sec,
            "overhead_percent": overhead
        }
    
    async def benchmark_memory_usage(self):
        """Benchmark memory overhead"""
        print("\n\n=== Memory Usage Benchmark ===")
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        print(f"Baseline memory: {baseline_memory:.1f} MB")
        
        # Create many instrumented spans
        from flashcard_pipeline.telemetry import create_span
        
        spans_created = 0
        start_memory = process.memory_info().rss / 1024 / 1024
        
        for i in range(1000):
            with create_span(f"test.span_{i}") as span:
                span.set_attribute("index", i)
                span.add_event("test_event", {"data": "x" * 100})
                spans_created += 1
        
        end_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = end_memory - start_memory
        memory_per_span = memory_increase / spans_created * 1000  # KB per span
        
        print(f"After creating {spans_created} spans:")
        print(f"  Memory increase: {memory_increase:.1f} MB")
        print(f"  Memory per span: {memory_per_span:.2f} KB")
        
        self.results["memory"] = {
            "baseline_mb": baseline_memory,
            "memory_per_span_kb": memory_per_span,
            "total_increase_mb": memory_increase
        }
    
    def print_summary(self):
        """Print summary of benchmark results"""
        print("\n" + "=" * 60)
        print("TELEMETRY OVERHEAD SUMMARY")
        print("=" * 60)
        
        if "database" in self.results:
            db = self.results["database"]
            print("\nDatabase Operations:")
            print(f"  INSERT overhead: {db['insert']['overhead_percent']:.1f}%")
            print(f"  SELECT overhead: {db['select']['overhead_percent']:.1f}%")
        
        if "cache" in self.results:
            cache = self.results["cache"]
            print("\nCache Operations:")
            print(f"  SET overhead: {cache['set']['overhead_percent']:.1f}%")
            print(f"  GET (hit) overhead: {cache['get_hit']['overhead_percent']:.1f}%")
        
        if "concurrent" in self.results:
            conc = self.results["concurrent"]
            print("\nConcurrent Operations:")
            print(f"  Throughput overhead: {conc['overhead_percent']:.1f}%")
            print(f"  Ops/sec reduction: {conc['plain_ops_per_sec'] - conc['instrumented_ops_per_sec']:.0f}")
        
        if "memory" in self.results:
            mem = self.results["memory"]
            print("\nMemory Usage:")
            print(f"  Per-span overhead: {mem['memory_per_span_kb']:.2f} KB")
        
        # Overall assessment
        overheads = []
        if "database" in self.results:
            overheads.extend([
                self.results["database"]["insert"]["overhead_percent"],
                self.results["database"]["select"]["overhead_percent"]
            ])
        if "cache" in self.results:
            overheads.extend([
                self.results["cache"]["set"]["overhead_percent"],
                self.results["cache"]["get_hit"]["overhead_percent"]
            ])
        
        if overheads:
            avg_overhead = statistics.mean(overheads)
            max_overhead = max(overheads)
            
            print(f"\nOverall Performance Impact:")
            print(f"  Average overhead: {avg_overhead:.1f}%")
            print(f"  Maximum overhead: {max_overhead:.1f}%")
            
            if avg_overhead < 5:
                print("  Assessment: EXCELLENT - Minimal impact")
            elif avg_overhead < 10:
                print("  Assessment: GOOD - Acceptable for most use cases")
            elif avg_overhead < 20:
                print("  Assessment: MODERATE - Consider sampling for high-traffic")
            else:
                print("  Assessment: HIGH - Optimization recommended")


async def main():
    """Run all benchmarks"""
    print("OpenTelemetry Performance Overhead Benchmark")
    print("=" * 60)
    
    benchmark = TelemetryOverheadBenchmark()
    await benchmark.setup()
    
    # Run benchmarks
    await benchmark.benchmark_database_operations(iterations=500)
    await benchmark.benchmark_cache_operations(iterations=5000)
    await benchmark.benchmark_concurrent_operations(workers=10, operations_per_worker=100)
    await benchmark.benchmark_memory_usage()
    
    # Print summary
    benchmark.print_summary()
    
    print("\n" + "=" * 60)
    print("Benchmark completed!")
    print("\nRecommendations:")
    print("- For high-frequency operations, consider sampling")
    print("- Use batch operations where possible")
    print("- Monitor memory usage in production")
    print("- Configure appropriate exporter batch sizes")


if __name__ == "__main__":
    asyncio.run(main())