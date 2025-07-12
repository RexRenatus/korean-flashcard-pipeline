#!/usr/bin/env python3
"""
Cache Maintenance Script

This script provides cache maintenance operations:
- Analyze cache performance
- Clean expired entries
- Manage cache size
- Warm cache with priority terms
- Generate cache reports
"""

import argparse
import asyncio
import sys
import os
from datetime import datetime, timedelta
from tabulate import tabulate
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.python.flashcard_pipeline.cache_v2 import ModernCacheService, CompressionType


async def analyze_cache(cache_service: ModernCacheService):
    """Analyze cache performance and display results"""
    print("\n=== Cache Performance Analysis ===\n")
    
    analysis = await cache_service.analyze_cache_performance()
    stats = analysis["stats"]
    
    # Display basic stats
    basic_stats = [
        ["Total Entries", f"{stats['total_entries']:,}"],
        ["Total Size", f"{stats['total_size_mb']:.2f} MB"],
        ["Stage 1 Entries", f"{stats['stage1_entries']:,}"],
        ["Stage 2 Entries", f"{stats['stage2_entries']:,}"],
        ["Hot Entries", f"{stats['hot_entries']:,}"],
        ["Compression Type", stats['compression_type']],
        ["Average Compression", f"{stats['avg_compression_ratio']:.2%}"],
        ["TTL", f"{stats['ttl_hours']} hours"],
    ]
    
    print("Basic Statistics:")
    print(tabulate(basic_stats, headers=["Metric", "Value"], tablefmt="simple"))
    
    # Display hit rates
    if "stage1_hit_rate" in stats:
        print("\nCache Hit Rates:")
        hit_stats = [
            ["Stage 1", f"{stats.get('stage1_hit_rate', 0):.1%}"],
            ["Stage 2", f"{stats.get('stage2_hit_rate', 0):.1%}"],
        ]
        print(tabulate(hit_stats, headers=["Stage", "Hit Rate"], tablefmt="simple"))
    
    # Display token savings
    if stats.get('total_tokens_saved', 0) > 0:
        print("\nToken Savings:")
        token_stats = [
            ["Tokens Saved", f"{stats['total_tokens_saved']:,}"],
            ["Estimated Cost Saved", f"${stats.get('estimated_cost_saved', 0):.2f}"],
        ]
        print(tabulate(token_stats, headers=["Metric", "Value"], tablefmt="simple"))
    
    # Display health score
    print(f"\nOverall Health Score: {analysis['health_score']:.1f}/100")
    
    # Display recommendations
    if analysis['recommendations']:
        print("\nRecommendations:")
        for i, rec in enumerate(analysis['recommendations'], 1):
            print(f"  {i}. {rec}")
    else:
        print("\nNo recommendations - cache is performing well!")


async def clean_expired(cache_service: ModernCacheService):
    """Clean expired cache entries"""
    print("\n=== Cleaning Expired Entries ===\n")
    
    # Get initial stats
    initial_stats = cache_service.get_stats()
    initial_count = initial_stats['total_entries']
    initial_size = initial_stats['total_size_mb']
    
    # Clean expired entries
    removed = await cache_service.invalidate_expired()
    
    # Get final stats
    final_stats = cache_service.get_stats()
    final_count = final_stats['total_entries']
    final_size = final_stats['total_size_mb']
    
    print(f"Removed {removed} expired entries")
    print(f"Freed {initial_size - final_size:.2f} MB")
    print(f"Remaining entries: {final_count:,}")


async def manage_size(cache_service: ModernCacheService, target_mb: int):
    """Manage cache size by evicting least recently used entries"""
    print(f"\n=== Managing Cache Size (Target: {target_mb} MB) ===\n")
    
    # Get initial stats
    initial_stats = cache_service.get_stats()
    initial_size = initial_stats['total_size_mb']
    
    if initial_size <= target_mb:
        print(f"Cache size ({initial_size:.2f} MB) is already below target")
        return
    
    # Evict entries
    removed = await cache_service.invalidate_by_size(target_mb)
    
    # Get final stats
    final_stats = cache_service.get_stats()
    final_size = final_stats['total_size_mb']
    
    print(f"Removed {removed} entries")
    print(f"Size reduced from {initial_size:.2f} MB to {final_size:.2f} MB")


async def warm_cache(cache_service: ModernCacheService, terms_file: str, priority: int):
    """Add terms to cache warming queue"""
    print(f"\n=== Warming Cache from {terms_file} ===\n")
    
    if not os.path.exists(terms_file):
        print(f"Error: File '{terms_file}' not found")
        return
    
    # Read terms
    with open(terms_file, 'r', encoding='utf-8') as f:
        terms = [line.strip() for line in f if line.strip()]
    
    print(f"Found {len(terms)} terms to warm")
    
    # Add to warming queue
    results = await cache_service.warm_cache(terms, priority)
    
    print(f"Newly queued: {results['queued']}")
    print(f"Already queued (priority boosted): {results['already_queued']}")
    
    # Show top candidates
    candidates = await cache_service.get_warming_candidates(5)
    if candidates:
        print("\nTop warming candidates:")
        cand_data = [[c['term'], c['priority']] for c in candidates]
        print(tabulate(cand_data, headers=["Term", "Priority"], tablefmt="simple"))


