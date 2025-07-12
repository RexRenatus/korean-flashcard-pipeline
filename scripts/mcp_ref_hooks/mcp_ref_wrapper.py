#!/usr/bin/env python3
"""
MCP Ref Wrapper - Direct interface to MCP Ref documentation search
This demonstrates how to call the MCP Ref tool programmatically
"""

import json
import sys
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flashcard_pipeline.utils import get_logger

logger = get_logger(__name__)


class MCPRefWrapper:
    """Wrapper for MCP Ref documentation search tool"""
    
    def __init__(self):
        self.cache_dir = Path(".claude/mcp_ref_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.current_year = datetime.now().year
    
    def search_documentation(
        self,
        query: str,
        keywords: List[str],
        source: str = "public"
    ) -> Dict[str, Any]:
        """
        Search documentation using MCP Ref tool
        
        Args:
            query: Full sentence or question to search
            keywords: List of keywords for grep-like search
            source: 'public', 'private', or 'web'
        
        Returns:
            Search results with documentation
        """
        # Ensure current year is in query and keywords
        if str(self.current_year) not in query:
            query = f"{query} {self.current_year}"
        
        if str(self.current_year) not in keywords:
            keywords = [str(self.current_year)] + keywords
        
        # This is a demonstration of the structure
        # In actual use, this would call the MCP tool:
        # mcp__Ref__ref_search_documentation(query=query, keyWords=keywords, source=source)
        
        print(f"[MCP REF] Searching documentation...")
        print(f"  Query: {query}")
        print(f"  Keywords: {', '.join(keywords)}")
        print(f"  Source: {source}")
        
        # Simulated response structure
        results = {
            "status": "success",
            "query": query,
            "keywords": keywords,
            "source": source,
            "results": [
                {
                    "title": "Example Documentation Result",
                    "url": "https://docs.example.com/api/reference",
                    "snippet": "This would contain the relevant documentation snippet...",
                    "relevance_score": 0.95,
                    "context": "API Reference"
                }
            ],
            "total_results": 1,
            "search_time_ms": 250
        }
        
        return results
    
    def read_url(self, url: str) -> str:
        """
        Fetch and convert URL content to markdown
        
        Args:
            url: URL to fetch
            
        Returns:
            Markdown content
        """
        # This would call: mcp__Ref__ref_read_url(url=url)
        
        print(f"[MCP REF] Fetching URL: {url}")
        
        # Simulated response
        return f"""# Documentation from {url}

## Overview
This is the fetched and converted content from the URL.

## API Reference
- Function descriptions
- Parameter details
- Example usage

## Code Examples
```python
# Example code from documentation
def example_function():
    pass
```
"""
    
    def extract_keywords_from_code(self, code: str) -> List[str]:
        """Extract relevant keywords from code snippet"""
        import re
        
        keywords = []
        
        # Extract imports
        imports = re.findall(r'(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)', code)
        keywords.extend(imports)
        
        # Extract class names
        classes = re.findall(r'class\s+([A-Z][a-zA-Z0-9_]*)', code)
        keywords.extend(classes)
        
        # Extract function names
        functions = re.findall(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)', code)
        keywords.extend(functions)
        
        # Extract common API terms
        api_terms = re.findall(r'\b(api|client|server|request|response|endpoint|auth|token)\b', code.lower())
        keywords.extend(set(api_terms))
        
        return list(set(keywords))[:10]
    
    def search_error_solution(self, error_type: str, error_message: str) -> Dict[str, Any]:
        """Search for error solutions"""
        # Extract keywords from error
        keywords = [error_type, str(self.current_year)]
        
        # Extract module names from error message
        import re
        modules = re.findall(r"'([a-zA-Z_][a-zA-Z0-9_]*)'", error_message)
        keywords.extend(modules)
        
        query = f"How to fix {error_type}: {error_message} in {self.current_year}"
        
        return self.search_documentation(query, keywords, "public")
    
    def search_api_usage(self, api_name: str, method_name: Optional[str] = None) -> Dict[str, Any]:
        """Search for API usage examples"""
        keywords = [api_name, str(self.current_year)]
        if method_name:
            keywords.append(method_name)
        
        query = f"How to use {api_name}"
        if method_name:
            query += f" {method_name} method"
        query += f" with examples in {self.current_year}"
        
        return self.search_documentation(query, keywords, "public")
    
    def search_best_practices(self, topic: str, language: str = "python") -> Dict[str, Any]:
        """Search for best practices"""
        keywords = [topic, language, "best", "practices", str(self.current_year)]
        query = f"Best practices for {topic} in {language} {self.current_year}"
        
        return self.search_documentation(query, keywords, "public")


def main():
    """Example usage of MCP Ref wrapper"""
    wrapper = MCPRefWrapper()
    
    # Example 1: Search for error solution
    print("\n=== Example 1: Error Solution ===")
    error_results = wrapper.search_error_solution(
        "ModuleNotFoundError",
        "No module named 'anthropic'"
    )
    print(json.dumps(error_results, indent=2))
    
    # Example 2: Search for API usage
    print("\n=== Example 2: API Usage ===")
    api_results = wrapper.search_api_usage("APIClient", "initialize")
    print(json.dumps(api_results, indent=2))
    
    # Example 3: Search for best practices
    print("\n=== Example 3: Best Practices ===")
    best_practices = wrapper.search_best_practices("rate limiting", "python")
    print(json.dumps(best_practices, indent=2))
    
    # Example 4: Extract keywords from code
    print("\n=== Example 4: Keyword Extraction ===")
    sample_code = """
from flashcard_pipeline.api_client import APIClient
import asyncio

class RateLimiter:
    def __init__(self, api_client):
        self.client = api_client
        self.token_bucket = TokenBucket()
    
    async def make_request(self, endpoint):
        await self.token_bucket.acquire()
        return await self.client.post(endpoint)
"""
    keywords = wrapper.extract_keywords_from_code(sample_code)
    print(f"Extracted keywords: {keywords}")
    
    # Example 5: Read URL content
    print("\n=== Example 5: Read URL ===")
    content = wrapper.read_url("https://docs.anthropic.com/api/rate-limits")
    print(content[:200] + "...")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Command line interface
        command = sys.argv[1]
        wrapper = MCPRefWrapper()
        
        if command == "search":
            if len(sys.argv) < 4:
                print("Usage: mcp_ref_wrapper.py search <query> <keyword1,keyword2,...> [source]")
                sys.exit(1)
            query = sys.argv[2]
            keywords = sys.argv[3].split(",")
            source = sys.argv[4] if len(sys.argv) > 4 else "public"
            
            results = wrapper.search_documentation(query, keywords, source)
            print(json.dumps(results, indent=2))
        
        elif command == "error":
            if len(sys.argv) < 4:
                print("Usage: mcp_ref_wrapper.py error <error_type> <error_message>")
                sys.exit(1)
            error_type = sys.argv[2]
            error_message = sys.argv[3]
            
            results = wrapper.search_error_solution(error_type, error_message)
            print(json.dumps(results, indent=2))
        
        elif command == "url":
            if len(sys.argv) < 3:
                print("Usage: mcp_ref_wrapper.py url <url>")
                sys.exit(1)
            url = sys.argv[2]
            
            content = wrapper.read_url(url)
            print(content)
        
        else:
            print(f"Unknown command: {command}")
            print("Available commands: search, error, url")
            sys.exit(1)
    else:
        # Run examples
        main()