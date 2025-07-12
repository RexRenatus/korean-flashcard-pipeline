"""Unit tests for query optimizer"""

import pytest
import time
from unittest.mock import Mock, patch

from flashcard_pipeline.database.query_optimizer import (
    QueryOptimizer,
    OptimizationLevel,
    IndexSuggestion,
    QueryPattern,
    PreparedStatement,
)


class TestQueryOptimizer:
    """Test query optimization functionality"""
    
    @pytest.fixture
    def optimizer(self):
        """Create a test query optimizer"""
        return QueryOptimizer(
            enable_n1_detection=True,
            enable_auto_indexing=True,
            slow_query_threshold=0.1,
            n1_threshold=3,
            prepared_cache_size=10
        )
    
    def test_query_normalization(self, optimizer):
        """Test query normalization"""
        queries = [
            ("SELECT * FROM users WHERE id = ?", "SELECT * FROM USERS WHERE ID = ?"),
            ("SELECT  *  FROM  users", "SELECT * FROM USERS"),
            ("SELECT * FROM users WHERE id = 123", "SELECT * FROM USERS WHERE ID = N"),
            ("SELECT * FROM users WHERE name = 'John'", "SELECT * FROM USERS WHERE NAME = 'STR'"),
            ("SELECT * FROM users WHERE id = :user_id", "SELECT * FROM USERS WHERE ID = :PARAM"),
        ]
        
        for query, expected in queries:
            normalized = optimizer._normalize_query(query)
            assert normalized == expected
    
    def test_n1_detection(self, optimizer):
        """Test N+1 query pattern detection"""
        # Simulate N+1 pattern
        base_query = "SELECT * FROM users WHERE id = ?"
        
        # First few queries don't trigger detection
        for i in range(2):
            result = optimizer.analyze_query(
                f"SELECT * FROM users WHERE id = {i}",
                execution_time=0.01
            )
            assert not any(p["type"] == "n_plus_1" for p in result["patterns"])
        
        # Third similar query should trigger N+1 detection
        result = optimizer.analyze_query(
            "SELECT * FROM users WHERE id = 3",
            execution_time=0.01
        )
        
        n1_patterns = [p for p in result["patterns"] if p["type"] == "n_plus_1"]
        assert len(n1_patterns) > 0
        assert n1_patterns[0]["level"] == OptimizationLevel.CRITICAL
        assert "N+1 pattern" in n1_patterns[0]["message"]
    
    def test_slow_query_detection(self, optimizer):
        """Test slow query detection"""
        # Fast query
        result = optimizer.analyze_query(
            "SELECT * FROM users",
            execution_time=0.05
        )
        slow_patterns = [p for p in result["patterns"] if p["type"] == "slow_query"]
        assert len(slow_patterns) == 0
        
        # Slow query
        result = optimizer.analyze_query(
            "SELECT * FROM users",
            execution_time=0.5
        )
        slow_patterns = [p for p in result["patterns"] if p["type"] == "slow_query"]
        assert len(slow_patterns) > 0
        assert slow_patterns[0]["level"] == OptimizationLevel.HIGH
    
    def test_index_suggestions(self, optimizer):
        """Test index suggestion generation"""
        query = "SELECT * FROM users WHERE email = ? ORDER BY created_at"
        query_plan = [
            "SCAN TABLE users",
            "TEMP B-TREE FOR ORDER BY"
        ]
        
        result = optimizer.analyze_query(query, 0.2, query_plan)
        
        # Should suggest indexes for WHERE and ORDER BY
        index_patterns = [p for p in result["patterns"] if "index" in p["type"]]
        assert len(index_patterns) >= 1
        
        # Check for specific suggestions
        messages = [p["message"] for p in index_patterns]
        assert any("Full table scan" in msg for msg in messages)
    
    def test_table_extraction(self, optimizer):
        """Test table name extraction from queries"""
        test_cases = [
            ("SELECT * FROM users", ["users"]),
            ("SELECT * FROM users u JOIN posts p ON u.id = p.user_id", ["users", "posts"]),
            ("SELECT * FROM users WHERE id IN (SELECT user_id FROM posts)", ["users", "posts"]),
        ]
        
        for query, expected_tables in test_cases:
            tables = optimizer._extract_tables(query)
            assert set(tables) == set(expected_tables)
    
    def test_where_column_extraction(self, optimizer):
        """Test WHERE clause column extraction"""
        query = "SELECT * FROM users WHERE email = ? AND status = 1"
        columns = optimizer._extract_where_columns(query)
        
        assert "users" in columns
        assert "email" in columns["users"]
        assert "status" in columns["users"]
    
    def test_join_column_extraction(self, optimizer):
        """Test JOIN column extraction"""
        query = """
            SELECT * FROM users u
            JOIN posts p ON u.id = p.user_id
            JOIN comments c ON p.id = c.post_id
        """
        columns = optimizer._extract_join_columns(query)
        
        assert len(columns) > 0
        assert any("id" in cols for cols in columns.values())
    
    def test_batch_query_suggestion(self, optimizer):
        """Test batch query suggestions"""
        queries = [
            "SELECT * FROM users WHERE id = 1",
            "SELECT * FROM users WHERE id = 2",
            "SELECT * FROM users WHERE id = 3",
        ]
        
        batch_query = optimizer.suggest_batch_query(queries)
        assert batch_query is not None
        assert "IN" in batch_query
        assert batch_query.count("?") == len(queries)
    
    def test_prepared_statement_caching(self, optimizer):
        """Test prepared statement management"""
        query = "SELECT * FROM users WHERE id = ?"
        
        # First access creates new statement
        stmt1 = optimizer.get_prepared_statement(query)
        assert stmt1 is not None
        assert stmt1.param_count == 1
        assert stmt1.use_count == 0
        
        # Second access returns cached statement
        stmt2 = optimizer.get_prepared_statement(query)
        assert stmt2.query_hash == stmt1.query_hash
        assert stmt2.use_count == 1
    
    def test_prepared_statement_eviction(self, optimizer):
        """Test LRU eviction of prepared statements"""
        optimizer.prepared_cache_size = 3
        
        # Fill cache
        for i in range(4):
            query = f"SELECT * FROM table{i} WHERE id = ?"
            optimizer.get_prepared_statement(query)
            time.sleep(0.01)  # Ensure different timestamps
        
        # Cache should have evicted the oldest
        assert len(optimizer._prepared_statements) == 3
    
    def test_optimization_report(self, optimizer):
        """Test comprehensive optimization report generation"""
        # Simulate various query patterns
        for i in range(5):
            optimizer.analyze_query(
                f"SELECT * FROM users WHERE id = {i}",
                execution_time=0.01
            )
        
        # Slow query
        optimizer.analyze_query(
            "SELECT * FROM posts JOIN users ON posts.user_id = users.id",
            execution_time=0.5,
            query_plan=["SCAN TABLE posts", "SCAN TABLE users"]
        )
        
        report = optimizer.get_optimization_report()
        
        assert report["total_queries_analyzed"] >= 6
        assert report["unique_patterns"] >= 2
        assert report["optimization_potential"] > 0.0
    
    def test_similar_query_detection(self, optimizer):
        """Test detection of similar queries"""
        q1 = "SELECT * FROM USERS WHERE ID = N"
        q2 = "SELECT * FROM USERS WHERE ID = N"
        q3 = "SELECT * FROM POSTS WHERE ID = N"
        
        assert optimizer._is_similar_query(q1, q2) is True
        assert optimizer._is_similar_query(q1, q3) is False
    
    def test_optimization_suggestions(self, optimizer):
        """Test optimization suggestion generation"""
        patterns = [
            {
                "type": "n_plus_1",
                "level": OptimizationLevel.CRITICAL,
                "message": "N+1 detected"
            },
            {
                "type": "missing_index",
                "level": OptimizationLevel.HIGH,
                "message": "Missing index",
                "details": IndexSuggestion(
                    table="users",
                    columns=["email"],
                    reason="Full scan",
                    level=OptimizationLevel.HIGH,
                    estimated_improvement=50.0
                )
            }
        ]
        
        query = "SELECT * FROM users WHERE email = ?"
        optimizations = optimizer._generate_optimizations(query, patterns)
        
        assert len(optimizations) > 0
        assert any("JOIN" in opt for opt in optimizations)
        assert any("CREATE INDEX" in opt for opt in optimizations)
    
    def test_query_pattern_tracking(self, optimizer):
        """Test query pattern statistics tracking"""
        # Execute same query multiple times
        query = "SELECT * FROM users WHERE status = ?"
        
        for i in range(3):
            optimizer.analyze_query(query, execution_time=0.1 * (i + 1))
        
        query_hash = optimizer._hash_query(optimizer._normalize_query(query))
        pattern = optimizer._query_patterns.get(query_hash)
        
        assert pattern is not None
        assert pattern.occurrences == 3
        assert pattern.total_time == 0.6  # 0.1 + 0.2 + 0.3
        assert pattern.avg_time == 0.2
    
    def test_reset_statistics(self, optimizer):
        """Test statistics reset"""
        # Add some data
        optimizer.analyze_query("SELECT * FROM users", 0.1)
        optimizer.get_prepared_statement("SELECT * FROM posts WHERE id = ?")
        
        assert len(optimizer._query_log) > 0
        assert len(optimizer._query_patterns) > 0
        
        # Reset
        optimizer.reset_statistics()
        
        assert len(optimizer._query_log) == 0
        assert len(optimizer._query_patterns) == 0
        assert len(optimizer._recent_queries) == 0


class TestIndexSuggestion:
    """Test index suggestion functionality"""
    
    def test_index_name_generation(self):
        """Test index name generation"""
        suggestion = IndexSuggestion(
            table="users",
            columns=["email", "status"],
            reason="Test",
            level=OptimizationLevel.HIGH,
            estimated_improvement=50.0
        )
        
        assert suggestion.index_name == "idx_users_email_status"
    
    def test_create_statement_generation(self):
        """Test CREATE INDEX statement generation"""
        suggestion = IndexSuggestion(
            table="posts",
            columns=["user_id", "created_at"],
            reason="Test",
            level=OptimizationLevel.MEDIUM,
            estimated_improvement=30.0
        )
        
        expected = "CREATE INDEX idx_posts_user_id_created_at ON posts(user_id, created_at)"
        assert suggestion.create_statement == expected


class TestQueryPattern:
    """Test query pattern tracking"""
    
    def test_pattern_initialization(self):
        """Test pattern initialization"""
        pattern = QueryPattern(
            pattern_type="n_plus_1",
            query_hash="abc123"
        )
        
        assert pattern.occurrences == 1
        assert pattern.total_time == 0.0
        assert pattern.avg_time == 0.0
        assert len(pattern.suggestions) == 0