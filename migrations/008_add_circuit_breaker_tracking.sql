-- Migration: Add Circuit Breaker Tracking Tables
-- Date: 2025-01-09
-- Purpose: Add database tracking for circuit breakers to persist state and analyze patterns

-- Table to track circuit breaker states for different services
CREATE TABLE IF NOT EXISTS circuit_breaker_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL UNIQUE,
    current_state TEXT NOT NULL CHECK (current_state IN ('closed', 'open', 'half_open')),
    failure_count INTEGER NOT NULL DEFAULT 0,
    failure_threshold INTEGER NOT NULL DEFAULT 5,
    recovery_timeout INTEGER NOT NULL DEFAULT 60,
    last_failure_time TIMESTAMP,
    last_success_time TIMESTAMP,
    state_changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Table to track circuit breaker state change events
CREATE TABLE IF NOT EXISTS circuit_breaker_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('state_change', 'failure', 'success', 'manual_reset', 'threshold_adjusted')),
    from_state TEXT,
    to_state TEXT,
    failure_count INTEGER,
    error_type TEXT,
    error_message TEXT,
    additional_data TEXT, -- JSON field for extra event data
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (service_name) REFERENCES circuit_breaker_states(service_name)
);

-- Table to track failure patterns for intelligent analysis
CREATE TABLE IF NOT EXISTS circuit_breaker_failure_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL,
    pattern_type TEXT NOT NULL CHECK (pattern_type IN ('burst', 'steady', 'intermittent', 'escalating')),
    time_window_seconds INTEGER NOT NULL,
    failure_count INTEGER NOT NULL,
    error_rate REAL NOT NULL,
    most_common_error TEXT,
    suggested_threshold INTEGER,
    suggested_timeout INTEGER,
    confidence_score REAL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (service_name) REFERENCES circuit_breaker_states(service_name)
);

-- Table to track circuit breaker performance metrics
CREATE TABLE IF NOT EXISTS circuit_breaker_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL,
    measurement_period_start TIMESTAMP NOT NULL,
    measurement_period_end TIMESTAMP NOT NULL,
    total_calls INTEGER NOT NULL DEFAULT 0,
    successful_calls INTEGER NOT NULL DEFAULT 0,
    failed_calls INTEGER NOT NULL DEFAULT 0,
    circuit_open_count INTEGER NOT NULL DEFAULT 0,
    circuit_open_duration_seconds INTEGER NOT NULL DEFAULT 0,
    average_response_time_ms REAL,
    p95_response_time_ms REAL,
    p99_response_time_ms REAL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (service_name) REFERENCES circuit_breaker_states(service_name),
    UNIQUE(service_name, measurement_period_start, measurement_period_end)
);

-- Table for circuit breaker alerts
CREATE TABLE IF NOT EXISTS circuit_breaker_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL,
    alert_type TEXT NOT NULL CHECK (alert_type IN ('circuit_opened', 'circuit_closed', 'high_failure_rate', 'pattern_detected', 'threshold_recommendation')),
    severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'error', 'critical')),
    message TEXT NOT NULL,
    details TEXT, -- JSON field for additional alert data
    acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    acknowledged_by TEXT,
    acknowledged_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (service_name) REFERENCES circuit_breaker_states(service_name)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_cb_events_service_time ON circuit_breaker_events(service_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cb_events_type ON circuit_breaker_events(event_type);
CREATE INDEX IF NOT EXISTS idx_cb_patterns_service ON circuit_breaker_failure_patterns(service_name, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_cb_metrics_service_period ON circuit_breaker_metrics(service_name, measurement_period_start DESC);
CREATE INDEX IF NOT EXISTS idx_cb_alerts_unack ON circuit_breaker_alerts(acknowledged, created_at DESC) WHERE acknowledged = FALSE;

-- Trigger to update the updated_at timestamp on circuit_breaker_states
CREATE TRIGGER IF NOT EXISTS update_circuit_breaker_states_timestamp 
AFTER UPDATE ON circuit_breaker_states
BEGIN
    UPDATE circuit_breaker_states SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;