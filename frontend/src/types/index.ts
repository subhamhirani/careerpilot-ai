// ============================================================
// CareerPilot - TypeScript Types (matching DB schema)
// ============================================================

// --- Enums / Unions ---

export type JobTier = 'tier_a' | 'tier_b' | 'tier_c';
export type JobStatus = 'new' | 'applied' | 'interviewing' | 'rejected' | 'offer' | 'accepted' | 'archived';
export type ApplicationStatus = 'pending_approval' | 'approved' | 'rejected' | 'submitted' | 'error';
export type ApprovalStatus = 'pending' | 'approved' | 'rejected';
export type MatchScoreCategory = 'excellent' | 'good' | 'fair' | 'poor';
export type ResumeStatus = 'active' | 'archived';

// --- Core Entities ---

export interface Job {
  id: string;
  title: string;
  company: string;
  location: string;
  description: string;
  url: string;
  source: string;
  tier: JobTier;
  status: JobStatus;
  salary_min?: number;
  salary_max?: number;
  salary_currency?: string;
  match_score?: number;
  match_breakdown?: MatchBreakdown;
  posted_at?: string;
  created_at: string;
  updated_at: string;
}

export interface MatchBreakdown {
  skills: number;
  experience: number;
  education: number;
  location: number;
  salary: number;
  overall: number;
}

export interface Application {
  id: string;
  job_id: string;
  resume_id?: string;
  cover_letter?: string;
  status: ApplicationStatus;
  match_score?: number;
  submitted_at?: string;
  approved_at?: string;
  error_message?: string;
  job?: Job;
  resume?: Resume;
  created_at: string;
  updated_at: string;
}

export interface Approval {
  id: string;
  application_id: string;
  status: ApprovalStatus;
  reviewer?: string;
  notes?: string;
  reviewed_at?: string;
  application?: Application;
  created_at: string;
}

export interface Resume {
  id: string;
  name: string;
  file_path: string;
  file_type: string;
  file_size: number;
  is_active: boolean;
  skills?: string[];
  parsed_data?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface UserSettings {
  id: string;
  preferences: Record<string, unknown>;
  notification_enabled: boolean;
  auto_apply: boolean;
  max_applications_per_day: number;
  search_queries: SearchQuery[];
  created_at: string;
  updated_at: string;
}

export interface SearchQuery {
  id: string;
  query: string;
  location?: string;
  tiers?: JobTier[];
  sources?: string[];
  active: boolean;
}

// --- Analytics ---

export interface DashboardStats {
  total_jobs_found: number;
  total_applications_sent: number;
  pending_approvals: number;
  interview_rate: number;
  top_matches: Job[];
  recent_activity: ActivityItem[];
  scraper: ScraperStatus;
}

export interface ScraperStatus {
  total_jobs: number;
  source_breakdown: Record<string, number>;
  last_scrape_at: string | null;
  is_scraping: boolean;
}

export interface ActivityItem {
  id: string;
  type: 'job_found' | 'application_submitted' | 'approval_granted' | 'interview_scheduled' | 'rejection' | 'offer';
  message: string;
  timestamp: string;
  job_id?: string;
}

export interface MatchTrend {
  date: string;
  average_score: number;
  count: number;
}

export interface SourceBreakdown {
  source: string;
  count: number;
  applications: number;
}

export interface FunnelData {
  stage: string;
  count: number;
}

export interface AnalyticsData {
  match_trends: MatchTrend[];
  source_breakdown: SourceBreakdown[];
  funnel: FunnelData[];
  total_jobs: number;
  total_applications: number;
  approval_rate: number;
  interview_conversion: number;
}

// --- API ---

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
  count?: number;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  total: number;
  page: number;
  page_size: number;
}

// --- Component Props ---

export interface StatsCardProps {
  title: string;
  value: string | number;
  description?: string;
  icon?: React.ReactNode;
  trend?: {
    direction: 'up' | 'down' | 'neutral';
    value: string;
  };
}

export interface JobCardProps {
  job: Job;
  onApply?: (jobId: string) => void;
  onView?: (jobId: string) => void;
}

export interface ApprovalCardProps {
  approval: Approval;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}

export interface MatchScoreBadgeProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

// --- Notification ---

export interface Notification {
  id: string;
  user_id: string;
  type: 'job_match' | 'application_update' | 'approval_needed' | 'cover_letter_generated' | 'resume_parsed' | 'scraper_complete' | 'system';
  title: string;
  message: string;
  is_read: boolean;
  entity_type?: string;
  entity_id?: string;
  created_at: string;
}

// --- User Profile ---

export interface UserProfile {
  id: string | null;
  user_id: string;
  full_name: string;
  phone: string;
  headline: string;
  summary: string;
  skills: string[];
  experience: any[];
  education: any[];
  certifications: any[];
  linkedin_url: string;
  github_url: string;
  portfolio_url: string;
  preferred_location: string;
  preferred_roles: string[];
}

// --- Cover Letter ---

export interface CoverLetter {
  id: string;
  job_posting_id: string | null;
  title: string;
  content: string;
  tone: string;
  word_count: number;
  is_approved: boolean;
  created_at: string | null;
}
