import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';

const getApiBaseUrl = (): string => {
  // If explicitly provided via build args or env (e.g., '/api')
  if (typeof process !== 'undefined' && process.env && process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  if (typeof process !== 'undefined' && process.env && (process.env as any).VITE_API_URL) {
    return (process.env as any).VITE_API_URL;
  }
  // When running in the browser
  if (typeof window !== 'undefined') {
    // Only local dev servers (port 5173 or 3000) connect directly to localhost:8000
    if (window.location.port === '5173' || window.location.port === '3000') {
      return 'http://localhost:8000';
    }
    // In production, docker container (port 8080/80), Cloudflare tunnel, etc.,
    // always use the reverse proxy path '/api' to avoid CORS and mixed-content issues
    return '/api';
  }
  return '/api';
};

export const API_BASE_URL: string = getApiBaseUrl();

const getWsBaseUrl = (): string => {
  if (typeof process !== 'undefined' && process.env && process.env.NEXT_PUBLIC_WS_URL) {
    return process.env.NEXT_PUBLIC_WS_URL;
  }
  if (typeof process !== 'undefined' && process.env && (process.env as any).VITE_WS_URL) {
    return (process.env as any).VITE_WS_URL;
  }
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    if (window.location.port === '5173' || window.location.port === '3000') {
      return 'ws://localhost:8000';
    }
    return `${protocol}//${window.location.host}`;
  }
  return 'ws://localhost:8000';
};

export const WS_BASE_URL: string = getWsBaseUrl();

export const getAssetUrl = (path?: string | null): string => {
  if (!path) return '';
  if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('data:')) {
    return path;
  }
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return normalizedPath;
};

import { isTokenExpired, handleSessionExpired } from '../utils/token';

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
});

// Automatically attach Authorization Bearer token for all outgoing axios requests
// and enforce strict 1-hour expiration
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (typeof localStorage !== 'undefined') {
      const token = localStorage.getItem('token');
      if (token) {
        if (isTokenExpired(token)) {
          handleSessionExpired();
          return Promise.reject(new axios.Cancel('Session expired: 1-hour expiration limit reached.'));
        }
        if (!config.headers.Authorization) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: automatically log out accounts if 401 is received
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      const url = error.config?.url || '';
      // Don't auto-logout on password change, set-password, or login validation
      if (!url.includes('/auth/login') && !url.includes('/auth/change-password') && !url.includes('/auth/set-password')) {
        if (typeof localStorage !== 'undefined' && localStorage.getItem('token')) {
          handleSessionExpired();
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;
