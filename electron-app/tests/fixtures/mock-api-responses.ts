/**
 * Mock API responses for testing
 */

export const mockFlashcardResponse = {
  id: 'mock-id-123',
  word: '안녕하세요',
  meaning: 'Hello (formal greeting)',
  pronunciation: 'annyeonghaseyo',
  part_of_speech: 'interjection',
  difficulty_level: 2,
  examples: [
    {
      korean: '안녕하세요, 만나서 반갑습니다.',
      english: 'Hello, nice to meet you.',
      romanization: 'Annyeonghaseyo, mannaseo bangapseumnida.'
    },
    {
      korean: '선생님, 안녕하세요?',
      english: 'Hello, teacher.',
      romanization: 'Seonsaengnim, annyeonghaseyo?'
    }
  ],
  usage_notes: 'Used as a formal greeting any time of day. More polite than 안녕.',
  cultural_notes: 'Often accompanied by a slight bow. The depth of bow indicates level of respect.',
  mnemonics: 'Think of "on your hay so" - imagine meeting someone on a hay field.',
  related_words: ['안녕', '안녕히 가세요', '안녕히 계세요'],
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString()
};

export const mockNuanceResponse = {
  stage: 'nuance_creation',
  nuance_text: `The Korean greeting "안녕하세요" (annyeonghaseyo) carries much more cultural weight than a simple "hello" in English. 

It literally means "Are you at peace?" and reflects the Korean cultural emphasis on harmony and well-being. The formal ending -요 makes it appropriate for most situations, from casual encounters to business meetings.

When saying 안녕하세요, Koreans often accompany it with a slight bow, with the depth indicating the level of respect. Among peers, a small nod suffices, while a deeper bow is used for elders or superiors.

The greeting can be used at any time of day, unlike English which has specific greetings for morning, afternoon, and evening. This versatility makes it an essential phrase for Korean learners.`,
  
  formality_level: 'polite',
  context_appropriate: true,
  timestamp: new Date().toISOString()
};

export const mockProcessingProgress = {
  status: 'processing',
  current: 5,
  total: 10,
  percentage: 50,
  currentWord: '안녕하세요',
  estimatedTimeRemaining: 120, // seconds
};

export const mockErrorResponse = {
  error: 'API_ERROR',
  message: 'Rate limit exceeded. Please try again later.',
  details: {
    provider: 'openrouter',
    model: 'anthropic/claude-3-haiku',
    rateLimitReset: new Date(Date.now() + 60000).toISOString(),
  }
};

export const mockExportData = {
  version: '1.0.0',
  exportDate: new Date().toISOString(),
  flashcards: [
    mockFlashcardResponse,
    {
      ...mockFlashcardResponse,
      id: 'mock-id-124',
      word: '감사합니다',
      meaning: 'Thank you',
      pronunciation: 'gamsahamnida',
    }
  ],
  metadata: {
    totalCards: 2,
    difficultyDistribution: {
      1: 0,
      2: 2,
      3: 0,
      4: 0,
      5: 0
    },
    partsOfSpeech: {
      interjection: 2
    }
  }
};

export const mockSettings = {
  theme: 'light',
  apiKey: 'test-api-key-123',
  apiProvider: 'openrouter',
  model: 'anthropic/claude-3-haiku',
  language: 'en',
  autoSave: true,
  maxConcurrentRequests: 3,
  retryAttempts: 3,
  retryDelay: 1000,
};

export const mockStats = {
  totalFlashcards: 150,
  todayReviewed: 25,
  todayAdded: 10,
  averageSuccessRate: 0.75,
  streakDays: 7,
  nextReviewCount: 15,
  difficultyDistribution: {
    1: 30,
    2: 45,
    3: 50,
    4: 20,
    5: 5
  },
  weeklyProgress: [
    { date: '2024-01-15', reviewed: 20, added: 5 },
    { date: '2024-01-16', reviewed: 25, added: 8 },
    { date: '2024-01-17', reviewed: 15, added: 3 },
    { date: '2024-01-18', reviewed: 30, added: 10 },
    { date: '2024-01-19', reviewed: 22, added: 6 },
    { date: '2024-01-20', reviewed: 28, added: 7 },
    { date: '2024-01-21', reviewed: 25, added: 10 },
  ]
};