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
} from 'lucide-react';

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
        <div className="flex h-16 items-center justify-between px-4 md:hidden">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary text-primary-foreground">
              <Rocket className="h-4 w-4" />
            </div>
            <span className="font-bold">CareerPilot</span>
          </Link>
          <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(false)}>
            <X className="h-5 w-5" />
          </Button>
        </div>

        <div className="hidden md:flex h-16 items-center px-4 border-b border-sidebar-border">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary text-primary-foreground">
              <Rocket className="h-4 w-4" />
            </div>
            <span className="font-bold text-lg">CareerPilot</span>
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
                    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                      : 'text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground'
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <Separator className="my-4 mx-3 w-auto" />

          <div className="px-3">
            <div className="rounded-lg bg-sidebar-accent/50 p-3">
              <p className="text-xs font-medium">AI Job Matching</p>
              <p className="text-xs text-sidebar-foreground/60 mt-1">
                Let AI find and apply to the best jobs for you.
              </p>
            </div>
          </div>
        </ScrollArea>
      </aside>
    </>
  );
}
