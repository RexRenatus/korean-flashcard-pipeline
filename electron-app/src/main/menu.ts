import { Menu, MenuItemConstructorOptions, shell, app, BrowserWindow, dialog } from 'electron';
import { getAutoUpdaterService } from './services/AutoUpdaterService';
import { getBackupService } from './services/BackupService';
import { getTelemetryService } from './services/TelemetryService';

export function createApplicationMenu(mainWindow: BrowserWindow): Menu {
  const isMac = process.platform === 'darwin';
  const isDevelopment = process.env.NODE_ENV !== 'production';

  const template: MenuItemConstructorOptions[] = [
    // App Menu (macOS only)
    ...(isMac
      ? [{
          label: app.getName(),
          submenu: [
            { role: 'about' as const },
            { type: 'separator' as const },
            {
              label: 'Preferences...',
              accelerator: 'CmdOrCtrl+,',
              click: () => {
                mainWindow.webContents.send('navigate', '/settings');
              },
            },
            { type: 'separator' as const },
            {
              label: 'Check for Updates...',
              click: async () => {
                const autoUpdater = getAutoUpdaterService();
                await autoUpdater.checkForUpdates();
              },
            },
            { type: 'separator' as const },
            { role: 'services' as const },
            { type: 'separator' as const },
            { role: 'hide' as const },
            { role: 'hideOthers' as const },
            { role: 'unhide' as const },
            { type: 'separator' as const },
            { role: 'quit' as const },
          ],
        }]
      : []),

    // File Menu
    {
      label: 'File',
      submenu: [
        {
          label: 'New Vocabulary',
          accelerator: 'CmdOrCtrl+N',
          click: () => {
            mainWindow.webContents.send('menu:new-vocabulary');
          },
        },
        {
          label: 'Import...',
          accelerator: 'CmdOrCtrl+I',
          click: () => {
            mainWindow.webContents.send('menu:import');
          },
        },
        {
          label: 'Export...',
          accelerator: 'CmdOrCtrl+E',
          click: () => {
            mainWindow.webContents.send('menu:export');
          },
        },
        { type: 'separator' },
        {
          label: 'Backup',
          submenu: [
            {
              label: 'Create Backup...',
              click: async () => {
                const backup = getBackupService();
                try {
                  const backupPath = await backup.createBackup();
                  dialog.showMessageBox(mainWindow, {
                    type: 'info',
                    title: 'Backup Created',
                    message: 'Backup created successfully',
                    detail: `Backup saved to: ${backupPath}`,
                    buttons: ['OK'],
                  });
                } catch (error) {
                  dialog.showErrorBox('Backup Failed', error.message);
                }
              },
            },
            {
              label: 'Restore Backup...',
              click: async () => {
                const result = await dialog.showOpenDialog(mainWindow, {
                  title: 'Select Backup File',
                  filters: [{ name: 'Backup Files', extensions: ['zip'] }],
                  properties: ['openFile'],
                });

                if (!result.canceled && result.filePaths.length > 0) {
                  const backup = getBackupService();
                  try {
                    await backup.restoreBackup(result.filePaths[0]);
                    dialog.showMessageBox(mainWindow, {
                      type: 'info',
                      title: 'Restore Complete',
                      message: 'Backup restored successfully',
                      detail: 'The application will restart to apply changes.',
                      buttons: ['Restart Now'],
                    }).then(() => {
                      app.relaunch();
                      app.exit();
                    });
                  } catch (error) {
                    dialog.showErrorBox('Restore Failed', error.message);
                  }
                }
              },
            },
          ],
        },
        { type: 'separator' },
        ...(!isMac
          ? [
              {
                label: 'Settings',
                accelerator: 'CmdOrCtrl+,',
                click: () => {
                  mainWindow.webContents.send('navigate', '/settings');
                },
              },
              { type: 'separator' as const },
              { role: 'quit' as const },
            ]
          : []),
      ],
    },

    // Edit Menu
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
        ...(isMac
          ? [
              { role: 'pasteAndMatchStyle' as const },
              { role: 'delete' as const },
              { role: 'selectAll' as const },
              { type: 'separator' as const },
              {
                label: 'Speech',
                submenu: [
                  { role: 'startSpeaking' as const },
                  { role: 'stopSpeaking' as const },
                ],
              },
            ]
          : [
              { role: 'delete' as const },
              { type: 'separator' as const },
              { role: 'selectAll' as const },
            ]),
      ],
    },

    // View Menu
    {
      label: 'View',
      submenu: [
        {
          label: 'Dashboard',
          accelerator: 'CmdOrCtrl+D',
          click: () => {
            mainWindow.webContents.send('navigate', '/dashboard');
          },
        },
        {
          label: 'Vocabulary',
          accelerator: 'CmdOrCtrl+V',
          click: () => {
            mainWindow.webContents.send('navigate', '/vocabulary');
          },
        },
        {
          label: 'Processing',
          accelerator: 'CmdOrCtrl+P',
          click: () => {
            mainWindow.webContents.send('navigate', '/processing');
          },
        },
        {
          label: 'Flashcards',
          accelerator: 'CmdOrCtrl+F',
          click: () => {
            mainWindow.webContents.send('navigate', '/flashcards');
          },
        },
        { type: 'separator' },
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
      ],
    },

    // Window Menu
    {
      label: 'Window',
      submenu: [
        { role: 'minimize' },
        { role: 'close' },
        ...(isMac
          ? [
              { type: 'separator' as const },
              { role: 'front' as const },
              { type: 'separator' as const },
              { role: 'window' as const },
            ]
          : []),
      ],
    },

    // Help Menu
    {
      role: 'help',
      submenu: [
        {
          label: 'Keyboard Shortcuts',
          accelerator: 'Shift+?',
          click: () => {
            mainWindow.webContents.send('menu:show-shortcuts');
          },
        },
        { type: 'separator' },
        {
          label: 'Documentation',
          click: async () => {
            await shell.openExternal('https://github.com/yourrepo/docs');
          },
        },
        {
          label: 'Report Issue',
          click: async () => {
            await shell.openExternal('https://github.com/yourrepo/issues/new');
          },
        },
        { type: 'separator' },
        {
          label: 'View Logs',
          click: async () => {
            const logsPath = app.getPath('logs');
            await shell.openPath(logsPath);
          },
        },
        {
          label: 'Telemetry',
          submenu: [
            {
              label: 'View Statistics',
              click: async () => {
                const telemetry = getTelemetryService();
                const stats = await telemetry.getStats();
                dialog.showMessageBox(mainWindow, {
                  type: 'info',
                  title: 'Telemetry Statistics',
                  message: 'Telemetry Data',
                  detail: JSON.stringify(stats, null, 2),
                  buttons: ['OK'],
                });
              },
            },
            {
              label: 'Clear Data',
              click: async () => {
                const result = await dialog.showMessageBox(mainWindow, {
                  type: 'warning',
                  title: 'Clear Telemetry Data',
                  message: 'Are you sure you want to clear all telemetry data?',
                  buttons: ['Cancel', 'Clear'],
                  defaultId: 0,
                  cancelId: 0,
                });

                if (result.response === 1) {
                  const telemetry = getTelemetryService();
                  await telemetry.clearAllData();
                  dialog.showMessageBox(mainWindow, {
                    type: 'info',
                    title: 'Data Cleared',
                    message: 'Telemetry data has been cleared.',
                    buttons: ['OK'],
                  });
                }
              },
            },
          ],
        },
        { type: 'separator' },
        ...(!isMac
          ? [
              {
                label: 'Check for Updates...',
                click: async () => {
                  const autoUpdater = getAutoUpdaterService();
                  await autoUpdater.checkForUpdates();
                },
              },
              { type: 'separator' as const },
              {
                label: 'About',
                click: () => {
                  dialog.showMessageBox(mainWindow, {
                    type: 'info',
                    title: 'About',
                    message: app.getName(),
                    detail: `Version: ${app.getVersion()}\nElectron: ${process.versions.electron}\nNode: ${process.versions.node}`,
                    buttons: ['OK'],
                  });
                },
              },
            ]
          : []),
      ],
    },
  ];

  return Menu.buildFromTemplate(template);
}