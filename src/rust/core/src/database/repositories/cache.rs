use sqlx::{FromRow, Row};
use chrono::{DateTime, Utc};
use serde_json;
use tracing::{info, debug};
use crate::models::{CacheEntry, CacheType, CacheStats, Stage1Result, Stage2Result, PipelineError};
use crate::database::DatabasePool;

pub struct CacheRepository {
    pool: DatabasePool,
}

#[derive(FromRow)]
struct CacheRow {
    id: i64,
    vocabulary_id: i64,
    cache_key: String,
    request_hash: String,
    response_json: String,
    token_count: i32,
    model_used: String,
    created_at: DateTime<Utc>,
    accessed_at: DateTime<Utc>,
    access_count: i32,
}

impl CacheRepository {
    pub fn new(pool: DatabasePool) -> Self {
        Self { pool }
    }

    pub async fn get_stage1_cache(&self, cache_key: &str) -> Result<Option<Stage1Result>, PipelineError> {
        debug!("Looking up Stage 1 cache for key: {}", cache_key);
        
        let row = sqlx::query_as::<_, CacheRow>(
            r#"
            SELECT id, vocabulary_id, cache_key, request_hash, response_json, 
                   token_count, model_used, created_at, accessed_at, access_count
            FROM stage1_cache WHERE cache_key = ?
            "#
        )
        .bind(cache_key)
        .fetch_optional(&self.pool)
        .await?;
        
        match row {
            Some(row) => {
                // Update access count and timestamp
                self.update_cache_access("stage1_cache", row.id).await?;
                
                let response_data: serde_json::Value = serde_json::from_str(&row.response_json)?;
                
                // Reconstruct Stage1Result from cached data
                let semantic_analysis = serde_json::from_value(
                    response_data.get("semantic_analysis")
                        .ok_or_else(|| PipelineError::Cache("Missing semantic_analysis in cache".to_string()))?
                        .clone()
                )?;
                
                let result = Stage1Result {
                    vocabulary_id: row.vocabulary_id,
                    request_id: response_data.get("request_id")
                        .and_then(|v| v.as_str())
                        .unwrap_or("cached")
                        .to_string(),
                    cache_key: row.cache_key,
                    semantic_analysis,
                    created_at: row.created_at,
                };
                
                info!("Stage 1 cache hit for key: {}", cache_key);
                self.increment_cache_metrics(CacheType::Stage1, true, row.token_count).await?;
                
                Ok(Some(result))
            }
            None => {
                info!("Stage 1 cache miss for key: {}", cache_key);
                self.increment_cache_metrics(CacheType::Stage1, false, 0).await?;
                Ok(None)
            }
        }
    }

    pub async fn save_stage1_cache(
        &self, 
        result: &Stage1Result,
        request_hash: String,
        token_count: i32,
        model_used: String,
    ) -> Result<(), PipelineError> {
        debug!("Saving Stage 1 cache for key: {}", result.cache_key);
        
        let response_json = serde_json::json!({
            "request_id": &result.request_id,
            "semantic_analysis": &result.semantic_analysis,
        });
        
        sqlx::query(
            r#"
            INSERT INTO stage1_cache 
            (vocabulary_id, cache_key, request_hash, response_json, token_count, model_used)
            VALUES (?, ?, ?, ?, ?, ?)
            "#
        )
        .bind(result.vocabulary_id)
        .bind(&result.cache_key)
        .bind(&request_hash)
        .bind(response_json.to_string())
        .bind(token_count)
        .bind(&model_used)
        .execute(&self.pool)
        .await?;
        
        info!("Saved Stage 1 cache for key: {}", result.cache_key);
        Ok(())
    }

