"""
Ingress Service V2 - Uses the reorganized database schema.
Provides functionality to import CSV files and manage vocabulary items.
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .database import DatabaseManager, VocabularyRecord
from .models import VocabularyItem
from .utils import get_logger

logger = get_logger(__name__)


class IngressServiceV2:
    """Service for managing vocabulary item ingestion with new schema"""
    
    def __init__(self, db_path: str):
        """Initialize the ingress service with database manager"""
        self.db = DatabaseManager(db_path)
    
    def import_csv(self, file_path: str, batch_id: Optional[str] = None) -> str:
        """
        Import CSV file to vocabulary_master table.
        
        Args:
            file_path: Path to CSV file with columns: position, term, type, english (optional)
            batch_id: Optional batch ID (will be generated if not provided)
            
        Returns:
            Operation ID of the import
        """
        if not batch_id:
            batch_id = f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        items = []
        
        # Read CSV file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    items.append({
                        'korean': row.get('term', '').strip(),
                        'english': row.get('english', '').strip() or None,
                        'type': row.get('type', 'word').strip(),
                        'position': int(row.get('position', 0))
                    })
        except Exception as e:
            logger.error(f"Failed to read CSV file: {e}")
            raise
        
        if not items:
            logger.warning("No items found in CSV file")
            return batch_id
        
        # Create import operation record
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO import_operations (
                    operation_id, source_file, source_type, total_items, status
                ) VALUES (?, ?, 'csv', ?, 'processing')
            """, (batch_id, Path(file_path).name, len(items)))
            
            import_id = cursor.lastrowid
            conn.commit()
        
        # Process items
        imported = 0
        duplicates = 0
        failed = 0
        
        for item in items:
            try:
                # Check if vocabulary already exists
                existing = self.db.get_vocabulary_by_korean(item['korean'])
                
                if existing:
                    vocab_id = existing.id
                    duplicates += 1
                    import_status = 'duplicate'
                else:
                    # Create new vocabulary record
                    vocab = VocabularyRecord(
                        korean=item['korean'],
                        english=item['english'],
                        type=item['type'],
                        source_reference=Path(file_path).name
                    )
                    vocab_id = self.db.create_vocabulary(vocab)
                    imported += 1
                    import_status = 'imported'
                
                # Create vocabulary_imports link
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO vocabulary_imports (
                            vocabulary_id, import_id, original_position, import_status
                        ) VALUES (?, ?, ?, ?)
                    """, (vocab_id, import_id, item['position'], import_status))
                    conn.commit()
                    
            except Exception as e:
                logger.error(f"Failed to import item {item['korean']}: {e}")
                failed += 1
        
        # Update import operation status
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            status = 'completed' if failed == 0 else 'partial' if imported > 0 else 'failed'
            
            cursor.execute("""
                UPDATE import_operations
                SET imported_items = ?, duplicate_items = ?, failed_items = ?,
                    status = ?, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (imported, duplicates, failed, status, import_id))
            conn.commit()
        
        logger.info(f"Import complete: {imported} imported, {duplicates} duplicates, {failed} failed")
        return batch_id
    
    def get_pending_items(self, limit: int = 100, 
                         batch_id: Optional[str] = None) -> List[Dict]:
        """
        Retrieve pending items from database.
        
        Args:
            limit: Maximum number of items to retrieve
            batch_id: Optional batch ID to filter by
            
        Returns:
            List of pending vocabulary items
        """
        # Get import_id from batch_id if provided
        import_id = None
        if batch_id:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id FROM import_operations WHERE operation_id = ?
                """, (batch_id,))
                row = cursor.fetchone()
                if row:
                    import_id = row[0]
        
        # Get pending vocabulary
        vocab_records = self.db.get_pending_vocabulary(limit, import_id)
        
        # Convert to dictionary format expected by pipeline
        items = []
        for vocab in vocab_records:
            items.append({
                'id': vocab.id,
                'korean': vocab.korean,
                'english': vocab.english,
                'type': vocab.type,
                'batch_id': batch_id
            })
        
        return items
    
    def update_item_status(self, item_id: int, status: str, 
                          error_message: Optional[str] = None) -> None:
        """
        Update processing status of an item.
        
        Args:
            item_id: ID of the vocabulary item
            status: New status ('processing', 'completed', 'failed')
            error_message: Optional error message for failed items
        """
        # Map old status to new task status
        task_status_map = {
            'processing': 'processing',
            'completed': 'completed',
            'failed': 'failed'
        }
        
        # Find or create a task for this vocabulary item
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if task exists
            cursor.execute("""
                SELECT id, task_id FROM processing_tasks 
                WHERE vocabulary_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (item_id,))
            
            row = cursor.fetchone()
            if row:
                task_id = row['task_id']
                self.db.update_task_status(task_id, task_status_map[status])
            else:
                # Create new task if doesn't exist
                from .database import ProcessingTask
                task = ProcessingTask(
                    task_id=f"task_{item_id}_{uuid.uuid4().hex[:8]}",
                    vocabulary_id=item_id,
                    task_type='full_pipeline',
                    status=task_status_map[status]
                )
                self.db.create_task(task)
    
    def get_batch_status(self, batch_id: str) -> Dict:
        """
        Get status of an import batch.
        
        Args:
            batch_id: Batch ID to query
            
        Returns:
            Dictionary with batch status information
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM import_operations WHERE operation_id = ?
            """, (batch_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Calculate progress
            total = row['total_items']
            processed = row['imported_items'] + row['duplicate_items'] + row['failed_items']
            
            return {
                'id': row['operation_id'],
                'source_file': row['source_file'],
                'total_items': total,
                'processed_items': row['imported_items'],
                'duplicate_items': row['duplicate_items'],
                'failed_items': row['failed_items'],
                'status': row['status'],
                'created_at': row['created_at'],
                'completed_at': row['completed_at'],
                'progress_percentage': (processed / total * 100) if total > 0 else 0
            }
    
    def list_batches(self, status: Optional[str] = None, 
                    limit: int = 20) -> List[Dict]:
        """
        List import batches.
        
        Args:
            status: Optional status filter
            limit: Maximum number of batches to return
            
        Returns:
            List of batch information dictionaries
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM v_import_summary"
            params = []
            
            if status:
                query += " WHERE status = ?"
                params.append(status)
            
            query += " LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            batches = []
            for row in cursor.fetchall():
                batches.append({
                    'id': row['operation_id'],
                    'source_file': row['source_file'],
                    'total_items': row['total_items'],
                    'processed_items': row['imported_items'],
                    'duplicate_items': row['duplicate_items'],
                    'failed_items': row['failed_items'],
                    'status': row['status'],
                    'created_at': row['created_at'],
                    'completed_at': row['completed_at'],
                    'success_rate': row['success_rate']
                })
            
            return batches
    
    def mark_batch_for_processing(self, batch_id: str) -> bool:
        """
        Mark a batch as ready for processing.
        
        Args:
            batch_id: Batch ID to mark
            
        Returns:
            True if successful, False otherwise
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Update operation status
            cursor.execute("""
                UPDATE import_operations
                SET status = 'processing', started_at = CURRENT_TIMESTAMP
                WHERE operation_id = ? AND status = 'pending'
            """, (batch_id,))
            
            if cursor.rowcount == 0:
                return False
            
            # Get all vocabulary items for this batch
            cursor.execute("""
                SELECT vi.vocabulary_id
                FROM vocabulary_imports vi
                JOIN import_operations io ON vi.import_id = io.id
                WHERE io.operation_id = ?
                AND vi.import_status = 'imported'
            """, (batch_id,))
            
            # Create processing tasks for each vocabulary item
            from .database import ProcessingTask
            for row in cursor.fetchall():
                task = ProcessingTask(
                    task_id=f"batch_{batch_id}_vocab_{row[0]}",
                    vocabulary_id=row[0],
                    task_type='full_pipeline',
                    status='pending'
                )
                self.db.create_task(task)
            
            conn.commit()
            return True
    
    def get_vocabulary_for_processing(self, batch_id: Optional[str] = None,
                                    limit: int = 100) -> List[VocabularyItem]:
        """
        Get vocabulary items ready for processing as VocabularyItem objects.
        
        Args:
            batch_id: Optional batch ID filter
            limit: Maximum items to return
            
        Returns:
            List of VocabularyItem objects
        """
        items = self.get_pending_items(limit, batch_id)
        
        vocab_items = []
        for item in items:
            vocab_items.append(VocabularyItem(
                position=item['id'],
                term=item['korean'],
                type=item.get('type', 'word')
            ))
        
        return vocab_items