async def show_warming_queue(cache_service: ModernCacheService, limit: int):
    """Display cache warming queue"""
    print(f"\n=== Cache Warming Queue (Top {limit}) ===\n")
    
    candidates = await cache_service.get_warming_candidates(limit)
    
    if not candidates:
        print("No items in warming queue")
        return
    
    # Display candidates
    data = []
    for i, cand in enumerate(candidates, 1):
        data.append([i, cand['term'], cand['priority']])
    
    print(tabulate(data, headers=["#", "Term", "Priority"], tablefmt="grid"))


async def generate_report(cache_service: ModernCacheService, output_file: str):
    """Generate comprehensive cache report"""
    print(f"\n=== Generating Cache Report ===\n")
    
    # Gather all data
    analysis = await cache_service.analyze_cache_performance()
    stats = cache_service.get_stats()
    
    # Get cache metadata samples
    with cache_service.db_manager.get_connection() as conn:
        # Most accessed entries
        most_accessed = conn.execute("""
            SELECT term, access_count, is_hot, tokens_saved
            FROM cache_metadata
            ORDER BY access_count DESC
            LIMIT 20
        """).fetchall()
        
        # Recently accessed
        recent = conn.execute("""
            SELECT term, accessed_at, stage
            FROM cache_metadata
            ORDER BY accessed_at DESC
            LIMIT 20
        """).fetchall()
        
        # Largest entries
        largest = conn.execute("""
            SELECT term, size_bytes, compression_ratio
            FROM cache_metadata
            ORDER BY size_bytes DESC
            LIMIT 20
        """).fetchall()
    
    # Build report
    report = {
        "generated_at": datetime.now().isoformat(),
        "stats": stats,
        "analysis": analysis,
        "most_accessed": [
            {
                "term": row[0],
                "access_count": row[1],
                "is_hot": bool(row[2]),
                "tokens_saved": row[3]
            }
            for row in most_accessed
        ],
        "recently_accessed": [
            {
                "term": row[0],
                "accessed_at": row[1],
                "stage": row[2]
            }
            for row in recent
        ],
        "largest_entries": [
            {
                "term": row[0],
                "size_bytes": row[1],
                "compression_ratio": row[2]
            }
            for row in largest
        ]
    }
    
    # Write report
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"Report saved to: {output_file}")
    print(f"Total entries analyzed: {stats['total_entries']:,}")


async def clear_cache(cache_service: ModernCacheService, stage: int = None):
    """Clear cache entries"""
    if stage:
        print(f"\n=== Clearing Stage {stage} Cache ===\n")
    else:
        print("\n=== Clearing All Cache ===\n")
    
    # Get initial stats
    initial_stats = cache_service.get_stats()
    
    # Clear cache
    removed = await cache_service.clear_cache(stage)
    
    print(f"Removed {removed} cache entries")
    
    # Show remaining stats
    if stage:
        final_stats = cache_service.get_stats()
        print(f"Remaining entries: {final_stats['total_entries']:,}")


async def main():
    parser = argparse.ArgumentParser(
        description="Cache maintenance utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze cache performance
  python cache_maintenance.py analyze

  # Clean expired entries
  python cache_maintenance.py clean

  # Manage cache size
  python cache_maintenance.py size --target 500

  # Warm cache with terms
  python cache_maintenance.py warm --file terms.txt --priority 10

  # Show warming queue
  python cache_maintenance.py queue --limit 20

  # Generate report
  python cache_maintenance.py report --output cache_report.json

  # Clear cache
  python cache_maintenance.py clear --stage 1
        """
    )
    
    parser.add_argument(
        "--cache-dir",
        default=".cache/flashcards_v2",
        help="Cache directory (default: .cache/flashcards_v2)"
    )
    parser.add_argument(
        "--db",
        default="pipeline.db",
        help="Database path (default: pipeline.db)"
    )
    parser.add_argument(
        "--compression",
        choices=["none", "gzip", "zlib", "lz4"],
        default="lz4",
        help="Compression type (default: lz4)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze cache performance")
    
    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Clean expired entries")
    
    # Size management command
    size_parser = subparsers.add_parser("size", help="Manage cache size")
    size_parser.add_argument("--target", type=int, required=True, help="Target size in MB")
    
    # Warm cache command
    warm_parser = subparsers.add_parser("warm", help="Warm cache with terms")
    warm_parser.add_argument("--file", required=True, help="File containing terms")
    warm_parser.add_argument("--priority", type=int, default=10, help="Priority boost")
    
    # Show queue command
    queue_parser = subparsers.add_parser("queue", help="Show warming queue")
    queue_parser.add_argument("--limit", type=int, default=10, help="Number to show")
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate cache report")
    report_parser.add_argument("--output", default="cache_report.json", help="Output file")
    
    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Clear cache")
    clear_parser.add_argument("--stage", type=int, choices=[1, 2], help="Stage to clear")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize cache service
    compression = CompressionType[args.compression.upper()]
    cache_service = ModernCacheService(
        cache_dir=args.cache_dir,
        db_path=args.db,
        compression=compression
    )
    
    # Execute command
    if args.command == "analyze":
        await analyze_cache(cache_service)
    elif args.command == "clean":
        await clean_expired(cache_service)
    elif args.command == "size":
        await manage_size(cache_service, args.target)
    elif args.command == "warm":
        await warm_cache(cache_service, args.file, args.priority)
    elif args.command == "queue":
        await show_warming_queue(cache_service, args.limit)
    elif args.command == "report":
        await generate_report(cache_service, args.output)
    elif args.command == "clear":
        await clear_cache(cache_service, args.stage)


if __name__ == "__main__":
    asyncio.run(main())