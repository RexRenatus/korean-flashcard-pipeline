use sqlx::{FromRow, Row};
use chrono::{DateTime, Utc};
use serde_json;
use tracing::{info, debug};
use crate::models::{VocabularyItem, DifficultyLevel, PipelineError};
use crate::database::DatabasePool;

pub struct VocabularyRepository {
    pool: DatabasePool,
}

#[derive(FromRow)]
struct VocabularyRow {
    id: i64,
    korean: String,
    english: String,
    hanja: Option<String>,
    category: String,
    subcategory: Option<String>,
    difficulty_level: String,
    source: String,
    example_sentence: Option<String>,
    notes: Option<String>,
    metadata: String,
    tags: String,
    created_at: DateTime<Utc>,
    updated_at: DateTime<Utc>,
}

impl VocabularyRepository {
    pub fn new(pool: DatabasePool) -> Self {
        Self { pool }
    }

    pub async fn create(&self, item: &VocabularyItem) -> Result<i64, PipelineError> {
        debug!("Creating vocabulary item: {} - {}", item.korean, item.english);
        
        let tags_json = serde_json::to_string(&item.tags)?;
        let metadata_json = serde_json::to_string(&item.metadata)?;
        let difficulty = format!("{:?}", item.difficulty_level).to_lowercase();
        
        let result = sqlx::query(
            r#"
            INSERT INTO vocabulary_items 
            (korean, english, hanja, category, subcategory, difficulty_level, 
             source, example_sentence, notes, metadata, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            "#
        )
        .bind(&item.korean)
        .bind(&item.english)
        .bind(&item.hanja)
        .bind(&item.category)
        .bind(&item.subcategory)
        .bind(&difficulty)
        .bind(&item.source)
        .bind(&item.example_sentence)
        .bind(&item.notes)
        .bind(&metadata_json)
        .bind(&tags_json)
        .execute(&self.pool)
        .await?;
        
        let id = result.last_insert_rowid();
        info!("Created vocabulary item with id: {}", id);
        Ok(id)
    }

    pub async fn get_by_id(&self, id: i64) -> Result<Option<VocabularyItem>, PipelineError> {
        debug!("Fetching vocabulary item by id: {}", id);
        
        let row = sqlx::query_as::<_, VocabularyRow>(
            "SELECT * FROM vocabulary_items WHERE id = ?"
        )
        .bind(id)
        .fetch_optional(&self.pool)
        .await?;
        
        match row {
            Some(row) => Ok(Some(self.row_to_item(row)?)),
            None => Ok(None),
        }
    }

    pub async fn find_by_content(
        &self, 
        korean: &str, 
        english: &str, 
        category: &str
    ) -> Result<Option<VocabularyItem>, PipelineError> {
        debug!("Finding vocabulary item: {} - {} in {}", korean, english, category);
        
        let row = sqlx::query_as::<_, VocabularyRow>(
            "SELECT * FROM vocabulary_items WHERE korean = ? AND english = ? AND category = ?"
        )
        .bind(korean)
        .bind(english)
        .bind(category)
        .fetch_optional(&self.pool)
        .await?;
        
        match row {
            Some(row) => Ok(Some(self.row_to_item(row)?)),
            None => Ok(None),
        }
    }

    pub async fn list_by_category(&self, category: &str) -> Result<Vec<VocabularyItem>, PipelineError> {
        debug!("Listing vocabulary items in category: {}", category);
        
        let rows = sqlx::query_as::<_, VocabularyRow>(
            "SELECT * FROM vocabulary_items WHERE category = ? ORDER BY created_at DESC"
        )
        .bind(category)
        .fetch_all(&self.pool)
        .await?;
        
        let items: Result<Vec<_>, _> = rows.into_iter()
            .map(|row| self.row_to_item(row))
            .collect();
        
        items
    }

    pub async fn list_unprocessed(&self, limit: i32) -> Result<Vec<VocabularyItem>, PipelineError> {
        debug!("Listing unprocessed vocabulary items, limit: {}", limit);
        
        let rows = sqlx::query_as::<_, VocabularyRow>(
            r#"
            SELECT v.* FROM vocabulary_items v
            LEFT JOIN stage1_cache s1 ON v.id = s1.vocabulary_id
            WHERE s1.id IS NULL
            ORDER BY v.created_at ASC
            LIMIT ?
            "#
        )
        .bind(limit)
        .fetch_all(&self.pool)
        .await?;
        
        let items: Result<Vec<_>, _> = rows.into_iter()
            .map(|row| self.row_to_item(row))
            .collect();
        
        items
    }

    pub async fn update(&self, item: &VocabularyItem) -> Result<(), PipelineError> {
        if let Some(id) = item.id {
            debug!("Updating vocabulary item: {}", id);
            
            let tags_json = serde_json::to_string(&item.tags)?;
            let metadata_json = serde_json::to_string(&item.metadata)?;
            let difficulty = format!("{:?}", item.difficulty_level).to_lowercase();
            
            sqlx::query(
                r#"
                UPDATE vocabulary_items 
                SET korean = ?, english = ?, hanja = ?, category = ?, 
                    subcategory = ?, difficulty_level = ?, source = ?, 
                    example_sentence = ?, notes = ?, metadata = ?, tags = ?
                WHERE id = ?
                "#
            )
            .bind(&item.korean)
            .bind(&item.english)
            .bind(&item.hanja)
            .bind(&item.category)
            .bind(&item.subcategory)
            .bind(&difficulty)
            .bind(&item.source)
            .bind(&item.example_sentence)
            .bind(&item.notes)
            .bind(&metadata_json)
            .bind(&tags_json)
            .bind(id)
            .execute(&self.pool)
            .await?;
            
            info!("Updated vocabulary item: {}", id);
            Ok(())
        } else {
            Err(PipelineError::Validation("Cannot update vocabulary item without id".to_string()))
        }
    }

    pub async fn delete(&self, id: i64) -> Result<bool, PipelineError> {
        debug!("Deleting vocabulary item: {}", id);
        
        let result = sqlx::query("DELETE FROM vocabulary_items WHERE id = ?")
            .bind(id)
            .execute(&self.pool)
            .await?;
        
        let deleted = result.rows_affected() > 0;
        if deleted {
            info!("Deleted vocabulary item: {}", id);
        }
        Ok(deleted)
    }

    pub async fn count(&self) -> Result<i64, PipelineError> {
        let count = sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM vocabulary_items")
            .fetch_one(&self.pool)
            .await?;
        
        Ok(count)
    }

    fn row_to_item(&self, row: VocabularyRow) -> Result<VocabularyItem, PipelineError> {
        let difficulty = match row.difficulty_level.as_str() {
            "beginner" => DifficultyLevel::Beginner,
            "elementary" => DifficultyLevel::Elementary,
            "intermediate" => DifficultyLevel::Intermediate,
            "advanced" => DifficultyLevel::Advanced,
            "native" => DifficultyLevel::Native,
            _ => return Err(PipelineError::Validation(
                format!("Invalid difficulty level: {}", row.difficulty_level)
            )),
        };
        
        let tags: Vec<String> = serde_json::from_str(&row.tags)?;
        let metadata = serde_json::from_str(&row.metadata)?;
        
        Ok(VocabularyItem {
            id: Some(row.id),
            korean: row.korean,
            english: row.english,
            hanja: row.hanja,
            category: row.category,
            subcategory: row.subcategory,
            tags,
            difficulty_level: difficulty,
            source: row.source,
            example_sentence: row.example_sentence,
            notes: row.notes,
            metadata,
            created_at: row.created_at,
            updated_at: row.updated_at,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;
    
    async fn setup_test_db() -> DatabasePool {
        let temp_file = NamedTempFile::new().unwrap();
        let db_path = temp_file.path().to_str().unwrap();
        
        let pool = crate::database::create_pool(db_path).await.unwrap();
        crate::database::migrations::run_migrations(&pool).await.unwrap();
        
        pool
    }
    
    #[tokio::test]
    async fn test_create_and_get() {
        let pool = setup_test_db().await;
        let repo = VocabularyRepository::new(pool);
        
        let item = VocabularyItem::new(
            "안녕하세요".to_string(),
            "Hello".to_string(),
            "greetings".to_string(),
        );
        
        let id = repo.create(&item).await.unwrap();
        assert!(id > 0);
        
        let fetched = repo.get_by_id(id).await.unwrap();
        assert!(fetched.is_some());
        
        let fetched = fetched.unwrap();
        assert_eq!(fetched.korean, "안녕하세요");
        assert_eq!(fetched.english, "Hello");
        assert_eq!(fetched.category, "greetings");
    }
}