'use client';

import React, { useEffect } from 'react';
import { Provider } from 'react-redux';
import { HelmetProvider } from 'react-helmet-async';
import { Toaster } from 'react-hot-toast';
import { store } from '../redux/store';
import { NavigationProvider } from '../utils/navigation';
import ScrollToTop from '../components/layout/ScrollToTop';
import ErrorBoundary from '../components/common/ErrorBoundary';
import SessionTimeoutWatcher from '../components/common/SessionTimeoutWatcher';

export default function Providers({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const root = window.document.documentElement;
      root.classList.remove('dark');
      root.classList.add('light');
      try {
        localStorage.removeItem('theme');
      } catch {
        // ignore
      }
    }
  }, []);

  return (
    <ErrorBoundary>
      <HelmetProvider>
        <Provider store={store}>
          <SessionTimeoutWatcher />
          <NavigationProvider>
            <ScrollToTop />
            {children}
            <Toaster position="top-right" />
          </NavigationProvider>
        </Provider>
      </HelmetProvider>
    </ErrorBoundary>
  );
}
