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
    const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
    const userRole = typeof localStorage !== 'undefined' ? localStorage.getItem('role') : null;

    if (!token || isTokenExpired(token)) {
      handleSessionExpired();
      navigate('/login?session_expired=1', { replace: true });
      setIsAuthorized(false);
      return;
    }

    if (allowedRole && (userRole || '').toUpperCase() !== allowedRole.toUpperCase()) {
      navigate('/', { replace: true });
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
