'use client';

import React, { Suspense } from 'react';
import PublicRoute from '../../PublicRoute';
import ResetPassword from '../../views/publicPages/authenticationPages/ResetPassword';

export default function ResetPasswordPage() {
  return (
    <PublicRoute>
      <Suspense
        fallback={
          <div className="min-h-screen flex items-center justify-center bg-[#F0F4F9]">
            <div className="w-8 h-8 border-4 border-[#D60041] border-t-transparent rounded-full animate-spin"></div>
          </div>
        }
      >
        <ResetPassword />
      </Suspense>
    </PublicRoute>
  );
}
