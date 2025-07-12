"""
JSON Exporter
=============

Exports flashcards in JSON format for APIs and data interchange.
Supports structured output, compression, and metadata inclusion.
"""

import json
import gzip
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import base64

from ..models import ExportConfig
from ..exceptions import ExportError

logger = logging.getLogger(__name__)


class JSONExporter:
    """
    JSON format exporter for flashcards.
    
    Features:
    - Structured JSON output
    - API-friendly formatting
    - Optional compression (gzip)
    - Metadata inclusion
    - Custom field filtering
    - Batch export support
    - Schema validation
    """
    
    # JSON schema version
    SCHEMA_VERSION = "1.0"
    
    # Default output structure
    DEFAULT_STRUCTURE = {
        'version': SCHEMA_VERSION,
        'generated_at': None,
        'metadata': {},
        'flashcards': [],
        'decks': [],
        'tags': {}
    }
    
    def __init__(
        self,
        pretty_print: bool = True,
        include_schema: bool = True,
        date_format: str = 'iso'
    ):
        """
        Initialize JSON exporter.
        
        Args:
            pretty_print: Format JSON with indentation
            include_schema: Include schema information in output
            date_format: Date formatting style ('iso', 'timestamp', 'readable')
        """
        self.pretty_print = pretty_print
        self.include_schema = include_schema
        self.date_format = date_format
        self.indent = 2 if pretty_print else None
    
    def export(
        self,
        export_data: Dict[str, Any],
        config: ExportConfig
    ) -> None:
        """
        Export flashcards to JSON file.
        
        Args:
            export_data: Dictionary containing flashcards and metadata
            config: Export configuration
        """
        try:
            # Build JSON structure
            output = self._build_json_structure(export_data, config)
            
            # Convert to JSON string
            json_str = json.dumps(
                output,
                ensure_ascii=False,
                indent=self.indent,
                sort_keys=True,
                default=self._json_serializer
            )
            
            # Write to file
            if config.compression:
                self._write_compressed(config.output_path, json_str, config.encoding)
            else:
                self._write_plain(config.output_path, json_str, config.encoding)
            
            logger.info(
                f"Exported {len(export_data.get('flashcards', []))} flashcards "
                f"to JSON file: {config.output_path}"
            )
            
        except Exception as e:
            logger.error(f"JSON export failed: {e}")
            raise ExportError(f"Failed to export JSON file: {e}")
    
    def _build_json_structure(
        self,
        export_data: Dict[str, Any],
        config: ExportConfig
    ) -> Dict[str, Any]:
        """Build structured JSON output"""
        output = self.DEFAULT_STRUCTURE.copy()
        
        # Set metadata
        output['generated_at'] = self._format_date(datetime.now())
        output['metadata'] = self._build_metadata(export_data, config)
        
        # Add flashcards
        flashcards = export_data.get('flashcards', [])
        output['flashcards'] = self._format_flashcards(flashcards, config)
        
        # Add decks if available
        if decks := export_data.get('decks'):
            output['decks'] = decks
        
        # Add tag summary if available
        if tags := export_data.get('tags'):
            output['tags'] = tags
        
        # Add statistics if available
        if stats := export_data.get('statistics'):
            output['statistics'] = stats
        
        # Add schema if configured
        if self.include_schema:
            output['schema'] = self._get_schema()
        
        return output
    
    def _build_metadata(
        self,
        export_data: Dict[str, Any],
        config: ExportConfig
    ) -> Dict[str, Any]:
        """Build metadata section"""
        metadata = {
            'export_format': config.format.value,
            'total_flashcards': len(export_data.get('flashcards', [])),
            'export_date': self._format_date(datetime.now()),
            'encoding': config.encoding,
            'compressed': config.compression
        }
        
        # Add filters if any
        if config.filters:
            metadata['filters_applied'] = config.filters
        
        # Add custom metadata from export data
        if export_meta := export_data.get('metadata'):
            metadata.update(export_meta)
        
        return metadata
    
    def _format_flashcards(
        self,
        flashcards: List[Dict[str, Any]],
        config: ExportConfig
    ) -> List[Dict[str, Any]]:
        """Format flashcards for JSON output"""
        formatted = []
        
        for flashcard in flashcards:
            card = self._format_single_flashcard(flashcard, config)
            formatted.append(card)
        
        return formatted
    
    def _format_single_flashcard(
        self,
        flashcard: Dict[str, Any],
        config: ExportConfig
    ) -> Dict[str, Any]:
        """Format a single flashcard"""
        # Start with all fields
        card = flashcard.copy()
        
        # Format dates
        for date_field in ['created_at', 'updated_at', 'last_reviewed']:
            if date_field in card and card[date_field]:
                card[date_field] = self._format_date(card[date_field])
        
        # Apply custom field mapping if specified
        if config.custom_fields:
            mapped_card = {}
            for source, target in config.custom_fields.items():
                if source in card:
                    mapped_card[target] = card[source]
            card = mapped_card
        
        # Remove None values for cleaner output
        card = {k: v for k, v in card.items() if v is not None}
        
        return card
    
    def _format_date(self, date_value: Any) -> Union[str, int]:
        """Format date based on configured format"""
        if not date_value:
            return None
        
        # Handle string dates
        if isinstance(date_value, str):
            try:
                date_value = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            except:
                return date_value
        
        # Format based on preference
        if self.date_format == 'timestamp':
            return int(date_value.timestamp())
        elif self.date_format == 'readable':
            return date_value.strftime('%Y-%m-%d %H:%M:%S')
        else:  # iso
            return date_value.isoformat()
    
    def _json_serializer(self, obj):
        """Custom JSON serializer for non-standard types"""
        if isinstance(obj, datetime):
            return self._format_date(obj)
        elif isinstance(obj, bytes):
            return base64.b64encode(obj).decode('utf-8')
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    def _get_schema(self) -> Dict[str, Any]:
        """Get JSON schema information"""
        return {
            'version': self.SCHEMA_VERSION,
            'flashcard_fields': {
                'id': {'type': 'string', 'required': True},
                'korean': {'type': 'string', 'required': True},
                'english': {'type': 'string', 'required': True},
                'romanization': {'type': 'string', 'required': False},
                'explanation': {'type': 'string', 'required': False},
                'tags': {'type': 'array', 'items': {'type': 'string'}},
                'deck_id': {'type': 'string', 'required': False},
                'created_at': {'type': 'string', 'format': 'date-time'},
                'validation_status': {'type': 'string', 'enum': ['pending', 'approved', 'rejected']},
                'processing_stage': {'type': 'string'}
            }
        }
    
    def _write_plain(self, path: Path, content: str, encoding: str):
        """Write plain JSON file"""
        with open(path, 'w', encoding=encoding) as f:
            f.write(content)
    
    def _write_compressed(self, path: Path, content: str, encoding: str):
        """Write gzip-compressed JSON file"""
        # Ensure .gz extension
        if not str(path).endswith('.gz'):
            path = Path(str(path) + '.gz')
        
        with gzip.open(path, 'wt', encoding=encoding) as f:
            f.write(content)
    
    def export_streaming(
        self,
        flashcard_generator,
        config: ExportConfig,
        batch_size: int = 100
    ) -> None:
        """
        Export flashcards using streaming for large datasets.
        
        Args:
            flashcard_generator: Generator yielding flashcards
            config: Export configuration
            batch_size: Number of flashcards to buffer before writing
        """
        try:
            with open(config.output_path, 'w', encoding=config.encoding) as f:
                # Write opening structure
                f.write('{\n')
                f.write(f'  "version": "{self.SCHEMA_VERSION}",\n')
                f.write(f'  "generated_at": "{self._format_date(datetime.now())}",\n')
                f.write('  "flashcards": [\n')
                
                first = True
                count = 0
                
                for flashcard in flashcard_generator:
                    if not first:
                        f.write(',\n')
                    else:
                        first = False
                    
                    # Write formatted flashcard
                    card_json = json.dumps(
                        self._format_single_flashcard(flashcard, config),
                        ensure_ascii=False,
                        indent=4 if self.pretty_print else None,
                        default=self._json_serializer
                    )
                    
                    # Indent for array
                    if self.pretty_print:
                        card_json = '\n'.join('    ' + line for line in card_json.split('\n'))
                    
                    f.write(card_json)
                    count += 1
                
                # Close structure
                f.write('\n  ],\n')
                f.write(f'  "total_exported": {count}\n')
                f.write('}\n')
            
            logger.info(f"Streamed {count} flashcards to JSON file")
            
        except Exception as e:
            logger.error(f"Streaming JSON export failed: {e}")
            raise ExportError(f"Failed to export JSON stream: {e}")
    
    def validate_json(self, file_path: Path) -> Dict[str, Any]:
        """
        Validate a JSON export file.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Validation results dictionary
        """
        results = {
            'valid': True,
            'flashcard_count': 0,
            'has_metadata': False,
            'has_schema': False,
            'issues': [],
            'warnings': []
        }
        
        try:
            # Read file
            if str(file_path).endswith('.gz'):
                with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            # Check structure
            if not isinstance(data, dict):
                results['valid'] = False
                results['issues'].append("Root element must be an object")
                return results
            
            # Check version
            if 'version' not in data:
                results['warnings'].append("No version field found")
            
            # Check flashcards
            if 'flashcards' not in data:
                results['valid'] = False
                results['issues'].append("No flashcards array found")
            else:
                flashcards = data['flashcards']
                if not isinstance(flashcards, list):
                    results['valid'] = False
                    results['issues'].append("Flashcards must be an array")
                else:
                    results['flashcard_count'] = len(flashcards)
                    
                    # Validate each flashcard
                    for idx, card in enumerate(flashcards):
                        card_issues = self._validate_flashcard(card, idx)
                        results['warnings'].extend(card_issues)
            
            # Check optional fields
            results['has_metadata'] = 'metadata' in data
            results['has_schema'] = 'schema' in data
            
        except json.JSONDecodeError as e:
            results['valid'] = False
            results['issues'].append(f"Invalid JSON: {e}")
        except Exception as e:
            results['valid'] = False
            results['issues'].append(f"Failed to read file: {e}")
        
        return results
    
    def _validate_flashcard(self, card: Dict[str, Any], index: int) -> List[str]:
        """Validate a single flashcard"""
        issues = []
        
        # Check required fields
        required_fields = ['korean', 'english']
        for field in required_fields:
            if field not in card or not card[field]:
                issues.append(f"Flashcard {index}: Missing or empty '{field}' field")
        
        # Check field types
        if 'tags' in card and not isinstance(card['tags'], list):
            issues.append(f"Flashcard {index}: 'tags' must be an array")
        
        return issues