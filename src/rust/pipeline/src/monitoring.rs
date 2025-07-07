use crate::errors::{PipelineError, Result};
use flashcard_core::repositories::{CacheRepository, QueueRepository};
use std::sync::Arc;
use parking_lot::RwLock;
use std::time::{Duration, Instant};
use tracing::{info, debug, instrument};
use serde::{Serialize, Deserialize};
use chrono::{DateTime, Utc};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PipelineMetrics {
    pub start_time: DateTime<Utc>,
    pub items_processed: usize,
    pub items_succeeded: usize,
    pub items_failed: usize,
    pub cache_hits: usize,
    pub cache_misses: usize,
    pub api_calls: usize,
    pub api_tokens_used: usize,
    pub api_errors: usize,
    pub rate_limit_hits: usize,
    pub average_processing_time_ms: f64,
    pub total_processing_time: Duration,
    pub estimated_cost: f64,
}

impl Default for PipelineMetrics {
    fn default() -> Self {
        Self {
            start_time: Utc::now(),
            items_processed: 0,
            items_succeeded: 0,
            items_failed: 0,
            cache_hits: 0,
            cache_misses: 0,
            api_calls: 0,
            api_tokens_used: 0,
            api_errors: 0,
            rate_limit_hits: 0,
            average_processing_time_ms: 0.0,
            total_processing_time: Duration::from_secs(0),
            estimated_cost: 0.0,
        }
    }
}

pub struct MetricsCollector {
    metrics: Arc<RwLock<PipelineMetrics>>,
    item_timings: Arc<RwLock<Vec<Duration>>>,
}

impl MetricsCollector {
    pub fn new() -> Self {
        Self {
            metrics: Arc::new(RwLock::new(PipelineMetrics::default())),
            item_timings: Arc::new(RwLock::new(Vec::new())),
        }
    }
    
    pub fn record_item_processed(&self, success: bool, processing_time: Duration) {
        let mut metrics = self.metrics.write();
        metrics.items_processed += 1;
        
        if success {
            metrics.items_succeeded += 1;
        } else {
            metrics.items_failed += 1;
        }
        
        // Update timings
        let mut timings = self.item_timings.write();
        timings.push(processing_time);
        
        // Calculate average
        let total_ms: f64 = timings.iter().map(|d| d.as_millis() as f64).sum();
        metrics.average_processing_time_ms = total_ms / timings.len() as f64;
        metrics.total_processing_time = Duration::from_millis(total_ms as u64);
    }
    
    pub fn record_cache_hit(&self) {
        self.metrics.write().cache_hits += 1;
    }
    
    pub fn record_cache_miss(&self) {
        self.metrics.write().cache_misses += 1;
    }
    
    pub fn record_api_call(&self, tokens_used: usize) {
        let mut metrics = self.metrics.write();
        metrics.api_calls += 1;
        metrics.api_tokens_used += tokens_used;
        
        // Estimate cost (Claude Sonnet 4 pricing)
        // Input: $3 per million tokens
        // Output: $15 per million tokens
        // Rough estimate: average $10 per million tokens
        metrics.estimated_cost = (metrics.api_tokens_used as f64 / 1_000_000.0) * 10.0;
    }
    
    pub fn record_api_error(&self) {
        self.metrics.write().api_errors += 1;
    }
    
    pub fn record_rate_limit(&self) {
        self.metrics.write().rate_limit_hits += 1;
    }
    
    pub fn get_metrics(&self) -> PipelineMetrics {
        self.metrics.read().clone()
    }
    
    pub fn get_cache_hit_rate(&self) -> f64 {
        let metrics = self.metrics.read();
        let total = metrics.cache_hits + metrics.cache_misses;
        if total == 0 {
            0.0
        } else {
            metrics.cache_hits as f64 / total as f64 * 100.0
        }
    }
    
    pub fn get_success_rate(&self) -> f64 {
        let metrics = self.metrics.read();
        if metrics.items_processed == 0 {
            0.0
        } else {
            metrics.items_succeeded as f64 / metrics.items_processed as f64 * 100.0
        }
    }
    
