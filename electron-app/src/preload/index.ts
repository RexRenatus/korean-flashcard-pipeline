import { contextBridge, ipcRenderer } from 'electron';
import { IPC_CHANNELS } from '../shared/constants';

// Whitelist of allowed channels
const allowedChannels = Object.values(IPC_CHANNELS);

// Validate channel is allowed
function isAllowedChannel(channel: string): boolean {
  return allowedChannels.includes(channel as any);
}

// Expose protected methods to the renderer process
contextBridge.exposeInMainWorld('electronAPI', {
  // Invoke method for two-way communication
  invoke: async (channel: string, ...args: any[]) => {
    if (!isAllowedChannel(channel)) {
      throw new Error(`Channel ${channel} is not allowed`);
    }
    return ipcRenderer.invoke(channel, ...args);
  },

  // Send method for one-way communication
  send: (channel: string, ...args: any[]) => {
    if (!isAllowedChannel(channel)) {
      throw new Error(`Channel ${channel} is not allowed`);
    }
    ipcRenderer.send(channel, ...args);
  },

  // Listen for events from main process
  on: (channel: string, callback: (...args: any[]) => void) => {
    if (!isAllowedChannel(channel)) {
      throw new Error(`Channel ${channel} is not allowed`);
    }
    
    // Wrap the callback to ensure security
    const subscription = (_event: Electron.IpcRendererEvent, ...args: any[]) => {
      callback(...args);
    };
    
    ipcRenderer.on(channel, subscription);
    
    // Return unsubscribe function
    return () => {
      ipcRenderer.off(channel, subscription);
    };
  },

  // Listen for one-time events
  once: (channel: string, callback: (...args: any[]) => void) => {
    if (!isAllowedChannel(channel)) {
      throw new Error(`Channel ${channel} is not allowed`);
    }
    
    ipcRenderer.once(channel, (_event, ...args) => {
      callback(...args);
    });
  },

  // Remove all listeners for a channel
  removeAllListeners: (channel: string) => {
    if (!isAllowedChannel(channel)) {
      throw new Error(`Channel ${channel} is not allowed`);
    }
    ipcRenderer.removeAllListeners(channel);
  },

  // Convenience methods for common operations
  // Database - Vocabulary
  getVocabulary: (options?: any) => ipcRenderer.invoke(IPC_CHANNELS.DB_GET_VOCABULARY, options),
  addVocabulary: (item: any) => ipcRenderer.invoke(IPC_CHANNELS.DB_ADD_VOCABULARY, item),
  updateVocabulary: (data: any) => ipcRenderer.invoke(IPC_CHANNELS.DB_UPDATE_VOCABULARY, data),
  deleteVocabulary: (id: number) => ipcRenderer.invoke(IPC_CHANNELS.DB_DELETE_VOCABULARY, id),
  deleteVocabularyBatch: (ids: number[]) => ipcRenderer.invoke(IPC_CHANNELS.DB_DELETE_VOCABULARY_BATCH, ids),
  importVocabulary: (data: any) => ipcRenderer.invoke(IPC_CHANNELS.DB_IMPORT_VOCABULARY, data),
  
  // Database - Flashcards
  getFlashcards: (options?: any) => ipcRenderer.invoke(IPC_CHANNELS.DB_GET_FLASHCARDS, options),
  deleteFlashcard: (id: number) => ipcRenderer.invoke(IPC_CHANNELS.DB_DELETE_FLASHCARD, id),
  deleteFlashcards: (ids: number[]) => ipcRenderer.invoke(IPC_CHANNELS.DB_DELETE_FLASHCARDS, ids),
  exportFlashcards: (options: any) => ipcRenderer.invoke(IPC_CHANNELS.DB_EXPORT_FLASHCARDS, options),
  
  // Processing
  processVocabulary: (options: any) => ipcRenderer.invoke(IPC_CHANNELS.PROCESS_VOCABULARY, options),
  processBatch: (vocabularyIds: number[]) => ipcRenderer.invoke(IPC_CHANNELS.PROCESS_BATCH, vocabularyIds),
  getProcessingStatus: () => ipcRenderer.invoke(IPC_CHANNELS.PROCESS_GET_STATUS),
  cancelProcessing: (taskId: string) => ipcRenderer.invoke(IPC_CHANNELS.PROCESS_CANCEL, taskId),
  regenerateFlashcard: (data: any) => ipcRenderer.invoke(IPC_CHANNELS.PROCESS_REGENERATE, data),
  
  // Configuration
  loadConfig: () => ipcRenderer.invoke(IPC_CHANNELS.CONFIG_LOAD),
  saveConfig: (config: any) => ipcRenderer.invoke(IPC_CHANNELS.CONFIG_SAVE, config),
  updateConfig: (updates: any) => ipcRenderer.invoke(IPC_CHANNELS.CONFIG_UPDATE, updates),
  resetConfig: () => ipcRenderer.invoke(IPC_CHANNELS.CONFIG_RESET),
  
  // Cache
  getCacheStats: () => ipcRenderer.invoke(IPC_CHANNELS.CACHE_GET_STATS),
  clearCache: (options?: any) => ipcRenderer.invoke(IPC_CHANNELS.CACHE_CLEAR, options),
  verifyCache: () => ipcRenderer.invoke(IPC_CHANNELS.CACHE_VERIFY),
  
  // System
  getSystemStats: () => ipcRenderer.invoke(IPC_CHANNELS.SYSTEM_GET_STATS),
  getVersion: () => ipcRenderer.invoke(IPC_CHANNELS.SYSTEM_GET_VERSION),
  
  // Favorites
  toggleFavorite: (data: any) => ipcRenderer.invoke(IPC_CHANNELS.FAVORITES_TOGGLE, data),
  getFavorites: (type: string) => ipcRenderer.invoke(IPC_CHANNELS.FAVORITES_GET, type),
  
  // Dialogs
  openFile: (options?: any) => ipcRenderer.invoke('dialog:openFile', options),
  saveFile: (options?: any) => ipcRenderer.invoke('dialog:saveFile', options),
  
  // Shell
  openExternal: (url: string) => ipcRenderer.invoke('shell:openExternal', url),
  showItemInFolder: (path: string) => ipcRenderer.invoke('shell:showItemInFolder', path)
});

