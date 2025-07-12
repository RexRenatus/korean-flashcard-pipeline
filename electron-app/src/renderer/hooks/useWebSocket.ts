import { useEffect, useRef, useState, useCallback } from 'react';
import { useDispatch } from 'react-redux';
import { AppDispatch } from '@renderer/store';
import { updateProcessingTask } from '@renderer/store/processingSlice';
import { useNotification } from '@renderer/providers/NotificationProvider';

interface WebSocketOptions {
  url?: string;
  reconnect?: boolean;
  reconnectInterval?: number;
  reconnectMaxAttempts?: number;
}

interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: number;
}

export const useWebSocket = (options: WebSocketOptions = {}) => {
  const {
    url = 'ws://localhost:8081',
    reconnect = true,
    reconnectInterval = 3000,
    reconnectMaxAttempts = 5,
  } = options;

  const dispatch = useDispatch<AppDispatch>();
  const { showNotification } = useNotification();
  
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  
  const ws = useRef<WebSocket | null>(null);
  const reconnectCount = useRef(0);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    try {
      ws.current = new WebSocket(url);
      
      ws.current.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        reconnectCount.current = 0;
        
        // Subscribe to updates
        ws.current?.send(JSON.stringify({
          type: 'subscribe',
          data: { topics: ['processing', 'system'] },
        }));
      };

      ws.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);
          
          // Handle different message types
          switch (message.type) {
            case 'processing-update':
              handleProcessingUpdate(message.data);
              break;
              
            case 'system-update':
              handleSystemUpdate(message.data);
              break;
              
            case 'notification':
              handleNotification(message.data);
              break;
              
            case 'connection':
              console.log('WebSocket connection established:', message.data);
              break;
              
            default:
              console.log('Unknown WebSocket message type:', message.type);
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.current.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        ws.current = null;
        
        // Attempt reconnection
        if (reconnect && reconnectCount.current < reconnectMaxAttempts) {
          reconnectCount.current++;
          console.log(`Reconnecting... (attempt ${reconnectCount.current}/${reconnectMaxAttempts})`);
          
          reconnectTimeout.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
    }
  }, [url, reconnect, reconnectInterval, reconnectMaxAttempts]);

  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }
    
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
    
    setIsConnected(false);
  }, []);

  const sendMessage = useCallback((type: string, data: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type, data }));
    } else {
      console.warn('WebSocket is not connected');
    }
  }, []);

  // Message handlers
  const handleProcessingUpdate = (data: any) => {
    dispatch(updateProcessingTask(data));
  };

  const handleSystemUpdate = (data: any) => {
    // Handle system updates (could update system stats, etc.)
    console.log('System update:', data);
  };

  const handleNotification = (data: any) => {
    const { level, message, details } = data;
    
    switch (level) {
      case 'success':
        showNotification(message, 'success');
        break;
      case 'error':
        showNotification(message, 'error');
        break;
      case 'warning':
        showNotification(message, 'warning');
        break;
      default:
        showNotification(message, 'info');
    }
  };

  // Setup and cleanup
  useEffect(() => {
    connect();
    
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    lastMessage,
    sendMessage,
    connect,
    disconnect,
  };
};