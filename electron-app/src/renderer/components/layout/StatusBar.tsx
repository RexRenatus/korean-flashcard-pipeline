import React from 'react';
import { Box, Typography, Chip } from '@mui/material';
import { Circle as CircleIcon } from '@mui/icons-material';
import { useSelector } from 'react-redux';
import { RootState } from '@renderer/store';

export const StatusBar: React.FC = () => {
  const { connectionStatus, apiHealth, lastSync } = useSelector(
    (state: RootState) => state.system
  );

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected':
      case 'healthy':
        return 'success';
      case 'connecting':
      case 'degraded':
        return 'warning';
      case 'disconnected':
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  const formatLastSync = (lastSync: string | null) => {
    if (!lastSync) return 'Never';
    
    const date = new Date(lastSync);
    const now = new Date();
    const diffMinutes = Math.floor((now.getTime() - date.getTime()) / 60000);
    
    if (diffMinutes < 1) return 'Just now';
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    if (diffMinutes < 1440) return `${Math.floor(diffMinutes / 60)}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <Box
      sx={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        height: 24,
        bgcolor: 'background.paper',
        borderTop: 1,
        borderColor: 'divider',
        display: 'flex',
        alignItems: 'center',
        px: 2,
        gap: 2,
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <CircleIcon
          sx={{
            fontSize: 8,
            color: `${getStatusColor(connectionStatus)}.main`,
          }}
        />
        <Typography variant="caption" color="text.secondary">
          {connectionStatus === 'connected' ? 'Connected' : 'Disconnected'}
        </Typography>
      </Box>

      <Chip
        label={`API: ${apiHealth}`}
        size="small"
        color={getStatusColor(apiHealth)}
        variant="outlined"
        sx={{ height: 20 }}
      />

      <Box sx={{ flexGrow: 1 }} />

      <Typography variant="caption" color="text.secondary">
        Last sync: {formatLastSync(lastSync)}
      </Typography>
    </Box>
  );
};