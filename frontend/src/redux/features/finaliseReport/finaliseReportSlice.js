import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  projects: [],
  loading: false,
  error: null,
};

const finaliseReportSlice = createSlice({
  name: 'finaliseReport',
  initialState,
  reducers: {
    finaliseReportRequest: (state, action) => {
      state.loading = true;
      state.error = null;
    },
    finaliseReportSuccess: (state, action) => {
      state.loading = false;
      state.projects = action.payload;
    },
    finaliseReportFailed: (state, action) => {
      state.loading = false;
      state.error = action.payload;
    },
  },
});

export const {
  finaliseReportRequest,
  finaliseReportSuccess,
  finaliseReportFailed,
} = finaliseReportSlice.actions;

export default finaliseReportSlice.reducer;
