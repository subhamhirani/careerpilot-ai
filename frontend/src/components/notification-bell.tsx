'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useNotificationStore } from '@/lib/notification-store';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import {
  Bell,
  Check,
  CheckCheck,
  Trash2,
  Briefcase,
  FileText,
  Sparkles,
  Bot,
  AlertCircle,
} from '@phosphor-icons/react';

const typeIcons: Record<string, React.ReactNode> = {
  job_match: <Briefcase className="h-4 w-4" />,
  application_update: <FileText className="h-4 w-4" />,
  approval_needed: <AlertCircle className="h-4 w-4" />,
  cover_letter_generated: <Sparkles className="h-4 w-4" />,
  resume_parsed: <FileText className="h-4 w-4" />,
  scraper_complete: <Bot className="h-4 w-4" />,
  system: <Bell className="h-4 w-4" />,
};

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const { notifications, unreadCount, fetchNotifications, fetchUnreadCount, markAsRead, markAllAsRead, deleteNotification } =
    useNotificationStore();

  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 30000);
    return () => clearInterval(interval);
  }, [fetchUnreadCount]);

  const handleOpen = () => {
    setOpen(!open);
    if (!open) {
      fetchNotifications();
    }
  };

  const handleMarkRead = async (id: string) => {
    await markAsRead(id);
  };

  const handleMarkAllRead = async () => {
    await markAllAsRead();
  };

  const handleDelete = async (id: string) => {
    await deleteNotification(id);
  };

  return (
    <div className="relative">
      <Button variant="ghost" size="icon" className="relative" onClick={handleOpen}>
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] flex items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white px-1">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </Button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-2 w-80 sm:w-96 bg-card border rounded-lg shadow-xl z-50 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b">
              <div className="flex items-center gap-2">
                <Bell className="h-4 w-4" />
                <span className="font-semibold text-sm">Notifications</span>
                {unreadCount > 0 && (
                  <Badge variant="secondary" className="text-xs">
                    {unreadCount} new
                  </Badge>
                )}
              </div>
              <div className="flex items-center gap-1">
                {unreadCount > 0 && (
                  <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={handleMarkAllRead}>
                    <CheckCheck className="h-3.5 w-3.5 mr-1" />
                    Mark all read
                  </Button>
                )}
                <Button variant="ghost" size="sm" className="h-7 text-xs" asChild>
                  <Link href="/notifications" onClick={() => setOpen(false)}>
                    View all
                  </Link>
                </Button>
              </div>
            </div>

            <ScrollArea className="max-h-80">
              {notifications.length === 0 ? (
                <div className="py-8 text-center text-muted-foreground text-sm">
                  No notifications yet
                </div>
              ) : (
                notifications.slice(0, 20).map((n, idx) => (
                  <div key={n.id}>
                    <div
                      className={`flex items-start gap-3 px-4 py-3 hover:bg-muted/50 transition-colors ${
                        !n.is_read ? 'bg-primary/5' : ''
                      }`}
                    >
                      <div className="mt-0.5 text-muted-foreground shrink-0">
                        {typeIcons[n.type] || <Bell className="h-4 w-4" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <p className={`text-sm font-medium ${!n.is_read ? 'text-foreground' : 'text-muted-foreground'}`}>
                            {n.title}
                          </p>
                          {!n.is_read && (
                            <button
                              onClick={() => handleMarkRead(n.id)}
                              className="text-muted-foreground hover:text-foreground shrink-0"
                              title="Mark as read"
                            >
                              <Check className="h-3.5 w-3.5" />
                            </button>
                          )}
                        </div>
                        {n.message && (
                          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{n.message}</p>
                        )}
                        <p className="text-[10px] text-muted-foreground/60 mt-1">
                          {new Date(n.created_at).toLocaleString()}
                        </p>
                      </div>
                      <button
                        onClick={() => handleDelete(n.id)}
                        className="text-muted-foreground hover:text-red-500 shrink-0 opacity-0 group-hover:opacity-100"
                        title="Delete"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                    {idx < Math.min(notifications.length, 20) - 1 && <Separator />}
                  </div>
                ))
              )}
            </ScrollArea>
          </div>
        </>
      )}
    </div>
  );
}
