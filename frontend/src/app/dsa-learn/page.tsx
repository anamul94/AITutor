'use client';

import { Suspense } from 'react';
import DSAModeChat from '@/components/dsa/DSAModeChat';

export default function DSALearnPage() {
  return (
    <Suspense>
      <DSAModeChat mode="learn_topic" />
    </Suspense>
  );
}
