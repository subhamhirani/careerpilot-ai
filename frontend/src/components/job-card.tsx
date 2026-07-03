'use client';

import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { MatchScoreBadge } from '@/components/match-score-badge';
import { MapPin, Building2, Calendar, ExternalLink, Send } from '@phosphor-icons/react';
import type { JobCardProps } from '@/types';

const tierLabels: Record<string, { label: string; variant: 'default' | 'secondary' | 'outline' }> = {
  tier_a: { label: 'Tier A', variant: 'default' },
  tier_b: { label: 'Tier B', variant: 'secondary' },
  tier_c: { label: 'Tier C', variant: 'outline' },
};

const statusLabels: Record<string, string> = {
  new: 'New',
  applied: 'Applied',
  interviewing: 'Interviewing',
  rejected: 'Rejected',
  offer: 'Offer',
  accepted: 'Accepted',
  archived: 'Archived',
};

export function JobCard({ job, onApply, onView }: JobCardProps) {
  const tier = tierLabels[job.tier] || { label: job.tier, variant: 'outline' as const };

  return (
    <Card className="transition-all hover:shadow-md hover:border-primary/20">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-lg truncate">{job.title}</CardTitle>
            <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
              <Building2 className="h-3.5 w-3.5" />
              <span>{job.company}</span>
              <span className="text-border">|</span>
              <MapPin className="h-3.5 w-3.5" />
              <span>{job.location}</span>
            </div>
          </div>
          {job.match_score !== undefined && (
            <MatchScoreBadge score={job.match_score} size="sm" />
          )}
        </div>
      </CardHeader>
      <CardContent className="pb-3">
        <p className="text-sm text-muted-foreground line-clamp-2">{job.description}</p>
        <div className="flex flex-wrap items-center gap-2 mt-3">
          <Badge variant={tier.variant}>{tier.label}</Badge>
          <Badge variant="outline">{statusLabels[job.status] || job.status}</Badge>
          {job.source && (
            <Badge variant="secondary" className="text-xs">
              {job.source}
            </Badge>
          )}
          {job.salary_min && (
            <Badge variant="outline" className="text-xs">
              {job.salary_currency || '$'}{job.salary_min.toLocaleString()}
              {job.salary_max ? ` - ${job.salary_currency || '$'}${job.salary_max.toLocaleString()}` : '+'}
            </Badge>
          )}
        </div>
      </CardContent>
      <CardFooter className="flex items-center justify-between border-t pt-3">
        <div className="flex items-center text-xs text-muted-foreground">
          <Calendar className="h-3 w-3 mr-1" />
          {new Date(job.created_at).toLocaleDateString()}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => onView?.(job.id)}>
            <ExternalLink className="h-3.5 w-3.5 mr-1" />
            View
          </Button>
          {job.status === 'new' && (
            <Button variant="default" size="sm" onClick={() => onApply?.(job.id)}>
              <Send className="h-3.5 w-3.5 mr-1" />
              Apply
            </Button>
          )}
        </div>
      </CardFooter>
    </Card>
  );
}
