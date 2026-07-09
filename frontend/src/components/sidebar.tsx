'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { useUIStore } from '@/lib/store';
import {
  LayoutDashboard,
  Briefcase,
  CheckSquare,
  Send,
  FileText,
  BarChart3,
  Settings,
  Rocket,
  X,
  Activity,
  Bell,
  UserCircle,
} from '@phosphor-icons/react';

const navItems = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/processes', label: 'Live Processes', icon: Activity },
  { href: '/jobs', label: 'Jobs', icon: Briefcase },
  { href: '/approvals', label: 'Approvals', icon: CheckSquare },
  { href: '/applications', label: 'Applications', icon: Send },
  { href: '/resumes', label: 'Resumes', icon: FileText },
  { href: '/notifications', label: 'Notifications', icon: Bell },
  { href: '/profile', label: 'Profile', icon: UserCircle },
  { href: '/analytics', label: 'Analytics', icon: BarChart3 },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarOpen, setSidebarOpen } = useUIStore();

  return (
    <>
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={cn(
          'fixed top-0 left-0 z-30 h-full w-64 border-r bg-sidebar text-sidebar-foreground transition-transform duration-200 md:relative md:translate-x-0 md:z-auto',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex h-16 items-center justify-between px-4 md:hidden border-b border-sidebar-border">
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
              <Briefcase className="h-4 w-4" />
            </div>
            <span className="font-bold tracking-tight">CareerPilot AI</span>
          </Link>
          <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(false)}>
            <X className="h-5 w-5" />
          </Button>
        </div>

        <div className="hidden md:flex h-16 items-center px-4 border-b border-sidebar-border">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm transition-transform duration-200 group-hover:scale-105">
              <Briefcase className="h-4 w-4" />
            </div>
            <span className="font-bold text-lg tracking-tight">CareerPilot AI</span>
          </Link>
        </div>

        <ScrollArea className="flex-1 py-3">
          <nav className="space-y-1 px-3">
            {navItems.map((item) => {
              const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-150',
                    isActive
                      ? 'bg-sidebar-accent text-sidebar-accent-foreground font-semibold shadow-sm'
                      : 'text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground hover:translate-x-0.5'
                  )}
                >
                  <item.icon className={cn('h-4 w-4 shrink-0', isActive && 'text-primary')} />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <Separator className="my-4 mx-3 w-auto" />

          <div className="px-3">
            <div className="rounded-xl border border-sidebar-border bg-sidebar-accent/40 p-3.5 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold tracking-tight">AI Matching Engine</span>
                <span className="inline-flex items-center rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
                  Active
                </span>
              </div>
              <p className="text-xs text-sidebar-foreground/60 leading-relaxed">
                Autonomous multi-source scrapers and vector match engine running.
              </p>
            </div>
          </div>
        </ScrollArea>
      </aside>
    </>
  );
}
