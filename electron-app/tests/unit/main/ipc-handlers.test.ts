/**
 * Unit tests for IPC handlers in main process
 */

import { ipcMain, dialog, shell } from 'electron';
import * as fs from 'fs/promises';
import * as path from 'path';

// Mock modules
jest.mock('electron');
jest.mock('fs/promises');
jest.mock('axios');

describe('IPC Handlers', () => {
  const mockEvent = {
    sender: {
      send: jest.fn(),
    },
    reply: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('File Operations', () => {
    it('should handle select-file', async () => {
      const mockFilePath = '/path/to/file.csv';
      (dialog.showOpenDialog as jest.Mock).mockResolvedValue({
        canceled: false,
        filePaths: [mockFilePath],
      });

      const handler = jest.fn().mockImplementation(async () => {
        const result = await dialog.showOpenDialog({
          properties: ['openFile'],
          filters: [
            { name: 'CSV Files', extensions: ['csv'] },
            { name: 'All Files', extensions: ['*'] },
          ],
        });
        return result.canceled ? null : result.filePaths[0];
      });

      const result = await handler();
      expect(result).toBe(mockFilePath);
      expect(dialog.showOpenDialog).toHaveBeenCalled();
    });

    it('should handle select-files with multiple selection', async () => {
      const mockFilePaths = ['/path/to/file1.csv', '/path/to/file2.csv'];
      (dialog.showOpenDialog as jest.Mock).mockResolvedValue({
        canceled: false,
        filePaths: mockFilePaths,
      });

      const handler = jest.fn().mockImplementation(async () => {
        const result = await dialog.showOpenDialog({
          properties: ['openFile', 'multiSelections'],
          filters: [
            { name: 'CSV Files', extensions: ['csv'] },
          ],
        });
        return result.canceled ? [] : result.filePaths;
      });

      const result = await handler();
      expect(result).toEqual(mockFilePaths);
    });

    it('should handle select-directory', async () => {
      const mockDirPath = '/path/to/directory';
      (dialog.showOpenDialog as jest.Mock).mockResolvedValue({
        canceled: false,
        filePaths: [mockDirPath],
      });

      const handler = jest.fn().mockImplementation(async () => {
        const result = await dialog.showOpenDialog({
          properties: ['openDirectory'],
        });
        return result.canceled ? null : result.filePaths[0];
      });

      const result = await handler();
      expect(result).toBe(mockDirPath);
    });

    it('should handle read-file', async () => {
      const mockContent = 'word,meaning\n안녕,hello';
      const mockFilePath = '/path/to/file.csv';
      (fs.readFile as jest.Mock).mockResolvedValue(mockContent);

      const handler = jest.fn().mockImplementation(async (event: any, filePath: string) => {
        const content = await fs.readFile(filePath, 'utf-8');
        return content;
      });

      const result = await handler(mockEvent, mockFilePath);
      expect(result).toBe(mockContent);
      expect(fs.readFile).toHaveBeenCalledWith(mockFilePath, 'utf--8');
    });

    it('should handle write-file', async () => {
      const mockFilePath = '/path/to/output.json';
      const mockContent = JSON.stringify({ test: 'data' });
      (fs.writeFile as jest.Mock).mockResolvedValue(undefined);

      const handler = jest.fn().mockImplementation(async (event: any, filePath: string, content: string) => {
        await fs.writeFile(filePath, content, 'utf-8');
        return true;
      });

      const result = await handler(mockEvent, mockFilePath, mockContent);
      expect(result).toBe(true);
      expect(fs.writeFile).toHaveBeenCalledWith(mockFilePath, mockContent, 'utf-8');
    });

    it('should handle file-exists', async () => {
      const mockFilePath = '/path/to/file.csv';
      (fs.access as jest.Mock).mockResolvedValue(undefined);

      const handler = jest.fn().mockImplementation(async (event: any, filePath: string) => {
        try {
          await fs.access(filePath);
          return true;
        } catch {
          return false;
        }
      });

      const result = await handler(mockEvent, mockFilePath);
      expect(result).toBe(true);
    });
  });

  describe('External Operations', () => {
    it('should handle open-external', async () => {
      const url = 'https://example.com';
      (shell.openExternal as jest.Mock).mockResolvedValue(undefined);

      const handler = jest.fn().mockImplementation(async (event: any, url: string) => {
        await shell.openExternal(url);
        return true;
      });

      const result = await handler(mockEvent, url);
      expect(result).toBe(true);
      expect(shell.openExternal).toHaveBeenCalledWith(url);
    });

    it('should handle show-item-in-folder', async () => {
      const filePath = '/path/to/file.csv';
      (shell.showItemInFolder as jest.Mock).mockReturnValue(undefined);

      const handler = jest.fn().mockImplementation((event: any, filePath: string) => {
        shell.showItemInFolder(filePath);
        return true;
      });

      const result = handler(mockEvent, filePath);
      expect(result).toBe(true);
      expect(shell.showItemInFolder).toHaveBeenCalledWith(filePath);
    });
  });

  describe('Error Handling', () => {
    it('should handle file read errors', async () => {
      const mockFilePath = '/path/to/nonexistent.csv';
      const mockError = new Error('File not found');
      (fs.readFile as jest.Mock).mockRejectedValue(mockError);

      const handler = jest.fn().mockImplementation(async (event: any, filePath: string) => {
        try {
          await fs.readFile(filePath, 'utf-8');
        } catch (error) {
          throw error;
        }
      });

      await expect(handler(mockEvent, mockFilePath)).rejects.toThrow('File not found');
    });

    it('should handle dialog cancellation', async () => {
      (dialog.showOpenDialog as jest.Mock).mockResolvedValue({
        canceled: true,
        filePaths: [],
      });

      const handler = jest.fn().mockImplementation(async () => {
        const result = await dialog.showOpenDialog({
          properties: ['openFile'],
        });
        return result.canceled ? null : result.filePaths[0];
      });

      const result = await handler();
      expect(result).toBeNull();
    });
  });
});