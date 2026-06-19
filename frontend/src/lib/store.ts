// ============================================================
// CareerPilot - Zustand Global Store
// ============================================================

import { create } from 'zustand';
import type {
  Job,
  Application,
  Approval,
  Resume,
  UserSettings,
  DashboardStats,
  AnalyticsData,
  SearchQuery,
} from '@/types';

// --- UI State ---

interface UIState {
  sidebarOpen: boolean;
  theme: 'light' | 'dark' | 'system';
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  theme: 'system',
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setTheme: (theme) => set({ theme }),
}));

// --- Job State ---

interface JobState {
  jobs: Job[];
  currentJob: Job | null;
  filters: {
    tier: string;
    location: string;
    status: string;
    source: string;
    date_from: string;
    date_to: string;
    search: string;
  };
  loading: boolean;
  total: number;
  page: number;
  setJobs: (jobs: Job[], total?: number) => void;
  setCurrentJob: (job: Job | null) => void;
  setFilter: (key: string, value: string) => void;
  resetFilters: () => void;
  setLoading: (loading: boolean) => void;
  setPage: (page: number) => void;
}

const defaultFilters = {
  tier: '',
  location: '',
  status: '',
  source: '',
  date_from: '',
  date_to: '',
  search: '',
};

export const useJobStore = create<JobState>((set) => ({
  jobs: [],
  currentJob: null,
  filters: { ...defaultFilters },
  loading: false,
  total: 0,
  page: 1,
  setJobs: (jobs, total) => set({ jobs, total: total ?? jobs.length }),
  setCurrentJob: (job) => set({ currentJob: job }),
  setFilter: (key, value) =>
    set((state) => ({
      filters: { ...state.filters, [key]: value },
      page: 1, // reset page on filter change
    })),
  resetFilters: () => set({ filters: { ...defaultFilters }, page: 1 }),
  setLoading: (loading) => set({ loading }),
  setPage: (page) => set({ page }),
}));

// --- Application State ---

interface ApplicationState {
  applications: Application[];
  loading: boolean;
  total: number;
  setApplications: (apps: Application[], total?: number) => void;
  setLoading: (loading: boolean) => void;
}

export const useApplicationStore = create<ApplicationState>((set) => ({
  applications: [],
  loading: false,
  total: 0,
  setApplications: (apps, total) => set({ applications: apps, total: total ?? apps.length }),
  setLoading: (loading) => set({ loading }),
}));

// --- Approval State ---

interface ApprovalState {
  approvals: Approval[];
  loading: boolean;
  total: number;
  setApprovals: (approvals: Approval[], total?: number) => void;
  setLoading: (loading: boolean) => void;
}

export const useApprovalStore = create<ApprovalState>((set) => ({
  approvals: [],
  loading: false,
  total: 0,
  setApprovals: (approvals, total) => set({ approvals, total: total ?? approvals.length }),
  setLoading: (loading) => set({ loading }),
}));

// --- Resume State ---

interface ResumeState {
  resumes: Resume[];
  loading: boolean;
  setResumes: (resumes: Resume[]) => void;
  setLoading: (loading: boolean) => void;
}

export const useResumeStore = create<ResumeState>((set) => ({
  resumes: [],
  loading: false,
  setResumes: (resumes) => set({ resumes }),
  setLoading: (loading) => set({ loading }),
}));

// --- Dashboard State ---

interface DashboardState {
  stats: DashboardStats | null;
  loading: boolean;
  setStats: (stats: DashboardStats) => void;
  setLoading: (loading: boolean) => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  stats: null,
  loading: false,
  setStats: (stats) => set({ stats }),
  setLoading: (loading) => set({ loading }),
}));

// --- Analytics State ---

interface AnalyticsState {
  data: AnalyticsData | null;
  loading: boolean;
  setData: (data: AnalyticsData) => void;
  setLoading: (loading: boolean) => void;
}

export const useAnalyticsStore = create<AnalyticsState>((set) => ({
  data: null,
  loading: false,
  setData: (data) => set({ data }),
  setLoading: (loading) => set({ loading }),
}));

// --- Settings State ---

interface SettingsState {
  settings: UserSettings | null;
  loading: boolean;
  setSettings: (settings: UserSettings) => void;
  setLoading: (loading: boolean) => void;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  settings: null,
  loading: false,
  setSettings: (settings) => set({ settings }),
  setLoading: (loading) => set({ loading }),
}));
