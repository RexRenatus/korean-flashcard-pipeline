use crate::errors::{PipelineError, Result};
use flashcard_core::models::{VocabularyItem, Stage2Result, FlashcardContent};
use std::path::Path;
use std::fs::File;
use std::io::{Write, BufWriter};
use tracing::{info, debug, instrument};
use csv::Writer;

pub struct TsvExporter {
    delimiter: u8,
    include_headers: bool,
}

impl Default for TsvExporter {
    fn default() -> Self {
        Self {
            delimiter: b'\t',
            include_headers: true,
        }
    }
}

impl TsvExporter {
    pub fn new() -> Self {
        Self::default()
    }
    
    #[instrument(skip(self, results))]
    pub async fn export(
        &self,
        results: &[(VocabularyItem, Stage2Result)],
        output_path: &Path,
    ) -> Result<ExportStats> {
        info!("Exporting {} flashcards to {:?}", results.len(), output_path);
        
        // Create parent directory if needed
        if let Some(parent) = output_path.parent() {
            tokio::fs::create_dir_all(parent).await?;
        }
        
        // Use blocking task for file I/O
        let results = results.to_vec();
        let delimiter = self.delimiter;
        let include_headers = self.include_headers;
        let output_path = output_path.to_owned();
        
        tokio::task::spawn_blocking(move || {
            let file = File::create(&output_path)?;
            let mut writer = Writer::from_writer(BufWriter::new(file));
            writer.set_delimiter(delimiter);
            
            // Write headers if requested
            if include_headers {
                writer.write_record(&[
                    "Position",
                    "Term",
                    "IPA",
                    "Part of Speech",
                    "Front Primary",
                    "Front Secondary",
                    "Front Example",
                    "Back Primary",
                    "Back Secondary",
                    "Back Example",
                    "Mnemonic",
                    "Difficulty",
                    "Frequency",
                    "Tags",
                    "Notes",
                ])?;
            }
            
            let mut stats = ExportStats::default();
            
            for (item, stage2) in &results {
                let front = &stage2.front;
                let back = &stage2.back;
                
                // Combine all tags
                let mut tags = Vec::new();
                tags.extend(front.thematic_tags.iter().cloned());
                tags.extend(front.grammatical_tags.iter().cloned());
                let tags_str = tags.join(", ");
                
                // Combine notes
                let mut notes = Vec::new();
                if let Some(ref usage) = front.usage_notes {
                    notes.push(format!("Usage: {}", usage));
                }
                if let Some(ref grammar) = front.grammar_notes {
                    notes.push(format!("Grammar: {}", grammar));
                }
                if let Some(ref cultural) = front.cultural_notes {
                    notes.push(format!("Cultural: {}", cultural));
                }
                let notes_str = notes.join(" | ");
                
                writer.write_record(&[
                    &item.position.to_string(),
                    &item.term,
                    &front.pronunciation_guide.as_deref().unwrap_or(""),
                    &item.word_type.as_deref().unwrap_or(""),
                    &front.primary_field,
                    &front.secondary_field.as_deref().unwrap_or(""),
                    &front.example_sentence.as_deref().unwrap_or(""),
                    &back.primary_field,
                    &back.secondary_field.as_deref().unwrap_or(""),
                    &back.example_sentence.as_deref().unwrap_or(""),
                    &front.mnemonic_aid.as_deref().unwrap_or(""),
                    &format!("{:?}", front.difficulty_level),
                    &format!("{:?}", front.frequency_level),
                    &tags_str,
                    &notes_str,
                ])?;
                
                stats.cards_exported += 1;
                
                // Count by difficulty
                match front.difficulty_level {
                    flashcard_core::models::DifficultyLevel::Beginner => stats.beginner_cards += 1,
                    flashcard_core::models::DifficultyLevel::Intermediate => stats.intermediate_cards += 1,
                    flashcard_core::models::DifficultyLevel::Advanced => stats.advanced_cards += 1,
                    flashcard_core::models::DifficultyLevel::Native => stats.native_cards += 1,
                }
                
                // Count special features
                if front.mnemonic_aid.is_some() {
                    stats.cards_with_mnemonics += 1;
                }
                if front.example_sentence.is_some() {
                    stats.cards_with_examples += 1;
                }
                if !notes.is_empty() {
                    stats.cards_with_notes += 1;
                }
            }
            
            writer.flush()?;
            
            debug!("Export complete: {:?}", stats);
            Ok::<ExportStats, PipelineError>(stats)
        })
        .await
        .map_err(|e| PipelineError::ExportError(format!("Task join error: {}", e)))?
    }
    
    pub async fn export_csv(
        &self,
        results: &[(VocabularyItem, Stage2Result)],
        output_path: &Path,
    ) -> Result<ExportStats> {
        let mut exporter = Self::new();
        exporter.delimiter = b',';
        exporter.export(results, output_path).await
    }
}

#[derive(Debug, Default, Clone)]
pub struct ExportStats {
    pub cards_exported: usize,
    pub beginner_cards: usize,
    pub intermediate_cards: usize,
    pub advanced_cards: usize,
    pub native_cards: usize,
    pub cards_with_mnemonics: usize,
    pub cards_with_examples: usize,
    pub cards_with_notes: usize,
}

impl ExportStats {
    pub fn summary(&self) -> String {
        format!(
            "Exported {} cards:\n  \
             - Beginner: {}\n  \
             - Intermediate: {}\n  \
             - Advanced: {}\n  \
             - Native: {}\n  \
             - With mnemonics: {}\n  \
             - With examples: {}\n  \
             - With notes: {}",
            self.cards_exported,
            self.beginner_cards,
            self.intermediate_cards,
            self.advanced_cards,
            self.native_cards,
            self.cards_with_mnemonics,
            self.cards_with_examples,
            self.cards_with_notes
        )
    }
}

// Additional export formats for future extension
pub trait Exporter {
    async fn export(
        &self,
        results: &[(VocabularyItem, Stage2Result)],
        output_path: &Path,
    ) -> Result<ExportStats>;
}

impl Exporter for TsvExporter {
    async fn export(
        &self,
        results: &[(VocabularyItem, Stage2Result)],
        output_path: &Path,
    ) -> Result<ExportStats> {
        self.export(results, output_path).await
    }
}

// JSON export for future use
pub struct JsonExporter;

impl JsonExporter {
    pub async fn export(
        &self,
        results: &[(VocabularyItem, Stage2Result)],
        output_path: &Path,
    ) -> Result<ExportStats> {
        info!("Exporting {} flashcards to JSON at {:?}", results.len(), output_path);
        
        let json_data = serde_json::to_string_pretty(results)?;
        tokio::fs::write(output_path, json_data).await?;
        
        Ok(ExportStats {
            cards_exported: results.len(),
            ..Default::default()
        })
    }
}