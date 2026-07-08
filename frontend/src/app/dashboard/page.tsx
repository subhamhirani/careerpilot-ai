'use client';

import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useDashboardStore } from '@/lib/store';
import { StatsCard } from '@/components/stats-card';
import { MatchScoreBadge } from '@/components/match-score-badge';
import { useProcessStatuses } from '@/lib/hooks/use-process-statuses';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Briefcase,
  Send,
  Clock,
  TrendingUp,
  ArrowRight,
  Bell,
  CheckCircle,
  XCircle,
  Calendar,
  Activity,
  Loader2,
} from '@phosphor-icons/react';
import Link from 'next/link';
import type { DashboardStats, ActivityItem } from '@/types';

function ActivityIcon({ type }: { type: ActivityItem['type'] }) {
  switch (type) {
    case 'job_found':
      return <Briefcase className="h-4 w-4 text-blue-500" />;
    case 'application_submitted':
      return <Send className="h-4 w-4 text-green-500" />;
    case 'approval_granted':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'interview_scheduled':
      return <Calendar className="h-4 w-4 text-purple-500" />;
    case 'rejection':
      return <XCircle className="h-4 w-4 text-red-500" />;
    case 'offer':
      return <TrendingUp className="h-4 w-4 text-yellow-500" />;
    default:
      return <Bell className="h-4 w-4 text-muted-foreground" />;
  }
}

const statusConfig: Record<string, { icon: typeof CheckCircle; color: string; label: string }> = {
  queued: { icon: Clock, color: 'text-yellow-500', label: 'Queued' },
  running: { icon: Loader2, color: 'text-blue-500', label: 'Running' },
  completed: { icon: CheckCircle, color: 'text-green-500', label: 'Completed' },
  failed: { icon: XCircle, color: 'text-red-500', label: 'Failed' },
};

function LiveProcessesCard() {
  const { data: processes } = useProcessStatuses();
  const active = processes?.filter((p) => p.status === 'running' || p.status === 'queued') || [];

  if (!active.length) return null;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Activity className="h-4 w-4 text-primary" />
          Live Processes
        </CardTitle>
        <Button variant="ghost" size="sm" asChild>
          <Link href="/processes">
            View all <ArrowRight className="ml-1 h-3 w-3" />
          </Link>
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        {active.map((proc) => {
          const cfg = statusConfig[proc.status] || statusConfig.queued;
          const Icon = cfg.icon;
          const clampedProgress = Math.min(100, Math.max(0, proc.progress_pct || 0));
          return (
            <div key={proc.id} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium truncate mr-2">{proc.task_name}</span>
                <span className={`text-xs shrink-0 flex items-center gap-1 ${cfg.color}`}>
                  <Icon className={`h-3 w-3 ${proc.status === 'running' ? 'animate-spin' : ''}`} />
                  {cfg.label} ({clampedProgress}%)
                </span>
              </div>
              <Progress value={clampedProgress} className="h-1.5" />
              {proc.current_step && (
                <p className="text-xs text-muted-foreground truncate">{proc.current_step}</p>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { stats, setStats, loading, setLoading } = useDashboardStore();

  const { data, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.get<DashboardStats>('/dashboard/stats'),
  });

  useEffect(() => {
    if (data) {
      setStats(data);
    }
    setLoading(isLoading);
  }, [data, isLoading, setStats, setLoading]);

  if (loading && !stats) {
    return (
      <div className="space-y-6">
        <div>
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-96" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-lg" />
          ))}
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-64 rounded-lg" />
          <Skeleton className="h-64 rounded-lg" />
        </div>
      </div>
    );
  }

  const s = stats;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Your AI-powered job search overview
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="Jobs Found"
          value={s?.total_jobs_found ?? 0}
          description="New jobs this week"
          icon={<Briefcase className="h-4 w-4" />}
          trend={{ direction: 'up', value: '+12%' }}
        />
        <StatsCard
          title="Applications Sent"
          value={s?.total_applications_sent ?? 0}
          description="Total submitted"
          icon={<Send className="h-4 w-4" />}
          trend={{ direction: 'up', value: '+8%' }}
        />
        <StatsCard
          title="Pending Approvals"
          value={s?.pending_approvals ?? 0}
          description="Awaiting review"
          icon={<Clock className="h-4 w-4" />}
          trend={
            (s?.pending_approvals ?? 0) > 0
              ? { direction: 'up', value: 'Needs attention' }
              : { direction: 'neutral', value: 'All clear' }
          }
        />
        <StatsCard
          title="Interview Rate"
          value={s ? `${s.interview_rate}%` : '0%'}
          description="Applications to interviews"
          icon={<TrendingUp className="h-4 w-4" />}
          trend={{ direction: 'up', value: '+5%' }}
        />
      </div>

      {/* Live Processes */}
      <LiveProcessesCard />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Top Matches */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg">Top Matches</CardTitle>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/jobs">
                View all <ArrowRight className="ml-1 h-3 w-3" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent className="space-y-4">
            {s?.top_matches && s.top_matches.length > 0 ? (
              s.top_matches.slice(0, 5).map((job) => (
                <div
                  key={job.id}
                  className="flex items-center justify-between p-3 rounded-lg border hover:bg-accent/50 transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium truncate">{job.title}</p>
                    <p className="text-xs text-muted-foreground truncate">
                      {job.company} — {job.location}
                    </p>
                  </div>
                  <MatchScoreBadge score={job.match_score ?? 0} size="sm" />
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <Briefcase className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No matches found yet</p>
                <p className="text-xs">Configure your search preferences to get started</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg">Recent Activity</CardTitle>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/applications">
                View all <ArrowRight className="ml-1 h-3 w-3" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            {s?.recent_activity && s.recent_activity.length > 0 ? (
              <div className="space-y-4">
                {s.recent_activity.slice(0, 10).map((activity) => (
                  <div key={activity.id} className="flex items-start gap-3">
                    <div className="mt-0.5">
                      <ActivityIcon type={activity.type} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm">{activity.message}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(activity.timestamp).toLocaleString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <Bell className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No recent activity</p>
                <p className="text-xs">Activity will appear as jobs are found and applications processed</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
