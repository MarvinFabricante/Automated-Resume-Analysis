'use client';

import React from 'react';
import ProtectedRoute from '../../ProtectedRoutes';

export default function HRLayout({ children }: { children: React.ReactNode }) {
  return <ProtectedRoute allowedRole="HR">{children}</ProtectedRoute>;
}
