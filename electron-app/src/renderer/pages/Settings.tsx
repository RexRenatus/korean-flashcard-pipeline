import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Switch,
  FormControlLabel,
  Divider,
  Alert,
  Tabs,
  Tab,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Slider,
  Stack,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  ToggleButtonGroup,
  ToggleButton,
  Grid,
} from '@mui/material';
import {
  Save as SaveIcon,
  Restore as RestoreIcon,
  Info as InfoIcon,
  Key as ApiKeyIcon,
  Visibility as ShowIcon,
  VisibilityOff as HideIcon,
  Brightness4 as DarkModeIcon,
  Brightness7 as LightModeIcon,
  Palette as PaletteIcon,
} from '@mui/icons-material';
import { useDispatch, useSelector } from 'react-redux';
import { AppDispatch, RootState } from '@renderer/store';
import { updateConfig } from '@renderer/store/configSlice';
import { useTheme } from '@renderer/contexts/ThemeContext';
import { KeyboardShortcutsDialog } from '@renderer/components/common/KeyboardShortcutsDialog';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index, ...other }) => {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`settings-tabpanel-${index}`}
      aria-labelledby={`settings-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
};

export const Settings: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const config = useSelector((state: RootState) => state.config);
  const { mode, toggleTheme, primaryColor, setPrimaryColor } = useTheme();
  
  const [tabValue, setTabValue] = useState(0);
  const [showApiKey, setShowApiKey] = useState(false);
  const [tempConfig, setTempConfig] = useState(config);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const [shortcutsDialogOpen, setShortcutsDialogOpen] = useState(false);

  useEffect(() => {
    setTempConfig(config);
  }, [config]);

  const handleChange = (section: string, key: string, value: any) => {
    setTempConfig({
      ...tempConfig,
      [section]: {
        ...tempConfig[section],
        [key]: value,
      },
    });
  };

  const handleSave = async () => {
    setSaveStatus('saving');
    try {
      await dispatch(updateConfig(tempConfig));
      setSaveStatus('saved');
      setTimeout(() => setSaveStatus('idle'), 2000);
    } catch (error) {
      setSaveStatus('error');
      setTimeout(() => setSaveStatus('idle'), 3000);
    }
  };

  const handleReset = () => {
    setResetDialogOpen(false);
    // Reset to default config
    const defaultConfig = {
      api: {
        base_url: 'https://openrouter.ai/api/v1',
        model: 'anthropic/claude-3.5-sonnet-20241022',
        timeout: 30,
        max_retries: 3,
      },
      processing: {
        batch_size: 10,
        parallel_requests: 3,
        rate_limit_rpm: 60,
        enable_cache: true,
      },
      cache: {
        ttl_hours: 24,
        max_size_mb: 100,
        cleanup_interval_hours: 6,
      },
      database: {
        path: './pipeline.db',
        backup_enabled: true,
        backup_interval_days: 7,
      },
    };
    setTempConfig(defaultConfig);
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4">Settings</Typography>
        <Stack direction="row" spacing={2}>
          <Button
            variant="outlined"
            startIcon={<RestoreIcon />}
            onClick={() => setResetDialogOpen(true)}
          >
            Reset to Defaults
          </Button>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSave}
            disabled={saveStatus === 'saving'}
          >
            {saveStatus === 'saving' ? 'Saving...' : 'Save Changes'}
          </Button>
        </Stack>
      </Box>

      {saveStatus === 'saved' && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Settings saved successfully!
        </Alert>
      )}

      {saveStatus === 'error' && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to save settings. Please try again.
        </Alert>
      )}

      <Paper>
        <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
          <Tab label="API Configuration" />
          <Tab label="Processing" />
          <Tab label="Cache" />
          <Tab label="Database" />
          <Tab label="Appearance" />
          <Tab label="Advanced" />
        </Tabs>

        <TabPanel value={tabValue} index={0}>
          <Typography variant="h6" gutterBottom>
            API Configuration
          </Typography>
          
          <TextField
            fullWidth
            label="API Base URL"
            value={tempConfig.api?.base_url || ''}
            onChange={(e) => handleChange('api', 'base_url', e.target.value)}
            sx={{ mb: 2 }}
          />

          <Box sx={{ mb: 2, position: 'relative' }}>
            <TextField
              fullWidth
              label="API Key"
              type={showApiKey ? 'text' : 'password'}
              value={tempConfig.api?.api_key || ''}
              onChange={(e) => handleChange('api', 'api_key', e.target.value)}
              InputProps={{
                endAdornment: (
                  <IconButton
                    onClick={() => setShowApiKey(!showApiKey)}
                    edge="end"
                  >
                    {showApiKey ? <HideIcon /> : <ShowIcon />}
                  </IconButton>
                ),
              }}
            />
          </Box>

          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Model</InputLabel>
            <Select
              value={tempConfig.api?.model || ''}
              onChange={(e) => handleChange('api', 'model', e.target.value)}
              label="Model"
            >
              <MenuItem value="anthropic/claude-3.5-sonnet-20241022">Claude 3.5 Sonnet</MenuItem>
              <MenuItem value="anthropic/claude-3-opus-20240229">Claude 3 Opus</MenuItem>
              <MenuItem value="anthropic/claude-3-haiku-20240307">Claude 3 Haiku</MenuItem>
              <MenuItem value="openai/gpt-4-turbo">GPT-4 Turbo</MenuItem>
              <MenuItem value="openai/gpt-3.5-turbo">GPT-3.5 Turbo</MenuItem>
            </Select>
          </FormControl>

          <Typography gutterBottom>Timeout (seconds)</Typography>
          <Slider
            value={tempConfig.api?.timeout || 30}
            onChange={(_, value) => handleChange('api', 'timeout', value)}
            min={10}
            max={120}
            marks
            valueLabelDisplay="auto"
            sx={{ mb: 2 }}
          />

          <Typography gutterBottom>Max Retries</Typography>
          <Slider
            value={tempConfig.api?.max_retries || 3}
            onChange={(_, value) => handleChange('api', 'max_retries', value)}
            min={0}
            max={10}
            marks
            valueLabelDisplay="auto"
          />
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <Typography variant="h6" gutterBottom>
            Processing Configuration
          </Typography>

          <Typography gutterBottom>Batch Size</Typography>
          <Slider
            value={tempConfig.processing?.batch_size || 10}
            onChange={(_, value) => handleChange('processing', 'batch_size', value)}
            min={1}
            max={50}
            marks
            valueLabelDisplay="auto"
            sx={{ mb: 3 }}
          />

          <Typography gutterBottom>Parallel Requests</Typography>
          <Slider
            value={tempConfig.processing?.parallel_requests || 3}
            onChange={(_, value) => handleChange('processing', 'parallel_requests', value)}
            min={1}
            max={10}
            marks
            valueLabelDisplay="auto"
            sx={{ mb: 3 }}
          />

          <Typography gutterBottom>Rate Limit (requests per minute)</Typography>
          <Slider
            value={tempConfig.processing?.rate_limit_rpm || 60}
            onChange={(_, value) => handleChange('processing', 'rate_limit_rpm', value)}
            min={10}
            max={200}
            step={10}
            marks
            valueLabelDisplay="auto"
            sx={{ mb: 3 }}
          />

          <FormControlLabel
            control={
              <Switch
                checked={tempConfig.processing?.enable_cache || false}
                onChange={(e) => handleChange('processing', 'enable_cache', e.target.checked)}
              />
            }
            label="Enable Cache"
          />
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <Typography variant="h6" gutterBottom>
            Cache Configuration
          </Typography>

          <Typography gutterBottom>TTL (hours)</Typography>
          <Slider
            value={tempConfig.cache?.ttl_hours || 24}
            onChange={(_, value) => handleChange('cache', 'ttl_hours', value)}
            min={1}
            max={168}
            marks={[
              { value: 24, label: '1d' },
              { value: 72, label: '3d' },
              { value: 168, label: '1w' },
            ]}
            valueLabelDisplay="auto"
            sx={{ mb: 3 }}
          />

          <Typography gutterBottom>Max Size (MB)</Typography>
          <Slider
            value={tempConfig.cache?.max_size_mb || 100}
            onChange={(_, value) => handleChange('cache', 'max_size_mb', value)}
            min={10}
            max={1000}
            step={10}
            marks
            valueLabelDisplay="auto"
            sx={{ mb: 3 }}
          />

          <Typography gutterBottom>Cleanup Interval (hours)</Typography>
          <Slider
            value={tempConfig.cache?.cleanup_interval_hours || 6}
            onChange={(_, value) => handleChange('cache', 'cleanup_interval_hours', value)}
            min={1}
            max={24}
            marks
            valueLabelDisplay="auto"
          />
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          <Typography variant="h6" gutterBottom>
            Database Configuration
          </Typography>

          <TextField
            fullWidth
            label="Database Path"
            value={tempConfig.database?.path || ''}
            onChange={(e) => handleChange('database', 'path', e.target.value)}
            sx={{ mb: 2 }}
          />

          <FormControlLabel
            control={
              <Switch
                checked={tempConfig.database?.backup_enabled || false}
                onChange={(e) => handleChange('database', 'backup_enabled', e.target.checked)}
              />
            }
            label="Enable Automatic Backups"
            sx={{ mb: 2 }}
          />

          {tempConfig.database?.backup_enabled && (
            <>
              <Typography gutterBottom>Backup Interval (days)</Typography>
              <Slider
                value={tempConfig.database?.backup_interval_days || 7}
                onChange={(_, value) => handleChange('database', 'backup_interval_days', value)}
                min={1}
                max={30}
                marks
                valueLabelDisplay="auto"
              />
            </>
          )}
        </TabPanel>

        <TabPanel value={tabValue} index={4}>
          <Typography variant="h6" gutterBottom>
            Appearance
          </Typography>

          <Box sx={{ mb: 4 }}>
            <Typography gutterBottom>Theme Mode</Typography>
            <ToggleButtonGroup
              value={mode}
              exclusive
              onChange={(e, newMode) => newMode && toggleTheme()}
              sx={{ mb: 2 }}
            >
              <ToggleButton value="light" aria-label="light mode">
                <LightModeIcon sx={{ mr: 1 }} />
                Light
              </ToggleButton>
              <ToggleButton value="dark" aria-label="dark mode">
                <DarkModeIcon sx={{ mr: 1 }} />
                Dark
              </ToggleButton>
            </ToggleButtonGroup>
          </Box>

          <Box sx={{ mb: 4 }}>
            <Typography gutterBottom>Primary Color</Typography>
            <Grid container spacing={2}>
              {['blue', 'green', 'orange', 'red'].map((color) => (
                <Grid item key={color}>
                  <Button
                    variant={primaryColor === color ? 'contained' : 'outlined'}
                    onClick={() => setPrimaryColor(color)}
                    sx={{
                      width: 80,
                      height: 80,
                      backgroundColor: primaryColor === color ? undefined : `${color}.500`,
                      borderColor: `${color}.500`,
                      '&:hover': {
                        backgroundColor: `${color}.600`,
                        borderColor: `${color}.600`,
                      },
                    }}
                  >
                    <PaletteIcon />
                  </Button>
                  <Typography variant="caption" display="block" align="center" sx={{ mt: 1 }}>
                    {color.charAt(0).toUpperCase() + color.slice(1)}
                  </Typography>
                </Grid>
              ))}
            </Grid>
          </Box>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h6" gutterBottom>
            Keyboard Shortcuts
          </Typography>
          <Button
            variant="outlined"
            onClick={() => setShortcutsDialogOpen(true)}
            sx={{ mb: 2 }}
          >
            View Keyboard Shortcuts
          </Button>

          <Typography variant="body2" color="text.secondary">
            Press <Chip label="Shift + ?" size="small" sx={{ height: 20 }} /> to show keyboard shortcuts anytime.
          </Typography>
        </TabPanel>

        <TabPanel value={tabValue} index={5}>
          <Typography variant="h6" gutterBottom>
            Advanced Settings
          </Typography>

          <Alert severity="warning" sx={{ mb: 2 }}>
            <Typography variant="body2">
              These settings are for advanced users only. Incorrect configuration may cause issues.
            </Typography>
          </Alert>

          <FormControlLabel
            control={
              <Switch
                checked={tempConfig.advanced?.debug_mode || false}
                onChange={(e) => handleChange('advanced', 'debug_mode', e.target.checked)}
              />
            }
            label="Debug Mode"
            sx={{ mb: 2 }}
          />

          <FormControlLabel
            control={
              <Switch
                checked={tempConfig.advanced?.telemetry_enabled || true}
                onChange={(e) => handleChange('advanced', 'telemetry_enabled', e.target.checked)}
              />
            }
            label="Enable Telemetry"
            sx={{ mb: 2 }}
          />

          <TextField
            fullWidth
            label="Log Level"
            select
            value={tempConfig.advanced?.log_level || 'info'}
            onChange={(e) => handleChange('advanced', 'log_level', e.target.value)}
            sx={{ mb: 2 }}
          >
            <MenuItem value="debug">Debug</MenuItem>
            <MenuItem value="info">Info</MenuItem>
            <MenuItem value="warning">Warning</MenuItem>
            <MenuItem value="error">Error</MenuItem>
          </TextField>
        </TabPanel>
      </Paper>

      <Dialog
        open={resetDialogOpen}
        onClose={() => setResetDialogOpen(false)}
      >
        <DialogTitle>Reset to Default Settings?</DialogTitle>
        <DialogContent>
          <Typography>
            This will reset all settings to their default values. Your API key will need to be re-entered.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleReset} color="error" variant="contained">
            Reset
          </Button>
        </DialogActions>
      </Dialog>

      <KeyboardShortcutsDialog
        open={shortcutsDialogOpen}
        onClose={() => setShortcutsDialogOpen(false)}
      />
    </Box>
  );
};