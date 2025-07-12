const { app, BrowserWindow } = require('electron');
const path = require('path');

// Simple test to verify Electron can start
app.whenReady().then(() => {
  console.log('Electron app is ready!');
  console.log('App path:', app.getAppPath());
  console.log('User data path:', app.getPath('userData'));
  
  // Create a test window
  const win = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });
  
  // Load a simple test page
  win.loadURL('data:text/html,<h1>Electron Test Successful!</h1>');
  
  // Close after 3 seconds
  setTimeout(() => {
    console.log('Test completed successfully!');
    app.quit();
  }, 3000);
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});