import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  letterData: null,
  loading: false,
  error: null,
};

const generateLetterSlice = createSlice({
  name: 'letter',
  initialState,
  reducers: {
    generateLetterRequest: (state) => {
      state.loading = true;
      state.error = null;
    },
    generateLetterSuccess: (state, action) => {
      state.loading = false;
      state.letterData = action.payload;
    },
    generateLetterFailed: (state, action) => {
      state.loading = false;
      state.error = action.payload;
    },
    resetLetter: (state) => {
      state.letterData = null;
      state.error = null;
    },
  },
});

export const {
  generateLetterRequest,
  generateLetterSuccess,
  generateLetterFailed,
  resetLetter,
} = generateLetterSlice.actions;

export default generateLetterSlice.reducer;
