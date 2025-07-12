import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';

interface ProcessingTask {
  id: string;
  taskId: string; // For compatibility with backend
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number; // 0-100
  totalItems: number;
  processedItems: number;
  startedAt?: string;
  completedAt?: string;
  error?: string;
  vocabularyIds: number[];
  currentStage?: 'stage1' | 'stage2' | 'both';
  currentItem?: string;
  message?: string;
  priority?: 'low' | 'normal' | 'high';
  stats?: {
    total: number;
    processed: number;
    succeeded: number;
    failed: number;
    remainingTime?: number;
  };
}

interface ProcessingState {
  tasks: Record<string, ProcessingTask>;
  activeTaskId: string | null;
  queue: string[];
  activeTasks: ProcessingTask[];
  queuedTasks: ProcessingTask[];
  recentTasks: ProcessingTask[];
  loading: boolean;
  error: string | null;
}

const initialState: ProcessingState = {
  tasks: {},
  activeTaskId: null,
  queue: [],
  activeTasks: [],
  queuedTasks: [],
  recentTasks: [],
  loading: false,
  error: null,
};

// Async thunks
export const startProcessing = createAsyncThunk(
  'processing/start',
  async ({ vocabularyIds, options }: { vocabularyIds: number[]; options?: any }) => {
    const result = await window.electronAPI.processBatch(vocabularyIds);
    return result;
  }
);

export const pauseProcessing = createAsyncThunk(
  'processing/pause',
  async (taskId: string) => {
    // Implement pause via IPC
    return { taskId };
  }
);

export const resumeProcessing = createAsyncThunk(
  'processing/resume',
  async (taskId: string) => {
    // Implement resume via IPC
    return { taskId };
  }
);

export const cancelProcessing = createAsyncThunk(
  'processing/cancel',
  async (taskId: string) => {
    const result = await window.electronAPI.cancelProcessing(taskId);
    return { taskId, result };
  }
);

export const fetchProcessingStatus = createAsyncThunk(
  'processing/fetchStatus',
  async () => {
    const status = await window.electronAPI.getProcessingStatus();
    return status;
  }
);

