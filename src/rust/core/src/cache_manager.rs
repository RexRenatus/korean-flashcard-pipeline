use std::sync::Arc;
use tracing::{info, debug, warn};
use crate::models::{
    VocabularyItem, Stage1Result, Stage2Result, CacheStats, CacheType, PipelineError
};
use crate::database::{DatabasePool, repositories::CacheRepository};

pub struct CacheManager {
    repository: Arc<CacheRepository>,
}

impl CacheManager {
    pub fn new(pool: DatabasePool) -> Self {
        Self {
            repository: Arc::new(CacheRepository::new(pool)),
        }
    }

    pub async fn get_or_compute_stage1<F, Fut>(
        &self,
        vocabulary_item: &VocabularyItem,
        compute_fn: F,
    ) -> Result<Stage1Result, PipelineError>
    where
        F: FnOnce() -> Fut,
        Fut: std::future::Future<Output = Result<(Stage1Result, String, i32, String), PipelineError>>,
    {
        let cache_key = Stage1Result::generate_cache_key(vocabulary_item);
        debug!("Checking Stage 1 cache for key: {}", cache_key);

        // Check cache first
        if let Some(cached_result) = self.repository.get_stage1_cache(&cache_key).await? {
            info!("Stage 1 cache hit for vocabulary item: {}", vocabulary_item.korean);
            return Ok(cached_result);
        }

        // Cache miss - compute result
        info!("Stage 1 cache miss for vocabulary item: {}", vocabulary_item.korean);
        let (result, request_hash, token_count, model_used) = compute_fn().await?;

        // Save to cache
        self.repository.save_stage1_cache(
            &result,
            request_hash,
            token_count,
            model_used,
        ).await?;

        Ok(result)
    }

    pub async fn get_or_compute_stage2<F, Fut>(
        &self,
        vocabulary_item: &VocabularyItem,
        stage1_result: &Stage1Result,
        compute_fn: F,
    ) -> Result<Stage2Result, PipelineError>
    where
        F: FnOnce() -> Fut,
        Fut: std::future::Future<Output = Result<(Stage2Result, String, i32, String), PipelineError>>,
    {
        let cache_key = Stage2Result::generate_cache_key(vocabulary_item, &stage1_result.cache_key);
        debug!("Checking Stage 2 cache for key: {}", cache_key);

        // Check cache first
        if let Some(cached_result) = self.repository.get_stage2_cache(&cache_key).await? {
            info!("Stage 2 cache hit for vocabulary item: {}", vocabulary_item.korean);
            return Ok(cached_result);
        }

        // Cache miss - compute result
        info!("Stage 2 cache miss for vocabulary item: {}", vocabulary_item.korean);
        let (result, request_hash, token_count, model_used) = compute_fn().await?;

        // Save to cache
        self.repository.save_stage2_cache(
            &result,
            request_hash,
            token_count,
            model_used,
        ).await?;

        Ok(result)
    }

    pub async fn get_stats(&self) -> Result<CacheStats, PipelineError> {
        self.repository.get_cache_stats().await
    }

    pub async fn clear_cache(&self, cache_type: Option<CacheType>) -> Result<i64, PipelineError> {
        warn!("Clearing cache: {:?}", cache_type);
        self.repository.clear_cache(cache_type).await
    }

    pub async fn get_stage1_direct(&self, cache_key: &str) -> Result<Option<Stage1Result>, PipelineError> {
        self.repository.get_stage1_cache(cache_key).await
    }

    pub async fn get_stage2_direct(&self, cache_key: &str) -> Result<Option<Stage2Result>, PipelineError> {
        self.repository.get_stage2_cache(cache_key).await
    }

