import { WebSocketServer, WebSocket } from 'ws';
import { EventEmitter } from 'events';
import { Server } from 'http';

interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: number;
}

interface ProcessingUpdate {
  taskId: string;
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  currentItem?: string;
  message?: string;
  error?: string;
  stats?: {
    total: number;
    processed: number;
    succeeded: number;
    failed: number;
    remainingTime?: number;
  };
}

export class WebSocketService extends EventEmitter {
  private wss: WebSocketServer | null = null;
  private clients: Set<WebSocket> = new Set();
  private port: number = 8080;
  private heartbeatInterval: NodeJS.Timer | null = null;

  constructor(port?: number) {
    super();
    if (port) this.port = port;
  }

  async start(server?: Server): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        if (server) {
          // Attach to existing HTTP server
          this.wss = new WebSocketServer({ server });
        } else {
          // Create standalone WebSocket server
          this.wss = new WebSocketServer({ port: this.port });
        }

        this.wss.on('connection', this.handleConnection.bind(this));
        this.wss.on('error', (error) => {
          console.error('WebSocket server error:', error);
          this.emit('error', error);
        });

        // Start heartbeat
        this.startHeartbeat();

        console.log(`WebSocket server started on port ${this.port}`);
        resolve();
      } catch (error) {
        reject(error);
      }
    });
  }

  private handleConnection(ws: WebSocket, request: any) {
    console.log('New WebSocket connection from:', request.socket.remoteAddress);
    
    this.clients.add(ws);
    
    // Send welcome message
    this.sendToClient(ws, {
      type: 'connection',
      data: { status: 'connected', clientId: this.generateClientId() },
    });

    ws.on('message', (message: Buffer) => {
      try {
        const data = JSON.parse(message.toString());
        this.handleMessage(ws, data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    });

    ws.on('close', () => {
      console.log('WebSocket connection closed');
      this.clients.delete(ws);
    });

    ws.on('error', (error) => {
      console.error('WebSocket client error:', error);
      this.clients.delete(ws);
    });

    // Send pong on ping
    ws.on('ping', () => {
      ws.pong();
    });
  }

  private handleMessage(ws: WebSocket, message: any) {
    const { type, data } = message;

    switch (type) {
      case 'subscribe':
        // Handle subscription to specific events
        ws.send(JSON.stringify({
          type: 'subscribed',
          data: { topics: data.topics || [] },
          timestamp: Date.now(),
        }));
        break;

      case 'ping':
        ws.send(JSON.stringify({
          type: 'pong',
          timestamp: Date.now(),
        }));
        break;

      default:
        // Emit for handlers to process
        this.emit('message', { client: ws, type, data });
    }
  }

  private sendToClient(client: WebSocket, message: WebSocketMessage) {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify({
        ...message,
        timestamp: message.timestamp || Date.now(),
      }));
    }
  }

  broadcast(message: WebSocketMessage) {
    const messageStr = JSON.stringify({
      ...message,
      timestamp: message.timestamp || Date.now(),
    });

    this.clients.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(messageStr);
      }
    });
  }

  // Processing-specific methods
  sendProcessingUpdate(update: ProcessingUpdate) {
    this.broadcast({
      type: 'processing-update',
      data: update,
      timestamp: Date.now(),
    });
  }

  sendSystemUpdate(data: any) {
    this.broadcast({
      type: 'system-update',
      data,
      timestamp: Date.now(),
    });
  }

  sendNotification(level: 'info' | 'warning' | 'error' | 'success', message: string, details?: any) {
    this.broadcast({
      type: 'notification',
      data: {
        level,
        message,
        details,
      },
      timestamp: Date.now(),
    });
  }

  private startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      this.clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
          client.ping();
        } else {
          this.clients.delete(client);
        }
      });
    }, 30000); // 30 seconds
  }

  private generateClientId(): string {
    return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  async stop() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }

    // Close all client connections
    this.clients.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        client.close(1000, 'Server shutting down');
      }
    });
    this.clients.clear();

    // Close server
    if (this.wss) {
      return new Promise<void>((resolve) => {
        this.wss!.close(() => {
          console.log('WebSocket server stopped');
          this.wss = null;
          resolve();
        });
      });
    }
  }

  getClientCount(): number {
    return this.clients.size;
  }

  isRunning(): boolean {
    return this.wss !== null;
  }
}