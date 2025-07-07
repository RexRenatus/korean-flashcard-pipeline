use sqlx::{FromRow, Row};
use chrono::{DateTime, Utc, Duration};
use serde_json;
use tracing::{info, debug, warn};
use crate::models::{
    QueueItem, ProcessingStatus, ProcessingStage, BatchProgress, 
    ProcessingCheckpoint, PipelineError
};
use crate::database::DatabasePool;

pub struct QueueRepository {
    pool: DatabasePool,
}

#[derive(FromRow)]
struct QueueRow {
    id: i64,
    vocabulary_id: i64,
    batch_id: String,
    status: String,
    stage: String,
    retry_count: i32,
    max_retries: i32,
    error_message: Option<String>,
    created_at: DateTime<Utc>,
    updated_at: DateTime<Utc>,
    started_at: Option<DateTime<Utc>>,
    completed_at: Option<DateTime<Utc>>,
}

impl QueueRepository {
    pub fn new(pool: DatabasePool) -> Self {
        Self { pool }
    }

    pub async fn enqueue_batch(&self, vocabulary_ids: Vec<i64>, batch_id: &str) -> Result<i64, PipelineError> {
        debug!("Enqueueing batch {} with {} items", batch_id, vocabulary_ids.len());
        
        let mut tx = self.pool.begin().await?;
        let mut count = 0;
        
        // Create batch metadata
        sqlx::query(
            r#"
            INSERT INTO batch_metadata (batch_id, total_items, status)
            VALUES (?, ?, 'pending')
            "#
        )
        .bind(batch_id)
        .bind(vocabulary_ids.len() as i32)
        .execute(&mut *tx)
        .await?;
        
        // Enqueue items
        for vocab_id in vocabulary_ids {
            sqlx::query(
                r#"
                INSERT INTO processing_queue 
                (vocabulary_id, batch_id, status, stage, retry_count, max_retries)
                VALUES (?, ?, 'pending', 'stage1', 0, 3)
                "#
            )
            .bind(vocab_id)
            .bind(batch_id)
            .execute(&mut *tx)
            .await?;
            
            count += 1;
        }
        
        tx.commit().await?;
        
        info!("Enqueued {} items in batch {}", count, batch_id);
        Ok(count)
    }

    pub async fn get_next_pending(&self, batch_id: Option<&str>) -> Result<Option<QueueItem>, PipelineError> {
        debug!("Getting next pending item from queue");
        
        let query = if let Some(batch_id) = batch_id {
            sqlx::query_as::<_, QueueRow>(
                r#"
                SELECT * FROM processing_queue 
                WHERE batch_id = ? AND status = 'pending'
                ORDER BY created_at ASC
                LIMIT 1
                "#
            )
            .bind(batch_id)
        } else {
            sqlx::query_as::<_, QueueRow>(
                r#"
                SELECT * FROM processing_queue 
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT 1
                "#
            )
        };
        
        let row = query.fetch_optional(&self.pool).await?;
        
        match row {
            Some(row) => Ok(Some(self.row_to_item(row)?)),
            None => Ok(None),
        }
    }

    pub async fn update_status(
        &self, 
        item_id: i64, 
        status: ProcessingStatus,
        error_message: Option<String>
    ) -> Result<(), PipelineError> {
        debug!("Updating queue item {} status to {:?}", item_id, status);
        
        let status_str = self.status_to_string(&status);
        
        let mut query = sqlx::query(
            r#"
            UPDATE processing_queue 
            SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
            "#
        );
        
        query = query.bind(&status_str).bind(&error_message);
        
        // Add additional fields based on status
        match status {
            ProcessingStatus::InProgress => {
                query = sqlx::query(
                    r#"
                    UPDATE processing_queue 
                    SET status = ?, error_message = ?, started_at = CURRENT_TIMESTAMP, 
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    "#
                )
                .bind(&status_str)
                .bind(&error_message)
                .bind(item_id);
            }
            ProcessingStatus::Completed => {
                query = sqlx::query(
                    r#"
                    UPDATE processing_queue 
                    SET status = ?, error_message = ?, completed_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    "#
                )
                .bind(&status_str)
                .bind(&error_message)
                .bind(item_id);
            }
            _ => {
                query = sqlx::query(
                    r#"
                    UPDATE processing_queue 
                    SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    "#
                )
                .bind(&status_str)
                .bind(&error_message)
                .bind(item_id);
            }
        }
        
        query.execute(&self.pool).await?;
        
        // Update batch progress
        if matches!(status, ProcessingStatus::Completed | ProcessingStatus::Failed | ProcessingStatus::Quarantined) {
            self.update_batch_progress(item_id).await?;
        }
        
        Ok(())
    }

