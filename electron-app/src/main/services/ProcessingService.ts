import { EventEmitter } from 'events';
import { PythonService } from './PythonService';
import { WebSocketService } from './WebSocketService';
import { v4 as uuidv4 } from 'uuid';

interface ProcessingTask {
  id: string;
  vocabularyIds: number[];
  stage: 'stage1' | 'stage2' | 'both';
  priority: 'low' | 'normal' | 'high';
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  startedAt?: Date;
  completedAt?: Date;
  error?: string;
  results?: {
    succeeded: number;
    failed: number;
    items: any[];
  };
}

interface ProcessingOptions {
  stage?: 'stage1' | 'stage2' | 'both';
  priority?: 'low' | 'normal' | 'high';
  batchSize?: number;
  maxRetries?: number;
}

export class ProcessingService extends EventEmitter {
  private pythonService: PythonService;
  private wsService: WebSocketService | null = null;
  private tasks: Map<string, ProcessingTask> = new Map();
  private queue: ProcessingTask[] = [];
  private activeTask: ProcessingTask | null = null;
  private isProcessing = false;
  private processInterval: NodeJS.Timer | null = null;

  constructor() {
    super();
    this.pythonService = PythonService.getInstance();
  }

  setWebSocketService(wsService: WebSocketService) {
    this.wsService = wsService;
  }

  async createTask(vocabularyIds: number[], options: ProcessingOptions = {}): Promise<ProcessingTask> {
    const task: ProcessingTask = {
      id: uuidv4(),
      vocabularyIds,
      stage: options.stage || 'both',
      priority: options.priority || 'normal',
      status: 'queued',
      progress: 0,
    };

    this.tasks.set(task.id, task);
    this.addToQueue(task);
    
    // Send initial update
    this.sendTaskUpdate(task);
    
    // Start processing if not already running
    if (!this.isProcessing) {
      this.startProcessing();
    }

    return task;
  }

  private addToQueue(task: ProcessingTask) {
    // Add task to queue based on priority
    if (task.priority === 'high') {
      // Find first non-high priority task and insert before it
      const index = this.queue.findIndex(t => t.priority !== 'high');
      if (index === -1) {
        this.queue.push(task);
      } else {
        this.queue.splice(index, 0, task);
      }
    } else if (task.priority === 'normal') {
      // Add after high priority tasks but before low priority
      const index = this.queue.findIndex(t => t.priority === 'low');
      if (index === -1) {
        this.queue.push(task);
      } else {
        this.queue.splice(index, 0, task);
      }
    } else {
      // Low priority - add to end
      this.queue.push(task);
    }
  }

  private async startProcessing() {
    if (this.isProcessing) return;
    
    this.isProcessing = true;
    
    // Process queue
    while (this.queue.length > 0 && this.isProcessing) {
      const task = this.queue.shift();
      if (!task) continue;

      await this.processTask(task);
    }
    
    this.isProcessing = false;
  }

