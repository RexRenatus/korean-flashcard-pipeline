#!/usr/bin/env python3
"""
Cache Warmup Script

This script proactively warms the cache by processing high-priority terms.
It can run as a background service or be triggered manually.
"""

import asyncio
import sys
import os
import argparse
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.python.flashcard_pipeline.cache_v2 import ModernCacheService, CompressionType
from src.python.flashcard_pipeline.api_client import OpenRouterClient
from src.python.flashcard_pipeline.models import VocabularyItem
from src.python.flashcard_pipeline.database import DatabaseManager
from src.python.flashcard_pipeline.exceptions import ApiError, RateLimitError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CacheWarmupService:
    """Service for warming cache with high-priority terms"""
    
    def __init__(
        self,
        cache_service: ModernCacheService,
        api_client: OpenRouterClient,
        db_manager: DatabaseManager
    ):
        self.cache = cache_service
        self.api_client = api_client
        self.db_manager = db_manager
        self.stats = {
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "tokens_used": 0,
            "cost": 0
        }
    
    async def warmup_from_queue(self, limit: int = 10) -> Dict[str, Any]:
        """Process terms from the warmup queue"""
        candidates = await self.cache.get_warming_candidates(limit)
        
        if not candidates:
            logger.info("No candidates in warming queue")
            return self.stats
        
        logger.info(f"Processing {len(candidates)} warmup candidates")
        
        for candidate in candidates:
            await self._process_term(candidate["term"])
            
            # Mark as processed
            with self.db_manager.get_connection() as conn:
                conn.execute("""
                    UPDATE cache_warming_queue
                    SET processed = 1, processed_at = ?
                    WHERE term = ? AND processed = 0
                """, (datetime.now(), candidate["term"]))
        
        return self.stats
    
    async def warmup_from_vocabulary(self, limit: int = 20) -> Dict[str, Any]:
        """Warm cache with recently accessed vocabulary"""
        with self.db_manager.get_connection() as conn:
            # Get frequently accessed vocabulary
            cursor = conn.execute("""
                SELECT DISTINCT vm.korean, vm.type
                FROM vocabulary_master vm
                LEFT JOIN cache_metadata cm ON cm.term = vm.korean
                WHERE cm.cache_key IS NULL OR cm.accessed_at < datetime('now', '-7 days')
                ORDER BY vm.priority DESC, vm.id DESC
                LIMIT ?
            """, (limit,))
            
            terms = cursor.fetchall()
        
        if not terms:
            logger.info("No vocabulary items need warming")
            return self.stats
        
        logger.info(f"Warming cache for {len(terms)} vocabulary items")
        
        for row in terms:
            await self._process_term(row["korean"], row["type"])
        
        return self.stats
    
    async def warmup_from_file(self, filepath: str) -> Dict[str, Any]:
        """Warm cache from a file of terms"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            terms = [line.strip() for line in f if line.strip()]
        
        logger.info(f"Warming cache for {len(terms)} terms from {filepath}")
        
        for term in terms:
            await self._process_term(term)
        
        return self.stats
    
    async def _process_term(self, term: str, term_type: str = "word"):
        """Process a single term through both stages"""
        try:
            vocab_item = VocabularyItem(
                position=0,  # Temporary position
                term=term,
                type=term_type
            )
            
            # Check if already cached
            stage1_cached = await self.cache.get_stage1(vocab_item)
            
            if stage1_cached:
                logger.debug(f"Term '{term}' already in cache")
                self.stats["skipped"] += 1
                
                # Check if stage 2 is also cached
                stage1_response, _ = stage1_cached
                stage2_cached = await self.cache.get_stage2(vocab_item, stage1_response)
                
                if not stage2_cached:
                    # Process stage 2 only
                    await self._process_stage2(vocab_item, stage1_response)
                
                return
            
            # Process stage 1
            logger.info(f"Processing stage 1 for '{term}'")
            stage1_response, usage1 = await self.api_client.process_stage1(vocab_item)
            await self.cache.save_stage1(vocab_item, stage1_response, usage1.total_tokens)
            
            self.stats["tokens_used"] += usage1.total_tokens
            self.stats["cost"] += usage1.estimated_cost
            
            # Process stage 2
            await self._process_stage2(vocab_item, stage1_response)
            
            self.stats["processed"] += 1
            
        except RateLimitError as e:
            logger.warning(f"Rate limit hit: {e}. Waiting {e.retry_after}s")
            await asyncio.sleep(e.retry_after)
            # Retry
            await self._process_term(term, term_type)
            
        except Exception as e:
            logger.error(f"Error processing '{term}': {e}")
            self.stats["errors"] += 1
    
    async def _process_stage2(self, vocab_item: VocabularyItem, stage1_response):
        """Process stage 2 for a term"""
        try:
            logger.info(f"Processing stage 2 for '{vocab_item.term}'")
            stage2_response, usage2 = await self.api_client.process_stage2(
                vocab_item, stage1_response
            )
            await self.cache.save_stage2(
                vocab_item, stage1_response, stage2_response, usage2.total_tokens
            )
            
            self.stats["tokens_used"] += usage2.total_tokens
            self.stats["cost"] += usage2.estimated_cost
            
        except Exception as e:
            logger.error(f"Error in stage 2 for '{vocab_item.term}': {e}")
            self.stats["errors"] += 1
    
    async def run_continuous(self, interval_minutes: int = 30, batch_size: int = 10):
        """Run continuous warmup service"""
        logger.info(f"Starting continuous warmup (interval={interval_minutes}m, batch={batch_size})")
        
        while True:
            try:
                # Reset stats
                self.stats = {
                    "processed": 0,
                    "skipped": 0,
                    "errors": 0,
                    "tokens_used": 0,
                    "cost": 0
                }
                
                # Process from queue first
                await self.warmup_from_queue(batch_size)
                
                # Then process vocabulary items
                remaining = batch_size - self.stats["processed"]
                if remaining > 0:
                    await self.warmup_from_vocabulary(remaining)
                
                # Log results
                logger.info(
                    f"Warmup complete: processed={self.stats['processed']}, "
                    f"skipped={self.stats['skipped']}, errors={self.stats['errors']}, "
                    f"cost=${self.stats['cost']:.4f}"
                )
                
                # Wait for next interval
                await asyncio.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("Warmup service stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in warmup service: {e}")
                await asyncio.sleep(60)  # Wait a minute before retry


async def main():
    parser = argparse.ArgumentParser(
        description="Cache warmup utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Warm cache from queue
  python cache_warmup.py queue --limit 20

  # Warm cache from vocabulary
  python cache_warmup.py vocabulary --limit 50

  # Warm cache from file
  python cache_warmup.py file --path priority_terms.txt

  # Run continuous warmup service
  python cache_warmup.py continuous --interval 30 --batch 10
        """
    )
    
    parser.add_argument(
        "--cache-dir",
        default=".cache/flashcards_v2",
        help="Cache directory"
    )
    parser.add_argument(
        "--db",
        default="pipeline.db",
        help="Database path"
    )
    parser.add_argument(
        "--compression",
        choices=["none", "gzip", "zlib", "lz4"],
        default="lz4",
        help="Compression type"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Queue command
    queue_parser = subparsers.add_parser("queue", help="Warm from queue")
    queue_parser.add_argument("--limit", type=int, default=10, help="Number to process")
    
    # Vocabulary command
    vocab_parser = subparsers.add_parser("vocabulary", help="Warm from vocabulary")
    vocab_parser.add_argument("--limit", type=int, default=20, help="Number to process")
    
    # File command
    file_parser = subparsers.add_parser("file", help="Warm from file")
    file_parser.add_argument("--path", required=True, help="File containing terms")
    
    # Continuous command
    continuous_parser = subparsers.add_parser("continuous", help="Run continuous service")
    continuous_parser.add_argument("--interval", type=int, default=30, help="Interval in minutes")
    continuous_parser.add_argument("--batch", type=int, default=10, help="Batch size")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    # Initialize services
    compression = CompressionType[args.compression.upper()]
    cache_service = ModernCacheService(
        cache_dir=args.cache_dir,
        db_path=args.db,
        compression=compression
    )
    
    api_client = OpenRouterClient()
    db_manager = DatabaseManager(args.db)
    
    warmup_service = CacheWarmupService(cache_service, api_client, db_manager)
    
    # Execute command
    if args.command == "queue":
        stats = await warmup_service.warmup_from_queue(args.limit)
    elif args.command == "vocabulary":
        stats = await warmup_service.warmup_from_vocabulary(args.limit)
    elif args.command == "file":
        stats = await warmup_service.warmup_from_file(args.path)
    elif args.command == "continuous":
        await warmup_service.run_continuous(args.interval, args.batch)
        return
    
    # Display results
    print("\n=== Warmup Results ===")
    print(f"Processed: {stats['processed']}")
    print(f"Skipped (already cached): {stats['skipped']}")
    print(f"Errors: {stats['errors']}")
    print(f"Tokens used: {stats['tokens_used']:,}")
    print(f"Cost: ${stats['cost']:.4f}")


if __name__ == "__main__":
    asyncio.run(main())