export const processingSlice = createSlice({
  name: 'processing',
  initialState,
  reducers: {
    
    // Update progress
    updateProcessingProgress: (state, action: PayloadAction<{
      taskId: string;
      progress: number;
      processedItems?: number;
      currentStage?: 'stage1' | 'stage2';
      message?: string;
    }>) => {
      const task = state.tasks[action.payload.taskId];
      if (task) {
        task.progress = action.payload.progress;
        if (action.payload.processedItems !== undefined) {
          task.processedItems = action.payload.processedItems;
        }
        if (action.payload.currentStage) {
          task.currentStage = action.payload.currentStage;
        }
        if (action.payload.message !== undefined) {
          task.message = action.payload.message;
        }
      }
    },
    
    // Complete processing
    completeProcessing: (state, action: PayloadAction<{ taskId: string }>) => {
      const task = state.tasks[action.payload.taskId];
      if (task) {
        task.status = 'completed';
        task.progress = 1;
        task.completedAt = new Date().toISOString();
        task.processedItems = task.totalItems;
      }
      
      if (state.activeTaskId === action.payload.taskId) {
        state.activeTaskId = null;
        
        // Start next task in queue if any
        if (state.queue.length > 0) {
          const nextTaskId = state.queue[0];
          const nextTask = state.tasks[nextTaskId];
          if (nextTask) {
            nextTask.status = 'processing';
            state.activeTaskId = nextTaskId;
            state.queue = state.queue.slice(1);
          }
        }
      }
    },
    
    // Fail processing
    failProcessing: (state, action: PayloadAction<{ taskId: string; error: string }>) => {
      const task = state.tasks[action.payload.taskId];
      if (task) {
        task.status = 'failed';
        task.error = action.payload.error;
        task.completedAt = new Date().toISOString();
      }
      
      if (state.activeTaskId === action.payload.taskId) {
        state.activeTaskId = null;
      }
    },
    
    // Queue management
    queueTask: (state, action: PayloadAction<{
      taskId: string;
      vocabularyIds: number[];
      totalItems: number;
    }>) => {
      const { taskId, vocabularyIds, totalItems } = action.payload;
      
      state.tasks[taskId] = {
        id: taskId,
        status: 'queued',
        progress: 0,
        totalItems,
        processedItems: 0,
        vocabularyIds
      };
      
      state.queue.push(taskId);
    },
    
    
    removeTask: (state, action: PayloadAction<string>) => {
      delete state.tasks[action.payload];
      state.queue = state.queue.filter(id => id !== action.payload);
      
      if (state.activeTaskId === action.payload) {
        state.activeTaskId = null;
      }
    },
    
    clearCompleted: (state) => {
      Object.keys(state.tasks).forEach(taskId => {
        if (state.tasks[taskId].status === 'completed') {
          delete state.tasks[taskId];
        }
      });
    },
    
    clearAll: (state) => {
      return initialState;
    },
    
    // WebSocket update handler
    updateProcessingTask: (state, action: PayloadAction<any>) => {
      const update = action.payload;
      const taskId = update.taskId;
      
      // Update in tasks record
      if (state.tasks[taskId]) {
        state.tasks[taskId] = {
          ...state.tasks[taskId],
          ...update,
          taskId: taskId,
          id: taskId,
        };
      }
      
      // Update in active tasks
      const activeIndex = state.activeTasks.findIndex(t => t.taskId === taskId);
      if (activeIndex >= 0) {
        state.activeTasks[activeIndex] = {
          ...state.activeTasks[activeIndex],
          ...update,
        };
        
        // Move to recent if completed/failed/cancelled
        if (['completed', 'failed', 'cancelled'].includes(update.status)) {
          const task = state.activeTasks.splice(activeIndex, 1)[0];
          state.recentTasks.unshift({
            ...task,
            completedAt: new Date().toISOString(),
          });
          // Keep only last 20 recent tasks
          if (state.recentTasks.length > 20) {
            state.recentTasks.pop();
          }
        }
      }
      
      // Update in queued tasks
      const queuedIndex = state.queuedTasks.findIndex(t => t.taskId === taskId);
      if (queuedIndex >= 0) {
        if (update.status === 'processing') {
          // Move from queued to active
          const task = state.queuedTasks.splice(queuedIndex, 1)[0];
          state.activeTasks.push({
            ...task,
            ...update,
          });
        } else {
          state.queuedTasks[queuedIndex] = {
            ...state.queuedTasks[queuedIndex],
            ...update,
          };
        }
      }
      
      // Add new task if not found
      if (activeIndex < 0 && queuedIndex < 0 && !state.tasks[taskId]) {
        const newTask: ProcessingTask = {
          id: taskId,
          taskId: taskId,
          totalItems: 0,
          processedItems: 0,
          vocabularyIds: [],
          ...update,
        };
        
        state.tasks[taskId] = newTask;
        
        if (update.status === 'queued') {
          state.queuedTasks.push(newTask);
        } else if (update.status === 'processing') {
          state.activeTasks.push(newTask);
        }
      }
    },
    
    // Async action creators
    startProcessingBatch: (state) => {
      state.loading = true;
      state.error = null;
    },
    
    startProcessingSuccess: (state, action: PayloadAction<{ taskId: string; status: string }>) => {
      state.loading = false;
      // Task will be added via WebSocket update
    },
    
    startProcessingFailure: (state, action: PayloadAction<string>) => {
      state.loading = false;
      state.error = action.payload;
    },
    
    fetchProcessingStatusSuccess: (state, action: PayloadAction<any>) => {
      const status = action.payload;
      // Update tasks based on status
      if (status.tasks) {
        state.activeTasks = status.tasks.active || [];
        state.queuedTasks = status.tasks.queued || [];
        state.recentTasks = status.tasks.recent || [];
      }
    }
  }
});

export const {
  updateProcessingProgress,
  completeProcessing,
  failProcessing,
  queueTask,
  removeTask,
  clearCompleted,
  clearAll,
  updateProcessingTask,
  startProcessingBatch,
  startProcessingSuccess,
  startProcessingFailure,
  fetchProcessingStatusSuccess,
} = processingSlice.actions;

export default processingSlice.reducer;