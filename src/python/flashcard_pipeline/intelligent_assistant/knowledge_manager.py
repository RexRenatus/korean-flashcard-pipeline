#!/usr/bin/env python3
"""
Dynamic Knowledge Management System
Captures, organizes, and retrieves project knowledge and insights
"""
import json
import sqlite3
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
import re
from collections import defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class KnowledgeType(Enum):
    """Types of knowledge we manage"""
    CONCEPT = "concept"
    PATTERN = "pattern"
    SOLUTION = "solution"
    BEST_PRACTICE = "best_practice"
    LESSON_LEARNED = "lesson_learned"
    ARCHITECTURE = "architecture"
    DEPENDENCY = "dependency"
    GOTCHA = "gotcha"
    OPTIMIZATION = "optimization"
    TROUBLESHOOTING = "troubleshooting"

class KnowledgeSource(Enum):
    """Source of knowledge"""
    CODE_ANALYSIS = "code_analysis"
    ERROR_RESOLUTION = "error_resolution"
    USER_FEEDBACK = "user_feedback"
    DOCUMENTATION = "documentation"
    EXTERNAL_REFERENCE = "external_reference"
    AI_INSIGHT = "ai_insight"
    TEST_RESULTS = "test_results"

@dataclass
class KnowledgeItem:
    """A single piece of knowledge"""
    id: str
    type: KnowledgeType
    title: str
    content: str
    context: str
    tags: List[str]
    source: KnowledgeSource
    confidence: float
    created_at: datetime
    updated_at: datetime
    usage_count: int = 0
    related_files: List[str] = field(default_factory=list)
    related_items: List[str] = field(default_factory=list)
    examples: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class KnowledgeQuery:
    """Query for retrieving knowledge"""
    query: str
    types: Optional[List[KnowledgeType]] = None
    tags: Optional[List[str]] = None
    context: Optional[str] = None
    min_confidence: float = 0.5
    max_results: int = 10

