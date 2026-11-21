import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { NotificationItem } from '../../types';

export interface NotificationState {
  notifications: NotificationItem[];
  unreadCount: number;
  unreadMessagesCount: number;
}

const initialState: NotificationState = {
  notifications: [],
  unreadCount: 0,
  unreadMessagesCount: 0,
};

const notificationSlice = createSlice({
  name: 'notifications',
  initialState,
  reducers: {
    setNotifications: (state, action: PayloadAction<NotificationItem[]>) => {
      state.notifications = action.payload;
      state.unreadCount = action.payload.filter(n => !n.read).length;
    },
    addNotification: (state, action: PayloadAction<NotificationItem>) => {
      const exists = state.notifications.some(n => String(n.id) === String(action.payload.id));
      if (exists) return;
      state.notifications = [action.payload, ...state.notifications];
      state.unreadCount = state.notifications.filter(n => !n.read).length;
    },
    markNotificationRead: (state, action: PayloadAction<number | string>) => {
      const targetId = String(action.payload);
      state.notifications = state.notifications.map(n =>
        String(n.id) === targetId ? { ...n, read: true, is_read: true } : n
      );
      state.unreadCount = state.notifications.filter(n => !n.read).length;
    },
    markAllRead: (state) => {
      state.notifications = state.notifications.map(n => ({ ...n, read: true, is_read: true }));
      state.unreadCount = 0;
    },
    setUnreadMessagesCount: (state, action: PayloadAction<number>) => {
      state.unreadMessagesCount = Math.max(0, action.payload || 0);
    },
    incrementUnreadMessagesCount: (state) => {
      state.unreadMessagesCount += 1;
    },
  },
});

export const {
  setNotifications,
  addNotification,
  markNotificationRead,
  markAllRead,
  setUnreadMessagesCount,
  incrementUnreadMessagesCount,
} = notificationSlice.actions;
export default notificationSlice.reducer;
