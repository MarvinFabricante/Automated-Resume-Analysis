import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';

interface ProtectedRouteProps {
  allowedRole?: string;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ allowedRole }) => {
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
  const userRole = typeof localStorage !== 'undefined' ? localStorage.getItem('role') : null;

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRole && (userRole || '').toUpperCase() !== allowedRole.toUpperCase()) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
};

export default ProtectedRoute;
