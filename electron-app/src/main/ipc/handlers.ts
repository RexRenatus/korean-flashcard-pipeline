import { ipcMain, dialog, shell } from 'electron';
import { promises as fs } from 'fs';
import path from 'path';
import { PythonService } from '../services/PythonService';
import { DatabaseService } from '../services/DatabaseService';
import { ConfigService } from '../services/ConfigService';
import { ExportService } from '../services/ExportService';
import { IPC_CHANNELS } from '../../shared/constants';

import { ProcessingService } from '../services/ProcessingService';

export function setupIPCHandlers(pythonService: PythonService, processingService?: ProcessingService) {
  const dbService = new DatabaseService();
  const configService = new ConfigService();
  const exportService = new ExportService();

  // System handlers
  ipcMain.handle(IPC_CHANNELS.SYSTEM_GET_STATS, async () => {
    return await pythonService.getSystemStats();
  });

  ipcMain.handle(IPC_CHANNELS.SYSTEM_GET_VERSION, async () => {
    const packageJson = require('../../../package.json');
    return {
      app: packageJson.version,
      python: await pythonService.getPythonVersion(),
      pipeline: await pythonService.getPipelineVersion(),
    };
  });

  // Database handlers - Vocabulary
  ipcMain.handle(IPC_CHANNELS.DB_GET_VOCABULARY, async (event, options) => {
    return await dbService.getVocabulary(options);
  });

  ipcMain.handle(IPC_CHANNELS.DB_ADD_VOCABULARY, async (event, data) => {
    return await dbService.addVocabulary(data);
  });

  ipcMain.handle(IPC_CHANNELS.DB_UPDATE_VOCABULARY, async (event, data) => {
    return await dbService.updateVocabulary(data.id, data);
  });

  ipcMain.handle(IPC_CHANNELS.DB_DELETE_VOCABULARY, async (event, id) => {
    return await dbService.deleteVocabulary(id);
  });

  ipcMain.handle(IPC_CHANNELS.DB_DELETE_VOCABULARY_BATCH, async (event, ids) => {
    return await dbService.deleteVocabularyBatch(ids);
  });

  ipcMain.handle(IPC_CHANNELS.DB_IMPORT_VOCABULARY, async (event, { filePath, format }) => {
    // If filePath is not provided, show file dialog
    if (!filePath) {
      const result = await dialog.showOpenDialog({
        properties: ['openFile'],
        filters: [
          { name: 'Vocabulary Files', extensions: ['csv', 'txt', 'json'] },
          { name: 'All Files', extensions: ['*'] }
        ]
      });
      
      if (result.canceled || !result.filePaths[0]) {
        throw new Error('Import cancelled');
      }
      
      filePath = result.filePaths[0];
      format = path.extname(filePath).slice(1) as any;
    }

    const content = await fs.readFile(filePath, 'utf-8');
    return await pythonService.importVocabulary(content, format);
  });

  // Database handlers - Flashcards
  ipcMain.handle(IPC_CHANNELS.DB_GET_FLASHCARDS, async (event, options) => {
    return await dbService.getFlashcards(options);
  });

  ipcMain.handle(IPC_CHANNELS.DB_DELETE_FLASHCARD, async (event, id) => {
    return await dbService.deleteFlashcard(id);
  });

  ipcMain.handle(IPC_CHANNELS.DB_DELETE_FLASHCARDS, async (event, ids) => {
    return await dbService.deleteFlashcardsBatch(ids);
  });

  ipcMain.handle(IPC_CHANNELS.DB_EXPORT_FLASHCARDS, async (event, options) => {
    const flashcards = await dbService.getFlashcards(options.filters);
    const exportPath = await exportService.exportFlashcards(flashcards.items, options);
    
    // Open the export location
    shell.showItemInFolder(exportPath);
    return { path: exportPath, count: flashcards.items.length };
  });

  // Processing handlers
  ipcMain.handle(IPC_CHANNELS.PROCESS_VOCABULARY, async (event, options) => {
    if (processingService) {
      // Use processing service for better progress tracking
      const task = await processingService.createTask(options.vocabularyIds, {
        stage: options.stage,
        priority: options.priority,
      });
      return { taskId: task.id, status: task.status };
    }
    return await pythonService.processVocabulary(options);
  });

  ipcMain.handle(IPC_CHANNELS.PROCESS_BATCH, async (event, vocabularyIds) => {
    if (processingService) {
      const task = await processingService.createTask(vocabularyIds);
      return { taskId: task.id, status: task.status };
    }
    return await pythonService.processBatch(vocabularyIds);
  });

  ipcMain.handle(IPC_CHANNELS.PROCESS_GET_STATUS, async () => {
    if (processingService) {
      return processingService.getQueueStatus();
    }
    return await pythonService.getProcessingStatus();
  });

  ipcMain.handle(IPC_CHANNELS.PROCESS_CANCEL, async (event, taskId) => {
    if (processingService) {
      return await processingService.cancelTask(taskId);
    }
    return await pythonService.cancelProcessing(taskId);
  });

  ipcMain.handle(IPC_CHANNELS.PROCESS_REGENERATE, async (event, { id, stage }) => {
    return await pythonService.regenerateFlashcard(id, stage);
  });

  // Additional processing handlers
  ipcMain.handle('processing:get-task', async (event, taskId) => {
    if (!processingService) return null;
    return processingService.getTask(taskId);
  });

  ipcMain.handle('processing:get-all-tasks', async () => {
    if (!processingService) return [];
    return processingService.getAllTasks();
  });

  ipcMain.handle('processing:clear-completed', async () => {
    if (!processingService) return 0;
    return processingService.clearCompletedTasks();
  });

  // Configuration handlers
  ipcMain.handle(IPC_CHANNELS.CONFIG_LOAD, async () => {
    return await configService.load();
  });

  ipcMain.handle(IPC_CHANNELS.CONFIG_SAVE, async (event, config) => {
    return await configService.save(config);
  });

  ipcMain.handle(IPC_CHANNELS.CONFIG_UPDATE, async (event, updates) => {
    return await configService.update(updates);
  });

  ipcMain.handle(IPC_CHANNELS.CONFIG_RESET, async () => {
    return await configService.reset();
  });

  // Cache handlers
  ipcMain.handle(IPC_CHANNELS.CACHE_GET_STATS, async () => {
    return await pythonService.getCacheStats();
  });

  ipcMain.handle(IPC_CHANNELS.CACHE_CLEAR, async (event, options) => {
    return await pythonService.clearCache(options);
  });

  ipcMain.handle(IPC_CHANNELS.CACHE_VERIFY, async () => {
    return await pythonService.verifyCache();
  });

  // Favorites handlers
  ipcMain.handle(IPC_CHANNELS.FAVORITES_TOGGLE, async (event, { type, id }) => {
    return await dbService.toggleFavorite(type, id);
  });

  ipcMain.handle(IPC_CHANNELS.FAVORITES_GET, async (event, type) => {
    return await dbService.getFavorites(type);
  });

  // File dialog handlers
  ipcMain.handle('dialog:openFile', async (event, options) => {
    const result = await dialog.showOpenDialog(options);
    return result;
  });

  ipcMain.handle('dialog:saveFile', async (event, options) => {
    const result = await dialog.showSaveDialog(options);
    return result;
  });

  // Shell handlers
  ipcMain.handle('shell:openExternal', async (event, url) => {
    await shell.openExternal(url);
  });

  ipcMain.handle('shell:showItemInFolder', async (event, path) => {
    shell.showItemInFolder(path);
  });
}