/**
 * JWT & Session Token Utilities
 * Enforces strict 1-hour session expiration and multi-account logout.
 */

export interface DecodedToken {
  sub?: string;
  role?: string;
  id?: number;
  exp?: number;
  iat?: number;
  [key: string]: any;
}

export const decodeToken = (token?: string | null): DecodedToken | null => {
  if (!token || typeof token !== 'string') return null;
  try {
    const parts = token.split('.');
    if (parts.length < 2) return null;
    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (e) {
    return null;
  }
};

export const getTokenRemainingTimeMs = (token?: string | null): number => {
  const decoded = decodeToken(token);
  if (!decoded || !decoded.exp) return 0;
  const expMs = decoded.exp * 1000;
  const remaining = expMs - Date.now();
  return remaining > 0 ? remaining : 0;
};

export const isTokenExpired = (token?: string | null): boolean => {
  if (!token) return true;
  const decoded = decodeToken(token);
  if (!decoded || !decoded.exp) return true;
  return Date.now() >= decoded.exp * 1000;
};

export const clearAllAuthSessions = (): void => {
  if (typeof window === 'undefined') return;
  try {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    localStorage.removeItem('user_id');
    localStorage.removeItem('saved_email');
    localStorage.removeItem('fullname');
    localStorage.removeItem('profile_image_url');
    // Notify other tabs to log out immediately
    localStorage.setItem('auth_logout_broadcast', Date.now().toString());
    window.dispatchEvent(new CustomEvent('auth:logout'));
  } catch (e) {
    console.error('Failed to clear local session storage:', e);
  }
};

export const handleSessionExpired = (): void => {
  clearAllAuthSessions();
  if (typeof window !== 'undefined') {
    const currentPath = window.location.pathname;
    // Don't create an infinite redirect loop if already on login or public pages
    if (!currentPath.startsWith('/login')) {
      window.location.href = '/login?session_expired=1';
    }
  }
};
