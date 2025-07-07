use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct VocabularyItem {
    pub id: Option<i64>,
    pub korean: String,
    pub english: String,
    pub hanja: Option<String>,
    pub category: String,
    pub subcategory: Option<String>,
    pub tags: Vec<String>,
    pub difficulty_level: DifficultyLevel,
    pub source: String,
    pub example_sentence: Option<String>,
    pub notes: Option<String>,
    pub metadata: HashMap<String, serde_json::Value>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum DifficultyLevel {
    Beginner,
    Elementary,
    Intermediate,
    Advanced,
    Native,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Stage1Result {
    pub vocabulary_id: i64,
    pub request_id: String,
    pub cache_key: String,
    pub semantic_analysis: SemanticAnalysis,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SemanticAnalysis {
    pub primary_meaning: String,
    pub alternative_meanings: Vec<String>,
    pub connotations: Vec<String>,
    pub register: String,
    pub usage_contexts: Vec<String>,
    pub cultural_notes: Option<String>,
    pub frequency: FrequencyLevel,
    pub formality: FormalityLevel,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum FrequencyLevel {
    VeryCommon,
    Common,
    Uncommon,
    Rare,
    Archaic,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum FormalityLevel {
    VeryFormal,
    Formal,
    Neutral,
    Informal,
    VeryInformal,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Stage2Result {
    pub vocabulary_id: i64,
    pub stage1_cache_key: String,
    pub request_id: String,
    pub cache_key: String,
    pub flashcard_content: FlashcardContent,
    pub tsv_output: String,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FlashcardContent {
    pub front: CardFace,
    pub back: CardFace,
    pub tags: Vec<String>,
    pub deck_name: String,
    pub card_type: CardType,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CardFace {
    pub primary_content: String,
    pub secondary_content: Option<String>,
    pub example: Option<String>,
    pub pronunciation: Option<String>,
    pub notes: Option<String>,
    pub media_references: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum CardType {
    Basic,
    BasicReversed,
    Cloze,
    Production,
    Recognition,
}

impl VocabularyItem {
    pub fn new(korean: String, english: String, category: String) -> Self {
        let now = Utc::now();
        Self {
            id: None,
            korean,
            english,
            hanja: None,
            category,
            subcategory: None,
            tags: Vec::new(),
            difficulty_level: DifficultyLevel::Intermediate,
            source: String::from("manual"),
            example_sentence: None,
            notes: None,
            metadata: HashMap::new(),
            created_at: now,
            updated_at: now,
        }
    }

    pub fn with_id(mut self, id: i64) -> Self {
        self.id = Some(id);
        self
    }

    pub fn generate_cache_key(&self) -> String {
        use sha2::{Sha256, Digest};
        let mut hasher = Sha256::new();
        
        hasher.update(&self.korean);
        hasher.update(&self.english);
        hasher.update(&self.category);
        
        if let Some(hanja) = &self.hanja {
            hasher.update(hanja);
        }
        
        if let Some(example) = &self.example_sentence {
            hasher.update(example);
        }
        
        format!("{:x}", hasher.finalize())
    }
}

impl Stage1Result {
    pub fn generate_cache_key(vocab_item: &VocabularyItem) -> String {
        format!("stage1_{}", vocab_item.generate_cache_key())
    }
}

impl Stage2Result {
    pub fn generate_cache_key(vocab_item: &VocabularyItem, stage1_key: &str) -> String {
        use sha2::{Sha256, Digest};
        let mut hasher = Sha256::new();
        hasher.update(stage1_key);
        hasher.update(vocab_item.generate_cache_key());
        format!("stage2_{:x}", hasher.finalize())
    }

    pub fn to_tsv_row(&self) -> String {
        let front = &self.flashcard_content.front;
        let back = &self.flashcard_content.back;
        
        let mut fields = vec![
            front.primary_content.clone(),
            back.primary_content.clone(),
        ];
        
        if let Some(secondary) = &back.secondary_content {
            fields.push(secondary.clone());
        }
        
        if let Some(example) = &back.example {
            fields.push(example.clone());
        }
        
        fields.push(self.flashcard_content.tags.join(" "));
        
        fields.join("\t")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_vocabulary_item_creation() {
        let item = VocabularyItem::new(
            "안녕하세요".to_string(),
            "Hello".to_string(),
            "greetings".to_string(),
        );
        
        assert_eq!(item.korean, "안녕하세요");
        assert_eq!(item.english, "Hello");
        assert_eq!(item.category, "greetings");
        assert_eq!(item.difficulty_level, DifficultyLevel::Intermediate);
    }

    #[test]
    fn test_cache_key_generation() {
        let item1 = VocabularyItem::new(
            "안녕하세요".to_string(),
            "Hello".to_string(),
            "greetings".to_string(),
        );
        
        let item2 = VocabularyItem::new(
            "안녕하세요".to_string(),
            "Hello".to_string(),
            "greetings".to_string(),
        );
        
        assert_eq!(item1.generate_cache_key(), item2.generate_cache_key());
        
        let item3 = VocabularyItem::new(
            "안녕".to_string(),
            "Hi".to_string(),
            "greetings".to_string(),
        );
        
        assert_ne!(item1.generate_cache_key(), item3.generate_cache_key());
    }
}