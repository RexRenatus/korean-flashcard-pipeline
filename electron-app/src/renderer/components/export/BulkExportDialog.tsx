import React, { useState, useEffect } from 'react';
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
  TextField,
  Checkbox,
  FormControlLabel,
  FormGroup,
  Chip,
  Stack,
  Alert,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
} from '@mui/material';
import {
  Download as DownloadIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  FolderOpen as FolderIcon,
  Code as JsonIcon,
  TableChart as CsvIcon,
  Description as FileIcon,
} from '@mui/icons-material';
import { useDispatch, useSelector } from 'react-redux';
import { AppDispatch, RootState } from '@renderer/store';
import { useNotification } from '@renderer/providers/NotificationProvider';

interface BulkExportDialogProps {
  open: boolean;
  onClose: () => void;
  selectedItems?: string[];
}

interface ExportOptions {
  format: 'json' | 'csv' | 'anki' | 'markdown' | 'custom';
  templateId?: string;
  includeMetadata: boolean;
  splitByTag: boolean;
  fileNamePattern: string;
  outputDirectory: string;
}

interface ExportProgress {
  total: number;
  completed: number;
  current: string;
  errors: string[];
}

export const BulkExportDialog: React.FC<BulkExportDialogProps> = ({
  open,
  onClose,
  selectedItems = [],
}) => {
  const dispatch = useDispatch<AppDispatch>();
  const { showSuccess, showError, showInfo } = useNotification();
  
  const [step, setStep] = useState<'configure' | 'exporting' | 'complete'>('configure');
  const [options, setOptions] = useState<ExportOptions>({
    format: 'json',
    includeMetadata: true,
    splitByTag: false,
    fileNamePattern: 'flashcards_{{date}}',
    outputDirectory: '',
  });
  
  const [progress, setProgress] = useState<ExportProgress>({
    total: 0,
    completed: 0,
    current: '',
    errors: [],
  });
  
  const [exportedFiles, setExportedFiles] = useState<string[]>([]);

  // Load export templates from localStorage
  const templates = [
    { id: 'default-json', name: 'JSON (Full)', format: 'json' },
    { id: 'default-csv', name: 'CSV (Simple)', format: 'csv' },
    { id: 'default-anki', name: 'Anki Import', format: 'anki' },
    { id: 'default-markdown', name: 'Markdown Study Guide', format: 'markdown' },
    ...JSON.parse(localStorage.getItem('exportTemplates') || '[]'),
  ];

  const handleSelectDirectory = async () => {
    try {
      const result = await window.electron.selectDirectory();
      if (result) {
        setOptions({ ...options, outputDirectory: result });
      }
    } catch (error) {
      showError('Failed to select directory');
    }
  };

  const handleExport = async () => {
    setStep('exporting');
    setProgress({
      total: selectedItems.length || 100, // If no items selected, export all
      completed: 0,
      current: 'Preparing export...',
      errors: [],
    });

    try {
      // Simulate export process
      for (let i = 0; i < (selectedItems.length || 100); i++) {
        setProgress(prev => ({
          ...prev,
          completed: i + 1,
          current: `Exporting item ${i + 1} of ${prev.total}...`,
        }));
        
        // Simulate processing time
        await new Promise(resolve => setTimeout(resolve, 50));
        
        // Simulate occasional errors
        if (Math.random() < 0.05) {
          setProgress(prev => ({
            ...prev,
            errors: [...prev.errors, `Failed to export item ${i + 1}`],
          }));
        }
      }

      // Generate file names based on options
      const files = [];
      const date = new Date().toISOString().split('T')[0];
      const baseName = options.fileNamePattern.replace('{{date}}', date);
      
      if (options.splitByTag) {
        files.push(`${baseName}_beginner.${options.format}`);
        files.push(`${baseName}_intermediate.${options.format}`);
        files.push(`${baseName}_advanced.${options.format}`);
      } else {
        files.push(`${baseName}.${options.format}`);
      }
      
      setExportedFiles(files);
      setStep('complete');
      showSuccess('Export completed successfully');
    } catch (error) {
      showError('Export failed: ' + error);
      setStep('configure');
    }
  };

  const handleClose = () => {
    if (step === 'exporting') {
      if (confirm('Export is in progress. Are you sure you want to cancel?')) {
        onClose();
      }
    } else {
      onClose();
      // Reset state after closing
      setTimeout(() => {
        setStep('configure');
        setProgress({ total: 0, completed: 0, current: '', errors: [] });
        setExportedFiles([]);
      }, 300);
    }
  };

  const getFormatIcon = (format: string) => {
    switch (format) {
      case 'json':
        return <JsonIcon />;
      case 'csv':
        return <CsvIcon />;
      default:
        return <FileIcon />;
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>
        {step === 'configure' && 'Bulk Export Flashcards'}
        {step === 'exporting' && 'Exporting...'}
        {step === 'complete' && 'Export Complete'}
      </DialogTitle>
      
      <DialogContent>
        {step === 'configure' && (
          <Box sx={{ pt: 2 }}>
            <Alert severity="info" sx={{ mb: 3 }}>
              {selectedItems.length > 0
                ? `Exporting ${selectedItems.length} selected flashcards`
                : 'Exporting all flashcards'}
            </Alert>

            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel>Export Format</InputLabel>
              <Select
                value={options.format}
                onChange={(e) => setOptions({ ...options, format: e.target.value as ExportOptions['format'] })}
                label="Export Format"
              >
                <MenuItem value="json">JSON - Full data with all fields</MenuItem>
                <MenuItem value="csv">CSV - Spreadsheet compatible</MenuItem>
                <MenuItem value="anki">Anki - Import into Anki app</MenuItem>
                <MenuItem value="markdown">Markdown - Study guide format</MenuItem>
                <MenuItem value="custom">Custom - Use custom template</MenuItem>
              </Select>
            </FormControl>

            {options.format === 'custom' && (
              <FormControl fullWidth sx={{ mb: 3 }}>
                <InputLabel>Template</InputLabel>
                <Select
                  value={options.templateId}
                  onChange={(e) => setOptions({ ...options, templateId: e.target.value })}
                  label="Template"
                >
                  {templates
                    .filter(t => t.format === 'custom')
                    .map(template => (
                      <MenuItem key={template.id} value={template.id}>
                        {template.name}
                      </MenuItem>
                    ))}
                </Select>
              </FormControl>
            )}

            <TextField
              fullWidth
              label="File Name Pattern"
              value={options.fileNamePattern}
              onChange={(e) => setOptions({ ...options, fileNamePattern: e.target.value })}
              helperText="Use {{date}} for current date"
              sx={{ mb: 3 }}
            />

            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" gutterBottom>
                Output Directory
              </Typography>
              <Stack direction="row" spacing={2} alignItems="center">
                <TextField
                  fullWidth
                  value={options.outputDirectory}
                  placeholder="Select output directory..."
                  InputProps={{ readOnly: true }}
                />
                <Button
                  variant="outlined"
                  startIcon={<FolderIcon />}
                  onClick={handleSelectDirectory}
                >
                  Browse
                </Button>
              </Stack>
            </Box>

            <Typography variant="subtitle2" gutterBottom>
              Export Options
            </Typography>
            <FormGroup>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={options.includeMetadata}
                    onChange={(e) => setOptions({ ...options, includeMetadata: e.target.checked })}
                  />
                }
                label="Include metadata (creation date, processing info)"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={options.splitByTag}
                    onChange={(e) => setOptions({ ...options, splitByTag: e.target.checked })}
                  />
                }
                label="Split into separate files by tag/difficulty"
              />
            </FormGroup>
          </Box>
        )}

        {step === 'exporting' && (
          <Box sx={{ pt: 2 }}>
            <Typography variant="body1" gutterBottom>
              {progress.current}
            </Typography>
            
            <Box sx={{ mb: 3 }}>
              <LinearProgress
                variant="determinate"
                value={(progress.completed / progress.total) * 100}
                sx={{ mb: 1 }}
              />
              <Typography variant="body2" color="text.secondary">
                {progress.completed} of {progress.total} items exported
              </Typography>
            </Box>

            {progress.errors.length > 0 && (
              <Alert severity="warning">
                {progress.errors.length} errors occurred during export
              </Alert>
            )}
          </Box>
        )}

        {step === 'complete' && (
          <Box sx={{ pt: 2 }}>
            <Alert
              severity={progress.errors.length > 0 ? 'warning' : 'success'}
              sx={{ mb: 3 }}
            >
              {progress.errors.length > 0
                ? `Export completed with ${progress.errors.length} errors`
                : 'All flashcards exported successfully!'}
            </Alert>

            <Typography variant="subtitle1" gutterBottom>
              Exported Files:
            </Typography>
            <List>
              {exportedFiles.map((file, index) => (
                <React.Fragment key={file}>
                  <ListItem>
                    <ListItemIcon>
                      {getFormatIcon(options.format)}
                    </ListItemIcon>
                    <ListItemText
                      primary={file}
                      secondary={`${options.outputDirectory}/${file}`}
                    />
                  </ListItem>
                  {index < exportedFiles.length - 1 && <Divider variant="inset" component="li" />}
                </React.Fragment>
              ))}
            </List>

            {progress.errors.length > 0 && (
              <Box sx={{ mt: 3 }}>
                <Typography variant="subtitle1" gutterBottom color="error">
                  Export Errors:
                </Typography>
                <List dense>
                  {progress.errors.map((error, index) => (
                    <ListItem key={index}>
                      <ListItemIcon>
                        <ErrorIcon color="error" fontSize="small" />
                      </ListItemIcon>
                      <ListItemText primary={error} />
                    </ListItem>
                  ))}
                </List>
              </Box>
            )}
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        {step === 'configure' && (
          <>
            <Button onClick={handleClose}>Cancel</Button>
            <Button
              onClick={handleExport}
              variant="contained"
              startIcon={<DownloadIcon />}
              disabled={!options.outputDirectory}
            >
              Start Export
            </Button>
          </>
        )}
        
        {step === 'exporting' && (
          <Button onClick={handleClose} color="error">
            Cancel Export
          </Button>
        )}
        
        {step === 'complete' && (
          <>
            <Button
              onClick={() => {
                // Open file explorer to output directory
                window.electron.openPath(options.outputDirectory);
              }}
              startIcon={<FolderIcon />}
            >
              Open Output Folder
            </Button>
            <Button onClick={handleClose} variant="contained">
              Close
            </Button>
          </>
        )}
      </DialogActions>
    </Dialog>
  );
};