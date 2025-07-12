import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { VocabularyItem } from '@/shared/types';

interface VocabularyState {
  items: VocabularyItem[];
  loading: boolean;
  error: string | null;
  filter: string;
  sort: {
    field: 'createdAt' | 'korean' | 'english' | 'position';
    order: 'asc' | 'desc';
  };
  pagination: {
    page: number;
    pageSize: number;
    total: number;
  };
}

const initialState: VocabularyState = {
  items: [],
  loading: false,
  error: null,
  filter: '',
  sort: { field: 'createdAt', order: 'desc' },
  pagination: { page: 1, pageSize: 50, total: 0 }
};

export const vocabularySlice = createSlice({
  name: 'vocabulary',
  initialState,
  reducers: {
    // Basic CRUD operations
    addVocabularyItem: (state, action: PayloadAction<VocabularyItem>) => {
      state.items.push(action.payload);
      state.pagination.total += 1;
    },
    
    updateVocabularyItem: (state, action: PayloadAction<{ id: number; changes: Partial<VocabularyItem> }>) => {
      const index = state.items.findIndex(item => item.id === action.payload.id);
      if (index !== -1) {
        state.items[index] = { ...state.items[index], ...action.payload.changes };
      }
    },
    
    deleteVocabularyItems: (state, action: PayloadAction<number[]>) => {
      state.items = state.items.filter(item => !action.payload.includes(item.id));
      state.pagination.total = Math.max(0, state.pagination.total - action.payload.length);
    },
    
    // Batch operations
    setVocabularyList: (state, action: PayloadAction<{
      items: VocabularyItem[];
      total?: number;
      page?: number;
      pageSize?: number;
    }>) => {
      state.items = action.payload.items;
      if (action.payload.total !== undefined) {
        state.pagination.total = action.payload.total;
      }
      if (action.payload.page !== undefined) {
        state.pagination.page = action.payload.page;
      }
      if (action.payload.pageSize !== undefined) {
        state.pagination.pageSize = action.payload.pageSize;
      }
    },
    
    // Loading states
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },
    
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    
    // Filter and sort
    setFilter: (state, action: PayloadAction<string>) => {
      state.filter = action.payload;
    },
    
    setSort: (state, action: PayloadAction<{
      field: 'createdAt' | 'korean' | 'english' | 'position';
      order: 'asc' | 'desc';
    }>) => {
      state.sort = action.payload;
    },
    
    // Pagination
    setPagination: (state, action: PayloadAction<Partial<VocabularyState['pagination']>>) => {
      state.pagination = { ...state.pagination, ...action.payload };
    },
    
    // Clear all
    clearVocabulary: (state) => {
      return initialState;
    }
  }
});

export const {
  addVocabularyItem,
  updateVocabularyItem,
  deleteVocabularyItems,
  setVocabularyList,
  setLoading,
  setError,
  setFilter,
  setSort,
  setPagination,
  clearVocabulary
} = vocabularySlice.actions;

export default vocabularySlice.reducer;