class DynamicKnowledgeManager:
    """Manages project knowledge dynamically"""
    
    def __init__(self, knowledge_db: str = ".claude/knowledge_base.db"):
        self.knowledge_db = knowledge_db
        self.cache_dir = Path(".claude/knowledge_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.knowledge_vectors = {}
        self._load_knowledge_vectors()
        
        # Pattern recognition
        self.patterns = {
            'error_pattern': re.compile(r'(error|exception|fail|bug|issue)', re.I),
            'solution_pattern': re.compile(r'(fix|solve|resolve|workaround|solution)', re.I),
            'optimization_pattern': re.compile(r'(optimize|improve|performance|speed|efficiency)', re.I),
            'architecture_pattern': re.compile(r'(design|architecture|structure|pattern|framework)', re.I),
        }
        
        # Knowledge graph
        self.knowledge_graph = defaultdict(set)
        self._build_knowledge_graph()
    
    def _init_database(self):
        """Initialize knowledge database"""
        conn = sqlite3.connect(self.knowledge_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_items (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                context TEXT,
                tags TEXT,
                source TEXT NOT NULL,
                confidence REAL,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                usage_count INTEGER DEFAULT 0,
                related_files TEXT,
                related_items TEXT,
                examples TEXT,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_relationships (
                item1_id TEXT,
                item2_id TEXT,
                relationship_type TEXT,
                strength REAL,
                FOREIGN KEY (item1_id) REFERENCES knowledge_items(id),
                FOREIGN KEY (item2_id) REFERENCES knowledge_items(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT,
                used_at TIMESTAMP,
                context TEXT,
                feedback TEXT,
                FOREIGN KEY (item_id) REFERENCES knowledge_items(id)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_knowledge_type ON knowledge_items(type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_knowledge_tags ON knowledge_items(tags)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_knowledge_confidence ON knowledge_items(confidence)')
        
        conn.commit()
        conn.close()
    
    def add_knowledge(self, item: KnowledgeItem) -> str:
        """Add new knowledge item"""
        conn = sqlite3.connect(self.knowledge_db)
        cursor = conn.cursor()
        
        # Generate ID if not provided
        if not item.id:
            item.id = f"{item.type.value}_{datetime.now().timestamp()}"
        
        cursor.execute('''
            INSERT OR REPLACE INTO knowledge_items
            (id, type, title, content, context, tags, source, confidence,
             created_at, updated_at, usage_count, related_files, related_items,
             examples, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item.id,
            item.type.value,
            item.title,
            item.content,
            item.context,
            json.dumps(item.tags),
            item.source.value,
            item.confidence,
            item.created_at.isoformat(),
            item.updated_at.isoformat(),
            item.usage_count,
            json.dumps(item.related_files),
            json.dumps(item.related_items),
            json.dumps(item.examples),
            json.dumps(item.metadata)
        ))
        
        conn.commit()
        conn.close()
        
        # Update vectors
        self._update_knowledge_vector(item)
        
        # Update knowledge graph
        self._update_knowledge_graph(item)
        
        return item.id
    
    def search_knowledge(self, query: KnowledgeQuery) -> List[KnowledgeItem]:
        """Search for relevant knowledge"""
        # First, get candidates from database
        candidates = self._get_candidates_from_db(query)
        
        if not candidates:
            return []
        
        # Then rank by relevance using vector similarity
        ranked_items = self._rank_by_relevance(candidates, query.query)
        
        # Apply confidence threshold
        filtered_items = [
            item for item in ranked_items
            if item.confidence >= query.min_confidence
        ]
        
        # Return top results
        return filtered_items[:query.max_results]
    
    def _get_candidates_from_db(self, query: KnowledgeQuery) -> List[KnowledgeItem]:
        """Get candidate items from database"""
        conn = sqlite3.connect(self.knowledge_db)
        cursor = conn.cursor()
        
        # Build SQL query
        sql = "SELECT * FROM knowledge_items WHERE 1=1"
        params = []
        
        if query.types:
            type_placeholders = ','.join('?' for _ in query.types)
            sql += f" AND type IN ({type_placeholders})"
            params.extend([t.value for t in query.types])
        
        if query.tags:
            # Tags are stored as JSON, so we need to check each
            tag_conditions = []
            for tag in query.tags:
                tag_conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')
            sql += f" AND ({' OR '.join(tag_conditions)})"
        
        if query.context:
            sql += " AND (context LIKE ? OR content LIKE ?)"
            params.extend([f"%{query.context}%", f"%{query.context}%"])
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to KnowledgeItem objects
        items = []
        for row in rows:
            items.append(self._row_to_knowledge_item(row))
        
        return items
    
    def _row_to_knowledge_item(self, row: Tuple) -> KnowledgeItem:
        """Convert database row to KnowledgeItem"""
        return KnowledgeItem(
            id=row[0],
            type=KnowledgeType(row[1]),
            title=row[2],
            content=row[3],
            context=row[4] or "",
            tags=json.loads(row[5]) if row[5] else [],
            source=KnowledgeSource(row[6]),
            confidence=row[7],
            created_at=datetime.fromisoformat(row[8]),
            updated_at=datetime.fromisoformat(row[9]),
            usage_count=row[10],
            related_files=json.loads(row[11]) if row[11] else [],
            related_items=json.loads(row[12]) if row[12] else [],
            examples=json.loads(row[13]) if row[13] else [],
            metadata=json.loads(row[14]) if row[14] else {}
        )
    
    def _rank_by_relevance(self, items: List[KnowledgeItem], query: str) -> List[KnowledgeItem]:
        """Rank items by relevance to query"""
        if not items:
            return []
        
        # Prepare texts for vectorization
        item_texts = [f"{item.title} {item.content}" for item in items]
        
        try:
            # Fit vectorizer if needed
            if not hasattr(self.vectorizer, 'vocabulary_'):
                all_texts = item_texts + [query]
                self.vectorizer.fit(all_texts)
            
            # Vectorize items and query
            item_vectors = self.vectorizer.transform(item_texts)
            query_vector = self.vectorizer.transform([query])
            
            # Calculate similarities
            similarities = cosine_similarity(query_vector, item_vectors).flatten()
            
            # Combine with confidence scores
            scores = []
            for i, item in enumerate(items):
                # Weight by both similarity and confidence
                combined_score = similarities[i] * 0.7 + item.confidence * 0.3
                scores.append((combined_score, item))
            
            # Sort by score
            scores.sort(key=lambda x: x[0], reverse=True)
            
            return [item for _, item in scores]
        
        except Exception as e:
            # Fallback to simple text matching
            return sorted(items, key=lambda x: x.confidence, reverse=True)
    
    def _update_knowledge_vector(self, item: KnowledgeItem):
        """Update vector representation of knowledge item"""
        text = f"{item.title} {item.content}"
        try:
            vector = self.vectorizer.transform([text])
            self.knowledge_vectors[item.id] = vector
        except:
            pass
    
    def _build_knowledge_graph(self):
        """Build knowledge graph from relationships"""
        conn = sqlite3.connect(self.knowledge_db)
        cursor = conn.cursor()
        
        cursor.execute('SELECT item1_id, item2_id, relationship_type FROM knowledge_relationships')
        for row in cursor.fetchall():
            self.knowledge_graph[row[0]].add((row[1], row[2]))
            self.knowledge_graph[row[1]].add((row[0], row[2]))
        
        conn.close()
    
    def _update_knowledge_graph(self, item: KnowledgeItem):
        """Update knowledge graph with new item"""
        # Find related items
        for related_id in item.related_items:
            self.knowledge_graph[item.id].add((related_id, 'related'))
            self.knowledge_graph[related_id].add((item.id, 'related'))
            
            # Store in database
            conn = sqlite3.connect(self.knowledge_db)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO knowledge_relationships
                (item1_id, item2_id, relationship_type, strength)
                VALUES (?, ?, ?, ?)
            ''', (item.id, related_id, 'related', 0.8))
            conn.commit()
            conn.close()
    
    def _load_knowledge_vectors(self):
        """Load all knowledge vectors for similarity search"""
        conn = sqlite3.connect(self.knowledge_db)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, title, content FROM knowledge_items')
        texts = []
        ids = []
        
        for row in cursor.fetchall():
            ids.append(row[0])
            texts.append(f"{row[1]} {row[2]}")
        
        conn.close()
        
        if texts:
            try:
                self.vectorizer.fit(texts)
                vectors = self.vectorizer.transform(texts)
                for i, item_id in enumerate(ids):
                    self.knowledge_vectors[item_id] = vectors[i]
            except:
                pass
    
    def extract_knowledge_from_code(self, file_path: str, content: str) -> List[KnowledgeItem]:
        """Extract knowledge from code analysis"""
        items = []
        timestamp = datetime.now()
        
        # Extract patterns
        for pattern_name, pattern in self.patterns.items():
            matches = pattern.findall(content)
            if matches and pattern_name == 'solution_pattern':
                # Look for solution patterns
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if pattern.search(line):
                        # Extract context
                        start = max(0, i - 3)
                        end = min(len(lines), i + 4)
                        context_lines = lines[start:end]
                        
                        item = KnowledgeItem(
                            id=f"solution_{file_path}_{i}_{timestamp.timestamp()}",
                            type=KnowledgeType.SOLUTION,
                            title=f"Solution pattern in {Path(file_path).name}",
                            content='\n'.join(context_lines),
                            context=file_path,
                            tags=['code_pattern', 'solution'],
                            source=KnowledgeSource.CODE_ANALYSIS,
                            confidence=0.7,
                            created_at=timestamp,
                            updated_at=timestamp,
                            related_files=[file_path]
                        )
                        items.append(item)
        
        # Extract function documentation as best practices
        if file_path.endswith('.py'):
            import ast
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and ast.get_docstring(node):
                        docstring = ast.get_docstring(node)
                        if len(docstring) > 50:  # Substantial documentation
                            item = KnowledgeItem(
                                id=f"practice_{file_path}_{node.name}_{timestamp.timestamp()}",
                                type=KnowledgeType.BEST_PRACTICE,
                                title=f"Implementation of {node.name}",
                                content=docstring,
                                context=f"Function {node.name} in {file_path}",
                                tags=['implementation', 'documented'],
                                source=KnowledgeSource.DOCUMENTATION,
                                confidence=0.9,
                                created_at=timestamp,
                                updated_at=timestamp,
                                related_files=[file_path],
                                examples=[{
                                    'code': ast.unparse(node) if hasattr(ast, 'unparse') else f"def {node.name}(...)",
                                    'description': f"Implementation of {node.name}"
                                }]
                            )
                            items.append(item)
            except:
                pass
        
        return items
    
    def learn_from_error_resolution(self, error_info: Dict[str, Any], solution: str):
        """Learn from how an error was resolved"""
        timestamp = datetime.now()
        
        item = KnowledgeItem(
            id=f"error_resolution_{timestamp.timestamp()}",
            type=KnowledgeType.TROUBLESHOOTING,
            title=f"Resolution for {error_info.get('error_type', 'Error')}",
            content=f"Error: {error_info.get('error_message', '')}\n\nSolution: {solution}",
            context=error_info.get('context', ''),
            tags=['error_resolution', error_info.get('error_type', 'general')],
            source=KnowledgeSource.ERROR_RESOLUTION,
            confidence=0.85,
            created_at=timestamp,
            updated_at=timestamp,
            related_files=error_info.get('files', []),
            examples=[{
                'error': error_info.get('error_message', ''),
                'solution': solution,
                'code_before': error_info.get('code_before', ''),
                'code_after': error_info.get('code_after', '')
            }],
            metadata={
                'error_details': error_info,
                'resolution_time': error_info.get('resolution_time', 'unknown')
            }
        )
        
        self.add_knowledge(item)
    
    def get_related_knowledge(self, item_id: str, max_depth: int = 2) -> List[KnowledgeItem]:
        """Get knowledge items related to a given item"""
        visited = set()
        related_items = []
        
        def traverse(current_id: str, depth: int):
            if depth > max_depth or current_id in visited:
                return
            
            visited.add(current_id)
            
            # Get directly related items
            for related_id, relationship in self.knowledge_graph.get(current_id, []):
                if related_id not in visited:
                    item = self.get_knowledge_by_id(related_id)
                    if item:
                        related_items.append(item)
                        traverse(related_id, depth + 1)
        
        traverse(item_id, 0)
        return related_items
    
    def get_knowledge_by_id(self, item_id: str) -> Optional[KnowledgeItem]:
        """Get a specific knowledge item by ID"""
        conn = sqlite3.connect(self.knowledge_db)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM knowledge_items WHERE id = ?', (item_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_knowledge_item(row)
        return None
    
    def update_usage(self, item_id: str, context: str = "", feedback: str = ""):
        """Update usage statistics for a knowledge item"""
        conn = sqlite3.connect(self.knowledge_db)
        cursor = conn.cursor()
        
        # Update usage count
        cursor.execute('''
            UPDATE knowledge_items 
            SET usage_count = usage_count + 1,
                updated_at = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), item_id))
        
        # Record usage
        cursor.execute('''
            INSERT INTO knowledge_usage (item_id, used_at, context, feedback)
            VALUES (?, ?, ?, ?)
        ''', (item_id, datetime.now().isoformat(), context, feedback))
        
        conn.commit()
        conn.close()
    
    def export_knowledge_graph(self) -> Dict[str, Any]:
        """Export knowledge graph for visualization"""
        nodes = []
        edges = []
        
        conn = sqlite3.connect(self.knowledge_db)
        cursor = conn.cursor()
        
        # Get all knowledge items as nodes
        cursor.execute('SELECT id, type, title, confidence, usage_count FROM knowledge_items')
        for row in cursor.fetchall():
            nodes.append({
                'id': row[0],
                'type': row[1],
                'label': row[2],
                'confidence': row[3],
                'size': min(10 + row[4] * 2, 50)  # Size based on usage
            })
        
        # Get all relationships as edges
        cursor.execute('SELECT item1_id, item2_id, relationship_type, strength FROM knowledge_relationships')
        for row in cursor.fetchall():
            edges.append({
                'source': row[0],
                'target': row[1],
                'type': row[2],
                'weight': row[3]
            })
        
        conn.close()
        
        return {
            'nodes': nodes,
            'edges': edges,
            'stats': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'knowledge_types': dict(defaultdict(int, {n['type']: 1 for n in nodes}))
            }
        }
    
    def generate_insights_report(self) -> Dict[str, Any]:
        """Generate insights report from knowledge base"""
        conn = sqlite3.connect(self.knowledge_db)
        cursor = conn.cursor()
        
        # Get statistics
        cursor.execute('SELECT COUNT(*) FROM knowledge_items')
        total_items = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT type, COUNT(*) as count 
            FROM knowledge_items 
            GROUP BY type 
            ORDER BY count DESC
        ''')
        type_distribution = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute('''
            SELECT title, usage_count, confidence 
            FROM knowledge_items 
            ORDER BY usage_count DESC 
            LIMIT 10
        ''')
        most_used = [{'title': row[0], 'usage': row[1], 'confidence': row[2]} 
                     for row in cursor.fetchall()]
        
        cursor.execute('''
            SELECT source, COUNT(*) as count 
            FROM knowledge_items 
            GROUP BY source
        ''')
        source_distribution = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Get recent additions
        cursor.execute('''
            SELECT title, type, created_at 
            FROM knowledge_items 
            ORDER BY created_at DESC 
            LIMIT 5
        ''')
        recent_additions = [{'title': row[0], 'type': row[1], 'created': row[2]} 
                           for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'total_knowledge_items': total_items,
            'type_distribution': type_distribution,
            'most_used_knowledge': most_used,
            'source_distribution': source_distribution,
            'recent_additions': recent_additions,
            'knowledge_graph_density': len(self.knowledge_graph) / max(total_items, 1)
        }


def demo_knowledge_management():
    """Demonstrate knowledge management capabilities"""
    km = DynamicKnowledgeManager()
    
    # Add some sample knowledge
    print("Adding sample knowledge...")
    
    # Add a solution
    solution = KnowledgeItem(
        id="",
        type=KnowledgeType.SOLUTION,
        title="Handling API Rate Limits",
        content="""
        When dealing with API rate limits, implement exponential backoff:
        1. Start with a base delay (e.g., 1 second)
        2. Double the delay after each retry
        3. Add jitter to prevent thundering herd
        4. Set a maximum number of retries
        """,
        context="API client implementation",
        tags=["api", "rate_limiting", "retry", "resilience"],
        source=KnowledgeSource.BEST_PRACTICE,
        confidence=0.95,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        examples=[{
            'code': 'delay = base_delay * (2 ** attempt) + random.uniform(0, 1)',
            'description': 'Exponential backoff with jitter'
        }]
    )
    km.add_knowledge(solution)
    
    # Add a pattern
    pattern = KnowledgeItem(
        id="",
        type=KnowledgeType.PATTERN,
        title="Repository Pattern for Data Access",
        content="""
        The Repository pattern provides an abstraction layer between your domain model and data mapping layers.
        Benefits:
        - Centralizes query logic
        - Makes testing easier with mock repositories
        - Allows switching data sources easily
        """,
        context="Architecture patterns",
        tags=["pattern", "repository", "data_access", "architecture"],
        source=KnowledgeSource.DOCUMENTATION,
        confidence=0.9,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        related_files=["src/repositories/base.py"]
    )
    km.add_knowledge(pattern)
    
    # Search for knowledge
    print("\nSearching for rate limiting knowledge...")
    query = KnowledgeQuery(
        query="rate limiting api",
        types=[KnowledgeType.SOLUTION, KnowledgeType.BEST_PRACTICE],
        min_confidence=0.7
    )
    results = km.search_knowledge(query)
    
    for item in results:
        print(f"\nFound: {item.title}")
        print(f"Type: {item.type.value}")
        print(f"Confidence: {item.confidence}")
        print(f"Tags: {', '.join(item.tags)}")
    
    # Generate insights report
    print("\n\nKnowledge Base Insights:")
    print("=" * 50)
    report = km.generate_insights_report()
    print(f"Total items: {report['total_knowledge_items']}")
    print(f"Type distribution: {report['type_distribution']}")
    print(f"Knowledge graph density: {report['knowledge_graph_density']:.2f}")


if __name__ == "__main__":
    demo_knowledge_management()