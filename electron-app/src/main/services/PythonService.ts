import { IPCBridge } from './IPCBridge';
import { 
  VocabularyItem, 
  SystemStats, 
  ImportResult, 
  ExportOptions,
  ProcessingTask 
} from '@/shared/types';

interface RetryOptions {
  retries?: number;
  retryDelay?: number;
}

interface VocabularyListOptions {
  page?: number;
  pageSize?: number;
  filter?: string;
  sort?: string;
  search?: string;
}

interface ProcessingOptions {
  priority?: 'low' | 'normal' | 'high';
  stage?: 'stage1' | 'stage2' | 'full_pipeline';
}

interface ProcessingStatus {
  taskId: string;
  status: string;
  progress: number;
  processed: number;
  total: number;
  currentStage: string;
  estimatedTimeRemaining?: number;
}

interface APIHealthCheck {
  status: 'healthy' | 'degraded' | 'down';
  latency: number;
  rateLimit?: {
    remaining: number;
    reset: string;
  };
}

export class PythonService {
  private static instance: PythonService;
  private bridge: IPCBridge;
  private initialized = false;

  private constructor() {
    this.bridge = new IPCBridge();
  }

  static getInstance(): PythonService {
    if (!PythonService.instance) {
      PythonService.instance = new PythonService();
    }
    return PythonService.instance;
  }

  async ensureInitialized(): Promise<void> {
    if (this.initialized && this.bridge.isReady()) {
      return;
    }

    try {
      await this.bridge.initialize();
      this.initialized = true;
    } catch (error) {
      throw new Error(`Failed to initialize Python service: ${error}`);
    }
  }

  // Vocabulary Operations
  async getVocabularyList(
    options: VocabularyListOptions = {}, 
    retryOptions?: RetryOptions
  ): Promise<{ items: VocabularyItem[]; total: number; page: number; pageSize: number }> {
    await this.ensureInitialized();

    const { page = 1, pageSize = 50, filter, sort, search } = options;

    try {
      return await this.executeWithRetry(
        'get_vocabulary_list',
        { page, pageSize, filter, sort, search },
        retryOptions
      );
    } catch (error) {
      throw new Error(`Failed to get vocabulary list: ${error}`);
    }
  }

  async addVocabulary(item: Partial<VocabularyItem>): Promise<VocabularyItem> {
    await this.ensureInitialized();

    try {
      return await this.bridge.execute('add_vocabulary', item);
    } catch (error: any) {
      if (error.code) {
        throw error; // Pass through detailed errors
      }
      throw new Error(`Failed to add vocabulary: ${error}`);
    }
  }

  async updateVocabulary(id: number, updates: Partial<VocabularyItem>): Promise<VocabularyItem> {
    await this.ensureInitialized();

    try {
      return await this.bridge.execute('update_vocabulary', { id, updates });
    } catch (error) {
      throw new Error(`Failed to update vocabulary: ${error}`);
    }
  }

  async deleteVocabulary(ids: number[]): Promise<boolean> {
    await this.ensureInitialized();

    try {
      const result = await this.bridge.execute('delete_vocabulary', { ids });
      return result.success;
    } catch (error) {
      throw new Error(`Failed to delete vocabulary: ${error}`);
    }
  }

  // Import Operations
  async importVocabulary(filePath: string, format: 'csv' | 'txt' | 'json'): Promise<ImportResult> {
    await this.ensureInitialized();

    try {
      return await this.bridge.execute('import_vocabulary', { filePath, format });
    } catch (error) {
      throw new Error(`Failed to import vocabulary: ${error}`);
    }
  }

  async validateImportData(data: any[]): Promise<{ valid: boolean; errors: string[] }> {
    await this.ensureInitialized();

    try {
      return await this.bridge.execute('validate_import', { data });
    } catch (error) {
      throw new Error(`Failed to validate import data: ${error}`);
    }
  }

  // Processing Operations
  async startProcessing(
    vocabularyIds: number[], 
    options: ProcessingOptions = {}
  ): Promise<{ taskId: string; status: string; itemCount: number }> {
    await this.ensureInitialized();

    try {
      return await this.bridge.execute('start_processing', { vocabularyIds, options });
    } catch (error) {
      throw new Error(`Failed to start processing: ${error}`);
    }
  }

  async getProcessingStatus(taskId: string): Promise<ProcessingStatus> {
    await this.ensureInitialized();

    try {
      return await this.bridge.execute('get_processing_status', { taskId });
    } catch (error) {
      throw new Error(`Failed to get processing status: ${error}`);
    }
  }

  async pauseProcessing(taskId: string): Promise<boolean> {
    await this.ensureInitialized();

    try {
      const result = await this.bridge.execute('pause_processing', { taskId });
      return result.success;
    } catch (error) {
      throw new Error(`Failed to pause processing: ${error}`);
    }
  }

