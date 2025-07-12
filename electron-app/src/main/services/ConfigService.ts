import { app } from 'electron';
import Store from 'electron-store';
import path from 'path';
import { promises as fs } from 'fs';

interface ConfigSchema {
  api: {
    base_url: string;
    api_key?: string;
    model: string;
    timeout: number;
    max_retries: number;
  };
  processing: {
    batch_size: number;
    parallel_requests: number;
    rate_limit_rpm: number;
    enable_cache: boolean;
  };
  cache: {
    ttl_hours: number;
    max_size_mb: number;
    cleanup_interval_hours: number;
  };
  database: {
    path: string;
    backup_enabled: boolean;
    backup_interval_days: number;
  };
  advanced?: {
    debug_mode: boolean;
    telemetry_enabled: boolean;
    log_level: 'debug' | 'info' | 'warning' | 'error';
  };
}

const defaultConfig: ConfigSchema = {
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
};

export class ConfigService {
  private store: Store<ConfigSchema>;
  private configPath: string;

  constructor() {
    this.store = new Store<ConfigSchema>({
      name: 'config',
      defaults: defaultConfig,
      schema: {
        api: {
          type: 'object',
          properties: {
            base_url: { type: 'string' },
            api_key: { type: 'string' },
            model: { type: 'string' },
            timeout: { type: 'number' },
            max_retries: { type: 'number' },
          },
        },
        processing: {
          type: 'object',
          properties: {
            batch_size: { type: 'number' },
            parallel_requests: { type: 'number' },
            rate_limit_rpm: { type: 'number' },
            enable_cache: { type: 'boolean' },
          },
        },
        cache: {
          type: 'object',
          properties: {
            ttl_hours: { type: 'number' },
            max_size_mb: { type: 'number' },
            cleanup_interval_hours: { type: 'number' },
          },
        },
        database: {
          type: 'object',
          properties: {
            path: { type: 'string' },
            backup_enabled: { type: 'boolean' },
            backup_interval_days: { type: 'number' },
          },
        },
      },
    });

    this.configPath = path.join(app.getPath('userData'), 'config.json');
    this.migrateFromEnv();
  }

  private migrateFromEnv() {
    // Check for environment variables and migrate them to the store
    if (process.env.OPENROUTER_API_KEY && !this.store.get('api.api_key')) {
      this.store.set('api.api_key', process.env.OPENROUTER_API_KEY);
    }
    if (process.env.OPENROUTER_BASE_URL) {
      this.store.set('api.base_url', process.env.OPENROUTER_BASE_URL);
    }
    if (process.env.OPENROUTER_MODEL) {
      this.store.set('api.model', process.env.OPENROUTER_MODEL);
    }
  }

  async load(): Promise<ConfigSchema> {
    // Try to load from JSON file first (for backward compatibility)
    try {
      const jsonConfig = await fs.readFile(this.configPath, 'utf-8');
      const config = JSON.parse(jsonConfig);
      // Update store with JSON config
      Object.entries(config).forEach(([key, value]) => {
        this.store.set(key as any, value);
      });
    } catch (error) {
      // JSON file doesn't exist or is invalid, use store defaults
    }

    return this.store.store;
  }

  async save(config: Partial<ConfigSchema>): Promise<ConfigSchema> {
    // Update store
    Object.entries(config).forEach(([key, value]) => {
      if (value !== undefined) {
        this.store.set(key as any, value);
      }
    });

    // Also save to JSON file for backward compatibility
    await fs.writeFile(this.configPath, JSON.stringify(this.store.store, null, 2));

    return this.store.store;
  }

  async update(updates: Partial<ConfigSchema>): Promise<ConfigSchema> {
    // Deep merge updates
    const currentConfig = this.store.store;
    const mergedConfig = this.deepMerge(currentConfig, updates);
    
    return this.save(mergedConfig);
  }

  async reset(): Promise<ConfigSchema> {
    this.store.clear();
    // Delete JSON file
    try {
      await fs.unlink(this.configPath);
    } catch (error) {
      // File might not exist
    }
    return defaultConfig;
  }

  get(key: keyof ConfigSchema): any {
    return this.store.get(key);
  }

  set(key: keyof ConfigSchema, value: any): void {
    this.store.set(key, value);
  }

  private deepMerge(target: any, source: any): any {
    const output = { ...target };
    
    Object.keys(source).forEach(key => {
      if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
        if (key in target) {
          output[key] = this.deepMerge(target[key], source[key]);
        } else {
          output[key] = source[key];
        }
      } else {
        output[key] = source[key];
      }
    });
    
    return output;
  }

  // Helper method to get config for Python backend
  async getPythonConfig(): Promise<any> {
    const config = this.store.store;
    return {
      api_key: config.api.api_key,
      base_url: config.api.base_url,
      model: config.api.model,
      timeout: config.api.timeout,
      max_retries: config.api.max_retries,
      batch_size: config.processing.batch_size,
      parallel_requests: config.processing.parallel_requests,
      rate_limit_rpm: config.processing.rate_limit_rpm,
      enable_cache: config.processing.enable_cache,
      cache_ttl_hours: config.cache.ttl_hours,
      cache_max_size_mb: config.cache.max_size_mb,
      database_path: config.database.path,
      debug_mode: config.advanced?.debug_mode || false,
      log_level: config.advanced?.log_level || 'info',
    };
  }
}