import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  LinearProgress,
  Grid,
  Card,
  CardContent,
  CardActions,
  Chip,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Collapse,
  Alert,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Stop as StopIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Error as ErrorIcon,
  CheckCircle as SuccessIcon,
  Schedule as PendingIcon,
  WifiOff as DisconnectedIcon,
  Wifi as ConnectedIcon,
} from '@mui/icons-material';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '@renderer/store';
import {
  startProcessing,
  pauseProcessing,
  resumeProcessing,
  cancelProcessing,
  fetchProcessingStatus,
} from '@renderer/store/processingSlice';
import { useWebSocket } from '@renderer/hooks/useWebSocket';

interface ProcessingTaskCardProps {
  task: any; // Replace with proper type
  onPause: () => void;
  onResume: () => void;
  onCancel: () => void;
  onRetry: () => void;
}

const ProcessingTaskCard: React.FC<ProcessingTaskCardProps> = ({
  task,
  onPause,
  onResume,
  onCancel,
  onRetry,
}) => {
  const [expanded, setExpanded] = useState(false);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'processing':
        return 'warning';
      case 'failed':
        return 'error';
      case 'paused':
        return 'info';
      default:
        return 'default';
    }
  };

  const getProgressValue = () => {
    if (task.total === 0) return 0;
    return (task.processed / task.total) * 100;
  };

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h6">Task {task.taskId.slice(0, 8)}</Typography>
          <Chip
            label={task.status}
            color={getStatusColor(task.status)}
            size="small"
          />
        </Box>

        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2">
              Progress: {task.processed} / {task.total}
            </Typography>
            <Typography variant="body2">{Math.round(getProgressValue())}%</Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={getProgressValue()}
            color={getStatusColor(task.status)}
          />
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            Stage: {task.currentStage}
          </Typography>
          {task.estimatedTimeRemaining && (
            <Typography variant="body2" color="text.secondary">
              ETA: {Math.round(task.estimatedTimeRemaining / 60)}m
            </Typography>
          )}
        </Box>

        {task.errors && task.errors.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Button
              size="small"
              onClick={() => setExpanded(!expanded)}
              endIcon={expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            >
              Errors ({task.errors.length})
            </Button>
            <Collapse in={expanded}>
              <List dense>
                {task.errors.slice(0, 5).map((error: any, index: number) => (
                  <ListItem key={index}>
                    <ListItemText
                      primary={error.word}
                      secondary={error.message}
                    />
                  </ListItem>
                ))}
              </List>
            </Collapse>
          </Box>
        )}
      </CardContent>

      <CardActions>
        {task.status === 'processing' && (
          <Button size="small" startIcon={<PauseIcon />} onClick={onPause}>
            Pause
          </Button>
        )}
        {task.status === 'paused' && (
          <Button size="small" startIcon={<PlayIcon />} onClick={onResume}>
            Resume
          </Button>
        )}
        {['processing', 'paused'].includes(task.status) && (
          <Button size="small" startIcon={<StopIcon />} onClick={onCancel} color="error">
            Cancel
          </Button>
        )}
        {task.status === 'failed' && (
          <Button size="small" startIcon={<RefreshIcon />} onClick={onRetry}>
            Retry
          </Button>
        )}
      </CardActions>
    </Card>
  );
};

