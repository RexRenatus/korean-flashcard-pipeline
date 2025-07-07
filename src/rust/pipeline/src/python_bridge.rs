#[cfg(feature = "python")]
use pyo3::prelude::*;
#[cfg(feature = "python")]
use pyo3_asyncio::tokio::future_into_py;
use async_trait::async_trait;
use flashcard_core::models::{VocabularyItem, Stage1Result, Stage2Result, FlashcardContent};
use crate::errors::{PipelineError, Result};
use std::path::Path;
use parking_lot::RwLock;
use std::sync::Arc;
use tracing::{info, debug, error, instrument};

#[async_trait]
pub trait ApiClient: Send + Sync {
    async fn process_stage1(&self, item: &VocabularyItem) -> Result<Stage1Result>;
    async fn process_stage2(&self, item: &VocabularyItem, stage1: &Stage1Result) -> Result<Stage2Result>;
    async fn health_check(&self) -> Result<()>;
}

#[cfg(feature = "python")]
pub struct PythonBridge {
    initialized: Arc<RwLock<bool>>,
}

#[cfg(feature = "python")]
impl PythonBridge {
    pub fn new() -> Result<Self> {
        Ok(Self {
            initialized: Arc::new(RwLock::new(false)),
        })
    }
    
    fn ensure_initialized(&self) -> Result<()> {
        let mut initialized = self.initialized.write();
        if !*initialized {
            pyo3::prepare_freethreaded_python();
            Python::with_gil(|py| {
                // Add Python module path
                let sys = py.import("sys")?;
                let path = sys.getattr("path")?;
                
                // Get the absolute path to the Python source
                let python_path = std::env::current_dir()?
                    .join("src")
                    .join("python");
                    
                path.call_method1("insert", (0, python_path.to_str().unwrap()))?;
                
                // Import and verify the module
                py.import("flashcard_pipeline")?;
                
                Ok::<(), PipelineError>(())
            })?;
            *initialized = true;
            info!("Python bridge initialized successfully");
        }
        Ok(())
    }
    
    async fn call_python_async<F, R>(&self, func: F) -> Result<R>
    where
        F: FnOnce(Python) -> PyResult<R> + Send + 'static,
        R: Send + 'static,
    {
        self.ensure_initialized()?;
        
        tokio::task::spawn_blocking(move || {
            Python::with_gil(|py| func(py).map_err(PipelineError::from))
        })
        .await
        .map_err(|e| PipelineError::PythonError(format!("Task join error: {}", e)))?
    }
}

#[cfg(feature = "python")]
#[async_trait]
impl ApiClient for PythonBridge {
    #[instrument(skip(self, item), fields(term = %item.term))]
    async fn process_stage1(&self, item: &VocabularyItem) -> Result<Stage1Result> {
        debug!("Processing stage 1 for term: {}", item.term);
        
        let item_clone = item.clone();
        self.call_python_async(move |py| {
            let module = py.import("flashcard_pipeline.api_client")?;
            let orchestrator_class = module.getattr("PipelineOrchestrator")?;
            
            // Create orchestrator instance
            let kwargs = pyo3::types::PyDict::new(py);
            kwargs.set_item("cache_dir", ".cache")?;
            let orchestrator = orchestrator_class.call((), Some(kwargs))?;
            
            // Create VocabularyItem dict
            let item_dict = pyo3::types::PyDict::new(py);
            item_dict.set_item("position", item_clone.position)?;
            item_dict.set_item("term", &item_clone.term)?;
            if let Some(ref word_type) = item_clone.word_type {
                item_dict.set_item("type", word_type)?;
            }
            
            // Call process_stage1
            let asyncio = py.import("asyncio")?;
            let coro = orchestrator.call_method1("process_stage1", (item_dict,))?;
            let result = asyncio.call_method1("run", (coro,))?;
            
            // Extract the stage1_result from tuple (stage1_result, usage)
            let stage1_result = result.get_item(0)?;
            
            // Convert to JSON string for deserialization
            let json_module = py.import("json")?;
            let json_str: String = json_module
                .call_method1("dumps", (stage1_result.call_method0("dict")?,))?
                .extract()?;
            
            serde_json::from_str(&json_str).map_err(PyErr::from)
        }).await
    }
    
