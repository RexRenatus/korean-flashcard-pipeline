import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';

interface APIConfig {
  base_url: string;
  api_key?: string;
  model: string;
  timeout: number;
  max_retries: number;
}

interface ProcessingConfig {
  batch_size: number;
  parallel_requests: number;
  rate_limit_rpm: number;
  enable_cache: boolean;
}

interface CacheConfig {
  ttl_hours: number;
  max_size_mb: number;
  cleanup_interval_hours: number;
}

interface DatabaseConfig {
  path: string;
  backup_enabled: boolean;
  backup_interval_days: number;
}

interface AdvancedConfig {
  debug_mode: boolean;
  telemetry_enabled: boolean;
  log_level: 'debug' | 'info' | 'warning' | 'error';
}

interface ConfigState {
  api: APIConfig;
  processing: ProcessingConfig;
  cache: CacheConfig;
  database: DatabaseConfig;
  advanced?: AdvancedConfig;
  loading: boolean;
  error: string | null;
  lastSaved: string | null;
}

const initialState: ConfigState = {
  api: {
    base_url: 'https://openrouter.ai/api/v1',
    model: 'anthropic/claude-3.5-sonnet-20241022',
    timeout: 30,
    max_retries: 3,
  },
  processing: {
    batch_size: 10,
    parallel_requests: 3,
    rate_limit_rpm: 60,
    enable_cache: true,
  },
  cache: {
    ttl_hours: 24,
    max_size_mb: 100,
    cleanup_interval_hours: 6,
  },
  database: {
    path: './pipeline.db',
    backup_enabled: true,
    backup_interval_days: 7,
  },
  advanced: {
    debug_mode: false,
    telemetry_enabled: true,
    log_level: 'info',
  },
  loading: false,
  error: null,
  lastSaved: null,
};

// Async thunks
export const loadConfig = createAsyncThunk(
  'config/load',
  async () => {
    const config = await window.electronAPI.loadConfig();
    return config;
  }
);

export const saveConfig = createAsyncThunk(
  'config/save',
  async (config: Partial<ConfigState>) => {
    await window.electronAPI.saveConfig(config);
    return config;
  }
);

export const updateConfig = createAsyncThunk(
  'config/update',
  async (config: Partial<ConfigState>) => {
    await window.electronAPI.updateConfig(config);
    return config;
  }
);

export const resetConfig = createAsyncThunk(
  'config/reset',
  async () => {
    await window.electronAPI.resetConfig();
    return initialState;
  }
);

// Slice
const configSlice = createSlice({
  name: 'config',
  initialState,
  reducers: {
    setApiConfig: (state, action: PayloadAction<Partial<APIConfig>>) => {
      state.api = { ...state.api, ...action.payload };
    },
    setProcessingConfig: (state, action: PayloadAction<Partial<ProcessingConfig>>) => {
      state.processing = { ...state.processing, ...action.payload };
    },
    setCacheConfig: (state, action: PayloadAction<Partial<CacheConfig>>) => {
      state.cache = { ...state.cache, ...action.payload };
    },
    setDatabaseConfig: (state, action: PayloadAction<Partial<DatabaseConfig>>) => {
      state.database = { ...state.database, ...action.payload };
    },
    setAdvancedConfig: (state, action: PayloadAction<Partial<AdvancedConfig>>) => {
      state.advanced = { ...state.advanced, ...action.payload } as AdvancedConfig;
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // Load config
    builder
      .addCase(loadConfig.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(loadConfig.fulfilled, (state, action) => {
        state.loading = false;
        Object.assign(state, action.payload);
      })
      .addCase(loadConfig.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to load configuration';
      });

    // Save config
    builder
      .addCase(saveConfig.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(saveConfig.fulfilled, (state, action) => {
        state.loading = false;
        state.lastSaved = new Date().toISOString();
        Object.assign(state, action.payload);
      })
      .addCase(saveConfig.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to save configuration';
      });

    // Update config
    builder
      .addCase(updateConfig.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(updateConfig.fulfilled, (state, action) => {
        state.loading = false;
        state.lastSaved = new Date().toISOString();
        Object.assign(state, action.payload);
      })
      .addCase(updateConfig.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to update configuration';
      });

    // Reset config
    builder
      .addCase(resetConfig.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(resetConfig.fulfilled, (state) => {
        state.loading = false;
        Object.assign(state, initialState);
      })
      .addCase(resetConfig.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to reset configuration';
      });
  },
});

export const {
  setApiConfig,
  setProcessingConfig,
  setCacheConfig,
  setDatabaseConfig,
  setAdvancedConfig,
  clearError,
} = configSlice.actions;

export default configSlice.reducer;