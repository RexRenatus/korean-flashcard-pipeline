import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  IconButton,
  Card,
  CardContent,
  CardActions,
  Grid,
  Chip,
  Stack,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Pagination,
  Tabs,
  Tab,
} from '@mui/material';
import {
  NavigateBefore as PrevIcon,
  NavigateNext as NextIcon,
  Download as ExportIcon,
  Visibility as ViewIcon,
  VisibilityOff as HideIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  Settings as SettingsIcon,
  ViewModule as ViewModuleIcon,
} from '@mui/icons-material';
import { useDispatch, useSelector } from 'react-redux';
import { AppDispatch, RootState } from '@renderer/store';
import { fetchFlashcards } from '@renderer/store/flashcardSlice';
import { BulkExportDialog } from '@renderer/components/export/BulkExportDialog';
import { ExportTemplates } from '@renderer/components/export/ExportTemplates';
import { useKeyboardShortcuts } from '@renderer/hooks/useKeyboardShortcuts';

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
      id={`flashcard-tabpanel-${index}`}
      aria-labelledby={`flashcard-tab-${index}`}
      {...other}
    >
      {value === index && children}
    </div>
  );
};

export const FlashcardViewerEnhanced: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { items, loading } = useSelector((state: RootState) => state.flashcards);
  
  const [tabValue, setTabValue] = useState(0);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterStage, setFilterStage] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [selectedItems, setSelectedItems] = useState<string[]>([]);

  useEffect(() => {
    dispatch(fetchFlashcards());
  }, [dispatch]);

  const filteredItems = items.filter(item => {
    if (filterStatus !== 'all' && item.status !== filterStatus) return false;
    if (filterStage !== 'all' && item.stage !== filterStage) return false;
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      return (
        item.word.toLowerCase().includes(search) ||
        item.definition?.toLowerCase().includes(search) ||
        item.example?.toLowerCase().includes(search)
      );
    }
    return true;
  });

  const currentCard = filteredItems[currentIndex];
  const totalCards = filteredItems.length;

  const handleNext = () => {
    if (currentIndex < totalCards - 1) {
      setCurrentIndex(currentIndex + 1);
      setShowAnswer(false);
    }
  };

  const handlePrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
      setShowAnswer(false);
    }
  };

  const handlePageChange = (_: React.ChangeEvent<unknown>, value: number) => {
    setCurrentIndex(value - 1);
    setShowAnswer(false);
  };

  // Set up keyboard shortcuts
  useKeyboardShortcuts([
    {
      key: 'ArrowLeft',
      description: 'Previous flashcard',
      action: handlePrevious,
    },
    {
      key: 'ArrowRight',
      description: 'Next flashcard',
      action: handleNext,
    },
    {
      key: ' ',
      description: 'Toggle answer',
      action: () => setShowAnswer(!showAnswer),
    },
  ]);

  // Listen for export shortcut
  useEffect(() => {
    const handleExportShortcut = () => setExportDialogOpen(true);
    window.addEventListener('shortcut:export', handleExportShortcut);
    return () => window.removeEventListener('shortcut:export', handleExportShortcut);
  }, []);

  if (loading) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography>Loading flashcards...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4">Flashcards</Typography>
        <Stack direction="row" spacing={2}>
          <Button
            variant="outlined"
            onClick={() => setTabValue(tabValue === 0 ? 1 : 0)}
            startIcon={tabValue === 0 ? <SettingsIcon /> : <ViewModuleIcon />}
          >
            {tabValue === 0 ? 'Manage Templates' : 'View Flashcards'}
          </Button>
          <Button
            variant="contained"
            startIcon={<ExportIcon />}
            onClick={() => setExportDialogOpen(true)}
          >
            Export
          </Button>
        </Stack>
      </Box>

      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
          <Tab label="Flashcards" />
          <Tab label="Export Templates" />
        </Tabs>
      </Paper>

      <TabPanel value={tabValue} index={0}>
        <Paper sx={{ p: 2, mb: 3 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="Search"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                size="small"
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Status</InputLabel>
                <Select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  label="Status"
                >
                  <MenuItem value="all">All</MenuItem>
                  <MenuItem value="pending">Pending</MenuItem>
                  <MenuItem value="processing">Processing</MenuItem>
                  <MenuItem value="completed">Completed</MenuItem>
                  <MenuItem value="failed">Failed</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Stage</InputLabel>
                <Select
                  value={filterStage}
                  onChange={(e) => setFilterStage(e.target.value)}
                  label="Stage"
                >
                  <MenuItem value="all">All</MenuItem>
                  <MenuItem value="stage1">Definition</MenuItem>
                  <MenuItem value="stage2">Nuance</MenuItem>
                  <MenuItem value="both">Both</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </Paper>

        {totalCards === 0 ? (
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <Typography variant="h6" color="text.secondary">
              No flashcards found
            </Typography>
          </Paper>
        ) : (
          <>
            <Card sx={{ maxWidth: 800, mx: 'auto', mb: 3 }}>
              <CardContent sx={{ minHeight: 300, position: 'relative' }}>
                <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
                  {currentCard.tags?.map(tag => (
                    <Chip key={tag} label={tag} size="small" />
                  ))}
                  <Chip
                    label={currentCard.stage}
                    size="small"
                    color={currentCard.stage === 'both' ? 'success' : 'primary'}
                  />
                </Stack>

                <Typography variant="h4" gutterBottom align="center" sx={{ mt: 4 }}>
                  {currentCard.word}
                </Typography>

                {showAnswer && (
                  <Box sx={{ mt: 4 }}>
                    <Typography variant="h6" gutterBottom>
                      Definition:
                    </Typography>
                    <Typography variant="body1" paragraph>
                      {currentCard.definition}
                    </Typography>

                    {currentCard.example && (
                      <>
                        <Typography variant="h6" gutterBottom>
                          Example:
                        </Typography>
                        <Typography variant="body1" paragraph>
                          {currentCard.example}
                        </Typography>
                      </>
                    )}

                    {currentCard.cultural_notes && (
                      <>
                        <Typography variant="h6" gutterBottom>
                          Cultural Notes:
                        </Typography>
                        <Typography variant="body1" paragraph>
                          {currentCard.cultural_notes}
                        </Typography>
                      </>
                    )}

                    {currentCard.usage_notes && (
                      <>
                        <Typography variant="h6" gutterBottom>
                          Usage Notes:
                        </Typography>
                        <Typography variant="body1" paragraph>
                          {currentCard.usage_notes}
                        </Typography>
                      </>
                    )}
                  </Box>
                )}

                <IconButton
                  sx={{ position: 'absolute', top: 16, right: 16 }}
                  onClick={() => {/* TODO: Implement favorite toggle */}}
                >
                  <StarBorderIcon />
                </IconButton>
              </CardContent>
              <CardActions sx={{ justifyContent: 'center', p: 2 }}>
                <Button
                  variant={showAnswer ? 'outlined' : 'contained'}
                  startIcon={showAnswer ? <HideIcon /> : <ViewIcon />}
                  onClick={() => setShowAnswer(!showAnswer)}
                >
                  {showAnswer ? 'Hide Answer' : 'Show Answer'}
                </Button>
              </CardActions>
            </Card>

            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 2 }}>
              <IconButton
                onClick={handlePrevious}
                disabled={currentIndex === 0}
                size="large"
              >
                <PrevIcon />
              </IconButton>
              
              <Pagination
                count={totalCards}
                page={currentIndex + 1}
                onChange={handlePageChange}
                size="small"
                siblingCount={1}
                boundaryCount={1}
              />
              
              <IconButton
                onClick={handleNext}
                disabled={currentIndex === totalCards - 1}
                size="large"
              >
                <NextIcon />
              </IconButton>
            </Box>

            <Typography align="center" sx={{ mt: 2 }} color="text.secondary">
              Card {currentIndex + 1} of {totalCards}
            </Typography>
          </>
        )}
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <ExportTemplates />
      </TabPanel>

      <BulkExportDialog
        open={exportDialogOpen}
        onClose={() => setExportDialogOpen(false)}
        selectedItems={selectedItems}
      />
    </Box>
  );
};