    pub async fn get_stage2_cache(&self, cache_key: &str) -> Result<Option<Stage2Result>, PipelineError> {
        debug!("Looking up Stage 2 cache for key: {}", cache_key);
        
        let row = sqlx::query(
            r#"
            SELECT id, vocabulary_id, stage1_cache_key, cache_key, request_hash, 
                   response_json, tsv_output, token_count, model_used, 
                   created_at, accessed_at, access_count
            FROM stage2_cache WHERE cache_key = ?
            "#
        )
        .bind(cache_key)
        .fetch_optional(&self.pool)
        .await?;
        
        match row {
            Some(row) => {
                let id: i64 = row.get(0);
                self.update_cache_access("stage2_cache", id).await?;
                
                let vocabulary_id: i64 = row.get(1);
                let stage1_cache_key: String = row.get(2);
                let cache_key: String = row.get(3);
                let response_json: String = row.get(5);
                let tsv_output: String = row.get(6);
                let token_count: i32 = row.get(7);
                let created_at: DateTime<Utc> = row.get(9);
                
                let response_data: serde_json::Value = serde_json::from_str(&response_json)?;
                
                let flashcard_content = serde_json::from_value(
                    response_data.get("flashcard_content")
                        .ok_or_else(|| PipelineError::Cache("Missing flashcard_content in cache".to_string()))?
                        .clone()
                )?;
                
                let result = Stage2Result {
                    vocabulary_id,
                    stage1_cache_key,
                    request_id: response_data.get("request_id")
                        .and_then(|v| v.as_str())
                        .unwrap_or("cached")
                        .to_string(),
                    cache_key,
                    flashcard_content,
                    tsv_output,
                    created_at,
                };
                
                info!("Stage 2 cache hit for key: {}", cache_key);
                self.increment_cache_metrics(CacheType::Stage2, true, token_count).await?;
                
                Ok(Some(result))
            }
            None => {
                info!("Stage 2 cache miss for key: {}", cache_key);
                self.increment_cache_metrics(CacheType::Stage2, false, 0).await?;
                Ok(None)
            }
        }
    }

