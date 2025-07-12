"""
TSV (Tab-Separated Values) Exporter
===================================

Exports flashcards in TSV format compatible with various flashcard applications.
Supports custom column mapping and UTF-8 encoding with BOM.
"""

import csv
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, TextIO
from datetime import datetime
import codecs

from ..models import ExportConfig
from ..exceptions import ExportError

logger = logging.getLogger(__name__)


class TSVExporter:
    """
    TSV format exporter for flashcards.
    
    Features:
    - Standard flashcard format (front/back/tags)
    - Custom column mapping
    - UTF-8 encoding with optional BOM
    - Header row configuration
    - Field escaping and quoting
    - Bulk export support
    """
    
    # Default column mapping
    DEFAULT_COLUMNS = {
        'korean': 'Front',
        'english': 'Back',
        'romanization': 'Romanization',
        'explanation': 'Notes',
        'tags': 'Tags'
    }
    
    # Standard Anki-compatible columns
    ANKI_COLUMNS = {
        'korean': 'Front',
        'english': 'Back',
        'tags': 'Tags'
    }
    
    def __init__(
        self,
        include_bom: bool = True,
        delimiter: str = '\t',
        quoting: int = csv.QUOTE_MINIMAL,
        escapechar: str = '\\',
        include_header: bool = True
    ):
        """
        Initialize TSV exporter.
        
        Args:
            include_bom: Include UTF-8 BOM for better compatibility
            delimiter: Column delimiter (default: tab)
            quoting: CSV quoting style
            escapechar: Character for escaping special characters
            include_header: Include header row
        """
        self.include_bom = include_bom
        self.delimiter = delimiter
        self.quoting = quoting
        self.escapechar = escapechar
        self.include_header = include_header
    
    def export(
        self,
        export_data: Dict[str, Any],
        config: ExportConfig
    ) -> None:
        """
        Export flashcards to TSV file.
        
        Args:
            export_data: Dictionary containing flashcards and metadata
            config: Export configuration
        """
        try:
            flashcards = export_data.get('flashcards', [])
            if not flashcards:
                logger.warning("No flashcards to export")
                return
            
            # Determine column mapping
            columns = self._get_column_mapping(config)
            
            # Open file with appropriate encoding
            with self._open_file(config.output_path, config.encoding) as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=list(columns.values()),
                    delimiter=self.delimiter,
                    quoting=self.quoting,
                    escapechar=self.escapechar
                )
                
                # Write header if configured
                if self.include_header:
                    writer.writeheader()
                
                # Write flashcards
                row_count = 0
                for flashcard in flashcards:
                    row = self._prepare_row(flashcard, columns)
                    writer.writerow(row)
                    row_count += 1
                
                logger.info(f"Exported {row_count} flashcards to TSV file")
                
                # Add metadata as comments if configured
                if config.include_metadata:
                    self._write_metadata(f, export_data.get('metadata', {}))
                    
        except Exception as e:
            logger.error(f"TSV export failed: {e}")
            raise ExportError(f"Failed to export TSV file: {e}")
    
    def _open_file(self, path: Path, encoding: str) -> TextIO:
        """Open file with appropriate encoding and BOM handling"""
        if self.include_bom and encoding.lower() == 'utf-8':
            # Use UTF-8 with BOM
            return codecs.open(
                path, 'w', encoding='utf-8-sig', errors='replace'
            )
        else:
            return open(
                path, 'w', encoding=encoding, errors='replace', newline=''
            )
    
    def _get_column_mapping(self, config: ExportConfig) -> Dict[str, str]:
        """Get column mapping from config or use defaults"""
        if config.custom_fields:
            return config.custom_fields
        
        # Check for preset mappings based on template
        if config.template_name == 'anki':
            return self.ANKI_COLUMNS.copy()
        
        return self.DEFAULT_COLUMNS.copy()
    
    def _prepare_row(
        self,
        flashcard: Dict[str, Any],
        columns: Dict[str, str]
    ) -> Dict[str, str]:
        """Prepare a row for CSV writing"""
        row = {}
        
        for source_field, target_column in columns.items():
            value = flashcard.get(source_field, '')
            
            # Special handling for different field types
            if source_field == 'tags':
                # Join tags with spaces (Anki convention)
                if isinstance(value, list):
                    value = ' '.join(str(tag) for tag in value)
            elif isinstance(value, (list, dict)):
                # Convert complex types to string
                value = str(value)
            elif value is None:
                value = ''
            
            # Clean and normalize text
            value = self._clean_text(str(value))
            
            row[target_column] = value
        
        return row
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for TSV export"""
        if not text:
            return ''
        
        # Remove or replace problematic characters
        cleaned = text.replace('\r\n', ' ')  # Windows line endings
        cleaned = cleaned.replace('\n', ' ')  # Unix line endings
        cleaned = cleaned.replace('\r', ' ')  # Old Mac line endings
        
        # Handle tabs in content
        if self.delimiter == '\t':
            cleaned = cleaned.replace('\t', '    ')  # Replace tabs with spaces
        
        # Remove excessive whitespace
        cleaned = ' '.join(cleaned.split())
        
        return cleaned.strip()
    
    def _write_metadata(self, f: TextIO, metadata: Dict[str, Any]):
        """Write metadata as comments at the end of file"""
        f.write('\n')
        f.write(f"# Export Metadata\n")
        f.write(f"# Generated: {metadata.get('export_date', datetime.now().isoformat())}\n")
        f.write(f"# Total Cards: {metadata.get('total_cards', 0)}\n")
        
        if filters := metadata.get('filters'):
            f.write(f"# Filters Applied:\n")
            for key, value in filters.items():
                f.write(f"#   {key}: {value}\n")
    
    def export_bulk(
        self,
        flashcard_batches: List[List[Dict[str, Any]]],
        base_path: Path,
        config: ExportConfig
    ) -> List[Path]:
        """
        Export multiple batches to separate TSV files.
        
        Args:
            flashcard_batches: List of flashcard batches
            base_path: Base path for output files
            config: Export configuration
            
        Returns:
            List of created file paths
        """
        output_files = []
        
        for idx, batch in enumerate(flashcard_batches):
            # Create unique filename for each batch
            batch_path = base_path.parent / f"{base_path.stem}_batch_{idx + 1}{base_path.suffix}"
            
            # Update config with new path
            batch_config = ExportConfig(
                format=config.format,
                output_path=batch_path,
                include_metadata=config.include_metadata,
                include_tags=config.include_tags,
                custom_fields=config.custom_fields,
                template_name=config.template_name,
                encoding=config.encoding
            )
            
            # Export batch
            export_data = {
                'flashcards': batch,
                'metadata': {
                    'batch_number': idx + 1,
                    'total_batches': len(flashcard_batches),
                    'cards_in_batch': len(batch)
                }
            }
            
            self.export(export_data, batch_config)
            output_files.append(batch_path)
        
        logger.info(f"Exported {len(flashcard_batches)} batches to TSV files")
        return output_files
    
    def validate_tsv(self, file_path: Path) -> Dict[str, Any]:
        """
        Validate a TSV file for common issues.
        
        Args:
            file_path: Path to TSV file
            
        Returns:
            Validation results dictionary
        """
        results = {
            'valid': True,
            'row_count': 0,
            'column_count': 0,
            'issues': [],
            'warnings': []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f, delimiter=self.delimiter)
                
                # Check header
                try:
                    header = next(reader)
                    results['column_count'] = len(header)
                    results['columns'] = header
                except StopIteration:
                    results['valid'] = False
                    results['issues'].append("File is empty")
                    return results
                
                # Validate rows
                for row_idx, row in enumerate(reader):
                    results['row_count'] += 1
                    
                    # Check column count
                    if len(row) != results['column_count']:
                        results['warnings'].append(
                            f"Row {row_idx + 2} has {len(row)} columns, "
                            f"expected {results['column_count']}"
                        )
                    
                    # Check for empty required fields
                    if len(row) >= 2:
                        if not row[0].strip():  # Front field
                            results['warnings'].append(
                                f"Row {row_idx + 2} has empty front field"
                            )
                        if not row[1].strip():  # Back field
                            results['warnings'].append(
                                f"Row {row_idx + 2} has empty back field"
                            )
                
                # Check minimum requirements
                if results['row_count'] == 0:
                    results['valid'] = False
                    results['issues'].append("No data rows found")
                
                if results['column_count'] < 2:
                    results['valid'] = False
                    results['issues'].append(
                        f"Insufficient columns ({results['column_count']}), "
                        "minimum 2 required for front/back"
                    )
                    
        except Exception as e:
            results['valid'] = False
            results['issues'].append(f"Failed to read file: {e}")
        
        return results