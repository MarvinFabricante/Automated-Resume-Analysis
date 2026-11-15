import { createSlice } from '@reduxjs/toolkit';

export interface UIState {
  isSidebarOpen: boolean;
}

const getInitialSidebarState = (): boolean => {
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem('sidebar_expanded');
    if (saved !== null) {
      return saved === 'true';
    }
  }
  // Default to expanded for all new sessions / new users on desktop and tablet
  return true;
};

const initialState: UIState = {
  isSidebarOpen: getInitialSidebarState(),
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    toggleSidebar: (state) => {
      state.isSidebarOpen = !state.isSidebarOpen;
      if (typeof window !== 'undefined') {
        localStorage.setItem('sidebar_expanded', String(state.isSidebarOpen));
      }
    },
    openSidebar: (state) => {
      state.isSidebarOpen = true;
      if (typeof window !== 'undefined') {
        localStorage.setItem('sidebar_expanded', 'true');
      }
    },
    closeSidebar: (state) => {
      state.isSidebarOpen = false;
      if (typeof window !== 'undefined') {
        localStorage.setItem('sidebar_expanded', 'false');
      }
    },
  },
});

export const { toggleSidebar, openSidebar, closeSidebar } = uiSlice.actions;
export default uiSlice.reducer;