    pub async fn warm_cache_for_batch(&self, vocabulary_items: &[VocabularyItem]) -> Result<CacheWarmupStats, PipelineError> {
        info!("Warming cache for {} vocabulary items", vocabulary_items.len());
        
        let mut stage1_hits = 0;
        let mut stage2_hits = 0;
        let mut total_tokens_saved = 0;

        for item in vocabulary_items {
            let stage1_key = Stage1Result::generate_cache_key(item);
            
            if let Some(stage1_result) = self.repository.get_stage1_cache(&stage1_key).await? {
                stage1_hits += 1;
                
                // Check Stage 2 cache
                let stage2_key = Stage2Result::generate_cache_key(item, &stage1_result.cache_key);
                if self.repository.get_stage2_cache(&stage2_key).await?.is_some() {
                    stage2_hits += 1;
                }
            }
        }

        let stats = CacheWarmupStats {
            total_items: vocabulary_items.len(),
            stage1_cached: stage1_hits,
            stage2_cached: stage2_hits,
            stage1_missing: vocabulary_items.len() - stage1_hits,
            stage2_missing: vocabulary_items.len() - stage2_hits,
            estimated_tokens_saved: total_tokens_saved,
        };

        info!("Cache warmup complete: {} stage1 hits, {} stage2 hits", 
              stage1_hits, stage2_hits);

        Ok(stats)
    }
}

#[derive(Debug, Clone)]
pub struct CacheWarmupStats {
    pub total_items: usize,
    pub stage1_cached: usize,
    pub stage2_cached: usize,
    pub stage1_missing: usize,
    pub stage2_missing: usize,
    pub estimated_tokens_saved: i64,
}

impl CacheWarmupStats {
    pub fn cache_hit_rate(&self) -> f64 {
        if self.total_items == 0 {
            return 0.0;
        }
        
        let total_possible = self.total_items * 2; // Stage 1 + Stage 2
        let total_hits = self.stage1_cached + self.stage2_cached;
        
        (total_hits as f64) / (total_possible as f64)
    }

    pub fn estimated_cost_saved(&self) -> f64 {
        // $0.15 per 1000 tokens
        (self.estimated_tokens_saved as f64) * 0.15 / 1000.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;
    use crate::models::{SemanticAnalysis, FrequencyLevel, FormalityLevel};
    
    async fn setup_test_manager() -> CacheManager {
        let temp_file = NamedTempFile::new().unwrap();
        let db_path = temp_file.path().to_str().unwrap();
        
        let pool = crate::database::create_pool(db_path).await.unwrap();
        crate::database::migrations::run_migrations(&pool).await.unwrap();
        
        CacheManager::new(pool)
    }

    #[tokio::test]
    async fn test_stage1_caching() {
        let manager = setup_test_manager().await;
        
        let vocab_item = VocabularyItem::new(
            "안녕하세요".to_string(),
            "Hello".to_string(),
            "greetings".to_string(),
        );
        
        let compute_count = std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));
        let compute_count_clone = compute_count.clone();
        
        // First call - should compute
        let result1 = manager.get_or_compute_stage1(&vocab_item, || {
            compute_count_clone.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
            async {
                Ok((
                    Stage1Result {
                        vocabulary_id: 1,
                        request_id: "test".to_string(),
                        cache_key: Stage1Result::generate_cache_key(&vocab_item),
                        semantic_analysis: SemanticAnalysis {
                            primary_meaning: "Greeting".to_string(),
                            alternative_meanings: vec![],
                            connotations: vec![],
                            register: "polite".to_string(),
                            usage_contexts: vec!["formal".to_string()],
                            cultural_notes: None,
                            frequency: FrequencyLevel::VeryCommon,
                            formality: FormalityLevel::Formal,
                        },
                        created_at: chrono::Utc::now(),
                    },
                    "hash123".to_string(),
                    100,
                    "claude-3-sonnet".to_string(),
                ))
            }
        }).await.unwrap();
        
        // Second call - should hit cache
        let result2 = manager.get_or_compute_stage1(&vocab_item, || {
            compute_count.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
            async {
                panic!("Should not compute - should hit cache");
            }
        }).await.unwrap();
        
        assert_eq!(compute_count.load(std::sync::atomic::Ordering::SeqCst), 1);
        assert_eq!(result1.cache_key, result2.cache_key);
    }
}