use flashcard_core::{
    database::{DatabasePool, repositories::*},
    models::{VocabularyItem, Stage1Result, Stage2Result, ProcessingStatus, BatchStats, Comparison},
    errors::PipelineError,
};
use sqlx::sqlite::SqlitePoolOptions;
use tempfile::NamedTempFile;
use chrono::{Utc, Duration};

async fn create_test_pool() -> DatabasePool {
    let temp_file = NamedTempFile::new().unwrap();
    let db_url = format!("sqlite:{}", temp_file.path().display());
    
    let pool = DatabasePool::new(&db_url).await.unwrap();
    pool.run_migrations().await.unwrap();
    
    pool
}

fn create_test_vocabulary_item(position: i32, term: &str) -> VocabularyItem {
    VocabularyItem {
        id: None,
        position,
        term: term.to_string(),
        word_type: Some("noun".to_string()),
        created_at: Utc::now(),
        updated_at: Utc::now(),
    }
}

fn create_test_stage1_result(term_number: i32, term: &str) -> Stage1Result {
    Stage1Result {
        term_number,
        term: term.to_string(),
        ipa: format!("[{}]", term),
        pos: "noun".to_string(),
        primary_meaning: format!("{} meaning", term),
        other_meanings: "other meanings".to_string(),
        metaphor: "like something".to_string(),
        metaphor_noun: "thing".to_string(),
        metaphor_action: "doing".to_string(),
        suggested_location: "place".to_string(),
        anchor_object: "object".to_string(),
        anchor_sensory: "sense".to_string(),
        explanation: "explanation".to_string(),
        usage_context: Some("context".to_string()),
        comparison: Comparison {
            similar_to: vec!["similar".to_string()],
            different_from: vec!["different".to_string()],
            commonly_confused_with: vec![],
        },
        homonyms: vec![],
        korean_keywords: vec!["keyword".to_string()],
    }
}

mod vocabulary_repository_tests {
    use super::*;
    
    #[tokio::test]
    async fn test_create_vocabulary_item() {
        let pool = create_test_pool().await;
        let repo = SqliteVocabularyRepository::new(pool);
        
        let item = create_test_vocabulary_item(1, "테스트");
        let created = repo.create(&item).await.unwrap();
        
        assert!(created.id.is_some());
        assert_eq!(created.term, "테스트");
        assert_eq!(created.position, 1);
    }
    
    #[tokio::test]
    async fn test_get_vocabulary_by_id() {
        let pool = create_test_pool().await;
        let repo = SqliteVocabularyRepository::new(pool);
        
        let item = create_test_vocabulary_item(1, "테스트");
        let created = repo.create(&item).await.unwrap();
        
        let retrieved = repo.get_by_id(created.id.unwrap()).await.unwrap();
        assert!(retrieved.is_some());
        
        let retrieved_item = retrieved.unwrap();
        assert_eq!(retrieved_item.term, "테스트");
    }
    
    #[tokio::test]
    async fn test_update_vocabulary_item() {
        let pool = create_test_pool().await;
        let repo = SqliteVocabularyRepository::new(pool);
        
        let item = create_test_vocabulary_item(1, "테스트");
        let mut created = repo.create(&item).await.unwrap();
        
        created.term = "수정된테스트".to_string();
        let updated = repo.update(&created).await.unwrap();
        
        assert_eq!(updated.term, "수정된테스트");
        assert!(updated.updated_at > created.updated_at);
    }
    
    #[tokio::test]
    async fn test_delete_vocabulary_item() {
        let pool = create_test_pool().await;
        let repo = SqliteVocabularyRepository::new(pool);
        
        let item = create_test_vocabulary_item(1, "테스트");
        let created = repo.create(&item).await.unwrap();
        
        repo.delete(created.id.unwrap()).await.unwrap();
        
        let retrieved = repo.get_by_id(created.id.unwrap()).await.unwrap();
        assert!(retrieved.is_none());
    }
    
