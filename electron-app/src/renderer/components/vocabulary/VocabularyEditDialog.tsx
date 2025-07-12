import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  FormControlLabel,
  Switch,
  Alert,
  Chip,
  Stack,
} from '@mui/material';
import { useDispatch } from 'react-redux';
import { AppDispatch } from '@renderer/store';
import { addVocabulary, updateVocabulary } from '@renderer/store/vocabularySlice';

interface VocabularyEditDialogProps {
  open: boolean;
  onClose: () => void;
  editItem?: {
    id: number;
    korean: string;
    english?: string;
    tags?: string[];
    priority?: number;
  } | null;
}

export const VocabularyEditDialog: React.FC<VocabularyEditDialogProps> = ({
  open,
  onClose,
  editItem,
}) => {
  const dispatch = useDispatch<AppDispatch>();
  const [korean, setKorean] = useState('');
  const [english, setEnglish] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [priority, setPriority] = useState(false);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (editItem) {
      setKorean(editItem.korean);
      setEnglish(editItem.english || '');
      setTags(editItem.tags || []);
      setPriority((editItem.priority || 0) > 0);
    } else {
      setKorean('');
      setEnglish('');
      setTags([]);
      setPriority(false);
    }
    setError('');
  }, [editItem, open]);

  const handleAddTag = () => {
    const trimmedTag = tagInput.trim();
    if (trimmedTag && !tags.includes(trimmedTag)) {
      setTags([...tags, trimmedTag]);
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setTags(tags.filter(tag => tag !== tagToRemove));
  };

  const handleSave = async () => {
    if (!korean.trim()) {
      setError('Korean word is required');
      return;
    }

    setSaving(true);
    try {
      const vocabularyData = {
        korean: korean.trim(),
        english: english.trim() || undefined,
        tags,
        priority: priority ? 1 : 0,
      };

      if (editItem) {
        await dispatch(updateVocabulary({
          id: editItem.id,
          ...vocabularyData,
        }));
      } else {
        await dispatch(addVocabulary(vocabularyData));
      }

      onClose();
    } catch (err) {
      setError(`Failed to save: ${err}`);
    } finally {
      setSaving(false);
    }
  };

  const handleClose = () => {
    if (!saving) {
      onClose();
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle>
        {editItem ? 'Edit Vocabulary' : 'Add New Vocabulary'}
      </DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 2 }}>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <TextField
            label="Korean Word"
            value={korean}
            onChange={(e) => setKorean(e.target.value)}
            fullWidth
            required
            autoFocus
            sx={{ mb: 2 }}
            error={!korean.trim() && error !== ''}
            helperText={!korean.trim() && error ? 'Required' : ''}
          />

          <TextField
            label="English Translation (Optional)"
            value={english}
            onChange={(e) => setEnglish(e.target.value)}
            fullWidth
            sx={{ mb: 2 }}
          />

          <Box sx={{ mb: 2 }}>
            <TextField
              label="Add Tag"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleAddTag();
                }
              }}
              fullWidth
              size="small"
              sx={{ mb: 1 }}
              placeholder="Press Enter to add tag"
            />
            <Stack direction="row" spacing={1} flexWrap="wrap">
              {tags.map((tag) => (
                <Chip
                  key={tag}
                  label={tag}
                  onDelete={() => handleRemoveTag(tag)}
                  size="small"
                  sx={{ mb: 1 }}
                />
              ))}
            </Stack>
          </Box>

          <FormControlLabel
            control={
              <Switch
                checked={priority}
                onChange={(e) => setPriority(e.target.checked)}
              />
            }
            label="High Priority"
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={saving}>
          Cancel
        </Button>
        <Button
          onClick={handleSave}
          variant="contained"
          disabled={saving || !korean.trim()}
        >
          {saving ? 'Saving...' : 'Save'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};