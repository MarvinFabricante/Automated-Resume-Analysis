import { createSlice } from '@reduxjs/toolkit';

export interface ThemeState {
  theme: string;
}

const initialState: ThemeState = {
  theme: 'light',
};

const themeSlice = createSlice({
  name: 'theme',
  initialState,
  reducers: {
    setTheme: (state) => {
      state.theme = 'light';
    },
  },
});

export const { setTheme } = themeSlice.actions;
export default themeSlice.reducer;
