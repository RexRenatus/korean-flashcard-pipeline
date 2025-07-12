import { createSlice, PayloadAction, createAsyncThunk } from '@reduxjs/toolkit';
import { SystemStats, ConnectionStatus, NotificationItem } from '@/shared/types';

interface SystemState {
  stats: SystemStats | null;
  connectionStatus: ConnectionStatus;
  notifications: NotificationItem[];
  loading: boolean;
  error: string | null;
  apiHealth: 'healthy' | 'degraded' | 'error';
  lastSync: string | null;
}

// Async thunk for fetching system stats
export const fetchSystemStats = createAsyncThunk(
  'system/fetchStats',
  async () => {
    const stats = await window.electronAPI.getSystemStats();
    return stats;
  }
);

const initialState: SystemState = {
  stats: null,
  connectionStatus: 'disconnected',
  notifications: [],
  loading: false,
  error: null,
  apiHealth: 'healthy',
  lastSync: null
};

export const systemSlice = createSlice({
  name: 'system',
  initialState,
  reducers: {
    // System stats
    updateSystemStats: (state, action: PayloadAction<Partial<SystemStats>>) => {
      if (state.stats) {
        state.stats = { ...state.stats, ...action.payload };
      }
    },
    
    setAPIHealth: (state, action: PayloadAction<'healthy' | 'degraded' | 'error'>) => {
      state.apiHealth = action.payload;
      if (state.stats) {
        state.stats.apiHealth = action.payload;
      }
    },
    
    // Connection status
    setConnectionStatus: (state, action: PayloadAction<ConnectionStatus>) => {
      state.connectionStatus = action.payload;
    },
    
    // Notifications
    addNotification: (state, action: PayloadAction<NotificationItem>) => {
      state.notifications.push(action.payload);
      
      // Keep only last 50 notifications
      if (state.notifications.length > 50) {
        state.notifications = state.notifications.slice(-50);
      }
    },
    
    removeNotification: (state, action: PayloadAction<string>) => {
      state.notifications = state.notifications.filter(n => n.id !== action.payload);
    },
    
    clearNotifications: (state) => {
      state.notifications = [];
    },
    
    // Performance metrics
    updatePerformanceMetrics: (state, action: PayloadAction<{
      cacheHitRate?: number;
      averageProcessingTime?: number;
    }>) => {
      if (state.stats) {
        if (action.payload.cacheHitRate !== undefined) {
          state.stats.cacheHitRate = action.payload.cacheHitRate;
        }
        if (action.payload.averageProcessingTime !== undefined) {
          state.stats.averageProcessingTime = action.payload.averageProcessingTime;
        }
      }
    },
    
    // Sync status
    updateLastSync: (state, action: PayloadAction<string>) => {
      state.lastSync = action.payload;
      if (state.stats) {
        state.stats.lastSync = action.payload;
      }
    },
    
    // Batch update for word counts
    updateWordCounts: (state, action: PayloadAction<{
      totalWords?: number;
      processedWords?: number;
      pendingWords?: number;
      failedWords?: number;
    }>) => {
      if (state.stats) {
        if (action.payload.totalWords !== undefined) {
          state.stats.totalWords = action.payload.totalWords;
        }
        if (action.payload.processedWords !== undefined) {
          state.stats.processedWords = action.payload.processedWords;
        }
        if (action.payload.pendingWords !== undefined) {
          state.stats.pendingWords = action.payload.pendingWords;
        }
        if (action.payload.failedWords !== undefined) {
          state.stats.failedWords = action.payload.failedWords;
        }
      }
    },
    
    // Reset stats
    resetStats: (state) => {
      state.stats = initialState.stats;
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchSystemStats.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchSystemStats.fulfilled, (state, action) => {
        state.loading = false;
        state.stats = action.payload;
        state.apiHealth = action.payload.apiHealth;
        state.lastSync = action.payload.lastSync;
      })
      .addCase(fetchSystemStats.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch system stats';
      });
  }
});

export const {
  updateSystemStats,
  setAPIHealth,
  setConnectionStatus,
  addNotification,
  removeNotification,
  clearNotifications,
  updatePerformanceMetrics,
  updateLastSync,
  updateWordCounts,
  resetStats
} = systemSlice.actions;

export default systemSlice.reducer;