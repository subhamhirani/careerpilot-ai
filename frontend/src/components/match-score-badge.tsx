'use client';

import { cn } from '@/lib/utils';
import type { MatchScoreBadgeProps } from '@/types';

function getScoreColor(score: number): string {
  if (score >= 80) return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100';
  if (score >= 60) return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100';
  if (score >= 40) return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100';
  return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100';
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
