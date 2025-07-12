# Korean Flashcard Pipeline - Desktop Application

A modern desktop application for AI-powered Korean language flashcard generation, built with Electron, React, and TypeScript.

## Features

- **Vocabulary Management**: Import, view, edit, and organize Korean vocabulary
- **Batch Processing**: Process multiple words simultaneously with progress tracking
- **Flashcard Viewer**: Interactive flashcard review with filtering and export options
- **Real-time Monitoring**: Track processing status and system performance
- **Configuration Management**: Customize API settings, processing parameters, and more
- **Cross-platform**: Works on Windows, macOS, and Linux

## Tech Stack

- **Frontend**: React 18 with TypeScript
- **UI Framework**: Material-UI (MUI) v5
- **State Management**: Redux Toolkit
- **Desktop Framework**: Electron 28
- **Build Tool**: Vite
- **Data Fetching**: React Query (TanStack Query)
- **IPC Communication**: Secure context bridge pattern

## Prerequisites

- Node.js 18 or higher
- npm 8 or higher
- Python 3.8+ (for backend integration)
- The flashcard pipeline backend must be installed and configured

## Installation

1. Navigate to the electron-app directory:
```bash
cd electron-app
```

2. Install dependencies:
```bash
npm install
```

3. Configure the backend connection:
   - Copy `.env.example` to `.env`
   - Set your OpenRouter API key and other configuration

## Development

1. Start the development server:
```bash
npm run dev
```

This will:
- Start the Vite development server on port 5173
- Launch Electron in development mode
- Enable hot module replacement for React

2. Run tests:
```bash
npm test              # Run unit tests
npm run test:e2e      # Run E2E tests
npm run test:coverage # Generate coverage report
```

3. Lint and format code:
```bash
npm run lint          # Check for linting errors
npm run lint:fix      # Fix linting errors
npm run format        # Format code with Prettier
npm run typecheck     # Run TypeScript type checking
```

## Building

1. Build for your current platform:
```bash
npm run build
```

2. Build for all platforms:
```bash
npm run build:all
```

The built applications will be in the `release` directory.

## Project Structure

```
electron-app/
├── src/
│   ├── main/              # Electron main process
│   │   ├── index.ts       # Main entry point
│   │   ├── ipc/           # IPC handlers
│   │   └── services/      # Backend services
│   ├── renderer/          # React application
│   │   ├── App.tsx        # Root component
│   │   ├── components/    # Reusable components
│   │   ├── pages/         # Page components
│   │   ├── store/         # Redux store
│   │   ├── hooks/         # Custom React hooks
│   │   ├── services/      # API services
│   │   └── utils/         # Utility functions
│   ├── preload/           # Preload scripts
│   │   └── index.ts       # Context bridge API
│   └── shared/            # Shared types and constants
├── assets/                # Application icons
├── dist/                  # Build output
├── release/               # Packaged applications
└── test/                  # Test files
```

## Key Components

### Main Process (`src/main/`)
- **index.ts**: Application entry point, window management
- **ipc/handlers.ts**: IPC communication handlers
- **services/python-bridge.ts**: Python backend integration

### Renderer Process (`src/renderer/`)
- **pages/Dashboard.tsx**: Main dashboard with statistics
- **pages/VocabularyManager.tsx**: Vocabulary CRUD operations
- **pages/ProcessingMonitor.tsx**: Real-time processing status
- **pages/FlashcardViewer.tsx**: Interactive flashcard review
- **pages/Settings.tsx**: Application configuration

### Components
- **MainLayout**: Application shell with navigation
- **VocabularyEditDialog**: Add/edit vocabulary items
- **VocabularyUploadDialog**: Bulk import functionality
- **NotificationProvider**: System-wide notifications

### State Management
- **configSlice**: Application configuration
- **vocabularySlice**: Vocabulary data management
- **flashcardSlice**: Flashcard data and operations
- **systemSlice**: System status and statistics

## IPC Communication

The application uses a secure IPC pattern with context isolation:

1. **Main Process**: Handles file system, Python integration, and system operations
2. **Preload Script**: Exposes a limited API to the renderer process
3. **Renderer Process**: Calls IPC methods through the window.electronAPI object

Example:
```typescript
// Renderer process
const vocabulary = await window.electronAPI.getVocabulary({ limit: 100 });

// Preload script
contextBridge.exposeInMainWorld('electronAPI', {
  getVocabulary: (options) => ipcRenderer.invoke('db:get-vocabulary', options)
});

// Main process
ipcMain.handle('db:get-vocabulary', async (event, options) => {
  return await databaseService.getVocabulary(options);
});
```

## Configuration

The application stores configuration in:
- **Development**: `~/.config/korean-flashcard-desktop/config.json`
- **Production**: Platform-specific app data directory

Configuration includes:
- API settings (base URL, model, timeout)
- Processing parameters (batch size, parallelism)
- Cache settings (TTL, max size)
- Database location
- UI preferences

## Troubleshooting

### Electron won't start
- Ensure Node.js 18+ is installed
- Delete `node_modules` and run `npm install` again
- Check for port conflicts on 5173

### Python backend connection issues
- Verify Python is installed and in PATH
- Check the flashcard pipeline is installed: `pip show flashcard-pipeline`
- Review logs in the developer console (Ctrl+Shift+I)

### Build failures
- Clear the `dist` and `release` directories
- Ensure you have proper permissions for code signing (macOS)
- Check available disk space

## License

MIT License - see the main project LICENSE file for details.