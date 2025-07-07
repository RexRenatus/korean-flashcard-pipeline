//! Core domain types and traits for the Korean Flashcard Pipeline
//! 
//! This crate defines the fundamental data structures used throughout
//! the pipeline, including vocabulary items, processing results, and
//! common traits.

pub mod types;
pub mod errors;
pub mod traits;
pub mod models;
pub mod database;
pub mod cache_manager;

#[cfg(feature = "pyo3")]
pub mod python_interop;

pub use cache_manager::CacheManager;

pub use errors::{CoreError, Result};
pub use types::{
    VocabularyItem,
    Stage1Result,
    Stage2Result,
    Comparison,
    Homonym,
    ProcessingStatus,
    QueueState,
};
pub use traits::{
    Cacheable,
    Processable,
    Validatable,
};

/// Re-export commonly used external types
pub use chrono::{DateTime, Utc};
pub use uuid::Uuid;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_module_exports() {
        // Ensure all public APIs are accessible
        let _ = VocabularyItem::default();
        let _ = CoreError::ValidationError("test".to_string());
    }
}