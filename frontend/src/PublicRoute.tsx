'use client';

import React, { useEffect, useState } from 'react';
import { useNavigate, Outlet } from './utils/navigation';
import { isTokenExpired, clearAllAuthSessions } from './utils/token';

interface PublicRouteProps {
  children?: React.ReactNode;
}

const PublicRoute: React.FC<PublicRouteProps> = ({ children }) => {
  const navigate = useNavigate();
  const [canRender, setCanRender] = useState<boolean | null>(null);

  useEffect(() => {
    const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
    const userRole = (typeof localStorage !== 'undefined' ? (localStorage.getItem('role') || '') : '').toUpperCase();

    if (token && isTokenExpired(token)) {
      clearAllAuthSessions();
      setCanRender(true);
      return;
    }

    if (token && userRole) {
      if (userRole === 'ADMIN') {
        navigate('/admin/dashboard', { replace: true });
      } else if (userRole === 'HR') {
        navigate('/hr/dashboard', { replace: true });
      } else if (userRole === 'CANDIDATE') {
        navigate('/candidate/dashboard', { replace: true });
      } else {
        navigate('/', { replace: true });
      }
      setCanRender(false);
      return;
    }

    setCanRender(true);
  }, [navigate]);

  if (canRender === null) {
    return null;
  }

  if (!canRender) {
    return null;
  }

  return children ? <>{children}</> : <Outlet />;
};

export default PublicRoute;
