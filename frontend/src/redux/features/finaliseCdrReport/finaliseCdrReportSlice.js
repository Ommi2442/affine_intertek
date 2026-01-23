import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  projects: [],
  loading: false,
  error: null,
};

const finaliseCdrReportSlice = createSlice({
  name: 'finaliseCdrReport',
  initialState,
  reducers: {
    finaliseCdrReportRequest: (state, action) => {
      state.loading = true;
      state.error = null;
    },
    finaliseCdrReportSuccess: (state, action) => {
      state.loading = false;
      state.projects = action.payload;
    },
    finaliseCdrReportFailed: (state, action) => {
      state.loading = false;
      state.error = action.payload;
    },
  },
});

export const {
  finaliseCdrReportRequest,
  finaliseCdrReportSuccess,
  finaliseCdrReportFailed,
} = finaliseCdrReportSlice.actions;

export default finaliseCdrReportSlice.reducer;
