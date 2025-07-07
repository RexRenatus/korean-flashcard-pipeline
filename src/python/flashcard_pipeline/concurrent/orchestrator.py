"""Concurrent pipeline orchestrator for batch processing"""

import asyncio
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import logging

from ..models import VocabularyItem, Stage1Response, Stage2Response
from ..api_client import OpenRouterClient
from ..cache import CacheService
from ..circuit_breaker import CircuitBreaker
from ..exceptions import PipelineError, ApiError, RateLimitError
from .ordered_collector import OrderedResultsCollector, ProcessingResult
from .distributed_rate_limiter import DistributedRateLimiter
from .progress_tracker import ConcurrentProgressTracker

logger = logging.getLogger(__name__)


class ConcurrentPipelineOrchestrator:
    """Orchestrates concurrent processing of vocabulary items"""
    
    def __init__(self, 
                 max_concurrent: int = 50,
                 api_client: Optional[OpenRouterClient] = None,
                 cache_service: Optional[CacheService] = None,
                 rate_limit_rpm: int = 600):
        """Initialize orchestrator
        
        Args:
            max_concurrent: Maximum concurrent processing tasks
            api_client: OpenRouter API client
            cache_service: Cache service instance
            rate_limit_rpm: API rate limit (requests per minute)
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Initialize components
        self.rate_limiter = DistributedRateLimiter(
            requests_per_minute=rate_limit_rpm,
            buffer_factor=0.8
        )
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=10,
            recovery_timeout=60
        )
        self.results_collector = OrderedResultsCollector()
        self.progress_tracker = ConcurrentProgressTracker(0)
        
        # Services
        self.api_client = api_client
        self.cache_service = cache_service
        
        # Statistics
        self.stats = {
            "batches_processed": 0,
            "total_items": 0,
            "total_successful": 0,
            "total_failed": 0,
            "total_from_cache": 0
        }
        
        logger.info(f"Concurrent orchestrator initialized (max: {max_concurrent})")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.rate_limiter.start()
        
        # Initialize API client if not provided
        if not self.api_client:
            self.api_client = OpenRouterClient()
            await self.api_client.__aenter__()
            
        # Initialize cache service if not provided
        if not self.cache_service:
            self.cache_service = CacheService()
            
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.rate_limiter.stop()
        
        # Clean up API client if we created it
        if hasattr(self, '_created_client') and self.api_client:
            await self.api_client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def process_batch(self, items: List[VocabularyItem]) -> List[ProcessingResult]:
        """Process items concurrently while maintaining order
        
        Args:
            items: List of vocabulary items to process
            
        Returns:
            List of processing results in order
        """
        start_time = asyncio.get_event_loop().time()
        
        # Reset components for new batch
        self.results_collector.clear()
        self.results_collector.set_expected_count(len(items))
        self.progress_tracker.reset(len(items))
        
        logger.info(f"Starting concurrent batch processing of {len(items)} items")
        
        # Pre-warm cache
        cache_stats = await self.cache_service.warm_cache_from_batch(items)
        logger.info(f"Cache pre-check: {cache_stats['stage1_cached']}/{len(items)} cached")
        
        # Create processing tasks
        tasks = []
        for item in items:
            task = self._create_processing_task(item)
            tasks.append(task)
        
        # Execute concurrently with error handling
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Task failed for item {items[i].position}: {result}")
                await self.results_collector.add_result(
                    items[i].position,
                    ProcessingResult(
                        position=items[i].position,
                        term=items[i].term,
                        error=str(result)
                    )
                )
        
        # Wait for all results to be collected
        await self.results_collector.wait_for_all(timeout=300.0)
        
        # Get ordered results
        ordered_results = self.results_collector.get_ordered_results()
        
        # Update statistics
        batch_stats = self.results_collector.get_statistics()
        self.stats["batches_processed"] += 1
        self.stats["total_items"] += len(items)
        self.stats["total_successful"] += batch_stats["successful"]
        self.stats["total_failed"] += batch_stats["failed"]
        self.stats["total_from_cache"] += batch_stats["from_cache"]
        
        # Log summary
        elapsed = (asyncio.get_event_loop().time() - start_time) * 1000
        logger.info(
            f"Batch processing complete: "
            f"{batch_stats['successful']}/{len(items)} successful, "
            f"{batch_stats['failed']} failed, "
            f"{batch_stats['cache_hit_rate']:.1f}% cache hits, "
            f"{elapsed:.0f}ms total"
        )
        
        return ordered_results
    
    async def _create_processing_task(self, item: VocabularyItem):
        """Create a processing task with proper error handling"""
        async with self.semaphore:
            return await self._process_single_item(item)
    
    async def _process_single_item(self, item: VocabularyItem):
        """Process a single item with all safety checks"""
        start_time = asyncio.get_event_loop().time()
        
        await self.progress_tracker.start_item(item.position)
        
        try:
            # Rate limiting
            await self.rate_limiter.acquire(timeout=30.0)
            
            # Check cache first
            cached_result = await self._check_cache(item)
            if cached_result:
                processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
                cached_result.processing_time_ms = processing_time
                
                await self.results_collector.add_result(item.position, cached_result)
                await self.progress_tracker.complete_item(
                    item.position, True, from_cache=True
                )
                return cached_result
            
            # Process through circuit breaker
            result = await self.circuit_breaker.call(
                lambda: self._api_process_item(item)
            )
            
            # Calculate processing time
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            result.processing_time_ms = processing_time
            
            # Add to collector
            await self.results_collector.add_result(item.position, result)
            await self.progress_tracker.complete_item(item.position, True)
            
            return result
            
        except RateLimitError as e:
            logger.warning(f"Rate limit hit for item {item.position}: {e}")
            await self.progress_tracker.complete_item(
                item.position, False, str(e)
            )
            raise
        except Exception as e:
            logger.error(f"Error processing item {item.position}: {e}")
            await self.progress_tracker.complete_item(
                item.position, False, str(e)
            )
            
            # Create error result
            error_result = ProcessingResult(
                position=item.position,
                term=item.term,
                error=str(e),
                processing_time_ms=(asyncio.get_event_loop().time() - start_time) * 1000
            )
            
            await self.results_collector.add_result(item.position, error_result)
            return error_result
        finally:
            # Always release rate limiter
            self.rate_limiter.release()
    
    async def _check_cache(self, item: VocabularyItem) -> Optional[ProcessingResult]:
        """Check if item is fully cached"""
        # Check stage 1 cache
        stage1_cached = await self.cache_service.get_stage1(item)
        if not stage1_cached:
            return None
            
        stage1_result, _ = stage1_cached
        
        # Check stage 2 cache
        stage2_cached = await self.cache_service.get_stage2(item, stage1_result)
        if not stage2_cached:
            return None
            
        stage2_result, _ = stage2_cached
        
        # Convert to TSV
        tsv_output = stage2_result.to_tsv()
        
        return ProcessingResult(
            position=item.position,
            term=item.term,
            flashcard_data=tsv_output,
            from_cache=True
        )
    
    async def _api_process_item(self, item: VocabularyItem) -> ProcessingResult:
        """Process item through API"""
        try:
            # Stage 1
            stage1_result, usage1 = await self.api_client.process_stage1(item)
            await self.cache_service.save_stage1(item, stage1_result, usage1.total_tokens)
            
            # Stage 2
            stage2_result, usage2 = await self.api_client.process_stage2(item, stage1_result)
            await self.cache_service.save_stage2(
                item, stage1_result, stage2_result, usage2.total_tokens
            )
            
            # Convert to TSV
            tsv_output = stage2_result.to_tsv()
            
            return ProcessingResult(
                position=item.position,
                term=item.term,
                flashcard_data=tsv_output,
                from_cache=False
            )
            
        except Exception as e:
            logger.error(f"API processing failed for '{item.term}': {e}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        progress_stats = self.progress_tracker.get_stats()
        rate_stats = self.rate_limiter.get_stats()
        
        return {
            "orchestrator": self.stats,
            "progress": progress_stats,
            "rate_limiter": rate_stats,
            "circuit_breaker": {
                "state": self.circuit_breaker.state.value,
                "failure_count": self.circuit_breaker.failure_count,
                "success_count": self.circuit_breaker.success_count
            }
        }