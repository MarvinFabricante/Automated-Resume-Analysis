'use client';

import React from 'react';
import ProtectedRoute from '../../ProtectedRoutes';

export default function CandidateLayout({ children }: { children: React.ReactNode }) {
  return <ProtectedRoute allowedRole="CANDIDATE">{children}</ProtectedRoute>;
}
