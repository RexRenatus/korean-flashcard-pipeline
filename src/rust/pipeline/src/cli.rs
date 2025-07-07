use clap::{Parser, Subcommand};
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "flashcard-pipeline")]
#[command(about = "Korean Language Flashcard Pipeline", long_about = None)]
#[command(version)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
    
    /// Database URL
    #[arg(long, env = "DATABASE_URL", default_value = "sqlite:pipeline.db")]
    pub database_url: String,
    
    /// Cache directory
    #[arg(long, env = "CACHE_DIR", default_value = ".cache")]
    pub cache_dir: PathBuf,
    
    /// Enable debug logging
    #[arg(long, short = 'd')]
    pub debug: bool,
    
    /// Disable colored output
    #[arg(long)]
    pub no_color: bool,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Process vocabulary from CSV file
    Process {
        /// Input CSV file path
        #[arg(value_name = "INPUT")]
        input: PathBuf,
        
        /// Output TSV file path
        #[arg(short, long, default_value = "output.tsv")]
        output: PathBuf,
        
        /// Maximum concurrent API requests
        #[arg(long, default_value_t = 5)]
        max_concurrent: usize,
        
        /// Batch size for processing
        #[arg(long, default_value_t = 10)]
        batch_size: usize,
        
        /// Resume from a specific batch ID
        #[arg(long)]
        resume: Option<i32>,
        
        /// Skip export (useful for testing)
        #[arg(long)]
        no_export: bool,
        
        /// Export as CSV instead of TSV
        #[arg(long)]
        csv: bool,
    },
    
    /// Show cache statistics
    CacheStats {
        /// Show detailed statistics
        #[arg(long, short)]
        detailed: bool,
    },
    
    /// Clear cache
    ClearCache {
        /// Clear only stage 1 cache
        #[arg(long)]
        stage1_only: bool,
        
        /// Clear only stage 2 cache
        #[arg(long)]
        stage2_only: bool,
        
        /// Force clear without confirmation
        #[arg(long, short)]
        force: bool,
    },
    
    /// Test API connection
    TestConnection {
        /// Test with a sample term
        #[arg(long, default_value = "안녕하세요")]
        test_term: String,
    },
    
    /// Check system health
    Health {
        /// Output in JSON format
        #[arg(long)]
        json: bool,
    },
    
    /// List processing batches
    ListBatches {
        /// Number of batches to show
        #[arg(long, default_value_t = 10)]
        limit: usize,
        
        /// Show detailed information
        #[arg(long, short)]
        detailed: bool,
    },
    
    /// Show batch status
    BatchStatus {
        /// Batch ID to check
        batch_id: i32,
        
        /// Show failed items
        #[arg(long)]
        show_failed: bool,
    },
    
    /// Export metrics in Prometheus format
    Metrics {
        /// Output file (stdout if not specified)
        #[arg(long)]
        output: Option<PathBuf>,
    },
    
    /// Warm cache with vocabulary items
    WarmCache {
        /// Input CSV file path
        input: PathBuf,
        
        /// Only warm stage 1 cache
        #[arg(long)]
        stage1_only: bool,
    },
}

impl Cli {
    pub fn init_logging(&self) {
        use tracing_subscriber::{fmt, EnvFilter};
        
        let filter = if self.debug {
            EnvFilter::new("debug")
        } else {
            EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| EnvFilter::new("info"))
        };
        
        let subscriber = fmt()
            .with_env_filter(filter)
            .with_ansi(!self.no_color);
            
        if self.debug {
            subscriber.pretty().init();
        } else {
            subscriber.init();
        }
    }
}