    pub async fn save_stage2_cache(
        &self,
        result: &Stage2Result,
        request_hash: String,
        token_count: i32,
        model_used: String,
    ) -> Result<(), PipelineError> {
        debug!("Saving Stage 2 cache for key: {}", result.cache_key);
        
        let response_json = serde_json::json!({
            "request_id": &result.request_id,
            "flashcard_content": &result.flashcard_content,
        });
        
        sqlx::query(
            r#"
            INSERT INTO stage2_cache 
            (vocabulary_id, stage1_cache_key, cache_key, request_hash, 
             response_json, tsv_output, token_count, model_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            "#
        )
        .bind(result.vocabulary_id)
        .bind(&result.stage1_cache_key)
        .bind(&result.cache_key)
        .bind(&request_hash)
        .bind(response_json.to_string())
        .bind(&result.tsv_output)
        .bind(token_count)
        .bind(&model_used)
        .execute(&self.pool)
        .await?;
        
        info!("Saved Stage 2 cache for key: {}", result.cache_key);
        Ok(())
    }

    pub async fn get_cache_stats(&self) -> Result<CacheStats, PipelineError> {
        debug!("Calculating cache statistics");
        
        let stage1_count = sqlx::query_scalar::<_, i64>(
            "SELECT COUNT(*) FROM stage1_cache"
        )
        .fetch_one(&self.pool)
        .await?;
        
        let stage2_count = sqlx::query_scalar::<_, i64>(
            "SELECT COUNT(*) FROM stage2_cache"
        )
        .fetch_one(&self.pool)
        .await?;
        
        let metrics = sqlx::query(
            r#"
            SELECT 
                SUM(hit_count) as total_hits,
                SUM(miss_count) as total_misses,
                SUM(total_tokens_saved) as total_tokens_saved
            FROM cache_metrics
            "#
        )
        .fetch_one(&self.pool)
        .await?;
        
        let total_hits: i64 = metrics.get::<Option<i64>, _>(0).unwrap_or(0);
        let total_misses: i64 = metrics.get::<Option<i64>, _>(1).unwrap_or(0);
        let total_tokens_saved: i64 = metrics.get::<Option<i64>, _>(2).unwrap_or(0);
        
        let mut stats = CacheStats {
            total_entries: stage1_count + stage2_count,
            stage1_entries: stage1_count,
            stage2_entries: stage2_count,
            total_hits,
            total_misses,
            hit_rate: 0.0,
            total_tokens_saved,
            estimated_cost_saved: 0.0,
        };
        
        stats.calculate_hit_rate();
        stats.estimate_cost_saved();
        
        Ok(stats)
    }

    pub async fn clear_cache(&self, cache_type: Option<CacheType>) -> Result<i64, PipelineError> {
        let count = match cache_type {
            Some(CacheType::Stage1) => {
                let result = sqlx::query("DELETE FROM stage1_cache")
                    .execute(&self.pool)
                    .await?;
                result.rows_affected() as i64
            }
            Some(CacheType::Stage2) => {
                let result = sqlx::query("DELETE FROM stage2_cache")
                    .execute(&self.pool)
                    .await?;
                result.rows_affected() as i64
            }
            None => {
                let result1 = sqlx::query("DELETE FROM stage1_cache")
                    .execute(&self.pool)
                    .await?;
                let result2 = sqlx::query("DELETE FROM stage2_cache")
                    .execute(&self.pool)
                    .await?;
                (result1.rows_affected() + result2.rows_affected()) as i64
            }
        };
        
        info!("Cleared {} cache entries", count);
        Ok(count)
    }

    async fn update_cache_access(&self, table: &str, id: i64) -> Result<(), PipelineError> {
        sqlx::query(&format!(
            "UPDATE {} SET access_count = access_count + 1 WHERE id = ?",
            table
        ))
        .bind(id)
        .execute(&self.pool)
        .await?;
        
        Ok(())
    }

    async fn increment_cache_metrics(
        &self, 
        cache_type: CacheType, 
        is_hit: bool,
        tokens_saved: i32
    ) -> Result<(), PipelineError> {
        let cache_type_str = match cache_type {
            CacheType::Stage1 => "stage1",
            CacheType::Stage2 => "stage2",
        };
        
        if is_hit {
            sqlx::query(
                r#"
                INSERT INTO cache_metrics (cache_type, hit_count, miss_count, total_tokens_saved, date)
                VALUES (?, 1, 0, ?, DATE('now'))
                ON CONFLICT(cache_type, date) DO UPDATE SET
                    hit_count = hit_count + 1,
                    total_tokens_saved = total_tokens_saved + ?
                "#
            )
            .bind(cache_type_str)
            .bind(tokens_saved)
            .bind(tokens_saved)
            .execute(&self.pool)
            .await?;
        } else {
            sqlx::query(
                r#"
                INSERT INTO cache_metrics (cache_type, hit_count, miss_count, total_tokens_saved, date)
                VALUES (?, 0, 1, 0, DATE('now'))
                ON CONFLICT(cache_type, date) DO UPDATE SET
                    miss_count = miss_count + 1
                "#
            )
            .bind(cache_type_str)
            .execute(&self.pool)
            .await?;
        }
        
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{VocabularyItem, SemanticAnalysis, FrequencyLevel, FormalityLevel};
    
    async fn setup_test_db() -> DatabasePool {
        use tempfile::NamedTempFile;
        
        let temp_file = NamedTempFile::new().unwrap();
        let db_path = temp_file.path().to_str().unwrap();
        
        let pool = crate::database::create_pool(db_path).await.unwrap();
        crate::database::migrations::run_migrations(&pool).await.unwrap();
        
        pool
    }
    
    #[tokio::test]
    async fn test_cache_operations() {
        let pool = setup_test_db().await;
        let repo = CacheRepository::new(pool);
        
        // Test cache miss
        let result = repo.get_stage1_cache("test_key").await.unwrap();
        assert!(result.is_none());
        
        // Create and save a Stage1Result
        let stage1_result = Stage1Result {
            vocabulary_id: 1,
            request_id: "test_request".to_string(),
            cache_key: "test_key".to_string(),
            semantic_analysis: SemanticAnalysis {
                primary_meaning: "Test meaning".to_string(),
                alternative_meanings: vec![],
                connotations: vec![],
                register: "neutral".to_string(),
                usage_contexts: vec![],
                cultural_notes: None,
                frequency: FrequencyLevel::Common,
                formality: FormalityLevel::Neutral,
            },
            created_at: Utc::now(),
        };
        
        repo.save_stage1_cache(
            &stage1_result,
            "test_hash".to_string(),
            100,
            "claude-3-sonnet".to_string()
        ).await.unwrap();
        
        // Test cache hit
        let cached = repo.get_stage1_cache("test_key").await.unwrap();
        assert!(cached.is_some());
        
        let cached = cached.unwrap();
        assert_eq!(cached.vocabulary_id, 1);
        assert_eq!(cached.cache_key, "test_key");
    }
}