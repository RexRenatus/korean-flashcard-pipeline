"""Batch database writer for ordered results"""

import asyncio
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from datetime import datetime
import aiosqlite

from .ordered_collector import ProcessingResult

logger = logging.getLogger(__name__)


class OrderedBatchDatabaseWriter:
    """Write results to database while preserving order"""
    
    def __init__(self, db_path: str):
        """Initialize writer
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.stats = {
            "total_written": 0,
            "batches_written": 0,
            "total_errors": 0
        }
        
        logger.info(f"Batch writer initialized with database: {db_path}")
    
    async def write_batch(self, results: List[ProcessingResult], batch_id: str,
                         metadata: Optional[Dict[str, Any]] = None) -> int:
        """Write batch results in order
        
        Args:
            results: List of processing results
            batch_id: Unique batch identifier
            metadata: Optional batch metadata
            
        Returns:
            Number of successfully written records
        """
        written = 0
        
        async with aiosqlite.connect(self.db_path) as db:
            # Enable WAL mode for better concurrency
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA synchronous=NORMAL")
            
            await db.execute("BEGIN TRANSACTION")
            
            try:
                # Write batch metadata
                await self._write_batch_metadata(db, batch_id, len(results), metadata)
                
                # Write results in order
                for result in results:
                    if await self._write_single_result(db, result, batch_id):
                        written += 1
                
                await db.commit()
                
                self.stats["total_written"] += written
                self.stats["batches_written"] += 1
                
                logger.info(f"Successfully wrote {written}/{len(results)} results for batch {batch_id}")
                
            except Exception as e:
                await db.rollback()
                self.stats["total_errors"] += 1
                logger.error(f"Failed to write batch {batch_id}: {e}")
                raise
        
        return written
    
    async def _write_batch_metadata(self, db: aiosqlite.Connection, batch_id: str,
                                  total_items: int, metadata: Optional[Dict[str, Any]]):
        """Write batch metadata"""
        await db.execute("""
            INSERT OR REPLACE INTO processing_batches (
                batch_id, total_items, status, created_at, updated_at,
                max_concurrent, processing_order
            ) VALUES (?, ?, 'completed', datetime('now'), datetime('now'), ?, ?)
        """, (
            batch_id,
            total_items,
            metadata.get("max_concurrent", 1) if metadata else 1,
            metadata.get("processing_order", "position") if metadata else "position"
        ))
    
    async def _write_single_result(self, db: aiosqlite.Connection, 
                                 result: ProcessingResult, batch_id: str) -> bool:
        """Write a single result maintaining position order
        
        Returns:
            True if written successfully, False otherwise
        """
        if not result.is_success:
            # Log failed item but continue
            logger.warning(f"Skipping failed result for position {result.position}: {result.error}")
            await self._write_error_record(db, result, batch_id)
            return False
        
        try:
            # Parse flashcard data (TSV format)
            flashcard_rows = self._parse_tsv_data(result.flashcard_data)
            
            for row in flashcard_rows:
                await db.execute("""
                    INSERT INTO flashcards (
                        batch_id, position, term, term_number, tab_name,
                        primer, front, back, tags, honorific_level,
                        processing_timestamp, processing_order, processing_time_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?)
                """, (
                    batch_id,
                    result.position,
                    result.term,
                    row.get("term_number", 1),
                    row.get("tab_name", ""),
                    row.get("primer", ""),
                    row.get("front", ""),
                    row.get("back", ""),
                    row.get("tags", ""),
                    row.get("honorific_level", ""),
                    result.position,  # Ensure order is preserved
                    result.processing_time_ms
                ))
            
            logger.debug(f"Wrote {len(flashcard_rows)} flashcards for position {result.position}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing result for position {result.position}: {e}")
            await self._write_error_record(db, result, batch_id, str(e))
            return False
    
    async def _write_error_record(self, db: aiosqlite.Connection,
                                result: ProcessingResult, batch_id: str,
                                additional_error: Optional[str] = None):
        """Write error record for failed processing"""
        error_msg = result.error or additional_error or "Unknown error"
        
        await db.execute("""
            INSERT INTO processing_errors (
                batch_id, position, term, error_message, error_timestamp
            ) VALUES (?, ?, ?, ?, datetime('now'))
        """, (batch_id, result.position, result.term, error_msg))
    
    def _parse_tsv_data(self, tsv_data: str) -> List[Dict[str, str]]:
        """Parse TSV flashcard data into dictionaries"""
        if not tsv_data:
            return []
        
        rows = []
        lines = tsv_data.strip().split('\n')
        
        # Skip header if present
        if lines and lines[0].startswith('position\tterm'):
            lines = lines[1:]
        
        for line in lines:
            if not line.strip():
                continue
                
            parts = line.split('\t')
            if len(parts) >= 9:  # Ensure we have all required fields
                rows.append({
                    "position": parts[0],
                    "term": parts[1],
                    "term_number": parts[2],
                    "tab_name": parts[3],
                    "primer": parts[4],
                    "front": parts[5],
                    "back": parts[6],
                    "tags": parts[7],
                    "honorific_level": parts[8] if len(parts) > 8 else ""
                })
        
        return rows
    
    async def write_to_file(self, results: List[ProcessingResult], output_path: Path):
        """Write results to TSV file in order"""
        # Collect all TSV rows
        all_rows = []
        
        for result in results:
            if result.is_success and result.flashcard_data:
                # Parse TSV data
                lines = result.flashcard_data.strip().split('\n')
                # Skip header if present
                if lines and lines[0].startswith('position\tterm'):
                    lines = lines[1:]
                all_rows.extend(lines)
        
        # Write to file
        header = "position\tterm\tterm_number\ttab_name\tprimer\tfront\tback\ttags\thonorific_level"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(header + '\n')
            f.write('\n'.join(all_rows))
        
        logger.info(f"Wrote {len(all_rows)} flashcards to {output_path}")
        
        return len(all_rows)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get writer statistics"""
        return {
            "total_written": self.stats["total_written"],
            "batches_written": self.stats["batches_written"],
            "total_errors": self.stats["total_errors"],
            "average_per_batch": (
                self.stats["total_written"] / self.stats["batches_written"]
                if self.stats["batches_written"] > 0 else 0
            )
        }