#!/usr/bin/env python3
"""
Unified Cache Management Tool
Combines functionality from cache_maintenance.py and cache_warmup.py
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import asyncio
from tabulate import tabulate

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.python.flashcard_pipeline.cache import CacheService
from src.python.flashcard_pipeline.database import DatabaseManager
from src.python.flashcard_pipeline.utils import setup_logging, get_logger, format_file_size

logger = get_logger(__name__)


class CacheManager:
    """Comprehensive cache management utility"""
    
    def __init__(self, cache_dir: str = None):
        self.cache_service = CacheService(
            cache_dir=cache_dir or "cache",
            mode="advanced"  # Use advanced mode for all features
        )
        self.db_manager = DatabaseManager()
    
    def analyze(self) -> Dict[str, Any]:
        """Analyze cache contents and statistics"""
        logger.info("Analyzing cache...")
        
        stats = self.cache_service.get_statistics()
        
        # Add detailed analysis
        analysis = {
            "overview": {
                "total_items": stats["total_items"],
                "total_size": stats["total_size"],
                "total_size_formatted": format_file_size(stats["total_size"]),
                "cache_directory": str(self.cache_service.cache_dir)
            },
            "breakdown": {
                "stage1_items": stats["stage1_items"],
                "stage1_size": stats["stage1_size"],
                "stage1_size_formatted": format_file_size(stats["stage1_size"]),
                "stage2_items": stats["stage2_items"], 
                "stage2_size": stats["stage2_size"],
                "stage2_size_formatted": format_file_size(stats["stage2_size"])
            },
            "efficiency": self._calculate_efficiency_metrics(stats),
            "recommendations": self._generate_recommendations(stats)
        }
        
        return analysis
    
    def clean(self, days_old: int = 30, dry_run: bool = False) -> Dict[str, Any]:
        """Clean old cache entries"""
        logger.info(f"Cleaning cache entries older than {days_old} days...")
        
        if dry_run:
            logger.info("DRY RUN - No files will be deleted")
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        cleaned = {
            "files_removed": 0,
            "space_freed": 0,
            "errors": []
        }
        
        # Scan cache directory
        for stage_dir in ["stage1", "stage2"]:
            stage_path = self.cache_service.cache_dir / stage_dir
            if not stage_path.exists():
                continue
            
            for cache_file in stage_path.glob("*.json*"):
                try:
                    # Check file age
                    mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                    if mtime < cutoff_date:
                        file_size = cache_file.stat().st_size
                        
                        if not dry_run:
                            cache_file.unlink()
                            # Also remove from in-memory cache
                            cache_key = cache_file.stem
                            self.cache_service._remove_from_memory(cache_key)
                        
                        cleaned["files_removed"] += 1
                        cleaned["space_freed"] += file_size
                        
                except Exception as e:
                    cleaned["errors"].append(f"Error processing {cache_file}: {e}")
        
        cleaned["space_freed_formatted"] = format_file_size(cleaned["space_freed"])
        
        return cleaned
    
    def warm(self, priority_terms: Optional[List[str]] = None, limit: int = 100) -> Dict[str, Any]:
        """Warm cache with priority terms"""
        logger.info("Warming cache with priority terms...")
        
        warmed = {
            "terms_processed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": []
        }
        
        # Get priority terms if not provided
        if not priority_terms:
            priority_terms = self._get_priority_terms(limit)
        
        # Check cache for each term
        for term in priority_terms:
            try:
                # Check if already cached
                stage1_cached = self.cache_service.get(
                    self._make_cache_key(term, 1)
                )
                stage2_cached = self.cache_service.get(
                    self._make_cache_key(term, 2)
                )
                
                if stage1_cached and stage2_cached:
                    warmed["cache_hits"] += 1
                else:
                    warmed["cache_misses"] += 1
                    # In a real implementation, we would trigger processing here
                    logger.debug(f"Term '{term}' not fully cached")
                
                warmed["terms_processed"] += 1
                
            except Exception as e:
                warmed["errors"].append(f"Error processing '{term}': {e}")
        
        return warmed
    
    def report(self, format: str = "table") -> None:
        """Generate comprehensive cache report"""
        analysis = self.analyze()
        
        if format == "json":
            print(json.dumps(analysis, indent=2))
            return
        
        # Print header
        print("\n" + "="*60)
        print("CACHE ANALYSIS REPORT")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
        
        # Overview section
        print("OVERVIEW:")
        print("-" * 40)
        overview_data = [
            ["Total Items", analysis["overview"]["total_items"]],
            ["Total Size", analysis["overview"]["total_size_formatted"]],
            ["Cache Directory", analysis["overview"]["cache_directory"]]
        ]
        print(tabulate(overview_data, tablefmt="simple"))
        
        # Breakdown section
        print("\n\nBREAKDOWN BY STAGE:")
        print("-" * 40)
        breakdown_data = [
            ["Stage", "Items", "Size"],
            ["Stage 1", analysis["breakdown"]["stage1_items"], 
             analysis["breakdown"]["stage1_size_formatted"]],
            ["Stage 2", analysis["breakdown"]["stage2_items"],
             analysis["breakdown"]["stage2_size_formatted"]]
        ]
        print(tabulate(breakdown_data, headers="firstrow", tablefmt="grid"))
        
        # Efficiency metrics
        print("\n\nEFFICIENCY METRICS:")
        print("-" * 40)
        efficiency_data = []
        for metric, value in analysis["efficiency"].items():
            efficiency_data.append([metric.replace("_", " ").title(), value])
        print(tabulate(efficiency_data, tablefmt="simple"))
        
        # Recommendations
        if analysis["recommendations"]:
            print("\n\nRECOMMENDATIONS:")
            print("-" * 40)
            for i, rec in enumerate(analysis["recommendations"], 1):
                print(f"{i}. {rec}")
    
    def _calculate_efficiency_metrics(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate cache efficiency metrics"""
        metrics = {}
        
        if stats["total_items"] > 0:
            metrics["average_item_size"] = format_file_size(
                stats["total_size"] / stats["total_items"]
            )
        else:
            metrics["average_item_size"] = "N/A"
        
        # Get hit rate if available
        if hasattr(self.cache_service, "_get_hit_rate"):
            metrics["hit_rate"] = f"{self.cache_service._get_hit_rate():.1%}"
        
        # Memory vs disk usage
        memory_stats = self.cache_service._memory_cache.get_stats() if hasattr(
            self.cache_service._memory_cache, "get_stats"
        ) else {}
        
        if memory_stats:
            metrics["memory_usage"] = format_file_size(memory_stats.get("size", 0))
            metrics["memory_items"] = memory_stats.get("items", 0)
        
        return metrics
    
    def _generate_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Generate cache optimization recommendations"""
        recommendations = []
        
        # Check if cache is too large
        if stats["total_size"] > 1024 * 1024 * 1024:  # 1GB
            recommendations.append(
                f"Cache size ({format_file_size(stats['total_size'])}) exceeds 1GB. "
                "Consider cleaning old entries."
            )
        
        # Check stage imbalance
        if stats["stage1_items"] > 0 and stats["stage2_items"] > 0:
            ratio = stats["stage1_items"] / stats["stage2_items"]
            if ratio > 2:
                recommendations.append(
                    f"Stage 1 has {ratio:.1f}x more items than Stage 2. "
                    "Some items may have failed Stage 2 processing."
                )
        
        # Check for empty cache
        if stats["total_items"] == 0:
            recommendations.append(
                "Cache is empty. Consider warming cache with frequently used terms."
            )
        
        return recommendations
    
    def _get_priority_terms(self, limit: int) -> List[str]:
        """Get priority terms from database"""
        terms = []
        
        try:
            with self.db_manager.get_connection() as conn:
                # Get most recently added terms that aren't cached
                cursor = conn.execute("""
                    SELECT DISTINCT term 
                    FROM vocabulary 
                    WHERE is_active = 1
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
                
                terms = [row[0] for row in cursor]
        except Exception as e:
            logger.error(f"Failed to get priority terms: {e}")
        
        return terms
    
    def _make_cache_key(self, term: str, stage: int) -> str:
        """Create cache key for term and stage"""
        # This should match the key format used by the pipeline
        return f"stage{stage}_{term}"


