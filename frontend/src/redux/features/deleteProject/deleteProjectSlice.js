import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  projects: [],
  loading: false,
  error: null,
};

const deleteProjectSlice = createSlice({
  name: 'projectDeleteData',
  initialState,
  reducers: {
    deleteProjectsRequest: (state) => {
      state.loading = true;
      state.error = null;
    },
    deleteProjectsSuccess: (state, action) => {
      state.loading = false;
      state.projects = action.payload;
    },
    deleteProjectsFailed: (state, action) => {
      state.loading = false;
      state.error = action.payload;
    },
  },
});

export const {
  deleteProjectsRequest,
  deleteProjectsSuccess,
  deleteProjectsFailed,
} = deleteProjectSlice.actions;

export default deleteProjectSlice.reducer;
