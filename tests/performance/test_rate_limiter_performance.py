"""Performance tests for rate limiter implementations"""

import asyncio
import time
import statistics
import matplotlib.pyplot as plt
from typing import List, Dict, Any, Tuple
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import json
from pathlib import Path

from flashcard_pipeline.rate_limiter import RateLimiter
from flashcard_pipeline.rate_limiter_v2 import (
    ShardedRateLimiter,
    AdaptiveShardedRateLimiter,
    DistributedRateLimiter,
)


class RateLimiterBenchmark:
    """Benchmark suite for rate limiter performance"""
    
    def __init__(self, output_dir: str = "performance_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results = {}
    
    async def benchmark_throughput(self, name: str, limiter: Any, 
                                 requests: int = 10000,
                                 concurrent_users: int = 100) -> Dict[str, Any]:
        """Benchmark throughput with concurrent users"""
        print(f"\n=== Benchmarking {name} ===")
        print(f"Requests: {requests}, Concurrent users: {concurrent_users}")
        
        async def user_workload(user_id: str, request_count: int) -> Tuple[int, float]:
            """Simulate a user making requests"""
            success_count = 0
            start_time = time.time()
            
            for _ in range(request_count):
                try:
                    if hasattr(limiter, 'try_acquire'):
                        # New sharded limiter
                        result = await limiter.try_acquire(user_id)
                        if result.allowed:
                            success_count += 1
                    else:
                        # Old limiter
                        if limiter.try_acquire():
                            success_count += 1
                except:
                    pass
            
            duration = time.time() - start_time
            return success_count, duration
        
        # Create user workloads
        requests_per_user = requests // concurrent_users
        tasks = []
        
        start_time = time.time()
        
        for i in range(concurrent_users):
            user_id = f"user_{i}"
            task = user_workload(user_id, requests_per_user)
            tasks.append(task)
        
        # Run all users concurrently
        results = await asyncio.gather(*tasks)
        
        total_duration = time.time() - start_time
        
        # Calculate statistics
        total_success = sum(r[0] for r in results)
        user_durations = [r[1] for r in results]
        
        stats = {
            "name": name,
            "total_requests": requests,
            "successful_requests": total_success,
            "success_rate": total_success / requests,
            "total_duration": total_duration,
            "throughput": requests / total_duration,
            "successful_throughput": total_success / total_duration,
            "concurrent_users": concurrent_users,
            "avg_user_duration": statistics.mean(user_durations),
            "max_user_duration": max(user_durations),
            "min_user_duration": min(user_durations),
        }
        
        print(f"  Total duration: {total_duration:.2f}s")
        print(f"  Throughput: {stats['throughput']:.0f} req/s")
        print(f"  Success rate: {stats['success_rate']:.1%}")
        
        return stats
    
    async def benchmark_latency(self, name: str, limiter: Any,
                              samples: int = 1000) -> Dict[str, Any]:
        """Benchmark individual request latency"""
        print(f"\n=== Latency Benchmark for {name} ===")
        
        latencies = []
        
        for i in range(samples):
            user_id = f"user_{i % 10}"  # Rotate through 10 users
            
            start = time.perf_counter()
            
            try:
                if hasattr(limiter, 'try_acquire'):
                    await limiter.try_acquire(user_id)
                else:
                    limiter.try_acquire()
            except:
                pass
            
            end = time.perf_counter()
            latency_ms = (end - start) * 1000
            latencies.append(latency_ms)
        
        # Calculate percentiles
        latencies.sort()
        
        stats = {
            "name": name,
            "samples": samples,
            "mean_latency_ms": statistics.mean(latencies),
            "median_latency_ms": statistics.median(latencies),
            "p95_latency_ms": latencies[int(samples * 0.95)],
            "p99_latency_ms": latencies[int(samples * 0.99)],
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "stdev_latency_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0,
        }
        
        print(f"  Mean latency: {stats['mean_latency_ms']:.3f}ms")
        print(f"  P95 latency: {stats['p95_latency_ms']:.3f}ms")
        print(f"  P99 latency: {stats['p99_latency_ms']:.3f}ms")
        
        return stats
    
    async def benchmark_shard_distribution(self, limiter: ShardedRateLimiter,
                                         requests: int = 10000) -> Dict[str, Any]:
        """Benchmark shard distribution balance"""
        print(f"\n=== Shard Distribution Benchmark ===")
        
        # Reset limiter
        await limiter.reset()
        
        # Make requests with different keys
        for i in range(requests):
            user_id = f"user_{i}"
            await limiter.try_acquire(user_id)
        
        # Get shard balance
        balance = limiter.get_shard_balance()
        status = limiter.get_status()
        
        stats = {
            "name": "Shard Distribution",
            "total_requests": requests,
            "shard_count": limiter.shards,
            "distribution": balance["distribution"],
            "balanced": balance["balanced"],
            "imbalance_ratio": balance["imbalance_ratio"],
            "expected_per_shard": requests / limiter.shards,
        }
        
        print(f"  Shards: {limiter.shards}")
        print(f"  Distribution: {balance['distribution']}")
        print(f"  Balanced: {balance['balanced']}")
        print(f"  Imbalance ratio: {balance['imbalance_ratio']:.2f}")
        
        return stats
    
    async def benchmark_reservation_system(self, limiter: ShardedRateLimiter,
                                         batch_size: int = 100) -> Dict[str, Any]:
        """Benchmark reservation system performance"""
        print(f"\n=== Reservation System Benchmark ===")
        
        # Create many reservations
        start_time = time.time()
        reservations = []
        
        for i in range(batch_size):
            try:
                reservation = await limiter.reserve(
                    f"user_{i}",
                    count=1,
                    max_wait=60.0
                )
                reservations.append(reservation)
            except:
                pass
        
        creation_time = time.time() - start_time
        
        # Execute reservations
        execution_start = time.time()
        successful_executions = 0
        
        # Sort by execution time
        reservations.sort(key=lambda r: r.execute_at)
        
        for reservation in reservations:
            wait_time = reservation.execute_at - time.time()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            
            try:
                result = await limiter.execute_reservation(reservation.id)
                if result.allowed:
                    successful_executions += 1
            except:
                pass
        
        execution_time = time.time() - execution_start
        
        stats = {
            "name": "Reservation System",
            "batch_size": batch_size,
            "reservations_created": len(reservations),
            "successful_executions": successful_executions,
            "creation_time": creation_time,
            "execution_time": execution_time,
            "avg_creation_time_ms": (creation_time / batch_size) * 1000,
            "throughput": batch_size / (creation_time + execution_time),
        }
        
        print(f"  Reservations created: {len(reservations)}")
        print(f"  Creation time: {creation_time:.3f}s")
        print(f"  Execution time: {execution_time:.3f}s")
        print(f"  Avg creation time: {stats['avg_creation_time_ms']:.3f}ms")
        
        return stats
    
    async def benchmark_scaling(self, base_rate: int = 1000) -> Dict[str, Any]:
        """Benchmark how performance scales with shard count"""
        print(f"\n=== Scaling Benchmark ===")
        
        shard_counts = [1, 2, 4, 8, 16, 32]
        results = []
        
        for shards in shard_counts:
            limiter = ShardedRateLimiter(
                rate=base_rate,
                period=60.0,
                shards=shards
            )
            
            # Run throughput test
            stats = await self.benchmark_throughput(
                f"ShardedRateLimiter ({shards} shards)",
                limiter,
                requests=5000,
                concurrent_users=50
            )
            
            results.append({
                "shards": shards,
                "throughput": stats["throughput"],
                "success_rate": stats["success_rate"],
            })
        
        return {
            "name": "Scaling Analysis",
            "base_rate": base_rate,
            "results": results,
        }
    
    def generate_report(self):
        """Generate performance report with visualizations"""
        report_path = self.output_dir / "performance_report.json"
        
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nPerformance report saved to: {report_path}")
        
        # Generate visualizations if matplotlib is available
        try:
            self._generate_charts()
        except ImportError:
            print("Install matplotlib for performance charts")
    
    def _generate_charts(self):
        """Generate performance charts"""
        # Throughput comparison chart
        if "throughput_comparison" in self.results:
            self._plot_throughput_comparison()
        
        # Latency comparison chart
        if "latency_comparison" in self.results:
            self._plot_latency_comparison()
        
        # Scaling chart
        if "scaling_analysis" in self.results:
            self._plot_scaling_analysis()
    
    def _plot_throughput_comparison(self):
        """Plot throughput comparison"""
        data = self.results["throughput_comparison"]
        
        names = [d["name"] for d in data]
        throughputs = [d["throughput"] for d in data]
        
        plt.figure(figsize=(10, 6))
        plt.bar(names, throughputs)
        plt.xlabel("Rate Limiter Type")
        plt.ylabel("Throughput (requests/second)")
        plt.title("Rate Limiter Throughput Comparison")
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        chart_path = self.output_dir / "throughput_comparison.png"
        plt.savefig(chart_path)
        plt.close()
        
        print(f"Throughput chart saved to: {chart_path}")
    
    def _plot_latency_comparison(self):
        """Plot latency comparison"""
        data = self.results["latency_comparison"]
        
        names = [d["name"] for d in data]
        p95_latencies = [d["p95_latency_ms"] for d in data]
        p99_latencies = [d["p99_latency_ms"] for d in data]
        
        x = np.arange(len(names))
        width = 0.35
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(x - width/2, p95_latencies, width, label='P95')
        ax.bar(x + width/2, p99_latencies, width, label='P99')
        
        ax.set_xlabel("Rate Limiter Type")
        ax.set_ylabel("Latency (ms)")
        ax.set_title("Rate Limiter Latency Comparison")
        ax.set_xticks(x)
        ax.set_xticklabels(names, rotation=45, ha='right')
        ax.legend()
        
        plt.tight_layout()
        
        chart_path = self.output_dir / "latency_comparison.png"
        plt.savefig(chart_path)
        plt.close()
        
        print(f"Latency chart saved to: {chart_path}")
    
    def _plot_scaling_analysis(self):
        """Plot scaling analysis"""
        data = self.results["scaling_analysis"]["results"]
        
        shards = [d["shards"] for d in data]
        throughputs = [d["throughput"] for d in data]
        
        plt.figure(figsize=(10, 6))
        plt.plot(shards, throughputs, marker='o', linewidth=2, markersize=8)
        plt.xlabel("Number of Shards")
        plt.ylabel("Throughput (requests/second)")
        plt.title("Rate Limiter Scaling with Shard Count")
        plt.grid(True, alpha=0.3)
        plt.xscale('log', base=2)
        
        plt.tight_layout()
        
        chart_path = self.output_dir / "scaling_analysis.png"
        plt.savefig(chart_path)
        plt.close()
        
        print(f"Scaling chart saved to: {chart_path}")


async def run_performance_tests():
    """Run all performance tests"""
    benchmark = RateLimiterBenchmark()
    
    # Create test instances
    old_limiter = RateLimiter(
        requests_per_minute=6000,  # 100 req/s
        burst_size=100
    )
    
    sharded_limiter_1 = ShardedRateLimiter(
        rate=6000,
        period=60.0,
        shards=1,
        burst_size=100
    )
    
    sharded_limiter_8 = ShardedRateLimiter(
        rate=6000,
        period=60.0,
        shards=8,
        burst_size=100
    )
    
    sharded_limiter_16 = ShardedRateLimiter(
        rate=6000,
        period=60.0,
        shards=16,
        burst_size=100
    )
    
    adaptive_limiter = AdaptiveShardedRateLimiter(
        rate=6000,
        initial_shards=8,
        rebalance_threshold=0.3
    )
    
    # 1. Throughput comparison
    print("\n" + "="*60)
    print("THROUGHPUT COMPARISON")
    print("="*60)
    
    throughput_results = []
    
    for name, limiter in [
        ("Original RateLimiter", old_limiter),
        ("ShardedRateLimiter (1 shard)", sharded_limiter_1),
        ("ShardedRateLimiter (8 shards)", sharded_limiter_8),
        ("ShardedRateLimiter (16 shards)", sharded_limiter_16),
        ("AdaptiveShardedRateLimiter", adaptive_limiter),
    ]:
        result = await benchmark.benchmark_throughput(
            name, limiter,
            requests=10000,
            concurrent_users=100
        )
        throughput_results.append(result)
    
    benchmark.results["throughput_comparison"] = throughput_results
    
    # 2. Latency comparison
    print("\n" + "="*60)
    print("LATENCY COMPARISON")
    print("="*60)
    
    latency_results = []
    
    for name, limiter in [
        ("Original RateLimiter", old_limiter),
        ("ShardedRateLimiter (1 shard)", sharded_limiter_1),
        ("ShardedRateLimiter (8 shards)", sharded_limiter_8),
        ("ShardedRateLimiter (16 shards)", sharded_limiter_16),
    ]:
        result = await benchmark.benchmark_latency(name, limiter)
        latency_results.append(result)
    
    benchmark.results["latency_comparison"] = latency_results
    
    # 3. Shard distribution test
    print("\n" + "="*60)
    print("SHARD DISTRIBUTION TEST")
    print("="*60)
    
    distribution_result = await benchmark.benchmark_shard_distribution(
        sharded_limiter_16,
        requests=10000
    )
    benchmark.results["shard_distribution"] = distribution_result
    
    # 4. Reservation system test
    print("\n" + "="*60)
    print("RESERVATION SYSTEM TEST")
    print("="*60)
    
    reservation_limiter = ShardedRateLimiter(
        rate=60,  # 1 per second for testing
        period=60.0,
        shards=4
    )
    
    reservation_result = await benchmark.benchmark_reservation_system(
        reservation_limiter,
        batch_size=50
    )
    benchmark.results["reservation_system"] = reservation_result
    
    # 5. Scaling analysis
    print("\n" + "="*60)
    print("SCALING ANALYSIS")
    print("="*60)
    
    scaling_result = await benchmark.benchmark_scaling(base_rate=6000)
    benchmark.results["scaling_analysis"] = scaling_result
    
    # Generate report
    benchmark.generate_report()
    
    # Print summary
    print("\n" + "="*60)
    print("PERFORMANCE TEST SUMMARY")
    print("="*60)
    
    # Find best performer
    best_throughput = max(throughput_results, key=lambda x: x["throughput"])
    print(f"\nBest throughput: {best_throughput['name']}")
    print(f"  {best_throughput['throughput']:.0f} requests/second")
    
    best_latency = min(latency_results, key=lambda x: x["p99_latency_ms"])
    print(f"\nBest latency: {best_latency['name']}")
    print(f"  P99: {best_latency['p99_latency_ms']:.3f}ms")
    
    # Calculate improvement
    original_throughput = next(r for r in throughput_results if "Original" in r["name"])
    sharded_16_throughput = next(r for r in throughput_results if "16 shards" in r["name"])
    
    improvement = (sharded_16_throughput["throughput"] / original_throughput["throughput"] - 1) * 100
    print(f"\nPerformance improvement with 16 shards: {improvement:.1f}%")


def run_stress_test():
    """Run stress test to find limits"""
    async def stress_test():
        print("\n" + "="*60)
        print("STRESS TEST - Finding Limits")
        print("="*60)
        
        limiter = ShardedRateLimiter(
            rate=10000,  # High rate
            period=60.0,
            shards=16
        )
        
        concurrent_levels = [10, 50, 100, 200, 500, 1000]
        
        for concurrent in concurrent_levels:
            print(f"\nTesting with {concurrent} concurrent users...")
            
            async def user_load(user_id: str):
                count = 0
                start = time.time()
                
                while time.time() - start < 5.0:  # 5 second test
                    result = await limiter.try_acquire(user_id)
                    if result.allowed:
                        count += 1
                    await asyncio.sleep(0.001)  # Small delay
                
                return count
            
            tasks = [user_load(f"user_{i}") for i in range(concurrent)]
            
            start_time = time.time()
            results = await asyncio.gather(*tasks)
            duration = time.time() - start_time
            
            total_requests = sum(results)
            throughput = total_requests / duration
            
            print(f"  Total requests: {total_requests}")
            print(f"  Throughput: {throughput:.0f} req/s")
            print(f"  Per user avg: {total_requests / concurrent:.1f} requests")
    
    asyncio.run(stress_test())


if __name__ == "__main__":
    # Run main performance tests
    asyncio.run(run_performance_tests())
    
    # Run stress test
    run_stress_test()