def main():
    parser = argparse.ArgumentParser(
        description="Cache Management Tool - Analyze, clean, warm, and optimize cache"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze cache contents")
    analyze_parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format"
    )
    
    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Clean old cache entries")
    clean_parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Remove entries older than N days (default: 30)"
    )
    clean_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without deleting"
    )
    
    # Warm command
    warm_parser = subparsers.add_parser("warm", help="Warm cache with priority terms")
    warm_parser.add_argument(
        "--terms",
        nargs="+",
        help="Specific terms to warm (otherwise uses recent terms)"
    )
    warm_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Number of terms to process (default: 100)"
    )
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate cache report")
    report_parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format"
    )
    
    # Global options
    parser.add_argument(
        "--cache-dir",
        help="Cache directory path"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Setup logging
    setup_logging(verbose=args.verbose)
    
    # Create cache manager
    manager = CacheManager(cache_dir=args.cache_dir)
    
    try:
        if args.command == "analyze":
            analysis = manager.analyze()
            if args.format == "json":
                print(json.dumps(analysis, indent=2))
            else:
                manager.report(format="table")
        
        elif args.command == "clean":
            result = manager.clean(days_old=args.days, dry_run=args.dry_run)
            print(f"\nCache cleanup {'(DRY RUN)' if args.dry_run else ''} complete:")
            print(f"Files removed: {result['files_removed']}")
            print(f"Space freed: {result['space_freed_formatted']}")
            if result['errors']:
                print(f"Errors: {len(result['errors'])}")
        
        elif args.command == "warm":
            result = manager.warm(priority_terms=args.terms, limit=args.limit)
            print(f"\nCache warming complete:")
            print(f"Terms processed: {result['terms_processed']}")
            print(f"Cache hits: {result['cache_hits']}")
            print(f"Cache misses: {result['cache_misses']}")
            if result['errors']:
                print(f"Errors: {len(result['errors'])}")
        
        elif args.command == "report":
            manager.report(format=args.format)
        
        return 0
        
    except Exception as e:
        logger.error(f"Command failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())