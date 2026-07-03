'use client';

import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { CheckCircle, XCircle, Clock, FileText } from 'phosphor-icons/react';
import type { ApprovalCardProps } from '@/types';

export function ApprovalCard({ approval, onApprove, onReject }: ApprovalCardProps) {
  const application = approval.application;
  const job = application?.job;

  return (
    <Card className="transition-all hover:shadow-md">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-base truncate">
              {job?.title || 'Unknown Position'}
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              {job?.company || 'Unknown Company'} — {job?.location || 'Unknown Location'}
            </p>
          </div>
          <Badge variant="warning" className="shrink-0">
            <Clock className="h-3 w-3 mr-1" />
            Pending
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="pb-3">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Match Score</span>
            <p className="font-medium">
              {application?.match_score !== undefined ? `${application.match_score}%` : 'N/A'}
            </p>
          </div>
          <div>
            <span className="text-muted-foreground">Resume</span>
            <p className="font-medium truncate">
              {application?.resume?.name || 'No resume attached'}
            </p>
          </div>
          <div>
            <span className="text-muted-foreground">Source</span>
            <p className="font-medium">{job?.source || 'N/A'}</p>
          </div>
          <div>
            <span className="text-muted-foreground">Tier</span>
            <p className="font-medium capitalize">{(job?.tier || '').replace('_', ' ')}</p>
          </div>
        </div>
        {application?.cover_letter && (
          <div className="mt-3">
            <span className="text-sm text-muted-foreground flex items-center gap-1">
              <FileText className="h-3 w-3" />
              Cover letter included
            </span>
          </div>
        )}
      </CardContent>
      <CardFooter className="flex items-center justify-end gap-2 border-t pt-3">
        <Button
          variant="outline"
          size="sm"
          className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950"
          onClick={() => onReject(approval.id)}
        >
          <XCircle className="h-4 w-4 mr-1" />
          Reject
        </Button>
        <Button
          variant="default"
          size="sm"
          className="bg-green-600 hover:bg-green-700"
          onClick={() => onApprove(approval.id)}
        >
          <CheckCircle className="h-4 w-4 mr-1" />
          Approve
        </Button>
      </CardFooter>
    </Card>
  );
}
