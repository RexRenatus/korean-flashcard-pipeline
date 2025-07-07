use sqlx::{sqlite::{SqlitePool, SqlitePoolOptions, SqliteConnectOptions}, Pool, Sqlite};
use std::time::Duration;
use tracing::{info, error};
use crate::models::PipelineError;

pub type DatabasePool = Pool<Sqlite>;

pub async fn create_pool(database_url: &str) -> Result<DatabasePool, PipelineError> {
    info!("Creating database connection pool for: {}", database_url);
    
    let options = SqliteConnectOptions::new()
        .filename(database_url)
        .create_if_missing(true)
        .journal_mode(sqlx::sqlite::SqliteJournalMode::Wal)
        .pragma("foreign_keys", "ON")
        .pragma("temp_store", "MEMORY")
        .pragma("mmap_size", "30000000000")
        .pragma("synchronous", "NORMAL");
    
    let pool = SqlitePoolOptions::new()
        .max_connections(10)
        .min_connections(2)
        .acquire_timeout(Duration::from_secs(5))
        .idle_timeout(Duration::from_secs(60))
        .max_lifetime(Duration::from_secs(1800))
        .connect_with(options)
        .await?;
    
    info!("Database connection pool created successfully");
    Ok(pool)
}

pub async fn ensure_database_exists(pool: &DatabasePool) -> Result<(), PipelineError> {
    info!("Ensuring database structure exists");
    
    // Test connection
    sqlx::query("SELECT 1")
        .fetch_one(pool)
        .await?;
    
    info!("Database connection verified");
    Ok(())
}

pub async fn get_database_version(pool: &DatabasePool) -> Result<i32, PipelineError> {
    let result = sqlx::query_scalar::<_, i32>(
        "SELECT version FROM schema_versions ORDER BY version DESC LIMIT 1"
    )
    .fetch_optional(pool)
    .await;
    
    match result {
        Ok(Some(version)) => Ok(version),
        Ok(None) => Ok(0),
        Err(sqlx::Error::Database(db_err)) if db_err.message().contains("no such table") => Ok(0),
        Err(e) => Err(e.into()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;
    
    #[tokio::test]
    async fn test_create_pool() {
        let temp_file = NamedTempFile::new().unwrap();
        let db_path = temp_file.path().to_str().unwrap();
        
        let pool = create_pool(db_path).await.unwrap();
        assert!(pool.size() > 0);
        
        // Test connection
        let result = sqlx::query("SELECT 1 as test")
            .fetch_one(&pool)
            .await
            .unwrap();
        
        let test: i32 = sqlx::Row::get(&result, "test");
        assert_eq!(test, 1);
    }
    
    #[tokio::test]
    async fn test_wal_mode() {
        let temp_file = NamedTempFile::new().unwrap();
        let db_path = temp_file.path().to_str().unwrap();
        
        let pool = create_pool(db_path).await.unwrap();
        
        let result = sqlx::query("PRAGMA journal_mode")
            .fetch_one(&pool)
            .await
            .unwrap();
        
        let mode: String = sqlx::Row::get(&result, 0);
        assert_eq!(mode, "wal");
    }
}