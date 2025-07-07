//! Core domain types and traits for the Korean Flashcard Pipeline
//! 
//! This crate defines the fundamental data structures used throughout
//! the pipeline, including vocabulary items, processing results, and
//! common traits.

pub mod models;
pub mod database;
pub mod cache_manager;
pub mod traits;
pub mod logging;

#[cfg(feature = "pyo3")]
pub mod python_interop;

// Re-export core types
pub use models::*;
pub use cache_manager::CacheManager;
pub use traits::*;

// Re-export database types
pub use database::{DatabasePool, create_pool};

// Re-export logging utilities
pub use logging::{init_logging, init_json_logging, LogContext};

/// Re-export commonly used external types
pub use chrono::{DateTime, Utc};