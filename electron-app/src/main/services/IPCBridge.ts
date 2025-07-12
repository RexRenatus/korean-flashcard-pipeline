import { spawn, ChildProcess } from 'child_process';
import { join } from 'path';
import { v4 as uuidv4 } from 'uuid';
import { VocabularyItem, ProcessingTask, SystemStats } from '@/shared/types';

interface PendingRequest {
  resolve: (value: any) => void;
  reject: (reason: any) => void;
  timeout: NodeJS.Timeout;
}

export class IPCBridge {
  private pythonProcess: ChildProcess | null = null;
  private isInitialized = false;
  private pendingRequests = new Map<string, PendingRequest>();
  private messageBuffer = '';
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 3;

  constructor() {}

  async initialize(timeout = 30000): Promise<boolean> {
    if (this.isInitialized) {
      return true;
    }

    return new Promise((resolve, reject) => {
      const pythonPath = process.env.PYTHON_PATH || 'python';
      const scriptPath = join(__dirname, 'python-bridge.py');
      
      this.pythonProcess = spawn(pythonPath, [scriptPath], {
        env: {
          ...process.env,
          PYTHONUNBUFFERED: '1'
        }
      });

      const initTimeout = setTimeout(() => {
        this.cleanup();
        reject(new Error('Python initialization timeout'));
      }, timeout);

      this.pythonProcess.stdout?.on('data', (data: Buffer) => {
        const message = data.toString();
        this.messageBuffer += message;
        
        // Process complete messages
        const lines = this.messageBuffer.split('\n');
        this.messageBuffer = lines.pop() || '';
        
        for (const line of lines) {
          if (!line.trim()) continue;
          
          try {
            const parsed = JSON.parse(line);
            
            if (parsed.type === 'ready') {
              clearTimeout(initTimeout);
              this.isInitialized = true;
              this.setupEventHandlers();
              resolve(true);
            } else if (parsed.id && this.pendingRequests.has(parsed.id)) {
              this.handleResponse(parsed);
            }
          } catch (err) {
            console.error('Failed to parse Python response:', err);
          }
        }
      });

      this.pythonProcess.stderr?.on('data', (data: Buffer) => {
        const error = data.toString();
        console.error('Python error:', error);
        
        if (!this.isInitialized) {
          clearTimeout(initTimeout);
          this.cleanup();
          reject(new Error('Failed to initialize Python bridge'));
        }
      });

      this.pythonProcess.on('error', (err) => {
        clearTimeout(initTimeout);
        this.cleanup();
        reject(new Error(`Failed to start Python process: ${err.message}`));
      });

      this.pythonProcess.on('exit', (code, signal) => {
        console.log(`Python process exited with code ${code} and signal ${signal}`);
        this.cleanup();
        
        if (!this.isInitialized) {
          clearTimeout(initTimeout);
          reject(new Error('Python process exited unexpectedly'));
        }
      });
    });
  }

  private setupEventHandlers(): void {
    if (!this.pythonProcess) return;

    this.pythonProcess.on('exit', (code, signal) => {
      console.error(`Python process exited unexpectedly: code=${code}, signal=${signal}`);
      this.handleProcessExit();
    });
  }

  private handleProcessExit(): void {
    this.cleanup();
    
    // Reject all pending requests
    for (const [id, request] of this.pendingRequests) {
      clearTimeout(request.timeout);
      request.reject(new Error('Python process exited'));
    }
    this.pendingRequests.clear();
  }

  private handleResponse(message: any): void {
    const request = this.pendingRequests.get(message.id);
    if (!request) return;

    clearTimeout(request.timeout);
    this.pendingRequests.delete(message.id);

    if (message.error) {
      request.reject(new Error(message.error.message || 'Unknown error'));
    } else {
      request.resolve(message.result);
    }
  }

  async execute(command: string, args: any = {}, timeout = 30000): Promise<any> {
    if (!this.isInitialized) {
      throw new Error('Python bridge not initialized');
    }

    const id = uuidv4();
    const request = {
      id,
      command,
      args
    };

    return new Promise((resolve, reject) => {
      const timeoutHandle = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(new Error('Command timeout'));
      }, timeout);

      this.pendingRequests.set(id, {
        resolve,
        reject,
        timeout: timeoutHandle
      });

      const success = this.pythonProcess?.stdin?.write(
        JSON.stringify(request) + '\n',
        (err) => {
          if (err) {
            clearTimeout(timeoutHandle);
            this.pendingRequests.delete(id);
            reject(err);
          }
        }
      );

      if (!success) {
        clearTimeout(timeoutHandle);
        this.pendingRequests.delete(id);
        reject(new Error('Failed to send command to Python'));
      }
    });
  }

  async processVocabulary(items: string[]): Promise<any> {
    return this.execute('process_vocabulary', { items });
  }

  async getVocabularyList(filters: any): Promise<VocabularyItem[]> {
    return this.execute('get_vocabulary', filters);
  }

  async getSystemStats(): Promise<SystemStats> {
    return this.execute('get_system_stats');
  }

  isReady(): boolean {
    return this.isInitialized && this.pythonProcess !== null;
  }

  async shutdown(): Promise<void> {
    if (!this.pythonProcess) return;

    // Clear all pending requests
    for (const [id, request] of this.pendingRequests) {
      clearTimeout(request.timeout);
      request.reject(new Error('Shutting down'));
    }
    this.pendingRequests.clear();

    // Try graceful shutdown
    const killed = this.pythonProcess.kill('SIGTERM');
    if (!killed) {
      // Force kill if graceful shutdown fails
      this.pythonProcess.kill('SIGKILL');
    }

    // Wait a bit for process to exit
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    this.cleanup();
  }

  private cleanup(): void {
    this.isInitialized = false;
    this.pythonProcess = null;
    this.messageBuffer = '';
  }
}