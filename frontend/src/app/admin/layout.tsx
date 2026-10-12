'use client';

import React from 'react';
import ProtectedRoute from '../../ProtectedRoutes';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return <ProtectedRoute allowedRole="ADMIN">{children}</ProtectedRoute>;
}
