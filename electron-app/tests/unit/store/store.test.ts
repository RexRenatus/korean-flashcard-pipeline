import { configureStore } from '@reduxjs/toolkit';
import { store, RootState, AppDispatch } from '@/renderer/store';
import { 
  vocabularySlice, 
  addVocabularyItem, 
  updateVocabularyItem,
  deleteVocabularyItems,
  setVocabularyList 
} from '@/renderer/store/vocabularySlice';
import {
  processingSlice,
  startProcessing,
  updateProcessingProgress,
  completeProcessing,
  failProcessing
} from '@/renderer/store/processingSlice';
import {
  systemSlice,
  updateSystemStats,
  setAPIHealth,
  setConnectionStatus
} from '@/renderer/store/systemSlice';
import { VocabularyItem, SystemStats } from '@/shared/types';

describe('Redux Store', () => {
  describe('Store Configuration', () => {
    it('should have the correct initial state', () => {
      const state = store.getState();
      
      expect(state).toHaveProperty('vocabulary');
      expect(state).toHaveProperty('processing');
      expect(state).toHaveProperty('system');
    });

    it('should handle actions correctly', () => {
      const testStore = configureStore({
        reducer: {
          vocabulary: vocabularySlice.reducer,
          processing: processingSlice.reducer,
          system: systemSlice.reducer
        }
      });

      // Dispatch an action
      testStore.dispatch(setConnectionStatus('connected'));
      
      expect(testStore.getState().system.connectionStatus).toBe('connected');
    });
  });

  describe('Vocabulary Slice', () => {
    let testStore: ReturnType<typeof configureStore>;

    beforeEach(() => {
      testStore = configureStore({
        reducer: {
          vocabulary: vocabularySlice.reducer
        }
      });
    });

    it('should have correct initial state', () => {
      const state = testStore.getState().vocabulary;
      
      expect(state).toEqual({
        items: [],
        loading: false,
        error: null,
        filter: '',
        sort: { field: 'createdAt', order: 'desc' },
        pagination: { page: 1, pageSize: 50, total: 0 }
      });
    });

    it('should handle adding vocabulary items', () => {
      const newItem: VocabularyItem = {
        id: 1,
        korean: '안녕하세요',
        english: 'Hello',
        isActive: true,
        createdAt: '2024-01-01',
        updatedAt: '2024-01-01'
      };

      testStore.dispatch(addVocabularyItem(newItem));
      
      const state = testStore.getState().vocabulary;
      expect(state.items).toHaveLength(1);
      expect(state.items[0]).toEqual(newItem);
    });

    it('should handle updating vocabulary items', () => {
      const item: VocabularyItem = {
        id: 1,
        korean: '안녕',
        english: 'Hi',
        isActive: true,
        createdAt: '2024-01-01',
        updatedAt: '2024-01-01'
      };

      testStore.dispatch(addVocabularyItem(item));
      testStore.dispatch(updateVocabularyItem({
        id: 1,
        changes: { english: 'Hello (informal)' }
      }));

      const state = testStore.getState().vocabulary;
      expect(state.items[0].english).toBe('Hello (informal)');
    });

    it('should handle deleting vocabulary items', () => {
      const items: VocabularyItem[] = [
        { id: 1, korean: '안녕', isActive: true, createdAt: '2024-01-01', updatedAt: '2024-01-01' },
        { id: 2, korean: '감사', isActive: true, createdAt: '2024-01-01', updatedAt: '2024-01-01' },
        { id: 3, korean: '사랑', isActive: true, createdAt: '2024-01-01', updatedAt: '2024-01-01' }
      ];

      testStore.dispatch(setVocabularyList({ items, total: 3 }));
      testStore.dispatch(deleteVocabularyItems([1, 3]));

      const state = testStore.getState().vocabulary;
      expect(state.items).toHaveLength(1);
      expect(state.items[0].id).toBe(2);
    });

    it('should handle pagination', () => {
      testStore.dispatch(setVocabularyList({
        items: [],
        total: 100,
        page: 2,
        pageSize: 25
      }));

      const state = testStore.getState().vocabulary;
      expect(state.pagination).toEqual({
        page: 2,
        pageSize: 25,
        total: 100
      });
    });
  });

  describe('Processing Slice', () => {
    let testStore: ReturnType<typeof configureStore>;

    beforeEach(() => {
      testStore = configureStore({
        reducer: {
          processing: processingSlice.reducer
        }
      });
    });

    it('should have correct initial state', () => {
      const state = testStore.getState().processing;
      
      expect(state).toEqual({
        tasks: {},
        activeTaskId: null,
        queue: []
      });
    });

    it('should handle starting processing', () => {
      testStore.dispatch(startProcessing({
        taskId: 'task-123',
        vocabularyIds: [1, 2, 3],
        totalItems: 3
      }));

      const state = testStore.getState().processing;
      expect(state.activeTaskId).toBe('task-123');
      expect(state.tasks['task-123']).toEqual({
        id: 'task-123',
        status: 'processing',
        progress: 0,
        totalItems: 3,
        processedItems: 0,
        startedAt: expect.any(String),
        vocabularyIds: [1, 2, 3]
      });
    });

    it('should handle progress updates', () => {
      testStore.dispatch(startProcessing({
        taskId: 'task-123',
        vocabularyIds: [1, 2, 3],
        totalItems: 3
      }));

      testStore.dispatch(updateProcessingProgress({
        taskId: 'task-123',
        progress: 0.5,
        processedItems: 2,
        currentStage: 'stage1',
        message: 'Processing item 2 of 3'
      }));

      const state = testStore.getState().processing;
      const task = state.tasks['task-123'];
      
      expect(task.progress).toBe(0.5);
      expect(task.processedItems).toBe(2);
      expect(task.currentStage).toBe('stage1');
      expect(task.message).toBe('Processing item 2 of 3');
    });

    it('should handle task completion', () => {
      testStore.dispatch(startProcessing({
        taskId: 'task-123',
        vocabularyIds: [1, 2, 3],
        totalItems: 3
      }));

      testStore.dispatch(completeProcessing({ taskId: 'task-123' }));

      const state = testStore.getState().processing;
      const task = state.tasks['task-123'];
      
      expect(task.status).toBe('completed');
      expect(task.progress).toBe(1);
      expect(task.completedAt).toBeDefined();
      expect(state.activeTaskId).toBeNull();
    });

    it('should handle task failure', () => {
      testStore.dispatch(startProcessing({
        taskId: 'task-123',
        vocabularyIds: [1, 2, 3],
        totalItems: 3
      }));

      testStore.dispatch(failProcessing({
        taskId: 'task-123',
        error: 'API rate limit exceeded'
      }));

      const state = testStore.getState().processing;
      const task = state.tasks['task-123'];
      
      expect(task.status).toBe('failed');
      expect(task.error).toBe('API rate limit exceeded');
      expect(state.activeTaskId).toBeNull();
    });
  });

  describe('System Slice', () => {
    let testStore: ReturnType<typeof configureStore>;

    beforeEach(() => {
      testStore = configureStore({
        reducer: {
          system: systemSlice.reducer
        }
      });
    });

    it('should have correct initial state', () => {
      const state = testStore.getState().system;
      
      expect(state).toEqual({
        stats: {
          totalWords: 0,
          processedWords: 0,
          pendingWords: 0,
          failedWords: 0,
          cacheHitRate: 0,
          averageProcessingTime: 0,
          apiHealth: 'healthy',
          lastSync: ''
        },
        connectionStatus: 'disconnected',
        notifications: []
      });
    });

    it('should handle system stats updates', () => {
      const stats: SystemStats = {
        totalWords: 1000,
        processedWords: 800,
        pendingWords: 150,
        failedWords: 50,
        cacheHitRate: 0.85,
        averageProcessingTime: 1.2,
        apiHealth: 'healthy',
        lastSync: '2024-01-01T00:00:00Z'
      };

      testStore.dispatch(updateSystemStats(stats));

      const state = testStore.getState().system;
      expect(state.stats).toEqual(stats);
    });

    it('should handle API health updates', () => {
      testStore.dispatch(setAPIHealth('degraded'));

      const state = testStore.getState().system;
      expect(state.stats.apiHealth).toBe('degraded');
    });

    it('should handle connection status changes', () => {
      testStore.dispatch(setConnectionStatus('connected'));

      const state = testStore.getState().system;
      expect(state.connectionStatus).toBe('connected');
    });
  });

  describe('Async Actions', () => {
    it('should handle async vocabulary loading', async () => {
      // This would test thunk actions
      expect(true).toBe(true); // Placeholder
    });
  });
});