"""Unified pipeline orchestrator for flashcard processing"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
from dataclasses import dataclass
from enum import Enum
import json

from ..core.models import (
    VocabularyItem,
    Stage1Response,
    Stage2Request,
    Stage2Response,
    BatchResult,
    ExportFormat,
)
from ..core.processing_models import ProcessingResult, BatchProcessingResult
from ..core.exceptions import ProcessingError, ValidationError
from ..core.constants import DEFAULT_BATCH_SIZE

from ..api import OpenRouterClient, create_api_client
from ..cache import CacheService, create_cache_service
from ..services import (
    IngressService,
    ExportService,
    MonitoringService,
    ImportMode,
    create_ingress_service,
    create_export_service,
    create_monitoring_service,
)

logger = logging.getLogger(__name__)


class ProcessingMode(str, Enum):
    """Processing mode options"""
    SEQUENTIAL = "sequential"
    CONCURRENT = "concurrent"
    BATCH = "batch"


class PipelineConfig:
    """Pipeline configuration"""
    
    def __init__(
        self,
        mode: ProcessingMode = ProcessingMode.SEQUENTIAL,
        batch_size: int = DEFAULT_BATCH_SIZE,
        max_concurrent: int = 5,
        enable_cache: bool = True,
        enable_monitoring: bool = True,
        enable_retry: bool = True,
        max_retries: int = 3,
        temperature_stage1: float = 0.7,
        temperature_stage2: float = 0.7,
        num_cards_per_term: int = 2,
    ):
        self.mode = mode
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.enable_cache = enable_cache
        self.enable_monitoring = enable_monitoring
        self.enable_retry = enable_retry
        self.max_retries = max_retries
        self.temperature_stage1 = temperature_stage1
        self.temperature_stage2 = temperature_stage2
        self.num_cards_per_term = num_cards_per_term


@dataclass
class PipelineStats:
    """Pipeline execution statistics"""
    total_items: int = 0
    processed_items: int = 0
    failed_items: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    api_calls: int = 0
    total_tokens: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    errors: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    @property
    def duration_seconds(self) -> float:
        """Calculate duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_items > 0:
            return self.processed_items / self.total_items
        return 0.0


