import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Typography,
  Box,
  Divider,
  IconButton,
} from '@mui/material';
import {
  Close as CloseIcon,
  Keyboard as KeyboardIcon,
} from '@mui/icons-material';
import { useKeyboardShortcuts } from '@renderer/hooks/useKeyboardShortcuts';

interface KeyboardShortcutsDialogProps {
  open?: boolean;
  onClose?: () => void;
}

export const KeyboardShortcutsDialog: React.FC<KeyboardShortcutsDialogProps> = ({
  open: controlledOpen,
  onClose: controlledOnClose,
}) => {
  const [open, setOpen] = useState(controlledOpen || false);
  const { shortcuts } = useKeyboardShortcuts();

  useEffect(() => {
    if (controlledOpen !== undefined) {
      setOpen(controlledOpen);
    }
  }, [controlledOpen]);

  useEffect(() => {
    const handleShowHelp = () => setOpen(true);
    window.addEventListener('shortcut:show-help', handleShowHelp);
    return () => window.removeEventListener('shortcut:show-help', handleShowHelp);
  }, []);

  const handleClose = () => {
    setOpen(false);
    controlledOnClose?.();
  };

  const formatKey = (key: string) => {
    const keyMap: Record<string, string> = {
      ' ': 'Space',
      'ArrowUp': '↑',
      'ArrowDown': '↓',
      'ArrowLeft': '←',
      'ArrowRight': '→',
    };
    return keyMap[key] || key.toUpperCase();
  };

  const renderShortcut = (shortcut: any) => {
    const keys = [];
    
    if (shortcut.ctrl) keys.push('Ctrl');
    if (shortcut.alt) keys.push('Alt');
    if (shortcut.shift) keys.push('Shift');
    if (shortcut.meta) keys.push('⌘');
    keys.push(formatKey(shortcut.key));

    return (
      <Box sx={{ display: 'flex', gap: 0.5 }}>
        {keys.map((key, index) => (
          <React.Fragment key={index}>
            {index > 0 && <Typography variant="body2">+</Typography>}
            <Chip
              label={key}
              size="small"
              sx={{
                height: 24,
                backgroundColor: 'action.hover',
                fontFamily: 'monospace',
              }}
            />
          </React.Fragment>
        ))}
      </Box>
    );
  };

  // Group shortcuts by category
  const navigationShortcuts = shortcuts.filter(s => 
    s.description.includes('Go to') || s.description.includes('Open')
  );
  const actionShortcuts = shortcuts.filter(s => 
    !s.description.includes('Go to') && 
    !s.description.includes('Open') &&
    !s.description.includes('Show')
  );
  const otherShortcuts = shortcuts.filter(s => 
    s.description.includes('Show') && !s.description.includes('Go to')
  );

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { height: '80vh' }
      }}
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <KeyboardIcon />
          <Typography variant="h6">Keyboard Shortcuts</Typography>
        </Box>
        <IconButton onClick={handleClose} size="small">
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      
      <DialogContent>
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Navigation
          </Typography>
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Shortcut</TableCell>
                  <TableCell>Description</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {navigationShortcuts.map((shortcut, index) => (
                  <TableRow key={index}>
                    <TableCell>{renderShortcut(shortcut)}</TableCell>
                    <TableCell>{shortcut.description}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Actions
          </Typography>
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Shortcut</TableCell>
                  <TableCell>Description</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {actionShortcuts.map((shortcut, index) => (
                  <TableRow key={index}>
                    <TableCell>{renderShortcut(shortcut)}</TableCell>
                    <TableCell>{shortcut.description}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Other
          </Typography>
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Shortcut</TableCell>
                  <TableCell>Description</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {otherShortcuts.map((shortcut, index) => (
                  <TableRow key={index}>
                    <TableCell>{renderShortcut(shortcut)}</TableCell>
                    <TableCell>{shortcut.description}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>

        <Divider sx={{ my: 2 }} />

        <Typography variant="body2" color="text.secondary">
          <strong>Tip:</strong> Press <Chip label="Esc" size="small" sx={{ height: 20 }} /> to exit any input field or dialog.
        </Typography>
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};