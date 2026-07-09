'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { TrendingUp, TrendingDown, Minus } from '@phosphor-icons/react';
import type { StatsCardProps } from '@/types';

export function StatsCard({ title, value, description, icon, trend }: StatsCardProps) {
  return (
    <Card className="transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md hover:border-primary/25">
      <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        {icon && (
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary dark:bg-primary/15">
            {icon}
          </div>
        )}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold tracking-tight text-foreground">{value}</div>
        <div className="flex items-center gap-2 mt-1.5">
          {description && (
            <p className="text-xs text-muted-foreground">{description}</p>
          )}
          {trend && (
            <span
              className={cn(
                'inline-flex items-center text-xs font-semibold px-1.5 py-0.5 rounded-full',
                trend.direction === 'up' && 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
                trend.direction === 'down' && 'bg-red-500/10 text-red-600 dark:text-red-400',
                trend.direction === 'neutral' && 'bg-muted text-muted-foreground'
              )}
            >
              {trend.direction === 'up' && <TrendingUp className="h-3 w-3 mr-1 shrink-0" />}
              {trend.direction === 'down' && <TrendingDown className="h-3 w-3 mr-1 shrink-0" />}
              {trend.direction === 'neutral' && <Minus className="h-3 w-3 mr-1 shrink-0" />}
              {trend.value}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
