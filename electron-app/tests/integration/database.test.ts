/**
 * Integration tests for database operations
 */

import * as path from 'path';
import * as fs from 'fs/promises';
import Database from 'better-sqlite3';

describe('Database Integration', () => {
  let db: Database.Database;
  const testDbPath = path.join(__dirname, '../fixtures/test.db');

  beforeEach(async () => {
    // Ensure directory exists
    await fs.mkdir(path.dirname(testDbPath), { recursive: true });
    
    // Create new database for each test
    db = new Database(testDbPath);
    
    // Create tables
    db.exec(`
      CREATE TABLE IF NOT EXISTS flashcards (
        id TEXT PRIMARY KEY,
        word TEXT NOT NULL,
        meaning TEXT NOT NULL,
        pronunciation TEXT,
        part_of_speech TEXT,
        difficulty_level INTEGER DEFAULT 3,
        examples TEXT,
        usage_notes TEXT,
        cultural_notes TEXT,
        mnemonics TEXT,
        related_words TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_reviewed DATETIME,
        review_count INTEGER DEFAULT 0,
        success_rate REAL DEFAULT 0.0
      );

      CREATE TABLE IF NOT EXISTS processing_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT NOT NULL,
        total_words INTEGER NOT NULL,
        processed_words INTEGER NOT NULL,
        failed_words INTEGER NOT NULL,
        status TEXT NOT NULL,
        started_at DATETIME NOT NULL,
        completed_at DATETIME,
        error_details TEXT
      );

      CREATE TABLE IF NOT EXISTS api_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider TEXT NOT NULL,
        model TEXT NOT NULL,
        tokens_used INTEGER NOT NULL,
        cost REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
      );

      CREATE INDEX IF NOT EXISTS idx_flashcards_word ON flashcards(word);
      CREATE INDEX IF NOT EXISTS idx_flashcards_difficulty ON flashcards(difficulty_level);
      CREATE INDEX IF NOT EXISTS idx_processing_history_status ON processing_history(status);
    `);
  });

  afterEach(async () => {
    // Close database
    if (db) db.close();
    
    // Remove test database
    await fs.unlink(testDbPath).catch(() => {});
  });

  describe('Flashcard Operations', () => {
    it('should insert a new flashcard', () => {
      const flashcard = {
        id: 'test-id-1',
        word: '안녕하세요',
        meaning: 'Hello (formal)',
        pronunciation: 'annyeonghaseyo',
        part_of_speech: 'interjection',
        difficulty_level: 2,
        examples: JSON.stringify(['안녕하세요, 만나서 반갑습니다.']),
        usage_notes: 'Used as a formal greeting',
        cultural_notes: 'Commonly used in formal situations',
        mnemonics: 'Sounds like "on your hay so"',
        related_words: JSON.stringify(['안녕', '안녕히']),
      };

      const stmt = db.prepare(`
        INSERT INTO flashcards (
          id, word, meaning, pronunciation, part_of_speech,
          difficulty_level, examples, usage_notes, cultural_notes,
          mnemonics, related_words
        ) VALUES (
          @id, @word, @meaning, @pronunciation, @part_of_speech,
          @difficulty_level, @examples, @usage_notes, @cultural_notes,
          @mnemonics, @related_words
        )
      `);

      const result = stmt.run(flashcard);
      expect(result.changes).toBe(1);

      // Verify insertion
      const retrieved = db.prepare('SELECT * FROM flashcards WHERE id = ?').get(flashcard.id);
      expect(retrieved).toBeDefined();
      expect(retrieved.word).toBe(flashcard.word);
    });

    it('should update an existing flashcard', () => {
      // First insert
      const flashcardId = 'test-id-2';
      db.prepare('INSERT INTO flashcards (id, word, meaning) VALUES (?, ?, ?)')
        .run(flashcardId, '감사합니다', 'Thank you');

      // Then update
      const updateStmt = db.prepare(`
        UPDATE flashcards 
        SET pronunciation = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
      `);
      
      const result = updateStmt.run('gamsahamnida', flashcardId);
      expect(result.changes).toBe(1);

      // Verify update
      const updated = db.prepare('SELECT * FROM flashcards WHERE id = ?').get(flashcardId);
      expect(updated.pronunciation).toBe('gamsahamnida');
    });

    it('should search flashcards by word', () => {
      // Insert test data
      const testData = [
        { id: '1', word: '안녕하세요', meaning: 'Hello' },
        { id: '2', word: '안녕', meaning: 'Hi/Bye' },
        { id: '3', word: '감사합니다', meaning: 'Thank you' },
      ];

      const insertStmt = db.prepare('INSERT INTO flashcards (id, word, meaning) VALUES (?, ?, ?)');
      testData.forEach(card => insertStmt.run(card.id, card.word, card.meaning));

      // Search
      const searchStmt = db.prepare('SELECT * FROM flashcards WHERE word LIKE ?');
      const results = searchStmt.all('%안녕%');

      expect(results).toHaveLength(2);
      expect(results.map(r => r.word)).toContain('안녕하세요');
      expect(results.map(r => r.word)).toContain('안녕');
    });

    it('should get flashcards by difficulty level', () => {
      // Insert test data with different difficulty levels
      const testData = [
        { id: '1', word: '안녕', meaning: 'Hi', difficulty_level: 1 },
        { id: '2', word: '감사합니다', meaning: 'Thank you', difficulty_level: 2 },
        { id: '3', word: '죄송합니다', meaning: 'I\'m sorry', difficulty_level: 3 },
        { id: '4', word: '실례합니다', meaning: 'Excuse me', difficulty_level: 3 },
      ];

      const insertStmt = db.prepare(
        'INSERT INTO flashcards (id, word, meaning, difficulty_level) VALUES (?, ?, ?, ?)'
      );
      testData.forEach(card => 
        insertStmt.run(card.id, card.word, card.meaning, card.difficulty_level)
      );

      // Get cards by difficulty
      const stmt = db.prepare('SELECT * FROM flashcards WHERE difficulty_level = ?');
      const level3Cards = stmt.all(3);

      expect(level3Cards).toHaveLength(2);
      expect(level3Cards.every(card => card.difficulty_level === 3)).toBe(true);
    });
  });

  describe('Processing History', () => {
    it('should record processing history', () => {
      const history = {
        file_path: '/path/to/vocabulary.csv',
        total_words: 100,
        processed_words: 95,
        failed_words: 5,
        status: 'completed',
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
      };

      const stmt = db.prepare(`
        INSERT INTO processing_history (
          file_path, total_words, processed_words, failed_words,
          status, started_at, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
      `);

      const result = stmt.run(
        history.file_path,
        history.total_words,
        history.processed_words,
        history.failed_words,
        history.status,
        history.started_at,
        history.completed_at
      );

      expect(result.lastInsertRowid).toBeGreaterThan(0);
    });

    it('should update processing status', () => {
      // Insert initial record
      const insertResult = db.prepare(`
        INSERT INTO processing_history (
          file_path, total_words, processed_words, failed_words,
          status, started_at
        ) VALUES (?, ?, ?, ?, ?, ?)
      `).run('/path/to/file.csv', 50, 0, 0, 'processing', new Date().toISOString());

      const historyId = insertResult.lastInsertRowid;

      // Update progress
      const updateStmt = db.prepare(`
        UPDATE processing_history
        SET processed_words = ?, failed_words = ?, status = ?
        WHERE id = ?
      `);

      updateStmt.run(25, 2, 'processing', historyId);

      // Verify update
      const updated = db.prepare('SELECT * FROM processing_history WHERE id = ?').get(historyId);
      expect(updated.processed_words).toBe(25);
      expect(updated.failed_words).toBe(2);
    });
  });

  describe('API Usage Tracking', () => {
    it('should track API usage', () => {
      const usage = {
        provider: 'openrouter',
        model: 'anthropic/claude-3-haiku',
        tokens_used: 1500,
        cost: 0.00375, // Example cost calculation
      };

      const stmt = db.prepare(`
        INSERT INTO api_usage (provider, model, tokens_used, cost)
        VALUES (?, ?, ?, ?)
      `);

      const result = stmt.run(
        usage.provider,
        usage.model,
        usage.tokens_used,
        usage.cost
      );

      expect(result.changes).toBe(1);
    });

    it('should calculate total API usage for a period', () => {
      // Insert test data
      const testData = [
        { provider: 'openrouter', model: 'claude-3-haiku', tokens: 1000, cost: 0.0025 },
        { provider: 'openrouter', model: 'claude-3-haiku', tokens: 2000, cost: 0.005 },
        { provider: 'anthropic', model: 'claude-3-opus', tokens: 500, cost: 0.015 },
      ];

      const stmt = db.prepare(
        'INSERT INTO api_usage (provider, model, tokens_used, cost) VALUES (?, ?, ?, ?)'
      );
      testData.forEach(usage => 
        stmt.run(usage.provider, usage.model, usage.tokens, usage.cost)
      );

      // Calculate totals
      const totals = db.prepare(`
        SELECT 
          provider,
          COUNT(*) as request_count,
          SUM(tokens_used) as total_tokens,
          SUM(cost) as total_cost
        FROM api_usage
        GROUP BY provider
      `).all();

      expect(totals).toHaveLength(2);
      
      const openrouterTotal = totals.find(t => t.provider === 'openrouter');
      expect(openrouterTotal.total_tokens).toBe(3000);
      expect(openrouterTotal.total_cost).toBeCloseTo(0.0075, 4);
    });
  });

  describe('Transactions', () => {
    it('should handle batch insertions in a transaction', () => {
      const flashcards = [
        { id: '1', word: '안녕', meaning: 'Hi' },
        { id: '2', word: '감사', meaning: 'Thanks' },
        { id: '3', word: '미안', meaning: 'Sorry' },
      ];

      const insertStmt = db.prepare('INSERT INTO flashcards (id, word, meaning) VALUES (?, ?, ?)');
      
      const insertMany = db.transaction((cards: typeof flashcards) => {
        for (const card of cards) {
          insertStmt.run(card.id, card.word, card.meaning);
        }
      });

      insertMany(flashcards);

      // Verify all inserted
      const count = db.prepare('SELECT COUNT(*) as count FROM flashcards').get();
      expect(count.count).toBe(3);
    });

    it('should rollback transaction on error', () => {
      const flashcards = [
        { id: '1', word: '안녕', meaning: 'Hi' },
        { id: '1', word: '감사', meaning: 'Thanks' }, // Duplicate ID will cause error
      ];

      const insertStmt = db.prepare('INSERT INTO flashcards (id, word, meaning) VALUES (?, ?, ?)');
      
      const insertMany = db.transaction((cards: typeof flashcards) => {
        for (const card of cards) {
          insertStmt.run(card.id, card.word, card.meaning);
        }
      });

      expect(() => insertMany(flashcards)).toThrow();

      // Verify nothing was inserted
      const count = db.prepare('SELECT COUNT(*) as count FROM flashcards').get();
      expect(count.count).toBe(0);
    });
  });
});