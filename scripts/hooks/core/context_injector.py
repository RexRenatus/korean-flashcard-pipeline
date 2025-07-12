#!/usr/bin/env python3
"""
Context Injector for Hook System
Automatically enriches hook execution context with project information.
Inspired by Claude Code Development Kit's context injection pattern.
"""
import os
import sys
import json
import subprocess
import hashlib
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import logging

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from scripts.hooks.cache_manager import get_cache_manager
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False

class ContextInjector:
    """
    Injects rich context into hook executions for better decision making.
    """
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root or os.getcwd())
        self.logger = logging.getLogger(__name__)
        self.cache = get_cache_manager() if CACHE_AVAILABLE else None
        self._project_info_cache = None
        self._project_info_cache_time = None
        
    async def enrich(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich the context with project information.
        """
        # Start with original context
        enriched = context.copy()
        
        # Add project information
        project_info = self._get_project_info()
        enriched['project'] = project_info
        
        # Add file-specific context if file_path is provided
        if 'file_path' in context and context['file_path']:
            file_context = self._get_file_context(context['file_path'])
            enriched['file'] = file_context
            
        # Add operation-specific context
        if 'operation' in context:
            operation_context = self._get_operation_context(
                context['operation'], 
                context.get('tool', '')
            )
            enriched['operation_context'] = operation_context
            
        # Add related documentation
        if self._should_inject_documentation(context):
            docs = self._get_relevant_documentation(context)
            enriched['documentation'] = docs
            
        # Add environment context
        enriched['environment'] = self._get_environment_context()
        
        # Add timing context
        enriched['timing'] = {
            'timestamp': datetime.now().isoformat(),
            'session_start': os.environ.get('CLAUDE_SESSION_START', ''),
            'operation_count': self._get_operation_count()
        }
        
        return enriched
        
    def _get_project_info(self) -> Dict[str, Any]:
        """Get cached project information."""
        # Cache for 5 minutes
        if (self._project_info_cache and 
            self._project_info_cache_time and 
            (datetime.now() - self._project_info_cache_time).seconds < 300):
            return self._project_info_cache
            
        info = {
            'root': str(self.project_root),
            'name': self.project_root.name,
            'type': self._detect_project_type(),
            'languages': self._detect_languages(),
            'has_tests': self._has_tests(),
            'has_ci': self._has_ci(),
            'git': self._get_git_info(),
            'structure': self._get_project_structure()
        }
        
        self._project_info_cache = info
        self._project_info_cache_time = datetime.now()
        return info
        
    def _detect_project_type(self) -> str:
        """Detect the type of project."""
        if (self.project_root / 'pyproject.toml').exists():
            return 'python'
        elif (self.project_root / 'package.json').exists():
            return 'javascript'
        elif (self.project_root / 'Cargo.toml').exists():
            return 'rust'
        elif (self.project_root / 'go.mod').exists():
            return 'go'
        else:
            return 'unknown'
            
    def _detect_languages(self) -> List[str]:
        """Detect languages used in the project."""
        languages = set()
        
        # Common file extensions
        extensions = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.rs': 'rust',
            '.go': 'go',
            '.java': 'java',
            '.cpp': 'c++',
            '.c': 'c',
            '.sh': 'shell',
            '.yml': 'yaml',
            '.json': 'json'
        }
        
        for ext, lang in extensions.items():
            if list(self.project_root.rglob(f'*{ext}')):
                languages.add(lang)
                
        return sorted(list(languages))
        
    def _has_tests(self) -> bool:
        """Check if project has tests."""
        test_patterns = ['test_*.py', '*_test.py', 'tests/', 'test/', '__tests__/']
        for pattern in test_patterns:
            if list(self.project_root.rglob(pattern)):
                return True
        return False
        
    def _has_ci(self) -> bool:
        """Check if project has CI/CD configuration."""
        ci_files = ['.github/workflows', '.gitlab-ci.yml', '.travis.yml', 'Jenkinsfile']
        for ci_file in ci_files:
            if (self.project_root / ci_file).exists():
                return True
        return False
        
    def _get_git_info(self) -> Dict[str, Any]:
        """Get git repository information."""
        try:
            # Get current branch
            branch = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            ).stdout.strip()
            
            # Get last commit
            commit = subprocess.run(
                ['git', 'rev-parse', '--short', 'HEAD'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            ).stdout.strip()
            
            # Check if dirty
            status = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            ).stdout
            
            return {
                'branch': branch,
                'commit': commit,
                'is_dirty': bool(status.strip()),
                'modified_files': len(status.strip().split('\n')) if status.strip() else 0
            }
        except:
            return {}
            
    def _get_project_structure(self) -> Dict[str, Any]:
        """Get high-level project structure."""
        structure = {
            'directories': [],
            'key_files': []
        }
        
        # Important directories
        important_dirs = ['src', 'tests', 'docs', 'scripts', 'config', '.claude']
        for dir_name in important_dirs:
            if (self.project_root / dir_name).is_dir():
                structure['directories'].append(dir_name)
                
        # Key files
        key_files = [
            'README.md', 'CLAUDE.md', 'pyproject.toml', 'package.json',
            'requirements.txt', 'Dockerfile', '.env.example'
        ]
        for file_name in key_files:
            if (self.project_root / file_name).exists():
                structure['key_files'].append(file_name)
                
        return structure
        
    def _get_file_context(self, file_path: str) -> Dict[str, Any]:
        """Get context specific to a file."""
        path = Path(file_path)
        
        if not path.exists():
            return {'exists': False}
            
        # Get file info
        stat = path.stat()
        
        # Calculate file hash for caching
        with open(path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()[:8]
            
        context = {
            'exists': True,
            'path': str(path),
            'name': path.name,
            'extension': path.suffix,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'hash': file_hash,
            'is_test': self._is_test_file(path),
            'module': self._get_module_name(path)
        }
        
        # Add language-specific context
        if path.suffix == '.py':
            context['python'] = self._get_python_file_context(path)
            
        return context
        
    def _is_test_file(self, path: Path) -> bool:
        """Check if file is a test file."""
        name = path.name.lower()
        return (name.startswith('test_') or 
                name.endswith('_test.py') or 
                'test' in path.parts)
                
    def _get_module_name(self, path: Path) -> Optional[str]:
        """Get Python module name from path."""
        try:
            rel_path = path.relative_to(self.project_root)
            if path.suffix == '.py':
                parts = list(rel_path.parts[:-1]) + [rel_path.stem]
                return '.'.join(parts)
        except:
            pass
        return None
        
    def _get_python_file_context(self, path: Path) -> Dict[str, Any]:
        """Get Python-specific file context."""
        context = {
            'imports': [],
            'classes': [],
            'functions': []
        }
        
        try:
            import ast
            with open(path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
                
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        context['imports'].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        context['imports'].append(node.module)
                elif isinstance(node, ast.ClassDef):
                    context['classes'].append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    if not any(node.name.startswith(c.lower() + '_') for c in context['classes']):
                        context['functions'].append(node.name)
        except:
            pass
            
        return context
        
    def _get_operation_context(self, operation: str, tool: str) -> Dict[str, Any]:
        """Get context specific to the operation being performed."""
        context = {
            'operation': operation,
            'tool': tool,
            'requires_validation': operation in ['validate', 'pre-check'],
            'modifies_files': tool in ['Write', 'Edit', 'MultiEdit'],
            'is_documentation': operation == 'documentation',
            'is_error_handling': operation == 'error'
        }
        
        # Add operation-specific hints
        if operation == 'validate':
            context['validation_hints'] = {
                'check_imports': True,
                'check_security': True,
                'check_style': True,
                'check_complexity': True
            }
        elif operation == 'documentation':
            context['doc_hints'] = {
                'include_examples': True,
                'search_current_year': True,
                'prefer_official_docs': True
            }
            
        return context
        
    def _should_inject_documentation(self, context: Dict[str, Any]) -> bool:
        """Determine if documentation should be injected."""
        # Always inject for documentation operations
        if context.get('operation') == 'documentation':
            return True
            
        # Inject for error handling
        if context.get('operation') == 'error':
            return True
            
        # Inject for new file creation
        if context.get('tool') == 'Write' and not os.path.exists(context.get('file_path', '')):
            return True
            
        return False
        
    def _get_relevant_documentation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get relevant documentation based on context."""
        docs = {
            'project_docs': [],
            'suggested_reads': []
        }
        
        # Check for CLAUDE.md
        claude_md = self.project_root / 'CLAUDE.md'
        if claude_md.exists():
            docs['project_docs'].append({
                'path': 'CLAUDE.md',
                'type': 'project_instructions',
                'priority': 'high'
            })
            
        # Check for README.md
        readme = self.project_root / 'README.md'
        if readme.exists():
            docs['project_docs'].append({
                'path': 'README.md',
                'type': 'project_overview',
                'priority': 'medium'
            })
            
        # Add context-specific suggestions
        if context.get('operation') == 'error':
            docs['suggested_reads'].append('Search for error solutions in documentation')
        elif context.get('file', {}).get('is_test'):
            docs['suggested_reads'].append('Review test patterns and best practices')
            
        return docs
        
    def _get_environment_context(self) -> Dict[str, Any]:
        """Get environment context."""
        return {
            'python_version': sys.version.split()[0],
            'platform': sys.platform,
            'cwd': os.getcwd(),
            'venv_active': 'VIRTUAL_ENV' in os.environ,
            'claude_session': bool(os.environ.get('CLAUDE_SESSION_START'))
        }
        
    def _get_operation_count(self) -> int:
        """Get count of operations in current session."""
        # This could be tracked more sophisticatedly
        return int(os.environ.get('CLAUDE_OPERATION_COUNT', '0'))
        
    def export_context_template(self) -> Dict[str, Any]:
        """Export a template of the context structure."""
        return {
            'project': {
                'root': 'project root path',
                'name': 'project name',
                'type': 'detected project type',
                'languages': ['detected languages'],
                'has_tests': 'boolean',
                'has_ci': 'boolean',
                'git': {
                    'branch': 'current branch',
                    'commit': 'current commit',
                    'is_dirty': 'boolean',
                    'modified_files': 'count'
                },
                'structure': {
                    'directories': ['important directories'],
                    'key_files': ['key files']
                }
            },
            'file': {
                'exists': 'boolean',
                'path': 'file path',
                'name': 'file name',
                'extension': 'file extension',
                'size': 'file size',
                'modified': 'last modified',
                'hash': 'file hash',
                'is_test': 'boolean',
                'module': 'python module name'
            },
            'operation_context': {
                'operation': 'operation type',
                'tool': 'tool name',
                'requires_validation': 'boolean',
                'modifies_files': 'boolean'
            },
            'documentation': {
                'project_docs': ['available project docs'],
                'suggested_reads': ['suggested documentation']
            },
            'environment': {
                'python_version': 'version',
                'platform': 'platform',
                'cwd': 'current directory',
                'venv_active': 'boolean',
                'claude_session': 'boolean'
            },
            'timing': {
                'timestamp': 'current time',
                'session_start': 'session start time',
                'operation_count': 'operations in session'
            }
        }

# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test_context_injection():
        injector = ContextInjector()
        
        # Test context
        test_context = {
            'tool': 'Write',
            'operation': 'validate',
            'file_path': __file__
        }
        
        # Enrich context
        enriched = await injector.enrich(test_context)
        
        # Print enriched context
        print(json.dumps(enriched, indent=2, default=str))
        
    asyncio.run(test_context_injection())