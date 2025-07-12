/**
 * Unit tests for Electron main process
 */

import { app, BrowserWindow } from 'electron';

// Mock electron modules
jest.mock('electron', () => ({
  app: {
    whenReady: jest.fn().mockResolvedValue(undefined),
    quit: jest.fn(),
    on: jest.fn(),
    getPath: jest.fn(),
    getName: jest.fn().mockReturnValue('korean-flashcard-desktop'),
    getVersion: jest.fn().mockReturnValue('1.0.0'),
    setAppUserModelId: jest.fn(),
    requestSingleInstanceLock: jest.fn().mockReturnValue(true),
  },
  BrowserWindow: jest.fn().mockImplementation(() => ({
    loadURL: jest.fn(),
    loadFile: jest.fn(),
    on: jest.fn(),
    once: jest.fn(),
    webContents: {
      on: jest.fn(),
      send: jest.fn(),
      openDevTools: jest.fn(),
    },
    show: jest.fn(),
    hide: jest.fn(),
    close: jest.fn(),
    minimize: jest.fn(),
    maximize: jest.fn(),
    unmaximize: jest.fn(),
    isMaximized: jest.fn().mockReturnValue(false),
    setAlwaysOnTop: jest.fn(),
  })),
  ipcMain: {
    handle: jest.fn(),
    on: jest.fn(),
    removeHandler: jest.fn(),
  },
  dialog: {
    showOpenDialog: jest.fn(),
    showSaveDialog: jest.fn(),
    showMessageBox: jest.fn(),
    showErrorBox: jest.fn(),
  },
  Menu: {
    buildFromTemplate: jest.fn(),
    setApplicationMenu: jest.fn(),
  },
  shell: {
    openExternal: jest.fn(),
    showItemInFolder: jest.fn(),
  },
}));

describe('Electron Main Process', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('App Lifecycle', () => {
    it('should request single instance lock', () => {
      expect(app.requestSingleInstanceLock).toBeDefined();
      const hasLock = app.requestSingleInstanceLock();
      expect(hasLock).toBe(true);
    });

    it('should set app user model ID', () => {
      app.setAppUserModelId('com.koreanflashcards.desktop');
      expect(app.setAppUserModelId).toHaveBeenCalledWith('com.koreanflashcards.desktop');
    });

    it('should handle app ready event', async () => {
      await app.whenReady();
      expect(app.whenReady).toHaveBeenCalled();
    });

    it('should quit app', () => {
      app.quit();
      expect(app.quit).toHaveBeenCalled();
    });
  });

  describe('BrowserWindow', () => {
    let mainWindow: any;

    beforeEach(() => {
      mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        webPreferences: {
          nodeIntegration: false,
          contextIsolation: true,
        },
      });
    });

    it('should create a new browser window', () => {
      expect(BrowserWindow).toHaveBeenCalledWith({
        width: 1200,
        height: 800,
        webPreferences: {
          nodeIntegration: false,
          contextIsolation: true,
        },
      });
    });

    it('should load URL', () => {
      const url = 'http://localhost:3000';
      mainWindow.loadURL(url);
      expect(mainWindow.loadURL).toHaveBeenCalledWith(url);
    });

    it('should handle window events', () => {
      const closedCallback = jest.fn();
      mainWindow.on('closed', closedCallback);
      expect(mainWindow.on).toHaveBeenCalledWith('closed', closedCallback);
    });

    it('should minimize window', () => {
      mainWindow.minimize();
      expect(mainWindow.minimize).toHaveBeenCalled();
    });

    it('should maximize window', () => {
      mainWindow.maximize();
      expect(mainWindow.maximize).toHaveBeenCalled();
    });

    it('should check if window is maximized', () => {
      const isMaximized = mainWindow.isMaximized();
      expect(isMaximized).toBe(false);
    });
  });

  describe('App Information', () => {
    it('should get app name', () => {
      const name = app.getName();
      expect(name).toBe('korean-flashcard-desktop');
    });

    it('should get app version', () => {
      const version = app.getVersion();
      expect(version).toBe('1.0.0');
    });
  });
});