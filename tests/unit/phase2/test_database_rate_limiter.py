"""Phase 2: Database Rate Limiter Tests

Tests for database-backed rate limiting with usage tracking,
quota management, and cost calculation features.
"""

import pytest
import asyncio
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import sqlite3

from flashcard_pipeline.rate_limiter import DatabaseRateLimiter, UsageAlert
from flashcard_pipeline.exceptions import RateLimitError


@pytest.fixture
def db_path():
    """Create temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def db_limiter(db_path):
    """Create database rate limiter"""
    return DatabaseRateLimiter(
        db_path=db_path,
        requests_per_minute=60,
        requests_per_hour=3000,
        burst_size=10,
        daily_token_quota=100000,
        monthly_budget_usd=50.0
    )


class TestDatabaseRateLimiter:
    """Test database rate limiter functionality"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, db_limiter, db_path):
        """Test database initialization"""
        # Check that tables were created
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check all required tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN 
            ('api_usage_tracking', 'api_quota_config', 'rate_limiter_state', 'usage_alerts')
        """)
        tables = [row[0] for row in cursor.fetchall()]
        assert len(tables) == 4
        assert 'api_usage_tracking' in tables
        assert 'api_quota_config' in tables
        assert 'rate_limiter_state' in tables
        assert 'usage_alerts' in tables
        
        conn.close()
    
    @pytest.mark.asyncio
    async def test_usage_tracking(self, db_limiter):
        """Test API usage tracking"""
        # Track a successful request
        cost = await db_limiter.track_usage(
            request_id="test-001",
            input_tokens=1000,
            output_tokens=500,
            endpoint="/v1/messages",
            status="success"
        )
        
        # Check cost calculation
        # Input: 1000 tokens * $3.00/1M = $0.003
        # Output: 500 tokens * $15.00/1M = $0.0075
        # Total: $0.0105
        assert abs(cost - 0.0105) < 0.0001
        
        # Verify it was recorded in database
        stats = db_limiter.get_usage_stats("today")
        assert stats['total_requests'] == 1
        assert stats['successful_requests'] == 1
        assert stats['total_tokens'] == 1500
        assert abs(stats['total_cost_usd'] - 0.0105) < 0.0001
    
    @pytest.mark.asyncio
    async def test_duplicate_request_tracking(self, db_limiter):
        """Test handling of duplicate request IDs"""
        # Track initial request
        await db_limiter.track_usage(
            request_id="test-002",
            input_tokens=1000,
            output_tokens=500,
            status="success"
        )
        
        # Track with same request ID (retry)
        await db_limiter.track_usage(
            request_id="test-002",
            input_tokens=1000,
            output_tokens=500,
            status="failed",
            error_message="Timeout"
        )
        
        # Should only count as one request with updated retry count
        stats = db_limiter.get_usage_stats("today")
        assert stats['total_requests'] == 1
    
    @pytest.mark.asyncio
    async def test_daily_token_quota(self, db_limiter):
        """Test daily token quota enforcement"""
        # Use up most of the quota
        await db_limiter.track_usage(
            request_id="test-003",
            input_tokens=50000,
            output_tokens=45000,
            status="success"
        )
        
        # This should trigger quota exceeded
        with pytest.raises(RateLimitError) as exc_info:
            await db_limiter.track_usage(
                request_id="test-004",
                input_tokens=10000,
                output_tokens=5000,
                status="success"
            )
        
        assert "Daily token quota exceeded" in str(exc_info.value)
        assert exc_info.value.retry_after == 86400  # 24 hours
    
    @pytest.mark.asyncio
    async def test_monthly_budget_enforcement(self, db_limiter):
        """Test monthly budget enforcement"""
        # First, increase the daily quota to avoid hitting it
        db_limiter.daily_token_quota = 10_000_000  # 10M tokens
        
        # Use up most of the budget with high token usage
        # Input: 100k * $3/1M = $0.30
        # Output: 3.3M * $15/1M = $49.50
        # Total: $49.80 (just under $50 budget)
        await db_limiter.track_usage(
            request_id="test-005",
            input_tokens=100000,  # $0.30
            output_tokens=3300000,  # $49.50
            status="success"
        )
        
        # This should trigger budget exceeded
        # Additional cost: 10k*$3/1M + 10k*$15/1M = $0.03 + $0.15 = $0.18
        # Total would be: $49.80 + $0.18 = $49.98 (still under)
        # Need a bit more to exceed
        with pytest.raises(RateLimitError) as exc_info:
            await db_limiter.track_usage(
                request_id="test-006",
                input_tokens=10000,   # $0.03
                output_tokens=15000,  # $0.225 - total would be $50.055
                status="success"
            )
        
        assert "Monthly budget exceeded" in str(exc_info.value)
        assert exc_info.value.retry_after == 2592000  # 30 days
    
    @pytest.mark.asyncio
    async def test_usage_alerts(self, db_limiter):
        """Test usage alert triggering"""
        # Mock logger to capture alerts
        with patch('flashcard_pipeline.rate_limiter.logger') as mock_logger:
            # Use 55% of daily quota (should trigger 50% alert)
            await db_limiter.track_usage(
                request_id="test-007",
                input_tokens=30000,
                output_tokens=25000,
                status="success"
            )
            
            # Check that info alert was logged
            mock_logger.info.assert_called()
            alert_message = mock_logger.info.call_args[0][0]
            assert "50% of quota used" in alert_message
            assert "55.0%" in alert_message
    
    @pytest.mark.asyncio
    async def test_custom_alert(self, db_limiter):
        """Test custom alert configuration"""
        # Add custom alert at 25%
        callback_called = False
        
        async def alert_callback(percent, usage, quota_type):
            nonlocal callback_called
            callback_called = True
        
        db_limiter.add_alert(25.0, "25% usage reached", "info", alert_callback)
        
        # Use 30% of quota
        await db_limiter.track_usage(
            request_id="test-008",
            input_tokens=15000,
            output_tokens=15000,
            status="success"
        )
        
        # Verify callback was called
        assert callback_called
    
    @pytest.mark.asyncio
    async def test_alert_spam_prevention(self, db_limiter):
        """Test that alerts don't spam (sent once per day)"""
        with patch('flashcard_pipeline.rate_limiter.logger') as mock_logger:
            # First request triggers 50% alert
            await db_limiter.track_usage(
                request_id="test-009",
                input_tokens=30000,
                output_tokens=25000,
                status="success"
            )
            
            info_call_count = mock_logger.info.call_count
            
            # Second request at same level shouldn't trigger another alert
            await db_limiter.track_usage(
                request_id="test-010",
                input_tokens=1000,
                output_tokens=1000,
                status="success"
            )
            
            # Should not have logged another alert
            assert mock_logger.info.call_count == info_call_count
    
    def test_usage_stats_periods(self, db_limiter):
        """Test usage statistics for different periods"""
        # Add some test data across different dates
        with db_limiter._get_connection() as conn:
            cursor = conn.cursor()
            
            # Today's usage
            cursor.execute("""
                INSERT INTO api_usage_tracking 
                (request_id, model_name, input_tokens, output_tokens, total_tokens, 
                 estimated_cost_usd, created_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, ("today-1", "claude-3-5-sonnet", 1000, 500, 1500, 0.0105))
            
            # Yesterday's usage
            cursor.execute("""
                INSERT INTO api_usage_tracking 
                (request_id, model_name, input_tokens, output_tokens, total_tokens, 
                 estimated_cost_usd, created_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now', '-1 day'))
            """, ("yesterday-1", "claude-3-5-sonnet", 2000, 1000, 3000, 0.021))
            
            # Last month's usage
            cursor.execute("""
                INSERT INTO api_usage_tracking 
                (request_id, model_name, input_tokens, output_tokens, total_tokens, 
                 estimated_cost_usd, created_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now', '-35 days'))
            """, ("lastmonth-1", "claude-3-5-sonnet", 3000, 1500, 4500, 0.0315))
            
            conn.commit()
        
        # Test different period queries
        today_stats = db_limiter.get_usage_stats("today")
        assert today_stats['total_requests'] == 1
        assert today_stats['total_tokens'] == 1500
        
        week_stats = db_limiter.get_usage_stats("week")
        assert week_stats['total_requests'] == 2  # today + yesterday
        assert week_stats['total_tokens'] == 4500
        
        all_stats = db_limiter.get_usage_stats("all")
        assert all_stats['total_requests'] == 3
        assert all_stats['total_tokens'] == 9000
    
    def test_usage_by_model(self, db_limiter):
        """Test usage breakdown by model"""
        # Add usage for different models
        with db_limiter._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO api_usage_tracking 
                (request_id, model_name, input_tokens, output_tokens, total_tokens, 
                 estimated_cost_usd, status)
                VALUES 
                (?, ?, ?, ?, ?, ?, ?),
                (?, ?, ?, ?, ?, ?, ?),
                (?, ?, ?, ?, ?, ?, ?)
            """, (
                "model1-1", "claude-3-5-sonnet", 1000, 500, 1500, 0.0105, "success",
                "model1-2", "claude-3-5-sonnet", 2000, 1000, 3000, 0.021, "success",
                "model2-1", "gpt-4", 1500, 750, 2250, 0.015, "success"
            ))
            conn.commit()
        
        usage_by_model = db_limiter.get_usage_by_model()
        
        assert "claude-3-5-sonnet" in usage_by_model
        assert usage_by_model["claude-3-5-sonnet"]["request_count"] == 2
        assert usage_by_model["claude-3-5-sonnet"]["total_tokens"] == 4500
        
        assert "gpt-4" in usage_by_model
        assert usage_by_model["gpt-4"]["request_count"] == 1
    
    def test_quota_updates(self, db_limiter):
        """Test updating quota configurations"""
        # Update daily token quota
        db_limiter.set_quota("daily_tokens", 200000)
        assert db_limiter.daily_token_quota == 200000
        
        # Update monthly budget
        db_limiter.set_quota("monthly_budget", 100.0)
        assert db_limiter.monthly_budget_usd == 100.0
        
        # Verify in database
        with db_limiter._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT quota_value FROM api_quota_config 
                WHERE quota_type = 'daily_tokens' 
                AND effective_date = DATE('now')
            """)
            assert cursor.fetchone()['quota_value'] == 200000
    
    @pytest.mark.asyncio
    async def test_state_persistence(self, db_path):
        """Test rate limiter state persistence across restarts"""
        # Create limiter and consume some tokens
        limiter1 = DatabaseRateLimiter(
            db_path=db_path,
            requests_per_minute=60,
            burst_size=10
        )
        
        # Consume 5 tokens
        for _ in range(5):
            await limiter1.acquire()
        
        # Save state
        limiter1._save_state()
        
        # Create new limiter instance
        limiter2 = DatabaseRateLimiter(
            db_path=db_path,
            requests_per_minute=60,
            burst_size=10
        )
        
        # Should have restored state (approximately)
        # Some tokens may have regenerated
        assert limiter2.tokens <= 5  # Should have 5 or fewer tokens
    
    @pytest.mark.asyncio
    async def test_acquire_with_quota_check(self, db_limiter):
        """Test that acquire checks quotas before allowing requests"""
        # Manually insert usage data to bypass track_usage quota check
        with db_limiter._get_connection() as conn:
            cursor = conn.cursor()
            # Insert usage that puts us at exactly the quota limit
            cursor.execute("""
                INSERT INTO api_usage_tracking 
                (request_id, model_name, input_tokens, output_tokens, total_tokens, 
                 estimated_cost_usd, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                "test-quota-1", "claude-3-5-sonnet", 60000, 40000, 100000, 
                0.18 + 0.6,  # 60k*3/1M + 40k*15/1M
                "success"
            ))
            conn.commit()
        
        # At this point we're at 100,000/100,000 tokens in the database
        # The next acquire() should fail because we're at the limit
        with pytest.raises(RateLimitError) as exc_info:
            await db_limiter.acquire()
        
        assert "Daily token quota exceeded" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_cost_calculation_accuracy(self, db_limiter):
        """Test accurate cost calculation for various token amounts"""
        # Pricing: Input=$3/1M tokens, Output=$15/1M tokens
        test_cases = [
            # input_tokens, output_tokens, expected_cost
            (100, 50, 0.0003 + 0.00075),         # 100*3/1M + 50*15/1M = 0.00105
            (10000, 5000, 0.03 + 0.075),         # 10k*3/1M + 5k*15/1M = 0.105
            (100000, 50000, 0.3 + 0.75),         # 100k*3/1M + 50k*15/1M = 1.05
            (1000000, 500000, 3.0 + 7.5),        # 1M*3/1M + 500k*15/1M = 10.5
        ]
        
        # Clear any previous usage to avoid quota issues
        db_limiter.daily_token_quota = 10_000_000  # 10M tokens
        
        for i, (input_tokens, output_tokens, expected_cost) in enumerate(test_cases):
            cost = await db_limiter.track_usage(
                request_id=f"cost-test-{i}",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                status="success"
            )
            assert abs(cost - expected_cost) < 0.0001, f"Test case {i}: expected {expected_cost}, got {cost}"