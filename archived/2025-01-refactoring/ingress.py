"""
Ingress Service for database-driven vocabulary item management.

This module provides functionality to import CSV files into the database
and manage vocabulary items for processing through the pipeline.
"""

import csv
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from contextlib import contextmanager

from .models import VocabularyItem
from .utils import get_logger

logger = get_logger(__name__)


class IngressService:
    """Service for managing vocabulary item ingestion and processing."""
    
    def __init__(self, db_path: str):
        """Initialize the ingress service with database connection."""
        self.db_path = db_path
        self._ensure_tables_exist()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _ensure_tables_exist(self):
        """Ensure required tables exist in the database."""
        migration_path = Path(__file__).parent.parent.parent.parent / "migrations" / "002_add_ingress_tables.sql"
        
        if migration_path.exists():
            with open(migration_path, 'r') as f:
                migration_sql = f.read()
            
            with self._get_connection() as conn:
                # Remove the schema_migrations insert for now
                statements = migration_sql.split(';')
                for statement in statements[:-1]:  # Skip the last schema_migrations insert
                    if statement.strip():
                        conn.execute(statement)
                conn.commit()
    
    def import_csv(self, file_path: str, batch_id: Optional[str] = None) -> str:
        """
        Import CSV file to vocabulary_items table.
        
        Args:
            file_path: Path to CSV file with columns: position, term, type
            batch_id: Optional batch ID (will be generated if not provided)
            
        Returns:
            Batch ID of the import operation
        """
        if not batch_id:
            batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        items = []
        duplicates = []
        
        # Read CSV file
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                items.append({
                    'korean': row['term'],
                    'english': row.get('english', ''),  # Optional field
                    'type': row.get('type', 'word'),
                    'source_file': Path(file_path).name,
                    'import_batch_id': batch_id
                })
        
        # Insert into database
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create import batch record
            cursor.execute("""
                INSERT INTO import_batches (id, source_file, total_items, status)
                VALUES (?, ?, ?, 'pending')
            """, (batch_id, Path(file_path).name, len(items)))
            
            # Insert vocabulary items
            successful = 0
            for item in items:
                try:
                    cursor.execute("""
                        INSERT INTO vocabulary_items 
                        (korean, english, type, source_file, import_batch_id, status)
                        VALUES (?, ?, ?, ?, ?, 'pending')
                    """, (item['korean'], item['english'], item['type'], 
                          item['source_file'], item['import_batch_id']))
                    successful += 1
                except sqlite3.IntegrityError:
                    # Handle duplicates
                    duplicates.append(item['korean'])
                    logger.warning(f"Duplicate item skipped: {item['korean']}")
            
            conn.commit()
            
        logger.info(f"Imported {successful}/{len(items)} items to batch {batch_id}")
        if duplicates:
            logger.warning(f"Skipped {len(duplicates)} duplicate items")
        
        return batch_id
    
    def get_pending_items(self, limit: int = 100, batch_id: Optional[str] = None) -> List[Dict]:
        """
        Retrieve pending items from database.
        
        Args:
            limit: Maximum number of items to retrieve
            batch_id: Optional batch ID to filter by
            
        Returns:
            List of pending vocabulary items
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT id, korean, english, type, import_batch_id
                FROM vocabulary_items
                WHERE status = 'pending'
            """
            params = []
            
            if batch_id:
                query += " AND import_batch_id = ?"
                params.append(batch_id)
            
            query += " ORDER BY id LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            items = []
            
            for row in cursor.fetchall():
                items.append({
                    'id': row['id'],
                    'korean': row['korean'],
                    'english': row['english'],
                    'type': row['type'],
                    'batch_id': row['import_batch_id']
                })
            
            return items
    
    def update_item_status(self, item_id: int, status: str, error_message: Optional[str] = None) -> None:
        """
        Update processing status of an item.
        
        Args:
            item_id: ID of the vocabulary item
            status: New status ('processing', 'completed', 'failed')
            error_message: Optional error message for failed items
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if error_message and status == 'failed':
                # Store error in a separate table or column if needed
                cursor.execute("""
                    UPDATE vocabulary_items 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, item_id))
            else:
                cursor.execute("""
                    UPDATE vocabulary_items 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, item_id))
            
            # Update batch progress
            cursor.execute("""
                SELECT import_batch_id FROM vocabulary_items WHERE id = ?
            """, (item_id,))
            
            batch_id = cursor.fetchone()
            if batch_id:
                self._update_batch_progress(conn, batch_id[0])
            
            conn.commit()
    
    def _update_batch_progress(self, conn: sqlite3.Connection, batch_id: str) -> None:
        """Update batch processing progress."""
        cursor = conn.cursor()
        
        # Get counts
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM vocabulary_items
            WHERE import_batch_id = ?
        """, (batch_id,))
        
        row = cursor.fetchone()
        total = row[0]
        completed = row[1]
        failed = row[2]
        
        # Determine batch status
        if completed + failed == total:
            if failed == 0:
                batch_status = 'completed'
            elif completed == 0:
                batch_status = 'failed'
            else:
                batch_status = 'partial'
            
            cursor.execute("""
                UPDATE import_batches
                SET processed_items = ?, failed_items = ?, status = ?, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (completed, failed, batch_status, batch_id))
        else:
            # Still processing
            cursor.execute("""
                UPDATE import_batches
                SET processed_items = ?, failed_items = ?, status = 'processing'
                WHERE id = ?
            """, (completed, failed, batch_id))
    
    def get_batch_status(self, batch_id: str) -> Dict:
        """
        Get status of an import batch.
        
        Args:
            batch_id: Batch ID to query
            
        Returns:
            Dictionary with batch status information
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM import_batches WHERE id = ?
            """, (batch_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                'id': row['id'],
                'source_file': row['source_file'],
                'total_items': row['total_items'],
                'processed_items': row['processed_items'],
                'failed_items': row['failed_items'],
                'status': row['status'],
                'created_at': row['created_at'],
                'completed_at': row['completed_at'],
                'progress_percentage': (row['processed_items'] + row['failed_items']) / row['total_items'] * 100
                    if row['total_items'] > 0 else 0
            }
    
    def list_batches(self, status: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """
        List import batches.
        
        Args:
            status: Optional status filter
            limit: Maximum number of batches to return
            
        Returns:
            List of batch information dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM import_batches"
            params = []
            
            if status:
                query += " WHERE status = ?"
                params.append(status)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            batches = []
            for row in cursor.fetchall():
                batches.append({
                    'id': row['id'],
                    'source_file': row['source_file'],
                    'total_items': row['total_items'],
                    'processed_items': row['processed_items'],
                    'failed_items': row['failed_items'],
                    'status': row['status'],
                    'created_at': row['created_at'],
                    'completed_at': row['completed_at']
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
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE import_batches
                SET status = 'processing', started_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'pending'
            """, (batch_id,))
            
            conn.commit()
            return cursor.rowcount > 0