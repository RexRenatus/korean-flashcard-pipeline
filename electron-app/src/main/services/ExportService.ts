import { app, dialog } from 'electron';
import { promises as fs } from 'fs';
import path from 'path';
import { format } from 'date-fns';

interface ExportOptions {
  format: 'json' | 'csv' | 'anki';
  includeFields?: string[];
  filters?: any;
}

interface FlashcardData {
  id: number;
  word: string;
  definition?: string;
  example?: string;
  pronunciation?: string;
  cultural_notes?: string;
  usage_notes?: string;
  tags?: string[];
  stage: string;
  status: string;
  created_at: string;
}

export class ExportService {
  private exportDir: string;

  constructor() {
    this.exportDir = path.join(app.getPath('documents'), 'Korean Flashcards Exports');
    this.ensureExportDir();
  }

  private async ensureExportDir() {
    try {
      await fs.mkdir(this.exportDir, { recursive: true });
    } catch (error) {
      console.error('Failed to create export directory:', error);
    }
  }

  async exportFlashcards(flashcards: FlashcardData[], options: ExportOptions): Promise<string> {
    const timestamp = format(new Date(), 'yyyy-MM-dd_HH-mm-ss');
    const baseFilename = `flashcards_export_${timestamp}`;
    
    let filePath: string;
    let content: string;

    switch (options.format) {
      case 'json':
        filePath = path.join(this.exportDir, `${baseFilename}.json`);
        content = this.formatAsJSON(flashcards, options);
        break;
        
      case 'csv':
        filePath = path.join(this.exportDir, `${baseFilename}.csv`);
        content = this.formatAsCSV(flashcards, options);
        break;
        
      case 'anki':
        filePath = path.join(this.exportDir, `${baseFilename}_anki.txt`);
        content = this.formatAsAnki(flashcards, options);
        break;
        
      default:
        throw new Error(`Unsupported export format: ${options.format}`);
    }

    // Show save dialog
    const { filePath: selectedPath, canceled } = await dialog.showSaveDialog({
      defaultPath: filePath,
      filters: this.getFileFilters(options.format),
    });

    if (canceled || !selectedPath) {
      throw new Error('Export cancelled by user');
    }

    await fs.writeFile(selectedPath, content, 'utf-8');
    return selectedPath;
  }

  private formatAsJSON(flashcards: FlashcardData[], options: ExportOptions): string {
    const data = flashcards.map(card => this.filterFields(card, options.includeFields));
    return JSON.stringify(data, null, 2);
  }

  private formatAsCSV(flashcards: FlashcardData[], options: ExportOptions): string {
    if (flashcards.length === 0) {
      return '';
    }

    const fields = options.includeFields || [
      'word',
      'definition',
      'example',
      'pronunciation',
      'cultural_notes',
      'usage_notes',
      'tags',
      'stage',
      'status',
    ];

    // Header
    const header = fields.join(',');
    
    // Rows
    const rows = flashcards.map(card => {
      return fields.map(field => {
        let value = (card as any)[field];
        
        // Handle special cases
        if (field === 'tags' && Array.isArray(value)) {
          value = value.join(';');
        }
        
        // Escape CSV values
        if (typeof value === 'string') {
          if (value.includes(',') || value.includes('"') || value.includes('\n')) {
            value = `"${value.replace(/"/g, '""')}"`;
          }
        }
        
        return value || '';
      }).join(',');
    });

    return [header, ...rows].join('\n');
  }

  private formatAsAnki(flashcards: FlashcardData[], options: ExportOptions): string {
    // Anki format: front[tab]back[tab]tags
    return flashcards.map(card => {
      const front = card.word;
      
      const backParts = [];
      if (card.definition) backParts.push(`Definition: ${card.definition}`);
      if (card.example) backParts.push(`Example: ${card.example}`);
      if (card.pronunciation) backParts.push(`Pronunciation: ${card.pronunciation}`);
      if (card.cultural_notes) backParts.push(`Cultural Notes: ${card.cultural_notes}`);
      if (card.usage_notes) backParts.push(`Usage Notes: ${card.usage_notes}`);
      
      const back = backParts.join('<br><br>');
      const tags = card.tags ? card.tags.join(' ') : '';
      
      return `${front}\t${back}\t${tags}`;
    }).join('\n');
  }

  private filterFields(card: FlashcardData, includeFields?: string[]): any {
    if (!includeFields || includeFields.length === 0) {
      return card;
    }

    const filtered: any = {};
    includeFields.forEach(field => {
      if (field in card) {
        filtered[field] = (card as any)[field];
      }
    });
    
    return filtered;
  }

  private getFileFilters(format: string): Electron.FileFilter[] {
    switch (format) {
      case 'json':
        return [
          { name: 'JSON Files', extensions: ['json'] },
          { name: 'All Files', extensions: ['*'] },
        ];
        
      case 'csv':
        return [
          { name: 'CSV Files', extensions: ['csv'] },
          { name: 'All Files', extensions: ['*'] },
        ];
        
      case 'anki':
        return [
          { name: 'Text Files', extensions: ['txt'] },
          { name: 'All Files', extensions: ['*'] },
        ];
        
      default:
        return [{ name: 'All Files', extensions: ['*'] }];
    }
  }

  async exportVocabulary(vocabulary: any[], format: 'csv' | 'json'): Promise<string> {
    const timestamp = format(new Date(), 'yyyy-MM-dd_HH-mm-ss');
    const baseFilename = `vocabulary_export_${timestamp}`;
    
    let filePath: string;
    let content: string;

    if (format === 'json') {
      filePath = path.join(this.exportDir, `${baseFilename}.json`);
      content = JSON.stringify(vocabulary, null, 2);
    } else {
      filePath = path.join(this.exportDir, `${baseFilename}.csv`);
      content = this.vocabularyToCSV(vocabulary);
    }

    const { filePath: selectedPath, canceled } = await dialog.showSaveDialog({
      defaultPath: filePath,
      filters: this.getFileFilters(format),
    });

    if (canceled || !selectedPath) {
      throw new Error('Export cancelled by user');
    }

    await fs.writeFile(selectedPath, content, 'utf-8');
    return selectedPath;
  }

  private vocabularyToCSV(vocabulary: any[]): string {
    if (vocabulary.length === 0) {
      return 'korean,english,tags,priority,status';
    }

    const header = 'korean,english,tags,priority,status';
    const rows = vocabulary.map(item => {
      const korean = item.korean || '';
      const english = item.english || '';
      const tags = Array.isArray(item.tags) ? item.tags.join(';') : '';
      const priority = item.priority || 0;
      const status = item.status || 'pending';
      
      return [korean, english, tags, priority, status]
        .map(value => {
          const str = String(value);
          if (str.includes(',') || str.includes('"') || str.includes('\n')) {
            return `"${str.replace(/"/g, '""')}"`;
          }
          return str;
        })
        .join(',');
    });

    return [header, ...rows].join('\n');
  }
}