    #[tokio::test]
    async fn test_list_vocabulary_items() {
        let pool = create_test_pool().await;
        let repo = SqliteVocabularyRepository::new(pool);
        
        // Create multiple items
        for i in 1..=5 {
            let item = create_test_vocabulary_item(i, &format!("테스트{}", i));
            repo.create(&item).await.unwrap();
        }
        
        let items = repo.list(10, 0).await.unwrap();
        assert_eq!(items.len(), 5);
        
        // Test pagination
        let page2 = repo.list(2, 2).await.unwrap();
        assert_eq!(page2.len(), 2);
        assert_eq!(page2[0].position, 3);
    }
    
    #[tokio::test]
    async fn test_find_by_term() {
        let pool = create_test_pool().await;
        let repo = SqliteVocabularyRepository::new(pool);
        
        let item = create_test_vocabulary_item(1, "unique_term");
        repo.create(&item).await.unwrap();
        
        let found = repo.find_by_term("unique_term").await.unwrap();
        assert!(found.is_some());
        assert_eq!(found.unwrap().term, "unique_term");
        
        let not_found = repo.find_by_term("nonexistent").await.unwrap();
        assert!(not_found.is_none());
    }
}

mod cache_repository_tests {
    use super::*;
    
    #[tokio::test]
    async fn test_stage1_cache_operations() {
        let pool = create_test_pool().await;
        let repo = SqliteCacheRepository::new(pool);
        
        let cache_key = "test_key_stage1";
        let result = create_test_stage1_result(1, "테스트");
        
        // Test set
        repo.set_stage1_cache(cache_key, &result).await.unwrap();
        
        // Test get
        let retrieved = repo.get_stage1_cache(cache_key).await.unwrap();
        assert!(retrieved.is_some());
        
        let cached_result = retrieved.unwrap();
        assert_eq!(cached_result.term, "테스트");
        assert_eq!(cached_result.primary_meaning, "테스트 meaning");
    }
    
    #[tokio::test]
    async fn test_stage2_cache_operations() {
        let pool = create_test_pool().await;
        let repo = SqliteCacheRepository::new(pool);
        
        let cache_key = "test_key_stage2";
        let result = Stage2Result {
            front: flashcard_core::models::FlashcardContent {
                primary_field: "Front".to_string(),
                secondary_field: Some("Secondary".to_string()),
                tertiary_field: None,
                example_sentence: Some("Example".to_string()),
                pronunciation_guide: Some("[pronunciation]".to_string()),
                image_prompt: None,
                mnemonic_aid: Some("Memory aid".to_string()),
                grammar_notes: None,
                cultural_notes: None,
                usage_notes: None,
                difficulty_level: flashcard_core::models::DifficultyLevel::Beginner,
                frequency_level: flashcard_core::models::FrequencyLevel::Common,
                thematic_tags: vec!["theme".to_string()],
                grammatical_tags: vec!["noun".to_string()],
                style_register: None,
            },
            back: flashcard_core::models::FlashcardContent {
                primary_field: "Back".to_string(),
                secondary_field: None,
                tertiary_field: None,
                example_sentence: None,
                pronunciation_guide: None,
                image_prompt: None,
                mnemonic_aid: None,
                grammar_notes: None,
                cultural_notes: None,
                usage_notes: None,
                difficulty_level: flashcard_core::models::DifficultyLevel::Beginner,
                frequency_level: flashcard_core::models::FrequencyLevel::Common,
                thematic_tags: vec![],
                grammatical_tags: vec![],
                style_register: None,
            },
            card_type: flashcard_core::models::CardType::Standard,
            learning_order: Some(1),
            related_cards: vec![],
        };
        
        // Test set
        repo.set_stage2_cache(cache_key, &result).await.unwrap();
        
        // Test get
        let retrieved = repo.get_stage2_cache(cache_key).await.unwrap();
        assert!(retrieved.is_some());
        
        let cached_result = retrieved.unwrap();
        assert_eq!(cached_result.front.primary_field, "Front");
        assert_eq!(cached_result.back.primary_field, "Back");
    }
    
