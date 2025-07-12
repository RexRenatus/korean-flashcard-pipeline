/** @type {import('jest').Config} */
module.exports = {
  // Use different test environments for main and renderer processes
  projects: [
    {
      // Main process tests
      displayName: 'main',
      testEnvironment: 'node',
      testMatch: [
        '<rootDir>/tests/unit/main/**/*.test.{ts,tsx}',
        '<rootDir>/src/main/**/*.test.{ts,tsx}'
      ],
      transform: {
        '^.+\\.tsx?$': ['ts-jest', {
          tsconfig: {
            jsx: 'react-jsx',
            module: 'commonjs'
          }
        }]
      },
      moduleNameMapper: {
        '^@/(.*)$': '<rootDir>/src/$1',
        '^@main/(.*)$': '<rootDir>/src/main/$1',
        '^@shared/(.*)$': '<rootDir>/src/shared/$1',
        '^@preload/(.*)$': '<rootDir>/src/preload/$1'
      }
    },
    {
      // Renderer process tests
      displayName: 'renderer',
      testEnvironment: 'jsdom',
      testMatch: [
        '<rootDir>/tests/unit/renderer/**/*.test.{ts,tsx}',
        '<rootDir>/src/renderer/**/*.test.{ts,tsx}'
      ],
      transform: {
        '^.+\\.tsx?$': ['ts-jest', {
          tsconfig: {
            jsx: 'react-jsx',
            module: 'commonjs'
          }
        }]
      },
      moduleNameMapper: {
        '^@/(.*)$': '<rootDir>/src/$1',
        '^@renderer/(.*)$': '<rootDir>/src/renderer/$1',
        '^@shared/(.*)$': '<rootDir>/src/shared/$1',
        '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
        '\\.(jpg|jpeg|png|gif|svg|webp)$': '<rootDir>/tests/mocks/fileMock.js'
      },
      setupFilesAfterEnv: ['<rootDir>/tests/setupTests.ts']
    },
    {
      // Integration tests
      displayName: 'integration',
      testEnvironment: 'node',
      testMatch: [
        '<rootDir>/tests/integration/**/*.test.{ts,tsx}'
      ],
      transform: {
        '^.+\\.tsx?$': ['ts-jest', {
          tsconfig: {
            jsx: 'react-jsx',
            module: 'commonjs'
          }
        }]
      },
      moduleNameMapper: {
        '^@/(.*)$': '<rootDir>/src/$1',
        '^@main/(.*)$': '<rootDir>/src/main/$1',
        '^@renderer/(.*)$': '<rootDir>/src/renderer/$1',
        '^@shared/(.*)$': '<rootDir>/src/shared/$1',
        '^@preload/(.*)$': '<rootDir>/src/preload/$1'
      }
    }
  ],

  // Common configuration
  preset: 'ts-jest',
  testEnvironment: 'node',
  rootDir: '.',
  
  // Coverage configuration
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.stories.{ts,tsx}',
    '!src/**/index.{ts,tsx}',
    '!src/renderer/main.tsx',
    '!src/main/index.ts',
    '!src/preload/index.ts'
  ],
  coverageDirectory: '<rootDir>/coverage',
  coverageReporters: ['text', 'lcov', 'html'],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  },

  // Module resolution
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],
  
  // Test utilities
  clearMocks: true,
  restoreMocks: true,
  
  // Ignore patterns
  testPathIgnorePatterns: [
    '/node_modules/',
    '/dist/',
    '/release/',
    '/coverage/',
    '/.vscode/',
    '/.git/'
  ],
  
  // Transform ignore patterns
  transformIgnorePatterns: [
    'node_modules/(?!(electron-store|conf|atomically|dot-prop|env-paths)/)'
  ],

  // Globals
  globals: {
    'ts-jest': {
      isolatedModules: true
    }
  },

  // Verbose output
  verbose: true,
  
  // Test timeout
  testTimeout: 10000,

  // Watch plugins
  watchPlugins: [
    'jest-watch-typeahead/filename',
    'jest-watch-typeahead/testname'
  ]
};