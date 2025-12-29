import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  cdrData: null,
  loading: false,
  error: null,
};

const generateCdrSlice = createSlice({
  name: 'cdr',
  initialState,
  reducers: {
    generateCdrRequest: (state) => {
      state.loading = true;
      state.error = null;
    },
    generateCdrSuccess: (state, action) => {
      state.loading = false;
      state.cdrData = action.payload;
    },
    generateCdrFailed: (state, action) => {
      state.loading = false;
      state.error = action.payload;
    },
    resetCdr: (state) => {
      state.cdrData = null;
      state.error = null;
    },
  },
});

export const {
  generateCdrRequest,
  generateCdrSuccess,
  generateCdrFailed,
  resetCdr,
} = generateCdrSlice.actions;

export default generateCdrSlice.reducer;
