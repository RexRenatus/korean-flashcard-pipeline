use flashcard_core::models::{
    VocabularyItem, Stage1Result, Stage2Result, FlashcardContent,
    DifficultyLevel, FrequencyLevel, CardType, Comparison, HomonymEntry
};
use chrono::Utc;

#[test]
fn test_vocabulary_item_creation() {
    let item = VocabularyItem {
        id: None,
        position: 1,
        term: "안녕하세요".to_string(),
        word_type: Some("greeting".to_string()),
        created_at: Utc::now(),
        updated_at: Utc::now(),
    };
    
    assert_eq!(item.position, 1);
    assert_eq!(item.term, "안녕하세요");
    assert_eq!(item.word_type, Some("greeting".to_string()));
}

#[test]
fn test_cache_key_generation() {
    let item = VocabularyItem {
        id: None,
        position: 1,
        term: "test".to_string(),
        word_type: Some("noun".to_string()),
        created_at: Utc::now(),
        updated_at: Utc::now(),
    };
    
    let key = item.cache_key();
    assert!(!key.is_empty());
    assert_eq!(key.len(), 64); // SHA256 hex string length
    
    // Same item should generate same key
    let key2 = item.cache_key();
    assert_eq!(key, key2);
}

#[test]
fn test_cache_key_uniqueness() {
    let item1 = VocabularyItem {
        id: None,
        position: 1,
        term: "test1".to_string(),
        word_type: Some("noun".to_string()),
        created_at: Utc::now(),
        updated_at: Utc::now(),
    };
    
    let item2 = VocabularyItem {
        id: None,
        position: 2,
        term: "test2".to_string(),
        word_type: Some("noun".to_string()),
        created_at: Utc::now(),
        updated_at: Utc::now(),
    };
    
    assert_ne!(item1.cache_key(), item2.cache_key());
}

#[test]
fn test_difficulty_level_ordering() {
    use DifficultyLevel::*;
    
    assert!(Beginner < Intermediate);
    assert!(Intermediate < Advanced);
    assert!(Advanced < Native);
}

#[test]
fn test_frequency_level_default() {
    let freq = FrequencyLevel::default();
    assert_eq!(freq, FrequencyLevel::Common);
}

#[test]
fn test_stage1_result_serialization() {
    let result = Stage1Result {
        term_number: 1,
        term: "test".to_string(),
        ipa: "[test]".to_string(),
        pos: "noun".to_string(),
        primary_meaning: "a test".to_string(),
        other_meanings: "examination".to_string(),
        metaphor: "like a quiz".to_string(),
        metaphor_noun: "quiz".to_string(),
        metaphor_action: "testing".to_string(),
        suggested_location: "classroom".to_string(),
        anchor_object: "pencil".to_string(),
        anchor_sensory: "sharp".to_string(),
        explanation: "used to evaluate".to_string(),
        usage_context: Some("academic".to_string()),
        comparison: Comparison {
            similar_to: vec!["exam".to_string()],
            different_from: vec!["homework".to_string()],
            commonly_confused_with: vec![],
        },
        homonyms: vec![],
        korean_keywords: vec!["시험".to_string()],
    };
    
    // Test serialization
    let json = serde_json::to_string(&result).unwrap();
    let deserialized: Stage1Result = serde_json::from_str(&json).unwrap();
    
    assert_eq!(result.term, deserialized.term);
    assert_eq!(result.comparison.similar_to, deserialized.comparison.similar_to);
}

#[test]
fn test_flashcard_content_creation() {
    let content = FlashcardContent {
        primary_field: "Front text".to_string(),
        secondary_field: Some("Additional info".to_string()),
        tertiary_field: None,
        example_sentence: Some("This is an example.".to_string()),
        pronunciation_guide: Some("[pronunciation]".to_string()),
        image_prompt: None,
        mnemonic_aid: Some("Memory helper".to_string()),
        grammar_notes: None,
        cultural_notes: None,
        usage_notes: Some("Common usage".to_string()),
        difficulty_level: DifficultyLevel::Intermediate,
        frequency_level: FrequencyLevel::Common,
        thematic_tags: vec!["daily".to_string()],
        grammatical_tags: vec!["noun".to_string()],
        style_register: None,
    };
    
    assert_eq!(content.primary_field, "Front text");
    assert_eq!(content.difficulty_level, DifficultyLevel::Intermediate);
    assert_eq!(content.thematic_tags.len(), 1);
}

#[test]
fn test_stage2_result_with_flashcard() {
    let front = FlashcardContent {
        primary_field: "안녕하세요".to_string(),
        secondary_field: Some("Hello (formal)".to_string()),
        tertiary_field: None,
        example_sentence: Some("안녕하세요, 만나서 반갑습니다.".to_string()),
        pronunciation_guide: Some("[an.njʌŋ.ha.se.jo]".to_string()),
        image_prompt: None,
        mnemonic_aid: None,
        grammar_notes: Some("Formal greeting".to_string()),
        cultural_notes: Some("Used with strangers or elders".to_string()),
        usage_notes: None,
        difficulty_level: DifficultyLevel::Beginner,
        frequency_level: FrequencyLevel::Essential,
        thematic_tags: vec!["greeting".to_string(), "formal".to_string()],
        grammatical_tags: vec!["interjection".to_string()],
        style_register: Some("formal".to_string()),
    };
    
    let back = FlashcardContent {
        primary_field: "Hello (formal greeting)".to_string(),
        secondary_field: Some("안녕하세요".to_string()),
        tertiary_field: None,
        example_sentence: Some("Hello, nice to meet you.".to_string()),
        pronunciation_guide: None,
        image_prompt: None,
        mnemonic_aid: Some("An young person says hello".to_string()),
        grammar_notes: None,
        cultural_notes: None,
        usage_notes: None,
        difficulty_level: DifficultyLevel::Beginner,
        frequency_level: FrequencyLevel::Essential,
        thematic_tags: vec![],
        grammatical_tags: vec![],
        style_register: None,
    };
    
    let result = Stage2Result {
        front,
        back,
        card_type: CardType::Standard,
        learning_order: Some(1),
        related_cards: vec![],
    };
    
    assert_eq!(result.card_type, CardType::Standard);
    assert_eq!(result.learning_order, Some(1));
    assert_eq!(result.front.primary_field, "안녕하세요");
}

#[test]
fn test_homonym_entry() {
    let homonym = HomonymEntry {
        term: "배".to_string(),
        meaning: "boat".to_string(),
        context: Some("transportation".to_string()),
    };
    
    assert_eq!(homonym.term, "배");
    assert_eq!(homonym.meaning, "boat");
    assert!(homonym.context.is_some());
}

#[test]
fn test_error_severity() {
    use flashcard_core::errors::{PipelineError, ErrorSeverity};
    
    let error = PipelineError::CacheError("test error".to_string());
    assert_eq!(error.severity(), ErrorSeverity::Warning);
    
    let error = PipelineError::DatabaseError("connection failed".to_string());
    assert_eq!(error.severity(), ErrorSeverity::Error);
    
    let error = PipelineError::ApiError("rate limited".to_string());
    assert!(error.is_retryable());
}