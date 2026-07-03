'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { TrendingUp, TrendingDown, Minus } from '@phosphor-icons/react';
import type { StatsCardProps } from '@/types';

export function StatsCard({ title, value, description, icon, trend }: StatsCardProps) {
  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        {icon && <div className="h-4 w-4 text-muted-foreground">{icon}</div>}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <div className="flex items-center gap-2 mt-1">
          {description && (
            <p className="text-xs text-muted-foreground">{description}</p>
          )}
          {trend && (
            <span
              className={cn(
                'inline-flex items-center text-xs font-medium',
                trend.direction === 'up' && 'text-green-600 dark:text-green-400',
                trend.direction === 'down' && 'text-red-600 dark:text-red-400',
                trend.direction === 'neutral' && 'text-muted-foreground'
              )}
            >
              {trend.direction === 'up' && <TrendingUp className="h-3 w-3 mr-1" />}
              {trend.direction === 'down' && <TrendingDown className="h-3 w-3 mr-1" />}
              {trend.direction === 'neutral' && <Minus className="h-3 w-3 mr-1" />}
              {trend.value}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
