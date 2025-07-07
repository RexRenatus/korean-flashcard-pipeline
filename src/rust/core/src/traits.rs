use async_trait::async_trait;
use crate::models::{
    VocabularyItem, Stage1Result, Stage2Result, QueueItem, BatchProgress,
    ProcessingCheckpoint, ProcessingStatus, ProcessingStage, CacheStats,
    CacheType, PipelineError
};

#[async_trait]
pub trait VocabularyRepository: Send + Sync {
    async fn create(&self, item: &VocabularyItem) -> Result<i64, PipelineError>;
    async fn get_by_id(&self, id: i64) -> Result<Option<VocabularyItem>, PipelineError>;
    async fn find_by_content(
        &self, 
        korean: &str, 
        english: &str, 
        category: &str
    ) -> Result<Option<VocabularyItem>, PipelineError>;
    async fn list_by_category(&self, category: &str) -> Result<Vec<VocabularyItem>, PipelineError>;
    async fn list_unprocessed(&self, limit: i32) -> Result<Vec<VocabularyItem>, PipelineError>;
    async fn update(&self, item: &VocabularyItem) -> Result<(), PipelineError>;
    async fn delete(&self, id: i64) -> Result<bool, PipelineError>;
    async fn count(&self) -> Result<i64, PipelineError>;
}

#[async_trait]
pub trait CacheRepository: Send + Sync {
    async fn get_stage1_cache(&self, cache_key: &str) -> Result<Option<Stage1Result>, PipelineError>;
    async fn save_stage1_cache(
        &self, 
        result: &Stage1Result,
        request_hash: String,
        token_count: i32,
        model_used: String,
    ) -> Result<(), PipelineError>;
    
    async fn get_stage2_cache(&self, cache_key: &str) -> Result<Option<Stage2Result>, PipelineError>;
    async fn save_stage2_cache(
        &self,
        result: &Stage2Result,
        request_hash: String,
        token_count: i32,
        model_used: String,
    ) -> Result<(), PipelineError>;
    
    async fn get_cache_stats(&self) -> Result<CacheStats, PipelineError>;
    async fn clear_cache(&self, cache_type: Option<CacheType>) -> Result<i64, PipelineError>;
}

#[async_trait]
pub trait QueueRepository: Send + Sync {
    async fn enqueue_batch(&self, vocabulary_ids: Vec<i64>, batch_id: &str) -> Result<i64, PipelineError>;
    async fn get_next_pending(&self, batch_id: Option<&str>) -> Result<Option<QueueItem>, PipelineError>;
    async fn update_status(
        &self, 
        item_id: i64, 
        status: ProcessingStatus,
        error_message: Option<String>
    ) -> Result<(), PipelineError>;
    async fn complete_stage(&self, item_id: i64) -> Result<ProcessingStage, PipelineError>;
    async fn increment_retry(&self, item_id: i64) -> Result<bool, PipelineError>;
    async fn get_batch_progress(&self, batch_id: &str) -> Result<BatchProgress, PipelineError>;
    async fn save_checkpoint(
        &self,
        batch_id: &str,
        last_processed_id: i64,
        stage: ProcessingStage,
        checkpoint_data: serde_json::Value,
    ) -> Result<(), PipelineError>;
    async fn get_latest_checkpoint(&self, batch_id: &str) -> Result<Option<ProcessingCheckpoint>, PipelineError>;
}

#[async_trait]
pub trait ApiClient: Send + Sync {
    async fn process_stage1(&self, vocabulary_item: &VocabularyItem) -> Result<Stage1Result, PipelineError>;
    async fn process_stage2(
        &self, 
        vocabulary_item: &VocabularyItem,
        stage1_result: &Stage1Result
    ) -> Result<Stage2Result, PipelineError>;
    async fn get_rate_limit_status(&self) -> Result<RateLimitStatus, PipelineError>;
}

#[derive(Debug, Clone)]
pub struct RateLimitStatus {
    pub requests_remaining: u32,
    pub requests_limit: u32,
    pub reset_at: chrono::DateTime<chrono::Utc>,
    pub retry_after: Option<std::time::Duration>,
}

#[async_trait]
pub trait Pipeline: Send + Sync {
    async fn process_batch(&self, batch_id: &str) -> Result<BatchProgress, PipelineError>;
    async fn process_single(&self, vocabulary_item: &VocabularyItem) -> Result<String, PipelineError>;
    async fn resume_batch(&self, batch_id: &str) -> Result<BatchProgress, PipelineError>;
    async fn get_batch_status(&self, batch_id: &str) -> Result<BatchProgress, PipelineError>;
}

#[async_trait]
pub trait MetricsCollector: Send + Sync {
    async fn record_api_call(
        &self,
        endpoint: &str,
        model: &str,
        status_code: Option<u16>,
        response_time_ms: u64,
        token_count: Option<i32>,
        error_message: Option<&str>,
    ) -> Result<(), PipelineError>;
    
    async fn record_cache_hit(&self, cache_type: CacheType, tokens_saved: i32) -> Result<(), PipelineError>;
    async fn record_cache_miss(&self, cache_type: CacheType) -> Result<(), PipelineError>;
    async fn get_metrics_summary(&self) -> Result<MetricsSummary, PipelineError>;
}

#[derive(Debug, Clone)]
pub struct MetricsSummary {
    pub total_api_calls: i64,
    pub successful_calls: i64,
    pub failed_calls: i64,
    pub average_response_time_ms: f64,
    pub total_tokens_used: i64,
    pub cache_hit_rate: f64,
    pub estimated_cost: f64,
}

#[async_trait]
pub trait HealthCheck: Send + Sync {
    async fn check_database(&self) -> Result<bool, PipelineError>;
    async fn check_api(&self) -> Result<bool, PipelineError>;
    async fn check_cache(&self) -> Result<bool, PipelineError>;
    async fn get_system_status(&self) -> Result<SystemStatus, PipelineError>;
}

#[derive(Debug, Clone)]
pub struct SystemStatus {
    pub database_healthy: bool,
    pub api_healthy: bool,
    pub cache_healthy: bool,
    pub queue_size: i64,
    pub cache_size: i64,
    pub last_error: Option<String>,
    pub uptime: std::time::Duration,
}