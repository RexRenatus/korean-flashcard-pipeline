// Shared types between main and renderer processes

export interface VocabularyItem {
  id: number;
  korean: string;
  english?: string;
  romanization?: string;
  hanja?: string;
  type?: string;
  category?: string;
  subcategory?: string;
  difficultyLevel?: number;
  frequencyRank?: number;
  sourceReference?: string;
  notes?: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ProcessingTask {
  id: string;
  taskId: string;
  vocabularyId: number;
  taskType: 'stage1' | 'stage2' | 'full_pipeline';
  priority: number;
  status: 'pending' | 'queued' | 'processing' | 'completed' | 'failed';
  retryCount: number;
  maxRetries: number;
  scheduledAt?: string;
  startedAt?: string;
  completedAt?: string;
  createdAt: string;
}

export interface Flashcard {
  id: number;
  vocabularyId: number;
  taskId: string;
  cardNumber: number;
  deckName: string;
  frontContent: string;
  backContent: string;
  pronunciationGuide?: string;
  exampleSentence?: string;
  exampleTranslation?: string;
  grammarNotes?: string;
  culturalNotes?: string;
  mnemonics?: string;
  difficultyRating: number;
  tags?: string[];
  honorificLevel?: string;
  qualityScore: number;
  isPublished: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface SystemStats {
  totalWords: number;
  processedWords: number;
  pendingWords: number;
  failedWords: number;
  cacheHitRate: number;
  averageProcessingTime: number;
  apiHealth: 'healthy' | 'degraded' | 'error';
  lastSync: string;
}

export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'error';

export interface NotificationItem {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  message: string;
  timestamp: string;
  dismissible?: boolean;
  action?: {
    label: string;
    handler: () => void;
  };
}

export interface ImportResult {
  success: boolean;
  imported: number;
  duplicates: number;
  errors: number;
  details: string[];
}

export interface ExportOptions {
  format: 'tsv' | 'anki' | 'json' | 'pdf';
  deckName?: string;
  includeExamples?: boolean;
  includeGrammar?: boolean;
  includeCultural?: boolean;
  qualityThreshold?: number;
}

export interface ProcessingProgress {
  taskId: string;
  stage: number;
  progress: number;
  message: string;
  estimatedTimeRemaining?: number;
}

export interface APIError {
  code: string;
  message: string;
  details?: any;
  timestamp: string;
}

// IPC Channel names
export const IPC_CHANNELS = {
  // Database operations
  DB_GET_VOCABULARY: 'db:get-vocabulary',
  DB_ADD_VOCABULARY: 'db:add-vocabulary',
  DB_UPDATE_VOCABULARY: 'db:update-vocabulary',
  DB_DELETE_VOCABULARY: 'db:delete-vocabulary',
  DB_GET_STATS: 'db:get-stats',
  
  // Processing operations
  PROCESS_START: 'process:start',
  PROCESS_PAUSE: 'process:pause',
  PROCESS_RESUME: 'process:resume',
  PROCESS_CANCEL: 'process:cancel',
  PROCESS_STATUS: 'process:status',
  PROCESS_PROGRESS: 'process:progress',
  
  // Import/Export operations
  IMPORT_FILE: 'import:file',
  EXPORT_FLASHCARDS: 'export:flashcards',
  
  // Settings
  SETTINGS_GET: 'settings:get',
  SETTINGS_SET: 'settings:set',
  
  // System
  SYSTEM_HEALTH: 'system:health',
  SYSTEM_SYNC: 'system:sync',
  
  // Window events
  WINDOW_MINIMIZE: 'window:minimize',
  WINDOW_MAXIMIZE: 'window:maximize',
  WINDOW_CLOSE: 'window:close'
} as const;

export type IPCChannel = typeof IPC_CHANNELS[keyof typeof IPC_CHANNELS];