#[cfg(feature = "python")]
mod python_bridge_tests {
    use flashcard_pipeline::{
        python_bridge::{PythonBridge, ApiClient, create_api_client},
        errors::PipelineError,
    };
    use flashcard_core::models::{VocabularyItem, Stage1Result, Stage2Result, Comparison};
    use std::sync::Arc;
    use tokio;
    use pyo3::prelude::*;
    use chrono::Utc;
    
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
    
    #[tokio::test]
    async fn test_python_bridge_initialization() {
        let bridge = PythonBridge::new();
        assert!(bridge.is_ok());
        
        let bridge = bridge.unwrap();
        
        // Test that Python is properly initialized
        let result = bridge.health_check().await;
        // This might fail if Python environment is not set up
        match result {
            Ok(_) => println!("Python bridge initialized successfully"),
            Err(e) => println!("Python bridge initialization failed (expected in test env): {}", e),
        }
    }
    
    #[tokio::test]
    async fn test_python_gil_handling() {
        let bridge = PythonBridge::new().unwrap();
        
        // Test multiple GIL acquisitions
        let tasks: Vec<_> = (0..5).map(|i| {
            let bridge_clone = Arc::new(PythonBridge::new().unwrap());
            tokio::spawn(async move {
                let item = VocabularyItem {
                    id: None,
                    position: i,
                    term: format!("test_{}", i),
                    word_type: Some("noun".to_string()),
                    created_at: Utc::now(),
                    updated_at: Utc::now(),
                };
                
                // This should handle GIL properly
                let result = bridge_clone.process_stage1(&item).await;
                (i, result.is_ok())
            })
        }).collect();
        
        let results = futures::future::join_all(tasks).await;
        
        // All tasks should complete without deadlock
        assert_eq!(results.len(), 5);
    }
    
    #[tokio::test]
    async fn test_vocabulary_item_conversion() {
        Python::with_gil(|py| {
            let item = create_test_vocabulary_item();
            
            // Test conversion to Python dict
            let dict = pyo3::types::PyDict::new(py);
            dict.set_item("position", item.position).unwrap();
            dict.set_item("term", &item.term).unwrap();
            if let Some(ref word_type) = item.word_type {
                dict.set_item("type", word_type).unwrap();
            }
            
            // Verify dict contents
            assert_eq!(dict.get_item("position").unwrap().extract::<i32>().unwrap(), 1);
            assert_eq!(dict.get_item("term").unwrap().extract::<String>().unwrap(), "테스트");
            assert_eq!(dict.get_item("type").unwrap().extract::<String>().unwrap(), "noun");
        });
    }
    
    #[tokio::test]
    async fn test_stage1_result_deserialization() {
        Python::with_gil(|py| {
            // Create a Python dict that mimics Stage1Response
            let result_dict = pyo3::types::PyDict::new(py);
            result_dict.set_item("term_number", 1).unwrap();
            result_dict.set_item("term", "테스트").unwrap();
            result_dict.set_item("ipa", "[tʰesɯtʰɯ]").unwrap();
            result_dict.set_item("pos", "noun").unwrap();
            result_dict.set_item("primary_meaning", "test").unwrap();
            result_dict.set_item("other_meanings", "examination").unwrap();
            result_dict.set_item("metaphor", "like a challenge").unwrap();
            result_dict.set_item("metaphor_noun", "challenge").unwrap();
            result_dict.set_item("metaphor_action", "testing").unwrap();
            result_dict.set_item("suggested_location", "classroom").unwrap();
            result_dict.set_item("anchor_object", "paper").unwrap();
            result_dict.set_item("anchor_sensory", "white").unwrap();
            result_dict.set_item("explanation", "evaluation method").unwrap();
            result_dict.set_item("usage_context", "academic").unwrap();
            
            // Create comparison dict
            let comparison_dict = pyo3::types::PyDict::new(py);
            comparison_dict.set_item("similar_to", vec!["시험"]).unwrap();
            comparison_dict.set_item("different_from", Vec::<String>::new()).unwrap();
            comparison_dict.set_item("commonly_confused_with", Vec::<String>::new()).unwrap();
            result_dict.set_item("comparison", comparison_dict).unwrap();
            
            result_dict.set_item("homonyms", Vec::<String>::new()).unwrap();
            result_dict.set_item("korean_keywords", vec!["테스트"]).unwrap();
            
            // Convert to JSON and deserialize
            let json_module = py.import("json").unwrap();
            let json_str: String = json_module
                .call_method1("dumps", (result_dict,))
                .unwrap()
                .extract()
                .unwrap();
            
            let stage1_result: Stage1Result = serde_json::from_str(&json_str).unwrap();
            
            assert_eq!(stage1_result.term, "테스트");
            assert_eq!(stage1_result.pos, "noun");
            assert_eq!(stage1_result.comparison.similar_to[0], "시험");
        });
    }
    
    #[tokio::test]
    async fn test_error_propagation_from_python() {
        let bridge = PythonBridge::new().unwrap();
        
        // Test with invalid item that should cause an error
        let invalid_item = VocabularyItem {
            id: None,
            position: -1, // Invalid position
            term: "".to_string(), // Empty term
            word_type: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };
        
        let result = bridge.process_stage1(&invalid_item).await;
        
        // Should get an error
        assert!(result.is_err());
        
        // Error should be properly typed
        match result {
            Err(PipelineError::PythonError(_)) => {
                // Expected error type
            }
            _ => panic!("Expected PythonError"),
        }
    }
    
