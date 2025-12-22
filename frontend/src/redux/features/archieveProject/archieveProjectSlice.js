import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  projects: [],
  loading: false,
  error: null,
};

const archieveProjectSlice = createSlice({
  name: 'projectArchieveData',
  initialState,
  reducers: {
    archieveProjectsRequest: (state, action) => {
      state.loading = true;
      state.error = null;
    },
    archieveProjectsSuccess: (state, action) => {
      state.loading = false;
      state.projects = action.payload;
    },
    archieveProjectsFailed: (state, action) => {
      state.loading = false;
      state.error = action.payload;
    },
  },
});

export const {
  archieveProjectsRequest,
  archieveProjectsSuccess,
  archieveProjectsFailed,
} = archieveProjectSlice.actions;

export default archieveProjectSlice.reducer;
