export const IPC_CHANNELS = {
  // System
  SYSTEM_GET_STATS: 'system:get-stats',
  SYSTEM_GET_VERSION: 'system:get-version',
  
  // Database - Vocabulary
  DB_GET_VOCABULARY: 'db:get-vocabulary',
  DB_ADD_VOCABULARY: 'db:add-vocabulary',
  DB_UPDATE_VOCABULARY: 'db:update-vocabulary',
  DB_DELETE_VOCABULARY: 'db:delete-vocabulary',
  DB_DELETE_VOCABULARY_BATCH: 'db:delete-vocabulary-batch',
  DB_IMPORT_VOCABULARY: 'db:import-vocabulary',
  
  // Database - Flashcards
  DB_GET_FLASHCARDS: 'db:get-flashcards',
  DB_DELETE_FLASHCARD: 'db:delete-flashcard',
  DB_DELETE_FLASHCARDS: 'db:delete-flashcards',
  DB_EXPORT_FLASHCARDS: 'db:export-flashcards',
  
  // Processing
  PROCESS_VOCABULARY: 'process:vocabulary',
  PROCESS_BATCH: 'process:batch',
  PROCESS_GET_STATUS: 'process:get-status',
  PROCESS_CANCEL: 'process:cancel',
  PROCESS_REGENERATE: 'process:regenerate',
  
  // Configuration
  CONFIG_LOAD: 'config:load',
  CONFIG_SAVE: 'config:save',
  CONFIG_UPDATE: 'config:update',
  CONFIG_RESET: 'config:reset',
  
  // Cache
  CACHE_GET_STATS: 'cache:get-stats',
  CACHE_CLEAR: 'cache:clear',
  CACHE_VERIFY: 'cache:verify',
  
  // Favorites
  FAVORITES_TOGGLE: 'favorites:toggle',
  FAVORITES_GET: 'favorites:get',
  
  // WebSocket events
  WS_PROCESSING_UPDATE: 'ws:processing-update',
  WS_SYSTEM_UPDATE: 'ws:system-update',
} as const;

export const PROCESSING_STATUS = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
} as const;

export const STAGE_TYPES = {
  STAGE1: 'stage1',
  STAGE2: 'stage2',
  BOTH: 'both',
} as const;

export const EXPORT_FORMATS = {
  JSON: 'json',
  CSV: 'csv',
  ANKI: 'anki',
} as const;

export const LOG_LEVELS = {
  DEBUG: 'debug',
  INFO: 'info',
  WARNING: 'warning',
  ERROR: 'error',
} as const;