import { app } from 'electron';
import { EventEmitter } from 'events';
import * as fs from 'fs/promises';
import * as path from 'path';
import { v4 as uuidv4 } from 'uuid';

interface TelemetryEvent {
  id: string;
  event: string;
  properties?: Record<string, any>;
  timestamp: string;
  sessionId: string;
  userId?: string;
  appVersion: string;
  platform: string;
  arch: string;
}

interface TelemetryConfig {
  enabled: boolean;
  endpoint?: string;
  batchSize: number;
  flushInterval: number;
  maxQueueSize: number;
  excludeEvents?: string[];
}

export class TelemetryService extends EventEmitter {
  private config: TelemetryConfig;
  private queue: TelemetryEvent[] = [];
  private sessionId: string;
  private userId?: string;
  private flushTimer?: NodeJS.Timeout;
  private telemetryPath: string;
  private isEnabled: boolean = true;

  constructor() {
    super();
    
    this.config = {
      enabled: true,
      batchSize: 50,
      flushInterval: 30000, // 30 seconds
      maxQueueSize: 1000,
      excludeEvents: ['mouse_move', 'scroll'],
    };

    this.sessionId = uuidv4();
    this.telemetryPath = path.join(app.getPath('userData'), 'telemetry');
    
    this.initialize();
  }

  private async initialize() {
    // Create telemetry directory
    await fs.mkdir(this.telemetryPath, { recursive: true });
    
    // Load saved telemetry events
    await this.loadQueuedEvents();
    
    // Start flush timer
    this.startFlushTimer();
    
    // Listen for app events
    this.setupAppEventListeners();
  }

  private setupAppEventListeners() {
    app.on('will-quit', () => {
      this.flush();
    });

    app.on('window-all-closed', () => {
      this.flush();
    });
  }

  public setUserId(userId: string) {
    this.userId = userId;
  }

  public setEnabled(enabled: boolean) {
    this.isEnabled = enabled;
    if (!enabled) {
      this.clearQueue();
    }
  }

  public track(event: string, properties?: Record<string, any>) {
    if (!this.isEnabled || !this.config.enabled) return;
    
    // Check if event is excluded
    if (this.config.excludeEvents?.includes(event)) return;

    const telemetryEvent: TelemetryEvent = {
      id: uuidv4(),
      event,
      properties,
      timestamp: new Date().toISOString(),
      sessionId: this.sessionId,
      userId: this.userId,
      appVersion: app.getVersion(),
      platform: process.platform,
      arch: process.arch,
    };

    this.queue.push(telemetryEvent);
    this.emit('event', telemetryEvent);

    // Check queue size
    if (this.queue.length >= this.config.maxQueueSize) {
      this.queue.shift(); // Remove oldest event
    }

    // Flush if batch size reached
    if (this.queue.length >= this.config.batchSize) {
      this.flush();
    }
  }

  private startFlushTimer() {
    this.flushTimer = setInterval(() => {
      this.flush();
    }, this.config.flushInterval);
  }

  private stopFlushTimer() {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
      this.flushTimer = undefined;
    }
  }

  private async flush() {
    if (this.queue.length === 0) return;

    const events = [...this.queue];
    this.queue = [];

    try {
      if (this.config.endpoint) {
        // Send to remote endpoint
        await this.sendToEndpoint(events);
      } else {
        // Save to local file
        await this.saveToFile(events);
      }
      
      this.emit('flush', events.length);
    } catch (error) {
      console.error('Failed to flush telemetry:', error);
      // Re-queue events on failure
      this.queue.unshift(...events);
    }
  }

  private async sendToEndpoint(events: TelemetryEvent[]) {
    // Implementation for sending to remote telemetry service
    // This would typically use fetch or axios to send data
    console.log(`Would send ${events.length} events to endpoint`);
  }

  private async saveToFile(events: TelemetryEvent[]) {
    const filename = `telemetry_${new Date().toISOString().split('T')[0]}.jsonl`;
    const filepath = path.join(this.telemetryPath, filename);
    
    const lines = events.map(event => JSON.stringify(event)).join('\n') + '\n';
    
    await fs.appendFile(filepath, lines, 'utf8');
  }

  private async loadQueuedEvents() {
    try {
      const files = await fs.readdir(this.telemetryPath);
      const telemetryFiles = files.filter(f => f.startsWith('telemetry_') && f.endsWith('.jsonl'));
      
      // Load only today's file if it exists
      const today = new Date().toISOString().split('T')[0];
      const todayFile = `telemetry_${today}.jsonl`;
      
      if (telemetryFiles.includes(todayFile)) {
        const filepath = path.join(this.telemetryPath, todayFile);
        const content = await fs.readFile(filepath, 'utf8');
        const lines = content.trim().split('\n');
        
        for (const line of lines) {
          try {
            const event = JSON.parse(line);
            // Don't re-queue old events, just count them
            this.emit('loaded', event);
          } catch (e) {
            // Skip invalid lines
          }
        }
      }
    } catch (error) {
      console.error('Failed to load telemetry events:', error);
    }
  }

  public async getStats() {
    const files = await fs.readdir(this.telemetryPath);
    const telemetryFiles = files.filter(f => f.startsWith('telemetry_') && f.endsWith('.jsonl'));
    
    let totalEvents = 0;
    for (const file of telemetryFiles) {
      const filepath = path.join(this.telemetryPath, file);
      const content = await fs.readFile(filepath, 'utf8');
      totalEvents += content.trim().split('\n').length;
    }

    return {
      queuedEvents: this.queue.length,
      totalEvents,
      sessionId: this.sessionId,
      isEnabled: this.isEnabled,
    };
  }

  private clearQueue() {
    this.queue = [];
  }

  public async clearAllData() {
    this.clearQueue();
    
    const files = await fs.readdir(this.telemetryPath);
    for (const file of files) {
      if (file.startsWith('telemetry_') && file.endsWith('.jsonl')) {
        await fs.unlink(path.join(this.telemetryPath, file));
      }
    }
  }

  public destroy() {
    this.stopFlushTimer();
    this.flush();
    this.removeAllListeners();
  }
}

// Singleton instance
let telemetryService: TelemetryService | null = null;

export const getTelemetryService = (): TelemetryService => {
  if (!telemetryService) {
    telemetryService = new TelemetryService();
  }
  return telemetryService;
};