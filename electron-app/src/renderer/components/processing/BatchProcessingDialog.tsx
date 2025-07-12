import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  RadioGroup,
  FormControlLabel,
  Radio,
  Chip,
  Alert,
  List,
  ListItem,
  ListItemText,
  Divider,
} from '@mui/material';
import {
  PlayArrow as StartIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { useDispatch, useSelector } from 'react-redux';
import { AppDispatch, RootState } from '@renderer/store';
import { startProcessing } from '@renderer/store/processingSlice';

interface BatchProcessingDialogProps {
  open: boolean;
  onClose: () => void;
  selectedIds?: number[];
}

export const BatchProcessingDialog: React.FC<BatchProcessingDialogProps> = ({
  open,
  onClose,
  selectedIds = [],
}) => {
  const dispatch = useDispatch<AppDispatch>();
  const vocabulary = useSelector((state: RootState) => state.vocabulary.items);
  
  const [options, setOptions] = useState({
    stage: 'both' as 'stage1' | 'stage2' | 'both',
    priority: 'normal' as 'low' | 'normal' | 'high',
    scope: selectedIds.length > 0 ? 'selected' : 'all' as 'all' | 'pending' | 'failed' | 'selected',
  });

  const getVocabularyToProcess = () => {
    switch (options.scope) {
      case 'all':
        return vocabulary.map(v => v.id);
      case 'pending':
        return vocabulary.filter(v => v.status === 'pending').map(v => v.id);
      case 'failed':
        return vocabulary.filter(v => v.status === 'failed').map(v => v.id);
      case 'selected':
        return selectedIds;
      default:
        return [];
    }
  };

  const vocabularyIds = getVocabularyToProcess();
  const itemCount = vocabularyIds.length;

  const handleStart = async () => {
    if (itemCount === 0) return;

    await dispatch(startProcessing({
      vocabularyIds,
      options: {
        stage: options.stage,
        priority: options.priority,
      },
    }));

    onClose();
  };

  const getEstimatedTime = () => {
    // Rough estimate: 2-3 seconds per item
    const avgTimePerItem = 2.5;
    const totalSeconds = itemCount * avgTimePerItem;
    const minutes = Math.floor(totalSeconds / 60);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes % 60}m`;
    }
    return `${minutes}m`;
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Start Batch Processing</DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 2 }}>
          {/* Scope Selection */}
          <FormControl component="fieldset" sx={{ mb: 3 }}>
            <Typography variant="subtitle2" gutterBottom>
              Select vocabulary to process:
            </Typography>
            <RadioGroup
              value={options.scope}
              onChange={(e) => setOptions({ ...options, scope: e.target.value as any })}
            >
              <FormControlLabel 
                value="all" 
                control={<Radio />} 
                label={`All vocabulary (${vocabulary.length} items)`}
              />
              <FormControlLabel 
                value="pending" 
                control={<Radio />} 
                label={`Pending only (${vocabulary.filter(v => v.status === 'pending').length} items)`}
              />
              <FormControlLabel 
                value="failed" 
                control={<Radio />} 
                label={`Failed only (${vocabulary.filter(v => v.status === 'failed').length} items)`}
              />
              {selectedIds.length > 0 && (
                <FormControlLabel 
                  value="selected" 
                  control={<Radio />} 
                  label={`Selected items (${selectedIds.length} items)`}
                />
              )}
            </RadioGroup>
          </FormControl>

          <Divider sx={{ my: 2 }} />

          {/* Processing Options */}
          <Typography variant="subtitle2" gutterBottom>
            Processing options:
          </Typography>
          
          <Box sx={{ mb: 2 }}>
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Processing Stage</InputLabel>
              <Select
                value={options.stage}
                onChange={(e) => setOptions({ ...options, stage: e.target.value as any })}
                label="Processing Stage"
              >
                <MenuItem value="stage1">Stage 1 - Basic Definition</MenuItem>
                <MenuItem value="stage2">Stage 2 - Nuanced Learning</MenuItem>
                <MenuItem value="both">Both Stages (Recommended)</MenuItem>
              </Select>
            </FormControl>

            <FormControl fullWidth>
              <InputLabel>Priority</InputLabel>
              <Select
                value={options.priority}
                onChange={(e) => setOptions({ ...options, priority: e.target.value as any })}
                label="Priority"
              >
                <MenuItem value="low">Low Priority</MenuItem>
                <MenuItem value="normal">Normal Priority</MenuItem>
                <MenuItem value="high">High Priority</MenuItem>
              </Select>
            </FormControl>
          </Box>

          <Divider sx={{ my: 2 }} />

          {/* Summary */}
          <Alert severity="info" icon={<InfoIcon />}>
            <Typography variant="subtitle2" gutterBottom>
              Processing Summary
            </Typography>
            <List dense>
              <ListItem>
                <ListItemText
                  primary="Items to process"
                  secondary={itemCount}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Estimated time"
                  secondary={getEstimatedTime()}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Processing stage"
                  secondary={
                    options.stage === 'both' 
                      ? 'Full pipeline (2 stages)' 
                      : `Stage ${options.stage.slice(-1)} only`
                  }
                />
              </ListItem>
            </List>
          </Alert>

          {itemCount === 0 && (
            <Alert severity="warning" sx={{ mt: 2 }}>
              No items match your selection criteria. Please adjust your filters.
            </Alert>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          onClick={handleStart}
          disabled={itemCount === 0}
          startIcon={<StartIcon />}
        >
          Start Processing ({itemCount} items)
        </Button>
      </DialogActions>
    </Dialog>
  );
};