use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheEntry {
    pub id: Option<i64>,
    pub cache_key: String,
    pub cache_type: CacheType,
    pub vocabulary_id: i64,
    pub request_hash: String,
    pub response_json: serde_json::Value,
    pub token_count: i32,
    pub model_used: String,
    pub created_at: DateTime<Utc>,
    pub accessed_at: DateTime<Utc>,
    pub access_count: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum CacheType {
    Stage1,
    Stage2,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheStats {
    pub total_entries: i64,
    pub stage1_entries: i64,
    pub stage2_entries: i64,
    pub total_hits: i64,
    pub total_misses: i64,
    pub hit_rate: f64,
    pub total_tokens_saved: i64,
    pub estimated_cost_saved: f64,
}

impl CacheEntry {
    pub fn new(
        cache_key: String,
        cache_type: CacheType,
        vocabulary_id: i64,
        request_hash: String,
        response_json: serde_json::Value,
        token_count: i32,
        model_used: String,
    ) -> Self {
        let now = Utc::now();
        Self {
            id: None,
            cache_key,
            cache_type,
            vocabulary_id,
            request_hash,
            response_json,
            token_count,
            model_used,
            created_at: now,
            accessed_at: now,
            access_count: 1,
        }
    }

    pub fn increment_access(&mut self) {
        self.access_count += 1;
        self.accessed_at = Utc::now();
    }
}

impl CacheStats {
    pub fn calculate_hit_rate(&mut self) {
        let total = self.total_hits + self.total_misses;
        self.hit_rate = if total > 0 {
            (self.total_hits as f64) / (total as f64)
        } else {
            0.0
        };
    }

    pub fn estimate_cost_saved(&mut self) {
        // $0.15 per 1000 tokens as per requirements
        self.estimated_cost_saved = (self.total_tokens_saved as f64) * 0.15 / 1000.0;
    }
}