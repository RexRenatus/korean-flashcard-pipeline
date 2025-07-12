import { useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { AppDispatch } from '@renderer/store';
import { useNotification } from '@renderer/providers/NotificationProvider';

interface ShortcutConfig {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  meta?: boolean;
  description: string;
  action: () => void;
  global?: boolean;
}

const SHORTCUTS: ShortcutConfig[] = [
  // Navigation
  {
    key: 'd',
    ctrl: true,
    description: 'Go to Dashboard',
    action: () => window.location.hash = '#/dashboard',
  },
  {
    key: 'v',
    ctrl: true,
    description: 'Go to Vocabulary',
    action: () => window.location.hash = '#/vocabulary',
  },
  {
    key: 'p',
    ctrl: true,
    description: 'Go to Processing',
    action: () => window.location.hash = '#/processing',
  },
  {
    key: 'f',
    ctrl: true,
    description: 'Go to Flashcards',
    action: () => window.location.hash = '#/flashcards',
  },
  {
    key: ',',
    ctrl: true,
    description: 'Open Settings',
    action: () => window.location.hash = '#/settings',
  },
  // Actions
  {
    key: 'n',
    ctrl: true,
    description: 'New Vocabulary',
    action: () => {
      const event = new CustomEvent('shortcut:new-vocabulary');
      window.dispatchEvent(event);
    },
  },
  {
    key: 'i',
    ctrl: true,
    description: 'Import Vocabulary',
    action: () => {
      const event = new CustomEvent('shortcut:import-vocabulary');
      window.dispatchEvent(event);
    },
  },
  {
    key: 'e',
    ctrl: true,
    description: 'Export',
    action: () => {
      const event = new CustomEvent('shortcut:export');
      window.dispatchEvent(event);
    },
  },
  {
    key: 'r',
    ctrl: true,
    shift: true,
    description: 'Start Processing',
    action: () => {
      const event = new CustomEvent('shortcut:start-processing');
      window.dispatchEvent(event);
    },
  },
  // Search
  {
    key: '/',
    ctrl: true,
    description: 'Focus Search',
    action: () => {
      const searchInput = document.querySelector('input[type="search"], input[placeholder*="Search"]') as HTMLInputElement;
      if (searchInput) {
        searchInput.focus();
        searchInput.select();
      }
    },
  },
  // Help
  {
    key: '?',
    shift: true,
    description: 'Show Keyboard Shortcuts',
    action: () => {
      const event = new CustomEvent('shortcut:show-help');
      window.dispatchEvent(event);
    },
  },
];

export const useKeyboardShortcuts = (additionalShortcuts: ShortcutConfig[] = []) => {
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  const { showInfo } = useNotification();
  const enabledRef = useRef(true);

  const allShortcuts = [...SHORTCUTS, ...additionalShortcuts];

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (!enabledRef.current) return;

    // Don't trigger shortcuts when typing in inputs
    const target = event.target as HTMLElement;
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.contentEditable === 'true') {
      // Allow Escape to blur the input
      if (event.key === 'Escape') {
        target.blur();
      }
      return;
    }

    // Find matching shortcut
    const shortcut = allShortcuts.find(s => {
      const keyMatch = s.key.toLowerCase() === event.key.toLowerCase();
      const ctrlMatch = s.ctrl ? (event.ctrlKey || event.metaKey) : !(event.ctrlKey || event.metaKey);
      const shiftMatch = s.shift ? event.shiftKey : !event.shiftKey;
      const altMatch = s.alt ? event.altKey : !event.altKey;
      
      return keyMatch && ctrlMatch && shiftMatch && altMatch;
    });

    if (shortcut) {
      event.preventDefault();
      shortcut.action();
    }
  }, [allShortcuts]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const setEnabled = (enabled: boolean) => {
    enabledRef.current = enabled;
  };

  const showShortcutsHelp = () => {
    const event = new CustomEvent('shortcut:show-help');
    window.dispatchEvent(event);
  };

  return {
    shortcuts: allShortcuts,
    setEnabled,
    showShortcutsHelp,
  };
};

// Global keyboard shortcuts for Electron menu
export const setupGlobalShortcuts = () => {
  // These will be handled by Electron's globalShortcut API
  const globalShortcuts = [
    { accelerator: 'CmdOrCtrl+Q', action: 'quit' },
    { accelerator: 'CmdOrCtrl+W', action: 'close-window' },
    { accelerator: 'F11', action: 'toggle-fullscreen' },
    { accelerator: 'CmdOrCtrl+Shift+I', action: 'toggle-devtools' },
    { accelerator: 'CmdOrCtrl+R', action: 'reload' },
    { accelerator: 'CmdOrCtrl+=', action: 'zoom-in' },
    { accelerator: 'CmdOrCtrl+-', action: 'zoom-out' },
    { accelerator: 'CmdOrCtrl+0', action: 'zoom-reset' },
  ];

  return globalShortcuts;
};