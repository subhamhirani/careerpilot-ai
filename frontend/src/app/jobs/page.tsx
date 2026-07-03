'use client';

import { useEffect, useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useJobStore } from '@/lib/store';
import { JobCard } from '@/components/job-card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Search,
  SlidersHorizontal,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
  Briefcase,
} from 'phosphor-icons/react';
import Link from 'next/link';
import type { PaginatedResponse, Job } from '@/types';

const TIER_OPTIONS = [
  { value: '', label: 'All Tiers' },
  { value: 'tier_a', label: 'Tier A' },
  { value: 'tier_b', label: 'Tier B' },
  { value: 'tier_c', label: 'Tier C' },
];

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'new', label: 'New' },
  { value: 'applied', label: 'Applied' },
  { value: 'interviewing', label: 'Interviewing' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'offer', label: 'Offer' },
  { value: 'archived', label: 'Archived' },
];

export default function JobsPage() {
  const { jobs, filters, loading, total, page, setJobs, setFilter, resetFilters, setLoading, setPage } = useJobStore();
  const [searchInput, setSearchInput] = useState(filters.search);
  const [showFilters, setShowFilters] = useState(false);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['jobs', filters, page],
    queryFn: () =>
      api.get<PaginatedResponse<Job>>('/jobs', {
        ...filters,
        page,
        page_size: 20,
      } as Record<string, string | number | boolean | undefined>),
  });

  useEffect(() => {
    if (data) {
      setJobs(data.data ?? [], data.total);
    }
    setLoading(isLoading);
  }, [data, isLoading, setJobs, setLoading]);

  const handleSearch = useCallback(() => {
    setFilter('search', searchInput);
  }, [searchInput, setFilter]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch();
  };

  const handleView = (jobId: string) => {
    window.location.href = `/jobs/${jobId}`;
  };

  const handleApply = async (jobId: string) => {
    try {
      await api.post(`/jobs/${jobId}/apply`);
      refetch();
    } catch (err) {
      console.error('Failed to apply:', err);
    }
  };

  const totalPages = Math.ceil(total / 20);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Jobs</h1>
          <p className="text-muted-foreground mt-1">
            Browse and apply to matching positions
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
          >
            <SlidersHorizontal className="h-4 w-4 mr-2" />
            Filters
          </Button>
          <Badge variant="secondary" className="text-sm">
            {total} jobs found
          </Badge>
        </div>
      </div>

      {/* Search Bar */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search jobs by title, company, or keyword..."
            className="pl-9"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>
        <Button onClick={handleSearch}>Search</Button>
        {(filters.search || filters.tier || filters.location || filters.status || filters.source) && (
          <Button variant="ghost" size="icon" onClick={resetFilters} title="Reset filters">
            <RotateCcw className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 border rounded-lg bg-card">
          <div className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground">Tier</label>
            <Select value={filters.tier} onValueChange={(v) => setFilter('tier', v)}>
              <SelectTrigger>
                <SelectValue placeholder="All Tiers" />
              </SelectTrigger>
              <SelectContent>
                {TIER_OPTIONS.map((o) => (
                  <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground">Status</label>
            <Select value={filters.status} onValueChange={(v) => setFilter('status', v)}>
              <SelectTrigger>
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((o) => (
                  <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground">Location</label>
            <Input
              placeholder="e.g. Remote, New York"
              value={filters.location}
              onChange={(e) => setFilter('location', e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground">Source</label>
            <Input
              placeholder="e.g. LinkedIn, Indeed"
              value={filters.source}
              onChange={(e) => setFilter('source', e.target.value)}
            />
          </div>
        </div>
      )}

      {/* Job List */}
      {loading ? (
        <div className="space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-48 rounded-lg" />
          ))}
        </div>
      ) : jobs.length > 0 ? (
        <div className="space-y-4">
          {jobs.map((job) => (
            <JobCard
              key={job.id}
              job={job}
              onView={handleView}
              onApply={handleApply}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-16">
          <Briefcase className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
          <h3 className="text-lg font-medium">No jobs found</h3>
          <p className="text-muted-foreground text-sm mt-1">
            Try adjusting your filters or search terms
          </p>
          <Button variant="outline" className="mt-4" onClick={resetFilters}>
            Clear Filters
          </Button>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-4">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
          >
            <ChevronLeft className="h-4 w-4 mr-1" />
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage(page + 1)}
          >
            Next
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        </div>
      )}
    </div>
  );
}
