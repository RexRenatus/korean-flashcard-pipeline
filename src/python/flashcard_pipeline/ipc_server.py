#!/usr/bin/env python3
"""
IPC Server for Electron-Python communication

This module provides a JSON-RPC style server that communicates with the Electron
main process via stdin/stdout. It handles all database and processing operations
requested by the desktop application.
"""

import sys
import json
import asyncio
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flashcard_pipeline.models import VocabularyRecord, ProcessingStatus
from flashcard_pipeline.database.db_manager import DatabaseManager
from flashcard_pipeline.api_client import APIClient
from flashcard_pipeline.pipeline import SequentialPipeline
from flashcard_pipeline.exceptions import FlashcardPipelineError
from flashcard_pipeline.utils import get_logger

# Configure logging
logger = get_logger(__name__)

class IPCServer:
    """Handles IPC communication with Electron main process"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.api_client = APIClient()
        self.pipeline = SequentialPipeline(self.db_manager, self.api_client)
        self.running = True
        self.processing_tasks = {}
        
    async def initialize(self):
        """Initialize the server and its dependencies"""
        try:
            # Initialize database
            await self.db_manager.initialize()
            
            # Send ready signal
            self._send_response({"type": "ready", "version": "1.0.0"})
            logger.info("IPC Server initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize IPC server: {e}")
            self._send_error(None, "INIT_ERROR", str(e))
            raise
    
    def _send_response(self, response: Dict[str, Any]):
        """Send response to Electron via stdout"""
        try:
            json_response = json.dumps(response)
            sys.stdout.write(json_response + '\n')
            sys.stdout.flush()
        except Exception as e:
            logger.error(f"Failed to send response: {e}")
    
    def _send_result(self, request_id: str, result: Any):
        """Send successful result"""
        self._send_response({
            "id": request_id,
            "result": result
        })
    
    def _send_error(self, request_id: Optional[str], code: str, message: str, details: Any = None):
        """Send error response"""
        error_data = {
            "code": code,
            "message": message
        }
        if details:
            error_data["details"] = details
            
        response = {"error": error_data}
        if request_id:
            response["id"] = request_id
            
        self._send_response(response)
    
    async def handle_request(self, request: Dict[str, Any]):
        """Handle incoming request from Electron"""
        request_id = request.get("id")
        command = request.get("command")
        args = request.get("args", {})
        
        if not command:
            self._send_error(request_id, "INVALID_REQUEST", "Missing command")
            return
        
        try:
            # Route to appropriate handler
            handler = getattr(self, f"_handle_{command}", None)
            if not handler:
                self._send_error(request_id, "UNKNOWN_COMMAND", f"Unknown command: {command}")
                return
            
            # Execute handler
            result = await handler(args)
            self._send_result(request_id, result)
            
        except FlashcardPipelineError as e:
            self._send_error(request_id, e.__class__.__name__, str(e))
        except Exception as e:
            logger.error(f"Error handling command {command}: {e}\n{traceback.format_exc()}")
            self._send_error(request_id, "INTERNAL_ERROR", str(e))
    
    # Vocabulary Operations
    async def _handle_get_vocabulary_list(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get paginated vocabulary list"""
        page = args.get("page", 1)
        page_size = args.get("pageSize", 50)
        filter_status = args.get("filter")
        sort_by = args.get("sort", "created_at")
        search = args.get("search")
        
        offset = (page - 1) * page_size
        
        # Build query
        query = "SELECT * FROM vocabulary_master WHERE 1=1"
        params = []
        
        if filter_status == "active":
            query += " AND is_active = 1"
        elif filter_status == "inactive":
            query += " AND is_active = 0"
        
        if search:
            query += " AND (korean LIKE ? OR english LIKE ?)"
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern])
        
        # Get total count
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        total = await self.db_manager.fetch_one(count_query, params)
        total_count = total[0] if total else 0
        
        # Add sorting and pagination
        query += f" ORDER BY {sort_by} DESC LIMIT ? OFFSET ?"
        params.extend([page_size, offset])
        
        # Fetch items
        rows = await self.db_manager.fetch_all(query, params)
        items = [self._row_to_vocabulary_dict(row) for row in rows]
        
        return {
            "items": items,
            "total": total_count,
            "page": page,
            "pageSize": page_size
        }
    
    async def _handle_add_vocabulary(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Add new vocabulary item"""
        # Validate required fields
        if not args.get("korean"):
            raise ValueError("Korean field is required")
        
        # Create vocabulary record
        vocab = VocabularyRecord(
            korean=args["korean"],
            english=args.get("english"),
            romanization=args.get("romanization"),
            hanja=args.get("hanja"),
            type=args.get("type", "word"),
            category=args.get("category"),
            subcategory=args.get("subcategory"),
            difficulty_level=args.get("difficulty_level"),
            frequency_rank=args.get("frequency_rank"),
            source_reference=args.get("source_reference"),
            notes=args.get("notes")
        )
        
        # Insert into database
        vocab_id = await self.db_manager.add_vocabulary(vocab)
        
        # Fetch and return the created item
        row = await self.db_manager.fetch_one(
            "SELECT * FROM vocabulary_master WHERE id = ?",
            [vocab_id]
        )
        
        return self._row_to_vocabulary_dict(row)
    
    async def _handle_update_vocabulary(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing vocabulary item"""
        vocab_id = args.get("id")
        updates = args.get("updates", {})
        
        if not vocab_id:
            raise ValueError("Vocabulary ID is required")
        
        # Build update query
        update_fields = []
        params = []
        
        for field, value in updates.items():
            if field not in ["id", "created_at"]:  # Don't update these fields
                update_fields.append(f"{field} = ?")
                params.append(value)
        
        if not update_fields:
            raise ValueError("No fields to update")
        
        # Add updated_at
        update_fields.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        
        # Add ID for WHERE clause
        params.append(vocab_id)
        
        # Execute update
        query = f"UPDATE vocabulary_master SET {', '.join(update_fields)} WHERE id = ?"
        await self.db_manager.execute(query, params)
        
        # Fetch and return updated item
        row = await self.db_manager.fetch_one(
            "SELECT * FROM vocabulary_master WHERE id = ?",
            [vocab_id]
        )
        
        return self._row_to_vocabulary_dict(row)
    
    async def _handle_delete_vocabulary(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Delete vocabulary items (soft delete)"""
        ids = args.get("ids", [])
        
        if not ids:
            raise ValueError("No IDs provided for deletion")
        
        # Soft delete by setting is_active = 0
        placeholders = ','.join(['?' for _ in ids])
        query = f"UPDATE vocabulary_master SET is_active = 0 WHERE id IN ({placeholders})"
        
        await self.db_manager.execute(query, ids)
        
        return {"success": True}
    
    # Processing Operations
    async def _handle_start_processing(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Start processing vocabulary items"""
        vocabulary_ids = args.get("vocabularyIds", [])
        options = args.get("options", {})
        
        if not vocabulary_ids:
            raise ValueError("No vocabulary IDs provided")
        
        # Create processing task
        task_id = f"task_{datetime.now().timestamp()}"
        
        # TODO: Implement actual processing logic
        # For now, return mock response
        return {
            "taskId": task_id,
            "status": "queued",
            "itemCount": len(vocabulary_ids)
        }
    
    async def _handle_get_processing_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get status of processing task"""
        task_id = args.get("taskId")
        
        if not task_id:
            raise ValueError("Task ID is required")
        
        # TODO: Implement actual status tracking
        # For now, return mock response
        return {
            "taskId": task_id,
            "status": "processing",
            "progress": 0.45,
            "processed": 45,
            "total": 100,
            "currentStage": "stage1",
            "estimatedTimeRemaining": 120
        }
    
    # System Operations
    async def _handle_get_system_stats(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get system statistics"""
        # Get counts from database
        total_words = await self.db_manager.fetch_one(
            "SELECT COUNT(*) FROM vocabulary_master WHERE is_active = 1"
        )
        processed_words = await self.db_manager.fetch_one(
            "SELECT COUNT(DISTINCT vocabulary_id) FROM flashcards"
        )
        pending_words = await self.db_manager.fetch_one(
            "SELECT COUNT(*) FROM vocabulary_master v WHERE is_active = 1 AND NOT EXISTS (SELECT 1 FROM flashcards f WHERE f.vocabulary_id = v.id)"
        )
        failed_words = await self.db_manager.fetch_one(
            "SELECT COUNT(*) FROM processing_tasks WHERE status = 'failed'"
        )
        
        # Get cache statistics
        cache_stats = await self.db_manager.fetch_one(
            "SELECT COUNT(*) as total, SUM(hit_count) as hits FROM cache_entries"
        )
        
        total_cache_entries = cache_stats[0] if cache_stats else 0
        total_hits = cache_stats[1] if cache_stats and cache_stats[1] else 0
        cache_hit_rate = total_hits / (total_cache_entries + 1) if total_cache_entries > 0 else 0
        
        # Get average processing time
        avg_time = await self.db_manager.fetch_one(
            "SELECT AVG(JULIANDAY(completed_at) - JULIANDAY(started_at)) * 86400 FROM processing_tasks WHERE status = 'completed'"
        )
        avg_processing_time = avg_time[0] if avg_time and avg_time[0] else 0
        
        return {
            "totalWords": total_words[0] if total_words else 0,
            "processedWords": processed_words[0] if processed_words else 0,
            "pendingWords": pending_words[0] if pending_words else 0,
            "failedWords": failed_words[0] if failed_words else 0,
            "cacheHitRate": cache_hit_rate,
            "averageProcessingTime": avg_processing_time,
            "apiHealth": "healthy",  # TODO: Implement actual health check
            "lastSync": datetime.now().isoformat()
        }
    
    async def _handle_check_api_health(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Check API health status"""
        try:
            # Perform health check
            start_time = datetime.now()
            # TODO: Implement actual API health check
            latency = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return {
                "status": "healthy",
                "latency": latency,
                "rateLimit": {
                    "remaining": 950,
                    "reset": datetime.now().isoformat()
                }
            }
        except Exception as e:
            return {
                "status": "down",
                "latency": -1,
                "error": str(e)
            }
    
    # Import/Export Operations
    async def _handle_import_vocabulary(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Import vocabulary from file"""
        file_path = args.get("filePath")
        file_format = args.get("format", "csv")
        
        if not file_path:
            raise ValueError("File path is required")
        
        # TODO: Implement actual import logic
        return {
            "success": True,
            "imported": 100,
            "duplicates": 5,
            "errors": 2,
            "details": ["Line 10: Invalid format", "Line 25: Missing required field"]
        }
    
    async def _handle_validate_import(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Validate import data"""
        data = args.get("data", [])
        
        errors = []
        for i, item in enumerate(data):
            if not item.get("korean"):
                errors.append(f"Row {i+1}: Korean field is required")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    async def _handle_export_flashcards(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Export flashcards in specified format"""
        vocabulary_ids = args.get("vocabularyIds", [])
        options = args.get("options", {})
        
        # TODO: Implement actual export logic
        return {
            "filePath": "/tmp/korean_vocab.apkg",
            "cardCount": 150,
            "fileSize": "2.5MB"
        }
    
    # Cache Operations
    async def _handle_clear_cache(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Clear cache entries"""
        older_than = args.get("olderThan")
        
        # TODO: Implement cache clearing logic
        return {
            "cleared": 1234,
            "freedSpace": "125MB"
        }
    
    # Helper methods
    def _row_to_vocabulary_dict(self, row) -> Dict[str, Any]:
        """Convert database row to vocabulary dictionary"""
        if not row:
            return None
            
        columns = [
            "id", "korean", "english", "romanization", "hanja", 
            "type", "category", "subcategory", "difficulty_level",
            "frequency_rank", "source_reference", "notes", "is_active",
            "created_at", "updated_at"
        ]
        
        vocab_dict = dict(zip(columns, row))
        vocab_dict["isActive"] = bool(vocab_dict.pop("is_active", True))
        vocab_dict["createdAt"] = vocab_dict.pop("created_at", "")
        vocab_dict["updatedAt"] = vocab_dict.pop("updated_at", "")
        vocab_dict["difficultyLevel"] = vocab_dict.pop("difficulty_level", None)
        vocab_dict["frequencyRank"] = vocab_dict.pop("frequency_rank", None)
        vocab_dict["sourceReference"] = vocab_dict.pop("source_reference", None)
        
        return vocab_dict
    
    async def run(self):
        """Main server loop"""
        logger.info("Starting IPC server...")
        
        # Initialize server
        await self.initialize()
        
        # Read from stdin
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        
        # Process requests
        while self.running:
            try:
                line = await reader.readline()
                if not line:
                    break
                
                # Parse request
                request = json.loads(line.decode().strip())
                
                # Handle request
                await self.handle_request(request)
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received: {e}")
                self._send_error(None, "PARSE_ERROR", "Invalid JSON")
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}\n{traceback.format_exc()}")
                self._send_error(None, "INTERNAL_ERROR", str(e))
        
        logger.info("IPC server stopped")
    
    async def shutdown(self):
        """Cleanup resources"""
        self.running = False
        if self.db_manager:
            await self.db_manager.close()


async def main():
    """Main entry point"""
    server = IPCServer()
    
    try:
        await server.run()
    finally:
        await server.shutdown()


if __name__ == "__main__":
    # Run the server
    asyncio.run(main())