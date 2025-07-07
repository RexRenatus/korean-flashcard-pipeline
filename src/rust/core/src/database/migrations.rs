use sqlx::{Sqlite, Transaction};
use tracing::{info, error};
use crate::models::PipelineError;
use super::DatabasePool;

pub struct Migration {
    pub version: i32,
    pub description: &'static str,
    pub sql: &'static str,
}

const MIGRATIONS: &[Migration] = &[
    Migration {
        version: 1,
        description: "Create initial schema",
        sql: include_str!("../../../migrations/001_initial_schema.sql"),
    },
];

pub async fn run_migrations(pool: &DatabasePool) -> Result<(), PipelineError> {
    info!("Starting database migrations");
    
    // Create schema_versions table if it doesn't exist
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS schema_versions (
            version INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        "#
    )
    .execute(pool)
    .await?;
    
    let current_version = super::get_database_version(pool).await?;
    info!("Current database version: {}", current_version);
    
    for migration in MIGRATIONS {
        if migration.version > current_version {
            apply_migration(pool, migration).await?;
        }
    }
    
    info!("All migrations completed successfully");
    Ok(())
}

async fn apply_migration(pool: &DatabasePool, migration: &Migration) -> Result<(), PipelineError> {
    info!("Applying migration {}: {}", migration.version, migration.description);
    
    let mut tx = pool.begin().await?;
    
    // Execute migration SQL
    sqlx::query(migration.sql)
        .execute(&mut *tx)
        .await
        .map_err(|e| {
            error!("Failed to apply migration {}: {}", migration.version, e);
            e
        })?;
    
    // Record migration
    sqlx::query(
        "INSERT INTO schema_versions (version, description) VALUES (?, ?)"
    )
    .bind(migration.version)
    .bind(migration.description)
    .execute(&mut *tx)
    .await?;
    
    tx.commit().await?;
    
    info!("Migration {} applied successfully", migration.version);
    Ok(())
}

pub async fn rollback_migration(pool: &DatabasePool, target_version: i32) -> Result<(), PipelineError> {
    let current_version = super::get_database_version(pool).await?;
    
    if target_version >= current_version {
        return Err(PipelineError::Configuration(
            format!("Target version {} must be less than current version {}", target_version, current_version)
        ));
    }
    
    // Note: This is a simplified rollback. In production, you'd need down migrations
    error!("Rollback not implemented. Manual database restoration required.");
    Err(PipelineError::Configuration("Rollback not implemented".to_string()))
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;
    
    #[tokio::test]
    async fn test_migrations() {
        let temp_file = NamedTempFile::new().unwrap();
        let db_path = temp_file.path().to_str().unwrap();
        
        let pool = super::super::create_pool(db_path).await.unwrap();
        
        // Run migrations
        run_migrations(&pool).await.unwrap();
        
        // Check version
        let version = super::super::get_database_version(&pool).await.unwrap();
        assert!(version > 0);
        
        // Run again - should be idempotent
        run_migrations(&pool).await.unwrap();
    }
}