"""
Query optimization and indexing utilities for the flashcard pipeline.

This module provides:
- Query plan analysis and optimization
- Automatic index suggestions
- N+1 query detection and prevention
- Batch query optimization
- Prepared statement management
"""

import re
import hashlib
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple, Callable
from collections import defaultdict, Counter
import logging
import time
from enum import Enum

logger = logging.getLogger(__name__)


class OptimizationLevel(Enum):
    """Query optimization severity levels"""
    CRITICAL = "critical"  # Major performance issue
    HIGH = "high"         # Significant improvement possible
    MEDIUM = "medium"     # Moderate improvement possible
    LOW = "low"          # Minor optimization available
    INFO = "info"        # Informational only


@dataclass
class IndexSuggestion:
    """Suggested index for query optimization"""
    table: str
    columns: List[str]
    reason: str
    level: OptimizationLevel
    estimated_improvement: float  # Percentage improvement
    
    @property
    def index_name(self) -> str:
        """Generate index name"""
        cols = "_".join(self.columns)
        return f"idx_{self.table}_{cols}"
    
    @property
    def create_statement(self) -> str:
        """Generate CREATE INDEX statement"""
        cols = ", ".join(self.columns)
        return f"CREATE INDEX {self.index_name} ON {self.table}({cols})"


@dataclass
class QueryPattern:
    """Detected query pattern for optimization"""
    pattern_type: str  # e.g., "n+1", "missing_index", "full_scan"
    query_hash: str
    occurrences: int = 1
    total_time: float = 0.0
    avg_time: float = 0.0
    suggestions: List[str] = field(default_factory=list)


@dataclass
class PreparedStatement:
    """Prepared statement for reuse"""
    query: str
    query_hash: str
    param_count: int
    last_used: float = field(default_factory=time.time)
    use_count: int = 0


