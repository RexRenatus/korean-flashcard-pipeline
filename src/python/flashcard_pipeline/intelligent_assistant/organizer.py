"""
Intelligent Organizer Component

Maintains project structure, documentation, and organization.
"""

import os
import re
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class IntelligentOrganizer:
    """
    Intelligent file and project organization system.
    
    Features:
    - Automatic file categorization
    - Project structure maintenance
    - Documentation updates
    - Dependency tracking
    - Organization suggestions
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.project_root = Path.cwd()
        
        # File categorization patterns
        self.file_categories = {
            "components": ["component", "widget", "view", "_component"],
            "utilities": ["util", "helper", "tool", "utils"],
            "services": ["service", "api", "client", "_service"],
            "models": ["model", "schema", "type", "entity"],
            "tests": ["test", "spec", "_test", ".test"],
            "config": ["config", "settings", "env", ".config"],
            "docs": ["README", "DOCS", ".md", "GUIDE"],
            "migrations": ["migration", "migrate", "_migration"],
            "hooks": ["hook", "_hook", "middleware"],
            "scripts": ["script", ".sh", ".py", "tool"]
        }
        
        # Initialize state
        self.project_structure = {}
        self.documentation_map = {}
        self.dependency_graph = defaultdict(set)
        self.orphaned_files = set()
        self.misplaced_files = {}
        
        # Documentation templates
        self.doc_templates = self._load_doc_templates()
        
        logger.info("Intelligent Organizer initialized")
    
    def initialize(self):
        """Initialize organizer by scanning project."""
        logger.info("Scanning project structure...")
        self.scan_project_structure()
        self.build_documentation_map()
        self.analyze_dependencies()
        logger.info("Project scan complete")
    
    def scan_project_structure(self) -> Dict[str, Any]:
        """Scan and analyze project structure."""
        structure = {
            "directories": {},
            "files": {},
            "statistics": {
                "total_files": 0,
                "total_dirs": 0,
                "file_types": defaultdict(int),
                "categories": defaultdict(int)
            }
        }
        
        ignore_patterns = {
            "__pycache__", ".git", "node_modules", ".pytest_cache",
            "*.pyc", "*.pyo", ".DS_Store", "venv", "env"
        }
        
        for root, dirs, files in os.walk(self.project_root):
            # Filter ignored directories
            dirs[:] = [d for d in dirs if not any(p in d for p in ignore_patterns)]
            
            rel_root = Path(root).relative_to(self.project_root)
            
            for file in files:
                if any(file.endswith(p) or p in file for p in ignore_patterns):
                    continue
                
                file_path = Path(root) / file
                rel_path = file_path.relative_to(self.project_root)
                
                # Categorize file
                category = self.categorize_file(str(rel_path))
                
                # Store file info
                structure["files"][str(rel_path)] = {
                    "path": str(rel_path),
                    "category": category,
                    "size": file_path.stat().st_size,
                    "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    "extension": file_path.suffix
                }
                
                # Update statistics
                structure["statistics"]["total_files"] += 1
                structure["statistics"]["file_types"][file_path.suffix] += 1
                structure["statistics"]["categories"][category] += 1
            
            structure["statistics"]["total_dirs"] = len(dirs)
        
        self.project_structure = structure
        return structure
    
    def categorize_file(self, file_path: str) -> str:
        """Intelligently categorize a file based on name and content."""
        file_name = Path(file_path).name.lower()
        
        # Check against category patterns
        for category, patterns in self.file_categories.items():
            if any(pattern in file_name for pattern in patterns):
                return category
        
        # Check by extension
        extension = Path(file_path).suffix.lower()
        extension_map = {
            ".py": "scripts",
            ".rs": "source",
            ".js": "scripts",
            ".ts": "scripts",
            ".json": "config",
            ".yaml": "config",
            ".yml": "config",
            ".md": "docs",
            ".txt": "docs",
            ".sql": "migrations",
            ".sh": "scripts",
            ".bat": "scripts"
        }
        
        if extension in extension_map:
            return extension_map[extension]
        
        # Check by directory
        parts = Path(file_path).parts
        if "test" in parts or "tests" in parts:
            return "tests"
        elif "doc" in parts or "docs" in parts:
            return "docs"
        elif "src" in parts:
            return "source"
        
        return "uncategorized"
    
    def build_documentation_map(self) -> Dict[str, Any]:
        """Build a map of all documentation in the project."""
        doc_map = {
            "main_docs": [],
            "api_docs": [],
            "guides": [],
            "references": [],
            "missing": []
        }
        
        # Standard documentation files to check
        standard_docs = [
            "README.md",
            "CONTRIBUTING.md",
            "CHANGELOG.md",
            "LICENSE",
            "PROJECT_INDEX.md",
            "API_DOCS.md",
            "ARCHITECTURE.md"
        ]
        
        # Check for standard docs
        for doc in standard_docs:
            doc_path = self.project_root / doc
            if doc_path.exists():
                doc_map["main_docs"].append(str(doc))
            else:
                doc_map["missing"].append(doc)
        
        # Scan for all documentation files
        for file_info in self.project_structure.get("files", {}).values():
            if file_info["category"] == "docs":
                file_path = file_info["path"]
                
                # Categorize documentation
                if "api" in file_path.lower():
                    doc_map["api_docs"].append(file_path)
                elif "guide" in file_path.lower() or "tutorial" in file_path.lower():
                    doc_map["guides"].append(file_path)
                else:
                    doc_map["references"].append(file_path)
        
        self.documentation_map = doc_map
        return doc_map
    
    def analyze_dependencies(self) -> Dict[str, Set[str]]:
        """Analyze file dependencies and imports."""
        import_patterns = {
            "python": [
                r"^\s*import\s+(\S+)",
                r"^\s*from\s+(\S+)\s+import",
            ],
            "javascript": [
                r"^\s*import\s+.*\s+from\s+['\"]([^'\"]+)['\"]",
                r"^\s*const\s+.*\s+=\s+require\(['\"]([^'\"]+)['\"]\)",
            ],
            "rust": [
                r"^\s*use\s+(\S+)(?:::|\s*;)",
                r"^\s*mod\s+(\S+)\s*;",
            ]
        }
        
        for file_info in self.project_structure.get("files", {}).values():
            file_path = self.project_root / file_info["path"]
            
            if not file_path.suffix in [".py", ".js", ".rs", ".ts"]:
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Detect language
                language = {
                    ".py": "python",
                    ".js": "javascript",
                    ".ts": "javascript",
                    ".rs": "rust"
                }.get(file_path.suffix)
                
                if language and language in import_patterns:
                    for pattern in import_patterns[language]:
                        matches = re.findall(pattern, content, re.MULTILINE)
                        for match in matches:
                            self.dependency_graph[str(file_info["path"])].add(match)
            
            except Exception as e:
                logger.warning(f"Failed to analyze dependencies for {file_path}: {e}")
        
        return dict(self.dependency_graph)
    
    def prepare_workspace(self, task_info: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare workspace before task execution."""
        preparation_report = {
            "directories_created": [],
            "missing_files": [],
            "organization_suggestions": [],
            "dependency_check": {}
        }
        
        # Determine required directories based on task
        task_type = task_info.get("type", "general")
        required_dirs = []
        
        if task_type in ["create_test", "test"]:
            required_dirs.extend(["tests", "tests/unit", "tests/integration"])
        elif task_type in ["create_component", "component"]:
            required_dirs.extend(["src/components", "src/components/common"])
        elif task_type in ["documentation", "docs"]:
            required_dirs.extend(["docs", "docs/guides", "docs/api"])
        
        # Create missing directories
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                full_path.mkdir(parents=True, exist_ok=True)
                preparation_report["directories_created"].append(dir_path)
                logger.info(f"Created directory: {dir_path}")
        
        # Check for required documentation
        if not (self.project_root / "README.md").exists():
            preparation_report["missing_files"].append("README.md")
        
        # Check for orphaned files
        self.find_orphaned_files()
        if self.orphaned_files:
            preparation_report["organization_suggestions"].append({
                "type": "orphaned_files",
                "files": list(self.orphaned_files),
                "suggestion": "Consider organizing these files into appropriate directories"
            })
        
        return preparation_report
    
    def check_dependencies(self, task_info: Dict[str, Any]) -> Dict[str, Any]:
        """Check if required dependencies are available."""
        dependency_report = {
            "missing_dependencies": [],
            "outdated_dependencies": [],
            "circular_dependencies": []
        }
        
        # Check for circular dependencies
        circular = self._find_circular_dependencies()
        if circular:
            dependency_report["circular_dependencies"] = circular
        
        return dependency_report
    
    def update_project_structure(self, task_result: Dict[str, Any]) -> Dict[str, Any]:
        """Update project structure after task completion."""
        update_report = {
            "files_organized": [],
            "suggestions": [],
            "documentation_updates": []
        }
        
        modified_files = task_result.get("modified_files", [])
        new_files = task_result.get("new_files", [])
        
        for file_path in new_files:
            # Categorize new file
            category = self.categorize_file(file_path)
            
            # Check if file is in appropriate location
            suggested_location = self._suggest_file_location(file_path, category)
            if suggested_location != file_path:
                self.misplaced_files[file_path] = suggested_location
                update_report["suggestions"].append({
                    "type": "move_file",
                    "file": file_path,
                    "current_location": file_path,
                    "suggested_location": suggested_location,
                    "reason": f"Better organization for {category} files"
                })
        
        # Update project index if needed
        if modified_files or new_files:
            self._update_project_index()
            update_report["documentation_updates"].append("PROJECT_INDEX.md")
        
        return update_report
    
    def update_documentation(self, task_result: Dict[str, Any]) -> Dict[str, Any]:
        """Update project documentation based on changes."""
        doc_updates = {
            "files_updated": [],
            "sections_added": [],
            "references_updated": []
        }
        
        # Check if documentation needs updating
        modified_files = task_result.get("modified_files", [])
        
        for file_path in modified_files:
            # Check if this is a significant file that should be documented
            if self._is_significant_file(file_path):
                # Update relevant documentation
                if "api" in file_path.lower():
                    self._update_api_docs(file_path)
                    doc_updates["files_updated"].append("API_DOCS.md")
                
                if "component" in file_path.lower():
                    self._update_component_docs(file_path)
                    doc_updates["files_updated"].append("COMPONENT_GUIDE.md")
        
        return doc_updates
    
    def find_orphaned_files(self) -> Set[str]:
        """Find files that don't belong to any clear category or location."""
        orphaned = set()
        
        for file_info in self.project_structure.get("files", {}).values():
            file_path = file_info["path"]
            category = file_info["category"]
            
            # Check if file is in root when it shouldn't be
            if "/" not in file_path and category != "docs":
                if not file_path in ["README.md", "LICENSE", "setup.py", "requirements.txt"]:
                    orphaned.add(file_path)
            
            # Check if uncategorized
            if category == "uncategorized":
                orphaned.add(file_path)
        
        self.orphaned_files = orphaned
        return orphaned
    
    def suggest_refactoring(self) -> List[Dict[str, Any]]:
        """Suggest organizational improvements."""
        suggestions = []
        
        # Check for misplaced files
        for file_path, suggested_location in self.misplaced_files.items():
            suggestions.append({
                "type": "move_file",
                "priority": "medium",
                "file": file_path,
                "suggested_location": suggested_location,
                "reason": "Better organization based on file type"
            })
        
        # Check for files that should be split
        large_files = self._find_large_files(threshold=500)
        for file_path in large_files:
            suggestions.append({
                "type": "split_file",
                "priority": "low",
                "file": file_path,
                "reason": "File exceeds recommended size (500 lines)"
            })
        
        # Check for missing documentation
        for missing_doc in self.documentation_map.get("missing", []):
            suggestions.append({
                "type": "create_documentation",
                "priority": "high" if missing_doc == "README.md" else "medium",
                "file": missing_doc,
                "reason": "Standard documentation file is missing"
            })
        
        return suggestions
    
    def get_status(self) -> Dict[str, Any]:
        """Get current organizer status."""
        return {
            "total_files": len(self.project_structure.get("files", {})),
            "orphaned_files": len(self.orphaned_files),
            "misplaced_files": len(self.misplaced_files),
            "missing_docs": len(self.documentation_map.get("missing", [])),
            "categories": dict(self.project_structure.get("statistics", {}).get("categories", {}))
        }
    
    def shutdown(self):
        """Clean shutdown."""
        # Save any pending updates
        if hasattr(self, "_pending_updates"):
            self._flush_pending_updates()
        logger.info("Intelligent Organizer shutdown complete")
    
    # Helper methods
    
    def _load_doc_templates(self) -> Dict[str, str]:
        """Load documentation templates."""
        return {
            "README": """# {project_name}

## Overview
{description}

## Installation
```bash
{installation_steps}
```

## Usage
{usage_examples}

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License
{license}
""",
            "PROJECT_INDEX": """# PROJECT INDEX
Last Updated: {timestamp}

## Project Structure
{structure_tree}

## Component Map
{component_map}

## File Categories
{file_categories}

## Recent Changes
{recent_changes}
"""
        }
    
    def _suggest_file_location(self, file_path: str, category: str) -> str:
        """Suggest appropriate location for a file based on its category."""
        category_dirs = {
            "tests": "tests",
            "components": "src/components",
            "utilities": "src/utils",
            "services": "src/services",
            "models": "src/models",
            "config": "config",
            "docs": "docs",
            "migrations": "migrations",
            "scripts": "scripts"
        }
        
        suggested_dir = category_dirs.get(category, "src")
        file_name = Path(file_path).name
        
        return str(Path(suggested_dir) / file_name)
    
    def _find_circular_dependencies(self) -> List[List[str]]:
        """Find circular dependencies in the project."""
        # Simplified circular dependency detection
        circular = []
        visited = set()
        
        def dfs(node, path):
            if node in path:
                cycle_start = path.index(node)
                circular.append(path[cycle_start:] + [node])
                return
            
            if node in visited:
                return
            
            visited.add(node)
            path.append(node)
            
            for dep in self.dependency_graph.get(node, []):
                dfs(dep, path.copy())
        
        for node in self.dependency_graph:
            if node not in visited:
                dfs(node, [])
        
        return circular
    
    def _find_large_files(self, threshold: int = 500) -> List[str]:
        """Find files exceeding line threshold."""
        large_files = []
        
        for file_info in self.project_structure.get("files", {}).values():
            if file_info["category"] in ["source", "components", "services"]:
                file_path = self.project_root / file_info["path"]
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        line_count = sum(1 for _ in f)
                    
                    if line_count > threshold:
                        large_files.append(file_info["path"])
                except:
                    pass
        
        return large_files
    
    def _is_significant_file(self, file_path: str) -> bool:
        """Determine if a file is significant enough to update documentation."""
        # Files that should trigger documentation updates
        significant_patterns = [
            "api", "endpoint", "route", "component", "service",
            "model", "schema", "interface", "public"
        ]
        
        return any(pattern in file_path.lower() for pattern in significant_patterns)
    
    def _update_project_index(self):
        """Update PROJECT_INDEX.md with current structure."""
        index_path = self.project_root / "PROJECT_INDEX.md"
        
        content = self.doc_templates["PROJECT_INDEX"].format(
            timestamp=datetime.now().isoformat(),
            structure_tree=self._generate_structure_tree(),
            component_map=self._generate_component_map(),
            file_categories=self._format_file_categories(),
            recent_changes=self._get_recent_changes()
        )
        
        try:
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info("Updated PROJECT_INDEX.md")
        except Exception as e:
            logger.error(f"Failed to update PROJECT_INDEX.md: {e}")
    
    def _generate_structure_tree(self) -> str:
        """Generate a tree representation of project structure."""
        # Simplified tree generation
        lines = []
        
        def add_directory(path, prefix=""):
            try:
                items = sorted(os.listdir(path))
                for i, item in enumerate(items):
                    if item.startswith('.'):
                        continue
                    
                    item_path = path / item
                    is_last = i == len(items) - 1
                    
                    current_prefix = "└── " if is_last else "├── "
                    lines.append(f"{prefix}{current_prefix}{item}")
                    
                    if item_path.is_dir() and not item in ["__pycache__", "node_modules"]:
                        extension = "    " if is_last else "│   "
                        add_directory(item_path, prefix + extension)
            except:
                pass
        
        add_directory(self.project_root)
        return "\n".join(lines[:50])  # Limit to 50 lines
    
    def _generate_component_map(self) -> str:
        """Generate a map of key components."""
        components = defaultdict(list)
        
        for file_info in self.project_structure.get("files", {}).values():
            if file_info["category"] in ["components", "services", "models"]:
                components[file_info["category"]].append(file_info["path"])
        
        lines = []
        for category, files in components.items():
            lines.append(f"\n### {category.title()}")
            for file in sorted(files)[:10]:  # Limit to 10 per category
                lines.append(f"- {file}")
        
        return "\n".join(lines)
    
    def _format_file_categories(self) -> str:
        """Format file category statistics."""
        stats = self.project_structure.get("statistics", {}).get("categories", {})
        
        lines = []
        for category, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"- {category}: {count} files")
        
        return "\n".join(lines)
    
    def _get_recent_changes(self) -> str:
        """Get recently modified files."""
        recent_files = []
        
        for file_info in self.project_structure.get("files", {}).values():
            recent_files.append({
                "path": file_info["path"],
                "modified": datetime.fromisoformat(file_info["modified"])
            })
        
        # Sort by modification time
        recent_files.sort(key=lambda x: x["modified"], reverse=True)
        
        lines = []
        for file in recent_files[:10]:  # Top 10 recent files
            time_str = file["modified"].strftime("%Y-%m-%d %H:%M")
            lines.append(f"- {file['path']} ({time_str})")
        
        return "\n".join(lines)
    
    def _update_api_docs(self, file_path: str):
        """Update API documentation for a file."""
        # Placeholder for API doc updates
        logger.info(f"Would update API docs for {file_path}")
    
    def _update_component_docs(self, file_path: str):
        """Update component documentation for a file."""
        # Placeholder for component doc updates
        logger.info(f"Would update component docs for {file_path}")
    
    def _flush_pending_updates(self):
        """Flush any pending documentation updates."""
        # Placeholder for flushing updates
        pass