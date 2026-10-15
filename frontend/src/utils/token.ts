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

export interface AuthBroadcastPayload {
  type: 'LOGIN' | 'LOGOUT';
  userId?: number;
  email?: string;
  role?: string;
  timestamp: number;
}

export const broadcastAuthLogin = (
  userId?: number | string | null,
  email?: string | null,
  role?: string | null
): void => {
  if (typeof window === 'undefined') return;
  const parsedId = userId ? Number(userId) : undefined;
  const payload: AuthBroadcastPayload = {
    type: 'LOGIN',
    userId: parsedId && !isNaN(parsedId) ? parsedId : undefined,
    email: (email || '').trim().toLowerCase(),
    role: (role || '').toUpperCase(),
    timestamp: Date.now(),
  };
  try {
    if ('BroadcastChannel' in window) {
      const channel = new BroadcastChannel('mariwasa_auth_channel');
      channel.postMessage(payload);
      channel.close();
    }
  } catch (e) {
    // BroadcastChannel unsupported or blocked
  }
  try {
    localStorage.setItem('auth_login_broadcast', JSON.stringify(payload));
  } catch (e) {
    // localStorage quota or private mode
  }
};

export const broadcastAuthLogout = (): void => {
  if (typeof window === 'undefined') return;
  const payload: AuthBroadcastPayload = {
    type: 'LOGOUT',
    timestamp: Date.now(),
  };
  try {
    if ('BroadcastChannel' in window) {
      const channel = new BroadcastChannel('mariwasa_auth_channel');
      channel.postMessage(payload);
      channel.close();
    }
  } catch (e) {
    // ignore
  }
  try {
    localStorage.setItem('auth_logout_broadcast', Date.now().toString());
    window.dispatchEvent(new CustomEvent('auth:logout'));
  } catch (e) {
    // ignore
  }
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
    // Notify other windows/tabs to log out immediately
    broadcastAuthLogout();
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

export const handleSessionSwitched = (): void => {
  if (typeof window !== 'undefined') {
    const currentPath = window.location.pathname;
    if (!currentPath.startsWith('/login')) {
      window.location.href = '/login?session_switched=1';
    }
  }
};
