'use client';

import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { MatchScoreBadge } from '@/components/match-score-badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import {
  MapPin,
  Building2,
  Calendar,
  ExternalLink,
  Send,
  ArrowLeft,
  Briefcase,
  DollarSign,
  Globe,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';
import type { Job, CoverLetter } from '@/types';

function ScoreBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">{value}%</span>
      </div>
      <div className="h-2 rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}

export default function JobDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [isApplying, setIsApplying] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  const { data: job, isLoading } = useQuery({
    queryKey: ['job', params.id],
    queryFn: () => api.get<Job>(`/jobs/${params.id}`),
  });

  const applyMutation = useMutation({
    mutationFn: () => api.post(`/jobs/${params.id}/apply`),
    onSuccess: () => {
      setIsApplying(false);
      router.push('/applications');
    },
    onError: () => {
      setIsApplying(false);
    },
  });

  const coverLetterMutation = useMutation({
    mutationFn: () => api.post<CoverLetter>('/cover-letters/generate', {
      job_posting_id: params.id,
      tone: 'professional',
    }),
    onSuccess: (data) => {
      setIsGenerating(false);
      toast.success('Cover letter generated!');
      router.push(`/jobs/${params.id}?tab=cover-letter`);
    },
    onError: (err) => {
      setIsGenerating(false);
      toast.error(err instanceof Error ? err.message : 'Failed to generate cover letter');
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-12 w-96" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (!job) {
    return (
      <div className="text-center py-16">
        <Briefcase className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
        <h3 className="text-lg font-medium">Job not found</h3>
        <p className="text-muted-foreground text-sm mt-1">
          This job may have been removed or the link is invalid.
        </p>
        <Button variant="outline" className="mt-4" asChild>
          <Link href="/jobs">Back to Jobs</Link>
        </Button>
      </div>
    );
  }

  const tierLabels: Record<string, string> = {
    tier_a: 'Tier A',
    tier_b: 'Tier B',
    tier_c: 'Tier C',
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Back button */}
      <Button variant="ghost" size="sm" onClick={() => router.back()}>
        <ArrowLeft className="h-4 w-4 mr-2" />
        Back
      </Button>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold">{job.title}</h1>
            {job.match_score !== undefined && (
              <MatchScoreBadge score={job.match_score} size="md" />
            )}
          </div>
          <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <Building2 className="h-3.5 w-3.5" />
              {job.company}
            </span>
            <span className="flex items-center gap-1">
              <MapPin className="h-3.5 w-3.5" />
              {job.location}
            </span>
            {job.salary_min && (
              <span className="flex items-center gap-1">
                <DollarSign className="h-3.5 w-3.5" />
                {job.salary_currency || '$'}{job.salary_min.toLocaleString()}
                {job.salary_max ? ` - ${job.salary_currency || '$'}${job.salary_max.toLocaleString()}` : '+'}
              </span>
            )}
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" />
              {new Date(job.created_at).toLocaleDateString()}
            </span>
          </div>
        </div>
        <div className="flex gap-2 shrink-0">
          {job.url && (
            <Button variant="outline" size="sm" asChild>
              <a href={job.url} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-4 w-4 mr-1" />
                Original Posting
              </a>
            </Button>
          )}
          <Button
            size="sm"
            disabled={job.status !== 'new' || isApplying}
            onClick={() => {
              setIsApplying(true);
              applyMutation.mutate();
            }}
          >
            <Send className="h-4 w-4 mr-1" />
            {isApplying ? 'Applying...' : 'Apply Now'}
          </Button>
        </div>
      </div>

      {/* Tags */}
      <div className="flex flex-wrap gap-2">
        <Badge variant={job.tier === 'tier_a' ? 'default' : job.tier === 'tier_b' ? 'secondary' : 'outline'}>
          {tierLabels[job.tier] || job.tier}
        </Badge>
        <Badge variant="outline">{job.status}</Badge>
        {job.source && (
          <Badge variant="secondary" className="flex items-center gap-1">
            <Globe className="h-3 w-3" />
            {job.source}
          </Badge>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Job Description */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Briefcase className="h-5 w-5" />
                Job Description
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap">
                {job.description}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar: Match Breakdown & Actions */}
        <div className="space-y-6">
          {/* Match Score Breakdown */}
          {job.match_breakdown && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-yellow-500" />
                  Match Breakdown
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <ScoreBar label="Skills" value={job.match_breakdown.skills} color="bg-blue-500" />
                <ScoreBar label="Experience" value={job.match_breakdown.experience} color="bg-green-500" />
                <ScoreBar label="Education" value={job.match_breakdown.education} color="bg-purple-500" />
                <ScoreBar label="Location" value={job.match_breakdown.location} color="bg-orange-500" />
                <ScoreBar label="Salary" value={job.match_breakdown.salary} color="bg-pink-500" />
                <Separator />
                <div className="flex items-center justify-between">
                  <span className="font-medium">Overall</span>
                  <span className="text-lg font-bold">{job.match_breakdown.overall}%</span>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Tailoring Action Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Sparkles className="h-5 w-5" />
                AI Tailoring
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Let AI tailor your resume and cover letter to this specific job description for higher match scores.
              </p>
              <Button className="w-full" variant="secondary" size="sm" asChild>
                <Link href={`/resumes?tailor=${job.id}`}>
                  <Sparkles className="h-4 w-4 mr-1" />
                  Tailor Resume
                </Link>
              </Button>
              <Button
                className="w-full"
                variant="outline"
                size="sm"
                disabled={isGenerating}
                onClick={() => {
                  setIsGenerating(true);
                  coverLetterMutation.mutate();
                }}
              >
                <Sparkles className="h-4 w-4 mr-1" />
                {isGenerating ? 'Generating...' : 'Generate Cover Letter'}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
