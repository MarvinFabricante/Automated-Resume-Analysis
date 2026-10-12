'use client';

import React, { Suspense } from 'react';
import CompareCandidates from '../../../views/hr/CompareCandidates';

export default function CompareCandidatesPageRoute() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="w-8 h-8 border-4 border-[#D60041] border-t-transparent rounded-full animate-spin"></div>
        </div>
      }
    >
      <CompareCandidates />
    </Suspense>
  );
}
