import { PythonService } from './PythonService';

interface VocabularyItem {
  id: number;
  korean: string;
  english?: string;
  tags?: string[];
  priority?: number;
  status: string;
  created_at: string;
  updated_at: string;
}

interface FlashcardItem {
  id: number;
  vocabulary_id: number;
  word: string;
  stage: string;
  status: string;
  definition?: string;
  example?: string;
  cultural_notes?: string;
  usage_notes?: string;
  created_at: string;
  updated_at: string;
}

interface QueryOptions {
  page?: number;
  pageSize?: number;
  search?: string;
  status?: string;
  stage?: string;
  tags?: string[];
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export class DatabaseService {
  private pythonService: PythonService;

  constructor() {
    this.pythonService = PythonService.getInstance();
  }

  // Vocabulary methods
  async getVocabulary(options: QueryOptions = {}) {
    const result = await this.pythonService.runCommand('db', 'get_vocabulary', options);
    return {
      items: result.items as VocabularyItem[],
      total: result.total,
      page: options.page || 1,
      pageSize: options.pageSize || 50,
    };
  }

  async addVocabulary(data: {
    korean: string;
    english?: string;
    tags?: string[];
    priority?: number;
  }) {
    const result = await this.pythonService.runCommand('db', 'add_vocabulary', data);
    return result as VocabularyItem;
  }

  async updateVocabulary(id: number, data: Partial<VocabularyItem>) {
    const result = await this.pythonService.runCommand('db', 'update_vocabulary', {
      id,
      ...data,
    });
    return result as VocabularyItem;
  }

  async deleteVocabulary(id: number) {
    await this.pythonService.runCommand('db', 'delete_vocabulary', { id });
    return true;
  }

  async deleteVocabularyBatch(ids: number[]) {
    await this.pythonService.runCommand('db', 'delete_vocabulary_batch', { ids });
    return true;
  }

  // Flashcard methods
  async getFlashcards(options: QueryOptions = {}) {
    const result = await this.pythonService.runCommand('db', 'get_flashcards', options);
    return {
      items: result.items as FlashcardItem[],
      total: result.total,
      page: options.page || 1,
      pageSize: options.pageSize || 50,
      favorites: result.favorites || [],
    };
  }

  async deleteFlashcard(id: number) {
    await this.pythonService.runCommand('db', 'delete_flashcard', { id });
    return true;
  }

  async deleteFlashcardsBatch(ids: number[]) {
    await this.pythonService.runCommand('db', 'delete_flashcards_batch', { ids });
    return true;
  }

  // Favorites methods
  async toggleFavorite(type: 'vocabulary' | 'flashcard', id: number) {
    const result = await this.pythonService.runCommand('db', 'toggle_favorite', {
      type,
      id,
    });
    return result.is_favorite;
  }

  async getFavorites(type: 'vocabulary' | 'flashcard') {
    const result = await this.pythonService.runCommand('db', 'get_favorites', { type });
    return result.ids as number[];
  }

  // Stats methods
  async getDatabaseStats() {
    const result = await this.pythonService.runCommand('db', 'get_stats', {});
    return {
      vocabularyCount: result.vocabulary_count,
      flashcardCount: result.flashcard_count,
      processingCount: result.processing_count,
      failedCount: result.failed_count,
      databaseSize: result.database_size,
      lastBackup: result.last_backup,
    };
  }

  // Backup methods
  async createBackup() {
    const result = await this.pythonService.runCommand('db', 'create_backup', {});
    return result.backup_path;
  }

  async restoreBackup(backupPath: string) {
    await this.pythonService.runCommand('db', 'restore_backup', { backup_path: backupPath });
    return true;
  }
}