    #[instrument(skip(self))]
    pub fn print_summary(&self) {
        let metrics = self.get_metrics();
        let cache_hit_rate = self.get_cache_hit_rate();
        let success_rate = self.get_success_rate();
        
        info!("Pipeline Metrics Summary:");
        info!("  Items processed: {}", metrics.items_processed);
        info!("  Success rate: {:.1}%", success_rate);
        info!("  Cache hit rate: {:.1}%", cache_hit_rate);
        info!("  API calls made: {}", metrics.api_calls);
        info!("  Tokens used: {}", metrics.api_tokens_used);
        info!("  Estimated cost: ${:.2}", metrics.estimated_cost);
        info!("  Average processing time: {:.0}ms", metrics.average_processing_time_ms);
        info!("  Total processing time: {:?}", metrics.total_processing_time);
        
        if metrics.api_errors > 0 {
            info!("  API errors: {}", metrics.api_errors);
        }
        if metrics.rate_limit_hits > 0 {
            info!("  Rate limit hits: {}", metrics.rate_limit_hits);
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthStatus {
    pub healthy: bool,
    pub database_status: ServiceStatus,
    pub cache_status: ServiceStatus,
    pub api_status: ServiceStatus,
    pub python_bridge_status: ServiceStatus,
    pub last_check: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ServiceStatus {
    Healthy,
    Degraded(String),
    Unhealthy(String),
}

impl ServiceStatus {
    pub fn is_healthy(&self) -> bool {
        matches!(self, ServiceStatus::Healthy)
    }
}

pub struct HealthChecker {
    cache_repo: Arc<dyn CacheRepository>,
    queue_repo: Arc<dyn QueueRepository>,
}

impl HealthChecker {
    pub fn new(
        cache_repo: Arc<dyn CacheRepository>,
        queue_repo: Arc<dyn QueueRepository>,
    ) -> Self {
        Self {
            cache_repo,
            queue_repo,
        }
    }
    
    #[instrument(skip(self))]
    pub async fn check_health(&self) -> Result<HealthStatus> {
        debug!("Running health check");
        
        let mut status = HealthStatus {
            healthy: true,
            database_status: ServiceStatus::Healthy,
            cache_status: ServiceStatus::Healthy,
            api_status: ServiceStatus::Healthy,
            python_bridge_status: ServiceStatus::Healthy,
            last_check: Utc::now(),
        };
        
        // Check database
        match self.check_database().await {
            Ok(_) => {
                debug!("Database health check passed");
            }
            Err(e) => {
                status.database_status = ServiceStatus::Unhealthy(e.to_string());
                status.healthy = false;
            }
        }
        
        // Check cache
        match self.check_cache().await {
            Ok(_) => {
                debug!("Cache health check passed");
            }
            Err(e) => {
                status.cache_status = ServiceStatus::Unhealthy(e.to_string());
                status.healthy = false;
            }
        }
        
        // Check Python bridge
        #[cfg(feature = "python")]
        {
            match self.check_python_bridge().await {
                Ok(_) => {
                    debug!("Python bridge health check passed");
                }
                Err(e) => {
                    status.python_bridge_status = ServiceStatus::Unhealthy(e.to_string());
                    status.healthy = false;
                }
            }
        }
        
        // API status would be checked via the Python bridge
        
        info!("Health check complete: {}", if status.healthy { "HEALTHY" } else { "UNHEALTHY" });
        Ok(status)
    }
    
    async fn check_database(&self) -> Result<()> {
        // Try to get batch count
        self.queue_repo.get_batch_count().await?;
        Ok(())
    }
    
    async fn check_cache(&self) -> Result<()> {
        // Try to get cache stats
        self.cache_repo.get_cache_stats().await?;
        Ok(())
    }
    
    #[cfg(feature = "python")]
    async fn check_python_bridge(&self) -> Result<()> {
        use crate::python_bridge::create_api_client;
        
        let client = create_api_client()?;
        client.health_check().await?;
        Ok(())
    }
}

// Prometheus-compatible metrics export
impl PipelineMetrics {
    pub fn to_prometheus_format(&self) -> String {
        let mut output = String::new();
        
        output.push_str("# HELP pipeline_items_processed Total number of items processed\n");
        output.push_str("# TYPE pipeline_items_processed counter\n");
        output.push_str(&format!("pipeline_items_processed {}\n", self.items_processed));
        
        output.push_str("# HELP pipeline_items_succeeded Total number of items successfully processed\n");
        output.push_str("# TYPE pipeline_items_succeeded counter\n");
        output.push_str(&format!("pipeline_items_succeeded {}\n", self.items_succeeded));
        
        output.push_str("# HELP pipeline_items_failed Total number of items that failed processing\n");
        output.push_str("# TYPE pipeline_items_failed counter\n");
        output.push_str(&format!("pipeline_items_failed {}\n", self.items_failed));
        
        output.push_str("# HELP pipeline_cache_hits Total number of cache hits\n");
        output.push_str("# TYPE pipeline_cache_hits counter\n");
        output.push_str(&format!("pipeline_cache_hits {}\n", self.cache_hits));
        
        output.push_str("# HELP pipeline_api_calls Total number of API calls made\n");
        output.push_str("# TYPE pipeline_api_calls counter\n");
        output.push_str(&format!("pipeline_api_calls {}\n", self.api_calls));
        
        output.push_str("# HELP pipeline_api_tokens_used Total number of tokens used\n");
        output.push_str("# TYPE pipeline_api_tokens_used counter\n");
        output.push_str(&format!("pipeline_api_tokens_used {}\n", self.api_tokens_used));
        
        output.push_str("# HELP pipeline_estimated_cost_dollars Estimated cost in dollars\n");
        output.push_str("# TYPE pipeline_estimated_cost_dollars gauge\n");
        output.push_str(&format!("pipeline_estimated_cost_dollars {:.4}\n", self.estimated_cost));
        
        output.push_str("# HELP pipeline_average_processing_time_ms Average processing time per item in milliseconds\n");
        output.push_str("# TYPE pipeline_average_processing_time_ms gauge\n");
        output.push_str(&format!("pipeline_average_processing_time_ms {:.2}\n", self.average_processing_time_ms));
        
        output
    }
}