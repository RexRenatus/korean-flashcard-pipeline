#!/usr/bin/env python3
"""
MCP Ref Hook: Error Documentation Search
Searches for error solutions in documentation
"""

import sys
import json
import re
from typing import List, Dict, Any
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flashcard_pipeline.utils import get_logger

logger = get_logger(__name__)


class ErrorDocumentationHook:
    """Searches documentation for error solutions"""
    
    def extract_error_keywords(self, error_type: str, error_message: str, stack_trace: str) -> List[str]:
        """Extract keywords from error context"""
        keywords = []
        
        # Add error type
        if error_type and error_type != "None":
            keywords.append(error_type)
            # Extract base error type
            base_error = error_type.split('.')[-1]
            if base_error != error_type:
                keywords.append(base_error)
        
        # Extract from error message
        if error_message and error_message != "None":
            # Look for module names
            modules = re.findall(r"'([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)'", error_message)
            keywords.extend(modules)
            
            # Look for function/method names
            funcs = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\(\)', error_message)
            keywords.extend(funcs)
            
            # Look for common error terms
            error_terms = re.findall(r'\b(missing|invalid|failed|cannot|unable|not found|undefined|null|none)\b', error_message.lower())
            keywords.extend(error_terms[:3])  # Limit error terms
        
        # Extract from stack trace
        if stack_trace and stack_trace != "None":
            # Look for file names and modules
            files = re.findall(r'File "([^"]+)"', stack_trace)
            for file_path in files[:3]:  # Limit to top 3 files
                module = Path(file_path).stem
                if module not in ["<stdin>", "<string>", "__main__"]:
                    keywords.append(module)
            
            # Look for line references with context
            line_refs = re.findall(r'line \d+, in ([a-zA-Z_][a-zA-Z0-9_]*)', stack_trace)
            keywords.extend(line_refs[:2])  # Top 2 function names
        
        # Deduplicate and clean
        keywords = list(set(k for k in keywords if k and len(k) > 2))
        
        # Prioritize specific terms
        priority_terms = []
        for k in keywords:
            if any(term in k.lower() for term in ["error", "exception", "module", "import", "api"]):
                priority_terms.append(k)
        
        # Combine prioritized and regular terms
        final_keywords = priority_terms + [k for k in keywords if k not in priority_terms]
        
        return final_keywords[:10]
    
    def generate_error_query(self, error_type: str, keywords: List[str]) -> str:
        """Generate query for error solution search"""
        if error_type and error_type != "None":
            base_query = f"How to fix {error_type}"
        else:
            base_query = "How to resolve error"
        
        # Add context from keywords
        if keywords:
            context = " ".join(keywords[:3])
            base_query = f"{base_query} with {context}"
        
        return base_query
    
    def suggest_fixes(self, error_type: str, keywords: List[str]) -> List[Dict[str, Any]]:
        """Generate fix suggestions based on error type"""
        suggestions = []
        
        # Common error patterns and fixes
        error_patterns = {
            "ModuleNotFoundError": {
                "suggestion": "Install missing module",
                "command": f"pip install {keywords[0] if keywords else 'module'}",
                "confidence": 0.9
            },
            "ImportError": {
                "suggestion": "Check module installation and Python path",
                "command": "pip list | grep module_name",
                "confidence": 0.85
            },
            "AttributeError": {
                "suggestion": "Verify object has the attribute or method",
                "command": "Check API documentation for correct usage",
                "confidence": 0.8
            },
            "TypeError": {
                "suggestion": "Check argument types and function signatures",
                "command": "Review function parameters",
                "confidence": 0.8
            },
            "ValueError": {
                "suggestion": "Validate input data format and constraints",
                "command": "Add input validation",
                "confidence": 0.75
            },
            "KeyError": {
                "suggestion": "Verify dictionary key exists before access",
                "command": "Use .get() method or check key existence",
                "confidence": 0.85
            },
            "FileNotFoundError": {
                "suggestion": "Check file path and permissions",
                "command": "Verify file exists: ls -la path/to/file",
                "confidence": 0.9
            }
        }
        
        # Check if we have a known error pattern
        for pattern, fix_info in error_patterns.items():
            if error_type and pattern in error_type:
                suggestions.append({
                    "type": "pattern_match",
                    "suggestion": fix_info["suggestion"],
                    "command": fix_info["command"],
                    "confidence": fix_info["confidence"],
                    "documentation_link": f"https://docs.python.org/3/library/exceptions.html#{pattern.lower()}"
                })
                break
        
        # Add keyword-based suggestions
        if "api" in [k.lower() for k in keywords]:
            suggestions.append({
                "type": "api_related",
                "suggestion": "Check API endpoint and authentication",
                "command": "Verify API key and endpoint configuration",
                "confidence": 0.7
            })
        
        if "database" in [k.lower() for k in keywords]:
            suggestions.append({
                "type": "database_related",
                "suggestion": "Check database connection and schema",
                "command": "Verify database is running and accessible",
                "confidence": 0.7
            })
        
        return suggestions
    
    def run(self, error_type: str, error_message: str, stack_trace: str) -> None:
        """Main hook execution"""
        try:
            # Extract keywords
            keywords = self.extract_error_keywords(error_type, error_message, stack_trace)
            logger.info(f"Extracted error keywords: {keywords}")
            
            # Generate query
            query = self.generate_error_query(error_type, keywords)
            logger.info(f"Generated error query: {query}")
            
            # Generate fix suggestions
            suggestions = self.suggest_fixes(error_type, keywords)
            
            # Output results
            print(f"[MCP REF ERROR] Analyzing error: {error_type}")
            print(f"[MCP REF ERROR] Keywords: {', '.join(keywords)}")
            print(f"[MCP REF ERROR] Search query: {query}")
            
            if suggestions:
                print(f"[MCP REF ERROR] Found {len(suggestions)} potential fixes:")
                for i, suggestion in enumerate(suggestions, 1):
                    print(f"  {i}. {suggestion['suggestion']}")
                    if 'command' in suggestion:
                        print(f"     Command: {suggestion['command']}")
                    print(f"     Confidence: {suggestion['confidence']:.0%}")
            
            # Save results for other hooks
            results_file = Path(".claude/mcp_ref_error_analysis.json")
            with open(results_file, 'w') as f:
                json.dump({
                    "error_type": error_type,
                    "error_message": error_message,
                    "keywords": keywords,
                    "query": query,
                    "suggestions": suggestions,
                    "documentation_search": {
                        "query": query,
                        "keywords": keywords,
                        "source": "public"
                    }
                }, f, indent=2)
            
        except Exception as e:
            logger.error(f"Error in error documentation hook: {e}")
            print(f"[MCP REF ERROR] Warning: Error analysis failed: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: error_documentation.py <error_type> [error_message] [stack_trace]")
        sys.exit(1)
    
    error_type = sys.argv[1] if sys.argv[1] != "None" else None
    error_message = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "None" else None
    stack_trace = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "None" else None
    
    hook = ErrorDocumentationHook()
    hook.run(error_type, error_message, stack_trace)