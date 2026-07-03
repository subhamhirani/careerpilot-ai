'use client';

import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useApprovalStore } from '@/lib/store';
import { ApprovalCard } from '@/components/approval-card';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { CheckSquare, CheckCircle, XCircle } from 'phosphor-icons/react';
import { toast } from 'sonner';
import type { PaginatedResponse, Approval } from '@/types';

export default function ApprovalsPage() {
  const queryClient = useQueryClient();
  const { approvals, setApprovals, loading, setLoading } = useApprovalStore();
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['approvals'],
    queryFn: () => api.get<PaginatedResponse<Approval>>('/approvals', { status: 'pending' }),
  });

  useEffect(() => {
    if (data) {
      setApprovals(data.data ?? [], data.total);
    }
    setLoading(isLoading);
  }, [data, isLoading, setApprovals, setLoading]);

  const approveMutation = useMutation({
    mutationFn: (id: string) => api.post(`/approvals/${id}/approve`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      toast.success('Application approved successfully');
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Failed to approve');
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) => api.post(`/approvals/${id}/reject`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      toast.success('Application rejected');
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Failed to reject');
    },
  });

  const handleApprove = async (id: string) => {
    setActionLoading(id);
    await approveMutation.mutateAsync(id);
    setActionLoading(null);
  };

  const handleReject = async (id: string) => {
    setActionLoading(id);
    await rejectMutation.mutateAsync(id);
    setActionLoading(null);
  };

  if (loading && approvals.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-64" />
        </div>
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-40 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Approvals</h1>
          <p className="text-muted-foreground mt-1">
            Review and approve or reject applications before submission
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1 text-sm text-muted-foreground">
            <CheckSquare className="h-4 w-4" />
            {approvals.length} pending
          </span>
        </div>
      </div>

      {approvals.length > 0 ? (
        <div className="space-y-4">
          {approvals.map((approval) => (
            <ApprovalCard
              key={approval.id}
              approval={approval}
              onApprove={handleApprove}
              onReject={handleReject}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-16 border rounded-lg bg-card">
          <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-500" />
          <h3 className="text-lg font-medium">All caught up!</h3>
          <p className="text-muted-foreground text-sm mt-1">
            No pending approvals. New applications will appear here for your review.
          </p>
        </div>
      )}

      {(approveMutation.isPending || rejectMutation.isPending) && actionLoading && (
        <div className="fixed inset-0 bg-background/50 flex items-center justify-center z-50">
          <div className="flex items-center gap-2 bg-card border rounded-lg px-4 py-3 shadow-lg">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary" />
            <span className="text-sm">Processing...</span>
          </div>
        </div>
      )}
    </div>
  );
}
