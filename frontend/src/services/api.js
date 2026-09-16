import axios from 'axios';

const BASE_URL = 'http://localhost:8000';
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
      // fallback
    }
  }
  return 'ws://localhost:8000';
};

export const WS_BASE_URL = getWsBaseUrl();

const api = axios.create({
  baseURL: BASE_URL,
  baseURL: API_BASE_URL,
});

export default api;
