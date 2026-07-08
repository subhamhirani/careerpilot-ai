'use client';

import { useAuth } from '@/lib/auth-context';
import IntroPage from './intro/page';
import DashboardPage from './dashboard/page';

export default function Home() {
  const { isAuthenticated } = useAuth();

  if (isAuthenticated) {
    return <DashboardPage />;
  }

  return <IntroPage />;
}