    #[tokio::test]
    async fn test_cache_stats() {
        let pool = create_test_pool().await;
        let repo = SqliteCacheRepository::new(pool);
        
        // Add some cache entries
        for i in 1..=3 {
            let key = format!("stage1_key_{}", i);
            let result = create_test_stage1_result(i, &format!("term{}", i));
            repo.set_stage1_cache(&key, &result).await.unwrap();
        }
        
        for i in 1..=2 {
            let key = format!("stage2_key_{}", i);
            let result = Stage2Result {
                front: flashcard_core::models::FlashcardContent {
                    primary_field: format!("Front{}", i),
                    secondary_field: None,
                    tertiary_field: None,
                    example_sentence: None,
                    pronunciation_guide: None,
                    image_prompt: None,
                    mnemonic_aid: None,
                    grammar_notes: None,
                    cultural_notes: None,
                    usage_notes: None,
                    difficulty_level: flashcard_core::models::DifficultyLevel::Beginner,
                    frequency_level: flashcard_core::models::FrequencyLevel::Common,
                    thematic_tags: vec![],
                    grammatical_tags: vec![],
                    style_register: None,
                },
                back: flashcard_core::models::FlashcardContent {
                    primary_field: format!("Back{}", i),
                    secondary_field: None,
                    tertiary_field: None,
                    example_sentence: None,
                    pronunciation_guide: None,
                    image_prompt: None,
                    mnemonic_aid: None,
                    grammar_notes: None,
                    cultural_notes: None,
                    usage_notes: None,
                    difficulty_level: flashcard_core::models::DifficultyLevel::Beginner,
                    frequency_level: flashcard_core::models::FrequencyLevel::Common,
                    thematic_tags: vec![],
                    grammatical_tags: vec![],
                    style_register: None,
                },
                card_type: flashcard_core::models::CardType::Standard,
                learning_order: Some(i),
                related_cards: vec![],
            };
            repo.set_stage2_cache(&key, &result).await.unwrap();
        }
        
        let stats = repo.get_cache_stats().await.unwrap();
        assert_eq!(stats.total_entries, 5);
        assert_eq!(stats.stage1_entries, 3);
        assert_eq!(stats.stage2_entries, 2);
        assert!(stats.total_size_bytes > 0);
    }
    
    #[tokio::test]
    async fn test_clear_cache() {
        let pool = create_test_pool().await;
        let repo = SqliteCacheRepository::new(pool);
        
        // Add cache entries
        repo.set_stage1_cache("key1", &create_test_stage1_result(1, "test")).await.unwrap();
        repo.set_stage1_cache("key2", &create_test_stage1_result(2, "test2")).await.unwrap();
        
        // Clear cache
        let cleared = repo.clear_cache().await.unwrap();
        assert_eq!(cleared, 2);
        
        // Verify cache is empty
        let stats = repo.get_cache_stats().await.unwrap();
        assert_eq!(stats.total_entries, 0);
    }
    
    #[tokio::test]
    async fn test_cache_expiry() {
        let pool = create_test_pool().await;
        let repo = SqliteCacheRepository::new(pool);
        
        // Note: Since our cache is permanent (no TTL), this tests that entries don't expire
        let cache_key = "permanent_key";
        let result = create_test_stage1_result(1, "permanent");
        
        repo.set_stage1_cache(cache_key, &result).await.unwrap();
        
        // Even after "time passing", entry should still exist
        let retrieved = repo.get_stage1_cache(cache_key).await.unwrap();
        assert!(retrieved.is_some());
    }
}

mod queue_repository_tests {
    use super::*;
    
    #[tokio::test]
    async fn test_create_batch() {
        let pool = create_test_pool().await;
        let repo = SqliteQueueRepository::new(pool);
        
        let batch_id = repo.create_batch(10).await.unwrap();
        assert!(batch_id > 0);
        
        let count = repo.get_batch_count().await.unwrap();
        assert_eq!(count, 1);
    }
    
