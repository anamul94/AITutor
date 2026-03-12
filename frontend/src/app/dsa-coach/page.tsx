'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function DSACoachRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/dsa-learn');
  }, [router]);

  return null;
}
