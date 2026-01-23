import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  projects: [],
  loading: false,
  error: null,
};

const finaliseLetterReportSlice = createSlice({
  name: 'finaliseLetterReport',
  initialState,
  reducers: {
    finaliseLetterReportRequest: (state, action) => {
      state.loading = true;
      state.error = null;
    },
    finaliseLetterReportSuccess: (state, action) => {
      state.loading = false;
      state.projects = action.payload;
    },
    finaliseLetterReportFailed: (state, action) => {
      state.loading = false;
      state.error = action.payload;
    },
  },
});

export const {
  finaliseLetterReportRequest,
  finaliseLetterReportSuccess,
  finaliseLetterReportFailed,
} = finaliseLetterReportSlice.actions;

export default finaliseLetterReportSlice.reducer;
