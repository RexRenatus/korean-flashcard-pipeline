import { configureStore } from '@reduxjs/toolkit';
import { vocabularySlice } from './vocabularySlice';
import { processingSlice } from './processingSlice';
import { systemSlice } from './systemSlice';
import configReducer from './configSlice';
import flashcardReducer from './flashcardSlice';

export const store = configureStore({
  reducer: {
    vocabulary: vocabularySlice.reducer,
    processing: processingSlice.reducer,
    system: systemSlice.reducer,
    config: configReducer,
    flashcards: flashcardReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these action types
        ignoredActions: ['processing/updateProgress'],
        // Ignore these field paths in all actions
        ignoredActionPaths: ['payload.timestamp'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;