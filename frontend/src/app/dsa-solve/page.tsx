'use client';

import { Suspense } from 'react';
import DSAModeChat from '@/components/dsa/DSAModeChat';

export default function DSASolvePage() {
  return (
    <Suspense>
      <DSAModeChat mode="solve_problem" />
    </Suspense>
  );
}
