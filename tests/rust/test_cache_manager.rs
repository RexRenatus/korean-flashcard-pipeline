use flashcard_core::{
    cache_manager::CacheManager,
    models::{VocabularyItem, Stage1Result, Stage2Result, Comparison},
    repositories::CacheRepository,
    errors::PipelineError,
};
use async_trait::async_trait;
use std::sync::Arc;
use parking_lot::RwLock;
use std::collections::HashMap;
use chrono::Utc;

// Mock cache repository for testing
struct MockCacheRepository {
    cache: Arc<RwLock<HashMap<String, Vec<u8>>>>,
    stats: Arc<RwLock<MockStats>>,
}

#[derive(Default)]
struct MockStats {
    stage1_entries: usize,
    stage2_entries: usize,
    total_size: i64,
}

impl MockCacheRepository {
    fn new() -> Self {
        Self {
            cache: Arc::new(RwLock::new(HashMap::new())),
            stats: Arc::new(RwLock::new(MockStats::default())),
        }
    }
}

#[async_trait]
impl CacheRepository for MockCacheRepository {
    async fn get_stage1_cache(&self, cache_key: &str) -> Result<Option<Stage1Result>, PipelineError> {
        let cache = self.cache.read();
        if let Some(data) = cache.get(cache_key) {
            let result: Stage1Result = serde_json::from_slice(data)
                .map_err(|e| PipelineError::SerializationError(e.to_string()))?;
            Ok(Some(result))
        } else {
            Ok(None)
        }
    }
    
    async fn set_stage1_cache(&self, cache_key: &str, result: &Stage1Result) -> Result<(), PipelineError> {
        let data = serde_json::to_vec(result)
            .map_err(|e| PipelineError::SerializationError(e.to_string()))?;
        
        let mut cache = self.cache.write();
        cache.insert(cache_key.to_string(), data);
        
        let mut stats = self.stats.write();
        stats.stage1_entries += 1;
        
        Ok(())
    }
    
    async fn get_stage2_cache(&self, cache_key: &str) -> Result<Option<Stage2Result>, PipelineError> {
        let cache = self.cache.read();
        if let Some(data) = cache.get(cache_key) {
            let result: Stage2Result = serde_json::from_slice(data)
                .map_err(|e| PipelineError::SerializationError(e.to_string()))?;
            Ok(Some(result))
        } else {
            Ok(None)
        }
    }
    
    async fn set_stage2_cache(&self, cache_key: &str, result: &Stage2Result) -> Result<(), PipelineError> {
        let data = serde_json::to_vec(result)
            .map_err(|e| PipelineError::SerializationError(e.to_string()))?;
        
        let mut cache = self.cache.write();
        cache.insert(cache_key.to_string(), data);
        
        let mut stats = self.stats.write();
        stats.stage2_entries += 1;
        
        Ok(())
    }
    
    async fn get_cache_stats(&self) -> Result<flashcard_core::models::CacheStats, PipelineError> {
        let stats = self.stats.read();
        Ok(flashcard_core::models::CacheStats {
            total_entries: stats.stage1_entries + stats.stage2_entries,
            stage1_entries: stats.stage1_entries,
            stage2_entries: stats.stage2_entries,
            total_size_bytes: stats.total_size,
            oldest_entry: None,
            newest_entry: None,
        })
    }
    
    async fn clear_cache(&self) -> Result<usize, PipelineError> {
        let mut cache = self.cache.write();
        let count = cache.len();
        cache.clear();
        
        let mut stats = self.stats.write();
        *stats = MockStats::default();
        
        Ok(count)
    }
}

fn create_test_vocabulary_item() -> VocabularyItem {
    VocabularyItem {
        id: None,
        position: 1,
        term: "테스트".to_string(),
        word_type: Some("noun".to_string()),
        created_at: Utc::now(),
        updated_at: Utc::now(),
    }
}

fn create_test_stage1_result() -> Stage1Result {
    Stage1Result {
        term_number: 1,
        term: "테스트".to_string(),
        ipa: "[tʰesɯtʰɯ]".to_string(),
        pos: "noun".to_string(),
        primary_meaning: "test".to_string(),
        other_meanings: "exam, trial".to_string(),
        metaphor: "like a challenge".to_string(),
        metaphor_noun: "challenge".to_string(),
        metaphor_action: "testing".to_string(),
        suggested_location: "classroom".to_string(),
        anchor_object: "paper".to_string(),
        anchor_sensory: "white".to_string(),
        explanation: "evaluation method".to_string(),
        usage_context: Some("academic".to_string()),
        comparison: Comparison {
            similar_to: vec!["시험".to_string()],
            different_from: vec![],
            commonly_confused_with: vec![],
        },
        homonyms: vec![],
        korean_keywords: vec!["테스트".to_string()],
    }
}

