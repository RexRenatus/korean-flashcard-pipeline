import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Stack,
  Alert,
  Tooltip,
  Divider,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  FileCopy as DuplicateIcon,
  Save as SaveIcon,
  Code as CodeIcon,
  Description as TemplateIcon,
} from '@mui/icons-material';
import { useDispatch, useSelector } from 'react-redux';
import { AppDispatch, RootState } from '@renderer/store';
import { useNotification } from '@renderer/providers/NotificationProvider';

interface ExportTemplate {
  id: string;
  name: string;
  description: string;
  format: 'json' | 'csv' | 'anki' | 'markdown' | 'custom';
  fields: string[];
  customFormat?: string;
  isDefault?: boolean;
  createdAt: string;
  updatedAt: string;
}

const DEFAULT_TEMPLATES: ExportTemplate[] = [
  {
    id: 'default-json',
    name: 'JSON (Full)',
    description: 'Complete flashcard data in JSON format',
    format: 'json',
    fields: ['word', 'meaning', 'example', 'nuances', 'stage1_output', 'stage2_output'],
    isDefault: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'default-csv',
    name: 'CSV (Simple)',
    description: 'Basic flashcard data for spreadsheet import',
    format: 'csv',
    fields: ['word', 'meaning', 'example'],
    isDefault: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'default-anki',
    name: 'Anki Import',
    description: 'Format compatible with Anki flashcard app',
    format: 'anki',
    fields: ['word', 'meaning', 'example', 'tags'],
    isDefault: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'default-markdown',
    name: 'Markdown Study Guide',
    description: 'Formatted markdown for study notes',
    format: 'markdown',
    fields: ['word', 'meaning', 'example', 'nuances'],
    isDefault: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
];

const AVAILABLE_FIELDS = [
  { value: 'word', label: 'Word' },
  { value: 'meaning', label: 'Meaning' },
  { value: 'example', label: 'Example' },
  { value: 'nuances', label: 'Nuances' },
  { value: 'stage1_output', label: 'Stage 1 Output' },
  { value: 'stage2_output', label: 'Stage 2 Output' },
  { value: 'tags', label: 'Tags' },
  { value: 'difficulty', label: 'Difficulty' },
  { value: 'created_at', label: 'Created Date' },
  { value: 'processed_at', label: 'Processed Date' },
];

export const ExportTemplates: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { showSuccess, showError } = useNotification();
  
  const [templates, setTemplates] = useState<ExportTemplate[]>([
    ...DEFAULT_TEMPLATES,
    // Load user templates from localStorage
    ...JSON.parse(localStorage.getItem('exportTemplates') || '[]'),
  ]);
  
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<ExportTemplate | null>(null);
  const [formData, setFormData] = useState<Partial<ExportTemplate>>({
    name: '',
    description: '',
    format: 'json',
    fields: ['word', 'meaning'],
    customFormat: '',
  });

  const saveTemplates = (newTemplates: ExportTemplate[]) => {
    const userTemplates = newTemplates.filter(t => !t.isDefault);
    localStorage.setItem('exportTemplates', JSON.stringify(userTemplates));
    setTemplates(newTemplates);
  };

  const handleEdit = (template: ExportTemplate) => {
    if (template.isDefault) {
      // Clone default template for editing
      setEditingTemplate(null);
      setFormData({
        ...template,
        id: undefined,
        name: `${template.name} (Copy)`,
        isDefault: false,
      });
    } else {
      setEditingTemplate(template);
      setFormData(template);
    }
    setEditDialogOpen(true);
  };

  const handleDelete = (templateId: string) => {
    const template = templates.find(t => t.id === templateId);
    if (template?.isDefault) {
      showError('Cannot delete default templates');
      return;
    }
    
    const newTemplates = templates.filter(t => t.id !== templateId);
    saveTemplates(newTemplates);
    showSuccess('Template deleted');
  };

  const handleDuplicate = (template: ExportTemplate) => {
    const newTemplate: ExportTemplate = {
      ...template,
      id: `template-${Date.now()}`,
      name: `${template.name} (Copy)`,
      isDefault: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    
    const newTemplates = [...templates, newTemplate];
    saveTemplates(newTemplates);
    showSuccess('Template duplicated');
  };

  const handleSave = () => {
    if (!formData.name || !formData.format || formData.fields?.length === 0) {
      showError('Please fill in all required fields');
      return;
    }

    let newTemplates: ExportTemplate[];
    
    if (editingTemplate) {
      // Update existing template
      newTemplates = templates.map(t => 
        t.id === editingTemplate.id
          ? {
              ...t,
              ...formData,
              updatedAt: new Date().toISOString(),
            }
          : t
      );
    } else {
      // Create new template
      const newTemplate: ExportTemplate = {
        id: `template-${Date.now()}`,
        name: formData.name!,
        description: formData.description || '',
        format: formData.format as ExportTemplate['format'],
        fields: formData.fields!,
        customFormat: formData.customFormat,
        isDefault: false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      newTemplates = [...templates, newTemplate];
    }
    
    saveTemplates(newTemplates);
    showSuccess(editingTemplate ? 'Template updated' : 'Template created');
    setEditDialogOpen(false);
    setEditingTemplate(null);
    setFormData({
      name: '',
      description: '',
      format: 'json',
      fields: ['word', 'meaning'],
      customFormat: '',
    });
  };

  const getFormatIcon = (format: string) => {
    switch (format) {
      case 'json':
        return <CodeIcon />;
      case 'csv':
        return <TemplateIcon />;
      case 'anki':
        return <TemplateIcon />;
      case 'markdown':
        return <TemplateIcon />;
      case 'custom':
        return <CodeIcon />;
      default:
        return <TemplateIcon />;
    }
  };

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h5">Export Templates</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => {
            setEditingTemplate(null);
            setFormData({
              name: '',
              description: '',
              format: 'json',
              fields: ['word', 'meaning'],
              customFormat: '',
            });
            setEditDialogOpen(true);
          }}
        >
          New Template
        </Button>
      </Box>

      <Paper>
        <List>
          {templates.map((template, index) => (
            <React.Fragment key={template.id}>
              {index > 0 && <Divider />}
              <ListItem>
                <Box sx={{ display: 'flex', alignItems: 'center', mr: 2 }}>
                  {getFormatIcon(template.format)}
                </Box>
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="subtitle1">{template.name}</Typography>
                      {template.isDefault && (
                        <Chip label="Default" size="small" color="primary" />
                      )}
                      <Chip label={template.format.toUpperCase()} size="small" variant="outlined" />
                    </Box>
                  }
                  secondary={
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        {template.description}
                      </Typography>
                      <Stack direction="row" spacing={0.5} sx={{ mt: 0.5 }}>
                        {template.fields.map((field) => (
                          <Chip
                            key={field}
                            label={AVAILABLE_FIELDS.find(f => f.value === field)?.label || field}
                            size="small"
                            sx={{ height: 20 }}
                          />
                        ))}
                      </Stack>
                    </Box>
                  }
                />
                <ListItemSecondaryAction>
                  <Tooltip title="Edit">
                    <IconButton onClick={() => handleEdit(template)}>
                      <EditIcon />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Duplicate">
                    <IconButton onClick={() => handleDuplicate(template)}>
                      <DuplicateIcon />
                    </IconButton>
                  </Tooltip>
                  {!template.isDefault && (
                    <Tooltip title="Delete">
                      <IconButton onClick={() => handleDelete(template.id)} color="error">
                        <DeleteIcon />
                      </IconButton>
                    </Tooltip>
                  )}
                </ListItemSecondaryAction>
              </ListItem>
            </React.Fragment>
          ))}
        </List>
      </Paper>

      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingTemplate ? 'Edit Template' : 'New Export Template'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <TextField
              fullWidth
              label="Template Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              sx={{ mb: 2 }}
              required
            />
            
            <TextField
              fullWidth
              label="Description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              multiline
              rows={2}
              sx={{ mb: 2 }}
            />
            
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Format</InputLabel>
              <Select
                value={formData.format}
                onChange={(e) => setFormData({ ...formData, format: e.target.value as ExportTemplate['format'] })}
                label="Format"
              >
                <MenuItem value="json">JSON</MenuItem>
                <MenuItem value="csv">CSV</MenuItem>
                <MenuItem value="anki">Anki</MenuItem>
                <MenuItem value="markdown">Markdown</MenuItem>
                <MenuItem value="custom">Custom</MenuItem>
              </Select>
            </FormControl>
            
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Fields to Export</InputLabel>
              <Select
                multiple
                value={formData.fields}
                onChange={(e) => setFormData({ ...formData, fields: e.target.value as string[] })}
                label="Fields to Export"
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {(selected as string[]).map((value) => (
                      <Chip
                        key={value}
                        label={AVAILABLE_FIELDS.find(f => f.value === value)?.label || value}
                        size="small"
                      />
                    ))}
                  </Box>
                )}
              >
                {AVAILABLE_FIELDS.map((field) => (
                  <MenuItem key={field.value} value={field.value}>
                    {field.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            
            {formData.format === 'custom' && (
              <TextField
                fullWidth
                label="Custom Format Template"
                value={formData.customFormat}
                onChange={(e) => setFormData({ ...formData, customFormat: e.target.value })}
                multiline
                rows={4}
                placeholder="Use {{field}} placeholders, e.g., {{word}}: {{meaning}}"
                helperText="Define your custom export format using field placeholders"
              />
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSave} variant="contained" startIcon={<SaveIcon />}>
            Save Template
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};