  private async processTask(task: ProcessingTask) {
    this.activeTask = task;
    task.status = 'processing';
    task.startedAt = new Date();
    
    this.sendTaskUpdate(task);
    
    try {
      // Process in batches for better progress tracking
      const batchSize = 10;
      const results = {
        succeeded: 0,
        failed: 0,
        items: [] as any[],
      };

      for (let i = 0; i < task.vocabularyIds.length; i += batchSize) {
        if (task.status === 'cancelled') {
          break;
        }

        const batch = task.vocabularyIds.slice(i, i + batchSize);
        
        try {
          // Process batch through Python service
          const batchResult = await this.pythonService.processBatch(batch);
          
          // Update results
          results.succeeded += batchResult.succeeded || 0;
          results.failed += batchResult.failed || 0;
          results.items.push(...(batchResult.items || []));
          
          // Update progress
          task.progress = Math.round(((i + batch.length) / task.vocabularyIds.length) * 100);
          
          // Send progress update
          this.sendTaskUpdate(task, {
            currentItem: `Processing items ${i + 1}-${Math.min(i + batch.length, task.vocabularyIds.length)}`,
            stats: {
              total: task.vocabularyIds.length,
              processed: i + batch.length,
              succeeded: results.succeeded,
              failed: results.failed,
            },
          });
          
          // Small delay between batches
          await new Promise(resolve => setTimeout(resolve, 100));
        } catch (error) {
          console.error(`Error processing batch:`, error);
          results.failed += batch.length;
        }
      }

      // Task completed
      task.status = task.status === 'cancelled' ? 'cancelled' : 'completed';
      task.completedAt = new Date();
      task.progress = 100;
      task.results = results;
      
      this.sendTaskUpdate(task);
      
      // Send notification
      if (this.wsService) {
        this.wsService.sendNotification(
          task.status === 'completed' ? 'success' : 'warning',
          `Processing ${task.status}`,
          {
            taskId: task.id,
            succeeded: results.succeeded,
            failed: results.failed,
          }
        );
      }
      
    } catch (error: any) {
      console.error('Task processing error:', error);
      task.status = 'failed';
      task.error = error.message || 'Unknown error';
      task.completedAt = new Date();
      
      this.sendTaskUpdate(task);
      
      // Send error notification
      if (this.wsService) {
        this.wsService.sendNotification('error', 'Processing failed', {
          taskId: task.id,
          error: task.error,
        });
      }
    } finally {
      this.activeTask = null;
    }
  }

  private sendTaskUpdate(task: ProcessingTask, additionalData?: any) {
    const update = {
      taskId: task.id,
      status: task.status,
      progress: task.progress,
      error: task.error,
      ...additionalData,
    };

    // Send via WebSocket
    if (this.wsService) {
      this.wsService.sendProcessingUpdate(update);
    }

    // Emit event
    this.emit('task-update', update);
  }

  async cancelTask(taskId: string): Promise<boolean> {
    const task = this.tasks.get(taskId);
    if (!task) return false;

    if (task.status === 'queued') {
      // Remove from queue
      const index = this.queue.findIndex(t => t.id === taskId);
      if (index > -1) {
        this.queue.splice(index, 1);
      }
      
      task.status = 'cancelled';
      this.sendTaskUpdate(task);
      return true;
    } else if (task.status === 'processing' && task.id === this.activeTask?.id) {
      // Mark for cancellation - will be handled in processTask loop
      task.status = 'cancelled';
      return true;
    }

    return false;
  }

  getTask(taskId: string): ProcessingTask | undefined {
    return this.tasks.get(taskId);
  }

  getAllTasks(): ProcessingTask[] {
    return Array.from(this.tasks.values());
  }

  getQueueStatus() {
    return {
      queueLength: this.queue.length,
      activeTask: this.activeTask ? {
        id: this.activeTask.id,
        progress: this.activeTask.progress,
        status: this.activeTask.status,
      } : null,
      isProcessing: this.isProcessing,
      tasks: {
        total: this.tasks.size,
        queued: Array.from(this.tasks.values()).filter(t => t.status === 'queued').length,
        processing: Array.from(this.tasks.values()).filter(t => t.status === 'processing').length,
        completed: Array.from(this.tasks.values()).filter(t => t.status === 'completed').length,
        failed: Array.from(this.tasks.values()).filter(t => t.status === 'failed').length,
        cancelled: Array.from(this.tasks.values()).filter(t => t.status === 'cancelled').length,
      },
    };
  }

  clearCompletedTasks() {
    const completed = Array.from(this.tasks.entries())
      .filter(([_, task]) => task.status === 'completed' || task.status === 'cancelled')
      .map(([id]) => id);

    completed.forEach(id => this.tasks.delete(id));
    
    return completed.length;
  }

  async stopProcessing() {
    this.isProcessing = false;
    
    // Cancel active task
    if (this.activeTask) {
      this.activeTask.status = 'cancelled';
      this.sendTaskUpdate(this.activeTask);
    }
  }
}