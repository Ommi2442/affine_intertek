import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  projects: [],
  loading: false,
  error: null,
};

const createProjectSlice = createSlice({
  name: 'projectData',
  initialState,
  reducers: {
    createProjectsRequest: (state) => {
      state.loading = true;
      state.error = null;
    },
    createProjectsSuccess: (state, action) => {
      state.loading = false;
      state.projects = action.payload;
    },
    createProjectsFailed: (state, action) => {
      state.loading = false;
      state.error = action.payload;
    },
  },
});

export const {
  createProjectsRequest,
  createProjectsSuccess,
  createProjectsFailed,
} = createProjectSlice.actions;

export default createProjectSlice.reducer;
