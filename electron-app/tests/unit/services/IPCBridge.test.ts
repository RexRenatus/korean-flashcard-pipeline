import { IPCBridge } from '@/main/services/IPCBridge';
import { VocabularyItem, ProcessingTask, SystemStats } from '@/shared/types';
import { ChildProcess } from 'child_process';

// Mock child_process
jest.mock('child_process');

describe('IPCBridge', () => {
  let bridge: IPCBridge;
  let mockPythonProcess: jest.Mocked<ChildProcess>;

  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();
    
    // Create mock Python process
    mockPythonProcess = {
      stdin: {
        write: jest.fn(),
        end: jest.fn()
      },
      stdout: {
        on: jest.fn(),
        removeAllListeners: jest.fn()
      },
      stderr: {
        on: jest.fn(),
        removeAllListeners: jest.fn()
      },
      on: jest.fn(),
      kill: jest.fn(),
      pid: 12345
    } as any;

    bridge = new IPCBridge();
  });

  afterEach(async () => {
    await bridge.shutdown();
  });

  describe('initialization', () => {
    it('should initialize Python environment successfully', async () => {
      const spawnMock = jest.spyOn(require('child_process'), 'spawn')
        .mockReturnValue(mockPythonProcess);

      // Simulate successful initialization
      mockPythonProcess.stdout.on.mockImplementation((event, callback) => {
        if (event === 'data') {
          callback(Buffer.from(JSON.stringify({ 
            type: 'ready', 
            version: '1.0.0' 
          }) + '\n'));
        }
      });

      const result = await bridge.initialize();

      expect(result).toBe(true);
      expect(bridge.isReady()).toBe(true);
      expect(spawnMock).toHaveBeenCalledWith(
        'python',
        ['-m', 'flashcard_pipeline.ipc_server'],
        expect.objectContaining({
          cwd: expect.stringContaining('Anthropic_Flashcards')
        })
      );
    });

    it('should handle Python initialization errors', async () => {
      jest.spyOn(require('child_process'), 'spawn')
        .mockReturnValue(mockPythonProcess);

      // Simulate error
      mockPythonProcess.stderr.on.mockImplementation((event, callback) => {
        if (event === 'data') {
          callback(Buffer.from('Python error: Module not found'));
        }
      });

      await expect(bridge.initialize()).rejects.toThrow('Failed to initialize Python bridge');
      expect(bridge.isReady()).toBe(false);
    });

    it('should timeout if Python does not respond', async () => {
      jest.spyOn(require('child_process'), 'spawn')
        .mockReturnValue(mockPythonProcess);

      // Don't send any response
      const promise = bridge.initialize(1000); // 1 second timeout

      await expect(promise).rejects.toThrow('Python initialization timeout');
      expect(bridge.isReady()).toBe(false);
    });
  });

  describe('command execution', () => {
    beforeEach(async () => {
      // Setup successful initialization
      jest.spyOn(require('child_process'), 'spawn')
        .mockReturnValue(mockPythonProcess);

      mockPythonProcess.stdout.on.mockImplementation((event, callback) => {
        if (event === 'data') {
          callback(Buffer.from(JSON.stringify({ type: 'ready' }) + '\n'));
        }
      });

      await bridge.initialize();
    });

    it('should execute Python commands successfully', async () => {
      const mockResponse = {
        id: '123',
        result: { status: 'success', data: 'test' }
      };

      // Setup response handler
      const writeCallback = mockPythonProcess.stdin.write.mockImplementation((data, callback) => {
        // Simulate async response
        setImmediate(() => {
          const listeners = mockPythonProcess.stdout.on.mock.calls
            .filter(call => call[0] === 'data')
            .map(call => call[1]);
          
          listeners.forEach(listener => {
            listener(Buffer.from(JSON.stringify(mockResponse) + '\n'));
          });
        });
        if (callback) callback();
        return true;
      });

      const result = await bridge.execute('test_command', { param: 'value' });

      expect(result).toEqual(mockResponse.result);
      expect(mockPythonProcess.stdin.write).toHaveBeenCalled();
      
      const writtenData = JSON.parse(
        mockPythonProcess.stdin.write.mock.calls[0][0].toString()
      );
      expect(writtenData).toMatchObject({
        command: 'test_command',
        args: { param: 'value' }
      });
    });

    it('should handle Python command errors gracefully', async () => {
      const mockError = {
        id: '123',
        error: { code: 'PROCESSING_ERROR', message: 'Failed to process' }
      };

      mockPythonProcess.stdin.write.mockImplementation((data, callback) => {
        setImmediate(() => {
          const listeners = mockPythonProcess.stdout.on.mock.calls
            .filter(call => call[0] === 'data')
            .map(call => call[1]);
          
          listeners.forEach(listener => {
            listener(Buffer.from(JSON.stringify(mockError) + '\n'));
          });
        });
        if (callback) callback();
        return true;
      });

      await expect(bridge.execute('failing_command')).rejects.toThrow('Failed to process');
    });

    it('should handle command timeouts', async () => {
      // Don't send any response
      mockPythonProcess.stdin.write.mockImplementation(() => true);

      await expect(
        bridge.execute('slow_command', {}, 100) // 100ms timeout
      ).rejects.toThrow('Command timeout');
    });
  });

  describe('vocabulary operations', () => {
    beforeEach(async () => {
      jest.spyOn(require('child_process'), 'spawn')
        .mockReturnValue(mockPythonProcess);

      mockPythonProcess.stdout.on.mockImplementation((event, callback) => {
        if (event === 'data') {
          callback(Buffer.from(JSON.stringify({ type: 'ready' }) + '\n'));
        }
      });

      await bridge.initialize();
    });

    it('should process vocabulary items', async () => {
      const vocabularyItems = ['안녕하세요', '감사합니다'];
      const mockResult = {
        processed: 2,
        failed: 0,
        results: [
          { word: '안녕하세요', status: 'completed' },
          { word: '감사합니다', status: 'completed' }
        ]
      };

      mockPythonProcess.stdin.write.mockImplementation((data, callback) => {
        setImmediate(() => {
          const parsedData = JSON.parse(data.toString());
          const response = {
            id: parsedData.id,
            result: mockResult
          };
          
          const listeners = mockPythonProcess.stdout.on.mock.calls
            .filter(call => call[0] === 'data')
            .map(call => call[1]);
          
          listeners.forEach(listener => {
            listener(Buffer.from(JSON.stringify(response) + '\n'));
          });
        });
        if (callback) callback();
        return true;
      });

      const result = await bridge.processVocabulary(vocabularyItems);

      expect(result).toEqual(mockResult);
      expect(mockPythonProcess.stdin.write).toHaveBeenCalledWith(
        expect.stringContaining('process_vocabulary'),
        expect.any(Function)
      );
    });

    it('should get vocabulary list with filters', async () => {
      const mockVocabulary: VocabularyItem[] = [
        {
          id: 1,
          korean: '안녕',
          english: 'hello',
          isActive: true,
          createdAt: '2024-01-01',
          updatedAt: '2024-01-01'
        }
      ];

      mockPythonProcess.stdin.write.mockImplementation((data, callback) => {
        setImmediate(() => {
          const parsedData = JSON.parse(data.toString());
          const response = {
            id: parsedData.id,
            result: mockVocabulary
          };
          
          const listeners = mockPythonProcess.stdout.on.mock.calls
            .filter(call => call[0] === 'data')
            .map(call => call[1]);
          
          listeners.forEach(listener => {
            listener(Buffer.from(JSON.stringify(response) + '\n'));
          });
        });
        if (callback) callback();
        return true;
      });

      const result = await bridge.getVocabularyList({ 
        limit: 10, 
        offset: 0, 
        status: 'active' 
      });

      expect(result).toEqual(mockVocabulary);
      expect(mockPythonProcess.stdin.write).toHaveBeenCalledWith(
        expect.stringContaining('get_vocabulary'),
        expect.any(Function)
      );
    });
  });

  describe('database operations', () => {
    beforeEach(async () => {
      jest.spyOn(require('child_process'), 'spawn')
        .mockReturnValue(mockPythonProcess);

      mockPythonProcess.stdout.on.mockImplementation((event, callback) => {
        if (event === 'data') {
          callback(Buffer.from(JSON.stringify({ type: 'ready' }) + '\n'));
        }
      });

      await bridge.initialize();
    });

    it('should handle database queries', async () => {
      const mockStats: SystemStats = {
        totalWords: 1000,
        processedWords: 800,
        pendingWords: 150,
        failedWords: 50,
        cacheHitRate: 0.85,
        averageProcessingTime: 1.2,
        apiHealth: 'healthy',
        lastSync: '2024-01-01T00:00:00Z'
      };

      mockPythonProcess.stdin.write.mockImplementation((data, callback) => {
        setImmediate(() => {
          const parsedData = JSON.parse(data.toString());
          const response = {
            id: parsedData.id,
            result: mockStats
          };
          
          const listeners = mockPythonProcess.stdout.on.mock.calls
            .filter(call => call[0] === 'data')
            .map(call => call[1]);
          
          listeners.forEach(listener => {
            listener(Buffer.from(JSON.stringify(response) + '\n'));
          });
        });
        if (callback) callback();
        return true;
      });

      const result = await bridge.getSystemStats();

      expect(result).toEqual(mockStats);
    });

    it('should handle database connection errors', async () => {
      mockPythonProcess.stdin.write.mockImplementation((data, callback) => {
        setImmediate(() => {
          const parsedData = JSON.parse(data.toString());
          const response = {
            id: parsedData.id,
            error: {
              code: 'DB_CONNECTION_ERROR',
              message: 'Unable to connect to database'
            }
          };
          
          const listeners = mockPythonProcess.stdout.on.mock.calls
            .filter(call => call[0] === 'data')
            .map(call => call[1]);
          
          listeners.forEach(listener => {
            listener(Buffer.from(JSON.stringify(response) + '\n'));
          });
        });
        if (callback) callback();
        return true;
      });

      await expect(bridge.getSystemStats()).rejects.toThrow('Unable to connect to database');
    });
  });

  describe('error handling and recovery', () => {
    it('should restart Python process on crash', async () => {
      jest.spyOn(require('child_process'), 'spawn')
        .mockReturnValue(mockPythonProcess);

      mockPythonProcess.stdout.on.mockImplementation((event, callback) => {
        if (event === 'data') {
          callback(Buffer.from(JSON.stringify({ type: 'ready' }) + '\n'));
        }
      });

      await bridge.initialize();

      // Simulate process crash
      const exitCallback = mockPythonProcess.on.mock.calls
        .find(call => call[0] === 'exit')[1];
      
      exitCallback(1, null);

      // Should attempt to restart
      expect(bridge.isReady()).toBe(false);
      
      // Verify restart attempt
      const restartPromise = bridge.execute('test_command');
      await expect(restartPromise).rejects.toThrow();
    });

    it('should handle malformed responses', async () => {
      jest.spyOn(require('child_process'), 'spawn')
        .mockReturnValue(mockPythonProcess);

      mockPythonProcess.stdout.on.mockImplementation((event, callback) => {
        if (event === 'data') {
          if (mockPythonProcess.stdout.on.mock.calls.length === 1) {
            callback(Buffer.from(JSON.stringify({ type: 'ready' }) + '\n'));
          } else {
            // Send malformed JSON
            callback(Buffer.from('{ invalid json }'));
          }
        }
      });

      await bridge.initialize();

      await expect(bridge.execute('test_command')).rejects.toThrow();
    });
  });

  describe('shutdown', () => {
    it('should gracefully shutdown Python process', async () => {
      jest.spyOn(require('child_process'), 'spawn')
        .mockReturnValue(mockPythonProcess);

      mockPythonProcess.stdout.on.mockImplementation((event, callback) => {
        if (event === 'data') {
          callback(Buffer.from(JSON.stringify({ type: 'ready' }) + '\n'));
        }
      });

      await bridge.initialize();
      await bridge.shutdown();

      expect(mockPythonProcess.kill).toHaveBeenCalledWith('SIGTERM');
      expect(bridge.isReady()).toBe(false);
    });

    it('should force kill if graceful shutdown fails', async () => {
      jest.spyOn(require('child_process'), 'spawn')
        .mockReturnValue(mockPythonProcess);

      mockPythonProcess.stdout.on.mockImplementation((event, callback) => {
        if (event === 'data') {
          callback(Buffer.from(JSON.stringify({ type: 'ready' }) + '\n'));
        }
      });

      // Make kill fail initially
      mockPythonProcess.kill.mockReturnValue(false);

      await bridge.initialize();
      await bridge.shutdown();

      // Should try SIGTERM first, then SIGKILL
      expect(mockPythonProcess.kill).toHaveBeenCalledWith('SIGTERM');
      expect(mockPythonProcess.kill).toHaveBeenCalledWith('SIGKILL');
    });
  });
});