import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';

const PublicRoute: React.FC = () => {
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
  const userRole = (typeof localStorage !== 'undefined' ? (localStorage.getItem('role') || '') : '').toUpperCase();

  if (token && userRole) {
    if (userRole === 'ADMIN') {
      return <Navigate to="/admin/dashboard" replace />;
    } else if (userRole === 'HR') {
      return <Navigate to="/hr/dashboard" replace />;
    } else if (userRole === 'CANDIDATE') {
      return <Navigate to="/candidate/dashboard" replace />;
    } else {
      return <Navigate to="/" replace />;
    }
  }

  return <Outlet />;
};

export default PublicRoute;
