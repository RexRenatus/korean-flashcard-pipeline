/**
 * Jest setup file for renderer process tests
 * This file runs before each test file in the renderer environment
 */

import '@testing-library/jest-dom';
import { TextEncoder, TextDecoder } from 'util';

// Polyfill for TextEncoder/TextDecoder in jsdom environment
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder as any;

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock ResizeObserver
global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock IntersectionObserver
global.IntersectionObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
  root: null,
  rootMargin: '',
  thresholds: [],
}));

// Mock electron APIs for renderer process
window.electronAPI = {
  // File operations
  selectFile: jest.fn(),
  selectFiles: jest.fn(),
  selectDirectory: jest.fn(),
  readFile: jest.fn(),
  writeFile: jest.fn(),
  fileExists: jest.fn(),
  
  // Process operations
  processVocabulary: jest.fn(),
  cancelProcessing: jest.fn(),
  getProcessingStatus: jest.fn(),
  
  // Database operations
  getFlashcards: jest.fn(),
  searchFlashcards: jest.fn(),
  exportFlashcards: jest.fn(),
  importFlashcards: jest.fn(),
  getStats: jest.fn(),
  
  // Settings
  getSettings: jest.fn(),
  updateSettings: jest.fn(),
  
  // App info
  getAppVersion: jest.fn(),
  checkForUpdates: jest.fn(),
  
  // Event listeners
  on: jest.fn(),
  off: jest.fn(),
  once: jest.fn(),
  
  // Window controls
  minimizeWindow: jest.fn(),
  maximizeWindow: jest.fn(),
  closeWindow: jest.fn(),
  isMaximized: jest.fn(),
  
  // System
  openExternal: jest.fn(),
  showItemInFolder: jest.fn(),
  getSystemInfo: jest.fn(),
};

// Mock Notification API
global.Notification = jest.fn().mockImplementation(() => ({
  close: jest.fn(),
})) as any;

(global.Notification as any).permission = 'granted';
(global.Notification as any).requestPermission = jest.fn().mockResolvedValue('granted');

// Suppress console errors during tests (optional)
const originalError = console.error;
beforeAll(() => {
  console.error = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      args[0].includes('Warning: ReactDOM.render')
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});

// Clean up after each test
afterEach(() => {
  jest.clearAllMocks();
});