    #[tokio::test]
    async fn test_add_items_to_batch() {
        let pool = create_test_pool().await;
        let vocab_repo = SqliteVocabularyRepository::new(pool.clone());
        let queue_repo = SqliteQueueRepository::new(pool);
        
        // Create vocabulary items
        let item1 = vocab_repo.create(&create_test_vocabulary_item(1, "test1")).await.unwrap();
        let item2 = vocab_repo.create(&create_test_vocabulary_item(2, "test2")).await.unwrap();
        
        // Create batch and add items
        let batch_id = queue_repo.create_batch(2).await.unwrap();
        queue_repo.add_item_to_batch(batch_id, &item1).await.unwrap();
        queue_repo.add_item_to_batch(batch_id, &item2).await.unwrap();
        
        // Get batch status
        let status = queue_repo.get_batch_status(batch_id).await.unwrap();
        assert_eq!(status.total_items, 2);
        assert_eq!(status.completed_items, 0);
    }
    
    #[tokio::test]
    async fn test_update_item_status() {
        let pool = create_test_pool().await;
        let vocab_repo = SqliteVocabularyRepository::new(pool.clone());
        let queue_repo = SqliteQueueRepository::new(pool);
        
        let item = vocab_repo.create(&create_test_vocabulary_item(1, "test")).await.unwrap();
        let batch_id = queue_repo.create_batch(1).await.unwrap();
        queue_repo.add_item_to_batch(batch_id, &item).await.unwrap();
        
        // Update to processing
        queue_repo.update_item_status(
            batch_id,
            item.position,
            ProcessingStatus::Processing { stage: 1 }
        ).await.unwrap();
        
        // Update to completed
        queue_repo.update_item_status(
            batch_id,
            item.position,
            ProcessingStatus::Completed
        ).await.unwrap();
        
        let status = queue_repo.get_batch_status(batch_id).await.unwrap();
        assert_eq!(status.completed_items, 1);
    }
    
    #[tokio::test]
    async fn test_get_incomplete_items() {
        let pool = create_test_pool().await;
        let vocab_repo = SqliteVocabularyRepository::new(pool.clone());
        let queue_repo = SqliteQueueRepository::new(pool);
        
        // Create items
        let item1 = vocab_repo.create(&create_test_vocabulary_item(1, "complete")).await.unwrap();
        let item2 = vocab_repo.create(&create_test_vocabulary_item(2, "incomplete")).await.unwrap();
        let item3 = vocab_repo.create(&create_test_vocabulary_item(3, "failed")).await.unwrap();
        
        let batch_id = queue_repo.create_batch(3).await.unwrap();
        queue_repo.add_item_to_batch(batch_id, &item1).await.unwrap();
        queue_repo.add_item_to_batch(batch_id, &item2).await.unwrap();
        queue_repo.add_item_to_batch(batch_id, &item3).await.unwrap();
        
        // Mark one as completed
        queue_repo.update_item_status(
            batch_id,
            item1.position,
            ProcessingStatus::Completed
        ).await.unwrap();
        
        // Mark one as failed
        queue_repo.update_item_status(
            batch_id,
            item3.position,
            ProcessingStatus::Failed {
                error: "Test error".to_string(),
                retry_count: 1,
            }
        ).await.unwrap();
        
        let incomplete = queue_repo.get_incomplete_items(batch_id).await.unwrap();
        assert_eq!(incomplete.len(), 2); // incomplete and failed items
        assert!(incomplete.iter().any(|i| i.term == "incomplete"));
        assert!(incomplete.iter().any(|i| i.term == "failed"));
    }
    
