'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ProcessStatus } from '@/lib/hooks/use-process-statuses';
import {
  Activity,
  CheckCircle,
  Clock,
  AlertCircle,
  Loader2,
  RefreshCw,
  Cpu,
  FileSearch,
  Briefcase,
  Zap,
  RotateCcw,
} from '@phosphor-icons/react';
import { toast } from 'sonner';

const statusConfig = {
  queued: { icon: Clock, color: 'text-yellow-500', bg: 'bg-yellow-500/10', label: 'Queued' },
  running: { icon: Loader2, color: 'text-blue-500', bg: 'bg-blue-500/10', label: 'Running' },
  completed: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-500/10', label: 'Completed' },
  failed: { icon: AlertCircle, color: 'text-red-500', bg: 'bg-red-500/10', label: 'Failed' },
};

function ProcessCard({ process, onRetry }: { process: ProcessStatus; onRetry?: (id: string) => void }) {
  const config = statusConfig[process.status] || statusConfig.queued;
  const Icon = config.icon;

  return (
    <Card className={`transition-all ${process.status === 'running' ? 'ring-2 ring-blue-500/20' : ''}`}>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-lg ${config.bg}`}>
            <Icon className={`h-4 w-4 ${config.color} ${process.status === 'running' ? 'animate-spin' : ''}`} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-medium truncate">{process.task_name}</p>
              <Badge variant="secondary" className={`text-xs shrink-0 ${config.color}`}>
                {config.label}
              </Badge>
            </div>
            {process.current_step && (
              <p className="text-xs text-muted-foreground mt-1 truncate">
                {process.current_step}
              </p>
            )}
            {process.status === 'running' && (
              <div className="mt-2">
                <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                  <span>Progress</span>
                  <span>{process.progress_pct}%</span>
                </div>
                <Progress value={process.progress_pct} className="h-1.5" />
              </div>
            )}
            {process.error_message && (
              <p className="text-xs text-red-500 mt-1 line-clamp-2">
                {process.error_message}
              </p>
            )}
            <div className="flex items-center justify-between mt-2">
              <p className="text-xs text-muted-foreground">
                {new Date(process.updated_at).toLocaleString()}
              </p>
              {process.status === 'failed' && onRetry && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-xs text-blue-500 hover:text-blue-700"
                  onClick={() => onRetry(process.id)}
                >
                  <RotateCcw className="h-3 w-3 mr-1" />
                  Retry
                </Button>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function ProcessesPage() {
  const queryClient = useQueryClient();
  const { data: processes, isLoading, refetch } = useQuery({
    queryKey: ['process-statuses'],
    queryFn: () => api.get<ProcessStatus[]>('/process-statuses'),
    refetchInterval: 3000, // Poll every 3s for live updates
  });

  const retryMutation = useMutation({
    mutationFn: async (processId: string) => {
      // Find the process to retry
      const process = processes?.find(p => p.id === processId);
      if (!process) throw new Error('Process not found');

      // Delete the failed process status
      await api.delete(`/process-statuses/${processId}`);

      // Re-dispatch based on task name
      if (process.task_name.includes('Resume')) {
        // For resume processing, we need the resume_id and file_path
        // Since we don't have the original params, we'll create a new process status
        // and notify the user
        throw new Error('Resume retry requires re-uploading the file');
      } else if (process.task_name.includes('Job') || process.task_name.includes('Discovery')) {
        // Trigger job discovery
        await api.post('/matches/re-rank');
      } else {
        // Generic retry - just re-trigger
        await api.post('/matches/re-rank');
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['process-statuses'] });
      toast.success('Process retried successfully');
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Failed to retry process');
    },
  });

  const handleRetry = (processId: string) => {
    const process = processes?.find(p => p.id === processId);
    if (process?.task_name.includes('Resume')) {
      toast.error('Resume retry requires re-uploading the file. Please upload the resume again.');
      return;
    }
    retryMutation.mutate(processId);
  };

  const activeProcesses = processes?.filter((p) => p.status === 'running' || p.status === 'queued') || [];
  const failedProcesses = processes?.filter((p) => p.status === 'failed') || [];
  const completedProcesses = processes?.filter((p) => p.status === 'completed') || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Activity className="h-7 w-7 text-primary" />
            Live Processes
          </h1>
          <p className="text-muted-foreground mt-1">
            Real-time tracking of resume processing, job discovery, and matching tasks
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Failed Processes with Retry */}
      {failedProcesses.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-red-500" />
            Failed ({failedProcesses.length})
          </h2>
          <div className="space-y-3">
            {failedProcesses.map((p) => (
              <ProcessCard key={p.id} process={p} onRetry={handleRetry} />
            ))}
          </div>
        </div>
      )}

      {/* Active Processes */}
      <div>
        <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
          <Zap className="h-5 w-5 text-yellow-500" />
          Active ({activeProcesses.length})
        </h2>
        {isLoading && activeProcesses.length === 0 ? (
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <Skeleton key={i} className="h-24 rounded-lg" />
            ))}
          </div>
        ) : activeProcesses.length > 0 ? (
          <div className="space-y-3">
            {activeProcesses.map((p) => (
              <ProcessCard key={p.id} process={p} />
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              <Cpu className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No active processes</p>
              <p className="text-xs mt-1">Upload a resume to start processing</p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Completed / Recent */}
      {completedProcesses.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-green-500" />
            Completed ({completedProcesses.length})
          </h2>
          <div className="space-y-3">
            {completedProcesses.slice(0, 10).map((p) => (
              <ProcessCard key={p.id} process={p} />
            ))}
          </div>
        </div>
      )}

      {/* How it works */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <FileSearch className="h-4 w-4" />
            How Resume Processing Works
          </CardTitle>
          <CardDescription>
            When you upload a resume, CareerPilot automatically:
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { step: '1', title: 'Text Extraction', desc: 'Extract text from PDF/DOCX file', icon: FileSearch },
              { step: '2', title: 'AI Parsing', desc: 'Parse skills, experience, education with Groq LLM', icon: Cpu },
              { step: '3', title: 'Profile Creation', desc: 'Create/update your user profile in the database', icon: Briefcase },
              { step: '4', title: 'Job Matching', desc: 'Match your profile against discovered jobs', icon: Zap },
            ].map((item) => (
              <div key={item.step} className="flex items-start gap-3 p-3 rounded-lg border bg-card">
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 text-primary text-sm font-bold shrink-0">
                  {item.step}
                </div>
                <div>
                  <p className="text-sm font-medium">{item.title}</p>
                  <p className="text-xs text-muted-foreground">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