export const ProcessingMonitor: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { activeTasks, queuedTasks, recentTasks, loading } = useSelector(
    (state: RootState) => state.processing
  );
  const { items: vocabularyItems } = useSelector((state: RootState) => state.vocabulary);

  const [selectedWords, setSelectedWords] = useState<number[]>([]);
  const [processingOptions, setProcessingOptions] = useState({
    priority: 'normal' as 'low' | 'normal' | 'high',
    stage: 'full_pipeline' as 'stage1' | 'stage2' | 'full_pipeline',
  });

  // Use WebSocket for real-time updates
  const { isConnected, lastMessage } = useWebSocket();

  useEffect(() => {
    // Initial fetch of processing status
    dispatch(fetchProcessingStatus());
  }, [dispatch]);

  const handleStartProcessing = async () => {
    if (selectedWords.length === 0) {
      // Get all pending words
      const pendingWords = vocabularyItems
        .filter(item => !item.processingStatus || item.processingStatus === 'pending')
        .map(item => item.id);
      
      if (pendingWords.length > 0) {
        await dispatch(startProcessing({
          vocabularyIds: pendingWords,
          options: processingOptions,
        }));
      }
    } else {
      await dispatch(startProcessing({
        vocabularyIds: selectedWords,
        options: processingOptions,
      }));
    }
  };

  const handlePauseTask = (taskId: string) => {
    dispatch(pauseProcessing(taskId));
  };

  const handleResumeTask = (taskId: string) => {
    dispatch(resumeProcessing(taskId));
  };

  const handleCancelTask = (taskId: string) => {
    dispatch(cancelProcessing(taskId));
  };

  const handleRetryTask = (task: any) => {
    // Implement retry logic
    console.log('Retry task:', task);
  };

  const totalActive = activeTasks.length;
  const totalQueued = queuedTasks.length;
  const totalProcessing = activeTasks.filter(t => t.status === 'processing').length;

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Box>
          <Typography variant="h4" gutterBottom>
            Processing Monitor
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Monitor and control flashcard processing tasks
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <Chip
            icon={isConnected ? <ConnectedIcon /> : <DisconnectedIcon />}
            label={isConnected ? 'Connected' : 'Disconnected'}
            color={isConnected ? 'success' : 'error'}
            size="small"
          />
          <Button
            variant="contained"
            startIcon={<PlayIcon />}
            onClick={handleStartProcessing}
            disabled={totalProcessing >= 3} // Max 3 concurrent tasks
          >
            Start Processing
          </Button>
        </Box>
      </Box>

      {/* Overview Stats */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={4}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h4">{totalActive}</Typography>
            <Typography variant="body2" color="text.secondary">
              Active Tasks
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h4">{totalQueued}</Typography>
            <Typography variant="body2" color="text.secondary">
              Queued
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h4">{totalProcessing}</Typography>
            <Typography variant="body2" color="text.secondary">
              Processing
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Active Tasks */}
      {activeTasks.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Active Tasks
          </Typography>
          <Grid container spacing={2}>
            {activeTasks.map((task) => (
              <Grid item xs={12} md={6} key={task.taskId}>
                <ProcessingTaskCard
                  task={task}
                  onPause={() => handlePauseTask(task.taskId)}
                  onResume={() => handleResumeTask(task.taskId)}
                  onCancel={() => handleCancelTask(task.taskId)}
                  onRetry={() => handleRetryTask(task)}
                />
              </Grid>
            ))}
          </Grid>
        </Box>
      )}

      {/* Queued Tasks */}
      {queuedTasks.length > 0 && (
        <Paper sx={{ p: 2, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Queued Tasks ({queuedTasks.length})
          </Typography>
          <List>
            {queuedTasks.slice(0, 5).map((task, index) => (
              <ListItem key={task.taskId} divider={index < queuedTasks.length - 1}>
                <ListItemText
                  primary={`Task ${task.taskId.slice(0, 8)}`}
                  secondary={`${task.vocabularyCount} words • Priority: ${task.priority}`}
                />
                <ListItemSecondaryAction>
                  <IconButton
                    edge="end"
                    onClick={() => handleCancelTask(task.taskId)}
                  >
                    <StopIcon />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        </Paper>
      )}

      {/* Recent Tasks */}
      {recentTasks.length > 0 && (
        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            Recent Tasks
          </Typography>
          <List>
            {recentTasks.slice(0, 10).map((task, index) => (
              <ListItem key={task.taskId} divider={index < recentTasks.length - 1}>
                <ListItemText
                  primary={`Task ${task.taskId.slice(0, 8)}`}
                  secondary={`Completed ${new Date(task.completedAt).toLocaleString()}`}
                />
                <ListItemSecondaryAction>
                  {task.status === 'completed' && (
                    <SuccessIcon color="success" />
                  )}
                  {task.status === 'failed' && (
                    <ErrorIcon color="error" />
                  )}
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        </Paper>
      )}

      {/* Empty State */}
      {activeTasks.length === 0 && queuedTasks.length === 0 && (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <PendingIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            No Active Processing Tasks
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Click "Start Processing" to begin processing your vocabulary
          </Typography>
        </Paper>
      )}
    </Box>
  );
};