"""Consolidated ingress service for importing vocabulary data"""

import csv
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..core.models import VocabularyItem, ValidationError as ValidationErrorModel
from ..core.exceptions import ValidationError, DatabaseError
from ..core.constants import DEFAULT_BATCH_SIZE, SUPPORTED_INPUT_FORMATS

logger = logging.getLogger(__name__)


class ImportMode(str, Enum):
    """Import operation modes"""
    SIMPLE = "simple"  # Basic import without validation
    STANDARD = "standard"  # Normal import with validation
    STRICT = "strict"  # Strict import with all checks


class ImportStatus(str, Enum):
    """Import status values"""
    PENDING = "pending"
    VALIDATING = "validating"
    IMPORTING = "importing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class IngressConfig:
    """Configuration for ingress service"""
    
    def __init__(
        self,
        enable_validation: bool = True,
        enable_progress_tracking: bool = True,
        enable_duplicate_detection: bool = True,
        enable_retry_mechanism: bool = True,
        enable_async_processing: bool = False,
        default_batch_size: int = DEFAULT_BATCH_SIZE,
        max_validation_errors: int = 1000,
        encoding: Optional[str] = None,
        delimiter: str = ",",
    ):
        self.enable_validation = enable_validation
        self.enable_progress_tracking = enable_progress_tracking
        self.enable_duplicate_detection = enable_duplicate_detection
        self.enable_retry_mechanism = enable_retry_mechanism
        self.enable_async_processing = enable_async_processing
        self.default_batch_size = default_batch_size
        self.max_validation_errors = max_validation_errors
        self.encoding = encoding
        self.delimiter = delimiter


class ValidationResult:
    """Result of CSV validation"""
    
    def __init__(self):
        self.is_valid = True
        self.errors: List[ValidationErrorModel] = []
        self.warnings: List[str] = []
        self.row_count = 0
        self.valid_row_count = 0
        self.duplicate_count = 0
        self.column_mapping: Dict[str, str] = {}


class ImportResult:
    """Result of import operation"""
    
    def __init__(
        self,
        batch_id: Optional[int] = None,
        imported_count: int = 0,
        skipped_count: int = 0,
        error_count: int = 0,
        duplicate_count: int = 0,
        status: ImportStatus = ImportStatus.PENDING,
        errors: Optional[List[Dict[str, Any]]] = None,
        validation_result: Optional[ValidationResult] = None,
    ):
        self.batch_id = batch_id
        self.imported_count = imported_count
        self.skipped_count = skipped_count
        self.error_count = error_count
        self.duplicate_count = duplicate_count
        self.status = status
        self.errors = errors or []
        self.validation_result = validation_result
        self.started_at = datetime.now()
        self.completed_at: Optional[datetime] = None


