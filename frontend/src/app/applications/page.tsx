'use client';

import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useApplicationStore } from '@/lib/store';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { MatchScoreBadge } from '@/components/match-score-badge';
import { Send, Clock, CheckCircle, XCircle, AlertCircle, Building2, MapPin, FileText } from 'lucide-react';
import type { PaginatedResponse, Application } from '@/types';

const statusConfig: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'warning' | 'outline' | 'success' | 'info'; icon: typeof Send }> = {
  pending_approval: { label: 'Pending Approval', variant: 'warning', icon: Clock },
  approved: { label: 'Approved', variant: 'success', icon: CheckCircle },
  rejected: { label: 'Rejected', variant: 'destructive', icon: XCircle },
  submitted: { label: 'Submitted', variant: 'info', icon: Send },
  error: { label: 'Error', variant: 'destructive', icon: AlertCircle },
};

export default function ApplicationsPage() {
  const { applications, setApplications, loading, setLoading } = useApplicationStore();

  const { data, isLoading } = useQuery({
    queryKey: ['applications'],
    queryFn: () => api.get<PaginatedResponse<Application>>('/applications'),
  });

  useEffect(() => {
    if (data) {
      setApplications(data.data ?? [], data.total);
    }
    setLoading(isLoading);
  }, [data, isLoading, setApplications, setLoading]);

  if (loading && applications.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-64" />
        </div>
        <div className="space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Applications</h1>
        <p className="text-muted-foreground mt-1">
          Track the status of all submitted and pending applications
        </p>
      </div>

      {applications.length > 0 ? (
        <div className="space-y-4">
          {applications.map((app) => {
            const config = statusConfig[app.status] || statusConfig.pending_approval;
            const StatusIcon = config.icon;
            const job = app.job;

            return (
              <Card key={app.id} className="transition-all hover:shadow-md">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <CardTitle className="text-base truncate">
                        {job?.title || 'Unknown Position'}
                      </CardTitle>
                      <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
                        <Building2 className="h-3.5 w-3.5" />
                        <span>{job?.company || 'Unknown'}</span>
                        <span className="text-border">|</span>
                        <MapPin className="h-3.5 w-3.5" />
                        <span>{job?.location || 'Unknown'}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {app.match_score !== undefined && (
                        <MatchScoreBadge score={app.match_score} size="sm" />
                      )}
                      <Badge variant={config.variant as any}>
                        <StatusIcon className="h-3 w-3 mr-1" />
                        {config.label}
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">Source</span>
                      <p className="font-medium">{job?.source || 'N/A'}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Tier</span>
                      <p className="font-medium capitalize">{(job?.tier || '').replace('_', ' ')}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Submitted</span>
                      <p className="font-medium">
                        {app.submitted_at
                          ? new Date(app.submitted_at).toLocaleDateString()
                          : 'Not yet'}
                      </p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Resume</span>
                      <p className="font-medium truncate flex items-center gap-1">
                        <FileText className="h-3 w-3" />
                        {app.resume?.name || 'N/A'}
                      </p>
                    </div>
                  </div>
                  {app.error_message && (
                    <div className="mt-3 p-2 bg-red-50 dark:bg-red-950 rounded text-xs text-red-600 dark:text-red-400">
                      Error: {app.error_message}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <div className="text-center py-16 border rounded-lg bg-card">
          <Send className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
          <h3 className="text-lg font-medium">No applications yet</h3>
          <p className="text-muted-foreground text-sm mt-1">
            Start by finding a job and submitting an application.
          </p>
        </div>
      )}
    </div>
  );
}