    pub async fn complete_stage(&self, item_id: i64) -> Result<ProcessingStage, PipelineError> {
        debug!("Completing stage for queue item {}", item_id);
        
        let mut tx = self.pool.begin().await?;
        
        // Get current stage
        let current_stage: String = sqlx::query_scalar(
            "SELECT stage FROM processing_queue WHERE id = ?"
        )
        .bind(item_id)
        .fetch_one(&mut *tx)
        .await?;
        
        let next_stage = match current_stage.as_str() {
            "stage1" => {
                sqlx::query(
                    r#"
                    UPDATE processing_queue 
                    SET stage = 'stage2', status = 'pending', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    "#
                )
                .bind(item_id)
                .execute(&mut *tx)
                .await?;
                
                ProcessingStage::Stage2
            }
            "stage2" => {
                sqlx::query(
                    r#"
                    UPDATE processing_queue 
                    SET stage = 'complete', status = 'completed', 
                        completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    "#
                )
                .bind(item_id)
                .execute(&mut *tx)
                .await?;
                
                ProcessingStage::Complete
            }
            _ => return Err(PipelineError::Validation(
                format!("Invalid stage transition from: {}", current_stage)
            )),
        };
        
        tx.commit().await?;
        
        info!("Queue item {} advanced to stage {:?}", item_id, next_stage);
        Ok(next_stage)
    }

    pub async fn increment_retry(&self, item_id: i64) -> Result<bool, PipelineError> {
        debug!("Incrementing retry count for queue item {}", item_id);
        
        let mut tx = self.pool.begin().await?;
        
        // Get current retry info
        let row = sqlx::query(
            "SELECT retry_count, max_retries FROM processing_queue WHERE id = ?"
        )
        .bind(item_id)
        .fetch_one(&mut *tx)
        .await?;
        
        let retry_count: i32 = row.get(0);
        let max_retries: i32 = row.get(1);
        
        let new_retry_count = retry_count + 1;
        
        if new_retry_count >= max_retries {
            // Quarantine the item
            sqlx::query(
                r#"
                UPDATE processing_queue 
                SET status = 'quarantined', retry_count = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                "#
            )
            .bind(new_retry_count)
            .bind(item_id)
            .execute(&mut *tx)
            .await?;
            
            tx.commit().await?;
            
            warn!("Queue item {} quarantined after {} retries", item_id, new_retry_count);
            Ok(false)
        } else {
            // Reset to pending for retry
            sqlx::query(
                r#"
                UPDATE processing_queue 
                SET status = 'pending', retry_count = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                "#
            )
            .bind(new_retry_count)
            .bind(item_id)
            .execute(&mut *tx)
            .await?;
            
            tx.commit().await?;
            
            info!("Queue item {} retry count: {}/{}", item_id, new_retry_count, max_retries);
            Ok(true)
        }
    }

    pub async fn get_batch_progress(&self, batch_id: &str) -> Result<BatchProgress, PipelineError> {
        debug!("Getting progress for batch {}", batch_id);
        
        let metadata = sqlx::query(
            "SELECT total_items, start_time FROM batch_metadata WHERE batch_id = ?"
        )
        .bind(batch_id)
        .fetch_optional(&self.pool)
        .await?;
        
        if metadata.is_none() {
            return Err(PipelineError::Validation(
                format!("Batch {} not found", batch_id)
            ));
        }
        
        let metadata = metadata.unwrap();
        let total_items: i32 = metadata.get(0);
        let start_time: DateTime<Utc> = metadata.get(1);
        
        // Count items by status
        let counts = sqlx::query(
            r#"
            SELECT 
                status,
                COUNT(*) as count
            FROM processing_queue 
            WHERE batch_id = ?
            GROUP BY status
            "#
        )
        .bind(batch_id)
        .fetch_all(&self.pool)
        .await?;
        
        let mut progress = BatchProgress {
            batch_id: batch_id.to_string(),
            total_items,
            completed_items: 0,
            failed_items: 0,
            quarantined_items: 0,
            pending_items: 0,
            in_progress_items: 0,
            start_time,
            estimated_completion: None,
            items_per_second: 0.0,
        };
        
        for row in counts {
            let status: String = row.get(0);
            let count: i32 = row.get(1);
            
            match status.as_str() {
                "completed" => progress.completed_items = count,
                "failed" => progress.failed_items = count,
                "quarantined" => progress.quarantined_items = count,
                "pending" => progress.pending_items = count,
                "in_progress" => progress.in_progress_items = count,
                _ => {}
            }
        }
        
        // Calculate items per second
        let elapsed = Utc::now() - start_time;
        let elapsed_seconds = elapsed.num_seconds() as f64;
        if elapsed_seconds > 0.0 && progress.completed_items > 0 {
            progress.items_per_second = progress.completed_items as f64 / elapsed_seconds;
            progress.estimate_completion();
        }
        
        Ok(progress)
    }

