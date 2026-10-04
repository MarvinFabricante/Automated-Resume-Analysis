import axios from 'axios';

const getApiBaseUrl = () => {
  // If explicitly provided via build args or env (e.g., '/api')
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  // When running in the browser
  if (typeof window !== 'undefined') {
    // Only Vite dev server (port 5173) connects directly to localhost:8000
    if (window.location.port === '5173') {
      return 'http://localhost:8000';
    }
    // In production, docker container (port 8080/80), Cloudflare tunnel, etc.,
    // always use the reverse proxy path '/api' to avoid CORS and mixed-content issues
    return '/api';
  }
  return '/api';
};

export const API_BASE_URL = getApiBaseUrl();

const getWsBaseUrl = () => {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL;
  }
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    if (window.location.port === '5173') {
      return 'ws://localhost:8000';
    }
    return `${protocol}//${window.location.host}`;
  }
  return 'ws://localhost:8000';
};

export const WS_BASE_URL = getWsBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
});

// Automatically attach Authorization Bearer token for all outgoing axios requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export default api;
