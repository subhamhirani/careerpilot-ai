import type { Metadata } from 'next';
import { Providers } from '@/components/providers';
import { AppShell } from '@/components/app-shell';
import './globals.css';

export const metadata: Metadata = {
  title: 'CareerPilot AI — Automated Job Application System',
  description: 'AI-powered job search and automated application system. Find, match, and apply to jobs intelligently.',
  keywords: ['jobs', 'career', 'AI', 'job search', 'automation', 'applications'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="font-sans antialiased">
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}