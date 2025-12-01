import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  trfData: null,
  loading: false,
  error: null,
};

const generateTrfSlice = createSlice({
  name: 'trf',
  initialState,
  reducers: {
    generateTrfRequest: (state) => {
      state.loading = true;
      state.error = null;
    },
    generateTrfSuccess: (state, action) => {
      state.loading = false;
      state.trfData = action.payload;
    },
    generateTrfFailed: (state, action) => {
      state.loading = false;
      state.error = action.payload;
    },
    resetTrf: (state) => {
      state.trfData = null;
      state.error = null;
    },
  },
});

export const {
  generateTrfRequest,
  generateTrfSuccess,
  generateTrfFailed,
  resetTrf,
} = generateTrfSlice.actions;

export default generateTrfSlice.reducer;