  async resumeProcessing(taskId: string): Promise<boolean> {
    await this.ensureInitialized();

    try {
      const result = await this.bridge.execute('resume_processing', { taskId });
      return result.success;
    } catch (error) {
      throw new Error(`Failed to resume processing: ${error}`);
    }
  }

  async cancelProcessing(taskId: string): Promise<boolean> {
    await this.ensureInitialized();

    try {
      const result = await this.bridge.execute('cancel_processing', { taskId });
      return result.success;
    } catch (error) {
      throw new Error(`Failed to cancel processing: ${error}`);
    }
  }

  // System Operations
  async getSystemStats(): Promise<SystemStats> {
    await this.ensureInitialized();

    try {
      return await this.bridge.getSystemStats();
    } catch (error) {
      throw new Error(`Failed to get system stats: ${error}`);
    }
  }

  async checkAPIHealth(): Promise<APIHealthCheck> {
    await this.ensureInitialized();

    try {
      return await this.bridge.execute('check_api_health');
    } catch (error) {
      throw new Error(`Failed to check API health: ${error}`);
    }
  }

  async clearCache(options: { olderThan?: number } = {}): Promise<{ cleared: number; freedSpace: string }> {
    await this.ensureInitialized();

    try {
      return await this.bridge.execute('clear_cache', options);
    } catch (error) {
      throw new Error(`Failed to clear cache: ${error}`);
    }
  }

  // Export Operations
  async exportFlashcards(
    vocabularyIds: number[], 
    options: ExportOptions
  ): Promise<{ filePath: string; cardCount: number; fileSize: string }> {
    await this.ensureInitialized();

    try {
      return await this.bridge.execute('export_flashcards', { vocabularyIds, options });
    } catch (error) {
      throw new Error(`Failed to export flashcards: ${error}`);
    }
  }

  async getExportPreview(
    vocabularyIds: number[], 
    options: { format: ExportOptions['format']; limit?: number }
  ): Promise<{ cards: any[]; total: number }> {
    await this.ensureInitialized();

    try {
      return await this.bridge.execute('get_export_preview', { vocabularyIds, options });
    } catch (error) {
      throw new Error(`Failed to get export preview: ${error}`);
    }
  }

  // Utility methods
  private async executeWithRetry<T>(
    command: string, 
    args: any, 
    options: RetryOptions = {}
  ): Promise<T> {
    const { retries = 0, retryDelay = 1000 } = options;
    let lastError: any;

    for (let i = 0; i <= retries; i++) {
      try {
        return await this.bridge.execute(command, args);
      } catch (error) {
        lastError = error;
        if (i < retries) {
          await new Promise(resolve => setTimeout(resolve, retryDelay));
        }
      }
    }

    throw lastError;
  }

  async shutdown(): Promise<void> {
    try {
      await this.bridge.shutdown();
    } catch (error) {
      // Log but don't throw - best effort shutdown
      console.error('Error during Python service shutdown:', error);
    }
    this.initialized = false;
  }

  // Additional methods needed for DatabaseService integration
  async runCommand(module: string, command: string, args: any = {}): Promise<any> {
    await this.ensureInitialized();
    return this.bridge.execute(`${module}.${command}`, args);
  }

  async processVocabulary(options: any): Promise<any> {
    await this.ensureInitialized();
    return this.bridge.execute('process_vocabulary', options);
  }

  async processBatch(vocabularyIds: number[]): Promise<any> {
    await this.ensureInitialized();
    return this.bridge.execute('process_batch', { vocabularyIds });
  }

  async regenerateFlashcard(id: number, stage: string): Promise<any> {
    await this.ensureInitialized();
    return this.bridge.execute('regenerate_flashcard', { id, stage });
  }

  async getCacheStats(): Promise<any> {
    await this.ensureInitialized();
    return this.bridge.execute('get_cache_stats');
  }

  async verifyCache(): Promise<any> {
    await this.ensureInitialized();
    return this.bridge.execute('verify_cache');
  }

  async getPythonVersion(): Promise<string> {
    await this.ensureInitialized();
    const result = await this.bridge.execute('get_version');
    return result.python;
  }

  async getPipelineVersion(): Promise<string> {
    await this.ensureInitialized();
    const result = await this.bridge.execute('get_version');
    return result.pipeline;
  }

  async importVocabulary(content: string, format: string): Promise<any> {
    await this.ensureInitialized();
    return this.bridge.execute('import_vocabulary_content', { content, format });
  }

  async getProcessingStatus(): Promise<any> {
    await this.ensureInitialized();
    return this.bridge.execute('get_all_processing_status');
  }
}