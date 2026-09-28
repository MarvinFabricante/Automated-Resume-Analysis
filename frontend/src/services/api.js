import axios from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const getWsBaseUrl = () => {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL;
  }
  if (import.meta.env.VITE_API_URL) {
    try {
      const url = new URL(import.meta.env.VITE_API_URL);
      const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${protocol}//${url.host}`;
    } catch {
      // If VITE_API_URL is a relative path like '/api', derive from window.location
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${protocol}//${window.location.host}`;
    }
  }
  return 'ws://localhost:8000';
};

export const WS_BASE_URL = getWsBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
});

export default api;