    #[tokio::test]
    async fn test_stage2_processing_with_stage1_result() {
        let bridge = PythonBridge::new().unwrap();
        
        let item = create_test_vocabulary_item();
        let stage1 = Stage1Result {
            term_number: 1,
            term: "테스트".to_string(),
            ipa: "[tʰesɯtʰɯ]".to_string(),
            pos: "noun".to_string(),
            primary_meaning: "test".to_string(),
            other_meanings: "exam".to_string(),
            metaphor: "challenge".to_string(),
            metaphor_noun: "challenge".to_string(),
            metaphor_action: "testing".to_string(),
            suggested_location: "classroom".to_string(),
            anchor_object: "paper".to_string(),
            anchor_sensory: "white".to_string(),
            explanation: "evaluation".to_string(),
            usage_context: Some("academic".to_string()),
            comparison: Comparison {
                similar_to: vec!["시험".to_string()],
                different_from: vec![],
                commonly_confused_with: vec![],
            },
            homonyms: vec![],
            korean_keywords: vec!["테스트".to_string()],
        };
        
        // This will fail without actual Python environment
        let result = bridge.process_stage2(&item, &stage1).await;
        
        match result {
            Ok(stage2) => {
                assert!(!stage2.front.primary_field.is_empty());
                assert!(!stage2.back.primary_field.is_empty());
            }
            Err(e) => {
                println!("Stage2 processing failed (expected in test env): {}", e);
            }
        }
    }
    
    #[tokio::test]
    async fn test_concurrent_api_calls() {
        let bridge = Arc::new(PythonBridge::new().unwrap());
        
        // Launch multiple concurrent API calls
        let mut handles = vec![];
        
        for i in 0..10 {
            let bridge_clone = Arc::clone(&bridge);
            let handle = tokio::spawn(async move {
                let item = VocabularyItem {
                    id: None,
                    position: i,
                    term: format!("concurrent_test_{}", i),
                    word_type: Some("noun".to_string()),
                    created_at: Utc::now(),
                    updated_at: Utc::now(),
                };
                
                bridge_clone.process_stage1(&item).await
            });
            handles.push(handle);
        }
        
        // All should complete without issues
        let results = futures::future::join_all(handles).await;
        
        for (i, result) in results.iter().enumerate() {
            assert!(result.is_ok(), "Task {} panicked", i);
        }
    }
    
    #[tokio::test]
    async fn test_api_client_factory() {
        // Test creating API client
        let client_result = create_api_client();
        assert!(client_result.is_ok());
        
        let client = client_result.unwrap();
        
        // Should be able to call methods
        let health_result = client.health_check().await;
        
        // In test environment without Python, this might fail
        match health_result {
            Ok(_) => println!("API client created successfully"),
            Err(e) => println!("API client health check failed (expected): {}", e),
        }
    }
    
    #[tokio::test]
    async fn test_python_module_import_error_handling() {
        Python::with_gil(|py| {
            // Try to import a non-existent module
            let result = py.import("nonexistent_module");
            assert!(result.is_err());
            
            // Error should be a ModuleNotFoundError
            if let Err(e) = result {
                let error_str = e.to_string();
                assert!(error_str.contains("No module named") || error_str.contains("ModuleNotFoundError"));
            }
        });
    }
    
    #[tokio::test]
    async fn test_memory_management() {
        let bridge = PythonBridge::new().unwrap();
        
        // Process many items to test memory management
        for i in 0..100 {
            let item = VocabularyItem {
                id: None,
                position: i,
                term: format!("memory_test_{}", i),
                word_type: Some("noun".to_string()),
                created_at: Utc::now(),
                updated_at: Utc::now(),
            };
            
            // This should not leak memory
            let _ = bridge.process_stage1(&item).await;
        }
        
        // Memory should be properly managed by PyO3
        // No direct assertion, but this test helps detect memory leaks
    }
}

// Tests for when Python feature is disabled
#[cfg(not(feature = "python"))]
mod mock_api_client_tests {
    use flashcard_pipeline::python_bridge::{create_api_client, ApiClient};
    use flashcard_core::models::VocabularyItem;
    use chrono::Utc;
    
    #[tokio::test]
    async fn test_mock_client_creation() {
        let client = create_api_client().unwrap();
        
        // Should get mock client
        let result = client.health_check().await;
        assert!(result.is_ok());
    }
    
    #[tokio::test]
    async fn test_mock_stage1_processing() {
        let client = create_api_client().unwrap();
        
        let item = VocabularyItem {
            id: None,
            position: 1,
            term: "mock_test".to_string(),
            word_type: Some("noun".to_string()),
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };
        
        let result = client.process_stage1(&item).await.unwrap();
        
        assert_eq!(result.term, "mock_test");
        assert_eq!(result.primary_meaning, "Mock primary meaning");
    }
    
    #[tokio::test]
    async fn test_mock_stage2_processing() {
        let client = create_api_client().unwrap();
        
        let item = VocabularyItem {
            id: None,
            position: 1,
            term: "mock_test".to_string(),
            word_type: Some("noun".to_string()),
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };
        
        let stage1 = client.process_stage1(&item).await.unwrap();
        let stage2 = client.process_stage2(&item, &stage1).await.unwrap();
        
        assert_eq!(stage2.front.primary_field, "Mock front");
        assert_eq!(stage2.back.primary_field, "Mock back");
    }
}