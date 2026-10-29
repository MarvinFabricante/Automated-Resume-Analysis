'use client';

import React, { useEffect, useState } from 'react';
import { useNavigate, Outlet } from './utils/navigation';
import { isTokenExpired, handleSessionExpired } from './utils/token';

interface ProtectedRouteProps {
  allowedRole?: string;
  children?: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ allowedRole, children }) => {
  const navigate = useNavigate();
  const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);

  useEffect(() => {
    // If user voluntarily logged out from any dashboard or portal, redirect to homepage immediately
    if (typeof window !== 'undefined') {
      const isVoluntary = sessionStorage.getItem('voluntary_logout');
      if (isVoluntary) {
        sessionStorage.removeItem('voluntary_logout');
        window.location.href = '/';
        return;
      }
    }

    const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
    const userRole = typeof localStorage !== 'undefined' ? localStorage.getItem('role') : null;

    // Genuine session expiration: token exists in storage but is past the 1-hour expiration time
    if (token && isTokenExpired(token)) {
      handleSessionExpired();
      setIsAuthorized(false);
      return;
    }

    // Unauthenticated access (e.g. guest or post-logout without token)
    if (!token) {
      navigate('/login', { replace: true });
      setIsAuthorized(false);
      return;
    }

    if (allowedRole && (userRole || '').toUpperCase() !== allowedRole.toUpperCase()) {
      // Role mismatch caused by another account logging in on another window
      navigate('/login?session_switched=1', { replace: true });
      setIsAuthorized(false);
      return;
    }

    setIsAuthorized(true);
  }, [allowedRole, navigate]);

  if (isAuthorized === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-8 h-8 border-4 border-[#D60041] border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!isAuthorized) {
    return null;
  }

  return children ? <>{children}</> : <Outlet />;
};

export default ProtectedRoute;
