#!/usr/bin/env python3
"""
Python Bridge for Electron Application
Handles communication between Electron main process and Python flashcard pipeline
"""

import sys
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path

# Add the flashcard pipeline to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent))

try:
    from src.python.flashcard_pipeline import (
        api_client,
        database,
        cache_v2,
        export_service,
        pipeline,
        models,
    )
    from src.python.flashcard_pipeline.cli_v2 import FlashcardCLI
    from src.python.flashcard_pipeline.database.manager import DatabaseManager
except ImportError as e:
    print(json.dumps({
        "error": f"Failed to import flashcard pipeline: {str(e)}",
        "type": "ImportError"
    }))
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PythonBridge:
    """Handles IPC communication with Electron"""
    
    def __init__(self):
        self.db_manager = None
        self.pipeline_instance = None
        self.cli = None
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
    def initialize(self):
        """Initialize the Python services"""
        try:
            # Initialize database
            self.db_manager = DatabaseManager()
            
            # Initialize CLI (which contains all the main functionality)
            self.cli = FlashcardCLI()
            
            return {"success": True, "message": "Python bridge initialized"}
        except Exception as e:
            logger.error(f"Failed to initialize: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def handle_command(self, command: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Route commands to appropriate handlers"""
        try:
            # Parse module.command format
            if '.' in command:
                module, method = command.split('.', 1)
                handler = getattr(self, f"handle_{module}", None)
                if handler:
                    return handler(method, args)
            
            # Direct command handlers
            handler = getattr(self, f"handle_{command}", None)
            if handler:
                return handler(args)
            
            return {
                "success": False,
                "error": f"Unknown command: {command}"
            }
        except Exception as e:
            logger.error(f"Error handling command {command}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "type": type(e).__name__
            }
    
    def handle_db(self, method: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle database operations"""
        if not self.db_manager:
            return {"success": False, "error": "Database not initialized"}
        
        try:
            if method == "get_vocabulary":
                return self._get_vocabulary(args)
            elif method == "add_vocabulary":
                return self._add_vocabulary(args)
            elif method == "update_vocabulary":
                return self._update_vocabulary(args)
            elif method == "delete_vocabulary":
                return self._delete_vocabulary(args)
            elif method == "delete_vocabulary_batch":
                return self._delete_vocabulary_batch(args)
            elif method == "get_flashcards":
                return self._get_flashcards(args)
            elif method == "delete_flashcard":
                return self._delete_flashcard(args)
            elif method == "delete_flashcards_batch":
                return self._delete_flashcards_batch(args)
            elif method == "toggle_favorite":
                return self._toggle_favorite(args)
            elif method == "get_favorites":
                return self._get_favorites(args)
            elif method == "get_stats":
                return self._get_database_stats()
            elif method == "create_backup":
                return self._create_backup()
            elif method == "restore_backup":
                return self._restore_backup(args)
            else:
                return {"success": False, "error": f"Unknown database method: {method}"}
        except Exception as e:
            logger.error(f"Database error in {method}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _get_vocabulary(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get vocabulary items with pagination"""
        page = args.get('page', 1)
        page_size = args.get('pageSize', 50)
        search = args.get('search')
        status = args.get('status')
        tags = args.get('tags', [])
        
        # Query database
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build query
            query = "SELECT * FROM vocabulary WHERE 1=1"
            params = []
            
            if search:
                query += " AND (korean LIKE ? OR english LIKE ?)"
                params.extend([f"%{search}%", f"%{search}%"])
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            # Get total count
            count_query = query.replace("SELECT *", "SELECT COUNT(*)")
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]
            
            # Add pagination
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([page_size, (page - 1) * page_size])
            
            cursor.execute(query, params)
            columns = [description[0] for description in cursor.description]
            items = []
            
            for row in cursor.fetchall():
                item = dict(zip(columns, row))
                # Parse tags if stored as JSON
                if item.get('tags') and isinstance(item['tags'], str):
                    try:
                        item['tags'] = json.loads(item['tags'])
                    except:
                        item['tags'] = []
                items.append(item)
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "pageSize": page_size
        }
    
    def _add_vocabulary(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new vocabulary item"""
        korean = args.get('korean')
        english = args.get('english', '')
        tags = args.get('tags', [])
        priority = args.get('priority', 0)
        
        if not korean:
            return {"success": False, "error": "Korean word is required"}
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if already exists
            cursor.execute("SELECT id FROM vocabulary WHERE korean = ?", (korean,))
            if cursor.fetchone():
                return {"success": False, "error": "Word already exists", "code": "DUPLICATE"}
            
            # Insert new vocabulary
            cursor.execute("""
                INSERT INTO vocabulary (korean, english, tags, priority, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'pending', datetime('now'), datetime('now'))
            """, (korean, english, json.dumps(tags), priority))
            
            conn.commit()
            vocab_id = cursor.lastrowid
            
            # Fetch and return the created item
            cursor.execute("SELECT * FROM vocabulary WHERE id = ?", (vocab_id,))
            columns = [description[0] for description in cursor.description]
            row = cursor.fetchone()
            item = dict(zip(columns, row))
            if item.get('tags') and isinstance(item['tags'], str):
                item['tags'] = json.loads(item['tags'])
            
            return item
    
    def _update_vocabulary(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Update a vocabulary item"""
        vocab_id = args.get('id')
        if not vocab_id:
            return {"success": False, "error": "ID is required"}
        
        updates = {}
        for field in ['korean', 'english', 'tags', 'priority', 'status']:
            if field in args:
                value = args[field]
                if field == 'tags' and isinstance(value, list):
                    value = json.dumps(value)
                updates[field] = value
        
        if not updates:
            return {"success": False, "error": "No updates provided"}
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build update query
            set_clauses = [f"{field} = ?" for field in updates.keys()]
            set_clauses.append("updated_at = datetime('now')")
            query = f"UPDATE vocabulary SET {', '.join(set_clauses)} WHERE id = ?"
            
            cursor.execute(query, list(updates.values()) + [vocab_id])
            conn.commit()
            
            # Fetch and return updated item
            cursor.execute("SELECT * FROM vocabulary WHERE id = ?", (vocab_id,))
            columns = [description[0] for description in cursor.description]
            row = cursor.fetchone()
            
            if not row:
                return {"success": False, "error": "Vocabulary not found"}
            
            item = dict(zip(columns, row))
            if item.get('tags') and isinstance(item['tags'], str):
                item['tags'] = json.loads(item['tags'])
            
            return item
    
    def _delete_vocabulary(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a vocabulary item"""
        vocab_id = args.get('id')
        if not vocab_id:
            return {"success": False, "error": "ID is required"}
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Delete associated flashcards first
            cursor.execute("DELETE FROM flashcards WHERE vocabulary_id = ?", (vocab_id,))
            
            # Delete vocabulary
            cursor.execute("DELETE FROM vocabulary WHERE id = ?", (vocab_id,))
            conn.commit()
            
            return {"success": True}
    
    def _delete_vocabulary_batch(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Delete multiple vocabulary items"""
        ids = args.get('ids', [])
        if not ids:
            return {"success": False, "error": "No IDs provided"}
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Delete associated flashcards
            placeholders = ','.join('?' * len(ids))
            cursor.execute(f"DELETE FROM flashcards WHERE vocabulary_id IN ({placeholders})", ids)
            
            # Delete vocabulary items
            cursor.execute(f"DELETE FROM vocabulary WHERE id IN ({placeholders})", ids)
            conn.commit()
            
            return {"success": True, "deleted": cursor.rowcount}
    
    def _get_flashcards(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get flashcards with filtering"""
        page = args.get('page', 1)
        page_size = args.get('pageSize', 50)
        status = args.get('status')
        stage = args.get('stage')
        search = args.get('search')
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build query
            query = """
                SELECT f.*, v.korean as word
                FROM flashcards f
                JOIN vocabulary v ON f.vocabulary_id = v.id
                WHERE 1=1
            """
            params = []
            
            if status:
                query += " AND f.status = ?"
                params.append(status)
            
            if stage:
                query += " AND f.stage = ?"
                params.append(stage)
            
            if search:
                query += " AND (v.korean LIKE ? OR f.definition LIKE ?)"
                params.extend([f"%{search}%", f"%{search}%"])
            
            # Get total count
            count_query = query.replace("SELECT f.*, v.korean as word", "SELECT COUNT(*)")
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]
            
            # Add pagination
            query += " ORDER BY f.created_at DESC LIMIT ? OFFSET ?"
            params.extend([page_size, (page - 1) * page_size])
            
            cursor.execute(query, params)
            columns = [description[0] for description in cursor.description]
            items = []
            
            for row in cursor.fetchall():
                item = dict(zip(columns, row))
                # Parse JSON fields
                for field in ['tags', 'synonyms', 'antonyms']:
                    if item.get(field) and isinstance(item[field], str):
                        try:
                            item[field] = json.loads(item[field])
                        except:
                            item[field] = []
                items.append(item)
            
            # Get favorites
            cursor.execute("SELECT item_id FROM favorites WHERE item_type = 'flashcard'")
            favorites = [row[0] for row in cursor.fetchall()]
        
        return {
            "items": items,
            "total": total,
            "favorites": favorites
        }
    
    def _get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Vocabulary count
            cursor.execute("SELECT COUNT(*) FROM vocabulary")
            stats['vocabulary_count'] = cursor.fetchone()[0]
            
            # Flashcard count
            cursor.execute("SELECT COUNT(*) FROM flashcards")
            stats['flashcard_count'] = cursor.fetchone()[0]
            
            # Processing count
            cursor.execute("SELECT COUNT(*) FROM vocabulary WHERE status = 'processing'")
            stats['processing_count'] = cursor.fetchone()[0]
            
            # Failed count
            cursor.execute("SELECT COUNT(*) FROM vocabulary WHERE status = 'failed'")
            stats['failed_count'] = cursor.fetchone()[0]
            
            # Database size
            db_path = self.db_manager.db_path
            if db_path.exists():
                stats['database_size'] = db_path.stat().st_size
            else:
                stats['database_size'] = 0
            
            return stats
    
    def handle_get_version(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get version information"""
        return {
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "pipeline": "1.0.0"  # You should get this from your package
        }
    
    def handle_get_system_stats(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get system statistics"""
        stats = self._get_database_stats()
        
        # Add cache stats if available
        try:
            cache_stats = self.handle_get_cache_stats({})
            stats.update(cache_stats)
        except:
            pass
        
        return stats
    
    def handle_get_cache_stats(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get cache statistics"""
        # This would connect to your cache implementation
        return {
            "cache_size": 0,
            "cache_entries": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
    
    def handle_process_vocabulary(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Process vocabulary through the pipeline"""
        vocab_ids = args.get('vocabularyIds', [])
        stage = args.get('stage', 'both')
        
        if not vocab_ids:
            return {"success": False, "error": "No vocabulary IDs provided"}
        
        # This would integrate with your actual processing pipeline
        # For now, return a mock response
        return {
            "taskId": f"task_{int(asyncio.get_event_loop().time())}",
            "status": "started",
            "itemCount": len(vocab_ids)
        }
    
    def handle_import_vocabulary_content(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Import vocabulary from content string"""
        content = args.get('content', '')
        format_type = args.get('format', 'csv')
        
        if not content:
            return {"success": False, "error": "No content provided"}
        
        try:
            items = []
            
            if format_type == 'csv':
                lines = content.strip().split('\n')
                # Check if first line is header
                if lines and 'korean' in lines[0].lower():
                    lines = lines[1:]
                
                for line in lines:
                    if line.strip():
                        parts = line.split(',')
                        if parts:
                            item = {
                                'korean': parts[0].strip(),
                                'english': parts[1].strip() if len(parts) > 1 else ''
                            }
                            items.append(item)
            
            elif format_type == 'txt':
                lines = content.strip().split('\n')
                for line in lines:
                    if line.strip():
                        items.append({'korean': line.strip()})
            
            elif format_type == 'json':
                data = json.loads(content)
                if isinstance(data, list):
                    items = data
                else:
                    return {"success": False, "error": "JSON must be an array"}
            
            # Import items to database
            imported = 0
            duplicates = 0
            errors = []
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                for item in items:
                    korean = item.get('korean')
                    if not korean:
                        errors.append("Missing Korean word")
                        continue
                    
                    # Check if exists
                    cursor.execute("SELECT id FROM vocabulary WHERE korean = ?", (korean,))
                    if cursor.fetchone():
                        duplicates += 1
                        continue
                    
                    # Insert
                    try:
                        cursor.execute("""
                            INSERT INTO vocabulary (korean, english, tags, priority, status, created_at, updated_at)
                            VALUES (?, ?, '[]', 0, 'pending', datetime('now'), datetime('now'))
                        """, (korean, item.get('english', '')))
                        imported += 1
                    except Exception as e:
                        errors.append(str(e))
                
                conn.commit()
            
            return {
                "success": True,
                "imported": imported,
                "duplicates": duplicates,
                "errors": errors,
                "total": len(items)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def run(self):
        """Main event loop for handling IPC messages"""
        logger.info("Python bridge starting...")
        
        # Initialize services
        init_result = self.initialize()
        if not init_result.get("success"):
            print(json.dumps(init_result))
            return
        
        # Send ready signal
        print(json.dumps({"type": "ready", "message": "Python bridge ready"}))
        sys.stdout.flush()
        
        # Main message loop
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                
                message = json.loads(line.strip())
                command = message.get("command")
                args = message.get("args", {})
                msg_id = message.get("id")
                
                if command == "shutdown":
                    logger.info("Shutdown requested")
                    break
                
                # Handle command
                result = self.handle_command(command, args)
                
                # Send response
                response = {
                    "id": msg_id,
                    "result": result
                }
                print(json.dumps(response))
                sys.stdout.flush()
                
            except json.JSONDecodeError as e:
                error_response = {
                    "error": f"Invalid JSON: {str(e)}",
                    "type": "JSONDecodeError"
                }
                print(json.dumps(error_response))
                sys.stdout.flush()
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                error_response = {
                    "error": str(e),
                    "type": type(e).__name__
                }
                print(json.dumps(error_response))
                sys.stdout.flush()
        
        logger.info("Python bridge shutting down")


if __name__ == "__main__":
    bridge = PythonBridge()
    bridge.run()