#[tokio::test]
async fn test_cache_manager_stage1_cache_hit() {
    let cache_repo = Arc::new(MockCacheRepository::new());
    let cache_manager = CacheManager::new(
        cache_repo.clone(),
        std::path::PathBuf::from("/tmp/test_cache"),
    );
    
    let item = create_test_vocabulary_item();
    let expected_result = create_test_stage1_result();
    
    // Pre-populate cache
    let cache_key = item.cache_key();
    cache_repo.set_stage1_cache(&cache_key, &expected_result).await.unwrap();
    
    // Test cache hit
    let (result, was_cached) = cache_manager.get_or_compute_stage1(
        &item,
        |_| async { unreachable!("Should not call compute function on cache hit") }
    ).await.unwrap();
    
    assert!(was_cached);
    assert_eq!(result.term, expected_result.term);
}

#[tokio::test]
async fn test_cache_manager_stage1_cache_miss() {
    let cache_repo = Arc::new(MockCacheRepository::new());
    let cache_manager = CacheManager::new(
        cache_repo.clone(),
        std::path::PathBuf::from("/tmp/test_cache"),
    );
    
    let item = create_test_vocabulary_item();
    let expected_result = create_test_stage1_result();
    
    // Test cache miss
    let (result, was_cached) = cache_manager.get_or_compute_stage1(
        &item,
        |_| async { Ok(expected_result.clone()) }
    ).await.unwrap();
    
    assert!(!was_cached);
    assert_eq!(result.term, expected_result.term);
    
    // Verify it was cached
    let cache_key = item.cache_key();
    let cached = cache_repo.get_stage1_cache(&cache_key).await.unwrap();
    assert!(cached.is_some());
}

#[tokio::test]
async fn test_cache_manager_cache_stats() {
    let cache_repo = Arc::new(MockCacheRepository::new());
    let cache_manager = CacheManager::new(
        cache_repo.clone(),
        std::path::PathBuf::from("/tmp/test_cache"),
    );
    
    // Initially empty
    let stats = cache_manager.get_cache_stats().await.unwrap();
    assert_eq!(stats.total_entries, 0);
    
    // Add some cache entries
    let item = create_test_vocabulary_item();
    let stage1_result = create_test_stage1_result();
    
    cache_manager.get_or_compute_stage1(
        &item,
        |_| async { Ok(stage1_result.clone()) }
    ).await.unwrap();
    
    // Check stats updated
    let stats = cache_manager.get_cache_stats().await.unwrap();
    assert_eq!(stats.stage1_entries, 1);
    assert_eq!(stats.total_entries, 1);
}

#[tokio::test]
async fn test_cache_manager_compute_error_handling() {
    let cache_repo = Arc::new(MockCacheRepository::new());
    let cache_manager = CacheManager::new(
        cache_repo,
        std::path::PathBuf::from("/tmp/test_cache"),
    );
    
    let item = create_test_vocabulary_item();
    
    // Test error propagation
    let result = cache_manager.get_or_compute_stage1(
        &item,
        |_| async { Err(PipelineError::ApiError("Test error".to_string())) }
    ).await;
    
    assert!(result.is_err());
    match result {
        Err(PipelineError::ApiError(msg)) => assert_eq!(msg, "Test error"),
        _ => panic!("Wrong error type"),
    }
}

#[tokio::test]
async fn test_cache_manager_warm_cache() {
    let cache_repo = Arc::new(MockCacheRepository::new());
    let cache_manager = CacheManager::new(
        cache_repo.clone(),
        std::path::PathBuf::from("/tmp/test_cache"),
    );
    
    let items = vec![
        VocabularyItem {
            id: None,
            position: 1,
            term: "하나".to_string(),
            word_type: Some("number".to_string()),
            created_at: Utc::now(),
            updated_at: Utc::now(),
        },
        VocabularyItem {
            id: None,
            position: 2,
            term: "둘".to_string(),
            word_type: Some("number".to_string()),
            created_at: Utc::now(),
            updated_at: Utc::now(),
        },
    ];
    
    // Pre-populate one item
    let stage1_result = create_test_stage1_result();
    cache_repo.set_stage1_cache(&items[0].cache_key(), &stage1_result).await.unwrap();
    
    // Warm cache should detect 1 existing, not touch it
    let warmed = cache_manager.warm_cache(&items).await.unwrap();
    assert_eq!(warmed, 1); // Only the one already cached
}