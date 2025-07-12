import React, { useState, useCallback } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  LinearProgress,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { useDispatch } from 'react-redux';
import { AppDispatch } from '@renderer/store';
import { importVocabulary } from '@renderer/store/vocabularySlice';

interface VocabularyUploadDialogProps {
  open: boolean;
  onClose: () => void;
}

interface ValidationResult {
  valid: boolean;
  warnings: string[];
  errors: string[];
  preview: Array<{
    korean: string;
    english?: string;
    status: 'valid' | 'duplicate' | 'invalid';
  }>;
}

export const VocabularyUploadDialog: React.FC<VocabularyUploadDialogProps> = ({
  open,
  onClose,
}) => {
  const dispatch = useDispatch<AppDispatch>();
  const [uploading, setUploading] = useState(false);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];
    setSelectedFile(file);

    // Read and validate file
    try {
      const text = await file.text();
      let data: any[] = [];

      if (file.name.endsWith('.csv')) {
        // Parse CSV
        const lines = text.split('\n').filter(line => line.trim());
        const hasHeader = lines[0].includes('korean') || lines[0].includes('Korean');
        const startIndex = hasHeader ? 1 : 0;

        data = lines.slice(startIndex).map(line => {
          const parts = line.split(',').map(p => p.trim());
          return {
            korean: parts[0],
            english: parts[1] || '',
          };
        });
      } else if (file.name.endsWith('.txt')) {
        // Parse TXT (one word per line)
        data = text.split('\n')
          .filter(line => line.trim())
          .map(line => ({ korean: line.trim() }));
      } else if (file.name.endsWith('.json')) {
        // Parse JSON
        data = JSON.parse(text);
      }

      // Validate data
      const validation: ValidationResult = {
        valid: true,
        warnings: [],
        errors: [],
        preview: [],
      };

      // Check for duplicates and validate
      const seen = new Set<string>();
      data.forEach((item, index) => {
        if (!item.korean) {
          validation.errors.push(`Row ${index + 1}: Missing Korean word`);
          validation.valid = false;
          return;
        }

        if (seen.has(item.korean)) {
          validation.warnings.push(`Duplicate word: ${item.korean}`);
          validation.preview.push({
            ...item,
            status: 'duplicate',
          });
        } else {
          seen.add(item.korean);
          validation.preview.push({
            ...item,
            status: 'valid',
          });
        }
      });

      setValidationResult(validation);
    } catch (error) {
      setValidationResult({
        valid: false,
        errors: [`Failed to parse file: ${error}`],
        warnings: [],
        preview: [],
      });
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'text/plain': ['.txt'],
      'application/json': ['.json'],
    },
    multiple: false,
  });

  const handleUpload = async () => {
    if (!selectedFile || !validationResult?.valid) return;

    setUploading(true);
    try {
      const format = selectedFile.name.endsWith('.csv') ? 'csv' :
                    selectedFile.name.endsWith('.txt') ? 'txt' : 'json';
      
      await dispatch(importVocabulary({
        filePath: selectedFile.path || selectedFile.name,
        format,
      }));

      onClose();
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setUploading(false);
    }
  };

  const handleClose = () => {
    if (!uploading) {
      setSelectedFile(null);
      setValidationResult(null);
      onClose();
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle>Import Vocabulary</DialogTitle>
      <DialogContent>
        {!selectedFile ? (
          <Box
            {...getRootProps()}
            sx={{
              border: '2px dashed',
              borderColor: isDragActive ? 'primary.main' : 'divider',
              borderRadius: 2,
              p: 4,
              textAlign: 'center',
              cursor: 'pointer',
              bgcolor: isDragActive ? 'action.hover' : 'background.paper',
              transition: 'all 0.2s',
              '&:hover': {
                borderColor: 'primary.main',
                bgcolor: 'action.hover',
              },
            }}
          >
            <input {...getInputProps()} />
            <UploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              Drop your file here or click to browse
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Supported formats: CSV, TXT, JSON
            </Typography>
          </Box>
        ) : (
          <Box>
            <Alert severity="info" sx={{ mb: 2 }}>
              Selected file: {selectedFile.name}
            </Alert>

            {validationResult && (
              <>
                {validationResult.errors.length > 0 && (
                  <Alert severity="error" sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Errors found:
                    </Typography>
                    <List dense>
                      {validationResult.errors.map((error, index) => (
                        <ListItem key={index}>
                          <ListItemIcon>
                            <ErrorIcon color="error" />
                          </ListItemIcon>
                          <ListItemText primary={error} />
                        </ListItem>
                      ))}
                    </List>
                  </Alert>
                )}

                {validationResult.warnings.length > 0 && (
                  <Alert severity="warning" sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Warnings:
                    </Typography>
                    <List dense>
                      {validationResult.warnings.map((warning, index) => (
                        <ListItem key={index}>
                          <ListItemIcon>
                            <WarningIcon color="warning" />
                          </ListItemIcon>
                          <ListItemText primary={warning} />
                        </ListItem>
                      ))}
                    </List>
                  </Alert>
                )}

                {validationResult.valid && (
                  <Alert severity="success" sx={{ mb: 2 }}>
                    <Typography variant="subtitle2">
                      File validated successfully!
                    </Typography>
                    <Typography variant="body2">
                      {validationResult.preview.filter(p => p.status === 'valid').length} valid words
                      ready for import
                    </Typography>
                  </Alert>
                )}

                <Typography variant="subtitle2" gutterBottom>
                  Preview (first 10 items):
                </Typography>
                <List dense sx={{ maxHeight: 200, overflow: 'auto' }}>
                  {validationResult.preview.slice(0, 10).map((item, index) => (
                    <ListItem key={index}>
                      <ListItemText
                        primary={item.korean}
                        secondary={item.english}
                      />
                      <Chip
                        label={item.status}
                        size="small"
                        color={
                          item.status === 'valid' ? 'success' :
                          item.status === 'duplicate' ? 'warning' : 'error'
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              </>
            )}
          </Box>
        )}

        {uploading && <LinearProgress sx={{ mt: 2 }} />}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={uploading}>
          Cancel
        </Button>
        {selectedFile && (
          <Button
            onClick={() => {
              setSelectedFile(null);
              setValidationResult(null);
            }}
            disabled={uploading}
          >
            Choose Different File
          </Button>
        )}
        <Button
          onClick={handleUpload}
          variant="contained"
          disabled={!validationResult?.valid || uploading}
          startIcon={<UploadIcon />}
        >
          Import
        </Button>
      </DialogActions>
    </Dialog>
  );
};