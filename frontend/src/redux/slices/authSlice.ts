import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface AuthState {
  user: string | null;
  role: string;
  userId: number | null;
  profileImageUrl: string | null;
  isAuthenticated: boolean;
}

export interface SetCredentialsPayload {
  user: string;
  role: string;
  userId?: number | null;
  profileImageUrl?: string | null;
}

const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
const rawUserId = token && typeof localStorage !== 'undefined' ? localStorage.getItem('user_id') : null;

const initialState: AuthState = {
  user: token ? localStorage.getItem('saved_email') : null,
  role: token ? (localStorage.getItem('role') || 'Guest') : 'Guest',
  userId: rawUserId ? parseInt(rawUserId, 10) : null,
  profileImageUrl: token ? localStorage.getItem('profile_image_url') : null,
  isAuthenticated: !!token,
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setCredentials: (state, action: PayloadAction<SetCredentialsPayload>) => {
      const { user, role, userId, profileImageUrl } = action.payload;
      state.user = user;
      state.role = role;
      if (userId !== undefined) state.userId = userId;
      state.profileImageUrl = profileImageUrl || null;
      state.isAuthenticated = true;
      
      // Sync with localStorage
      localStorage.setItem('saved_email', user);
      localStorage.setItem('role', role);
      if (userId !== undefined && userId !== null) {
        localStorage.setItem('user_id', userId.toString());
      }
      if (profileImageUrl) localStorage.setItem('profile_image_url', profileImageUrl);
    },
    resetAuthState: (state) => {
      // Clears in-memory auth state for this window without wiping localStorage
      state.user = null;
      state.role = 'Guest';
      state.userId = null;
      state.profileImageUrl = null;
      state.isAuthenticated = false;
    },
    logout: (state) => {
      state.user = null;
      state.role = 'Guest';
      state.userId = null;
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

export const { setCredentials, resetAuthState, logout, updateProfileImage } = authSlice.actions;
export default authSlice.reducer;
