'use client';

import PublicRoute from '../../PublicRoute';
import ForgotPassword from '../../views/publicPages/authenticationPages/ForgotPassword';

export default function ForgotPasswordPage() {
  return (
    <PublicRoute>
      <ForgotPassword />
    </PublicRoute>
  );
}
