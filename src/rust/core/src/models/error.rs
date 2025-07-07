use thiserror::Error;

#[derive(Error, Debug)]
pub enum PipelineError {
    #[error("Database error: {0}")]
    Database(#[from] sqlx::Error),
    
    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
    
    #[error("API error: {message}")]
    Api { message: String, status_code: Option<u16> },
    
    #[error("Rate limit exceeded: retry after {retry_after} seconds")]
    RateLimit { retry_after: u64 },
    
    #[error("Cache error: {0}")]
    Cache(String),
    
    #[error("Validation error: {0}")]
    Validation(String),
    
    #[error("Python interop error: {0}")]
    PythonInterop(String),
    
    #[error("Queue error: {0}")]
    Queue(String),
    
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    
    #[error("Configuration error: {0}")]
    Configuration(String),
    
    #[error("Processing timeout after {seconds} seconds")]
    Timeout { seconds: u64 },
    
    #[error("Item quarantined after {attempts} attempts: {reason}")]
    Quarantined { attempts: u32, reason: String },
}

pub type Result<T> = std::result::Result<T, PipelineError>;

#[derive(Debug, Clone, PartialEq)]
pub enum ErrorSeverity {
    Recoverable,
    Retryable,
    Fatal,
}

impl PipelineError {
    pub fn severity(&self) -> ErrorSeverity {
        match self {
            Self::RateLimit { .. } => ErrorSeverity::Retryable,
            Self::Api { status_code, .. } => {
                match status_code {
                    Some(429) | Some(503) | Some(502) => ErrorSeverity::Retryable,
                    Some(400..=499) => ErrorSeverity::Fatal,
                    _ => ErrorSeverity::Retryable,
                }
            }
            Self::Timeout { .. } => ErrorSeverity::Retryable,
            Self::Database(_) => ErrorSeverity::Retryable,
            Self::Io(_) => ErrorSeverity::Retryable,
            Self::Validation(_) => ErrorSeverity::Fatal,
            Self::Configuration(_) => ErrorSeverity::Fatal,
            Self::Quarantined { .. } => ErrorSeverity::Fatal,
            _ => ErrorSeverity::Recoverable,
        }
    }
    
    pub fn is_retryable(&self) -> bool {
        self.severity() == ErrorSeverity::Retryable
    }
}