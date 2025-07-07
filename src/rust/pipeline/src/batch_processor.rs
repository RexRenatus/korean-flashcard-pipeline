use crate::errors::{PipelineError, Result};
use crate::python_bridge::ApiClient;
use flashcard_core::{
    models::{VocabularyItem, Stage1Result, Stage2Result, ProcessingStatus},
    repositories::{QueueRepository, CacheRepository},
    cache_manager::CacheManager,
};
use std::sync::Arc;
use tokio::sync::{Semaphore, mpsc};
use tracing::{info, warn, error, debug, instrument};
use indicatif::{ProgressBar, ProgressStyle, MultiProgress};
use console::style;
use crossbeam_channel;
use std::time::{Duration, Instant};
use parking_lot::RwLock;

pub struct BatchProcessor {
    api_client: Arc<dyn ApiClient>,
    cache_manager: Arc<CacheManager>,
    queue_repo: Arc<dyn QueueRepository>,
    semaphore: Arc<Semaphore>,
    progress: Arc<RwLock<ProcessingProgress>>,
}

struct ProcessingProgress {
    total: usize,
    completed: usize,
    cached: usize,
    failed: usize,
    start_time: Instant,
}

impl ProcessingProgress {
    fn new(total: usize) -> Self {
        Self {
            total,
            completed: 0,
            cached: 0,
            failed: 0,
            start_time: Instant::now(),
        }
    }
    
    fn eta(&self) -> Option<Duration> {
        if self.completed == 0 {
            return None;
        }
        
        let elapsed = self.start_time.elapsed();
        let rate = self.completed as f64 / elapsed.as_secs_f64();
        let remaining = self.total - self.completed;
        
        Some(Duration::from_secs_f64(remaining as f64 / rate))
    }
}

pub struct BatchResult {
    pub successful: Vec<(VocabularyItem, Stage2Result)>,
    pub failed: Vec<(VocabularyItem, String)>,
    pub total_processed: usize,
    pub cache_hits: usize,
    pub processing_time: Duration,
}

impl BatchProcessor {
    pub fn new(
        api_client: Arc<dyn ApiClient>,
        cache_manager: Arc<CacheManager>,
        queue_repo: Arc<dyn QueueRepository>,
        max_concurrent: usize,
    ) -> Self {
        Self {
            api_client,
            cache_manager,
            queue_repo,
            semaphore: Arc::new(Semaphore::new(max_concurrent)),
            progress: Arc::new(RwLock::new(ProcessingProgress::new(0))),
        }
    }
    
    #[instrument(skip(self, items))]
    pub async fn process_batch(
        &self,
        items: Vec<VocabularyItem>,
        batch_id: i32,
    ) -> Result<BatchResult> {
        let total = items.len();
        info!("Starting batch processing for {} items", total);
        
        // Initialize progress
        {
            let mut progress = self.progress.write();
            *progress = ProcessingProgress::new(total);
        }
        
        // Create progress bars
        let multi_progress = MultiProgress::new();
        let main_bar = multi_progress.add(ProgressBar::new(total as u64));
        main_bar.set_style(
            ProgressStyle::default_bar()
                .template("{spinner:.green} [{bar:40.cyan/blue}] {pos}/{len} ({percent}%) {msg}")
                .unwrap()
                .progress_chars("#>-"),
        );
        
        let eta_bar = multi_progress.add(ProgressBar::new_spinner());
        eta_bar.set_style(
            ProgressStyle::default_spinner()
                .template("{spinner:.yellow} {msg}")
                .unwrap(),
        );
        
        // Spawn progress updater
        let progress_handle = {
            let progress = Arc::clone(&self.progress);
            let main_bar = main_bar.clone();
            let eta_bar = eta_bar.clone();
            
            tokio::spawn(async move {
                loop {
                    tokio::time::sleep(Duration::from_millis(100)).await;
                    
                    let prog = progress.read();
                    main_bar.set_position(prog.completed as u64);
                    main_bar.set_message(format!(
                        "✓ {} | ⚡ {} cached | ✗ {} failed",
                        style(prog.completed).green(),
                        style(prog.cached).yellow(),
                        style(prog.failed).red()
                    ));
                    
                    if let Some(eta) = prog.eta() {
                        eta_bar.set_message(format!(
                            "ETA: {} | Rate: {:.1} items/sec",
                            humantime::format_duration(eta),
                            prog.completed as f64 / prog.start_time.elapsed().as_secs_f64()
                        ));
                    }
                    
                    if prog.completed >= prog.total {
                        break;
                    }
                }
            })
        };
        
        // Create checkpoint
        self.queue_repo.create_checkpoint(batch_id).await?;
        
        // Process items concurrently
        let (tx, mut rx) = mpsc::channel(100);
        let mut handles = Vec::new();
        
        for item in items {
            let permit = Arc::clone(&self.semaphore);
            let api_client = Arc::clone(&self.api_client);
            let cache_manager = Arc::clone(&self.cache_manager);
            let queue_repo = Arc::clone(&self.queue_repo);
            let progress = Arc::clone(&self.progress);
            let tx = tx.clone();
            
            let handle = tokio::spawn(async move {
                let _permit = permit.acquire().await.unwrap();
                let result = Self::process_single_item(
                    &item,
                    api_client,
                    cache_manager,
                    queue_repo,
                    batch_id,
                ).await;
                
                // Update progress
                {
                    let mut prog = progress.write();
                    prog.completed += 1;
                    match &result {
                        Ok((_, was_cached)) => {
                            if *was_cached {
                                prog.cached += 1;
                            }
                        }
                        Err(_) => {
                            prog.failed += 1;
                        }
                    }
                }
                
                tx.send((item, result)).await.ok();
            });
            
            handles.push(handle);
        }
        
        drop(tx);
        
        // Collect results
        let mut successful = Vec::new();
        let mut failed = Vec::new();
        let mut cache_hits = 0;
        
        while let Some((item, result)) = rx.recv().await {
            match result {
                Ok((stage2_result, was_cached)) => {
                    successful.push((item, stage2_result));
                    if was_cached {
                        cache_hits += 1;
                    }
                }
                Err(e) => {
                    failed.push((item, e.to_string()));
                }
            }
        }
        
        // Wait for all tasks
        for handle in handles {
            handle.await.map_err(|e| PipelineError::PythonError(e.to_string()))?;
        }
        
        // Stop progress updater
        progress_handle.abort();
        
        // Finalize progress bars
        main_bar.finish_with_message(format!(
            "✅ Completed: {} successful, {} failed, {} cached",
            style(successful.len()).green(),
            style(failed.len()).red(),
            style(cache_hits).yellow()
        ));
        
        let processing_time = self.progress.read().start_time.elapsed();
        info!(
            "Batch processing complete: {} successful, {} failed, {} cache hits in {:?}",
            successful.len(),
            failed.len(),
            cache_hits,
            processing_time
        );
        
        Ok(BatchResult {
            successful,
            failed,
            total_processed: total,
            cache_hits,
            processing_time,
        })
    }
    
