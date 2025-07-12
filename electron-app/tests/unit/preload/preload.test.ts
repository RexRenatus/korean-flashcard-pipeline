import { contextBridge, ipcRenderer } from 'electron';

// Mock electron modules
jest.mock('electron', () => ({
  contextBridge: {
    exposeInMainWorld: jest.fn()
  },
  ipcRenderer: {
    invoke: jest.fn(),
    send: jest.fn(),
    on: jest.fn(),
    once: jest.fn(),
    off: jest.fn(),
    removeAllListeners: jest.fn()
  }
}));

// Import after mocking
import '../../../src/preload/index';

describe('Preload Script', () => {
  let exposedAPI: any;

  beforeEach(() => {
    // Get the API that was exposed
    const exposeCall = (contextBridge.exposeInMainWorld as jest.Mock).mock.calls[0];
    expect(exposeCall[0]).toBe('electronAPI');
    exposedAPI = exposeCall[1];
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('API exposure', () => {
    it('should expose electronAPI to the window', () => {
      expect(contextBridge.exposeInMainWorld).toHaveBeenCalledWith(
        'electronAPI',
        expect.objectContaining({
          invoke: expect.any(Function),
          send: expect.any(Function),
          on: expect.any(Function),
          once: expect.any(Function),
          removeAllListeners: expect.any(Function)
        })
      );
    });
  });

  describe('invoke method', () => {
    it('should forward valid channel invocations', async () => {
      const mockResult = { data: 'test' };
      (ipcRenderer.invoke as jest.Mock).mockResolvedValue(mockResult);

      const result = await exposedAPI.invoke('db:get-vocabulary', { page: 1 });

      expect(ipcRenderer.invoke).toHaveBeenCalledWith('db:get-vocabulary', { page: 1 });
      expect(result).toEqual(mockResult);
    });

    it('should reject invalid channels', async () => {
      await expect(
        exposedAPI.invoke('invalid:channel')
      ).rejects.toThrow('Channel invalid:channel is not allowed');

      expect(ipcRenderer.invoke).not.toHaveBeenCalled();
    });
  });

  describe('send method', () => {
    it('should forward valid channel sends', () => {
      exposedAPI.send('window:minimize');

      expect(ipcRenderer.send).toHaveBeenCalledWith('window:minimize');
    });

    it('should reject invalid channels', () => {
      expect(() => {
        exposedAPI.send('invalid:channel');
      }).toThrow('Channel invalid:channel is not allowed');

      expect(ipcRenderer.send).not.toHaveBeenCalled();
    });
  });

  describe('on method', () => {
    it('should register listeners for valid channels', () => {
      const callback = jest.fn();
      const unsubscribe = exposedAPI.on('process:progress', callback);

      expect(ipcRenderer.on).toHaveBeenCalledWith(
        'process:progress',
        expect.any(Function)
      );

      // Test callback wrapping
      const wrappedCallback = (ipcRenderer.on as jest.Mock).mock.calls[0][1];
      wrappedCallback({}, { progress: 50 });

      expect(callback).toHaveBeenCalledWith({ progress: 50 });

      // Test unsubscribe
      unsubscribe();
      expect(ipcRenderer.off).toHaveBeenCalledWith(
        'process:progress',
        wrappedCallback
      );
    });

    it('should reject invalid channels', () => {
      expect(() => {
        exposedAPI.on('invalid:channel', jest.fn());
      }).toThrow('Channel invalid:channel is not allowed');

      expect(ipcRenderer.on).not.toHaveBeenCalled();
    });
  });

  describe('once method', () => {
    it('should register one-time listeners for valid channels', () => {
      const callback = jest.fn();
      exposedAPI.once('process:progress', callback);

      expect(ipcRenderer.once).toHaveBeenCalledWith(
        'process:progress',
        expect.any(Function)
      );

      // Test callback wrapping
      const wrappedCallback = (ipcRenderer.once as jest.Mock).mock.calls[0][1];
      wrappedCallback({}, { progress: 100 });

      expect(callback).toHaveBeenCalledWith({ progress: 100 });
    });

    it('should reject invalid channels', () => {
      expect(() => {
        exposedAPI.once('invalid:channel', jest.fn());
      }).toThrow('Channel invalid:channel is not allowed');

      expect(ipcRenderer.once).not.toHaveBeenCalled();
    });
  });

  describe('removeAllListeners method', () => {
    it('should remove listeners for valid channels', () => {
      exposedAPI.removeAllListeners('process:progress');

      expect(ipcRenderer.removeAllListeners).toHaveBeenCalledWith('process:progress');
    });

    it('should reject invalid channels', () => {
      expect(() => {
        exposedAPI.removeAllListeners('invalid:channel');
      }).toThrow('Channel invalid:channel is not allowed');

      expect(ipcRenderer.removeAllListeners).not.toHaveBeenCalled();
    });
  });

  describe('security', () => {
    it('should only allow whitelisted channels', () => {
      const validChannels = [
        'db:get-vocabulary',
        'db:add-vocabulary', 
        'process:start',
        'process:progress',
        'window:minimize'
      ];

      const invalidChannels = [
        'fs:read-file',
        'shell:execute',
        'app:quit',
        'custom:channel'
      ];

      // Test valid channels
      for (const channel of validChannels) {
        expect(() => exposedAPI.send(channel)).not.toThrow();
      }

      // Test invalid channels
      for (const channel of invalidChannels) {
        expect(() => exposedAPI.send(channel)).toThrow();
      }
    });
  });
});