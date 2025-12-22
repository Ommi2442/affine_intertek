import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  summary: null,
};

const confidenceSlice = createSlice({
  name: 'confidence',
  initialState,
  reducers: {
    setConfidenceScore(state, action) {
      state.summary = action.payload;
    },
    clearConfidenceScore(state) {
      state.summary = null;
    },
  },
});

export const { setConfidenceScore, clearConfidenceScore } =
  confidenceSlice.actions;

export default confidenceSlice.reducer;
