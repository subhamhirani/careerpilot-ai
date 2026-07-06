'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { Header } from '@/components/header';
import { Sidebar } from '@/components/sidebar';

const PUBLIC_PATHS = ['/login', '/register', '/forgot-password', '/intro'];

export function AppShell({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [isClient, setIsClient] = useState(false);

  // Mark as client after mount (runs only in browser)
  useEffect(() => {
    setIsClient(true);
  }, []);

  const isPublicPath = PUBLIC_PATHS.some(
    (p) => pathname === p || pathname.startsWith(p + '/')
  );

  // Redirect unauthenticated users away from protected routes
  useEffect(() => {
    if (isClient && !isAuthenticated && !isPublicPath) {
      router.push('/login');
    }
  }, [isClient, isAuthenticated, isPublicPath, router]);

  // SERVER-SIDE: Before client mount, check auth from context
  // On first SSR render, isAuthenticated is false (no localStorage yet)
  // So we render nothing to prevent shell leak
  if (!isClient && !isAuthenticated && !isPublicPath) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
          <p className="text-sm text-muted-foreground">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  // For public routes, render children directly
  if (isPublicPath) {
    return <>{children}</>;
  }

  // For protected routes on client, redirect if not authenticated
  if (isClient && !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
          <p className="text-sm text-muted-foreground">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  // Authenticated — render the full app shell
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header />
        <main className="flex-1 p-4 md:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
