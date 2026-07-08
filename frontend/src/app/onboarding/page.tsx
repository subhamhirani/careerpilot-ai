'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { toast } from 'sonner';
import {
  Upload,
  User,
  Key,
  Search,
  Sparkles,
  FileText,
  Send,
  CheckCircle2,
  Circle,
  SkipForward,
  ArrowRight,
  ArrowLeft,
  Rocket,
  Briefcase,
  MapPin,
  X,
} from '@phosphor-icons/react';

// ── Types ──────────────────────────────────────────────────

interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  href: string;
  status: 'complete' | 'pending' | 'skippable';
  detail?: string | null;
}

interface OnboardingStatus {
  steps: OnboardingStep[];
  progress: { completed: number; total: number; percent: number };
  is_complete: boolean;
}

// ── Step configuration ─────────────────────────────────────

const STEP_META: Record<string, { icon: typeof Upload; color: string; description: string }> = {
  upload_resume: {
    icon: Upload,
    color: 'text-blue-500',
    description: 'Upload your resume so CareerPilot can match you with the right jobs.',
  },
  setup_profile: {
    icon: User,
    color: 'text-purple-500',
    description: 'Tell us about your skills, experience, and what roles you\'re targeting.',
  },
  add_api_keys: {
    icon: Key,
    color: 'text-amber-500',
    description: 'Connect job board APIs for real-time listings. Optional — we have pre-loaded jobs.',
  },
  run_scraper: {
    icon: Search,
    color: 'text-green-500',
    description: 'Job feed is ready! Browse pre-loaded jobs or run the scraper for fresh listings.',
  },
  view_matches: {
    icon: Sparkles,
    color: 'text-yellow-500',
    description: 'See AI-scored job matches ranked by how well they fit your profile.',
  },
  generate_cover_letter: {
    icon: FileText,
    color: 'text-pink-500',
    description: 'Let AI craft a tailored cover letter for any job you\'re interested in.',
  },
  apply: {
    icon: Send,
    color: 'text-indigo-500',
    description: 'Apply to jobs and track your application status all in one place.',
  },
};

const STEP_ORDER = [
  'upload_resume',
  'setup_profile',
  'add_api_keys',
  'run_scraper',
  'view_matches',
  'generate_cover_letter',
  'apply',
];

// ── Main component ─────────────────────────────────────────

