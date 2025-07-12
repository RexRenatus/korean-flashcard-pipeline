import React, { useState, useEffect } from 'react';
import {
  Snackbar,
  Alert,
  Button,
  LinearProgress,
  Box,
  Typography,
  IconButton,
} from '@mui/material';
import {
  Download as DownloadIcon,
  Refresh as RestartIcon,
  Close as CloseIcon,
  Update as UpdateIcon,
} from '@mui/icons-material';

interface UpdateStatus {
  status: 'idle' | 'checking' | 'available' | 'downloading' | 'ready' | 'error';
  version?: string;
  progress?: number;
  error?: string;
}

export const UpdateNotification: React.FC = () => {
  const [updateStatus, setUpdateStatus] = useState<UpdateStatus>({ status: 'idle' });
  const [open, setOpen] = useState(false);

  useEffect(() => {
    // Listen for update events
    const handleUpdateStatus = (event: any, data: any) => {
      const { status, data: updateData } = data;

      switch (status) {
        case 'checking-for-update':
          setUpdateStatus({ status: 'checking' });
          break;
        
        case 'update-available':
          setUpdateStatus({
            status: 'available',
            version: updateData.version,
          });
          setOpen(true);
          break;
        
        case 'update-not-available':
          setUpdateStatus({ status: 'idle' });
          break;
        
        case 'download-progress':
          setUpdateStatus(prev => ({
            ...prev,
            status: 'downloading',
            progress: updateData.percent,
          }));
          break;
        
        case 'update-downloaded':
          setUpdateStatus({
            status: 'ready',
            version: updateData.version,
          });
          break;
        
        case 'update-error':
          setUpdateStatus({
            status: 'error',
            error: updateData.message,
          });
          setOpen(true);
          break;
      }
    };

    window.electron?.on('updater:status', handleUpdateStatus);

    // Check for updates on mount
    checkForUpdates();

    return () => {
      window.electron?.removeListener('updater:status', handleUpdateStatus);
    };
  }, []);

  const checkForUpdates = async () => {
    try {
      await window.electron?.checkForUpdates();
    } catch (error) {
      console.error('Failed to check for updates:', error);
    }
  };

  const handleDownload = async () => {
    try {
      await window.electron?.downloadUpdate();
    } catch (error) {
      console.error('Failed to download update:', error);
    }
  };

  const handleInstall = async () => {
    try {
      await window.electron?.installUpdate();
    } catch (error) {
      console.error('Failed to install update:', error);
    }
  };

  const handleClose = () => {
    setOpen(false);
  };

  const renderContent = () => {
    switch (updateStatus.status) {
      case 'checking':
        return (
          <Alert
            severity="info"
            icon={<UpdateIcon />}
            action={
              <IconButton size="small" onClick={handleClose}>
                <CloseIcon fontSize="small" />
              </IconButton>
            }
          >
            Checking for updates...
          </Alert>
        );

      case 'available':
        return (
          <Alert
            severity="info"
            icon={<UpdateIcon />}
            action={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Button
                  size="small"
                  startIcon={<DownloadIcon />}
                  onClick={handleDownload}
                  color="inherit"
                >
                  Download
                </Button>
                <IconButton size="small" onClick={handleClose}>
                  <CloseIcon fontSize="small" />
                </IconButton>
              </Box>
            }
          >
            <Typography variant="body2">
              Update available: Version {updateStatus.version}
            </Typography>
          </Alert>
        );

      case 'downloading':
        return (
          <Alert
            severity="info"
            icon={<DownloadIcon />}
            action={
              <IconButton size="small" onClick={handleClose}>
                <CloseIcon fontSize="small" />
              </IconButton>
            }
          >
            <Box sx={{ width: '100%' }}>
              <Typography variant="body2" gutterBottom>
                Downloading update... {Math.round(updateStatus.progress || 0)}%
              </Typography>
              <LinearProgress
                variant="determinate"
                value={updateStatus.progress || 0}
                sx={{ mt: 1 }}
              />
            </Box>
          </Alert>
        );

      case 'ready':
        return (
          <Alert
            severity="success"
            icon={<UpdateIcon />}
            action={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Button
                  size="small"
                  startIcon={<RestartIcon />}
                  onClick={handleInstall}
                  color="inherit"
                >
                  Restart Now
                </Button>
                <IconButton size="small" onClick={handleClose}>
                  <CloseIcon fontSize="small" />
                </IconButton>
              </Box>
            }
          >
            <Typography variant="body2">
              Update ready! Restart to install version {updateStatus.version}
            </Typography>
          </Alert>
        );

      case 'error':
        return (
          <Alert
            severity="error"
            action={
              <IconButton size="small" onClick={handleClose}>
                <CloseIcon fontSize="small" />
              </IconButton>
            }
          >
            <Typography variant="body2">
              Update error: {updateStatus.error || 'Unknown error'}
            </Typography>
          </Alert>
        );

      default:
        return null;
    }
  };

  return (
    <Snackbar
      open={open}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      sx={{ maxWidth: 500 }}
    >
      <Box sx={{ width: '100%' }}>
        {renderContent()}
      </Box>
    </Snackbar>
  );
};