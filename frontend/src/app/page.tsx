'use client';

import PublicRoute from '../PublicRoute';
import LandingPage from '../views/publicPages/site/LandingPage';

export default function HomePage() {
  return (
    <PublicRoute>
      <LandingPage />
    </PublicRoute>
  );
}
