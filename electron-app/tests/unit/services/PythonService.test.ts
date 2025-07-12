import { PythonService } from '@/main/services/PythonService';
import { IPCBridge } from '@/main/services/IPCBridge';
import { VocabularyItem, SystemStats, ImportResult } from '@/shared/types';

// Mock IPCBridge
jest.mock('@/main/services/IPCBridge');

describe('PythonService', () => {
  let service: PythonService;
  let mockBridge: jest.Mocked<IPCBridge>;

  beforeEach(() => {
    // Create mock bridge
    mockBridge = {
      initialize: jest.fn().mockResolvedValue(true),
      isReady: jest.fn().mockReturnValue(true),
      execute: jest.fn(),
      processVocabulary: jest.fn(),
      getVocabularyList: jest.fn(),
      getSystemStats: jest.fn(),
      shutdown: jest.fn().mockResolvedValue(undefined)
    } as any;

    // Mock the constructor
    (IPCBridge as jest.MockedClass<typeof IPCBridge>).mockImplementation(() => mockBridge);

    service = new PythonService();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('initialization', () => {
    it('should initialize the Python bridge on first use', async () => {
      await service.ensureInitialized();

      expect(mockBridge.initialize).toHaveBeenCalledTimes(1);
      expect(mockBridge.initialize).toHaveBeenCalledWith();
    });

    it('should not reinitialize if already initialized', async () => {
      await service.ensureInitialized();
      await service.ensureInitialized();

      expect(mockBridge.initialize).toHaveBeenCalledTimes(1);
    });

    it('should handle initialization failures', async () => {
      mockBridge.initialize.mockRejectedValueOnce(new Error('Init failed'));
      mockBridge.isReady.mockReturnValue(false);

      await expect(service.ensureInitialized()).rejects.toThrow('Failed to initialize Python service');
    });
  });

  describe('vocabulary operations', () => {
    beforeEach(async () => {
      await service.ensureInitialized();
    });

    it('should get vocabulary list with pagination', async () => {
      const mockVocabulary: VocabularyItem[] = [
        {
          id: 1,
          korean: '안녕',
          english: 'hello',
          isActive: true,
          createdAt: '2024-01-01',
          updatedAt: '2024-01-01'
        }
      ];

      mockBridge.execute.mockResolvedValueOnce({
        items: mockVocabulary,
        total: 100,
        page: 1,
        pageSize: 10
      });

      const result = await service.getVocabularyList({
        page: 1,
        pageSize: 10,
        filter: 'active'
      });

      expect(result.items).toEqual(mockVocabulary);
      expect(result.total).toBe(100);
      expect(mockBridge.execute).toHaveBeenCalledWith('get_vocabulary_list', {
        page: 1,
        pageSize: 10,
        filter: 'active'
      });
    });

    it('should add new vocabulary items', async () => {
      const newItem = {
        korean: '새로운',
        english: 'new',
        type: 'adjective'
      };

      mockBridge.execute.mockResolvedValueOnce({
        id: 123,
        ...newItem,
        isActive: true,
        createdAt: '2024-01-01',
        updatedAt: '2024-01-01'
      });

      const result = await service.addVocabulary(newItem);

      expect(result.id).toBe(123);
      expect(result.korean).toBe('새로운');
      expect(mockBridge.execute).toHaveBeenCalledWith('add_vocabulary', newItem);
    });

    it('should update existing vocabulary', async () => {
      const updates = {
        id: 1,
        english: 'hi',
        notes: 'Informal greeting'
      };

      mockBridge.execute.mockResolvedValueOnce({
        ...updates,
        korean: '안녕',
        isActive: true,
        createdAt: '2024-01-01',
        updatedAt: '2024-01-02'
      });

      const result = await service.updateVocabulary(1, updates);

      expect(result.english).toBe('hi');
      expect(result.notes).toBe('Informal greeting');
      expect(mockBridge.execute).toHaveBeenCalledWith('update_vocabulary', {
        id: 1,
        updates
      });
    });

    it('should delete vocabulary items', async () => {
      mockBridge.execute.mockResolvedValueOnce({ success: true });

      const result = await service.deleteVocabulary([1, 2, 3]);

      expect(result).toBe(true);
      expect(mockBridge.execute).toHaveBeenCalledWith('delete_vocabulary', {
        ids: [1, 2, 3]
      });
    });
  });

  describe('import operations', () => {
    beforeEach(async () => {
      await service.ensureInitialized();
    });

    it('should import vocabulary from CSV file', async () => {
      const filePath = '/path/to/vocabulary.csv';
      const mockResult: ImportResult = {
        success: true,
        imported: 100,
        duplicates: 5,
        errors: 2,
        details: ['Line 10: Invalid format', 'Line 25: Missing required field']
      };

      mockBridge.execute.mockResolvedValueOnce(mockResult);

      const result = await service.importVocabulary(filePath, 'csv');

      expect(result).toEqual(mockResult);
      expect(mockBridge.execute).toHaveBeenCalledWith('import_vocabulary', {
        filePath,
        format: 'csv'
      });
    });

    it('should validate import data before processing', async () => {
      const data = [
        { korean: '안녕', english: 'hello' },
        { korean: '감사', english: 'thanks' }
      ];

      mockBridge.execute.mockResolvedValueOnce({
        valid: true,
        errors: []
      });

      const result = await service.validateImportData(data);

      expect(result.valid).toBe(true);
      expect(mockBridge.execute).toHaveBeenCalledWith('validate_import', { data });
    });

    it('should handle import validation errors', async () => {
      const data = [
        { korean: '', english: 'hello' }, // Invalid: empty Korean
        { korean: '감사', english: 'thanks' }
      ];

      mockBridge.execute.mockResolvedValueOnce({
        valid: false,
        errors: ['Row 1: Korean field is required']
      });

      const result = await service.validateImportData(data);

      expect(result.valid).toBe(false);
      expect(result.errors).toHaveLength(1);
    });
  });

  describe('processing operations', () => {
    beforeEach(async () => {
      await service.ensureInitialized();
    });

    it('should start vocabulary processing', async () => {
      const vocabularyIds = [1, 2, 3];
      
      mockBridge.execute.mockResolvedValueOnce({
        taskId: 'task-123',
        status: 'queued',
        itemCount: 3
      });

      const result = await service.startProcessing(vocabularyIds, {
        priority: 'high',
        stage: 'full_pipeline'
      });

      expect(result.taskId).toBe('task-123');
      expect(mockBridge.execute).toHaveBeenCalledWith('start_processing', {
        vocabularyIds,
        options: {
          priority: 'high',
          stage: 'full_pipeline'
        }
      });
    });

    it('should get processing status', async () => {
      mockBridge.execute.mockResolvedValueOnce({
        taskId: 'task-123',
        status: 'processing',
        progress: 0.45,
        processed: 45,
        total: 100,
        currentStage: 'stage1',
        estimatedTimeRemaining: 120
      });

      const status = await service.getProcessingStatus('task-123');

      expect(status.progress).toBe(0.45);
      expect(status.currentStage).toBe('stage1');
      expect(mockBridge.execute).toHaveBeenCalledWith('get_processing_status', {
        taskId: 'task-123'
      });
    });

    it('should pause processing', async () => {
      mockBridge.execute.mockResolvedValueOnce({ success: true });

      const result = await service.pauseProcessing('task-123');

      expect(result).toBe(true);
      expect(mockBridge.execute).toHaveBeenCalledWith('pause_processing', {
        taskId: 'task-123'
      });
    });

    it('should resume processing', async () => {
      mockBridge.execute.mockResolvedValueOnce({ success: true });

      const result = await service.resumeProcessing('task-123');

      expect(result).toBe(true);
      expect(mockBridge.execute).toHaveBeenCalledWith('resume_processing', {
        taskId: 'task-123'
      });
    });

    it('should cancel processing', async () => {
      mockBridge.execute.mockResolvedValueOnce({ success: true });

      const result = await service.cancelProcessing('task-123');

      expect(result).toBe(true);
      expect(mockBridge.execute).toHaveBeenCalledWith('cancel_processing', {
        taskId: 'task-123'
      });
    });
  });

  describe('system operations', () => {
    beforeEach(async () => {
      await service.ensureInitialized();
    });

    it('should get system statistics', async () => {
      const mockStats: SystemStats = {
        totalWords: 1000,
        processedWords: 800,
        pendingWords: 150,
        failedWords: 50,
        cacheHitRate: 0.85,
        averageProcessingTime: 1.2,
        apiHealth: 'healthy',
        lastSync: '2024-01-01T00:00:00Z'
      };

      mockBridge.getSystemStats.mockResolvedValueOnce(mockStats);

      const stats = await service.getSystemStats();

      expect(stats).toEqual(mockStats);
      expect(mockBridge.getSystemStats).toHaveBeenCalled();
    });

    it('should check API health', async () => {
      mockBridge.execute.mockResolvedValueOnce({
        status: 'healthy',
        latency: 45,
        rateLimit: {
          remaining: 950,
          reset: '2024-01-01T01:00:00Z'
        }
      });

      const health = await service.checkAPIHealth();

      expect(health.status).toBe('healthy');
      expect(health.latency).toBe(45);
      expect(mockBridge.execute).toHaveBeenCalledWith('check_api_health');
    });

    it('should clear cache', async () => {
      mockBridge.execute.mockResolvedValueOnce({
        cleared: 1234,
        freedSpace: '125MB'
      });

      const result = await service.clearCache({ 
        olderThan: 7 * 24 * 60 * 60 * 1000 // 7 days
      });

      expect(result.cleared).toBe(1234);
      expect(mockBridge.execute).toHaveBeenCalledWith('clear_cache', {
        olderThan: 7 * 24 * 60 * 60 * 1000
      });
    });
  });

  describe('export operations', () => {
    beforeEach(async () => {
      await service.ensureInitialized();
    });

    it('should export flashcards in various formats', async () => {
      const exportOptions = {
        format: 'anki' as const,
        deckName: 'Korean Vocabulary',
        includeExamples: true,
        qualityThreshold: 0.8
      };

      mockBridge.execute.mockResolvedValueOnce({
        filePath: '/tmp/korean_vocab.apkg',
        cardCount: 150,
        fileSize: '2.5MB'
      });

      const result = await service.exportFlashcards([1, 2, 3], exportOptions);

      expect(result.filePath).toContain('.apkg');
      expect(result.cardCount).toBe(150);
      expect(mockBridge.execute).toHaveBeenCalledWith('export_flashcards', {
        vocabularyIds: [1, 2, 3],
        options: exportOptions
      });
    });

    it('should generate export preview', async () => {
      mockBridge.execute.mockResolvedValueOnce({
        cards: [
          {
            front: '안녕하세요',
            back: 'Hello (formal)',
            examples: ['안녕하세요, 만나서 반갑습니다.']
          }
        ],
        total: 50
      });

      const preview = await service.getExportPreview([1], { 
        format: 'anki' as const,
        limit: 5 
      });

      expect(preview.cards).toHaveLength(1);
      expect(preview.total).toBe(50);
      expect(mockBridge.execute).toHaveBeenCalledWith('get_export_preview', {
        vocabularyIds: [1],
        options: { format: 'anki', limit: 5 }
      });
    });
  });

  describe('error handling', () => {
    beforeEach(async () => {
      await service.ensureInitialized();
    });

    it('should handle Python bridge errors gracefully', async () => {
      mockBridge.execute.mockRejectedValueOnce(new Error('Python process crashed'));

      await expect(service.getVocabularyList({})).rejects.toThrow('Failed to get vocabulary list');
    });

    it('should retry operations on transient failures', async () => {
      // First call fails, second succeeds
      mockBridge.execute
        .mockRejectedValueOnce(new Error('Temporary failure'))
        .mockResolvedValueOnce({ items: [], total: 0 });

      const result = await service.getVocabularyList({}, { retries: 1 });

      expect(result.items).toEqual([]);
      expect(mockBridge.execute).toHaveBeenCalledTimes(2);
    });

    it('should provide detailed error information', async () => {
      const detailedError = {
        code: 'VALIDATION_ERROR',
        message: 'Invalid vocabulary format',
        details: {
          field: 'korean',
          value: '',
          requirement: 'non-empty string'
        }
      };

      mockBridge.execute.mockRejectedValueOnce(detailedError);

      try {
        await service.addVocabulary({ korean: '', english: 'test' });
        fail('Should have thrown error');
      } catch (error: any) {
        expect(error.code).toBe('VALIDATION_ERROR');
        expect(error.details.field).toBe('korean');
      }
    });
  });

  describe('cleanup', () => {
    it('should properly shutdown the Python bridge', async () => {
      await service.ensureInitialized();
      await service.shutdown();

      expect(mockBridge.shutdown).toHaveBeenCalled();
    });

    it('should handle shutdown errors', async () => {
      await service.ensureInitialized();
      mockBridge.shutdown.mockRejectedValueOnce(new Error('Shutdown failed'));

      // Should not throw
      await expect(service.shutdown()).resolves.not.toThrow();
    });
  });
});