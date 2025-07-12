# GUI Architecture for Korean Flashcard Pipeline

**Last Updated**: 2025-01-08

## Overview

This document outlines the architecture for a modern, production-ready GUI application for the Korean Flashcard Pipeline system. The GUI will provide an intuitive interface for managing vocabulary, monitoring processing, and accessing generated flashcards.

## Technology Stack

### Frontend Framework: Electron + React + TypeScript
- **Electron**: Cross-platform desktop application framework
- **React**: Modern UI library with component-based architecture
- **TypeScript**: Type safety and better developer experience
- **Material-UI (MUI)**: Professional UI component library
- **Redux Toolkit**: State management for complex application state
- **React Query**: Server state management and caching

### Backend Integration
- **IPC (Inter-Process Communication)**: Electron main/renderer process communication
- **Python Bridge**: Direct integration with existing Python pipeline
- **WebSocket**: Real-time updates for processing status
- **REST API**: Alternative deployment option for web-based access

## Architecture Layers

### 1. Presentation Layer
```
├── components/
│   ├── common/           # Shared UI components
│   ├── vocabulary/       # Vocabulary management components
│   ├── processing/       # Pipeline processing UI
│   ├── flashcards/       # Flashcard viewing/export
│   └── settings/         # Application settings
```

### 2. State Management
```typescript
interface AppState {
  vocabulary: VocabularyState;
  processing: ProcessingState;
  flashcards: FlashcardState;
  settings: SettingsState;
  notifications: NotificationState;
}
```

### 3. Service Layer
```
├── services/
│   ├── VocabularyService    # CRUD operations for vocabulary
│   ├── ProcessingService    # Pipeline control and monitoring
│   ├── FlashcardService     # Flashcard management
│   ├── ImportExportService  # File handling
│   └── SettingsService      # Configuration management
```

### 4. IPC Communication
```typescript
// Main Process Handlers
ipcMain.handle('vocabulary:upload', handleBulkUpload);
ipcMain.handle('processing:start', startProcessing);
ipcMain.handle('processing:status', getProcessingStatus);
ipcMain.handle('flashcards:export', exportFlashcards);
```

## Core Features

### 1. Dashboard
- **Overview Stats**: Total words, processed, pending, failed
- **Processing Status**: Real-time progress bars and ETAs
- **Recent Activity**: Latest processed items
- **System Health**: API status, rate limits, circuit breaker status

### 2. Vocabulary Management
- **Bulk Import**: Drag-and-drop CSV/TXT files
- **Table View**: Sortable, filterable, paginated data grid
- **Inline Editing**: Direct cell editing with validation
- **Batch Operations**: Select multiple items for actions
- **Status Filtering**: View by pending/processing/completed/failed

### 3. Ingress Toll System
- **Upload Queue**: Visual queue of pending uploads
- **Validation Preview**: Show validation results before commit
- **Duplicate Detection**: Highlight existing vocabulary
- **Batch Configuration**: Set processing parameters per batch
- **Progress Tracking**: Individual and overall progress

### 4. Processing Monitor
- **Real-time Updates**: WebSocket-based live updates
- **Pipeline Visualization**: Stage 1/2 progress indicators
- **Error Details**: Expandable error information
- **Retry Controls**: Manual retry for failed items
- **Performance Metrics**: Processing speed, API latency

### 5. Flashcard Viewer
- **Card Preview**: Interactive flashcard preview
- **Export Options**: Anki, CSV, PDF formats
- **Filtering**: By difficulty, date, category
- **Bulk Export**: Selected or all flashcards
- **Quality Review**: Flag cards for review

### 6. Settings & Configuration
- **API Configuration**: OpenRouter API key management
- **Processing Settings**: Rate limits, concurrency
- **UI Preferences**: Theme, language, layout
- **Export Templates**: Customizable export formats
- **Backup/Restore**: Configuration import/export

## Component Architecture

### Main Window Structure
```typescript
<App>
  <NavigationBar />
  <MainContent>
    <Router>
      <Route path="/dashboard" component={Dashboard} />
      <Route path="/vocabulary" component={VocabularyManager} />
      <Route path="/processing" component={ProcessingMonitor} />
      <Route path="/flashcards" component={FlashcardViewer} />
      <Route path="/settings" component={Settings} />
    </Router>
  </MainContent>
  <StatusBar />
  <NotificationSystem />
</App>
```

