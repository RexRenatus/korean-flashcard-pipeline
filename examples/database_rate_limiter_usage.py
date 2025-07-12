#!/usr/bin/env python3
"""
Example: Using DatabaseRateLimiter for API usage tracking and quota management

This example demonstrates:
1. Setting up database-backed rate limiting
2. Tracking API usage and costs
3. Configuring quotas and alerts
4. Monitoring usage statistics
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from flashcard_pipeline.rate_limiter import DatabaseRateLimiter, UsageAlert

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def custom_alert_handler(usage_percent: float, current_usage: float, quota_type: str):
    """Custom alert handler for quota warnings"""
    logger.warning(f"CUSTOM ALERT: {quota_type} at {usage_percent:.1f}% - Usage: {current_usage}")
    
    # You could also:
    # - Send email notifications
    # - Post to Slack/Discord
    # - Trigger automated scaling
    # - Pause non-critical operations


async def simulate_api_requests(limiter: DatabaseRateLimiter, num_requests: int = 10):
    """Simulate making API requests with tracking"""
    
    for i in range(num_requests):
        try:
            # Check rate limit
            await limiter.acquire()
            
            # Simulate API call
            request_id = f"example-{datetime.now().timestamp()}-{i}"
            
            # Simulate varying token usage
            input_tokens = 500 + (i * 100)
            output_tokens = 250 + (i * 50)
            
            # Track usage
            cost = await limiter.track_usage(
                request_id=request_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                endpoint="/v1/messages",
                status="success"
            )
            
            logger.info(f"Request {i+1}: {input_tokens} + {output_tokens} tokens, Cost: ${cost:.4f}")
            
            # Small delay between requests
            await asyncio.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Request failed: {e}")
            
            # Track failed request
            await limiter.track_usage(
                request_id=f"failed-{datetime.now().timestamp()}-{i}",
                input_tokens=0,
                output_tokens=0,
                endpoint="/v1/messages",
                status="failed",
                error_message=str(e)
            )


def display_usage_stats(limiter: DatabaseRateLimiter):
    """Display comprehensive usage statistics"""
    
    print("\n" + "="*60)
    print("API USAGE STATISTICS")
    print("="*60)
    
    # Today's stats
    today_stats = limiter.get_usage_stats("today")
    print("\nToday's Usage:")
    print(f"  Total Requests: {today_stats.get('total_requests', 0)}")
    print(f"  Successful: {today_stats.get('successful_requests', 0)}")
    print(f"  Failed: {today_stats.get('failed_requests', 0)}")
    print(f"  Total Tokens: {today_stats.get('total_tokens', 0):,}")
    print(f"  Total Cost: ${today_stats.get('total_cost_usd', 0):.4f}")
    
    if 'daily_tokens_quota' in today_stats:
        print(f"\n  Daily Token Quota: {today_stats['daily_tokens_quota']:,}")
        print(f"  Tokens Used: {today_stats['daily_tokens_used']:,} ({today_stats['daily_tokens_percent']:.1f}%)")
    
    # This week's stats
    week_stats = limiter.get_usage_stats("week")
    print("\nThis Week's Usage:")
    print(f"  Total Requests: {week_stats.get('total_requests', 0)}")
    print(f"  Total Tokens: {week_stats.get('total_tokens', 0):,}")
    print(f"  Total Cost: ${week_stats.get('total_cost_usd', 0):.4f}")
    
    # Monthly budget status
    month_stats = limiter.get_usage_stats("month")
    if 'monthly_budget_usd' in month_stats:
        print(f"\nMonthly Budget Status:")
        print(f"  Budget: ${month_stats['monthly_budget_usd']:.2f}")
        print(f"  Spent: ${month_stats['monthly_cost_usd']:.2f} ({month_stats['monthly_budget_percent']:.1f}%)")
    
    # Recent alerts
    if 'recent_alerts' in today_stats and today_stats['recent_alerts']:
        print("\nRecent Alerts:")
        for alert in today_stats['recent_alerts'][:5]:
            print(f"  [{alert['created_at']}] {alert['alert_type'].upper()}: {alert['message']}")
    
    # Usage by model
    print("\nUsage by Model:")
    model_usage = limiter.get_usage_by_model()
    for model, stats in model_usage.items():
        print(f"  {model}:")
        print(f"    Requests: {stats['request_count']}")
        print(f"    Tokens: {stats['total_tokens']:,}")
        print(f"    Cost: ${stats['total_cost']:.4f}")
    
    print("\n" + "="*60)


async def main():
    """Main example function"""
    
    # Create database path
    db_path = Path("example_rate_limiter.db")
    
    # Initialize database rate limiter with quotas
    limiter = DatabaseRateLimiter(
        db_path=str(db_path),
        requests_per_minute=60,
        requests_per_hour=3000,
        burst_size=10,
        daily_token_quota=50000,      # 50k tokens per day
        monthly_budget_usd=25.00,     # $25 monthly budget
        model_name="claude-3-5-sonnet"
    )
    
    # Add custom alerts
    limiter.add_alert(
        threshold_percent=30.0,
        message="30% of quota consumed - monitoring usage",
        alert_type="info"
    )
    
    limiter.add_alert(
        threshold_percent=75.0,
        message="75% of quota consumed - consider pausing non-critical tasks",
        alert_type="warning",
        callback=custom_alert_handler
    )
    
    logger.info("Starting API usage simulation...")
    
    try:
        # Simulate API requests
        await simulate_api_requests(limiter, num_requests=20)
        
        # Display statistics
        display_usage_stats(limiter)
        
        # Update quotas (example)
        logger.info("\nUpdating quotas...")
        limiter.set_quota("daily_tokens", 100000)  # Increase to 100k tokens
        limiter.set_quota("monthly_budget", 50.00)  # Increase to $50
        
        # Make more requests with new quotas
        await simulate_api_requests(limiter, num_requests=10)
        
        # Final statistics
        display_usage_stats(limiter)
        
    except Exception as e:
        logger.error(f"Example failed: {e}")
        raise
    
    finally:
        # Clean up example database
        if db_path.exists():
            logger.info(f"Example complete. Database saved at: {db_path}")
            # Uncomment to clean up:
            # db_path.unlink()


if __name__ == "__main__":
    asyncio.run(main())