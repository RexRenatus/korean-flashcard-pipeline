import { app, BrowserWindow, ipcMain, Menu } from 'electron';
import * as path from 'path';
import { PythonService } from './services/PythonService';
import { WebSocketService } from './services/WebSocketService';
import { ProcessingService } from './services/ProcessingService';
import { getAutoUpdaterService } from './services/AutoUpdaterService';
import { getTelemetryService } from './services/TelemetryService';
import { getBackupService } from './services/BackupService';
import { setupIPCHandlers } from './ipc/handlers';
import { createApplicationMenu } from './menu';

// Keep a global reference of the window object
let mainWindow: BrowserWindow | null = null;
let pythonService: PythonService | null = null;
let wsService: WebSocketService | null = null;
let processingService: ProcessingService | null = null;

const isDevelopment = process.env.NODE_ENV !== 'production';

async function createWindow() {
  // Create the browser window
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, '../preload/index.js')
    },
    icon: path.join(__dirname, '../../assets/icon.png'),
    show: false,
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
  });

  // Set up auto-updater
  const autoUpdater = getAutoUpdaterService();
  autoUpdater.setMainWindow(mainWindow);

  // Load the app
  if (isDevelopment) {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));
  }

  // Show window when ready
  mainWindow.once('ready-to-show', () => {
    mainWindow?.show();
    
    // Check for updates after window is shown
    if (!isDevelopment) {
      setTimeout(() => {
        autoUpdater.checkForUpdatesInBackground();
      }, 10000); // Check after 10 seconds
    }
  });

  // Handle window closed
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Set up application menu
  const menu = createApplicationMenu(mainWindow);
  Menu.setApplicationMenu(menu);
}

// Initialize services
async function initializeServices() {
  try {
    // Initialize Python service
    pythonService = PythonService.getInstance();
    await pythonService.ensureInitialized();
    console.log('Python service initialized successfully');

    // Initialize WebSocket service
    wsService = new WebSocketService(8081);
    await wsService.start();
    console.log('WebSocket service started successfully');

    // Initialize Processing service
    processingService = new ProcessingService();
    processingService.setWebSocketService(wsService);
    console.log('Processing service initialized successfully');

    // Initialize Telemetry service
    const telemetry = getTelemetryService();
    telemetry.track('app_start', {
      version: app.getVersion(),
      platform: process.platform,
      isDevelopment,
    });
    console.log('Telemetry service initialized successfully');

    // Initialize Backup service
    const backup = getBackupService();
    // Schedule auto-backup every 24 hours
    if (!isDevelopment) {
      await backup.scheduleAutoBackup(24);
    }
    console.log('Backup service initialized successfully');

    // Send system ready notification
    wsService.sendSystemUpdate({
      status: 'ready',
      services: {
        python: true,
        websocket: true,
        processing: true,
        telemetry: true,
        backup: true,
      },
    });
  } catch (error) {
    console.error('Failed to initialize services:', error);
    const telemetry = getTelemetryService();
    telemetry.track('service_init_error', {
      error: error.message,
      stack: error.stack,
    });
  }
}

// App event handlers
app.whenReady().then(async () => {
  await initializeServices();
  if (pythonService && processingService) {
    setupIPCHandlers(pythonService, processingService);
  }
  createWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on('before-quit', async () => {
  // Track app shutdown
  const telemetry = getTelemetryService();
  telemetry.track('app_shutdown', {
    sessionDuration: Date.now() - app.getPath('sessionStart'),
  });

  // Cleanup services
  if (processingService) {
    await processingService.stopProcessing();
  }
  
  if (wsService) {
    await wsService.stop();
  }
  
  if (pythonService) {
    await pythonService.shutdown();
  }

  // Cleanup telemetry (flushes remaining events)
  telemetry.destroy();
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  // You might want to show an error dialog or log to a file
});

process.on('unhandledRejection', (error) => {
  console.error('Unhandled Promise Rejection:', error);
  // You might want to show an error dialog or log to a file
});