import { store } from '@renderer/store';
import { showNotification } from '@renderer/store/notificationSlice';

interface ErrorReport {
  message: string;
  stack?: string;
  timestamp: string;
  userAgent: string;
  appVersion?: string;
  context?: Record<string, any>;
}

class ErrorHandler {
  private errorQueue: ErrorReport[] = [];
  private isOnline: boolean = navigator.onLine;
  private maxQueueSize: number = 100;

  constructor() {
    this.setupGlobalHandlers();
    this.setupNetworkListeners();
  }

  private setupGlobalHandlers() {
    // Handle unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      console.error('Unhandled promise rejection:', event.reason);
      this.handleError(event.reason, {
        type: 'unhandledRejection',
        promise: event.promise,
      });
      event.preventDefault();
    });

    // Handle global errors
    window.addEventListener('error', (event) => {
      console.error('Global error:', event.error);
      this.handleError(event.error || new Error(event.message), {
        type: 'globalError',
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
      });
      event.preventDefault();
    });
  }

  private setupNetworkListeners() {
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.flushErrorQueue();
    });

    window.addEventListener('offline', () => {
      this.isOnline = false;
    });
  }

  public handleError(error: Error | string, context?: Record<string, any>) {
    const errorObj = error instanceof Error ? error : new Error(String(error));
    
    const errorReport: ErrorReport = {
      message: errorObj.message,
      stack: errorObj.stack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      appVersion: window.electron?.getVersion?.(),
      context,
    };

    // Log to console
    console.error('Error reported:', errorReport);

    // Show user notification for non-network errors
    if (!this.isNetworkError(errorObj)) {
      store.dispatch(
        showNotification({
          message: 'An error occurred. Please try again.',
          severity: 'error',
          autoHide: true,
        })
      );
    }

    // Send to telemetry
    this.sendToTelemetry(errorReport);

    // Queue for retry if offline
    if (!this.isOnline) {
      this.queueError(errorReport);
    }
  }

  private isNetworkError(error: Error): boolean {
    return (
      error.message.toLowerCase().includes('network') ||
      error.message.toLowerCase().includes('fetch') ||
      error.message.toLowerCase().includes('xhr')
    );
  }

  private sendToTelemetry(errorReport: ErrorReport) {
    try {
      window.electron?.sendTelemetry?.({
        event: 'error',
        properties: {
          error_message: errorReport.message,
          error_stack: errorReport.stack,
          app_version: errorReport.appVersion,
          context: JSON.stringify(errorReport.context),
          timestamp: errorReport.timestamp,
        },
      });
    } catch (telemetryError) {
      console.error('Failed to send error telemetry:', telemetryError);
    }
  }

  private queueError(errorReport: ErrorReport) {
    if (this.errorQueue.length >= this.maxQueueSize) {
      this.errorQueue.shift(); // Remove oldest error
    }
    this.errorQueue.push(errorReport);
    this.saveQueueToStorage();
  }

  private saveQueueToStorage() {
    try {
      localStorage.setItem('errorQueue', JSON.stringify(this.errorQueue));
    } catch (e) {
      console.error('Failed to save error queue:', e);
    }
  }

  private loadQueueFromStorage() {
    try {
      const stored = localStorage.getItem('errorQueue');
      if (stored) {
        this.errorQueue = JSON.parse(stored);
      }
    } catch (e) {
      console.error('Failed to load error queue:', e);
    }
  }

  private async flushErrorQueue() {
    if (this.errorQueue.length === 0) return;

    const errors = [...this.errorQueue];
    this.errorQueue = [];
    this.saveQueueToStorage();

    for (const errorReport of errors) {
      this.sendToTelemetry(errorReport);
    }
  }

  public clearErrorQueue() {
    this.errorQueue = [];
    localStorage.removeItem('errorQueue');
  }

  public getErrorStats() {
    return {
      queuedErrors: this.errorQueue.length,
      isOnline: this.isOnline,
    };
  }
}

// Create singleton instance
export const errorHandler = new ErrorHandler();

// Helper function for manual error reporting
export const reportError = (
  error: Error | string,
  context?: Record<string, any>
) => {
  errorHandler.handleError(error, context);
};

// React hook for error handling
export const useErrorHandler = () => {
  return {
    reportError,
    errorStats: errorHandler.getErrorStats(),
  };
};