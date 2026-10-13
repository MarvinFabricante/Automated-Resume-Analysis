'use client';

import React, { useEffect, useRef } from 'react';
import { useDispatch } from 'react-redux';
import { logout } from '../../redux/slices/authSlice';
import {
  isTokenExpired,
  getTokenRemainingTimeMs,
  handleSessionExpired,
  clearAllAuthSessions
} from '../../utils/token';

export const SessionTimeoutWatcher: React.FC = () => {
  const dispatch = useDispatch();
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
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

    // Cross-tab synchronization via storage event
    const handleStorageEvent = (event: StorageEvent) => {
      if (event.key === 'auth_logout_broadcast' || event.key === 'token') {
        const currentToken = localStorage.getItem('token');
        if (!currentToken || isTokenExpired(currentToken)) {
          dispatch(logout());
          clearAllAuthSessions();
          if (
            typeof window !== 'undefined' &&
            !window.location.pathname.startsWith('/login') &&
            !window.location.pathname.startsWith('/register') &&
            window.location.pathname !== '/'
          ) {
            window.location.href = '/login?session_expired=1';
          }
        }
      }
    };

    // Custom in-window logout listener
    const handleCustomLogout = () => {
      dispatch(logout());
    };

    window.addEventListener('storage', handleStorageEvent);
    window.addEventListener('auth:logout', handleCustomLogout);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      clearInterval(intervalId);
      window.removeEventListener('storage', handleStorageEvent);
      window.removeEventListener('auth:logout', handleCustomLogout);
    };
  }, [dispatch]);

  return null;
};

export default SessionTimeoutWatcher;