// Type augmentation for window object
declare global {
  interface Window {
    electronAPI: {
      invoke: (channel: string, ...args: any[]) => Promise<any>;
      send: (channel: string, ...args: any[]) => void;
      on: (channel: string, callback: (...args: any[]) => void) => () => void;
      once: (channel: string, callback: (...args: any[]) => void) => void;
      removeAllListeners: (channel: string) => void;
      
      // Database - Vocabulary
      getVocabulary: (options?: any) => Promise<any>;
      addVocabulary: (item: any) => Promise<any>;
      updateVocabulary: (data: any) => Promise<any>;
      deleteVocabulary: (id: number) => Promise<any>;
      deleteVocabularyBatch: (ids: number[]) => Promise<any>;
      importVocabulary: (data: any) => Promise<any>;
      
      // Database - Flashcards
      getFlashcards: (options?: any) => Promise<any>;
      deleteFlashcard: (id: number) => Promise<any>;
      deleteFlashcards: (ids: number[]) => Promise<any>;
      exportFlashcards: (options: any) => Promise<any>;
      
      // Processing
      processVocabulary: (options: any) => Promise<any>;
      processBatch: (vocabularyIds: number[]) => Promise<any>;
      getProcessingStatus: () => Promise<any>;
      cancelProcessing: (taskId: string) => Promise<any>;
      regenerateFlashcard: (data: any) => Promise<any>;
      
      // Configuration
      loadConfig: () => Promise<any>;
      saveConfig: (config: any) => Promise<any>;
      updateConfig: (updates: any) => Promise<any>;
      resetConfig: () => Promise<any>;
      
      // Cache
      getCacheStats: () => Promise<any>;
      clearCache: (options?: any) => Promise<any>;
      verifyCache: () => Promise<any>;
      
      // System
      getSystemStats: () => Promise<any>;
      getVersion: () => Promise<any>;
      
      // Favorites
      toggleFavorite: (data: any) => Promise<any>;
      getFavorites: (type: string) => Promise<any>;
      
      // Dialogs
      openFile: (options?: any) => Promise<any>;
      saveFile: (options?: any) => Promise<any>;
      
      // Shell
      openExternal: (url: string) => Promise<any>;
      showItemInFolder: (path: string) => Promise<any>;
    };
  }
}