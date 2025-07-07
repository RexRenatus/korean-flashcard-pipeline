use flashcard_pipeline::{
    cli::{Cli, Commands},
    pipeline::{Pipeline, PipelineConfig},
    monitoring::HealthStatus,
    errors::PipelineError,
};
use clap::Parser;
use tracing::{info, error, warn};
use console::{style, Emoji};
use std::process;

static SPARKLE: Emoji<'_, '_> = Emoji("✨ ", "* ");
static ROCKET: Emoji<'_, '_> = Emoji("🚀 ", "=> ");
static CHECK: Emoji<'_, '_> = Emoji("✅ ", "[OK] ");
static CROSS: Emoji<'_, '_> = Emoji("❌ ", "[FAIL] ");
static THINKING: Emoji<'_, '_> = Emoji("🤔 ", "... ");
static CACHE: Emoji<'_, '_> = Emoji("💾 ", "[CACHE] ");
static HEALTH: Emoji<'_, '_> = Emoji("🏥 ", "[HEALTH] ");

#[tokio::main]
async fn main() {
    let cli = Cli::parse();
    cli.init_logging();
    
    if let Err(e) = run(cli).await {
        error!("{} {}", CROSS, style(e).red());
        process::exit(e.exit_code());
    }
}

async fn run(cli: Cli) -> Result<(), PipelineError> {
    match cli.command {
        Commands::Process {
            input,
            output,
            max_concurrent,
            batch_size,
            resume,
            no_export,
            csv,
        } => {
            println!("{} {}Korean Language Flashcard Pipeline", SPARKLE, style("Starting ").bold());
            
            let config = PipelineConfig {
                database_url: cli.database_url,
                cache_dir: cli.cache_dir,
                max_concurrent,
                batch_size,
                enable_metrics: true,
                checkpoint_interval: 10,
            };
            
            let pipeline = Pipeline::new(config).await?;
            
            let result = pipeline.process_csv_file(&input, &output, resume).await?;
            
            println!("\n{} {}!", CHECK, style("Processing complete").green().bold());
            println!("  Total items: {}", style(result.total_items).cyan());
            println!("  Successful: {}", style(result.successful_items).green());
            println!("  Failed: {}", style(result.failed_items).red());
            println!("  Cache hits: {} ({:.1}%)", 
                style(result.cache_hits).yellow(),
                (result.cache_hits as f64 / result.total_items as f64) * 100.0
            );
            println!("  Processing time: {:?}", result.processing_time);
            
            if !no_export && result.successful_items > 0 {
                println!("\n{} Export statistics:", SPARKLE);
                println!("{}", result.export_stats.summary());
                println!("\nOutput written to: {}", style(output.display()).cyan());
            }
        }
        
        Commands::CacheStats { detailed } => {
            let config = PipelineConfig {
                database_url: cli.database_url,
                cache_dir: cli.cache_dir,
                ..Default::default()
            };
            
            let pipeline = Pipeline::new(config).await?;
            let stats = pipeline.get_cache_stats().await?;
            
            println!("{} {}:", CACHE, style("Cache Statistics").bold());
            println!("  Total entries: {}", style(stats.total_entries).cyan());
            println!("  Stage 1 entries: {}", style(stats.stage1_entries).cyan());
            println!("  Stage 2 entries: {}", style(stats.stage2_entries).cyan());
            println!("  Total size: {} MB", style(stats.total_size_bytes / 1_048_576).cyan());
            println!("  Hit rate: {:.1}%", stats.cache_hit_rate);
            
            if detailed {
                // TODO: Add more detailed statistics
            }
        }
        
        Commands::ClearCache { stage1_only, stage2_only, force } => {
            if !force {
                println!("{} Are you sure you want to clear the cache? This cannot be undone.", THINKING);
                println!("Use --force to skip this confirmation.");
                return Ok(());
            }
            
            let config = PipelineConfig {
                database_url: cli.database_url,
                cache_dir: cli.cache_dir,
                ..Default::default()
            };
            
            let pipeline = Pipeline::new(config).await?;
            
            // TODO: Implement cache clearing
            println!("{} Cache cleared successfully", CHECK);
        }
        
        Commands::TestConnection { test_term } => {
            println!("{} Testing API connection...", ROCKET);
            
            let config = PipelineConfig {
                database_url: cli.database_url,
                cache_dir: cli.cache_dir,
                ..Default::default()
            };
            
            let pipeline = Pipeline::new(config).await?;
            
            // Create test item
            let test_item = flashcard_core::models::VocabularyItem {
                id: None,
                position: 1,
                term: test_term.clone(),
                word_type: None,
                created_at: chrono::Utc::now(),
                updated_at: chrono::Utc::now(),
            };
            
            println!("Testing with term: {}", style(&test_term).cyan());
            
            // Process single item
            let result = pipeline.process_csv_file(
                &std::path::Path::new("test.csv"),
                &std::path::Path::new("test.tsv"),
                None
            ).await;
            
            match result {
                Ok(_) => println!("{} API connection successful!", CHECK),
                Err(e) => {
                    println!("{} API connection failed: {}", CROSS, e);
                    return Err(e);
                }
            }
        }
        
        Commands::Health { json } => {
            let config = PipelineConfig {
                database_url: cli.database_url,
                cache_dir: cli.cache_dir,
                ..Default::default()
            };
            
            let pipeline = Pipeline::new(config).await?;
            let health = pipeline.health_checker.check_health().await?;
            
            if json {
                println!("{}", serde_json::to_string_pretty(&health)?);
            } else {
                println!("{} {}:", HEALTH, style("System Health Check").bold());
                println!("  Overall: {}", 
                    if health.healthy { 
                        style("HEALTHY").green() 
                    } else { 
                        style("UNHEALTHY").red() 
                    }
                );
                
                print_service_status("Database", &health.database_status);
                print_service_status("Cache", &health.cache_status);
                print_service_status("API", &health.api_status);
                print_service_status("Python Bridge", &health.python_bridge_status);
                
                println!("  Last check: {}", health.last_check.format("%Y-%m-%d %H:%M:%S UTC"));
            }
        }
        
        Commands::ListBatches { limit, detailed } => {
            let config = PipelineConfig {
                database_url: cli.database_url,
                cache_dir: cli.cache_dir,
                ..Default::default()
            };
            
            let pipeline = Pipeline::new(config).await?;
            let batches = pipeline.list_batches().await?;
            
            if batches.is_empty() {
                println!("No batches found.");
                return Ok(());
            }
            
            println!("{} {}:", SPARKLE, style("Processing Batches").bold());
            for batch in batches.iter().take(limit) {
                println!("  Batch #{}: {} items (created: {})",
                    style(batch.batch_id).cyan(),
                    batch.total_items,
                    batch.created_at.format("%Y-%m-%d %H:%M:%S UTC")
                );
                
                if detailed {
                    // TODO: Add more batch details
                }
            }
        }
        
        Commands::BatchStatus { batch_id, show_failed } => {
            let config = PipelineConfig {
                database_url: cli.database_url,
                cache_dir: cli.cache_dir,
                ..Default::default()
            };
            
            let pipeline = Pipeline::new(config).await?;
            let status = pipeline.get_batch_status(batch_id).await?;
            
            println!("{} Batch #{} Status:", SPARKLE, style(batch_id).cyan());
            println!("  Total items: {}", status.total_items);
            println!("  Completed: {} ({:.1}%)", 
                style(status.completed_items).green(),
                (status.completed_items as f64 / status.total_items as f64) * 100.0
            );
            println!("  Failed: {}", style(status.failed_items).red());
            println!("  In progress: {}", 
                if status.in_progress { 
                    style("Yes").yellow() 
                } else { 
                    style("No").dim() 
                }
            );
            
            if show_failed && status.failed_items > 0 {
                // TODO: Show failed items
            }
        }
        
        Commands::Metrics { output } => {
            let config = PipelineConfig {
                database_url: cli.database_url,
                cache_dir: cli.cache_dir,
                ..Default::default()
            };
            
            let pipeline = Pipeline::new(config).await?;
            let metrics = pipeline.metrics_collector.get_metrics();
            let prometheus_format = metrics.to_prometheus_format();
            
            if let Some(output_path) = output {
                tokio::fs::write(&output_path, prometheus_format).await?;
                println!("{} Metrics written to: {}", CHECK, output_path.display());
            } else {
                println!("{}", prometheus_format);
            }
        }
        
        Commands::WarmCache { input, stage1_only } => {
            println!("{} Warming cache...", CACHE);
            
            let config = PipelineConfig {
                database_url: cli.database_url,
                cache_dir: cli.cache_dir,
                ..Default::default()
            };
            
            let pipeline = Pipeline::new(config).await?;
            
            // Load items from CSV
            let items = pipeline.load_csv(&input).await?;
            let warmed = pipeline.warm_cache(&items).await?;
            
            println!("{} Cache warmed with {} entries", CHECK, style(warmed).cyan());
        }
    }
    
    Ok(())
}

fn print_service_status(name: &str, status: &flashcard_pipeline::monitoring::ServiceStatus) {
    use flashcard_pipeline::monitoring::ServiceStatus;
    
    let (emoji, text) = match status {
        ServiceStatus::Healthy => (CHECK, style("Healthy").green()),
        ServiceStatus::Degraded(msg) => (Emoji("⚠️ ", "[WARN] "), style(format!("Degraded: {}", msg)).yellow()),
        ServiceStatus::Unhealthy(msg) => (CROSS, style(format!("Unhealthy: {}", msg)).red()),
    };
    
    println!("  {}: {} {}", name, emoji, text);
}