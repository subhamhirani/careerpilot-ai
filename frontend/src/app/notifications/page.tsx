'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useNotificationStore } from '@/lib/notification-store';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
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
  ArrowLeft,
} from 'phosphor-icons/react';

const typeIcons: Record<string, React.ReactNode> = {
  job_match: <Briefcase className="h-4 w-4" />,
  application_update: <FileText className="h-4 w-4" />,
  approval_needed: <AlertCircle className="h-4 w-4" />,
  cover_letter_generated: <Sparkles className="h-4 w-4" />,
  resume_parsed: <FileText className="h-4 w-4" />,
  scraper_complete: <Bot className="h-4 w-4" />,
  system: <Bell className="h-4 w-4" />,
};

const typeLabels: Record<string, string> = {
  job_match: 'Job Match',
  application_update: 'Application',
  approval_needed: 'Approval',
  cover_letter_generated: 'Cover Letter',
  resume_parsed: 'Resume',
  scraper_complete: 'Scraper',
  system: 'System',
};

export default function NotificationsPage() {
  const { notifications, unreadCount, loading, fetchNotifications, markAsRead, markAllAsRead, deleteNotification } =
    useNotificationStore();

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              <Bell className="h-6 w-6" />
              Notifications
            </h1>
            <p className="text-muted-foreground text-sm mt-1">
              {unreadCount > 0 ? `${unreadCount} unread notification${unreadCount > 1 ? 's' : ''}` : 'All caught up!'}
            </p>
          </div>
        </div>
        {unreadCount > 0 && (
          <Button variant="outline" size="sm" onClick={markAllAsRead}>
            <CheckCheck className="h-4 w-4 mr-2" />
            Mark all as read
          </Button>
        )}
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">All Notifications</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-4 space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : notifications.length === 0 ? (
            <div className="py-16 text-center">
              <Bell className="h-12 w-12 mx-auto mb-4 text-muted-foreground/30" />
              <h3 className="text-lg font-medium text-muted-foreground">No notifications</h3>
              <p className="text-sm text-muted-foreground/60 mt-1">
                You&apos;ll be notified here when something happens.
              </p>
            </div>
          ) : (
            <ScrollArea className="max-h-[600px]">
              {notifications.map((n) => (
                <div
                  key={n.id}
                  className={`flex items-start gap-3 px-6 py-4 border-b last:border-0 hover:bg-muted/30 transition-colors ${
                    !n.is_read ? 'bg-primary/5' : ''
                  }`}
                >
                  <div className="mt-0.5 text-muted-foreground shrink-0">
                    {typeIcons[n.type] || <Bell className="h-4 w-4" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <Badge variant="outline" className="text-[10px] h-5 px-1.5">
                        {typeLabels[n.type] || n.type}
                      </Badge>
                      {!n.is_read && <span className="w-2 h-2 rounded-full bg-primary shrink-0" />}
                    </div>
                    <p className={`text-sm font-medium ${!n.is_read ? 'text-foreground' : 'text-muted-foreground'}`}>
                      {n.title}
                    </p>
                    {n.message && (
                      <p className="text-sm text-muted-foreground mt-1">{n.message}</p>
                    )}
                    <p className="text-xs text-muted-foreground/60 mt-1">
                      {new Date(n.created_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    {!n.is_read && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => markAsRead(n.id)}
                        title="Mark as read"
                      >
                        <Check className="h-3.5 w-3.5" />
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-muted-foreground hover:text-red-500"
                      onClick={() => deleteNotification(n.id)}
                      title="Delete"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              ))}
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
