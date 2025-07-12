import React, { useState, useCallback } from 'react';
import {
  Box,
  Paper,
  Button,
  TextField,
  InputAdornment,
  IconButton,
  Chip,
  Menu,
  MenuItem,
} from '@mui/material';
import {
  Add as AddIcon,
  Upload as UploadIcon,
  Search as SearchIcon,
  FilterList as FilterIcon,
  MoreVert as MoreIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
} from '@mui/icons-material';
import { DataGrid, GridColDef, GridRowSelectionModel } from '@mui/x-data-grid';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '@renderer/store';
import { fetchVocabulary, deleteVocabulary } from '@renderer/store/vocabularySlice';
import { VocabularyUploadDialog } from '@renderer/components/vocabulary/VocabularyUploadDialog';
import { VocabularyEditDialog } from '@renderer/components/vocabulary/VocabularyEditDialog';
import { VocabularyItem } from '@shared/types';

export const VocabularyManager: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { items, total, loading, page, pageSize } = useSelector(
    (state: RootState) => state.vocabulary
  );
  
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRows, setSelectedRows] = useState<GridRowSelectionModel>([]);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<VocabularyItem | null>(null);
  const [filterAnchorEl, setFilterAnchorEl] = useState<null | HTMLElement>(null);
  const [rowMenuAnchorEl, setRowMenuAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedRowId, setSelectedRowId] = useState<number | null>(null);

  React.useEffect(() => {
    dispatch(fetchVocabulary({ page: 1, pageSize: 50 }));
  }, [dispatch]);

  const handleSearch = useCallback(() => {
    dispatch(fetchVocabulary({ page: 1, pageSize, search: searchQuery }));
  }, [dispatch, pageSize, searchQuery]);

  const handlePageChange = (newPage: number) => {
    dispatch(fetchVocabulary({ page: newPage + 1, pageSize, search: searchQuery }));
  };

  const handlePageSizeChange = (newPageSize: number) => {
    dispatch(fetchVocabulary({ page: 1, pageSize: newPageSize, search: searchQuery }));
  };

  const handleDeleteSelected = async () => {
    if (selectedRows.length > 0) {
      const ids = selectedRows.map(id => Number(id));
      await dispatch(deleteVocabulary(ids));
      setSelectedRows([]);
    }
  };

  const handleEditRow = (item: VocabularyItem) => {
    setEditingItem(item);
    setEditDialogOpen(true);
    setRowMenuAnchorEl(null);
  };

  const handleDeleteRow = async (id: number) => {
    await dispatch(deleteVocabulary([id]));
    setRowMenuAnchorEl(null);
  };

  const columns: GridColDef[] = [
    {
      field: 'korean',
      headerName: 'Korean',
      flex: 1,
      minWidth: 150,
    },
    {
      field: 'english',
      headerName: 'English',
      flex: 1,
      minWidth: 150,
    },
    {
      field: 'type',
      headerName: 'Type',
      width: 100,
      renderCell: (params) => (
        params.value ? <Chip label={params.value} size="small" /> : null
      ),
    },
    {
      field: 'difficultyLevel',
      headerName: 'Difficulty',
      width: 100,
      valueGetter: (params) => params.row.difficultyLevel || 'N/A',
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 120,
      renderCell: (params) => {
        const status = params.row.processingStatus || 'pending';
        const color = status === 'completed' ? 'success' : 
                     status === 'processing' ? 'warning' : 
                     status === 'failed' ? 'error' : 'default';
        return <Chip label={status} color={color} size="small" />;
      },
    },
    {
      field: 'actions',
      headerName: '',
      width: 50,
      sortable: false,
      renderCell: (params) => (
        <IconButton
          size="small"
          onClick={(e) => {
            e.stopPropagation();
            setSelectedRowId(params.row.id);
            setRowMenuAnchorEl(e.currentTarget);
          }}
        >
          <MoreIcon />
        </IconButton>
      ),
    },
  ];

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Box>
          <h2>Vocabulary Manager</h2>
          <p>Manage your Korean vocabulary list</p>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<UploadIcon />}
            onClick={() => setUploadDialogOpen(true)}
          >
            Import
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => {
              setEditingItem(null);
              setEditDialogOpen(true);
            }}
          >
            Add Word
          </Button>
        </Box>
      </Box>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
          <TextField
            placeholder="Search vocabulary..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
            sx={{ flexGrow: 1 }}
          />
          <Button
            variant="outlined"
            startIcon={<FilterIcon />}
            onClick={(e) => setFilterAnchorEl(e.currentTarget)}
          >
            Filter
          </Button>
          {selectedRows.length > 0 && (
            <Button
              variant="outlined"
              color="error"
              startIcon={<DeleteIcon />}
              onClick={handleDeleteSelected}
            >
              Delete ({selectedRows.length})
            </Button>
          )}
        </Box>

        <DataGrid
          rows={items}
          columns={columns}
          rowCount={total}
          loading={loading}
          pageSizeOptions={[25, 50, 100]}
          paginationModel={{
            page: page - 1,
            pageSize,
          }}
          onPaginationModelChange={(model) => {
            if (model.page !== page - 1) {
              handlePageChange(model.page);
            }
            if (model.pageSize !== pageSize) {
              handlePageSizeChange(model.pageSize);
            }
          }}
          checkboxSelection
          onRowSelectionModelChange={setSelectedRows}
          rowSelectionModel={selectedRows}
          sx={{ height: 600 }}
        />
      </Paper>

      {/* Upload Dialog */}
      <VocabularyUploadDialog
        open={uploadDialogOpen}
        onClose={() => setUploadDialogOpen(false)}
      />

      {/* Edit Dialog */}
      <VocabularyEditDialog
        open={editDialogOpen}
        item={editingItem}
        onClose={() => {
          setEditDialogOpen(false);
          setEditingItem(null);
        }}
      />

      {/* Filter Menu */}
      <Menu
        anchorEl={filterAnchorEl}
        open={Boolean(filterAnchorEl)}
        onClose={() => setFilterAnchorEl(null)}
      >
        <MenuItem onClick={() => setFilterAnchorEl(null)}>All</MenuItem>
        <MenuItem onClick={() => setFilterAnchorEl(null)}>Pending</MenuItem>
        <MenuItem onClick={() => setFilterAnchorEl(null)}>Processing</MenuItem>
        <MenuItem onClick={() => setFilterAnchorEl(null)}>Completed</MenuItem>
        <MenuItem onClick={() => setFilterAnchorEl(null)}>Failed</MenuItem>
      </Menu>

      {/* Row Actions Menu */}
      <Menu
        anchorEl={rowMenuAnchorEl}
        open={Boolean(rowMenuAnchorEl)}
        onClose={() => setRowMenuAnchorEl(null)}
      >
        <MenuItem onClick={() => {
          const item = items.find(i => i.id === selectedRowId);
          if (item) handleEditRow(item);
        }}>
          <EditIcon sx={{ mr: 1 }} /> Edit
        </MenuItem>
        <MenuItem onClick={() => {
          if (selectedRowId) handleDeleteRow(selectedRowId);
        }}>
          <DeleteIcon sx={{ mr: 1 }} /> Delete
        </MenuItem>
      </Menu>
    </Box>
  );
};