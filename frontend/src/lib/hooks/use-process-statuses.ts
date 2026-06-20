import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface ProcessStatus {
  id: string;
  user_id: string;
  task_name: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  progress_pct: number;
  current_step?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export function useProcessStatuses(taskName?: string) {
  return useQuery({
    queryKey: ['process-statuses', taskName],
    queryFn: () => api.get<ProcessStatus[]>('/process-statuses', { task_name: taskName }),
    refetchInterval: 5000, // Poll every 5s for live updates
  });
}