class PipelineOrchestrator:
    """Orchestrates the flashcard generation pipeline"""
    
    def __init__(
        self,
        api_client: Optional[OpenRouterClient] = None,
        cache_service: Optional[CacheService] = None,
        ingress_service: Optional[IngressService] = None,
        export_service: Optional[ExportService] = None,
        monitoring_service: Optional[MonitoringService] = None,
        db_manager=None,
        config: Optional[PipelineConfig] = None,
    ):
        self.api_client = api_client
        self.cache = cache_service
        self.ingress = ingress_service
        self.export = export_service or ExportService()
        self.monitoring = monitoring_service
        self.db_manager = db_manager
        self.config = config or PipelineConfig()
        
        # Statistics
        self.stats = PipelineStats()
        
        # Semaphore for concurrent processing
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
    
    async def process_file(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        output_format: ExportFormat = ExportFormat.TSV,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        import_mode: ImportMode = ImportMode.STANDARD,
    ) -> BatchProcessingResult:
        """
        Process vocabulary file through the complete pipeline.
        
        Args:
            input_path: Path to input CSV file
            output_path: Optional output path
            output_format: Output format
            progress_callback: Progress callback function
            import_mode: Import validation mode
            
        Returns:
            BatchProcessingResult with all results
        """
        self.stats = PipelineStats(start_time=datetime.now())
        
        try:
            # Import vocabulary
            if self.ingress:
                import_result = self.ingress.import_csv(
                    input_path,
                    mode=import_mode,
                    batch_size=self.config.batch_size,
                    progress_callback=progress_callback,
                )
                
                if import_result.status == "failed":
                    raise ProcessingError(f"Import failed: {import_result.errors}")
                
                # Get imported items
                vocabulary_items = self._get_imported_items(import_result.batch_id)
            else:
                # Direct CSV reading fallback
                vocabulary_items = self._read_csv_direct(input_path)
            
            self.stats.total_items = len(vocabulary_items)
            
            # Process items
            if self.config.mode == ProcessingMode.SEQUENTIAL:
                results = await self._process_sequential(vocabulary_items, progress_callback)
            elif self.config.mode == ProcessingMode.CONCURRENT:
                results = await self._process_concurrent(vocabulary_items, progress_callback)
            else:  # BATCH
                results = await self._process_batch(vocabulary_items, progress_callback)
            
            # Export results
            if output_path and results:
                self.export.export(results, output_format, output_path)
            
            # Update stats
            self.stats.end_time = datetime.now()
            self.stats.processed_items = len([r for r in results if r.success])
            self.stats.failed_items = len([r for r in results if not r.success])
            
            # Monitor if enabled
            if self.monitoring:
                await self.monitoring.collect_metrics()
                await self.monitoring.save_metrics()
            
            # Create batch result
            return BatchProcessingResult(
                results=results,
                total_processed=self.stats.processed_items,
                total_failed=self.stats.failed_items,
                processing_time=self.stats.duration_seconds,
                metadata={
                    "stats": self._get_stats_dict(),
                    "config": self._get_config_dict(),
                }
            )
            
        except Exception as e:
            logger.error(f"Pipeline processing failed: {e}")
            self.stats.errors.append({"error": str(e), "type": type(e).__name__})
            raise ProcessingError(f"Pipeline failed: {e}")
    
    async def process_items(
        self,
        items: List[VocabularyItem],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[ProcessingResult]:
        """
        Process a list of vocabulary items.
        
        Args:
            items: List of vocabulary items to process
            progress_callback: Optional progress callback
            
        Returns:
            List of processing results
        """
        self.stats = PipelineStats(
            start_time=datetime.now(),
            total_items=len(items)
        )
        
        # Process based on mode
        if self.config.mode == ProcessingMode.SEQUENTIAL:
            results = await self._process_sequential(items, progress_callback)
        elif self.config.mode == ProcessingMode.CONCURRENT:
            results = await self._process_concurrent(items, progress_callback)
        else:  # BATCH
            results = await self._process_batch(items, progress_callback)
        
        # Update stats
        self.stats.end_time = datetime.now()
        self.stats.processed_items = len([r for r in results if r.success])
        self.stats.failed_items = len([r for r in results if not r.success])
        
        return results
    
    async def _process_sequential(
        self,
        items: List[VocabularyItem],
        progress_callback: Optional[Callable],
    ) -> List[ProcessingResult]:
        """Process items sequentially"""
        results = []
        
        for i, item in enumerate(items):
            try:
                result = await self._process_single_item(item, i + 1)
                results.append(result)
                
                if progress_callback:
                    progress_callback(i + 1, len(items))
                    
            except Exception as e:
                logger.error(f"Failed to process {item.term}: {e}")
                results.append(ProcessingResult(
                    term=item.term,
                    pos=item.type,
                    term_number=i + 1,
                    success=False,
                    error=str(e)
                ))
        
        return results
    
    async def _process_concurrent(
        self,
        items: List[VocabularyItem],
        progress_callback: Optional[Callable],
    ) -> List[ProcessingResult]:
        """Process items concurrently"""
        tasks = []
        completed = 0
        
        async def process_with_progress(item: VocabularyItem, index: int):
            nonlocal completed
            async with self._semaphore:
                result = await self._process_single_item(item, index)
                completed += 1
                if progress_callback:
                    progress_callback(completed, len(items))
                return result
        
        # Create tasks
        for i, item in enumerate(items):
            task = asyncio.create_task(process_with_progress(item, i + 1))
            tasks.append(task)
        
        # Wait for all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ProcessingResult(
                    term=items[i].term,
                    pos=items[i].type,
                    term_number=i + 1,
                    success=False,
                    error=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _process_batch(
        self,
        items: List[VocabularyItem],
        progress_callback: Optional[Callable],
    ) -> List[ProcessingResult]:
        """Process items in batches"""
        results = []
        batch_size = self.config.batch_size
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            
            # Process batch concurrently
            batch_results = await self._process_concurrent(batch, None)
            results.extend(batch_results)
            
            if progress_callback:
                progress_callback(min(i + batch_size, len(items)), len(items))
        
        return results
    
    async def _process_single_item(
        self,
        item: VocabularyItem,
        term_number: int,
    ) -> ProcessingResult:
        """Process a single vocabulary item through both stages"""
        try:
            # Stage 1: Generate nuances
            stage1_output = await self._process_stage1(item)
            
            if not stage1_output:
                raise ProcessingError("Stage 1 produced no output")
            
            # Stage 2: Generate flashcards
            stage2_input = Stage2Request.from_stage1_result(item, stage1_output)
            
            stage2_output = await self._process_stage2(stage2_input)
            
            if not stage2_output:
                raise ProcessingError("Stage 2 produced no output")
            
            # Update database status if available
            if self.db_manager and hasattr(item, 'id'):
                self._update_item_status(item.id, "completed")
            
            return ProcessingResult(
                term=item.term,
                pos=item.type,
                term_number=term_number,
                stage1_output=stage1_output,
                stage2_output=stage2_output,
                success=True,
                cached_stage1=False,  # Will be updated by cache checks
                cached_stage2=False,
            )
            
        except Exception as e:
            logger.error(f"Error processing {item.term}: {e}")
            
            # Update database status if available
            if self.db_manager and hasattr(item, 'id'):
                self._update_item_status(item.id, "error", str(e))
            
            self.stats.errors.append({
                "term": item.term,
                "error": str(e),
                "type": type(e).__name__
            })
            
            return ProcessingResult(
                term=item.term,
                pos=item.type,
                term_number=term_number,
                success=False,
                error=str(e)
            )
    
    async def _process_stage1(self, item: VocabularyItem) -> Optional[Stage1Response]:
        """Process Stage 1 with retry logic"""
        if not self.api_client:
            raise ProcessingError("API client not configured")
        
        retries = 0
        last_error = None
        
        while retries <= self.config.max_retries:
            try:
                output = await self.api_client.process_stage1(
                    item.term,
                    item.type,
                    temperature=self.config.temperature_stage1
                )
                
                # Update stats
                if hasattr(self.api_client, 'stats'):
                    self.stats.cache_hits = self.api_client.stats.cache_hits
                    self.stats.cache_misses = self.api_client.stats.cache_misses
                    self.stats.api_calls = self.api_client.stats.requests
                    self.stats.total_tokens = self.api_client.stats.tokens_used
                
                return output
                
            except Exception as e:
                last_error = e
                retries += 1
                if retries <= self.config.max_retries:
                    await asyncio.sleep(2 ** retries)  # Exponential backoff
        
        raise ProcessingError(f"Stage 1 failed after {retries} retries: {last_error}")
    
    async def _process_stage2(self, stage2_input: Stage2Request) -> Optional[Stage2Response]:
        """Process Stage 2 with retry logic"""
        if not self.api_client:
            raise ProcessingError("API client not configured")
        
        retries = 0
        last_error = None
        
        while retries <= self.config.max_retries:
            try:
                output = await self.api_client.process_stage2(
                    stage2_input,
                    temperature=self.config.temperature_stage2
                )
                
                # Update stats
                if hasattr(self.api_client, 'stats'):
                    self.stats.api_calls = self.api_client.stats.requests
                    self.stats.total_tokens = self.api_client.stats.tokens_used
                
                return output
                
            except Exception as e:
                last_error = e
                retries += 1
                if retries <= self.config.max_retries:
                    await asyncio.sleep(2 ** retries)
        
        raise ProcessingError(f"Stage 2 failed after {retries} retries: {last_error}")
    
    def _get_imported_items(self, batch_id: int) -> List[VocabularyItem]:
        """Get imported vocabulary items from database"""
        if not self.db_manager:
            return []
        
        rows = self.db_manager.execute(
            """SELECT id, term, pos, definition, example, difficulty, tags, notes
            FROM vocabulary
            WHERE import_batch_id = ?
            ORDER BY id""",
            (batch_id,)
        ).fetchall()
        
        items = []
        for i, row in enumerate(rows):
            item = VocabularyItem(
                position=i+1,
                term=row[1],
                type=row[2]
            )
            item.id = row[0]  # Store ID for status updates
            items.append(item)
        
        return items
    
    def _read_csv_direct(self, file_path: Union[str, Path]) -> List[VocabularyItem]:
        """Read CSV file directly (fallback)"""
        import csv
        
        items = []
        file_path = Path(file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                item = VocabularyItem(
                    position=i+1,  # Use row number as position
                    term=row.get("term", "").strip(),
                    type=row.get("type", row.get("pos", "")).strip(),  # Support both 'type' and 'pos' columns
                )
                items.append(item)
        
        return items
    
    def _update_item_status(
        self,
        item_id: int,
        status: str,
        error_message: Optional[str] = None
    ):
        """Update vocabulary item status in database"""
        if not self.db_manager:
            return
        
        self.db_manager.execute(
            """UPDATE vocabulary
            SET status = ?, error_message = ?, updated_at = ?
            WHERE id = ?""",
            (status, error_message, datetime.now().isoformat(), item_id)
        )
    
    def _get_stats_dict(self) -> Dict[str, Any]:
        """Get statistics as dictionary"""
        return {
            "total_items": self.stats.total_items,
            "processed_items": self.stats.processed_items,
            "failed_items": self.stats.failed_items,
            "success_rate": f"{self.stats.success_rate:.1%}",
            "cache_hits": self.stats.cache_hits,
            "cache_misses": self.stats.cache_misses,
            "api_calls": self.stats.api_calls,
            "total_tokens": self.stats.total_tokens,
            "duration_seconds": self.stats.duration_seconds,
            "errors": len(self.stats.errors),
        }
    
    def _get_config_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary"""
        return {
            "mode": self.config.mode.value,
            "batch_size": self.config.batch_size,
            "max_concurrent": self.config.max_concurrent,
            "enable_cache": self.config.enable_cache,
            "enable_monitoring": self.config.enable_monitoring,
            "max_retries": self.config.max_retries,
            "num_cards_per_term": self.config.num_cards_per_term,
        }
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get pipeline health status"""
        status = {
            "pipeline": "healthy",
            "components": {}
        }
        
        # Check API client
        if self.api_client:
            try:
                connected = await self.api_client.test_connection()
                status["components"]["api"] = "healthy" if connected else "unhealthy"
            except Exception as e:
                status["components"]["api"] = f"error: {e}"
                status["pipeline"] = "degraded"
        
        # Check cache
        if self.cache:
            try:
                cache_stats = await self.cache.get_stats()
                status["components"]["cache"] = {
                    "status": "healthy",
                    "hit_rate": cache_stats.get("hit_rate", 0)
                }
            except Exception as e:
                status["components"]["cache"] = f"error: {e}"
                status["pipeline"] = "degraded"
        
        # Check monitoring
        if self.monitoring:
            try:
                health = await self.monitoring.check_health()
                status["components"]["monitoring"] = health["status"]
            except Exception as e:
                status["components"]["monitoring"] = f"error: {e}"
        
        return status


# Factory function
def create_pipeline(
    api_key: str,
    db_manager=None,
    cache_dir: str = ".cache",
    simple_mode: bool = False,
    config: Optional[PipelineConfig] = None,
) -> PipelineOrchestrator:
    """Create a configured pipeline orchestrator"""
    
    # Create services
    api_client = create_api_client(api_key, simple_mode=simple_mode)
    cache_service = create_cache_service(cache_dir, simple_mode=simple_mode)
    
    ingress_service = None
    monitoring_service = None
    
    if db_manager:
        ingress_service = create_ingress_service(db_manager, simple_mode=simple_mode)
        if not simple_mode:
            monitoring_service = create_monitoring_service(
                db_manager=db_manager,
                cache_service=cache_service,
                api_client=api_client
            )
    
    return PipelineOrchestrator(
        api_client=api_client,
        cache_service=cache_service,
        ingress_service=ingress_service,
        monitoring_service=monitoring_service,
        db_manager=db_manager,
        config=config,
    )