export default function OnboardingPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [activeStep, setActiveStep] = useState<string>('upload_resume');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Profile form state
  const [profile, setProfile] = useState({
    full_name: '',
    headline: '',
    summary: '',
    skills: '',
    preferred_location: '',
    preferred_roles: '',
    linkedin_url: '',
    github_url: '',
  });

  // Resume upload state
  const [uploading, setUploading] = useState(false);

  // API keys state
  const [apiKeys, setApiKeys] = useState({ linkedin: '', indeed: '', naukri: '' });

  const fetchStatus = useCallback(async () => {
    try {
      const data = await api.get<OnboardingStatus>('/onboarding/status');
      setStatus(data);
      // Auto-advance to first incomplete step
      const firstPending = data.steps.find(
        (s) => s.status === 'pending'
      );
      if (firstPending) {
        setActiveStep(firstPending.id);
      }
    } catch {
      // If onboarding endpoint fails, still show the page
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/');
      return;
    }
    fetchStatus();
  }, [isAuthenticated, router, fetchStatus]);

  // ── Handlers ─────────────────────────────────────────────

  const handleResumeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('name', file.name.replace(/\.(pdf|docx)$/i, ''));
      await api.postForm('/resumes/upload', formData);
      toast.success('Resume uploaded successfully!');
      fetchStatus();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleProfileSave = async () => {
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {};
      if (profile.full_name.trim()) payload.full_name = profile.full_name.trim();
      if (profile.headline.trim()) payload.headline = profile.headline.trim();
      if (profile.summary.trim()) payload.summary = profile.summary.trim();
      if (profile.skills.trim()) {
        payload.skills = profile.skills.split(',').map((s) => s.trim()).filter(Boolean);
      }
      if (profile.preferred_location.trim()) payload.preferred_location = profile.preferred_location.trim();
      if (profile.preferred_roles.trim()) {
        payload.preferred_roles = profile.preferred_roles.split(',').map((s) => s.trim()).filter(Boolean);
      }
      if (profile.linkedin_url.trim()) payload.linkedin_url = profile.linkedin_url.trim();
      if (profile.github_url.trim()) payload.github_url = profile.github_url.trim();

      await api.post('/onboarding/setup-profile', payload);
      toast.success('Profile saved!');
      fetchStatus();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  const handleSkip = (stepId: string) => {
    const idx = STEP_ORDER.indexOf(stepId);
    const next = STEP_ORDER[idx + 1];
    if (next) setActiveStep(next);
  };

  const handleFinish = async () => {
    try {
      await api.post('/onboarding/dismiss', {});
    } catch {
      // ignore
    }
    router.push('/jobs');
  };

  // ── Render ───────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center space-y-4">
          <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full mx-auto" />
          <p className="text-muted-foreground">Setting up your workspace…</p>
        </div>
      </div>
    );
  }

  const steps = status?.steps || [];
  const progress = status?.progress || { completed: 0, total: 6, percent: 0 };
  const currentStepMeta = STEP_META[activeStep];
  const CurrentIcon = currentStepMeta?.icon || Circle;
  const clampedPercent = Math.min(100, Math.max(0, progress.percent || 0));

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <Rocket className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-2xl font-bold">Welcome to CareerPilot!</h1>
            <p className="text-muted-foreground">
              Let's get you set up in a few quick steps. Everything uses your own data.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 mt-4">
          <Progress value={clampedPercent} className="flex-1 h-2" />
          <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">
            {progress.completed}/{progress.total} done ({clampedPercent}%)
          </span>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        {/* Step sidebar */}
        <div className="space-y-1">
          {steps.map((step) => {
            const meta = STEP_META[step.id];
            const Icon = meta?.icon || Circle;
            const isActive = step.id === activeStep;
            const isComplete = step.status === 'complete';
            return (
              <button
                key={step.id}
                onClick={() => setActiveStep(step.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left text-sm transition-colors ${
                  isActive
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'hover:bg-muted text-muted-foreground'
                }`}
              >
                {isComplete ? (
                  <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0" />
                ) : (
                  <Icon className={`h-5 w-5 shrink-0 ${meta?.color || ''}`} />
                )}
                <div className="min-w-0">
                  <div className="truncate">{step.title}</div>
                  {step.detail && (
                    <div className="text-xs text-muted-foreground truncate">{step.detail}</div>
                  )}
                </div>
              </button>
            );
          })}
        </div>

        {/* Active step content */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <CurrentIcon className={`h-6 w-6 ${currentStepMeta?.color || ''}`} />
              <div>
                <CardTitle>
                  {steps.find((s) => s.id === activeStep)?.title || 'Setup'}
                </CardTitle>
                <CardDescription>
                  {currentStepMeta?.description}
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* ── Upload Resume ── */}
            {activeStep === 'upload_resume' && (
              <div className="space-y-4">
                <div className="border-2 border-dashed rounded-lg p-8 text-center space-y-4 hover:border-primary/50 transition-colors">
                  <Upload className="h-10 w-10 mx-auto text-muted-foreground" />
                  <div>
                    <p className="font-medium">Upload your resume</p>
                    <p className="text-sm text-muted-foreground">PDF or DOCX, max 10MB</p>
                  </div>
                  <Label htmlFor="resume-upload">
                    <Button variant="outline" disabled={uploading} asChild>
                      <span>{uploading ? 'Uploading…' : 'Choose File'}</span>
                    </Button>
                  </Label>
                  <input
                    id="resume-upload"
                    type="file"
                    accept=".pdf,.docx"
                    className="hidden"
                    onChange={handleResumeUpload}
                  />
                </div>
                <div className="bg-muted/50 rounded-lg p-4 text-sm space-y-2">
                  <p className="font-medium">Why we need this:</p>
                  <ul className="list-disc list-inside text-muted-foreground space-y-1">
                    <li>Extract your skills, experience, and education automatically</li>
                    <li>Match you with jobs that fit your background</li>
                    <li>Generate tailored cover letters based on your experience</li>
                  </ul>
                </div>
                {steps.find((s) => s.id === 'upload_resume')?.status === 'complete' && (
                  <div className="flex items-center gap-2 text-green-600 text-sm">
                    <CheckCircle2 className="h-4 w-4" />
                    Resume uploaded! You can upload more later.
                  </div>
                )}
              </div>
            )}

            {/* ── Setup Profile ── */}
            {activeStep === 'setup_profile' && (
              <div className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Full Name</Label>
                    <Input
                      placeholder="John Doe"
                      value={profile.full_name}
                      onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Headline</Label>
                    <Input
                      placeholder="DevOps Engineer | Cloud | SRE"
                      value={profile.headline}
                      onChange={(e) => setProfile({ ...profile, headline: e.target.value })}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Summary</Label>
                  <Textarea
                    placeholder="Brief description of your background and what you're looking for..."
                    rows={3}
                    value={profile.summary}
                    onChange={(e) => setProfile({ ...profile, summary: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Skills (comma-separated)</Label>
                  <Input
                    placeholder="Python, Docker, Kubernetes, AWS, Linux"
                    value={profile.skills}
                    onChange={(e) => setProfile({ ...profile, skills: e.target.value })}
                  />
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Preferred Location</Label>
                    <Input
                      placeholder="Remote, Bangalore, Mumbai"
                      value={profile.preferred_location}
                      onChange={(e) => setProfile({ ...profile, preferred_location: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Target Roles (comma-separated)</Label>
                    <Input
                      placeholder="DevOps Engineer, SRE, Cloud Engineer"
                      value={profile.preferred_roles}
                      onChange={(e) => setProfile({ ...profile, preferred_roles: e.target.value })}
                    />
                  </div>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>LinkedIn URL</Label>
                    <Input
                      placeholder="https://linkedin.com/in/yourname"
                      value={profile.linkedin_url}
                      onChange={(e) => setProfile({ ...profile, linkedin_url: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>GitHub URL</Label>
                    <Input
                      placeholder="https://github.com/yourname"
                      value={profile.github_url}
                      onChange={(e) => setProfile({ ...profile, github_url: e.target.value })}
                    />
                  </div>
                </div>
                <Button onClick={handleProfileSave} disabled={saving}>
                  {saving ? 'Saving…' : 'Save Profile'}
                </Button>
              </div>
            )}

            {/* ── API Keys ── */}
            {activeStep === 'add_api_keys' && (
              <div className="space-y-4">
                <div className="bg-blue-50 dark:bg-blue-950/30 rounded-lg p-4 text-sm space-y-2">
                  <p className="font-medium text-blue-700 dark:text-blue-300">Optional step</p>
                  <p className="text-blue-600 dark:text-blue-400">
                    CareerPilot comes with pre-loaded job listings. Add API keys later to scrape fresh jobs from specific boards.
                  </p>
                </div>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label>LinkedIn API Key</Label>
                    <Input
                      type="password"
                      placeholder="Leave empty to skip"
                      value={apiKeys.linkedin}
                      onChange={(e) => setApiKeys({ ...apiKeys, linkedin: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Indeed Publisher ID</Label>
                    <Input
                      type="password"
                      placeholder="Leave empty to skip"
                      value={apiKeys.indeed}
                      onChange={(e) => setApiKeys({ ...apiKeys, indeed: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Naukri API Key</Label>
                    <Input
                      type="password"
                      placeholder="Leave empty to skip"
                      value={apiKeys.naukri}
                      onChange={(e) => setApiKeys({ ...apiKeys, naukri: e.target.value })}
                    />
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => handleSkip('add_api_keys')}>
                    <SkipForward className="h-4 w-4 mr-1" />
                    Skip for now
                  </Button>
                </div>
              </div>
            )}

            {/* ── Job Feed / Scraper ── */}
            {activeStep === 'run_scraper' && (
              <div className="space-y-4">
                <div className="bg-green-50 dark:bg-green-950/30 rounded-lg p-4 text-sm space-y-2">
                  <p className="font-medium text-green-700 dark:text-green-300">Jobs are ready!</p>
                  <p className="text-green-600 dark:text-green-400">
                    CareerPilot comes with pre-loaded job listings from LinkedIn and Naukri. You can browse them right away.
                  </p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Button variant="outline" onClick={() => router.push('/jobs')}>
                    <Briefcase className="h-4 w-4 mr-2" />
                    Browse Jobs
                  </Button>
                  <Button variant="outline" onClick={() => router.push('/scraper')}>
                    <Search className="h-4 w-4 mr-2" />
                    Run Scraper
                  </Button>
                </div>
              </div>
            )}

            {/* ── View Matches ── */}
            {activeStep === 'view_matches' && (
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Once your resume is uploaded and profile is set, CareerPilot will match you with the best jobs.
                </p>
                <div className="bg-muted/50 rounded-lg p-4 text-sm space-y-2">
                  <p className="font-medium">How matching works:</p>
                  <ul className="list-disc list-inside text-muted-foreground space-y-1">
                    <li>Skills match — how your skills align with job requirements</li>
                    <li>Experience level — years and relevance of your background</li>
                    <li>Education — degree and field alignment</li>
                    <li>Location — proximity or remote compatibility</li>
                    <li>Salary — compensation range fit</li>
                  </ul>
                </div>
                <Button onClick={() => router.push('/matches')}>
                  <Sparkles className="h-4 w-4 mr-2" />
                  View My Matches
                </Button>
              </div>
            )}

            {/* ── Cover Letter ── */}
            {activeStep === 'generate_cover_letter' && (
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  AI generates personalized cover letters based on your resume and the job description.
                </p>
                <div className="bg-muted/50 rounded-lg p-4 text-sm space-y-2">
                  <p className="font-medium">How it works:</p>
                  <ul className="list-disc list-inside text-muted-foreground space-y-1">
                    <li>Open any job listing</li>
                    <li>Click "Generate Cover Letter"</li>
                    <li>AI tailors it using your resume + job description</li>
                    <li>Review, edit, and save</li>
                  </ul>
                </div>
                <Button onClick={() => router.push('/jobs')}>
                  <FileText className="h-4 w-4 mr-2" />
                  Go to Jobs
                </Button>
              </div>
            )}

            {/* ── Apply ── */}
            {activeStep === 'apply' && (
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Track all your job applications in one place.
                </p>
                <div className="bg-muted/50 rounded-lg p-4 text-sm space-y-2">
                  <p className="font-medium">Application tracking:</p>
                  <ul className="list-disc list-inside text-muted-foreground space-y-1">
                    <li>Apply directly from the job detail page</li>
                    <li>Track status: Applied, Interview, Offer, Rejected</li>
                    <li>Add notes and follow-up reminders</li>
                    <li>View all applications in one dashboard</li>
                  </ul>
                </div>
                <Button onClick={() => router.push('/applications')}>
                  <Send className="h-4 w-4 mr-2" />
                  View Applications
                </Button>
              </div>
            )}

            {/* Navigation */}
            <div className="flex items-center justify-between pt-4 border-t">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  const idx = STEP_ORDER.indexOf(activeStep);
                  if (idx > 0) setActiveStep(STEP_ORDER[idx - 1]);
                }}
                disabled={STEP_ORDER.indexOf(activeStep) === 0}
              >
                <ArrowLeft className="h-4 w-4 mr-1" />
                Back
              </Button>
              <div className="flex gap-2">
                {activeStep !== 'apply' && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const idx = STEP_ORDER.indexOf(activeStep);
                      const next = STEP_ORDER[idx + 1];
                      if (next) setActiveStep(next);
                    }}
                  >
                    Next
                    <ArrowRight className="h-4 w-4 ml-1" />
                  </Button>
                )}
                {activeStep === 'apply' && (
                  <Button onClick={handleFinish}>
                    <Rocket className="h-4 w-4 mr-2" />
                    Go to Dashboard
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
