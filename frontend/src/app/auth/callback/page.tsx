'use client';

import React, { Suspense } from 'react';
import GoogleCallback from '../../../views/publicPages/authenticationPages/GoogleCallback';

export default function GoogleCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="w-8 h-8 border-4 border-[#D60041] border-t-transparent rounded-full animate-spin"></div>
        </div>
      }
    >
      <GoogleCallback />
    </Suspense>
  );
}
