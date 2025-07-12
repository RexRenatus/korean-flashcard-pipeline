"""
Enhanced Ingress Service with comprehensive validation and progress tracking.
Uses the latest database schema with proper error handling and batch management.
"""

import csv
import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Iterator
from datetime import datetime
from dataclasses import dataclass, field
import hashlib
from collections import defaultdict
import asyncio
from concurrent.futures import ThreadPoolExecutor
import chardet

from .database import (
    ValidatedDatabaseManager,
    EnhancedDatabaseManager,
    VocabularyRecord
)
from .models import VocabularyItem
from .exceptions import ValidationError, IngressError
from .database.validation import DataValidator, ValidationRule, ValidationType
from .utils import get_logger

logger = get_logger(__name__)


@dataclass
class ImportProgress:
    """Track import progress with detailed metrics"""
    total_rows: int = 0
    processed_rows: int = 0
    successful_rows: int = 0
    failed_rows: int = 0
    duplicate_rows: int = 0
    validation_errors: List[Dict[str, Any]] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds"""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    @property
    def rows_per_second(self) -> float:
        """Calculate processing rate"""
        if self.elapsed_seconds > 0:
            return self.processed_rows / self.elapsed_seconds
        return 0
    
    @property
    def estimated_remaining_seconds(self) -> Optional[float]:
        """Estimate remaining time"""
        if self.rows_per_second > 0 and self.processed_rows < self.total_rows:
            remaining = self.total_rows - self.processed_rows
            return remaining / self.rows_per_second
        return None
    
    @property
    def progress_percentage(self) -> float:
        """Get progress percentage"""
        if self.total_rows > 0:
            return (self.processed_rows / self.total_rows) * 100
        return 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "total_rows": self.total_rows,
            "processed_rows": self.processed_rows,
            "successful_rows": self.successful_rows,
            "failed_rows": self.failed_rows,
            "duplicate_rows": self.duplicate_rows,
            "validation_errors": self.validation_errors[:100],  # Limit to first 100
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "elapsed_seconds": self.elapsed_seconds,
            "rows_per_second": self.rows_per_second,
            "estimated_remaining_seconds": self.estimated_remaining_seconds,
            "progress_percentage": self.progress_percentage
        }


@dataclass
class ImportBatch:
    """Represents an import batch with metadata"""
    batch_id: str
    source_file: str
    total_items: int
    status: str = "pending"  # pending, processing, completed, failed, cancelled
    progress: ImportProgress = field(default_factory=ImportProgress)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "batch_id": self.batch_id,
            "source_file": self.source_file,
            "total_items": self.total_items,
            "status": self.status,
            "progress": self.progress.to_dict(),
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "metadata": self.metadata
        }


class CSVValidator:
    """Validates and parses CSV files for vocabulary import"""
    
    # Column mappings for different CSV formats
    COLUMN_MAPPINGS = {
        # Standard format
        "term": ["term", "korean", "word", "vocabulary", "hangul", "Hangul"],
        "meaning": ["meaning", "english", "definition", "translation", "Definition"],
        "reading": ["reading", "pronunciation", "romanization", "IPA_Pronunciation"],
        "pos": ["pos", "part_of_speech", "type", "Word_Type"],
        "level": ["level", "difficulty", "difficulty_level", "TOPIK_Level"],
        "tags": ["tags", "categories", "labels"],
        "hanja": ["hanja", "chinese", "chinese_characters"],
        "notes": ["notes", "comments", "memo"],
        "example_kr": ["example_kr", "korean_example", "example_korean", "Example_Sentence"],
        "example_en": ["example_en", "english_example", "example_english", "Example_Sentence_Translation"],
        "frequency": ["frequency", "frequency_rank", "rank"],
        "source": ["source", "source_reference", "reference"]
    }
    
    REQUIRED_COLUMNS = {"term"}  # Only term is absolutely required
    
    def __init__(self):
        self.validator = DataValidator()
        self.column_map = {}
    
    def detect_encoding(self, file_path: Path) -> str:
        """Detect file encoding with chardet"""
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)  # Read first 10KB
            result = chardet.detect(raw_data)
            encoding = result.get('encoding', 'utf-8')
            confidence = result.get('confidence', 0)
            
            logger.info(f"Detected encoding: {encoding} (confidence: {confidence:.2f})")
            
            # Use UTF-8 if confidence is low
            if confidence < 0.7:
                logger.warning("Low confidence in encoding detection, using UTF-8")
                return 'utf-8'
            
            return encoding
    
    def normalize_headers(self, headers: List[str]) -> Dict[str, str]:
        """Normalize CSV headers to standard field names"""
        self.column_map = {}
        normalized_headers = [h.lower().strip() for h in headers]
        
        for standard_field, variations in self.COLUMN_MAPPINGS.items():
            for header_idx, header in enumerate(normalized_headers):
                if header in variations:
                    self.column_map[headers[header_idx]] = standard_field
                    break
        
        return self.column_map
    
    def validate_headers(self, headers: List[str]) -> Tuple[bool, Optional[str]]:
        """Validate CSV headers and build column mapping"""
        # Normalize headers
        self.normalize_headers(headers)
        
        # Check for required columns
        found_columns = set(self.column_map.values())
        missing = self.REQUIRED_COLUMNS - found_columns
        
        if missing:
            return False, f"Missing required columns: {', '.join(missing)}"
        
        # Log column mapping
        logger.info(f"Column mapping: {self.column_map}")
        
        return True, None
    
    def validate_row(self, row: Dict[str, str], row_number: int) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """Validate and normalize a single CSV row"""
        try:
            # Map to standard fields
            normalized_row = {}
            for csv_field, standard_field in self.column_map.items():
                if csv_field in row:
                    normalized_row[standard_field] = row[csv_field]
            
            # Check required fields
            if not normalized_row.get("term", "").strip():
                return False, f"Row {row_number}: Missing required field 'term'", None
            
            # Validate and sanitize data
            validated_row = {}
            
            # Term validation (Korean)
            term = self.validator.sanitize_string(normalized_row["term"])
            if len(term) > 100:
                return False, f"Row {row_number}: Term too long (max 100 chars)", None
            validated_row["korean"] = term
            
            # Meaning validation (English)
            if "meaning" in normalized_row:
                meaning = self.validator.sanitize_string(normalized_row.get("meaning", ""))
                if meaning and len(meaning) > 500:
                    return False, f"Row {row_number}: Meaning too long (max 500 chars)", None
                validated_row["english"] = meaning
            
            # Reading/Romanization
            if "reading" in normalized_row:
                validated_row["romanization"] = self.validator.sanitize_string(
                    normalized_row.get("reading", "")
                )
            
            # Part of speech / Type
            if "pos" in normalized_row:
                pos = normalized_row.get("pos", "word").lower()
                valid_types = ["word", "phrase", "idiom", "grammar", "noun", "verb", 
                              "adjective", "adverb", "particle"]
                if pos in valid_types:
                    validated_row["type"] = pos
                else:
                    validated_row["type"] = "word"
            else:
                validated_row["type"] = "word"
            
            # Hanja
            if "hanja" in normalized_row:
                validated_row["hanja"] = self.validator.sanitize_string(
                    normalized_row.get("hanja", "")
                )
            
            # Difficulty level
            if "level" in normalized_row and normalized_row["level"].strip():
                try:
                    level = int(normalized_row["level"])
                    if 1 <= level <= 10:
                        validated_row["difficulty_level"] = level
                    else:
                        return False, f"Row {row_number}: Difficulty level must be 1-10", None
                except ValueError:
                    return False, f"Row {row_number}: Invalid difficulty level", None
            
            # Frequency rank
            if "frequency" in normalized_row and normalized_row["frequency"].strip():
                try:
                    rank = int(normalized_row["frequency"])
                    if rank > 0:
                        validated_row["frequency_rank"] = rank
                    else:
                        return False, f"Row {row_number}: Frequency rank must be positive", None
                except ValueError:
                    return False, f"Row {row_number}: Invalid frequency rank", None
            
            # Tags processing
            if "tags" in normalized_row and normalized_row["tags"].strip():
                tags = [t.strip() for t in normalized_row["tags"].split(",") if t.strip()]
                validated_row["tags"] = tags
            
            # Notes
            if "notes" in normalized_row:
                validated_row["notes"] = self.validator.sanitize_string(
                    normalized_row.get("notes", "")
                )
            
            # Source reference
            if "source" in normalized_row:
                validated_row["source_reference"] = self.validator.sanitize_string(
                    normalized_row.get("source", "")
                )
            
            return True, None, validated_row
            
        except Exception as e:
            return False, f"Row {row_number}: Validation error - {str(e)}", None


class DuplicateDetector:
    """Detects duplicate vocabulary items with fuzzy matching"""
    
    def __init__(self):
        self.term_index = {}  # term_hash -> (id, term)
        self.content_index = {}  # content_hash -> id
    
    def _normalize_korean(self, text: str) -> str:
        """Normalize Korean text for comparison"""
        # Remove spaces and convert to lowercase
        normalized = text.lower().strip()
        # Remove spaces between Korean characters
        if any('\uAC00' <= c <= '\uD7AF' for c in normalized):
            normalized = ''.join(normalized.split())
        return normalized
    
    def _generate_term_hash(self, term: str) -> str:
        """Generate hash for term comparison"""
        normalized = self._normalize_korean(term)
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _generate_content_hash(self, item: Dict[str, Any]) -> str:
        """Generate hash for full content comparison"""
        # Create deterministic string representation
        content_parts = [
            self._normalize_korean(item.get("korean", "")),
            item.get("english", "").lower().strip(),
            item.get("type", "").lower().strip()
        ]
        content = "|".join(content_parts)
        return hashlib.md5(content.encode()).hexdigest()
    
    def check_duplicate(self, item: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Check if item is duplicate
        Returns: (is_duplicate, reason, existing_id)
        """
        term_hash = self._generate_term_hash(item.get("korean", ""))
        content_hash = self._generate_content_hash(item)
        
        # Check exact term match
        if term_hash in self.term_index:
            existing_id, existing_term = self.term_index[term_hash]
            
            # Check if content is also the same
            if content_hash in self.content_index:
                return True, "Exact duplicate found", existing_id
            else:
                return True, f"Term '{existing_term}' already exists with different meaning", existing_id
        
        return False, None, None
    
    def add_item(self, item_id: int, item: Dict[str, Any]):
        """Add item to duplicate tracking"""
        term_hash = self._generate_term_hash(item.get("korean", ""))
        content_hash = self._generate_content_hash(item)
        
        self.term_index[term_hash] = (item_id, item.get("korean", ""))
        self.content_index[content_hash] = item_id
    
    def load_existing_vocabulary(self, db_manager: ValidatedDatabaseManager):
        """Load existing vocabulary from database for duplicate checking"""
        with db_manager.db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, korean, english, type 
                FROM vocabulary_master 
                WHERE is_active = 1
            """)
            
            count = 0
            for row in cursor:
                item = {
                    "korean": row["korean"],
                    "english": row["english"] or "",
                    "type": row["type"] or "word"
                }
                self.add_item(row["id"], item)
                count += 1
            
            logger.info(f"Loaded {count} existing vocabulary items for duplicate checking")


class IngressServiceEnhanced:
    """Enhanced ingress service with comprehensive features"""
    
    def __init__(self, db_manager: ValidatedDatabaseManager):
        self.db_manager = db_manager
        self.csv_validator = CSVValidator()
        self.active_batches: Dict[str, ImportBatch] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._progress_callbacks: Dict[str, callable] = {}
    
    def create_import_batch(self, source_file: str, metadata: Optional[Dict] = None) -> str:
        """Create a new import batch"""
        batch_id = f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        batch = ImportBatch(
            batch_id=batch_id,
            source_file=source_file,
            total_items=0,
            metadata=metadata or {}
        )
        
        self.active_batches[batch_id] = batch
        
        # Store in database
        with self.db_manager.db_manager.get_connection() as conn:
            conn.execute("""
                INSERT INTO import_operations 
                (operation_id, source_file, source_type, total_items, status, metadata)
                VALUES (?, ?, 'csv', ?, ?, ?)
            """, (
                batch_id,
                source_file,
                batch.total_items,
                batch.status,
                json.dumps(batch.metadata)
            ))
            conn.commit()
        
        logger.info(f"Created import batch: {batch_id}")
        return batch_id
    
    def import_csv(self, file_path: str, 
                   batch_size: int = 100,
                   skip_duplicates: bool = True,
                   validate_only: bool = False,
                   progress_callback: Optional[callable] = None) -> ImportBatch:
        """
        Import vocabulary from CSV file
        
        Args:
            file_path: Path to CSV file
            batch_size: Number of items to process in each batch
            skip_duplicates: Whether to skip duplicate items
            validate_only: Only validate without importing
            progress_callback: Function to call with progress updates
            
        Returns:
            ImportBatch with results
        """
        file_path = Path(file_path)
        
        # Validate file
        if not file_path.exists():
            raise IngressError(f"File not found: {file_path}")
        
        if not file_path.suffix.lower() == '.csv':
            raise IngressError(f"Not a CSV file: {file_path}")
        
        # Create batch
        batch_id = self.create_import_batch(str(file_path))
        batch = self.active_batches[batch_id]
        
        # Register progress callback
        if progress_callback:
            self._progress_callbacks[batch_id] = progress_callback
        
        try:
            # Detect encoding
            encoding = self.csv_validator.detect_encoding(file_path)
            
            # Count total rows
            with open(file_path, 'r', encoding=encoding) as f:
                batch.total_items = sum(1 for _ in f) - 1  # Subtract header
                batch.progress.total_rows = batch.total_items
            
            logger.info(f"Starting import of {batch.total_items} items from {file_path}")
            
            # Initialize duplicate detector
            detector = DuplicateDetector()
            if skip_duplicates:
                detector.load_existing_vocabulary(self.db_manager)
            
            # Update batch status
            batch.status = "processing"
            self._update_batch_status(batch_id, "processing")
            
            # Process file
            with open(file_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                
                # Validate headers
                headers_valid, header_msg = self.csv_validator.validate_headers(reader.fieldnames)
                if not headers_valid:
                    raise IngressError(header_msg)
                
                if header_msg:  # Warning message
                    logger.warning(header_msg)
                
                # Process in batches
                buffer = []
                
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
                    batch.progress.processed_rows += 1
                    
                    # Validate row
                    valid, error_msg, validated_data = self.csv_validator.validate_row(row, row_num)
                    
                    if not valid:
                        batch.progress.failed_rows += 1
                        batch.progress.validation_errors.append({
                            "row": row_num,
                            "error": error_msg,
                            "data": row
                        })
                        continue
                    
                    # Check duplicates
                    if skip_duplicates:
                        is_dup, dup_msg, existing_id = detector.check_duplicate(validated_data)
                        if is_dup:
                            batch.progress.duplicate_rows += 1
                            batch.progress.validation_errors.append({
                                "row": row_num,
                                "error": f"Duplicate: {dup_msg}",
                                "data": row,
                                "existing_id": existing_id
                            })
                            continue
                    
                    # Add metadata
                    validated_data["_row_number"] = row_num
                    validated_data["_batch_id"] = batch_id
                    
                    # Add to buffer
                    buffer.append(validated_data)
                    
                    # Process batch when full
                    if len(buffer) >= batch_size:
                        if not validate_only:
                            self._process_buffer(buffer, batch, detector)
                        else:
                            batch.progress.successful_rows += len(buffer)
                        buffer = []
                        
                        # Progress callback
                        self._report_progress(batch_id)
                
                # Process remaining items
                if buffer:
                    if not validate_only:
                        self._process_buffer(buffer, batch, detector)
                    else:
                        batch.progress.successful_rows += len(buffer)
                    self._report_progress(batch_id)
            
            # Mark complete
            batch.status = "completed" if batch.progress.failed_rows == 0 else "partial"
            batch.completed_at = datetime.now()
            batch.progress.end_time = datetime.now()
            
            self._update_batch_status(batch_id, batch.status)
            
            # Final progress report
            self._report_progress(batch_id)
            
            logger.info(
                f"Import completed: {batch.progress.successful_rows} successful, "
                f"{batch.progress.duplicate_rows} duplicates, "
                f"{batch.progress.failed_rows} failed"
            )
            
            return batch
            
        except Exception as e:
            logger.error(f"Import failed: {str(e)}")
            batch.status = "failed"
            batch.error_message = str(e)
            batch.completed_at = datetime.now()
            batch.progress.end_time = datetime.now()
            self._update_batch_status(batch_id, "failed", str(e))
            raise
        finally:
            # Clean up
            if batch_id in self._progress_callbacks:
                del self._progress_callbacks[batch_id]
    
    def _process_buffer(self, buffer: List[Dict], batch: ImportBatch, detector: DuplicateDetector):
        """Process a buffer of validated items"""
        import_id = self._get_import_id(batch.batch_id)
        
        for item in buffer:
            try:
                row_number = item.pop("_row_number", 0)
                batch_id = item.pop("_batch_id", batch.batch_id)
                
                # Create vocabulary record
                vocab = VocabularyRecord(
                    korean=item["korean"],
                    english=item.get("english"),
                    romanization=item.get("romanization"),
                    hanja=item.get("hanja"),
                    type=item.get("type", "word"),
                    category=item.get("category"),
                    subcategory=item.get("subcategory"),
                    difficulty_level=item.get("difficulty_level"),
                    frequency_rank=item.get("frequency_rank"),
                    source_reference=item.get("source_reference", batch.source_file),
                    notes=item.get("notes")
                )
                
                # Create vocabulary item
                vocab_id = self.db_manager.create_vocabulary_validated(vocab.__dict__)
                
                # Track in duplicate detector
                detector.add_item(vocab_id, item)
                
                # Create import link
                with self.db_manager.db_manager.get_connection() as conn:
                    conn.execute("""
                        INSERT INTO vocabulary_imports
                        (vocabulary_id, import_id, original_position, import_status)
                        VALUES (?, ?, ?, ?)
                    """, (vocab_id, import_id, row_number, "imported"))
                    conn.commit()
                
                batch.progress.successful_rows += 1
                
            except ValidationError as e:
                batch.progress.failed_rows += 1
                batch.progress.validation_errors.append({
                    "row": item.get("_row_number", "unknown"),
                    "error": f"Validation error: {str(e)}",
                    "data": item
                })
            except Exception as e:
                batch.progress.failed_rows += 1
                batch.progress.validation_errors.append({
                    "row": item.get("_row_number", "unknown"),
                    "error": f"Import error: {str(e)}",
                    "data": item
                })
    
    def _get_import_id(self, batch_id: str) -> int:
        """Get import operation ID from batch ID"""
        with self.db_manager.db_manager.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id FROM import_operations WHERE operation_id = ?",
                (batch_id,)
            )
            row = cursor.fetchone()
            return row["id"] if row else None
    
    def _update_batch_status(self, batch_id: str, status: str, error_message: Optional[str] = None):
        """Update batch status in database"""
        batch = self.active_batches.get(batch_id)
        if not batch:
            return
        
        with self.db_manager.db_manager.get_connection() as conn:
            if status in ["completed", "failed", "partial"]:
                conn.execute("""
                    UPDATE import_operations
                    SET status = ?, 
                        completed_at = CURRENT_TIMESTAMP,
                        imported_items = ?,
                        duplicate_items = ?,
                        failed_items = ?,
                        error_message = ?
                    WHERE operation_id = ?
                """, (
                    status,
                    batch.progress.successful_rows,
                    batch.progress.duplicate_rows,
                    batch.progress.failed_rows,
                    error_message,
                    batch_id
                ))
            else:
                conn.execute("""
                    UPDATE import_operations
                    SET status = ?, started_at = CURRENT_TIMESTAMP
                    WHERE operation_id = ?
                """, (status, batch_id))
            conn.commit()
    
    def _report_progress(self, batch_id: str):
        """Report progress to registered callback"""
        if batch_id in self._progress_callbacks:
            batch = self.active_batches.get(batch_id)
            if batch:
                try:
                    self._progress_callbacks[batch_id](batch.progress)
                except Exception as e:
                    logger.error(f"Progress callback error: {e}")
    
    def get_batch_status(self, batch_id: str) -> Optional[ImportBatch]:
        """Get status of an import batch"""
        # Check active batches first
        if batch_id in self.active_batches:
            return self.active_batches[batch_id]
        
        # Load from database
        with self.db_manager.db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM import_operations WHERE operation_id = ?
            """, (batch_id,))
            row = cursor.fetchone()
            
            if row:
                batch = ImportBatch(
                    batch_id=row["operation_id"],
                    source_file=row["source_file"],
                    total_items=row["total_items"],
                    status=row["status"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                    error_message=row["error_message"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {}
                )
                
                # Reconstruct progress
                batch.progress.total_rows = row["total_items"]
                batch.progress.successful_rows = row["imported_items"] or 0
                batch.progress.duplicate_rows = row["duplicate_items"] or 0
                batch.progress.failed_rows = row["failed_items"] or 0
                batch.progress.processed_rows = (
                    batch.progress.successful_rows + 
                    batch.progress.duplicate_rows + 
                    batch.progress.failed_rows
                )
                
                return batch
        
        return None
    
    def list_batches(self, status: Optional[str] = None, 
                     limit: int = 50, offset: int = 0) -> List[ImportBatch]:
        """List import batches with filtering"""
        with self.db_manager.db_manager.get_connection() as conn:
            query = """
                SELECT * FROM import_operations
                WHERE 1=1
            """
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor = conn.execute(query, params)
            batches = []
            
            for row in cursor:
                batch = ImportBatch(
                    batch_id=row["operation_id"],
                    source_file=row["source_file"],
                    total_items=row["total_items"],
                    status=row["status"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                    error_message=row["error_message"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {}
                )
                
                # Add progress info
                batch.progress.total_rows = row["total_items"]
                batch.progress.successful_rows = row["imported_items"] or 0
                batch.progress.duplicate_rows = row["duplicate_items"] or 0
                batch.progress.failed_rows = row["failed_items"] or 0
                
                batches.append(batch)
            
            return batches
    
    def cancel_batch(self, batch_id: str) -> bool:
        """Cancel an active import batch"""
        if batch_id in self.active_batches:
            batch = self.active_batches[batch_id]
            if batch.status == "processing":
                batch.status = "cancelled"
                batch.completed_at = datetime.now()
                self._update_batch_status(batch_id, "cancelled")
                logger.info(f"Cancelled batch: {batch_id}")
                return True
        return False
    
    def cleanup_old_batches(self, days: int = 30) -> int:
        """Clean up old import batches and their data"""
        with self.db_manager.db_manager.get_connection() as conn:
            # Get old batch IDs
            cursor = conn.execute("""
                SELECT id FROM import_operations
                WHERE completed_at < datetime('now', ? || ' days')
            """, (-days,))
            
            old_ids = [row["id"] for row in cursor]
            
            if not old_ids:
                return 0
            
            # Delete import links
            conn.execute("""
                DELETE FROM vocabulary_imports
                WHERE import_id IN ({})
            """.format(','.join('?' * len(old_ids))), old_ids)
            
            # Delete operations
            conn.execute("""
                DELETE FROM import_operations
                WHERE id IN ({})
            """.format(','.join('?' * len(old_ids))), old_ids)
            
            conn.commit()
            
            logger.info(f"Cleaned up {len(old_ids)} old import batches")
            return len(old_ids)
    
    def get_batch_errors(self, batch_id: str, limit: int = 100) -> List[Dict]:
        """Get detailed errors from a batch"""
        batch = self.get_batch_status(batch_id)
        if not batch:
            return []
        
        # Return validation errors (limited)
        return batch.progress.validation_errors[:limit]
    
    def retry_failed_items(self, batch_id: str) -> ImportBatch:
        """Retry failed items from a batch"""
        # Get original batch
        original_batch = self.get_batch_status(batch_id)
        if not original_batch:
            raise IngressError(f"Batch not found: {batch_id}")
        
        if not original_batch.progress.validation_errors:
            raise IngressError("No failed items to retry")
        
        # Extract failed items data
        failed_items = []
        for error in original_batch.progress.validation_errors:
            if "data" in error and error.get("error", "").startswith("Duplicate:") == False:
                failed_items.append(error["data"])
        
        if not failed_items:
            raise IngressError("No retryable items found")
        
        # Create retry batch
        retry_batch_id = self.create_import_batch(
            f"retry_{batch_id}",
            metadata={
                "parent_batch": batch_id,
                "retry": True,
                "retry_count": len(failed_items)
            }
        )
        
        retry_batch = self.active_batches[retry_batch_id]
        retry_batch.total_items = len(failed_items)
        retry_batch.progress.total_rows = len(failed_items)
        
        # Process items
        retry_batch.status = "processing"
        self._update_batch_status(retry_batch_id, "processing")
        
        # Initialize duplicate detector
        detector = DuplicateDetector()
        detector.load_existing_vocabulary(self.db_manager)
        
        # Process all items
        validated_items = []
        for idx, item in enumerate(failed_items):
            retry_batch.progress.processed_rows += 1
            
            # Re-validate with new row number
            valid, error_msg, validated_data = self.csv_validator.validate_row(
                item, idx + 1
            )
            
            if valid:
                validated_data["_row_number"] = idx + 1
                validated_data["_batch_id"] = retry_batch_id
                validated_items.append(validated_data)
            else:
                retry_batch.progress.failed_rows += 1
                retry_batch.progress.validation_errors.append({
                    "row": idx + 1,
                    "error": error_msg,
                    "data": item
                })
        
        # Process valid items
        if validated_items:
            self._process_buffer(validated_items, retry_batch, detector)
        
        # Complete
        retry_batch.status = "completed" if retry_batch.progress.failed_rows == 0 else "partial"
        retry_batch.completed_at = datetime.now()
        retry_batch.progress.end_time = datetime.now()
        self._update_batch_status(retry_batch_id, retry_batch.status)
        
        logger.info(
            f"Retry completed: {retry_batch.progress.successful_rows} successful, "
            f"{retry_batch.progress.failed_rows} failed"
        )
        
        return retry_batch
    
    def export_batch_report(self, batch_id: str, output_path: Optional[str] = None) -> str:
        """Export detailed batch report"""
        batch = self.get_batch_status(batch_id)
        if not batch:
            raise IngressError(f"Batch not found: {batch_id}")
        
        if not output_path:
            output_path = f"import_report_{batch_id}.json"
        
        report = {
            "batch": batch.to_dict(),
            "summary": {
                "total_items": batch.progress.total_rows,
                "successful": batch.progress.successful_rows,
                "duplicates": batch.progress.duplicate_rows,
                "failed": batch.progress.failed_rows,
                "success_rate": (
                    batch.progress.successful_rows / batch.progress.total_rows * 100
                    if batch.progress.total_rows > 0 else 0
                ),
                "processing_time": batch.progress.elapsed_seconds,
                "items_per_second": batch.progress.rows_per_second
            },
            "errors": batch.progress.validation_errors
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported batch report to: {output_path}")
        return output_path
    
    async def import_csv_async(self, file_path: str, **kwargs) -> ImportBatch:
        """Async wrapper for CSV import"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self.import_csv,
            file_path,
            **kwargs
        )
    
    def close(self):
        """Cleanup resources"""
        self._executor.shutdown(wait=True)