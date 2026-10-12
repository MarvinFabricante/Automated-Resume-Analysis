'use client';

import PublicRoute from '../../PublicRoute';
import Register from '../../views/publicPages/authenticationPages/Register';

export default function RegisterPage() {
  return (
    <PublicRoute>
      <Register />
    </PublicRoute>
  );
}
