import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';

interface Flashcard {
  id: number;
  vocabulary_id: number;
  word: string;
  stage: 'stage1' | 'stage2' | 'both';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  definition?: string;
  example?: string;
  pronunciation?: string;
  etymology?: string;
  synonyms?: string[];
  antonyms?: string[];
  part_of_speech?: string;
  cultural_notes?: string;
  usage_notes?: string;
  formality_level?: string;
  tags?: string[];
  created_at: string;
  updated_at: string;
}

interface FlashcardFilters {
  status?: string;
  stage?: string;
  tags?: string[];
  search?: string;
  dateRange?: {
    start: string;
    end: string;
  };
}

interface ExportOptions {
  format: 'json' | 'csv' | 'anki';
  filters?: FlashcardFilters;
  includeFields?: string[];
}

interface FlashcardState {
  items: Flashcard[];
  selectedIds: number[];
  filters: FlashcardFilters;
  loading: boolean;
  exporting: boolean;
  error: string | null;
  totalCount: number;
  currentPage: number;
  pageSize: number;
  favorites: number[];
}

const initialState: FlashcardState = {
  items: [],
  selectedIds: [],
  filters: {},
  loading: false,
  exporting: false,
  error: null,
  totalCount: 0,
  currentPage: 1,
  pageSize: 50,
  favorites: [],
};

// Async thunks
export const fetchFlashcards = createAsyncThunk(
  'flashcards/fetch',
  async (params?: { page?: number; filters?: FlashcardFilters }) => {
    const response = await window.electronAPI.getFlashcards({
      page: params?.page || 1,
      pageSize: 50,
      ...params?.filters,
    });
    return response;
  }
);

export const exportFlashcards = createAsyncThunk(
  'flashcards/export',
  async (options: ExportOptions) => {
    const result = await window.electronAPI.exportFlashcards(options);
    return result;
  }
);

export const deleteFlashcard = createAsyncThunk(
  'flashcards/delete',
  async (id: number) => {
    await window.electronAPI.deleteFlashcard(id);
    return id;
  }
);

export const deleteMultipleFlashcards = createAsyncThunk(
  'flashcards/deleteMultiple',
  async (ids: number[]) => {
    await window.electronAPI.deleteFlashcards(ids);
    return ids;
  }
);

export const regenerateFlashcard = createAsyncThunk(
  'flashcards/regenerate',
  async ({ id, stage }: { id: number; stage: 'stage1' | 'stage2' | 'both' }) => {
    const result = await window.electronAPI.regenerateFlashcard(id, stage);
    return result;
  }
);

export const toggleFavorite = createAsyncThunk(
  'flashcards/toggleFavorite',
  async (id: number) => {
    await window.electronAPI.toggleFavorite('flashcard', id);
    return id;
  }
);

// Slice
const flashcardSlice = createSlice({
  name: 'flashcards',
  initialState,
  reducers: {
    setFilters: (state, action: PayloadAction<FlashcardFilters>) => {
      state.filters = action.payload;
      state.currentPage = 1;
    },
    clearFilters: (state) => {
      state.filters = {};
      state.currentPage = 1;
    },
    setSelectedIds: (state, action: PayloadAction<number[]>) => {
      state.selectedIds = action.payload;
    },
    toggleSelection: (state, action: PayloadAction<number>) => {
      const id = action.payload;
      const index = state.selectedIds.indexOf(id);
      if (index > -1) {
        state.selectedIds.splice(index, 1);
      } else {
        state.selectedIds.push(id);
      }
    },
    selectAll: (state) => {
      state.selectedIds = state.items.map(item => item.id);
    },
    clearSelection: (state) => {
      state.selectedIds = [];
    },
    setPage: (state, action: PayloadAction<number>) => {
      state.currentPage = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // Fetch flashcards
    builder
      .addCase(fetchFlashcards.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchFlashcards.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload.items;
        state.totalCount = action.payload.total;
        state.favorites = action.payload.favorites || [];
      })
      .addCase(fetchFlashcards.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch flashcards';
      });

    // Export flashcards
    builder
      .addCase(exportFlashcards.pending, (state) => {
        state.exporting = true;
        state.error = null;
      })
      .addCase(exportFlashcards.fulfilled, (state) => {
        state.exporting = false;
      })
      .addCase(exportFlashcards.rejected, (state, action) => {
        state.exporting = false;
        state.error = action.error.message || 'Failed to export flashcards';
      });

    // Delete flashcard
    builder
      .addCase(deleteFlashcard.fulfilled, (state, action) => {
        state.items = state.items.filter(item => item.id !== action.payload);
        state.totalCount -= 1;
      });

    // Delete multiple flashcards
    builder
      .addCase(deleteMultipleFlashcards.fulfilled, (state, action) => {
        const deletedIds = new Set(action.payload);
        state.items = state.items.filter(item => !deletedIds.has(item.id));
        state.totalCount -= action.payload.length;
        state.selectedIds = [];
      });

    // Regenerate flashcard
    builder
      .addCase(regenerateFlashcard.pending, (state, action) => {
        const flashcard = state.items.find(item => item.id === action.meta.arg.id);
        if (flashcard) {
          flashcard.status = 'processing';
        }
      })
      .addCase(regenerateFlashcard.fulfilled, (state, action) => {
        const index = state.items.findIndex(item => item.id === action.payload.id);
        if (index !== -1) {
          state.items[index] = action.payload;
        }
      })
      .addCase(regenerateFlashcard.rejected, (state, action) => {
        const flashcard = state.items.find(item => item.id === action.meta.arg.id);
        if (flashcard) {
          flashcard.status = 'failed';
        }
        state.error = action.error.message || 'Failed to regenerate flashcard';
      });

    // Toggle favorite
    builder
      .addCase(toggleFavorite.fulfilled, (state, action) => {
        const id = action.payload;
        const index = state.favorites.indexOf(id);
        if (index > -1) {
          state.favorites.splice(index, 1);
        } else {
          state.favorites.push(id);
        }
      });
  },
});

export const {
  setFilters,
  clearFilters,
  setSelectedIds,
  toggleSelection,
  selectAll,
  clearSelection,
  setPage,
  clearError,
} = flashcardSlice.actions;

export default flashcardSlice.reducer;