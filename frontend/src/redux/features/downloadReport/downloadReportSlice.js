// src/redux/slice/downloadReportSlice.js
import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  loading: false,
  error: null,
};

const downloadReportSlice = createSlice({
  name: 'downloadReport',
  initialState,
  reducers: {
    downloadReportRequest: (state) => {
      state.loading = true;
      state.error = null;
    },
    downloadReportSuccess: (state) => {
      state.loading = false;
    },
    downloadReportFailed: (state, action) => {
      state.loading = false;
      state.error = action.payload;
    },
  },
});

export const {
  downloadReportRequest,
  downloadReportSuccess,
  downloadReportFailed,
} = downloadReportSlice.actions;

export default downloadReportSlice.reducer;