    async fn process_single_item(
        item: &VocabularyItem,
        api_client: Arc<dyn ApiClient>,
        cache_manager: Arc<CacheManager>,
        queue_repo: Arc<dyn QueueRepository>,
        batch_id: i32,
    ) -> Result<(Stage2Result, bool)> {
        debug!("Processing item: {} (position {})", item.term, item.position);
        
        // Update status to processing
        queue_repo.update_item_status(
            batch_id,
            item.position,
            ProcessingStatus::Processing { stage: 1 },
        ).await?;
        
        // Stage 1: Semantic Analysis
        let (stage1_result, stage1_cached) = match cache_manager.get_or_compute_stage1(
            item,
            |item| api_client.process_stage1(item),
        ).await {
            Ok(result) => result,
            Err(e) => {
                queue_repo.update_item_status(
                    batch_id,
                    item.position,
                    ProcessingStatus::Failed {
                        error: e.to_string(),
                        retry_count: 0,
                    },
                ).await?;
                return Err(e);
            }
        };
        
        // Update status to stage 2
        queue_repo.update_item_status(
            batch_id,
            item.position,
            ProcessingStatus::Processing { stage: 2 },
        ).await?;
        
        // Stage 2: Card Generation
        let (stage2_result, stage2_cached) = match cache_manager.get_or_compute_stage2(
            item,
            &stage1_result,
            |item, stage1| api_client.process_stage2(item, stage1),
        ).await {
            Ok(result) => result,
            Err(e) => {
                queue_repo.update_item_status(
                    batch_id,
                    item.position,
                    ProcessingStatus::Failed {
                        error: e.to_string(),
                        retry_count: 0,
                    },
                ).await?;
                return Err(e);
            }
        };
        
        // Update status to completed
        queue_repo.update_item_status(
            batch_id,
            item.position,
            ProcessingStatus::Completed,
        ).await?;
        
        let was_fully_cached = stage1_cached && stage2_cached;
        Ok((stage2_result, was_fully_cached))
    }
    
    pub async fn resume_batch(&self, batch_id: i32) -> Result<BatchResult> {
        info!("Resuming batch {}", batch_id);
        
        // Get incomplete items
        let incomplete = self.queue_repo.get_incomplete_items(batch_id).await?;
        
        if incomplete.is_empty() {
            info!("No incomplete items found for batch {}", batch_id);
            return Ok(BatchResult {
                successful: vec![],
                failed: vec![],
                total_processed: 0,
                cache_hits: 0,
                processing_time: Duration::from_secs(0),
            });
        }
        
        info!("Found {} incomplete items to process", incomplete.len());
        self.process_batch(incomplete, batch_id).await
    }
}