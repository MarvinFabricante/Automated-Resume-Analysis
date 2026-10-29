'use client';

import React, { useEffect, useRef } from 'react';
import { useDispatch } from 'react-redux';
import { logout, resetAuthState } from '../../redux/slices/authSlice';
import { apiSlice } from '../../redux/api/apiSlice';
import {
  isTokenExpired,
  getTokenRemainingTimeMs,
  handleSessionExpired,
  decodeToken,
  AuthBroadcastPayload,
} from '../../utils/token';

export const SessionTimeoutWatcher: React.FC = () => {
  const dispatch = useDispatch();
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Track the user ID, email, and role that this window instance is operating under
  const activeUserIdRef = useRef<string | null>(
    typeof localStorage !== 'undefined' ? localStorage.getItem('user_id') : null
  );
  const activeUserEmailRef = useRef<string | null>(
    typeof localStorage !== 'undefined' ? localStorage.getItem('saved_email') : null
  );
  const activeUserRoleRef = useRef<string | null>(
    typeof localStorage !== 'undefined' ? localStorage.getItem('role') : null
  );

  useEffect(() => {
    // Helper to get active credentials for this window (from refs, storage, or token)
    const getCurrentWindowUser = () => {
      let uid = activeUserIdRef.current || (typeof localStorage !== 'undefined' ? localStorage.getItem('user_id') : null);
      let email = activeUserEmailRef.current || (typeof localStorage !== 'undefined' ? localStorage.getItem('saved_email') : null);
      let role = activeUserRoleRef.current || (typeof localStorage !== 'undefined' ? localStorage.getItem('role') : null);

      if ((!uid || !email || !role) && typeof localStorage !== 'undefined') {
        const token = localStorage.getItem('token');
        if (token) {
          const decoded = decodeToken(token);
          if (decoded) {
            if (!uid && decoded.id) uid = decoded.id.toString();
            if (!email && decoded.sub) email = decoded.sub;
            if (!role && decoded.role) role = decoded.role;
          }
        }
      }
      return {
        uid: uid ? uid.toString() : null,
        email: (email || '').trim().toLowerCase(),
        role: (role || '').trim().toUpperCase(),
      };
    };

    // Sync current window credentials into refs
    const syncCurrentCredentials = () => {
      const { uid, email, role } = getCurrentWindowUser();
      activeUserIdRef.current = uid;
      activeUserEmailRef.current = email;
      activeUserRoleRef.current = role;
    };

    // Initialize refs with accurate decoded values
    syncCurrentCredentials();

    const checkAndSchedule = () => {
      if (typeof window === 'undefined') return;

      const token = localStorage.getItem('token');
      if (!token) {
        if (timerRef.current) clearTimeout(timerRef.current);
        return;
      }

      // Check if already expired (1 hour limit passed)
      if (isTokenExpired(token)) {
        dispatch(logout());
        handleSessionExpired();
        return;
      }

      // Schedule logout at exact token expiration
      const remainingMs = getTokenRemainingTimeMs(token);
      if (timerRef.current) clearTimeout(timerRef.current);

      if (remainingMs > 0) {
        timerRef.current = setTimeout(() => {
          dispatch(logout());
          handleSessionExpired();
        }, remainingMs);
      } else {
        dispatch(logout());
        handleSessionExpired();
      }
    };

    // Run initial check on mount
    checkAndSchedule();

    // Periodic safety check every 15 seconds
    const intervalId = setInterval(() => {
      checkAndSchedule();
    }, 15000);

    // Handle when another window signs in
    const handleLoginBroadcast = (payload: AuthBroadcastPayload) => {
      const { uid: myUserId, email: myEmail, role: myRole } = getCurrentWindowUser();

      // If this window does NOT have an active session, no need to log out
      const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
      if (!myUserId && !myEmail && !token) {
        return;
      }

      const incomingUserId = payload.userId ? payload.userId.toString() : null;
      const incomingEmail = (payload.email || '').trim().toLowerCase();
      const incomingRole = (payload.role || '').trim().toUpperCase();

      const isDifferentUser =
        (Boolean(myUserId && incomingUserId) && myUserId !== incomingUserId) ||
        (Boolean(myEmail && incomingEmail) && myEmail !== incomingEmail) ||
        (Boolean(myRole && incomingRole) && myRole !== incomingRole);

      if (isDifferentUser) {
        // Another account signed in in another window!
        // Immediately terminate this window's session without overwriting the new user's localStorage
        dispatch(resetAuthState());
        dispatch(apiSlice.util.resetApiState());

        if (typeof window !== 'undefined') {
          const pathname = window.location.pathname;
          if (!pathname.startsWith('/login')) {
            window.location.href = '/login?session_switched=1';
          }
        }
      } else {
        // Same user refreshed session or logged in again
        syncCurrentCredentials();
        checkAndSchedule();
      }
    };

    // Handle when a window initiates logout (redirect other open dashboard tabs to homepage)
    const handleLogoutBroadcast = () => {
      dispatch(resetAuthState());
      dispatch(apiSlice.util.resetApiState());
      if (
        typeof window !== 'undefined' &&
        !window.location.pathname.startsWith('/login') &&
        !window.location.pathname.startsWith('/register') &&
        window.location.pathname !== '/'
      ) {
        window.location.href = '/';
      }
    };

    // 1. BroadcastChannel listener (instant cross-window communication)
    let broadcastChannel: BroadcastChannel | null = null;
    if (typeof window !== 'undefined' && 'BroadcastChannel' in window) {
      try {
        broadcastChannel = new BroadcastChannel('mariwasa_auth_channel');
        broadcastChannel.onmessage = (event) => {
          const data = event.data as AuthBroadcastPayload;
          if (!data || !data.type) return;
          if (data.type === 'LOGIN') {
            handleLoginBroadcast(data);
          } else if (data.type === 'LOGOUT') {
            handleLogoutBroadcast();
          }
        };
      } catch (e) {
        console.debug('BroadcastChannel initialization error:', e);
      }
    }

    // 2. Storage event listener (fallback & cross-tab standard synchronization)
    const handleStorageEvent = (event: StorageEvent) => {
      if (event.key === 'auth_login_broadcast' && event.newValue) {
        try {
          const payload = JSON.parse(event.newValue) as AuthBroadcastPayload;
          handleLoginBroadcast(payload);
        } catch (e) {
          // ignore
        }
      } else if (event.key === 'auth_logout_broadcast') {
        handleLogoutBroadcast();
      } else if (event.key === 'token') {
        if (!event.newValue) {
          handleLogoutBroadcast();
        } else {
          // Check if token changed to another user
          const decoded = decodeToken(event.newValue);
          if (decoded) {
            const incomingId = decoded.id ? decoded.id.toString() : null;
            const incomingEmail = (decoded.sub || '').trim().toLowerCase();
            const incomingRole = (decoded.role || '').trim().toUpperCase();
            const { uid, email, role } = getCurrentWindowUser();

            const isDiff =
              (Boolean(uid && incomingId) && uid !== incomingId) ||
              (Boolean(email && incomingEmail) && email !== incomingEmail) ||
              (Boolean(role && incomingRole) && role !== incomingRole);

            if (isDiff) {
              handleLoginBroadcast({
                type: 'LOGIN',
                userId: decoded.id,
                email: decoded.sub,
                role: decoded.role,
                timestamp: Date.now(),
              });
            } else if (isTokenExpired(event.newValue)) {
              dispatch(logout());
              handleSessionExpired();
            } else {
              syncCurrentCredentials();
              checkAndSchedule();
            }
          }
        }
      }
    };

    // 3. Custom in-window logout listener
    const handleCustomLogout = () => {
      dispatch(resetAuthState());
      dispatch(apiSlice.util.resetApiState());
    };

    window.addEventListener('storage', handleStorageEvent);
    window.addEventListener('auth:logout', handleCustomLogout);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      clearInterval(intervalId);
      if (broadcastChannel) {
        broadcastChannel.close();
      }
      window.removeEventListener('storage', handleStorageEvent);
      window.removeEventListener('auth:logout', handleCustomLogout);
    };
  }, [dispatch]);

  return null;
};

export default SessionTimeoutWatcher;
