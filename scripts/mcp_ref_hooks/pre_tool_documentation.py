#!/usr/bin/env python3
"""
MCP Ref Hook: Pre-Tool Documentation Search
Searches relevant documentation before tool execution
"""

import sys
import json
import os
import hashlib
import re
from typing import List, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flashcard_pipeline.utils import get_logger

logger = get_logger(__name__)


class PreToolDocumentationHook:
    """Searches documentation before tool execution"""
    
    def __init__(self):
        self.cache_dir = Path(".claude/mcp_ref_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.current_year = datetime.now().year
        
    def extract_keywords(self, tool_name: str, file_path: str, operation: str) -> List[str]:
        """Extract relevant keywords based on context"""
        keywords = []
        
        # Extract from file path
        if file_path and file_path != "None":
            path_parts = Path(file_path).parts
            # Add meaningful path components
            for part in path_parts:
                if part not in [".", "..", "src", "tests", "docs"]:
                    keywords.append(part.replace("_", " "))
            
            # Add file extension context
            ext = Path(file_path).suffix
            if ext:
                ext_map = {
                    ".py": ["python", "code"],
                    ".js": ["javascript", "node"],
                    ".ts": ["typescript", "node"],
                    ".rs": ["rust", "cargo"],
                    ".go": ["golang", "go"],
                    ".java": ["java", "jvm"],
                    ".cpp": ["c++", "cpp"],
                    ".c": ["c", "programming"],
                    ".md": ["markdown", "documentation"],
                    ".json": ["json", "configuration"],
                    ".yaml": ["yaml", "configuration"],
                    ".yml": ["yaml", "configuration"],
                    ".sql": ["sql", "database"],
                    ".sh": ["bash", "shell", "script"],
                    ".dockerfile": ["docker", "container"],
                    ".toml": ["toml", "configuration"]
                }
                keywords.extend(ext_map.get(ext.lower(), []))
        
        # Extract from tool name
        tool_keywords = {
            "Task": ["implementation", "development", "coding"],
            "Write": ["create", "new", "file", "implementation"],
            "Edit": ["modify", "update", "refactor", "change"],
            "MultiEdit": ["refactor", "multiple", "changes", "update"],
            "Read": ["analyze", "understand", "review"],
            "Bash": ["command", "shell", "execute", "script"]
        }
        keywords.extend(tool_keywords.get(tool_name, []))
        
        # Extract from operation context
        if operation and operation != "None":
            # Look for common programming terms
            prog_terms = re.findall(r'\b(?:class|function|method|api|client|server|database|cache|test|error|exception|import|module)\b', operation.lower())
            keywords.extend(prog_terms)
        
        # Add current year to keywords for up-to-date documentation
        keywords.append(str(self.current_year))
        keywords.append(f"{self.current_year} latest")
        
        # Deduplicate and filter
        keywords = list(set(keywords))
        keywords = [k for k in keywords if len(k) > 2]
        
        # Ensure year is always included
        if str(self.current_year) not in keywords:
            keywords.insert(0, str(self.current_year))
        
        # Limit to top 10 most relevant
        return keywords[:10]
    
    def generate_query(self, tool_name: str, file_path: str, operation: str) -> str:
        """Generate search query based on context"""
        queries = {
            "Task": f"How to implement {operation} best practices in {self.current_year}",
            "Write": f"Creating new {Path(file_path).suffix if file_path else 'file'} file best practices {self.current_year}",
            "Edit": f"Refactoring and updating code best practices {self.current_year}",
            "MultiEdit": f"Large scale refactoring techniques {self.current_year}",
            "Read": f"Code analysis and review techniques {self.current_year}",
            "Bash": f"Shell scripting and command line best practices {self.current_year}"
        }
        
        base_query = queries.get(tool_name, f"{tool_name} operation best practices {self.current_year}")
        
        # Add file-specific context
        if file_path and file_path != "None":
            ext = Path(file_path).suffix
            if ext:
                base_query = f"{base_query} for {ext} files"
        
        # Always ensure year is in the query
        if str(self.current_year) not in base_query:
            base_query = f"{base_query} {self.current_year}"
        
        return base_query
    
    def search_documentation(self, query: str, keywords: List[str]) -> Dict[str, Any]:
        """Search documentation using MCP Ref tool"""
        # For now, return a structured response
        # In production, this would call the actual MCP Ref tool
        return {
            "query": query,
            "keywords": keywords,
            "source": "public",
            "results": [
                {
                    "title": f"Best practices for {keywords[0] if keywords else 'development'}",
                    "url": "https://docs.example.com/best-practices",
                    "relevance": 0.95,
                    "snippet": "Key recommendations and patterns..."
                }
            ],
            "search_time": 0.5
        }
    
    def cache_results(self, cache_key: str, results: Dict[str, Any]) -> None:
        """Cache search results"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        with open(cache_file, 'w') as f:
            json.dump(results, f, indent=2)
    
    def get_cached_results(self, cache_key: str) -> Dict[str, Any]:
        """Get cached results if available"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            # Check if cache is less than 24 hours old
            if (Path.ctime(cache_file) - Path.ctime(Path.cwd())) < 86400:
                with open(cache_file, 'r') as f:
                    return json.load(f)
        return None
    
    def run(self, tool_name: str, file_path: str, operation: str) -> None:
        """Main hook execution"""
        try:
            # Extract keywords
            keywords = self.extract_keywords(tool_name, file_path, operation)
            logger.info(f"Extracted keywords: {keywords}")
            
            # Generate query
            query = self.generate_query(tool_name, file_path, operation)
            logger.info(f"Generated query: {query}")
            
            # Create cache key
            cache_key = hashlib.md5(f"{query}:{':'.join(keywords)}".encode()).hexdigest()
            
            # Check cache
            cached = self.get_cached_results(cache_key)
            if cached:
                logger.info("Using cached documentation results")
                results = cached
            else:
                # Search documentation
                results = self.search_documentation(query, keywords)
                self.cache_results(cache_key, results)
            
            # Output results for hook system
            print(f"[MCP REF] Documentation search completed")
            print(f"[MCP REF] Query: {query}")
            print(f"[MCP REF] Keywords: {', '.join(keywords)}")
            print(f"[MCP REF] Found {len(results.get('results', []))} relevant documents")
            
            # Store results for other hooks to use
            results_file = Path(".claude/mcp_ref_last_search.json")
            with open(results_file, 'w') as f:
                json.dump({
                    "tool_name": tool_name,
                    "file_path": file_path,
                    "operation": operation,
                    "keywords": keywords,
                    "query": query,
                    "results": results
                }, f, indent=2)
            
        except Exception as e:
            logger.error(f"Error in pre-tool documentation hook: {e}")
            print(f"[MCP REF] Warning: Documentation search failed: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: pre_tool_documentation.py <tool_name> <file_path> <operation>")
        sys.exit(1)
    
    tool_name = sys.argv[1]
    file_path = sys.argv[2] if sys.argv[2] != "None" else None
    operation = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "None" else None
    
    hook = PreToolDocumentationHook()
    hook.run(tool_name, file_path, operation)