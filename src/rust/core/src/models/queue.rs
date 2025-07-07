use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueueItem {
    pub id: Option<i64>,
    pub vocabulary_id: i64,
    pub batch_id: String,
    pub status: ProcessingStatus,
    pub stage: ProcessingStage,
    pub retry_count: i32,
    pub max_retries: i32,
    pub error_message: Option<String>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub started_at: Option<DateTime<Utc>>,
    pub completed_at: Option<DateTime<Utc>>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum ProcessingStatus {
    Pending,
    InProgress,
    Completed,
    Failed,
    Quarantined,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum ProcessingStage {
    Stage1,
    Stage2,
    Complete,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BatchProgress {
    pub batch_id: String,
    pub total_items: i32,
    pub completed_items: i32,
    pub failed_items: i32,
    pub quarantined_items: i32,
    pub pending_items: i32,
    pub in_progress_items: i32,
    pub start_time: DateTime<Utc>,
    pub estimated_completion: Option<DateTime<Utc>>,
    pub items_per_second: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessingCheckpoint {
    pub id: Option<i64>,
    pub batch_id: String,
    pub last_processed_id: i64,
    pub stage: ProcessingStage,
    pub checkpoint_data: serde_json::Value,
    pub created_at: DateTime<Utc>,
}

impl QueueItem {
    pub fn new(vocabulary_id: i64, batch_id: String) -> Self {
        let now = Utc::now();
        Self {
            id: None,
            vocabulary_id,
            batch_id,
            status: ProcessingStatus::Pending,
            stage: ProcessingStage::Stage1,
            retry_count: 0,
            max_retries: 3,
            error_message: None,
            created_at: now,
            updated_at: now,
            started_at: None,
            completed_at: None,
        }
    }

    pub fn start_processing(&mut self) {
        self.status = ProcessingStatus::InProgress;
        self.started_at = Some(Utc::now());
        self.updated_at = Utc::now();
    }

    pub fn complete_stage(&mut self) {
        match self.stage {
            ProcessingStage::Stage1 => {
                self.stage = ProcessingStage::Stage2;
                self.status = ProcessingStatus::Pending;
            }
            ProcessingStage::Stage2 => {
                self.stage = ProcessingStage::Complete;
                self.status = ProcessingStatus::Completed;
                self.completed_at = Some(Utc::now());
            }
            ProcessingStage::Complete => {}
        }
        self.updated_at = Utc::now();
    }

    pub fn fail_with_retry(&mut self, error: String) -> bool {
        self.retry_count += 1;
        self.error_message = Some(error);
        self.updated_at = Utc::now();

        if self.retry_count >= self.max_retries {
            self.status = ProcessingStatus::Quarantined;
            false
        } else {
            self.status = ProcessingStatus::Pending;
            true
        }
    }

    pub fn quarantine(&mut self, reason: String) {
        self.status = ProcessingStatus::Quarantined;
        self.error_message = Some(reason);
        self.updated_at = Utc::now();
    }
}

impl BatchProgress {
    pub fn calculate_progress(&self) -> f64 {
        if self.total_items == 0 {
            return 0.0;
        }
        (self.completed_items as f64 / self.total_items as f64) * 100.0
    }

    pub fn estimate_completion(&mut self) {
        if self.items_per_second > 0.0 && self.pending_items > 0 {
            let seconds_remaining = self.pending_items as f64 / self.items_per_second;
            self.estimated_completion = Some(
                Utc::now() + chrono::Duration::seconds(seconds_remaining as i64)
            );
        }
    }

    pub fn is_complete(&self) -> bool {
        self.pending_items == 0 && self.in_progress_items == 0
    }
}