### Key Components

#### VocabularyUploader Component
```typescript
interface VocabularyUploaderProps {
  onUpload: (files: File[]) => Promise<void>;
  onValidation: (results: ValidationResult[]) => void;
}

// Features:
// - Drag & drop zone
// - File type validation
// - Progress indication
// - Error handling
// - Batch preview
```

#### ProcessingQueue Component
```typescript
interface ProcessingQueueProps {
  items: QueueItem[];
  onStart: () => void;
  onPause: () => void;
  onCancel: (itemId: string) => void;
}

// Features:
// - Queue visualization
// - Priority management
// - Status indicators
// - Action controls
```

## Data Flow

### Upload Flow
1. User drags files to upload zone
2. Frontend validates file format
3. Parse and preview data
4. User confirms upload
5. IPC call to main process
6. Python bridge inserts to database
7. Update UI with new items

### Processing Flow
1. User initiates processing
2. Main process starts Python pipeline
3. WebSocket connection established
4. Real-time updates sent to renderer
5. UI updates progress indicators
6. Completion notification shown

## Security Considerations

### API Key Management
- Secure storage using Electron safeStorage
- Never exposed to renderer process
- Encrypted in application data

### Input Validation
- File type restrictions
- Size limitations
- Content sanitization
- SQL injection prevention

### Process Isolation
- Renderer process sandboxing
- Context isolation enabled
- Preload scripts for safe IPC

## Performance Optimization

### Virtual Scrolling
- Large dataset handling
- React Window for virtualization
- Lazy loading strategies

### Caching Strategy
- React Query for server state
- IndexedDB for offline support
- Memory management

### Background Processing
- Worker threads for heavy operations
- Debounced search/filter
- Optimistic UI updates

## Styling and Theming

### Design System
```scss
// Color Palette
$primary: #1976d2;
$secondary: #dc004e;
$success: #4caf50;
$warning: #ff9800;
$error: #f44336;

// Typography
$font-family: 'Roboto', 'Noto Sans KR', sans-serif;

// Spacing
$spacing-unit: 8px;
```

### Theme Support
- Light/Dark mode toggle
- Customizable accent colors
- Responsive design
- Accessibility compliance

## Error Handling

### User-Friendly Errors
```typescript
class UserError extends Error {
  code: string;
  userMessage: string;
  technicalDetails?: any;
  recoveryAction?: () => void;
}
```

### Error Boundaries
- Component-level error catching
- Fallback UI components
- Error reporting service

## Testing Strategy

### Unit Tests
- Component testing with React Testing Library
- Service layer testing with Jest
- IPC handler mocking

### Integration Tests
- Electron Testing Framework
- End-to-end user flows
- Cross-platform testing

### Performance Tests
- Lighthouse metrics
- Memory profiling
- Large dataset handling

## Deployment Considerations

### Auto-Updates
- Electron-updater integration
- Staged rollouts
- Rollback capability

### Analytics
- Usage tracking (with consent)
- Error reporting
- Performance monitoring

### Platform-Specific
- Windows: MSI installer
- macOS: DMG with code signing
- Linux: AppImage/Snap packages

## Implementation Phases

### Phase 1: Core UI (2 weeks)
- Basic Electron setup
- Navigation and routing
- Dashboard implementation
- Basic vocabulary view

### Phase 2: Ingress Toll (1 week)
- File upload system
- Validation preview
- Bulk import functionality
- Queue management

### Phase 3: Processing Integration (2 weeks)
- Python bridge setup
- WebSocket implementation
- Real-time monitoring
- Error handling

### Phase 4: Advanced Features (1 week)
- Flashcard viewer
- Export functionality
- Settings management
- Theme support

### Phase 5: Production Ready (1 week)
- Auto-updater
- Analytics integration
- Performance optimization
- Security hardening

## Next Steps

1. Set up Electron + React boilerplate
2. Implement Python bridge for IPC
3. Create component library
4. Build ingress toll system
5. Integrate with existing pipeline