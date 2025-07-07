use crate::errors::{PipelineError, Result};
use crate::batch_processor::{BatchProcessor, BatchResult};
use crate::export::{TsvExporter, ExportStats};
use crate::monitoring::{MetricsCollector, HealthChecker};
use crate::python_bridge::{ApiClient, create_api_client};
use flashcard_core::{
    models::VocabularyItem,
    database::DatabasePool,
    repositories::{VocabularyRepository, CacheRepository, QueueRepository},
    cache_manager::CacheManager,
};
use std::sync::Arc;
use std::path::{Path, PathBuf};
use tracing::{info, warn, error, instrument};
use csv::ReaderBuilder;
use std::fs::File;
use parking_lot::RwLock;

pub struct Pipeline {
    api_client: Arc<dyn ApiClient>,
    cache_manager: Arc<CacheManager>,
    vocab_repo: Arc<dyn VocabularyRepository>,
    cache_repo: Arc<dyn CacheRepository>,
    queue_repo: Arc<dyn QueueRepository>,
    batch_processor: Arc<BatchProcessor>,
    pub metrics_collector: Arc<MetricsCollector>,
    pub health_checker: Arc<HealthChecker>,
    config: PipelineConfig,
}

#[derive(Clone)]
pub struct PipelineConfig {
    pub database_url: String,
    pub cache_dir: PathBuf,
    pub max_concurrent: usize,
    pub batch_size: usize,
    pub enable_metrics: bool,
    pub checkpoint_interval: usize,
}

impl Default for PipelineConfig {
    fn default() -> Self {
        Self {
            database_url: "sqlite:pipeline.db".to_string(),
            cache_dir: PathBuf::from(".cache"),
            max_concurrent: 5,
            batch_size: 10,
            enable_metrics: true,
            checkpoint_interval: 10,
        }
    }
}

impl Pipeline {
    pub async fn new(config: PipelineConfig) -> Result<Self> {
        info!("Initializing pipeline with config");
        
        // Create database pool
        let pool = DatabasePool::new(&config.database_url).await
            .map_err(|e| PipelineError::Core(e))?;
        
        // Run migrations
        pool.run_migrations().await
            .map_err(|e| PipelineError::Core(e))?;
        
        // Create repositories
        let vocab_repo = Arc::new(flashcard_core::database::repositories::SqliteVocabularyRepository::new(pool.clone()));
        let cache_repo = Arc::new(flashcard_core::database::repositories::SqliteCacheRepository::new(pool.clone()));
        let queue_repo = Arc::new(flashcard_core::database::repositories::SqliteQueueRepository::new(pool.clone()));
        
        // Create cache manager
        let cache_manager = Arc::new(CacheManager::new(
            cache_repo.clone(),
            config.cache_dir.clone(),
        ));
        
        // Create API client
        let api_client = create_api_client()?;
        
        // Create components
        let metrics_collector = Arc::new(MetricsCollector::new());
        let health_checker = Arc::new(HealthChecker::new(
            cache_repo.clone(),
            queue_repo.clone(),
        ));
        
        let batch_processor = Arc::new(BatchProcessor::new(
            api_client.clone(),
            cache_manager.clone(),
            queue_repo.clone(),
            config.max_concurrent,
        ));
        
        Ok(Self {
            api_client,
            cache_manager,
            vocab_repo,
            cache_repo,
            queue_repo,
            batch_processor,
            metrics_collector,
            health_checker,
            config,
        })
    }
    
    #[instrument(skip(self))]
    pub async fn process_csv_file(
        &self,
        input_path: &Path,
        output_path: &Path,
        resume_batch_id: Option<i32>,
    ) -> Result<ProcessingResult> {
        info!("Processing CSV file: {:?}", input_path);
        
        // Check health first
        let health = self.health_checker.check_health().await?;
        if !health.healthy {
            return Err(PipelineError::HealthCheckFailed(
                "System health check failed".to_string()
            ));
        }
        
        let start_time = std::time::Instant::now();
        
        // Load vocabulary items or resume
        let (items, batch_id) = if let Some(batch_id) = resume_batch_id {
            info!("Resuming batch {}", batch_id);
            let items = self.queue_repo.get_incomplete_items(batch_id).await?;
            (items, batch_id)
        } else {
            let items = self.load_csv(input_path).await?;
            let batch_id = self.queue_repo.create_batch(items.len()).await?;
            
            // Add items to queue
            for item in &items {
                self.queue_repo.add_item_to_batch(batch_id, item).await?;
            }
            
            (items, batch_id)
        };
        
        info!("Processing {} items in batch {}", items.len(), batch_id);
        
        // Process batch
        let batch_result = self.batch_processor.process_batch(items, batch_id).await?;
        
        // Export results
        let export_stats = if !batch_result.successful.is_empty() {
            let exporter = TsvExporter::new();
            exporter.export(&batch_result.successful, output_path).await?
        } else {
            ExportStats::default()
        };
        
        // Update metrics
        if self.config.enable_metrics {
            self.update_metrics(&batch_result).await;
            self.metrics_collector.print_summary();
        }
        
        let processing_time = start_time.elapsed();
        
        Ok(ProcessingResult {
            batch_id,
            total_items: batch_result.total_processed,
            successful_items: batch_result.successful.len(),
            failed_items: batch_result.failed.len(),
            cache_hits: batch_result.cache_hits,
            export_stats,
            processing_time,
        })
    }
    
