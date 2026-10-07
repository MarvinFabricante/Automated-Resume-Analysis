import { Navigate, Outlet } from 'react-router-dom';

const PublicRoute = () => {
  const token = localStorage.getItem('token');
  const userRole = (localStorage.getItem('role') || '').toUpperCase();

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
