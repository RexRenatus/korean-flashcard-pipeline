use tracing::{Level, Metadata, Subscriber};
use tracing_subscriber::{
    fmt::{self, format::FmtSpan, time::UtcTime},
    prelude::*,
    EnvFilter, Registry,
};
use std::io;

pub fn init_logging(log_level: Option<&str>) -> Result<(), Box<dyn std::error::Error>> {
    let env_filter = EnvFilter::try_from_default_env()
        .or_else(|_| EnvFilter::try_new(log_level.unwrap_or("info")))
        .unwrap();

    let fmt_layer = fmt::layer()
        .with_target(true)
        .with_thread_ids(true)
        .with_thread_names(true)
        .with_file(true)
        .with_line_number(true)
        .with_span_events(FmtSpan::CLOSE)
        .with_timer(UtcTime::rfc_3339())
        .with_ansi(true)
        .with_level(true);

    let subscriber = Registry::default()
        .with(env_filter)
        .with(fmt_layer);

    tracing::subscriber::set_global_default(subscriber)?;
    
    tracing::info!("Logging initialized with level: {}", log_level.unwrap_or("info"));
    Ok(())
}

pub fn init_json_logging(log_level: Option<&str>) -> Result<(), Box<dyn std::error::Error>> {
    let env_filter = EnvFilter::try_from_default_env()
        .or_else(|_| EnvFilter::try_new(log_level.unwrap_or("info")))
        .unwrap();

    let fmt_layer = fmt::layer()
        .json()
        .with_target(true)
        .with_thread_ids(true)
        .with_thread_names(true)
        .with_file(true)
        .with_line_number(true)
        .with_span_events(FmtSpan::CLOSE)
        .with_timer(UtcTime::rfc_3339())
        .with_level(true);

    let subscriber = Registry::default()
        .with(env_filter)
        .with(fmt_layer);

    tracing::subscriber::set_global_default(subscriber)?;
    
    tracing::info!("JSON logging initialized with level: {}", log_level.unwrap_or("info"));
    Ok(())
}

pub struct LogContext {
    pub batch_id: Option<String>,
    pub vocabulary_id: Option<i64>,
    pub stage: Option<String>,
}

impl LogContext {
    pub fn new() -> Self {
        Self {
            batch_id: None,
            vocabulary_id: None,
            stage: None,
        }
    }

    pub fn with_batch_id(mut self, batch_id: String) -> Self {
        self.batch_id = Some(batch_id);
        self
    }

    pub fn with_vocabulary_id(mut self, vocabulary_id: i64) -> Self {
        self.vocabulary_id = Some(vocabulary_id);
        self
    }

    pub fn with_stage(mut self, stage: String) -> Self {
        self.stage = Some(stage);
        self
    }
}

#[macro_export]
macro_rules! log_with_context {
    ($level:expr, $context:expr, $($arg:tt)+) => {{
        let mut span = tracing::span!($level, "pipeline");
        
        if let Some(batch_id) = &$context.batch_id {
            span = span.in_scope(|| {
                tracing::span!($level, "pipeline", batch_id = %batch_id)
            });
        }
        
        if let Some(vocab_id) = &$context.vocabulary_id {
            span = span.in_scope(|| {
                tracing::span!($level, "pipeline", vocabulary_id = %vocab_id)
            });
        }
        
        if let Some(stage) = &$context.stage {
            span = span.in_scope(|| {
                tracing::span!($level, "pipeline", stage = %stage)
            });
        }
        
        span.in_scope(|| {
            tracing::event!($level, $($arg)+);
        });
    }};
}

pub fn log_processing_start(batch_id: &str, total_items: usize) {
    tracing::info!(
        batch_id = %batch_id,
        total_items = total_items,
        "Starting batch processing"
    );
}

pub fn log_processing_complete(batch_id: &str, completed: usize, failed: usize, duration_secs: f64) {
    tracing::info!(
        batch_id = %batch_id,
        completed = completed,
        failed = failed,
        duration_secs = duration_secs,
        items_per_second = completed as f64 / duration_secs,
        "Batch processing complete"
    );
}

pub fn log_cache_hit(cache_type: &str, cache_key: &str, tokens_saved: i32) {
    tracing::debug!(
        cache_type = cache_type,
        cache_key = cache_key,
        tokens_saved = tokens_saved,
        "Cache hit"
    );
}

pub fn log_cache_miss(cache_type: &str, cache_key: &str) {
    tracing::debug!(
        cache_type = cache_type,
        cache_key = cache_key,
        "Cache miss"
    );
}

pub fn log_api_call(endpoint: &str, model: &str, tokens: i32, duration_ms: u64) {
    tracing::info!(
        endpoint = endpoint,
        model = model,
        tokens = tokens,
        duration_ms = duration_ms,
        cost_usd = (tokens as f64) * 0.15 / 1000.0,
        "API call completed"
    );
}

pub fn log_error_with_context(error: &crate::models::PipelineError, context: &LogContext) {
    let severity = error.severity();
    
    match severity {
        crate::models::ErrorSeverity::Fatal => {
            log_with_context!(Level::ERROR, context, 
                error = %error,
                severity = ?severity,
                "Fatal error occurred"
            );
        }
        crate::models::ErrorSeverity::Retryable => {
            log_with_context!(Level::WARN, context,
                error = %error,
                severity = ?severity,
                "Retryable error occurred"
            );
        }
        crate::models::ErrorSeverity::Recoverable => {
            log_with_context!(Level::INFO, context,
                error = %error,
                severity = ?severity,
                "Recoverable error occurred"
            );
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_logging_initialization() {
        // Initialize with debug level
        let result = init_logging(Some("debug"));
        assert!(result.is_ok());
        
        // Test logging
        tracing::debug!("Debug message");
        tracing::info!("Info message");
        tracing::warn!("Warning message");
        tracing::error!("Error message");
    }
    
    #[test]
    fn test_log_context() {
        let context = LogContext::new()
            .with_batch_id("test-batch".to_string())
            .with_vocabulary_id(123)
            .with_stage("stage1".to_string());
        
        assert_eq!(context.batch_id, Some("test-batch".to_string()));
        assert_eq!(context.vocabulary_id, Some(123));
        assert_eq!(context.stage, Some("stage1".to_string()));
    }
}