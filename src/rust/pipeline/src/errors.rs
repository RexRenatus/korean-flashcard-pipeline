use thiserror::Error;
use std::path::PathBuf;

pub type Result<T> = std::result::Result<T, PipelineError>;

#[derive(Error, Debug)]
pub enum PipelineError {
    #[error("Core error: {0}")]
    Core(#[from] flashcard_core::errors::PipelineError),
    
    #[error("Python integration error: {0}")]
    PythonError(String),
    
    #[error("CSV parsing error: {0}")]
    CsvError(#[from] csv::Error),
    
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
    
    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),
    
    #[error("Export error: {0}")]
    ExportError(String),
    
    #[error("Batch processing error at position {position}: {message}")]
    BatchError { position: i32, message: String },
    
    #[error("Configuration error: {0}")]
    ConfigError(String),
    
    #[error("File not found: {0}")]
    FileNotFound(PathBuf),
    
    #[error("Invalid input format: {0}")]
    InvalidFormat(String),
    
    #[error("Pipeline interrupted by user")]
    Interrupted,
    
    #[error("Health check failed: {0}")]
    HealthCheckFailed(String),
    
    #[error("Rate limit exceeded, retry after {0} seconds")]
    RateLimitExceeded(u64),
    
    #[error("API error: {0}")]
    ApiError(String),
    
    #[error("Cache error: {0}")]
    CacheError(String),
}

impl PipelineError {
    pub fn is_retryable(&self) -> bool {
        matches!(
            self,
            PipelineError::RateLimitExceeded(_) 
            | PipelineError::ApiError(_)
            | PipelineError::IoError(_)
        )
    }
    
    pub fn exit_code(&self) -> i32 {
        match self {
            PipelineError::Interrupted => 130, // Standard SIGINT exit code
            PipelineError::FileNotFound(_) => 2,
            PipelineError::InvalidFormat(_) => 3,
            PipelineError::ConfigError(_) => 4,
            PipelineError::HealthCheckFailed(_) => 5,
            _ => 1,
        }
    }
}

#[cfg(feature = "python")]
impl From<pyo3::PyErr> for PipelineError {
    fn from(err: pyo3::PyErr) -> Self {
        PipelineError::PythonError(err.to_string())
    }
}