class IngressService:
    """Consolidated ingress service for vocabulary imports"""
    
    def __init__(
        self,
        db_manager: Any,
        config: Optional[IngressConfig] = None,
    ):
        self.db_manager = db_manager
        self.config = config or IngressConfig()
        self._executor = ThreadPoolExecutor(max_workers=4) if config and config.enable_async_processing else None
    
    # Main import methods
    
    def import_csv(
        self,
        file_path: Union[str, Path],
        mode: ImportMode = ImportMode.STANDARD,
        batch_size: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        skip_duplicates: bool = True,
        validate_only: bool = False,
    ) -> ImportResult:
        """
        Import vocabulary from CSV file.
        
        Args:
            file_path: Path to CSV file
            mode: Import mode (simple, standard, strict)
            batch_size: Number of rows to process at once
            progress_callback: Callback for progress updates
            skip_duplicates: Whether to skip duplicate entries
            validate_only: Only validate without importing
            
        Returns:
            ImportResult with details of the operation
        """
        file_path = Path(file_path)
        
        # Validate file
        if not file_path.exists():
            raise ValidationError(f"File not found: {file_path}")
        
        if file_path.suffix.lower() not in SUPPORTED_INPUT_FORMATS:
            raise ValidationError(f"Unsupported file format: {file_path.suffix}")
        
        # Choose import method based on mode
        if mode == ImportMode.SIMPLE:
            return self._simple_import(
                file_path, batch_size, progress_callback, skip_duplicates
            )
        else:
            return self._standard_import(
                file_path, mode, batch_size, progress_callback, 
                skip_duplicates, validate_only
            )
    
    async def import_csv_async(
        self,
        file_path: Union[str, Path],
        **kwargs
    ) -> ImportResult:
        """Async wrapper for import_csv"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, self.import_csv, file_path, **kwargs
        )
    
    # Simple import (backward compatibility)
    
    def _simple_import(
        self,
        file_path: Path,
        batch_size: Optional[int],
        progress_callback: Optional[Callable],
        skip_duplicates: bool,
    ) -> ImportResult:
        """Simple import without validation"""
        batch_size = batch_size or self.config.default_batch_size
        result = ImportResult()
        
        try:
            # Create import batch
            batch_id = self._create_import_batch(str(file_path))
            result.batch_id = batch_id
            
            # Read CSV
            encoding = self._detect_encoding(file_path)
            rows = self._read_csv(file_path, encoding)
            
            # Process in batches
            batch = []
            total_rows = len(rows)
            
            for i, row in enumerate(rows):
                batch.append(row)
                
                if len(batch) >= batch_size:
                    self._process_batch(batch, batch_id, result, skip_duplicates)
                    batch = []
                
                if progress_callback and self.config.enable_progress_tracking:
                    progress_callback(i + 1, total_rows)
            
            # Process remaining
            if batch:
                self._process_batch(batch, batch_id, result, skip_duplicates)
            
            # Update batch status
            self._update_batch_status(batch_id, ImportStatus.COMPLETED, result)
            result.status = ImportStatus.COMPLETED
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            if result.batch_id:
                self._update_batch_status(result.batch_id, ImportStatus.FAILED, result)
            result.status = ImportStatus.FAILED
            result.errors.append({"error": str(e)})
            raise
        
        finally:
            result.completed_at = datetime.now()
        
        return result
    
    # Standard import with validation
    
    def _standard_import(
        self,
        file_path: Path,
        mode: ImportMode,
        batch_size: Optional[int],
        progress_callback: Optional[Callable],
        skip_duplicates: bool,
        validate_only: bool,
    ) -> ImportResult:
        """Standard import with validation"""
        batch_size = batch_size or self.config.default_batch_size
        result = ImportResult()
        
        try:
            # Validate first
            if self.config.enable_validation:
                validation = self.validate_csv(file_path, mode == ImportMode.STRICT)
                result.validation_result = validation
                
                if not validation.is_valid and mode == ImportMode.STRICT:
                    result.status = ImportStatus.FAILED
                    result.errors = [{"error": "Validation failed", "details": validation.errors}]
                    return result
                
                if validate_only:
                    result.status = ImportStatus.COMPLETED
                    return result
            
            # Create import batch
            batch_id = self._create_import_batch(str(file_path))
            result.batch_id = batch_id
            
            # Read and process CSV
            encoding = self._detect_encoding(file_path)
            rows = self._read_csv(file_path, encoding)
            
            # Filter valid rows if validation was done
            if result.validation_result:
                valid_indices = set(range(len(rows))) - {e.row for e in result.validation_result.errors}
                rows = [row for i, row in enumerate(rows) if i in valid_indices]
            
            # Process with progress tracking
            total_rows = len(rows)
            batch = []
            
            for i, row in enumerate(rows):
                batch.append(row)
                
                if len(batch) >= batch_size:
                    self._process_batch_with_retry(batch, batch_id, result, skip_duplicates)
                    batch = []
                
                if progress_callback and self.config.enable_progress_tracking:
                    progress_callback(i + 1, total_rows)
            
            # Process remaining
            if batch:
                self._process_batch_with_retry(batch, batch_id, result, skip_duplicates)
            
            # Determine final status
            if result.error_count == 0:
                result.status = ImportStatus.COMPLETED
            elif result.imported_count > 0:
                result.status = ImportStatus.PARTIAL
            else:
                result.status = ImportStatus.FAILED
            
            self._update_batch_status(batch_id, result.status, result)
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            if result.batch_id:
                self._update_batch_status(result.batch_id, ImportStatus.FAILED, result)
            result.status = ImportStatus.FAILED
            result.errors.append({"error": str(e)})
            raise
        
        finally:
            result.completed_at = datetime.now()
        
        return result
    
    # Validation methods
    
    def validate_csv(
        self,
        file_path: Union[str, Path],
        strict: bool = False,
    ) -> ValidationResult:
        """Validate CSV file before import"""
        file_path = Path(file_path)
        result = ValidationResult()
        
        try:
            encoding = self._detect_encoding(file_path)
            
            with open(file_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f, delimiter=self.config.delimiter)
                
                # Check headers
                headers = reader.fieldnames or []
                result.column_mapping = self._validate_headers(headers, strict)
                
                # Validate rows
                for i, row in enumerate(reader):
                    result.row_count += 1
                    
                    try:
                        self._validate_row(row, i, result, strict)
                        result.valid_row_count += 1
                        
                    except ValidationError as e:
                        if len(result.errors) < self.config.max_validation_errors:
                            result.errors.append(ValidationErrorModel(
                                row=i,
                                column=e.field if hasattr(e, 'field') else None,
                                message=str(e),
                                value=e.value if hasattr(e, 'value') else None,
                            ))
                        result.is_valid = False
                
                # Check for duplicates
                if self.config.enable_duplicate_detection:
                    duplicates = self._check_duplicates_in_file(file_path, encoding)
                    result.duplicate_count = len(duplicates)
                    
                    if strict and duplicates:
                        result.is_valid = False
                        result.errors.append(ValidationErrorModel(
                            message=f"Found {len(duplicates)} duplicate entries"
                        ))
        
        except Exception as e:
            result.is_valid = False
            result.errors.append(ValidationErrorModel(message=f"Validation error: {e}"))
        
        return result
    
    def _validate_headers(
        self,
        headers: List[str],
        strict: bool,
    ) -> Dict[str, str]:
        """Validate CSV headers and create column mapping"""
        required_columns = {"term", "pos"}
        optional_columns = {"definition", "example", "notes", "tags", "difficulty"}
        
        # Normalize headers
        normalized = {h.lower().strip(): h for h in headers}
        
        # Check required columns
        mapping = {}
        for req in required_columns:
            if req in normalized:
                mapping[req] = normalized[req]
            elif not strict:
                # Try to find similar column
                similar = self._find_similar_column(req, normalized.keys())
                if similar:
                    mapping[req] = normalized[similar]
                else:
                    raise ValidationError(f"Required column '{req}' not found")
            else:
                raise ValidationError(f"Required column '{req}' not found")
        
        # Map optional columns
        for opt in optional_columns:
            if opt in normalized:
                mapping[opt] = normalized[opt]
        
        return mapping
    
    def _validate_row(
        self,
        row: Dict[str, str],
        row_index: int,
        result: ValidationResult,
        strict: bool,
    ) -> None:
        """Validate a single row"""
        # Check required fields
        if not row.get("term", "").strip():
            raise ValidationError("Term is required", field="term", value="")
        
        if not row.get("pos", "").strip():
            raise ValidationError("Part of speech is required", field="pos", value="")
        
        # Validate part of speech
        valid_pos = {"noun", "verb", "adjective", "adverb", "phrase", "particle", "interjection"}
        pos = row.get("pos", "").lower().strip()
        
        if strict and pos not in valid_pos:
            raise ValidationError(f"Invalid part of speech: {pos}", field="pos", value=pos)
        
        # Check term length
        term = row.get("term", "").strip()
        if len(term) > 100:
            raise ValidationError("Term too long (max 100 characters)", field="term", value=term)
        
        # Validate difficulty if present
        if "difficulty" in row and row["difficulty"]:
            valid_difficulties = {"beginner", "intermediate", "advanced", "expert"}
            diff = row["difficulty"].lower().strip()
            if diff and diff not in valid_difficulties:
                if strict:
                    raise ValidationError(f"Invalid difficulty: {diff}", field="difficulty", value=diff)
                else:
                    result.warnings.append(f"Row {row_index}: Invalid difficulty '{diff}'")
    
    # Database operations
    
    def _create_import_batch(self, source_file: str) -> int:
        """Create import batch record"""
        cursor = self.db_manager.execute(
            """INSERT INTO import_batches (source_file, status, created_at)
            VALUES (?, ?, ?)""",
            (source_file, ImportStatus.PENDING.value, datetime.now().isoformat())
        )
        return cursor.lastrowid
    
    def _update_batch_status(
        self,
        batch_id: int,
        status: ImportStatus,
        result: ImportResult,
    ) -> None:
        """Update batch status"""
        metadata = {
            "imported": result.imported_count,
            "skipped": result.skipped_count,
            "errors": result.error_count,
            "duplicates": result.duplicate_count,
        }
        
        self.db_manager.execute(
            """UPDATE import_batches 
            SET status = ?, completed_at = ?, metadata = ?
            WHERE id = ?""",
            (status.value, datetime.now().isoformat(), json.dumps(metadata), batch_id)
        )
    
    def _process_batch(
        self,
        rows: List[Dict[str, str]],
        batch_id: int,
        result: ImportResult,
        skip_duplicates: bool,
    ) -> None:
        """Process a batch of rows"""
        for row in rows:
            try:
                # Create vocabulary item
                item = VocabularyItem(
                    term=row["term"].strip(),
                    pos=row.get("pos", "").strip(),
                    definition=row.get("definition", "").strip() or None,
                    example=row.get("example", "").strip() or None,
                    difficulty=row.get("difficulty", "").strip() or None,
                    tags=self._parse_tags(row.get("tags", "")),
                    notes=row.get("notes", "").strip() or None,
                )
                
                # Check for duplicates
                if self.config.enable_duplicate_detection:
                    if self._is_duplicate(item.term, item.pos):
                        if skip_duplicates:
                            result.skipped_count += 1
                            result.duplicate_count += 1
                            continue
                        else:
                            raise ValidationError(f"Duplicate entry: {item.term}")
                
                # Insert item
                item_id = self._insert_vocabulary_item(item, batch_id)
                result.imported_count += 1
                
            except Exception as e:
                logger.error(f"Failed to process row: {e}")
                result.error_count += 1
                result.errors.append({
                    "row": row,
                    "error": str(e)
                })
    
    def _process_batch_with_retry(
        self,
        rows: List[Dict[str, str]],
        batch_id: int,
        result: ImportResult,
        skip_duplicates: bool,
    ) -> None:
        """Process batch with retry mechanism"""
        if not self.config.enable_retry_mechanism:
            return self._process_batch(rows, batch_id, result, skip_duplicates)
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                self._process_batch(rows, batch_id, result, skip_duplicates)
                return
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                logger.warning(f"Batch processing failed, retrying ({retry_count}/{max_retries}): {e}")
                time.sleep(2 ** retry_count)  # Exponential backoff
    
    def _insert_vocabulary_item(
        self,
        item: VocabularyItem,
        batch_id: int,
    ) -> int:
        """Insert vocabulary item into database"""
        cursor = self.db_manager.execute(
            """INSERT INTO vocabulary (
                term, pos, definition, example, difficulty, tags, notes,
                import_batch_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item.term,
                item.pos,
                item.definition,
                item.example,
                item.difficulty,
                json.dumps(item.tags) if item.tags else None,
                item.notes,
                batch_id,
                datetime.now().isoformat(),
            )
        )
        return cursor.lastrowid
    
    def _is_duplicate(self, term: str, pos: str) -> bool:
        """Check if term already exists"""
        result = self.db_manager.execute(
            "SELECT COUNT(*) FROM vocabulary WHERE term = ? AND pos = ?",
            (term, pos)
        ).fetchone()
        return result[0] > 0
    
    # Utility methods
    
    def _detect_encoding(self, file_path: Path) -> str:
        """Detect file encoding"""
        if self.config.encoding:
            return self.config.encoding
        
        try:
            import chardet
            with open(file_path, 'rb') as f:
                result = chardet.detect(f.read(10000))
                return result['encoding'] or 'utf-8'
        except ImportError:
            return 'utf-8'
    
    def _read_csv(
        self,
        file_path: Path,
        encoding: str,
    ) -> List[Dict[str, str]]:
        """Read CSV file"""
        rows = []
        with open(file_path, 'r', encoding=encoding) as f:
            reader = csv.DictReader(f, delimiter=self.config.delimiter)
            for row in reader:
                rows.append(row)
        return rows
    
    def _parse_tags(self, tags_str: str) -> List[str]:
        """Parse tags from string"""
        if not tags_str:
            return []
        
        # Support comma or semicolon separated
        if ';' in tags_str:
            tags = tags_str.split(';')
        else:
            tags = tags_str.split(',')
        
        return [t.strip() for t in tags if t.strip()]
    
    def _find_similar_column(self, target: str, columns: List[str]) -> Optional[str]:
        """Find similar column name"""
        # Simple similarity check
        for col in columns:
            if target in col or col in target:
                return col
        
        # Check common variations
        variations = {
            "term": ["word", "vocabulary", "vocab"],
            "pos": ["part_of_speech", "type", "category"],
            "definition": ["meaning", "def", "description"],
        }
        
        for var in variations.get(target, []):
            if var in columns:
                return var
        
        return None
    
    def _check_duplicates_in_file(
        self,
        file_path: Path,
        encoding: str,
    ) -> List[Tuple[str, str]]:
        """Check for duplicates within the file"""
        seen = set()
        duplicates = []
        
        with open(file_path, 'r', encoding=encoding) as f:
            reader = csv.DictReader(f, delimiter=self.config.delimiter)
            for row in reader:
                key = (row.get("term", "").strip(), row.get("pos", "").strip())
                if key in seen:
                    duplicates.append(key)
                else:
                    seen.add(key)
        
        return duplicates
    
    # Status and reporting methods
    
    def get_import_status(self, batch_id: int) -> Dict[str, Any]:
        """Get status of import batch"""
        result = self.db_manager.execute(
            """SELECT id, source_file, status, created_at, completed_at, metadata
            FROM import_batches WHERE id = ?""",
            (batch_id,)
        ).fetchone()
        
        if not result:
            raise ValidationError(f"Batch {batch_id} not found")
        
        return {
            "id": result[0],
            "source_file": result[1],
            "status": result[2],
            "created_at": result[3],
            "completed_at": result[4],
            "metadata": json.loads(result[5]) if result[5] else {},
        }
    
    def get_import_errors(self, batch_id: int) -> List[Dict[str, Any]]:
        """Get errors for import batch"""
        # This would need a separate errors table in production
        # For now, errors are stored in the ImportResult
        return []
    
    def export_validation_report(
        self,
        validation_result: ValidationResult,
        output_path: Union[str, Path],
    ) -> None:
        """Export validation report to file"""
        output_path = Path(output_path)
        
        report = {
            "validated_at": datetime.now().isoformat(),
            "is_valid": validation_result.is_valid,
            "total_rows": validation_result.row_count,
            "valid_rows": validation_result.valid_row_count,
            "error_count": len(validation_result.errors),
            "duplicate_count": validation_result.duplicate_count,
            "warnings": validation_result.warnings,
            "errors": [
                {
                    "row": e.row,
                    "column": e.column,
                    "message": e.message,
                    "value": e.value,
                }
                for e in validation_result.errors
            ],
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
    
    def __del__(self):
        """Cleanup resources"""
        if self._executor:
            self._executor.shutdown(wait=False)


# Factory function
def create_ingress_service(
    db_manager: Any,
    simple_mode: bool = False,
    **kwargs
) -> IngressService:
    """Create ingress service instance"""
    config = IngressConfig(
        enable_validation=not simple_mode,
        enable_progress_tracking=not simple_mode,
        enable_duplicate_detection=not simple_mode,
        enable_retry_mechanism=not simple_mode,
        **kwargs
    )
    return IngressService(db_manager, config)