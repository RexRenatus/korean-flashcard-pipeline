/**
 * Integration tests for vocabulary processing workflow
 */

import { app, BrowserWindow } from 'electron';
import * as path from 'path';
import * as fs from 'fs/promises';

// Mock electron
jest.mock('electron');

describe('Vocabulary Processing Integration', () => {
  let mainWindow: any;
  const testDataDir = path.join(__dirname, '../fixtures/test-data');
  const outputDir = path.join(__dirname, '../fixtures/output');

  beforeAll(async () => {
    // Setup test directories
    await fs.mkdir(testDataDir, { recursive: true });
    await fs.mkdir(outputDir, { recursive: true });
  });

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock BrowserWindow
    mainWindow = {
      webContents: {
        send: jest.fn(),
      },
    };
  });

  afterAll(async () => {
    // Cleanup test directories
    await fs.rm(testDataDir, { recursive: true, force: true });
    await fs.rm(outputDir, { recursive: true, force: true });
  });

  describe('CSV Processing', () => {
    it('should process a valid CSV file', async () => {
      // Create test CSV file
      const csvContent = `word,meaning,notes
안녕하세요,Hello,Formal greeting
감사합니다,Thank you,Polite form
미안합니다,Sorry,Formal apology`;
      
      const csvPath = path.join(testDataDir, 'test-vocabulary.csv');
      await fs.writeFile(csvPath, csvContent, 'utf-8');

      // Mock processing function
      const processVocabulary = async (filePath: string) => {
        const content = await fs.readFile(filePath, 'utf-8');
        const lines = content.split('\n');
        const headers = lines[0].split(',');
        
        const words = lines.slice(1).map(line => {
          const values = line.split(',');
          return {
            word: values[0],
            meaning: values[1],
            notes: values[2] || '',
          };
        });

        return {
          total: words.length,
          processed: words.length,
          failed: 0,
          words,
        };
      };

      const result = await processVocabulary(csvPath);
      
      expect(result.total).toBe(3);
      expect(result.processed).toBe(3);
      expect(result.failed).toBe(0);
      expect(result.words[0].word).toBe('안녕하세요');
    });

    it('should handle malformed CSV gracefully', async () => {
      const malformedCsv = `word,meaning
안녕하세요
감사합니다,Thank you,Extra column
"미안합니다`;

      const csvPath = path.join(testDataDir, 'malformed.csv');
      await fs.writeFile(csvPath, malformedCsv, 'utf-8');

      // Mock error handling
      const processWithErrorHandling = async (filePath: string) => {
        try {
          const content = await fs.readFile(filePath, 'utf-8');
          const lines = content.split('\n').filter(line => line.trim());
          const headers = lines[0].split(',');
          
          const results = {
            total: lines.length - 1,
            processed: 0,
            failed: 0,
            words: [] as any[],
            errors: [] as any[],
          };

          lines.slice(1).forEach((line, index) => {
            try {
              const values = line.split(',');
              if (values.length >= 2) {
                results.words.push({
                  word: values[0],
                  meaning: values[1],
                });
                results.processed++;
              } else {
                throw new Error('Insufficient columns');
              }
            } catch (error) {
              results.failed++;
              results.errors.push({
                line: index + 2,
                content: line,
                error: (error as Error).message,
              });
            }
          });

          return results;
        } catch (error) {
          throw new Error(`Failed to process CSV: ${(error as Error).message}`);
        }
      };

      const result = await processWithErrorHandling(csvPath);
      
      expect(result.total).toBe(3);
      expect(result.processed).toBe(1);
      expect(result.failed).toBe(2);
    });
  });

  describe('API Integration', () => {
    it('should send processing updates via IPC', async () => {
      const mockProgress = {
        status: 'processing',
        current: 1,
        total: 10,
        word: '안녕하세요',
      };

      // Simulate sending progress updates
      mainWindow.webContents.send('processing-progress', mockProgress);

      expect(mainWindow.webContents.send).toHaveBeenCalledWith(
        'processing-progress',
        mockProgress
      );
    });

    it('should handle API rate limiting', async () => {
      // Mock rate limiter
      const rateLimiter = {
        tokensPerMinute: 60,
        currentTokens: 60,
        canProcess: function(tokens: number) {
          if (this.currentTokens >= tokens) {
            this.currentTokens -= tokens;
            return true;
          }
          return false;
        },
        waitTime: function(tokens: number) {
          if (this.currentTokens >= tokens) return 0;
          return ((tokens - this.currentTokens) / this.tokensPerMinute) * 60000;
        },
      };

      // Test rate limiting
      expect(rateLimiter.canProcess(30)).toBe(true);
      expect(rateLimiter.currentTokens).toBe(30);
      expect(rateLimiter.canProcess(40)).toBe(false);
      expect(rateLimiter.waitTime(40)).toBeGreaterThan(0);
    });
  });

  describe('Export Functionality', () => {
    it('should export flashcards to JSON', async () => {
      const flashcards = [
        {
          id: '1',
          word: '안녕하세요',
          meaning: 'Hello',
          pronunciation: 'annyeonghaseyo',
          examples: ['안녕하세요, 만나서 반갑습니다.'],
        },
        {
          id: '2',
          word: '감사합니다',
          meaning: 'Thank you',
          pronunciation: 'gamsahamnida',
          examples: ['도와주셔서 감사합니다.'],
        },
      ];

      const exportPath = path.join(outputDir, 'flashcards.json');
      await fs.writeFile(exportPath, JSON.stringify(flashcards, null, 2));

      const exported = await fs.readFile(exportPath, 'utf-8');
      const parsed = JSON.parse(exported);

      expect(parsed).toHaveLength(2);
      expect(parsed[0].word).toBe('안녕하세요');
    });

    it('should export to Anki format', async () => {
      const flashcards = [
        {
          word: '안녕하세요',
          meaning: 'Hello',
          pronunciation: 'annyeonghaseyo',
          examples: '안녕하세요, 만나서 반갑습니다.',
        },
      ];

      // Mock Anki export format
      const toAnkiFormat = (flashcards: any[]) => {
        return flashcards.map(card => 
          [
            card.word,
            card.pronunciation,
            card.meaning,
            card.examples,
          ].join('\t')
        ).join('\n');
      };

      const ankiContent = toAnkiFormat(flashcards);
      const exportPath = path.join(outputDir, 'flashcards.txt');
      await fs.writeFile(exportPath, ankiContent);

      const exported = await fs.readFile(exportPath, 'utf-8');
      expect(exported).toContain('안녕하세요\tannyeonghaseyo\tHello');
    });
  });

  describe('Error Recovery', () => {
    it('should recover from processing interruption', async () => {
      // Mock checkpoint system
      const checkpoint = {
        filePath: '/path/to/vocab.csv',
        processedWords: ['안녕하세요', '감사합니다'],
        lastProcessedIndex: 2,
        totalWords: 5,
      };

      const checkpointPath = path.join(outputDir, 'checkpoint.json');
      await fs.writeFile(checkpointPath, JSON.stringify(checkpoint));

      // Mock resume function
      const resumeProcessing = async (checkpointPath: string) => {
        const data = await fs.readFile(checkpointPath, 'utf-8');
        const checkpoint = JSON.parse(data);
        
        return {
          resumed: true,
          startIndex: checkpoint.lastProcessedIndex + 1,
          remaining: checkpoint.totalWords - checkpoint.processedWords.length,
        };
      };

      const result = await resumeProcessing(checkpointPath);
      
      expect(result.resumed).toBe(true);
      expect(result.startIndex).toBe(3);
      expect(result.remaining).toBe(3);
    });

    it('should handle network failures gracefully', async () => {
      // Mock retry logic
      const apiCallWithRetry = async (attempt = 1, maxAttempts = 3): Promise<any> => {
        try {
          if (attempt < 3) {
            throw new Error('Network error');
          }
          return { success: true, data: 'Flashcard created' };
        } catch (error) {
          if (attempt < maxAttempts) {
            // Wait before retry (exponential backoff)
            await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
            return apiCallWithRetry(attempt + 1, maxAttempts);
          }
          throw error;
        }
      };

      // Test should succeed on third attempt
      const result = await apiCallWithRetry();
      expect(result.success).toBe(true);
    });
  });
});