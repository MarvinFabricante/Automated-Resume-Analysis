'use client';

import PublicRoute from '../../PublicRoute';
import Login from '../../views/publicPages/authenticationPages/Login';

export default function LoginPage() {
  return (
    <PublicRoute>
      <Login />
    </PublicRoute>
  );
}