class QueryOptimizer:
    """Advanced query optimization engine"""
    
    def __init__(
        self,
        enable_n1_detection: bool = True,
        enable_auto_indexing: bool = True,
        slow_query_threshold: float = 0.1,
        n1_threshold: int = 5,
        prepared_cache_size: int = 100
    ):
        """
        Initialize query optimizer.
        
        Args:
            enable_n1_detection: Whether to detect N+1 queries
            enable_auto_indexing: Whether to suggest indexes automatically
            slow_query_threshold: Threshold for slow queries (seconds)
            n1_threshold: Number of similar queries to trigger N+1 detection
            prepared_cache_size: Maximum prepared statements to cache
        """
        self.enable_n1_detection = enable_n1_detection
        self.enable_auto_indexing = enable_auto_indexing
        self.slow_query_threshold = slow_query_threshold
        self.n1_threshold = n1_threshold
        self.prepared_cache_size = prepared_cache_size
        
        # Query tracking
        self._query_log: List[Dict[str, Any]] = []
        self._query_patterns: Dict[str, QueryPattern] = {}
        self._prepared_statements: Dict[str, PreparedStatement] = {}
        
        # N+1 detection
        self._recent_queries: List[Tuple[str, float]] = []
        self._n1_patterns: Set[str] = set()
        
        # Index tracking
        self._existing_indexes: Dict[str, Set[str]] = {}
        self._suggested_indexes: List[IndexSuggestion] = []
        
        logger.info("Initialized QueryOptimizer")
    
    def analyze_query(self, query: str, execution_time: float,
                     query_plan: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Analyze a query for optimization opportunities.
        
        Args:
            query: SQL query
            execution_time: Query execution time
            query_plan: Optional query execution plan
            
        Returns:
            Analysis results with suggestions
        """
        normalized = self._normalize_query(query)
        query_hash = self._hash_query(normalized)
        
        # Log query
        self._log_query(query, normalized, query_hash, execution_time)
        
        # Detect patterns
        patterns = []
        
        if self.enable_n1_detection:
            n1_result = self._detect_n1_pattern(normalized, query_hash)
            if n1_result:
                patterns.append(n1_result)
        
        if self.enable_auto_indexing and query_plan:
            index_suggestions = self._analyze_for_indexes(query, query_plan)
            patterns.extend(index_suggestions)
        
        # Check for other patterns
        if execution_time > self.slow_query_threshold:
            patterns.append({
                "type": "slow_query",
                "level": OptimizationLevel.HIGH,
                "message": f"Query took {execution_time:.2f}s (threshold: {self.slow_query_threshold}s)",
                "suggestion": "Consider adding indexes or optimizing query structure"
            })
        
        # Aggregate results
        return {
            "query": query,
            "query_hash": query_hash,
            "execution_time": execution_time,
            "patterns": patterns,
            "optimizations": self._generate_optimizations(query, patterns),
            "prepared_available": query_hash in self._prepared_statements
        }
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for pattern matching"""
        # Remove extra whitespace
        normalized = " ".join(query.split())
        
        # Replace parameter placeholders
        normalized = re.sub(r'\?', '?', normalized)
        normalized = re.sub(r':\w+', ':param', normalized)
        normalized = re.sub(r'%s', '?', normalized)
        
        # Remove numeric literals for pattern matching
        normalized = re.sub(r'\b\d+\b', 'N', normalized)
        
        # Remove string literals
        normalized = re.sub(r"'[^']*'", "'STR'", normalized)
        normalized = re.sub(r'"[^"]*"', '"STR"', normalized)
        
        return normalized.upper()
    
    def _hash_query(self, query: str) -> str:
        """Generate hash for query"""
        return hashlib.md5(query.encode()).hexdigest()
    
    def _log_query(self, query: str, normalized: str, 
                   query_hash: str, execution_time: float):
        """Log query for pattern analysis"""
        self._query_log.append({
            "query": query,
            "normalized": normalized,
            "hash": query_hash,
            "time": execution_time,
            "timestamp": time.time()
        })
        
        # Update patterns
        if query_hash not in self._query_patterns:
            self._query_patterns[query_hash] = QueryPattern(
                pattern_type="general",
                query_hash=query_hash
            )
        
        pattern = self._query_patterns[query_hash]
        pattern.occurrences += 1
        pattern.total_time += execution_time
        pattern.avg_time = pattern.total_time / pattern.occurrences
        
        # Track recent queries for N+1 detection
        self._recent_queries.append((normalized, time.time()))
        # Keep only recent queries (last 60 seconds)
        cutoff = time.time() - 60
        self._recent_queries = [
            (q, t) for q, t in self._recent_queries if t > cutoff
        ]
    
    def _detect_n1_pattern(self, normalized: str, query_hash: str) -> Optional[Dict[str, Any]]:
        """Detect N+1 query patterns"""
        # Count similar queries in recent history
        similar_count = sum(
            1 for q, _ in self._recent_queries
            if self._is_similar_query(normalized, q)
        )
        
        if similar_count >= self.n1_threshold:
            # Extract table and pattern
            table_match = re.search(r'FROM\s+(\w+)', normalized)
            table = table_match.group(1) if table_match else "unknown"
            
            return {
                "type": "n_plus_1",
                "level": OptimizationLevel.CRITICAL,
                "message": f"Detected N+1 pattern: {similar_count} similar queries to {table}",
                "suggestion": "Consider using JOIN or batch loading instead of individual queries",
                "occurrences": similar_count
            }
        
        return None
    
    def _is_similar_query(self, query1: str, query2: str) -> bool:
        """Check if two normalized queries are similar (potential N+1)"""
        # Remove WHERE clause variations
        pattern1 = re.sub(r'WHERE.*', 'WHERE', query1)
        pattern2 = re.sub(r'WHERE.*', 'WHERE', query2)
        
        return pattern1 == pattern2
    
    def _analyze_for_indexes(self, query: str, query_plan: List[Any]) -> List[Dict[str, Any]]:
        """Analyze query plan for index opportunities"""
        suggestions = []
        plan_text = " ".join(str(item) for item in query_plan)
        
        # Parse query for table and column information
        tables = self._extract_tables(query)
        where_columns = self._extract_where_columns(query)
        order_columns = self._extract_order_columns(query)
        join_columns = self._extract_join_columns(query)
        
        # Check for full table scans
        if "SCAN TABLE" in plan_text:
            for table in tables:
                if table in plan_text:
                    # Suggest index on WHERE columns
                    if where_columns.get(table):
                        suggestion = IndexSuggestion(
                            table=table,
                            columns=list(where_columns[table]),
                            reason="Full table scan detected",
                            level=OptimizationLevel.HIGH,
                            estimated_improvement=50.0
                        )
                        suggestions.append({
                            "type": "missing_index",
                            "level": suggestion.level,
                            "message": f"Full table scan on {table}",
                            "suggestion": suggestion.create_statement,
                            "details": suggestion
                        })
        
        # Check for sorting without index
        if "TEMP B-TREE" in plan_text and order_columns:
            for table, columns in order_columns.items():
                suggestion = IndexSuggestion(
                    table=table,
                    columns=list(columns),
                    reason="Sorting without index",
                    level=OptimizationLevel.MEDIUM,
                    estimated_improvement=30.0
                )
                suggestions.append({
                    "type": "missing_order_index",
                    "level": suggestion.level,
                    "message": f"Sorting {table} without index",
                    "suggestion": suggestion.create_statement,
                    "details": suggestion
                })
        
        # Check for join performance
        if join_columns and "NESTED LOOP" in plan_text:
            for table, columns in join_columns.items():
                suggestion = IndexSuggestion(
                    table=table,
                    columns=list(columns),
                    reason="Join without index",
                    level=OptimizationLevel.HIGH,
                    estimated_improvement=40.0
                )
                suggestions.append({
                    "type": "missing_join_index",
                    "level": suggestion.level,
                    "message": f"Join on {table} without index",
                    "suggestion": suggestion.create_statement,
                    "details": suggestion
                })
        
        return suggestions
    
    def _extract_tables(self, query: str) -> List[str]:
        """Extract table names from query"""
        tables = []
        
        # FROM clause
        from_match = re.findall(r'FROM\s+(\w+)', query, re.IGNORECASE)
        tables.extend(from_match)
        
        # JOIN clauses
        join_match = re.findall(r'JOIN\s+(\w+)', query, re.IGNORECASE)
        tables.extend(join_match)
        
        return list(set(tables))
    
    def _extract_where_columns(self, query: str) -> Dict[str, Set[str]]:
        """Extract columns used in WHERE clause"""
        columns = defaultdict(set)
        
        # Simple pattern for WHERE conditions
        where_match = re.search(r'WHERE\s+(.*?)(?:GROUP|ORDER|LIMIT|$)', 
                              query, re.IGNORECASE | re.DOTALL)
        
        if where_match:
            conditions = where_match.group(1)
            # Extract column references (simplified)
            col_matches = re.findall(r'(\w+)\.(\w+)\s*[=<>]', conditions)
            for table, column in col_matches:
                columns[table].add(column)
            
            # Also check for unqualified columns
            unqual_matches = re.findall(r'(\w+)\s*[=<>]', conditions)
            for col in unqual_matches:
                if col.upper() not in ['AND', 'OR', 'NOT', 'IN', 'EXISTS']:
                    # Assign to first table if unqualified
                    tables = self._extract_tables(query)
                    if tables:
                        columns[tables[0]].add(col)
        
        return dict(columns)
    
    def _extract_order_columns(self, query: str) -> Dict[str, Set[str]]:
        """Extract columns used in ORDER BY clause"""
        columns = defaultdict(set)
        
        order_match = re.search(r'ORDER\s+BY\s+(.*?)(?:LIMIT|$)', 
                              query, re.IGNORECASE | re.DOTALL)
        
        if order_match:
            order_clause = order_match.group(1)
            # Extract column references
            col_matches = re.findall(r'(\w+)\.(\w+)', order_clause)
            for table, column in col_matches:
                columns[table].add(column)
            
            # Unqualified columns
            unqual_matches = re.findall(r'(\w+)(?:\s+(?:ASC|DESC))?', order_clause)
            tables = self._extract_tables(query)
            if tables and unqual_matches:
                for col in unqual_matches:
                    if col.upper() not in ['ASC', 'DESC']:
                        columns[tables[0]].add(col)
        
        return dict(columns)
    
    def _extract_join_columns(self, query: str) -> Dict[str, Set[str]]:
        """Extract columns used in JOIN conditions"""
        columns = defaultdict(set)
        
        # Find JOIN ON conditions
        join_matches = re.findall(
            r'JOIN\s+(\w+)\s+ON\s+(.*?)(?:WHERE|GROUP|ORDER|JOIN|$)',
            query, re.IGNORECASE | re.DOTALL
        )
        
        for table, condition in join_matches:
            # Extract columns from join condition
            col_matches = re.findall(r'(\w+)\.(\w+)', condition)
            for t, c in col_matches:
                columns[t].add(c)
        
        return dict(columns)
    
    def _generate_optimizations(self, query: str, patterns: List[Dict[str, Any]]) -> List[str]:
        """Generate specific optimization recommendations"""
        optimizations = []
        
        # Group patterns by type
        pattern_types = defaultdict(list)
        for pattern in patterns:
            pattern_types[pattern["type"]].append(pattern)
        
        # N+1 optimization
        if "n_plus_1" in pattern_types:
            optimizations.append(
                "Replace individual queries with a single JOIN query or use batch loading"
            )
            
            # Provide example
            tables = self._extract_tables(query)
            if tables:
                optimizations.append(
                    f"Example: SELECT * FROM {tables[0]} WHERE id IN (?, ?, ?, ...)"
                )
        
        # Index optimizations
        if "missing_index" in pattern_types:
            for pattern in pattern_types["missing_index"]:
                if "details" in pattern:
                    details = pattern["details"]
                    optimizations.append(details.create_statement)
        
        # Slow query optimizations
        if "slow_query" in pattern_types:
            optimizations.extend([
                "Consider breaking complex queries into simpler ones",
                "Add LIMIT clause if not all results are needed",
                "Use EXPLAIN QUERY PLAN to understand execution"
            ])
        
        return optimizations
    
    def suggest_batch_query(self, queries: List[str]) -> Optional[str]:
        """
        Suggest a batch query to replace multiple similar queries.
        
        Args:
            queries: List of similar queries
            
        Returns:
            Suggested batch query or None
        """
        if len(queries) < 2:
            return None
        
        # Normalize all queries
        normalized = [self._normalize_query(q) for q in queries]
        
        # Check if they're similar
        base_pattern = re.sub(r'WHERE.*', 'WHERE', normalized[0])
        if not all(re.sub(r'WHERE.*', 'WHERE', n) == base_pattern for n in normalized[1:]):
            return None
        
        # Extract the varying part (usually in WHERE clause)
        # This is simplified - real implementation would be more sophisticated
        tables = self._extract_tables(queries[0])
        if not tables:
            return None
        
        # Generate batch query suggestion
        table = tables[0]
        
        # Try to extract the ID column being queried
        id_match = re.search(r'WHERE\s+(\w+)\s*=\s*\?', queries[0], re.IGNORECASE)
        if id_match:
            id_column = id_match.group(1)
            return f"SELECT * FROM {table} WHERE {id_column} IN ({', '.join(['?'] * len(queries))})"
        
        return None
    
    def get_prepared_statement(self, query: str) -> Optional[PreparedStatement]:
        """Get or create a prepared statement"""
        normalized = self._normalize_query(query)
        query_hash = self._hash_query(normalized)
        
        if query_hash in self._prepared_statements:
            stmt = self._prepared_statements[query_hash]
            stmt.last_used = time.time()
            stmt.use_count += 1
            return stmt
        
        # Create new prepared statement
        if len(self._prepared_statements) >= self.prepared_cache_size:
            # Evict least recently used
            lru_hash = min(
                self._prepared_statements.keys(),
                key=lambda h: self._prepared_statements[h].last_used
            )
            del self._prepared_statements[lru_hash]
        
        # Count parameters
        param_count = query.count('?')
        
        stmt = PreparedStatement(
            query=query,
            query_hash=query_hash,
            param_count=param_count
        )
        self._prepared_statements[query_hash] = stmt
        
        return stmt
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Generate comprehensive optimization report"""
        # Analyze all tracked patterns
        critical_patterns = []
        high_patterns = []
        medium_patterns = []
        
        for pattern in self._query_patterns.values():
            if pattern.avg_time > self.slow_query_threshold:
                level = OptimizationLevel.CRITICAL if pattern.avg_time > self.slow_query_threshold * 2 else OptimizationLevel.HIGH
                pattern_info = {
                    "query_hash": pattern.query_hash,
                    "occurrences": pattern.occurrences,
                    "avg_time": pattern.avg_time,
                    "total_time": pattern.total_time,
                    "level": level
                }
                
                if level == OptimizationLevel.CRITICAL:
                    critical_patterns.append(pattern_info)
                else:
                    high_patterns.append(pattern_info)
        
        # Sort by impact (total time)
        critical_patterns.sort(key=lambda x: x["total_time"], reverse=True)
        high_patterns.sort(key=lambda x: x["total_time"], reverse=True)
        
        return {
            "total_queries_analyzed": len(self._query_log),
            "unique_patterns": len(self._query_patterns),
            "n1_patterns_detected": len(self._n1_patterns),
            "prepared_statements_cached": len(self._prepared_statements),
            "critical_patterns": critical_patterns[:10],
            "high_impact_patterns": high_patterns[:10],
            "suggested_indexes": self._suggested_indexes[:20],
            "total_time_analyzed": sum(p.total_time for p in self._query_patterns.values()),
            "optimization_potential": self._calculate_optimization_potential()
        }
    
    def _calculate_optimization_potential(self) -> float:
        """Calculate potential performance improvement percentage"""
        if not self._query_patterns:
            return 0.0
        
        # Estimate based on patterns
        total_time = sum(p.total_time for p in self._query_patterns.values())
        potential_savings = 0.0
        
        # N+1 queries can be 90% faster with batching
        n1_time = sum(
            p.total_time for p in self._query_patterns.values()
            if p.pattern_type == "n_plus_1"
        )
        potential_savings += n1_time * 0.9
        
        # Slow queries can be 50% faster with indexes
        slow_time = sum(
            p.total_time for p in self._query_patterns.values()
            if p.avg_time > self.slow_query_threshold
        )
        potential_savings += slow_time * 0.5
        
        return (potential_savings / total_time * 100) if total_time > 0 else 0.0
    
    def reset_statistics(self):
        """Reset all tracking statistics"""
        self._query_log.clear()
        self._query_patterns.clear()
        self._recent_queries.clear()
        self._n1_patterns.clear()
        self._suggested_indexes.clear()
        logger.info("Query optimizer statistics reset")