    pub async fn load_csv(&self, path: &Path) -> Result<Vec<VocabularyItem>> {
        info!("Loading vocabulary from CSV: {:?}", path);
        
        let file = File::open(path)
            .map_err(|_| PipelineError::FileNotFound(path.to_path_buf()))?;
        
        let mut reader = ReaderBuilder::new()
            .has_headers(true)
            .from_reader(file);
        
        let mut items = Vec::new();
        
        for (index, result) in reader.records().enumerate() {
            let record = result?;
            
            // Expected format: position,term,type (optional)
            let position: i32 = record.get(0)
                .and_then(|s| s.parse().ok())
                .unwrap_or((index + 1) as i32);
                
            let term = record.get(1)
                .ok_or_else(|| PipelineError::InvalidFormat(
                    format!("Missing term at row {}", index + 1)
                ))?
                .to_string();
                
            let word_type = record.get(2).map(|s| s.to_string());
            
            items.push(VocabularyItem {
                id: None,
                position,
                term,
                word_type,
                created_at: chrono::Utc::now(),
                updated_at: chrono::Utc::now(),
            });
        }
        
        if items.is_empty() {
            return Err(PipelineError::InvalidFormat(
                "CSV file contains no valid vocabulary items".to_string()
            ));
        }
        
        info!("Loaded {} vocabulary items", items.len());
        Ok(items)
    }
    
    async fn update_metrics(&self, batch_result: &BatchResult) {
        for _ in 0..batch_result.successful.len() {
            self.metrics_collector.record_item_processed(true, batch_result.processing_time);
        }
        
        for _ in 0..batch_result.failed.len() {
            self.metrics_collector.record_item_processed(false, batch_result.processing_time);
        }
        
        // Cache metrics
        for _ in 0..batch_result.cache_hits {
            self.metrics_collector.record_cache_hit();
        }
        for _ in 0..(batch_result.total_processed - batch_result.cache_hits) {
            self.metrics_collector.record_cache_miss();
        }
    }
    
    pub async fn get_batch_status(&self, batch_id: i32) -> Result<BatchStatus> {
        let stats = self.queue_repo.get_batch_status(batch_id).await?;
        Ok(BatchStatus::from(stats))
    }
    
    pub async fn list_batches(&self) -> Result<Vec<BatchInfo>> {
        let batches = self.queue_repo.list_batches(10, 0).await?;
        Ok(batches.into_iter().map(BatchInfo::from).collect())
    }
    
    pub async fn warm_cache(&self, items: &[VocabularyItem]) -> Result<usize> {
        info!("Warming cache for {} items", items.len());
        let warmed = self.cache_manager.warm_cache(items).await?;
        info!("Cache warmed with {} items", warmed);
        Ok(warmed)
    }
    
    pub async fn get_cache_stats(&self) -> Result<CacheStats> {
        let stats = self.cache_repo.get_cache_stats().await?;
        Ok(CacheStats {
            total_entries: stats.total_entries,
            stage1_entries: stats.stage1_entries,
            stage2_entries: stats.stage2_entries,
            total_size_bytes: stats.total_size_bytes,
            cache_hit_rate: self.metrics_collector.get_cache_hit_rate(),
        })
    }
}

#[derive(Debug, Clone)]
pub struct ProcessingResult {
    pub batch_id: i32,
    pub total_items: usize,
    pub successful_items: usize,
    pub failed_items: usize,
    pub cache_hits: usize,
    pub export_stats: ExportStats,
    pub processing_time: std::time::Duration,
}

#[derive(Debug, Clone)]
pub struct BatchStatus {
    pub batch_id: i32,
    pub total_items: usize,
    pub completed_items: usize,
    pub failed_items: usize,
    pub in_progress: bool,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

impl From<flashcard_core::models::BatchStats> for BatchStatus {
    fn from(stats: flashcard_core::models::BatchStats) -> Self {
        Self {
            batch_id: stats.batch_id,
            total_items: stats.total_items,
            completed_items: stats.completed_items,
            failed_items: stats.failed_items,
            in_progress: stats.completed_items < stats.total_items,
            created_at: stats.created_at,
        }
    }
}

#[derive(Debug, Clone)]
pub struct BatchInfo {
    pub batch_id: i32,
    pub total_items: usize,
    pub status: String,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

impl From<(i32, usize, chrono::DateTime<chrono::Utc>)> for BatchInfo {
    fn from((batch_id, total_items, created_at): (i32, usize, chrono::DateTime<chrono::Utc>)) -> Self {
        Self {
            batch_id,
            total_items,
            status: "Created".to_string(),
            created_at,
        }
    }
}

#[derive(Debug, Clone)]
pub struct CacheStats {
    pub total_entries: usize,
    pub stage1_entries: usize,
    pub stage2_entries: usize,
    pub total_size_bytes: i64,
    pub cache_hit_rate: f64,
}