import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Stack,
  Chip,
  IconButton,
  Collapse,
  List,
  ListItem,
  ListItemText,
  Button,
} from '@mui/material';
import {
  Pause as PauseIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Timer as TimerIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material';

interface ProcessingProgressProps {
  task: {
    taskId: string;
    status: string;
    progress: number;
    currentItem?: string;
    stats?: {
      total: number;
      processed: number;
      succeeded: number;
      failed: number;
      remainingTime?: number;
    };
    error?: string;
    priority?: string;
    currentStage?: string;
  };
  onPause?: () => void;
  onResume?: () => void;
  onCancel?: () => void;
  showDetails?: boolean;
}

export const ProcessingProgress: React.FC<ProcessingProgressProps> = ({
  task,
  onPause,
  onResume,
  onCancel,
  showDetails = true,
}) => {
  const [expanded, setExpanded] = React.useState(false);

  const getStatusColor = () => {
    switch (task.status) {
      case 'completed':
        return 'success';
      case 'processing':
        return 'primary';
      case 'failed':
        return 'error';
      case 'cancelled':
        return 'warning';
      case 'paused':
        return 'info';
      default:
        return 'default';
    }
  };

  const formatTime = (seconds?: number) => {
    if (!seconds) return '--';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  const getProcessingSpeed = () => {
    if (!task.stats || task.stats.processed === 0) return 0;
    // Calculate items per minute
    return Math.round((task.stats.processed / task.stats.total) * 60);
  };

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2}>
          {/* Header */}
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Box>
              <Typography variant="h6" gutterBottom>
                Task {task.taskId.slice(0, 8)}
              </Typography>
              <Stack direction="row" spacing={1}>
                <Chip
                  label={task.status}
                  size="small"
                  color={getStatusColor()}
                />
                {task.priority && (
                  <Chip
                    label={`Priority: ${task.priority}`}
                    size="small"
                    variant="outlined"
                  />
                )}
                {task.currentStage && (
                  <Chip
                    label={`Stage: ${task.currentStage}`}
                    size="small"
                    variant="outlined"
                  />
                )}
              </Stack>
            </Box>
            
            {/* Action buttons */}
            <Stack direction="row" spacing={1}>
              {task.status === 'processing' && onPause && (
                <IconButton onClick={onPause} size="small">
                  <PauseIcon />
                </IconButton>
              )}
              {task.status === 'paused' && onResume && (
                <IconButton onClick={onResume} size="small">
                  <PlayIcon />
                </IconButton>
              )}
              {['processing', 'paused', 'queued'].includes(task.status) && onCancel && (
                <IconButton onClick={onCancel} size="small" color="error">
                  <StopIcon />
                </IconButton>
              )}
              {showDetails && (
                <IconButton
                  onClick={() => setExpanded(!expanded)}
                  size="small"
                >
                  {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </IconButton>
              )}
            </Stack>
          </Box>

          {/* Progress bar */}
          <Box>
            <Box display="flex" justifyContent="space-between" mb={1}>
              <Typography variant="body2" color="text.secondary">
                {task.stats
                  ? `${task.stats.processed} / ${task.stats.total} items`
                  : 'Processing...'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {task.progress}%
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={task.progress}
              color={getStatusColor()}
              sx={{ height: 8, borderRadius: 1 }}
            />
          </Box>

          {/* Current item */}
          {task.currentItem && (
            <Typography variant="body2" color="text.secondary" noWrap>
              Processing: {task.currentItem}
            </Typography>
          )}

          {/* Stats */}
          {task.stats && (
            <Box display="flex" gap={2}>
              <Box display="flex" alignItems="center" gap={0.5}>
                <TimerIcon fontSize="small" color="action" />
                <Typography variant="body2" color="text.secondary">
                  ETA: {formatTime(task.stats.remainingTime)}
                </Typography>
              </Box>
              <Box display="flex" alignItems="center" gap={0.5}>
                <SpeedIcon fontSize="small" color="action" />
                <Typography variant="body2" color="text.secondary">
                  {getProcessingSpeed()} items/min
                </Typography>
              </Box>
            </Box>
          )}

          {/* Error message */}
          {task.error && (
            <Typography variant="body2" color="error">
              Error: {task.error}
            </Typography>
          )}

          {/* Expanded details */}
          <Collapse in={expanded}>
            <Box sx={{ mt: 2, pt: 2, borderTop: 1, borderColor: 'divider' }}>
              <Typography variant="subtitle2" gutterBottom>
                Processing Details
              </Typography>
              {task.stats && (
                <List dense>
                  <ListItem>
                    <ListItemText
                      primary="Succeeded"
                      secondary={task.stats.succeeded}
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="Failed"
                      secondary={task.stats.failed}
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="Success Rate"
                      secondary={`${Math.round(
                        (task.stats.succeeded / task.stats.processed) * 100
                      )}%`}
                    />
                  </ListItem>
                </List>
              )}
            </Box>
          </Collapse>
        </Stack>
      </CardContent>
    </Card>
  );
};