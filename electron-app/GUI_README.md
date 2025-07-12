# Korean Flashcard Pipeline - Desktop Application

A powerful Electron-based desktop application for generating Korean language flashcards using AI, featuring a modern React UI with Material Design.

## Features

### Core Functionality
- **Vocabulary Management**: Add, edit, and organize Korean vocabulary
- **AI-Powered Processing**: Generate flashcards using Claude via OpenRouter API
- **Real-time Progress**: WebSocket-based live updates during processing
- **Batch Processing**: Process multiple vocabulary items efficiently
- **Export Options**: Multiple export formats (JSON, CSV, Anki, Markdown)

### Advanced Features
- **Dark Mode**: Full theme support with multiple color options
- **Keyboard Shortcuts**: Comprehensive keyboard navigation
- **Auto-Updates**: Seamless application updates
- **Backup/Restore**: Protect your data with automatic backups
- **Error Recovery**: Robust error handling with user-friendly recovery
- **Telemetry**: Optional usage analytics for improving the app

## Technology Stack

- **Frontend**: React 18, TypeScript, Material-UI
- **Desktop**: Electron 28
- **State Management**: Redux Toolkit, React Query
- **Backend Integration**: Python pipeline via IPC
- **Real-time Updates**: WebSocket
- **Build Tools**: Vite, electron-builder

## Installation

### Prerequisites
- Node.js 18+ and npm 8+
- Python 3.8+ (for the processing pipeline)
- Git

### Development Setup

1. Clone the repository:
```bash
git clone https://github.com/yourorg/korean-flashcard-desktop.git
cd korean-flashcard-desktop/electron-app
```

2. Install dependencies:
```bash
npm install
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your OpenRouter API key
```

4. Run in development mode:
```bash
npm run dev
```

## Building

### Build for all platforms:
```bash
npm run build
```

### Platform-specific builds:
```bash
# Windows
npm run build:win

# macOS
npm run build:mac

# Linux
npm run build:linux
```

## Usage

### Adding Vocabulary
1. Navigate to the Vocabulary page (Ctrl+V)
2. Click "Add Vocabulary" or press Ctrl+N
3. Enter Korean word and optional context
4. Save to add to your vocabulary list

### Processing Flashcards
1. Select vocabulary items to process
2. Click "Start Processing" or press Ctrl+Shift+R
3. Monitor real-time progress
4. View generated flashcards when complete

### Exporting Flashcards
1. Go to Flashcards page (Ctrl+F)
2. Use filters to select cards
3. Click Export or press Ctrl+E
4. Choose format and customize export

### Keyboard Shortcuts
- **Ctrl+D**: Dashboard
- **Ctrl+V**: Vocabulary
- **Ctrl+P**: Processing
- **Ctrl+F**: Flashcards
- **Ctrl+,**: Settings
- **Shift+?**: Show all shortcuts

## Configuration

### Settings Location
- **Windows**: `%APPDATA%/korean-flashcard-desktop`
- **macOS**: `~/Library/Application Support/korean-flashcard-desktop`
- **Linux**: `~/.config/korean-flashcard-desktop`

### Available Settings
- API configuration (endpoint, model, timeout)
- Processing options (batch size, rate limits)
- Cache settings (TTL, size limits)
- Theme preferences (dark/light mode, colors)
- Telemetry opt-out

## Architecture

### Main Process
- Manages application lifecycle
- Handles Python pipeline integration
- Provides IPC communication
- Manages WebSocket server
- Handles auto-updates and backups

### Renderer Process
- React application with Material-UI
- Redux for state management
- React Query for data fetching
- WebSocket client for real-time updates

### Services
- **PythonService**: Manages Python pipeline process
- **WebSocketService**: Real-time communication
- **ProcessingService**: Task queue management
- **TelemetryService**: Usage analytics
- **BackupService**: Automated backups
- **AutoUpdaterService**: Application updates

## Development

### Project Structure
```
electron-app/
├── src/
│   ├── main/           # Electron main process
│   ├── renderer/       # React application
│   ├── preload/        # Preload scripts
│   └── shared/         # Shared types/constants
├── assets/             # Icons and resources
├── docs/               # Documentation
└── tests/              # Test suites
```

### Testing
```bash
# Unit tests
npm test

# Integration tests
npm run test:integration

# E2E tests
npm run test:e2e
```

### Code Quality
```bash
# Linting
npm run lint

# Type checking
npm run typecheck

# Format code
npm run format
```

## Troubleshooting

### Common Issues

1. **Python service fails to start**
   - Ensure Python 3.8+ is installed
   - Check Python path in settings
   - Verify pipeline dependencies installed

2. **WebSocket connection issues**
   - Check if port 8081 is available
   - Restart the application
   - Check firewall settings

3. **Export not working**
   - Ensure output directory has write permissions
   - Check available disk space
   - Verify export template configuration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

- **Documentation**: [https://docs.koreanflashcards.app](https://docs.koreanflashcards.app)
- **Issues**: [GitHub Issues](https://github.com/yourorg/korean-flashcard-desktop/issues)
- **Discord**: [Community Server](https://discord.gg/koreanflashcards)

## Acknowledgments

- Built with Electron and React
- Uses Claude AI via OpenRouter
- Material-UI for the design system
- Community contributors