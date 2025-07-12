"""
Export Service for Flashcard Pipeline
====================================

Manages various export formats and operations for flashcards.
Supports TSV, Anki, JSON, and PDF formats with advanced filtering.

Features:
- Multiple export formats
- Tag-based filtering
- Custom field mapping
- Export templates
- Batch operations
- Progress tracking
"""

import os
import json
import logging
from typing import Dict, List, Optional, Set, Any, Union
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .database.db_manager import DatabaseManager
from .models import (
    Flashcard, Deck, Tag,
    ValidationStatus, ProcessingStage,
    ExportFormat as ModelExportFormat
)
from .exceptions import (
    ExportError, ValidationError,
    DatabaseError, ConfigurationError
)

logger = logging.getLogger(__name__)

# Use ExportFormat from models
ExportFormat = ModelExportFormat


@dataclass
class ExportConfig:
    """Configuration for export operations"""
    format: ModelExportFormat
    output_path: Path
    include_metadata: bool = True
    include_tags: bool = True
    include_statistics: bool = False
    custom_fields: Optional[Dict[str, str]] = None
    template_name: Optional[str] = None
    compression: bool = False
    encoding: str = "utf-8"
    batch_size: int = 1000
    filters: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if isinstance(self.output_path, str):
            self.output_path = Path(self.output_path)
        
        # Ensure output directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class ExportResult:
    """Result of an export operation"""
    success: bool
    format: ModelExportFormat
    output_path: Path
    total_cards: int
    exported_cards: int
    skipped_cards: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExportService:
    """
    Main service for exporting flashcards in various formats.
    
    Handles:
    - Format selection and validation
    - Filtering and data preparation
    - Progress tracking
    - Error handling and recovery
    - Batch processing
    """
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        exporters: Optional[Dict[ExportFormat, Any]] = None,
        templates_dir: Optional[Path] = None,
        max_workers: int = 4
    ):
        """
        Initialize export service.
        
        Args:
            db_manager: Database manager instance
            exporters: Dictionary of format-specific exporters
            templates_dir: Directory containing export templates
            max_workers: Maximum number of concurrent export workers
        """
        self.db_manager = db_manager
        self.exporters = exporters or {}
        self.templates_dir = templates_dir or Path("templates/export")
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Ensure templates directory exists
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Load available templates
        self.templates = self._load_templates()
        
        # Initialize default exporters if not provided
        if not self.exporters:
            self._initialize_default_exporters()
    
    def _initialize_default_exporters(self):
        """Initialize default exporters for each format"""
        try:
            # Import exporters dynamically
            from .exporters.tsv_exporter import TSVExporter
            from .exporters.anki_exporter import AnkiExporter
            from .exporters.json_exporter import JSONExporter
            from .exporters.pdf_exporter import PDFExporter
            
            self.exporters[ExportFormat.TSV] = TSVExporter()
            self.exporters[ExportFormat.ANKI] = AnkiExporter()
            self.exporters[ExportFormat.JSON] = JSONExporter()
            self.exporters[ExportFormat.PDF] = PDFExporter()
            
            logger.info(f"Initialized {len(self.exporters)} default exporters")
            
        except ImportError as e:
            logger.warning(f"Could not import all exporters: {e}")
    
    def _load_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load available export templates"""
        templates = {}
        
        if not self.templates_dir.exists():
            return templates
        
        for template_file in self.templates_dir.glob("*.json"):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                    template_name = template_file.stem
                    templates[template_name] = template_data
                    logger.debug(f"Loaded template: {template_name}")
            except Exception as e:
                logger.error(f"Failed to load template {template_file}: {e}")
        
        return templates
    
    async def export(
        self,
        config: ExportConfig,
        progress_callback: Optional[callable] = None
    ) -> ExportResult:
        """
        Export flashcards according to configuration.
        
        Args:
            config: Export configuration
            progress_callback: Optional callback for progress updates
            
        Returns:
            ExportResult with operation details
        """
        start_time = datetime.now()
        result = ExportResult(
            success=False,
            format=config.format,
            output_path=config.output_path,
            total_cards=0,
            exported_cards=0
        )
        
        try:
            # Validate configuration
            self._validate_config(config)
            
            # Get flashcards based on filters
            flashcards = await self._fetch_flashcards(config.filters)
            result.total_cards = len(flashcards)
            
            if not flashcards:
                result.warnings.append("No flashcards found matching filters")
                result.success = True
                return result
            
            # Apply template if specified
            if config.template_name:
                config = self._apply_template(config)
            
            # Get appropriate exporter
            exporter = self.exporters.get(config.format)
            if not exporter:
                raise ExportError(f"No exporter available for format: {config.format}")
            
            # Prepare export data
            export_data = await self._prepare_export_data(
                flashcards, config, progress_callback
            )
            
            # Perform export
            if hasattr(exporter, 'export_async'):
                await exporter.export_async(export_data, config)
            else:
                # Run synchronous exporter in thread pool
                await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    exporter.export,
                    export_data,
                    config
                )
            
            result.exported_cards = len(export_data['flashcards'])
            result.skipped_cards = result.total_cards - result.exported_cards
            result.success = True
            result.metadata = {
                'format': config.format.value,
                'filters_applied': bool(config.filters),
                'template_used': config.template_name,
                'compression': config.compression
            }
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            result.errors.append(str(e))
            raise ExportError(f"Export operation failed: {e}")
        
        finally:
            result.duration_seconds = (datetime.now() - start_time).total_seconds()
            
            # Log result
            if result.success:
                logger.info(
                    f"Export completed: {result.exported_cards}/{result.total_cards} "
                    f"cards exported to {result.output_path} in {result.duration_seconds:.2f}s"
                )
            else:
                logger.error(f"Export failed with {len(result.errors)} errors")
        
        return result
    
    def _validate_config(self, config: ExportConfig):
        """Validate export configuration"""
        if not config.format:
            raise ConfigurationError("Export format must be specified")
        
        if not config.output_path:
            raise ConfigurationError("Output path must be specified")
        
        # Validate format-specific requirements
        if config.format == ExportFormat.PDF and not config.template_name:
            # Set default PDF template if none specified
            config.template_name = "default_pdf"
        
        if config.custom_fields:
            # Validate custom field mappings
            for source, target in config.custom_fields.items():
                if not isinstance(source, str) or not isinstance(target, str):
                    raise ConfigurationError(
                        f"Invalid custom field mapping: {source} -> {target}"
                    )
    
    async def _fetch_flashcards(
        self,
        filters: Dict[str, Any]
    ) -> List[Flashcard]:
        """
        Fetch flashcards from database based on filters.
        
        Supported filters:
        - deck_ids: List of deck IDs
        - tag_names: List of tag names
        - created_after: DateTime
        - created_before: DateTime
        - status: ValidationStatus
        - stage: ProcessingStage
        - limit: Maximum number of cards
        """
        query_parts = []
        params = {}
        
        base_query = """
            SELECT DISTINCT f.* FROM flashcards f
            LEFT JOIN flashcard_tags ft ON f.id = ft.flashcard_id
            LEFT JOIN tags t ON ft.tag_id = t.id
            WHERE 1=1
        """
        
        # Apply deck filter
        if deck_ids := filters.get('deck_ids'):
            query_parts.append("AND f.deck_id IN :deck_ids")
            params['deck_ids'] = deck_ids
        
        # Apply tag filter
        if tag_names := filters.get('tag_names'):
            query_parts.append("AND t.name IN :tag_names")
            params['tag_names'] = tag_names
        
        # Apply date filters
        if created_after := filters.get('created_after'):
            query_parts.append("AND f.created_at >= :created_after")
            params['created_after'] = created_after
        
        if created_before := filters.get('created_before'):
            query_parts.append("AND f.created_at <= :created_before")
            params['created_before'] = created_before
        
        # Apply status filter
        if status := filters.get('status'):
            query_parts.append("AND f.validation_status = :status")
            params['status'] = status.value if hasattr(status, 'value') else status
        
        # Apply stage filter
        if stage := filters.get('stage'):
            query_parts.append("AND f.processing_stage = :stage")
            params['stage'] = stage.value if hasattr(stage, 'value') else stage
        
        # Build final query
        query = base_query + " ".join(query_parts)
        
        # Add ordering
        query += " ORDER BY f.created_at DESC"
        
        # Apply limit
        if limit := filters.get('limit'):
            query += f" LIMIT {int(limit)}"
        
        # Execute query
        try:
            async with self.db_manager.get_session() as session:
                result = await session.execute(query, params)
                flashcards = [Flashcard(**row) for row in result]
                
                # Load related data (tags, metadata)
                for flashcard in flashcards:
                    await self._load_flashcard_relations(flashcard, session)
                
                return flashcards
                
        except Exception as e:
            logger.error(f"Failed to fetch flashcards: {e}")
            raise DatabaseError(f"Could not fetch flashcards: {e}")
    
    async def _load_flashcard_relations(self, flashcard: Flashcard, session):
        """Load related data for a flashcard"""
        # Load tags
        tag_query = """
            SELECT t.* FROM tags t
            JOIN flashcard_tags ft ON t.id = ft.tag_id
            WHERE ft.flashcard_id = :flashcard_id
        """
        result = await session.execute(tag_query, {'flashcard_id': flashcard.id})
        flashcard.tags = [Tag(**row) for row in result]
        
        # Load metadata if needed
        # This could be extended based on requirements
    
    async def _prepare_export_data(
        self,
        flashcards: List[Flashcard],
        config: ExportConfig,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Prepare data for export.
        
        Returns:
            Dictionary with prepared export data
        """
        export_data = {
            'flashcards': [],
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'total_cards': len(flashcards),
                'format': config.format.value,
                'filters': config.filters
            }
        }
        
        # Process flashcards in batches
        batch_size = config.batch_size
        total_batches = (len(flashcards) + batch_size - 1) // batch_size
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(flashcards))
            batch = flashcards[start_idx:end_idx]
            
            # Process batch
            processed_batch = await self._process_flashcard_batch(batch, config)
            export_data['flashcards'].extend(processed_batch)
            
            # Update progress
            if progress_callback:
                progress = (batch_idx + 1) / total_batches
                await progress_callback(progress, f"Processing batch {batch_idx + 1}/{total_batches}")
        
        # Add deck information if needed
        if config.include_metadata:
            export_data['decks'] = await self._get_deck_info(flashcards)
        
        # Add tag summary if needed
        if config.include_tags:
            export_data['tags'] = self._get_tag_summary(flashcards)
        
        # Add statistics if needed
        if config.include_statistics:
            export_data['statistics'] = self._calculate_statistics(flashcards)
        
        return export_data
    
    async def _process_flashcard_batch(
        self,
        batch: List[Flashcard],
        config: ExportConfig
    ) -> List[Dict[str, Any]]:
        """Process a batch of flashcards for export"""
        processed = []
        
        for flashcard in batch:
            # Convert to export format
            card_data = {
                'id': flashcard.id,
                'korean': flashcard.korean,
                'english': flashcard.english,
                'romanization': flashcard.romanization,
                'explanation': flashcard.explanation,
                'tags': [tag.name for tag in flashcard.tags] if flashcard.tags else [],
                'created_at': flashcard.created_at.isoformat() if flashcard.created_at else None,
                'deck_id': flashcard.deck_id
            }
            
            # Apply custom field mappings
            if config.custom_fields:
                mapped_data = {}
                for source, target in config.custom_fields.items():
                    if source in card_data:
                        mapped_data[target] = card_data[source]
                card_data = mapped_data
            
            processed.append(card_data)
        
        return processed
    
    async def _get_deck_info(self, flashcards: List[Flashcard]) -> List[Dict[str, Any]]:
        """Get deck information for exported flashcards"""
        deck_ids = set(f.deck_id for f in flashcards if f.deck_id)
        
        if not deck_ids:
            return []
        
        try:
            async with self.db_manager.get_session() as session:
                query = "SELECT * FROM decks WHERE id IN :deck_ids"
                result = await session.execute(query, {'deck_ids': list(deck_ids)})
                
                return [
                    {
                        'id': row['id'],
                        'name': row['name'],
                        'description': row.get('description', '')
                    }
                    for row in result
                ]
        except Exception as e:
            logger.error(f"Failed to fetch deck info: {e}")
            return []
    
    def _get_tag_summary(self, flashcards: List[Flashcard]) -> Dict[str, int]:
        """Get tag usage summary"""
        tag_counts = {}
        
        for flashcard in flashcards:
            if flashcard.tags:
                for tag in flashcard.tags:
                    tag_name = tag.name
                    tag_counts[tag_name] = tag_counts.get(tag_name, 0) + 1
        
        return tag_counts
    
    def _calculate_statistics(self, flashcards: List[Flashcard]) -> Dict[str, Any]:
        """Calculate export statistics"""
        stats = {
            'total_cards': len(flashcards),
            'cards_by_status': {},
            'cards_by_stage': {},
            'avg_explanation_length': 0,
            'unique_tags': set()
        }
        
        total_explanation_length = 0
        
        for flashcard in flashcards:
            # Count by status
            status = flashcard.validation_status
            if status:
                stats['cards_by_status'][status] = stats['cards_by_status'].get(status, 0) + 1
            
            # Count by stage
            stage = flashcard.processing_stage
            if stage:
                stats['cards_by_stage'][stage] = stats['cards_by_stage'].get(stage, 0) + 1
            
            # Calculate explanation length
            if flashcard.explanation:
                total_explanation_length += len(flashcard.explanation)
            
            # Collect unique tags
            if flashcard.tags:
                stats['unique_tags'].update(tag.name for tag in flashcard.tags)
        
        # Calculate averages
        if flashcards:
            stats['avg_explanation_length'] = total_explanation_length / len(flashcards)
        
        stats['unique_tags'] = len(stats['unique_tags'])
        
        return stats
    
    def _apply_template(self, config: ExportConfig) -> ExportConfig:
        """Apply template settings to configuration"""
        if config.template_name not in self.templates:
            logger.warning(f"Template '{config.template_name}' not found")
            return config
        
        template = self.templates[config.template_name]
        
        # Apply template settings
        for key, value in template.items():
            if hasattr(config, key) and not getattr(config, key):
                setattr(config, key, value)
        
        return config
    
    async def export_batch(
        self,
        configs: List[ExportConfig],
        progress_callback: Optional[callable] = None
    ) -> List[ExportResult]:
        """
        Export flashcards in multiple formats simultaneously.
        
        Args:
            configs: List of export configurations
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of ExportResult objects
        """
        tasks = []
        
        for config in configs:
            task = self.export(config, progress_callback)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to failed results
        final_results = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                failed_result = ExportResult(
                    success=False,
                    format=configs[idx].format,
                    output_path=configs[idx].output_path,
                    total_cards=0,
                    exported_cards=0,
                    errors=[str(result)]
                )
                final_results.append(failed_result)
            else:
                final_results.append(result)
        
        return final_results
    
    def get_available_formats(self) -> List[ExportFormat]:
        """Get list of available export formats"""
        return list(self.exporters.keys())
    
    def get_available_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get available export templates"""
        return self.templates.copy()
    
    async def schedule_export(
        self,
        config: ExportConfig,
        schedule: str,
        callback: Optional[callable] = None
    ):
        """
        Schedule recurring exports.
        
        Args:
            config: Export configuration
            schedule: Cron-style schedule string
            callback: Optional callback for notifications
        """
        # This would integrate with a scheduler like APScheduler
        # Implementation depends on specific scheduling requirements
        raise NotImplementedError("Export scheduling not yet implemented")
    
    def __del__(self):
        """Cleanup resources"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)