    #[tokio::test]
    async fn test_checkpoint_operations() {
        let pool = create_test_pool().await;
        let queue_repo = SqliteQueueRepository::new(pool);
        
        let batch_id = queue_repo.create_batch(5).await.unwrap();
        
        // Create checkpoint
        queue_repo.create_checkpoint(batch_id).await.unwrap();
        
        // Update checkpoint
        queue_repo.update_checkpoint(batch_id, 3).await.unwrap();
        
        // Get checkpoint
        let checkpoint = queue_repo.get_checkpoint(batch_id).await.unwrap();
        assert_eq!(checkpoint, Some(3));
    }
    
    #[tokio::test]
    async fn test_list_batches() {
        let pool = create_test_pool().await;
        let queue_repo = SqliteQueueRepository::new(pool);
        
        // Create multiple batches
        for i in 1..=5 {
            queue_repo.create_batch(i * 10).await.unwrap();
        }
        
        let batches = queue_repo.list_batches(10, 0).await.unwrap();
        assert_eq!(batches.len(), 5);
        
        // Test pagination
        let page2 = queue_repo.list_batches(2, 2).await.unwrap();
        assert_eq!(page2.len(), 2);
    }
    
    #[tokio::test]
    async fn test_failed_items_tracking() {
        let pool = create_test_pool().await;
        let vocab_repo = SqliteVocabularyRepository::new(pool.clone());
        let queue_repo = SqliteQueueRepository::new(pool);
        
        let item = vocab_repo.create(&create_test_vocabulary_item(1, "test")).await.unwrap();
        let batch_id = queue_repo.create_batch(1).await.unwrap();
        queue_repo.add_item_to_batch(batch_id, &item).await.unwrap();
        
        // Fail with retry count
        for retry_count in 1..=3 {
            queue_repo.update_item_status(
                batch_id,
                item.position,
                ProcessingStatus::Failed {
                    error: format!("Attempt {} failed", retry_count),
                    retry_count: retry_count as u8,
                }
            ).await.unwrap();
        }
        
        let status = queue_repo.get_batch_status(batch_id).await.unwrap();
        assert_eq!(status.failed_items, 1);
    }
}

mod transaction_tests {
    use super::*;
    
    #[tokio::test]
    async fn test_transaction_rollback() {
        let pool = create_test_pool().await;
        let vocab_repo = SqliteVocabularyRepository::new(pool.clone());
        
        // Start a transaction that will fail
        let result: Result<(), PipelineError> = sqlx::query("BEGIN")
            .execute(&pool.pool)
            .await
            .map_err(|e| PipelineError::DatabaseError(e.to_string()))
            .and_then(|_| async {
                // Create an item
                let item = create_test_vocabulary_item(1, "rollback_test");
                vocab_repo.create(&item).await?;
                
                // Force an error
                Err(PipelineError::DatabaseError("Forced error".to_string()))
            }.await)
            .and_then(|_| async {
                sqlx::query("COMMIT")
                    .execute(&pool.pool)
                    .await
                    .map_err(|e| PipelineError::DatabaseError(e.to_string()))?;
                Ok(())
            }.await);
        
        // Transaction should have rolled back
        assert!(result.is_err());
        
        // Verify item was not created
        let items = vocab_repo.list(10, 0).await.unwrap();
        assert_eq!(items.len(), 0);
    }
    
    #[tokio::test]
    async fn test_concurrent_access() {
        let pool = create_test_pool().await;
        let repo = SqliteVocabularyRepository::new(pool);
        
        // Spawn multiple concurrent operations
        let mut handles = vec![];
        
        for i in 0..10 {
            let repo_clone = repo.clone();
            let handle = tokio::spawn(async move {
                let item = create_test_vocabulary_item(i, &format!("concurrent_{}", i));
                repo_clone.create(&item).await
            });
            handles.push(handle);
        }
        
        // Wait for all to complete
        let results: Vec<_> = futures::future::join_all(handles).await;
        
        // All should succeed
        for result in results {
            assert!(result.is_ok());
            assert!(result.unwrap().is_ok());
        }
        
        // Verify all items were created
        let items = repo.list(20, 0).await.unwrap();
        assert_eq!(items.len(), 10);
    }
}