    #[instrument(skip(self, item, stage1), fields(term = %item.term))]
    async fn process_stage2(&self, item: &VocabularyItem, stage1: &Stage1Result) -> Result<Stage2Result> {
        debug!("Processing stage 2 for term: {}", item.term);
        
        let item_clone = item.clone();
        let stage1_clone = stage1.clone();
        
        self.call_python_async(move |py| {
            let module = py.import("flashcard_pipeline.api_client")?;
            let orchestrator_class = module.getattr("PipelineOrchestrator")?;
            
            // Create orchestrator instance
            let kwargs = pyo3::types::PyDict::new(py);
            kwargs.set_item("cache_dir", ".cache")?;
            let orchestrator = orchestrator_class.call((), Some(kwargs))?;
            
            // Create VocabularyItem dict
            let item_dict = pyo3::types::PyDict::new(py);
            item_dict.set_item("position", item_clone.position)?;
            item_dict.set_item("term", &item_clone.term)?;
            if let Some(ref word_type) = item_clone.word_type {
                item_dict.set_item("type", word_type)?;
            }
            
            // Convert Stage1Result to dict
            let stage1_json = serde_json::to_string(&stage1_clone).map_err(PyErr::from)?;
            let json_module = py.import("json")?;
            let stage1_dict = json_module.call_method1("loads", (stage1_json,))?;
            
            // Create Stage1Response object from dict
            let models = py.import("flashcard_pipeline.models")?;
            let stage1_response_class = models.getattr("Stage1Response")?;
            let stage1_response = stage1_response_class.call_method1("parse_obj", (stage1_dict,))?;
            
            // Call process_stage2
            let asyncio = py.import("asyncio")?;
            let coro = orchestrator.call_method1("process_stage2", (item_dict, stage1_response))?;
            let result = asyncio.call_method1("run", (coro,))?;
            
            // Extract the stage2_result from tuple (stage2_result, usage)
            let stage2_result = result.get_item(0)?;
            
            // Convert to JSON string for deserialization
            let json_str: String = json_module
                .call_method1("dumps", (stage2_result.call_method0("dict")?,))?
                .extract()?;
            
            serde_json::from_str(&json_str).map_err(PyErr::from)
        }).await
    }
    
    async fn health_check(&self) -> Result<()> {
        self.call_python_async(|py| {
            let module = py.import("flashcard_pipeline.api_client")?;
            let client_class = module.getattr("OpenRouterClient")?;
            let client = client_class.call0()?;
            
            // Test that we can create a client instance
            let asyncio = py.import("asyncio")?;
            let coro = client.call_method0("test_connection")?;
            asyncio.call_method1("run", (coro,))?;
            
            Ok(())
        }).await
    }
}

// Mock implementation for testing without Python
#[cfg(not(feature = "python"))]
pub struct MockApiClient;

#[cfg(not(feature = "python"))]
#[async_trait]
impl ApiClient for MockApiClient {
    async fn process_stage1(&self, item: &VocabularyItem) -> Result<Stage1Result> {
        Ok(Stage1Result {
            term_number: item.position,
            term: item.term.clone(),
            ipa: "[mock-ipa]".to_string(),
            pos: "noun".to_string(),
            primary_meaning: "Mock primary meaning".to_string(),
            other_meanings: "Mock other meanings".to_string(),
            metaphor: "Mock metaphor".to_string(),
            metaphor_noun: "Mock noun".to_string(),
            metaphor_action: "Mock action".to_string(),
            suggested_location: "Mock location".to_string(),
            anchor_object: "Mock object".to_string(),
            anchor_sensory: "Mock sensory".to_string(),
            explanation: "Mock explanation".to_string(),
            usage_context: Some("Mock context".to_string()),
            comparison: flashcard_core::models::Comparison {
                similar_to: vec![],
                different_from: vec![],
                commonly_confused_with: vec![],
            },
            homonyms: vec![],
            korean_keywords: vec!["mock".to_string()],
        })
    }
    
    async fn process_stage2(&self, _item: &VocabularyItem, _stage1: &Stage1Result) -> Result<Stage2Result> {
        Ok(Stage2Result {
            front: FlashcardContent {
                primary_field: "Mock front".to_string(),
                secondary_field: Some("Mock secondary".to_string()),
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
            back: FlashcardContent {
                primary_field: "Mock back".to_string(),
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
        })
    }
    
    async fn health_check(&self) -> Result<()> {
        Ok(())
    }
}

pub fn create_api_client() -> Result<Box<dyn ApiClient>> {
    #[cfg(feature = "python")]
    {
        Ok(Box::new(PythonBridge::new()?))
    }
    
    #[cfg(not(feature = "python"))]
    {
        info!("Using mock API client (Python feature disabled)");
        Ok(Box::new(MockApiClient))
    }
}