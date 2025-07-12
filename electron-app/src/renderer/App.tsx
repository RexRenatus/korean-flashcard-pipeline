import React from 'react';
import { HashRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { CssBaseline } from '@mui/material';
import { Provider } from 'react-redux';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { store } from './store';
import { MainLayout } from './components/layout/MainLayout';
import { Dashboard } from './pages/Dashboard';
import { VocabularyManager } from './pages/VocabularyManager';
import { ProcessingMonitor } from './pages/ProcessingMonitor';
import { FlashcardViewer } from './pages/FlashcardViewer';
import { Settings } from './pages/Settings';
import { NotificationProvider } from './providers/NotificationProvider';
import { ThemeProvider } from './contexts/ThemeContext';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';
import { ErrorBoundary } from './components/error/ErrorBoundary';
import { UpdateNotification } from './components/updater/UpdateNotification';
import { errorHandler } from './utils/errorHandler';

// Create a query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

export const App: React.FC = () => {
  // Initialize global keyboard shortcuts
  useKeyboardShortcuts();

  // Set up menu navigation listener
  React.useEffect(() => {
    const handleNavigate = (event: any, path: string) => {
      window.location.hash = `#${path}`;
    };

    const handleShowShortcuts = () => {
      window.dispatchEvent(new CustomEvent('shortcut:show-help'));
    };

    window.electron?.on('navigate', handleNavigate);
    window.electron?.on('menu:show-shortcuts', handleShowShortcuts);

    return () => {
      window.electron?.removeListener('navigate', handleNavigate);
      window.electron?.removeListener('menu:show-shortcuts', handleShowShortcuts);
    };
  }, []);

  return (
    <ErrorBoundary
      onError={(error, errorInfo) => {
        // Send error to telemetry
        errorHandler.handleError(error, {
          componentStack: errorInfo.componentStack,
        });
      }}
    >
      <Provider store={store}>
        <QueryClientProvider client={queryClient}>
          <ThemeProvider>
            <CssBaseline />
            <NotificationProvider>
              <Router>
                <MainLayout>
                  <Routes>
                    <Route path="/" element={<Navigate to="/dashboard" replace />} />
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="/vocabulary" element={<VocabularyManager />} />
                    <Route path="/processing" element={<ProcessingMonitor />} />
                    <Route path="/flashcards" element={<FlashcardViewer />} />
                    <Route path="/settings" element={<Settings />} />
                  </Routes>
                </MainLayout>
              </Router>
              <UpdateNotification />
            </NotificationProvider>
          </ThemeProvider>
        </QueryClientProvider>
      </Provider>
    </ErrorBoundary>
  );
};