    pub async fn save_checkpoint(
        &self,
        batch_id: &str,
        last_processed_id: i64,
        stage: ProcessingStage,
        checkpoint_data: serde_json::Value,
    ) -> Result<(), PipelineError> {
        debug!("Saving checkpoint for batch {} at item {}", batch_id, last_processed_id);
        
        let stage_str = match stage {
            ProcessingStage::Stage1 => "stage1",
            ProcessingStage::Stage2 => "stage2",
            ProcessingStage::Complete => "complete",
        };
        
        sqlx::query(
            r#"
            INSERT INTO processing_checkpoints 
            (batch_id, last_processed_id, stage, checkpoint_data)
            VALUES (?, ?, ?, ?)
            "#
        )
        .bind(batch_id)
        .bind(last_processed_id)
        .bind(stage_str)
        .bind(checkpoint_data.to_string())
        .execute(&self.pool)
        .await?;
        
        info!("Checkpoint saved for batch {}", batch_id);
        Ok(())
    }

    pub async fn get_latest_checkpoint(
        &self,
        batch_id: &str,
    ) -> Result<Option<ProcessingCheckpoint>, PipelineError> {
        debug!("Getting latest checkpoint for batch {}", batch_id);
        
        let row = sqlx::query(
            r#"
            SELECT id, batch_id, last_processed_id, stage, checkpoint_data, created_at
            FROM processing_checkpoints
            WHERE batch_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            "#
        )
        .bind(batch_id)
        .fetch_optional(&self.pool)
        .await?;
        
        match row {
            Some(row) => {
                let stage_str: String = row.get(3);
                let stage = match stage_str.as_str() {
                    "stage1" => ProcessingStage::Stage1,
                    "stage2" => ProcessingStage::Stage2,
                    "complete" => ProcessingStage::Complete,
                    _ => return Err(PipelineError::Validation(
                        format!("Invalid stage in checkpoint: {}", stage_str)
                    )),
                };
                
                let checkpoint_data: serde_json::Value = 
                    serde_json::from_str(&row.get::<String, _>(4))?;
                
                Ok(Some(ProcessingCheckpoint {
                    id: Some(row.get(0)),
                    batch_id: row.get(1),
                    last_processed_id: row.get(2),
                    stage,
                    checkpoint_data,
                    created_at: row.get(5),
                }))
            }
            None => Ok(None),
        }
    }

    async fn update_batch_progress(&self, item_id: i64) -> Result<(), PipelineError> {
        // Get batch_id for the item
        let batch_id: String = sqlx::query_scalar(
            "SELECT batch_id FROM processing_queue WHERE id = ?"
        )
        .bind(item_id)
        .fetch_one(&self.pool)
        .await?;
        
        // Update batch metadata
        let progress = self.get_batch_progress(&batch_id).await?;
        
        let status = if progress.is_complete() {
            if progress.failed_items > 0 || progress.quarantined_items > 0 {
                "partial"
            } else {
                "completed"
            }
        } else {
            "in_progress"
        };
        
        sqlx::query(
            r#"
            UPDATE batch_metadata 
            SET completed_items = ?, failed_items = ?, quarantined_items = ?, 
                status = ?, end_time = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE end_time END
            WHERE batch_id = ?
            "#
        )
        .bind(progress.completed_items)
        .bind(progress.failed_items)
        .bind(progress.quarantined_items)
        .bind(status)
        .bind(progress.is_complete())
        .bind(&batch_id)
        .execute(&self.pool)
        .await?;
        
        Ok(())
    }

    fn row_to_item(&self, row: QueueRow) -> Result<QueueItem, PipelineError> {
        let status = match row.status.as_str() {
            "pending" => ProcessingStatus::Pending,
            "in_progress" => ProcessingStatus::InProgress,
            "completed" => ProcessingStatus::Completed,
            "failed" => ProcessingStatus::Failed,
            "quarantined" => ProcessingStatus::Quarantined,
            _ => return Err(PipelineError::Validation(
                format!("Invalid status: {}", row.status)
            )),
        };
        
        let stage = match row.stage.as_str() {
            "stage1" => ProcessingStage::Stage1,
            "stage2" => ProcessingStage::Stage2,
            "complete" => ProcessingStage::Complete,
            _ => return Err(PipelineError::Validation(
                format!("Invalid stage: {}", row.stage)
            )),
        };
        
        Ok(QueueItem {
            id: Some(row.id),
            vocabulary_id: row.vocabulary_id,
            batch_id: row.batch_id,
            status,
            stage,
            retry_count: row.retry_count,
            max_retries: row.max_retries,
            error_message: row.error_message,
            created_at: row.created_at,
            updated_at: row.updated_at,
            started_at: row.started_at,
            completed_at: row.completed_at,
        })
    }

    fn status_to_string(&self, status: &ProcessingStatus) -> String {
        match status {
            ProcessingStatus::Pending => "pending",
            ProcessingStatus::InProgress => "in_progress",
            ProcessingStatus::Completed => "completed",
            ProcessingStatus::Failed => "failed",
            ProcessingStatus::Quarantined => "quarantined",
        }
        .to_string()
    }
}