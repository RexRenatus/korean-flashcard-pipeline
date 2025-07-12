-- Migration: Add API usage tracking tables
-- Purpose: Track API usage, costs, and enforce quotas
-- Date: 2025-01-09

-- API usage tracking table
CREATE TABLE IF NOT EXISTS api_usage_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    model_name TEXT NOT NULL,
    endpoint TEXT,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    estimated_cost_usd REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'success',
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(request_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_api_usage_created_at 
ON api_usage_tracking(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_api_usage_model_name 
ON api_usage_tracking(model_name);

CREATE INDEX IF NOT EXISTS idx_api_usage_status
ON api_usage_tracking(status);

-- Quota configuration table
CREATE TABLE IF NOT EXISTS api_quota_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quota_type TEXT NOT NULL,  -- 'daily_tokens', 'monthly_budget'
    quota_value REAL NOT NULL,
    effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(quota_type, effective_date)
);

-- Rate limiter state table for persistence
CREATE TABLE IF NOT EXISTS rate_limiter_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    limiter_id TEXT NOT NULL UNIQUE,
    minute_tokens REAL NOT NULL,
    hour_window TEXT NOT NULL,  -- JSON array of timestamps
    last_update REAL NOT NULL,
    saved_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Usage alerts log
CREATE TABLE IF NOT EXISTS usage_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT NOT NULL,
    threshold_percent REAL NOT NULL,
    current_usage REAL NOT NULL,
    quota_type TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create index for alert queries
CREATE INDEX IF NOT EXISTS idx_usage_alerts_created_at
ON usage_alerts(created_at DESC);

-- Add views for common queries

-- Daily usage summary view
CREATE VIEW IF NOT EXISTS v_daily_usage_summary AS
SELECT 
    DATE(created_at) as usage_date,
    COUNT(*) as total_requests,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_requests,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_requests,
    SUM(input_tokens) as total_input_tokens,
    SUM(output_tokens) as total_output_tokens,
    SUM(total_tokens) as total_tokens,
    SUM(estimated_cost_usd) as total_cost_usd,
    AVG(total_tokens) as avg_tokens_per_request
FROM api_usage_tracking
GROUP BY DATE(created_at)
ORDER BY usage_date DESC;

-- Current quota status view
CREATE VIEW IF NOT EXISTS v_current_quota_status AS
SELECT 
    'daily_tokens' as quota_type,
    COALESCE((
        SELECT quota_value 
        FROM api_quota_config 
        WHERE quota_type = 'daily_tokens' 
        AND effective_date = DATE('now')
        ORDER BY created_at DESC 
        LIMIT 1
    ), 0) as quota_limit,
    COALESCE((
        SELECT SUM(total_tokens)
        FROM api_usage_tracking
        WHERE DATE(created_at) = DATE('now')
        AND status = 'success'
    ), 0) as current_usage,
    CASE 
        WHEN COALESCE((
            SELECT quota_value 
            FROM api_quota_config 
            WHERE quota_type = 'daily_tokens' 
            AND effective_date = DATE('now')
            ORDER BY created_at DESC 
            LIMIT 1
        ), 0) > 0 THEN
            ROUND(
                100.0 * COALESCE((
                    SELECT SUM(total_tokens)
                    FROM api_usage_tracking
                    WHERE DATE(created_at) = DATE('now')
                    AND status = 'success'
                ), 0) / (
                    SELECT quota_value 
                    FROM api_quota_config 
                    WHERE quota_type = 'daily_tokens' 
                    AND effective_date = DATE('now')
                    ORDER BY created_at DESC 
                    LIMIT 1
                ), 2
            )
        ELSE 0
    END as usage_percent
UNION ALL
SELECT 
    'monthly_budget' as quota_type,
    COALESCE((
        SELECT quota_value 
        FROM api_quota_config 
        WHERE quota_type = 'monthly_budget' 
        AND effective_date = DATE('now', 'start of month')
        ORDER BY created_at DESC 
        LIMIT 1
    ), 0) as quota_limit,
    COALESCE((
        SELECT SUM(estimated_cost_usd)
        FROM api_usage_tracking
        WHERE DATE(created_at) >= DATE('now', 'start of month')
        AND status = 'success'
    ), 0) as current_usage,
    CASE 
        WHEN COALESCE((
            SELECT quota_value 
            FROM api_quota_config 
            WHERE quota_type = 'monthly_budget' 
            AND effective_date = DATE('now', 'start of month')
            ORDER BY created_at DESC 
            LIMIT 1
        ), 0) > 0 THEN
            ROUND(
                100.0 * COALESCE((
                    SELECT SUM(estimated_cost_usd)
                    FROM api_usage_tracking
                    WHERE DATE(created_at) >= DATE('now', 'start of month')
                    AND status = 'success'
                ), 0) / (
                    SELECT quota_value 
                    FROM api_quota_config 
                    WHERE quota_type = 'monthly_budget' 
                    AND effective_date = DATE('now', 'start of month')
                    ORDER BY created_at DESC 
                    LIMIT 1
                ), 2
            )
        ELSE 0
    END as usage_percent;