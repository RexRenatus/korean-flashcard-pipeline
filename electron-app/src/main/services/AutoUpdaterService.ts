import { app, BrowserWindow, dialog, ipcMain } from 'electron';
import { autoUpdater } from 'electron-updater';
import { EventEmitter } from 'events';
import * as path from 'path';

interface UpdateInfo {
  version: string;
  releaseDate: string;
  releaseNotes?: string;
  releaseName?: string;
}

export class AutoUpdaterService extends EventEmitter {
  private mainWindow: BrowserWindow | null = null;
  private isChecking: boolean = false;
  private updateAvailable: boolean = false;
  private downloadProgress: number = 0;
  private updateInfo: UpdateInfo | null = null;

  constructor() {
    super();
    this.setupAutoUpdater();
    this.setupIpcHandlers();
  }

  public setMainWindow(window: BrowserWindow) {
    this.mainWindow = window;
  }

  private setupAutoUpdater() {
    // Configure auto-updater
    autoUpdater.autoDownload = false;
    autoUpdater.autoInstallOnAppQuit = true;

    // Set up event handlers
    autoUpdater.on('checking-for-update', () => {
      this.isChecking = true;
      this.sendStatusToWindow('checking-for-update');
      this.emit('checking-for-update');
    });

    autoUpdater.on('update-available', (info: UpdateInfo) => {
      this.isChecking = false;
      this.updateAvailable = true;
      this.updateInfo = info;
      this.sendStatusToWindow('update-available', info);
      this.emit('update-available', info);
      
      // Show notification dialog
      this.showUpdateAvailableDialog(info);
    });

    autoUpdater.on('update-not-available', () => {
      this.isChecking = false;
      this.updateAvailable = false;
      this.sendStatusToWindow('update-not-available');
      this.emit('update-not-available');
    });

    autoUpdater.on('error', (error: Error) => {
      this.isChecking = false;
      this.sendStatusToWindow('update-error', error);
      this.emit('error', error);
      console.error('Auto-updater error:', error);
    });

    autoUpdater.on('download-progress', (progressObj: any) => {
      this.downloadProgress = progressObj.percent;
      this.sendStatusToWindow('download-progress', progressObj);
      this.emit('download-progress', progressObj);
    });

    autoUpdater.on('update-downloaded', (info: UpdateInfo) => {
      this.sendStatusToWindow('update-downloaded', info);
      this.emit('update-downloaded', info);
      
      // Show restart dialog
      this.showUpdateReadyDialog(info);
    });
  }

  private setupIpcHandlers() {
    ipcMain.handle('updater:check', async () => {
      return this.checkForUpdates();
    });

    ipcMain.handle('updater:download', async () => {
      return this.downloadUpdate();
    });

    ipcMain.handle('updater:install', async () => {
      return this.installUpdate();
    });

    ipcMain.handle('updater:getStatus', async () => {
      return {
        isChecking: this.isChecking,
        updateAvailable: this.updateAvailable,
        downloadProgress: this.downloadProgress,
        updateInfo: this.updateInfo,
      };
    });
  }

  private sendStatusToWindow(status: string, data?: any) {
    if (this.mainWindow && !this.mainWindow.isDestroyed()) {
      this.mainWindow.webContents.send('updater:status', { status, data });
    }
  }

  public async checkForUpdates(): Promise<boolean> {
    if (this.isChecking) return false;

    try {
      const result = await autoUpdater.checkForUpdates();
      return result !== null;
    } catch (error) {
      console.error('Failed to check for updates:', error);
      return false;
    }
  }

  public async downloadUpdate(): Promise<boolean> {
    if (!this.updateAvailable) return false;

    try {
      await autoUpdater.downloadUpdate();
      return true;
    } catch (error) {
      console.error('Failed to download update:', error);
      return false;
    }
  }

  public installUpdate() {
    autoUpdater.quitAndInstall(false, true);
  }

  private async showUpdateAvailableDialog(info: UpdateInfo) {
    const result = await dialog.showMessageBox(this.mainWindow!, {
      type: 'info',
      title: 'Update Available',
      message: `A new version (${info.version}) is available!`,
      detail: info.releaseNotes || 'A new update is available for download.',
      buttons: ['Download Now', 'Later'],
      defaultId: 0,
      cancelId: 1,
    });

    if (result.response === 0) {
      this.downloadUpdate();
    }
  }

  private async showUpdateReadyDialog(info: UpdateInfo) {
    const result = await dialog.showMessageBox(this.mainWindow!, {
      type: 'info',
      title: 'Update Ready',
      message: 'Update downloaded successfully!',
      detail: `Version ${info.version} has been downloaded and is ready to install. The application will restart to apply the update.`,
      buttons: ['Restart Now', 'Later'],
      defaultId: 0,
      cancelId: 1,
    });

    if (result.response === 0) {
      this.installUpdate();
    }
  }

  public async checkForUpdatesInBackground() {
    // Check for updates silently in background
    try {
      await autoUpdater.checkForUpdates();
    } catch (error) {
      // Silently fail for background checks
      console.error('Background update check failed:', error);
    }
  }

  public setFeedURL(url: string) {
    autoUpdater.setFeedURL(url);
  }

  public setAutoDownload(enabled: boolean) {
    autoUpdater.autoDownload = enabled;
  }

  public setAutoInstallOnAppQuit(enabled: boolean) {
    autoUpdater.autoInstallOnAppQuit = enabled;
  }
}

// Singleton instance
let autoUpdaterService: AutoUpdaterService | null = null;

export const getAutoUpdaterService = (): AutoUpdaterService => {
  if (!autoUpdaterService) {
    autoUpdaterService = new AutoUpdaterService();
  }
  return autoUpdaterService;
};