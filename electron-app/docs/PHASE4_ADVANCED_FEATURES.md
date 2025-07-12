# Phase 4: Advanced Features

## Overview
Phase 4 implements advanced features including theme management, keyboard shortcuts, and export functionality to enhance the user experience of the Flashcard Pipeline Electron application.

## Key Components Implemented

### 1. Theme System (`ThemeContext.tsx`)
- **Dark/Light mode toggle** with system preference detection
- **Color customization** with 4 primary color options (blue, green, orange, red)
- **Persistent preferences** using localStorage
- **Material-UI theme integration** with custom component overrides
- **Responsive design** adjustments for dark mode

### 2. Keyboard Shortcuts (`useKeyboardShortcuts.ts`)
- **Global navigation shortcuts** (Ctrl+D for Dashboard, Ctrl+V for Vocabulary, etc.)
- **Action shortcuts** (Ctrl+N for new vocabulary, Ctrl+E for export)
- **Context-aware shortcuts** that don't interfere with input fields
- **Help dialog** accessible via Shift+?
- **Custom shortcut support** for components

### 3. Keyboard Shortcuts Dialog (`KeyboardShortcutsDialog.tsx`)
- **Categorized shortcuts** (Navigation, Actions, Other)
- **Visual keyboard representations** using Chip components
- **Event-driven display** triggered by Shift+? or button click
- **Platform-aware key labeling** (Ctrl/⌘)

### 4. Export Templates (`ExportTemplates.tsx`)
- **Pre-defined templates** for JSON, CSV, Anki, and Markdown formats
- **Custom template creation** with field selection
- **Template management** (edit, duplicate, delete)
- **Persistent storage** using localStorage
- **Field mapping** configuration

### 5. Bulk Export Dialog (`BulkExportDialog.tsx`)
- **Multi-format export** support
- **Progress tracking** with real-time updates
- **Directory selection** for output files
- **Export options** (metadata inclusion, file splitting)
- **Error handling** with detailed error reporting
- **File name patterns** with date placeholders

### 6. Enhanced Settings Page
- **Appearance tab** for theme and color preferences
- **Keyboard shortcuts viewer** integrated
- **Theme mode toggle** with visual feedback
- **Primary color selector** with preview

## Architecture Changes

### Theme Integration
```
App.tsx
├── ThemeProvider (custom)
│   ├── Theme mode management
│   ├── Color customization
│   └── MUI theme creation
└── Components
    └── Access theme via useTheme hook
```

### Export System
```
FlashcardViewer
├── Export Templates Tab
│   ├── Template list
│   ├── Template editor
│   └── Default templates
└── Bulk Export Dialog
    ├── Format selection
    ├── Template selection
    ├── Progress tracking
    └── File generation
```

## Usage Examples

### Using Keyboard Shortcuts
```typescript
// In a component
import { useKeyboardShortcuts } from '@renderer/hooks/useKeyboardShortcuts';

const MyComponent = () => {
  useKeyboardShortcuts([
    {
      key: 's',
      ctrl: true,
      description: 'Save changes',
      action: () => handleSave(),
    },
  ]);
};
```

### Using Theme System
```typescript
// Access theme context
import { useTheme } from '@renderer/contexts/ThemeContext';

const MyComponent = () => {
  const { mode, toggleTheme, primaryColor, setPrimaryColor } = useTheme();
  
  return (
    <Button onClick={toggleTheme}>
      Switch to {mode === 'light' ? 'dark' : 'light'} mode
    </Button>
  );
};
```

### Exporting Flashcards
1. Navigate to Flashcards page
2. Click "Export" button or press Ctrl+E
3. Select export format and template
4. Choose output directory
5. Configure export options
6. Click "Start Export" to begin

## Configuration

### Theme Preferences
- Stored in localStorage: `themeMode`, `themePrimaryColor`
- System preference detection on first load
- Automatic persistence of changes

### Export Templates
- Stored in localStorage: `exportTemplates`
- Default templates cannot be deleted
- Custom templates support all export formats

## Testing the Features

### Theme Testing
1. Toggle between light and dark modes
2. Change primary color and verify component updates
3. Refresh page to test persistence
4. Clear localStorage to test system preference detection

### Keyboard Shortcuts Testing
1. Press Shift+? to view all shortcuts
2. Test navigation shortcuts (Ctrl+D, Ctrl+V, etc.)
3. Test action shortcuts in relevant contexts
4. Verify shortcuts disabled in input fields

### Export Testing
1. Create a custom export template
2. Export flashcards using different formats
3. Test bulk export with progress tracking
4. Verify exported file contents

## Performance Considerations

- Theme changes are optimized with useMemo
- Keyboard event listeners use passive mode
- Export operations show progress for large datasets
- Templates cached in memory after first load

## Accessibility

- Keyboard shortcuts follow standard conventions
- Theme provides sufficient contrast ratios
- Export dialog fully keyboard navigable
- Screen reader friendly labeling

## Next Steps (Phase 5: Production Ready)
1. Add comprehensive error boundaries
2. Implement automatic updates
3. Add telemetry and analytics
4. Create installer packages
5. Add comprehensive documentation
6. Implement backup and restore functionality