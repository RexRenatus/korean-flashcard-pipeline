"""
Database Backup Manager for automated snapshots and recovery.
Provides backup, restore, and rollback functionality for SQLite database.
"""

import os
import shutil
import sqlite3
import gzip
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from contextlib import contextmanager

from ..utils import get_logger

logger = get_logger(__name__)


class BackupManager:
    """Manages database backups with automated snapshots and rollback support."""
    
    def __init__(self, db_path: str, backup_dir: Optional[str] = None):
        """
        Initialize backup manager.
        
        Args:
            db_path: Path to the SQLite database
            backup_dir: Directory for storing backups (default: ./backups)
        """
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir or "backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        # Create metadata file for tracking backups
        self.metadata_file = self.backup_dir / "backup_metadata.json"
        self._init_metadata()
    
    def _init_metadata(self):
        """Initialize backup metadata file if it doesn't exist."""
        if not self.metadata_file.exists():
            metadata = {
                "backups": [],
                "last_backup": None,
                "total_backups": 0
            }
            self._save_metadata(metadata)
    
    def _load_metadata(self) -> Dict:
        """Load backup metadata from file."""
        try:
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
            return {"backups": [], "last_backup": None, "total_backups": 0}
    
    def _save_metadata(self, metadata: Dict):
        """Save backup metadata to file."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
    
    def create_backup(self, description: str = "", compress: bool = True) -> Optional[str]:
        """
        Create a database backup with optional compression.
        
        Args:
            description: Optional description for the backup
            compress: Whether to compress the backup with gzip
            
        Returns:
            Path to the backup file or None if failed
        """
        try:
            # Generate backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"
            
            if compress:
                backup_path = self.backup_dir / f"{backup_name}.db.gz"
            else:
                backup_path = self.backup_dir / f"{backup_name}.db"
            
            # Ensure database exists
            if not self.db_path.exists():
                logger.error(f"Database not found: {self.db_path}")
                return None
            
            # Create backup
            logger.info(f"Creating backup: {backup_path}")
            
            if compress:
                # Compressed backup
                with sqlite3.connect(str(self.db_path)) as src_conn:
                    with gzip.open(backup_path, 'wb') as gz_file:
                        for line in src_conn.iterdump():
                            gz_file.write(f"{line}\n".encode('utf-8'))
            else:
                # Simple file copy
                shutil.copy2(self.db_path, backup_path)
            
            # Verify backup
            backup_size = backup_path.stat().st_size
            if backup_size == 0:
                logger.error("Backup file is empty")
                backup_path.unlink()
                return None
            
            # Update metadata
            metadata = self._load_metadata()
            backup_info = {
                "id": backup_name,
                "path": str(backup_path),
                "timestamp": timestamp,
                "size": backup_size,
                "compressed": compress,
                "description": description,
                "db_size": self.db_path.stat().st_size
            }
            
            metadata["backups"].append(backup_info)
            metadata["last_backup"] = timestamp
            metadata["total_backups"] += 1
            self._save_metadata(metadata)
            
            logger.info(f"Backup created successfully: {backup_path} ({backup_size:,} bytes)")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    def restore_backup(self, backup_id: str, target_path: Optional[str] = None) -> bool:
        """
        Restore a database backup.
        
        Args:
            backup_id: Backup ID or filename to restore
            target_path: Target path for restoration (default: original db path)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find backup in metadata
            metadata = self._load_metadata()
            backup_info = None
            
            for backup in metadata["backups"]:
                if backup["id"] == backup_id or backup["path"].endswith(backup_id):
                    backup_info = backup
                    break
            
            if not backup_info:
                logger.error(f"Backup not found: {backup_id}")
                return False
            
            backup_path = Path(backup_info["path"])
            if not backup_path.exists():
                logger.error(f"Backup file missing: {backup_path}")
                return False
            
            # Determine target path
            target = Path(target_path) if target_path else self.db_path
            
            # Create safety backup of current database
            if target.exists():
                safety_backup = self.create_backup(
                    description=f"Safety backup before restoring {backup_id}",
                    compress=False
                )
                if not safety_backup:
                    logger.error("Failed to create safety backup")
                    return False
            
            # Restore backup
            logger.info(f"Restoring backup: {backup_path} -> {target}")
            
            if backup_info["compressed"]:
                # Decompress and restore
                with gzip.open(backup_path, 'rb') as gz_file:
                    sql_script = gz_file.read().decode('utf-8')
                
                # Remove existing database
                if target.exists():
                    target.unlink()
                
                # Execute SQL script
                with sqlite3.connect(str(target)) as conn:
                    conn.executescript(sql_script)
            else:
                # Simple file copy
                shutil.copy2(backup_path, target)
            
            # Verify restoration
            with sqlite3.connect(str(target)) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                
                if result[0] != "ok":
                    logger.error(f"Database integrity check failed: {result}")
                    return False
            
            logger.info(f"Backup restored successfully: {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False
    
    def list_backups(self, limit: Optional[int] = None) -> List[Dict]:
        """
        List available backups.
        
        Args:
            limit: Maximum number of backups to return
            
        Returns:
            List of backup information dictionaries
        """
        metadata = self._load_metadata()
        backups = metadata["backups"]
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x["timestamp"], reverse=True)
        
        if limit:
            backups = backups[:limit]
        
        return backups
    
    def delete_backup(self, backup_id: str) -> bool:
        """
        Delete a specific backup.
        
        Args:
            backup_id: Backup ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            metadata = self._load_metadata()
            backup_info = None
            
            # Find and remove from metadata
            for i, backup in enumerate(metadata["backups"]):
                if backup["id"] == backup_id:
                    backup_info = backup
                    metadata["backups"].pop(i)
                    break
            
            if not backup_info:
                logger.error(f"Backup not found: {backup_id}")
                return False
            
            # Delete file
            backup_path = Path(backup_info["path"])
            if backup_path.exists():
                backup_path.unlink()
                logger.info(f"Deleted backup: {backup_path}")
            
            # Update metadata
            self._save_metadata(metadata)
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete backup: {e}")
            return False
    
    def cleanup_old_backups(self, keep_count: int = 10, keep_days: int = 30):
        """
        Clean up old backups based on count and age.
        
        Args:
            keep_count: Number of recent backups to keep
            keep_days: Keep backups newer than this many days
        """
        metadata = self._load_metadata()
        backups = metadata["backups"]
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Calculate cutoff date
        cutoff_date = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
        
        # Determine which backups to delete
        to_delete = []
        for i, backup in enumerate(backups):
            backup_time = datetime.strptime(backup["timestamp"], "%Y%m%d_%H%M%S").timestamp()
            
            # Keep recent backups by count
            if i < keep_count:
                continue
            
            # Keep backups newer than cutoff
            if backup_time > cutoff_date:
                continue
            
            to_delete.append(backup["id"])
        
        # Delete old backups
        deleted = 0
        for backup_id in to_delete:
            if self.delete_backup(backup_id):
                deleted += 1
        
        logger.info(f"Cleanup complete: deleted {deleted} old backups")
    
    def verify_backup(self, backup_id: str) -> Tuple[bool, str]:
        """
        Verify a backup's integrity.
        
        Args:
            backup_id: Backup ID to verify
            
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            metadata = self._load_metadata()
            backup_info = None
            
            for backup in metadata["backups"]:
                if backup["id"] == backup_id:
                    backup_info = backup
                    break
            
            if not backup_info:
                return False, f"Backup not found: {backup_id}"
            
            backup_path = Path(backup_info["path"])
            if not backup_path.exists():
                return False, f"Backup file missing: {backup_path}"
            
            # Check file size
            actual_size = backup_path.stat().st_size
            if actual_size != backup_info["size"]:
                return False, f"Size mismatch: expected {backup_info['size']}, got {actual_size}"
            
            # Try to read backup
            try:
                if backup_info["compressed"]:
                    with gzip.open(backup_path, 'rb') as gz_file:
                        # Just read first few bytes to verify it's valid gzip
                        gz_file.read(1024)
                else:
                    # Verify SQLite header
                    with open(backup_path, 'rb') as f:
                        header = f.read(16)
                        if not header.startswith(b'SQLite format 3'):
                            return False, "Invalid SQLite file format"
            except Exception as e:
                return False, f"Failed to read backup: {e}"
            
            return True, "Backup verified successfully"
            
        except Exception as e:
            return False, f"Verification failed: {e}"
    
    @contextmanager
    def transaction_backup(self, description: str = "Transaction backup"):
        """
        Context manager for creating automatic backup before transactions.
        
        Usage:
            with backup_manager.transaction_backup():
                # Perform database operations
                pass
        """
        backup_id = None
        try:
            # Create backup before transaction
            backup_path = self.create_backup(
                description=description,
                compress=False  # Fast backup for transactions
            )
            
            if backup_path:
                # Extract backup ID from path
                backup_id = Path(backup_path).stem.replace('.db', '')
                logger.info(f"Transaction backup created: {backup_id}")
            
            yield backup_id
            
        except Exception as e:
            # On error, attempt to restore backup
            if backup_id:
                logger.error(f"Transaction failed: {e}")
                logger.info(f"Attempting to restore backup: {backup_id}")
                
                if self.restore_backup(backup_id):
                    logger.info("Backup restored successfully")
                else:
                    logger.error("Failed to restore backup")
            
            raise