# Korean Flashcard Desktop Application

A modern, offline-first Electron desktop application for the Korean Language Flashcard Pipeline system. Built with React, TypeScript, and Test-Driven Development (TDD).

## Features

- 🖥️ **Native Desktop Experience**: Cross-platform support (Windows, macOS, Linux)
- 🔌 **Offline-First**: Full functionality without internet connection
- 🐍 **Python Integration**: Seamless integration with existing Python backend
- ⚡ **High Performance**: Virtual scrolling, lazy loading, and optimized rendering
- 🧪 **Test-Driven**: 90%+ test coverage with comprehensive test suite
- 🔒 **Secure**: Context isolation, sandboxing, and secure IPC communication

## Architecture

```
electron-app/
├── src/
│   ├── main/          # Electron main process
│   ├── renderer/      # React application
│   ├── preload/       # Secure bridge between main and renderer
│   └── shared/        # Shared types and constants
├── tests/
│   ├── unit/          # Unit tests (Jest + React Testing Library)
│   ├── integration/   # Integration tests
│   └── e2e/           # End-to-end tests (Playwright)
```

## Prerequisites

- Node.js 18+ and npm 8+
- Python 3.9+ with the flashcard_pipeline package installed
- SQLite database from the main project

## Installation

```bash
# Install dependencies
npm install

# Install Python dependencies (if not already installed)
cd .. && pip install -r requirements.txt
```

## Development

### Running Tests First (TDD)

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage

# Run E2E tests
npm run test:e2e

# Run E2E tests with UI
npm run test:e2e:ui
```

### Development Server

```bash
# Start the development server
npm run dev

# This will:
# 1. Start Vite dev server on port 5173
# 2. Launch Electron in development mode
# 3. Open DevTools automatically
```

### Linting and Formatting

```bash
# Run ESLint
npm run lint

# Fix ESLint issues
npm run lint:fix

# Format code with Prettier
npm run format

# Type checking
npm run typecheck
```

## Building for Production

```bash
# Build for current platform
npm run build

# Build for specific platforms
npm run build:win    # Windows
npm run build:mac    # macOS
npm run build:linux  # Linux

# Output will be in the 'release' directory
```

## Testing Strategy

### Unit Tests (70%)
- Component logic testing
- Service layer testing
- State management testing
- Utility function testing

### Integration Tests (20%)
- IPC communication testing
- Python bridge integration
- Database operations
- Component integration

### E2E Tests (10%)
- Critical user flows
- Cross-platform behavior
- Performance scenarios
- Error recovery

## Key Components

### 1. IPCBridge
Handles communication with Python backend:
```typescript
const bridge = new IPCBridge();
await bridge.initialize();
const result = await bridge.execute('process_vocabulary', { items });
```

### 2. PythonService
High-level API for Python operations:
```typescript
const service = new PythonService();
const stats = await service.getSystemStats();
const vocab = await service.getVocabularyList({ page: 1 });
```

### 3. Dashboard
Real-time system overview:
- Processing statistics
- System health indicators
- Recent activity feed
- Performance metrics

### 4. VocabularyManager
Comprehensive vocabulary management:
- Virtual scrolling for large datasets
- Inline editing
- Bulk operations
- Import/Export functionality

### 5. ProcessingMonitor
Real-time processing visualization:
- Queue management
- Progress tracking
- Error handling
- Retry mechanisms

## Security

- **Context Isolation**: Renderer process cannot access Node.js APIs directly
- **Preload Scripts**: Secure bridge with whitelisted IPC channels
- **Input Validation**: All user inputs are sanitized
- **Secure Storage**: API keys encrypted using Electron safeStorage

## Performance Optimization

- **Virtual Scrolling**: React Window for large lists
- **Lazy Loading**: Components loaded on demand
- **Worker Threads**: Heavy operations run in background
- **Debouncing**: Search and filter operations optimized
- **Caching**: IndexedDB for offline data storage

## Troubleshooting

### Python Service Not Initializing
1. Check Python is in PATH: `python --version`
2. Verify flashcard_pipeline is installed: `pip list | grep flashcard`
3. Check logs in DevTools console

### Build Failures
1. Clear node_modules: `rm -rf node_modules && npm install`
2. Clear Electron cache: `npm run postinstall`
3. Check native dependencies are rebuilt

### Performance Issues
1. Check DevTools Performance tab
2. Monitor memory usage
3. Review virtual scrolling implementation
4. Check for unnecessary re-renders

## Contributing

1. Write tests first (TDD)
2. Ensure all tests pass
3. Maintain 90%+ coverage
4. Follow ESLint and Prettier rules
5. Update documentation

## License

MIT License - See LICENSE file in project root