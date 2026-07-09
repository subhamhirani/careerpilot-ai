'use client';

import { cn } from '@/lib/utils';
import type { MatchScoreBadgeProps } from '@/types';

function getScoreColor(score: number): string {
  if (score >= 80) return 'border border-emerald-200/80 bg-emerald-50 text-emerald-800 dark:border-emerald-800/60 dark:bg-emerald-950/60 dark:text-emerald-300';
  if (score >= 60) return 'border border-blue-200/80 bg-blue-50 text-blue-800 dark:border-blue-800/60 dark:bg-blue-950/60 dark:text-blue-300';
  if (score >= 40) return 'border border-amber-200/80 bg-amber-50 text-amber-800 dark:border-amber-800/60 dark:bg-amber-950/60 dark:text-amber-300';
  return 'border border-red-200/80 bg-red-50 text-red-800 dark:border-red-800/60 dark:bg-red-950/60 dark:text-red-300';
}

function getScoreLabel(score: number): string {
  if (score >= 80) return 'Excellent';
  if (score >= 60) return 'Good';
  if (score >= 40) return 'Fair';
  return 'Low';
}

export function MatchScoreBadge({ score, size = 'md', showLabel = true }: MatchScoreBadgeProps) {
  const sizeClasses = {
    sm: 'text-xs px-1.5 py-0.5',
    md: 'text-sm px-2.5 py-1',
    lg: 'text-base px-3 py-1.5',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full font-medium',
        getScoreColor(score),
        sizeClasses[size]
      )}
    >
      {score}%
      {showLabel && <span className="ml-1 opacity-75">({getScoreLabel(score)})</span>}
    </span>
  );
}
