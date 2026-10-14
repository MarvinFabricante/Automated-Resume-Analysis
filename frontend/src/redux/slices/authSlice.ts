import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface AuthState {
  user: string | null;
  role: string;
  profileImageUrl: string | null;
  isAuthenticated: boolean;
}

export interface SetCredentialsPayload {
  user: string;
  role: string;
  profileImageUrl?: string | null;
}

const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
const initialState: AuthState = {
  user: token ? localStorage.getItem('saved_email') : null,
  role: token ? (localStorage.getItem('role') || 'Guest') : 'Guest',
  profileImageUrl: token ? localStorage.getItem('profile_image_url') : null,
  isAuthenticated: !!token,
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setCredentials: (state, action: PayloadAction<SetCredentialsPayload>) => {
      const { user, role, profileImageUrl } = action.payload;
      state.user = user;
      state.role = role;
      state.profileImageUrl = profileImageUrl || null;
      state.isAuthenticated = true;
      
      // Sync with localStorage
      localStorage.setItem('saved_email', user);
      localStorage.setItem('role', role);
      if (profileImageUrl) localStorage.setItem('profile_image_url', profileImageUrl);
    },
    logout: (state) => {
      state.user = null;
      state.role = 'Guest';
      state.profileImageUrl = null;
      state.isAuthenticated = false;
      
      localStorage.removeItem('token');
      localStorage.removeItem('role');
      localStorage.removeItem('user_id');
      localStorage.removeItem('saved_email');
      localStorage.removeItem('fullname');
      localStorage.removeItem('profile_image_url');
    },
    updateProfileImage: (state, action: PayloadAction<string>) => {
      state.profileImageUrl = action.payload;
      localStorage.setItem('profile_image_url', action.payload);
    }
  },
});

export const { setCredentials, logout, updateProfileImage } = authSlice.actions;
export default authSlice.reducer;
