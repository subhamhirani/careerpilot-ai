'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Briefcase,
  Rocket,
  ArrowRight,
  UserPlus,
  Lock,
  CheckCircle,
  Bot,
  Sparkle,
  Play,
} from '@phosphor-icons/react';

const PERSONAS = [
  {
    id: 'soc',
    title: 'L1 SOC Analyst @ Cybersecurity Corp',
    location: 'Bangalore, India (Hybrid)',
    salary: '₹8,00,000 - ₹12,00,000 PA',
    score: 94,
    verdict: 'EXCELLENT FIT',
    source: 'BrightData Scraper',
    reasons: [
      'Strong semantic match with SIEM tools (Splunk, QRadar) on your resume',
      'Exceeds minimum 1-year experience requirement in network monitoring',
      'Location matches your preferred Bangalore commute zone',
    ],
    coverLetterSnippet:
      'Dear Hiring Team, With practical hands-on experience monitoring security alerts, configuring SIEM dashboards, and remediating vulnerability incidents, I am excited to contribute to your SOC team...',
  },
  {
    id: 'react',
    title: 'Senior React & Next.js Engineer @ SaaS AI Labs',
    location: 'Remote (Global)',
    salary: '$110,000 - $140,000 / yr',
    score: 91,
    verdict: 'STRONG MATCH',
    source: 'Remotive API',
    reasons: [
      'Matches advanced skills in TypeScript, Next.js App Router, and Tailwind CSS',
      'Demonstrated experience building scalable AI dashboard architectures',
      'Full overlap with remote global working timezone preferences',
    ],
    coverLetterSnippet:
      'Dear Engineering Lead, As a full-stack engineer specialized in high-performance Next.js interfaces and real-time AI streaming architectures, I am thrilled to apply for the Senior React role...',
  },
  {
    id: 'devops',
    title: 'Cloud Network & Infrastructure Architect @ FinTech Systems',
    location: 'Mumbai / Bangalore',
    salary: '₹24,00,000 - ₹32,00,000 PA',
    score: 88,
    verdict: 'HIGH COMPATIBILITY',
    source: 'LinkedIn Fallback',
    reasons: [
      'Deep alignment with AWS VPC, Kubernetes, and Terraform infrastructure management',
      'Meets enterprise compliance and zero-trust security requirements',
      'Leadership experience in multi-cloud network operations',
    ],
    coverLetterSnippet:
      'Dear VP of Engineering, My background architecting resilient multi-region cloud infrastructures and managing automated CI/CD deployment pipelines aligns directly with your infrastructure requirements...',
  },
];

const SCRAPERS = [
  { name: 'BrightData', type: 'Tier 1 API & Proxy', status: 'Live Active', count: 'Advanced SERP & Web Unlocker' },
  { name: 'Remotive', type: 'Tier 1 Public API', status: 'Live Active', count: 'Remote & Tech Jobs' },
  { name: 'Arbeitnow', type: 'Tier 1 Public API', status: 'Live Active', count: 'Global Verified Listings' },
  { name: 'The Muse', type: 'Tier 1 Public API', status: 'Live Active', count: 'Curated Tech Roles' },
  { name: 'Adzuna', type: 'Tier 1 Premium API', status: 'Live Active', count: 'Aggregated Global Market' },
  { name: 'JSearch', type: 'Tier 1 Rapid API', status: 'Live Active', count: 'Multi-Board Indexer' },
  { name: 'Findwork', type: 'Tier 1 Developer API', status: 'Live Active', count: 'Software & Engineering' },
  { name: 'LinkedIn', type: 'Tier 2 Local Scraper', status: 'Fallback Active', count: 'Guest Directory Access' },
  { name: 'Naukri', type: 'Tier 2 Local Scraper', status: 'Fallback Active', count: 'Regional Indian Job Portal' },
];

export default function IntroPage() {
  const [activePersona, setActivePersona] = useState(PERSONAS[0]);
  const [activeTab, setActiveTab] = useState<'match' | 'cover'>('match');

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col selection:bg-primary selection:text-primary-foreground">
      {/* Cohesive Application Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
              <Briefcase className="h-5 w-5" />
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-lg leading-none tracking-tight">CareerPilot AI</span>
              <span className="text-[10px] text-muted-foreground font-medium">Autonomous Career Platform</span>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-muted-foreground">
            <a href="#simulator" className="hover:text-foreground transition-colors">
              Interactive Demo
            </a>
            <a href="#scrapers" className="hover:text-foreground transition-colors">
              9 Scraper Portals
            </a>
            <a href="#workflow" className="hover:text-foreground transition-colors">
              Workflow
            </a>
          </nav>

          <div className="flex items-center gap-3">
            <Link href="/login">
              <Button variant="ghost" size="sm" className="gap-2">
                <Lock className="h-4 w-4" />
                <span>Sign In</span>
              </Button>
            </Link>
            <Link href="/register">
              <Button size="sm" className="gap-2">
                <UserPlus className="h-4 w-4" />
                <span>Get Started</span>
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section matching Internal Software SaaS styling */}
      <main className="flex-1">
        <section className="py-16 md:py-24 px-6 border-b bg-gradient-to-b from-background via-muted/30 to-background">
          <div className="max-w-5xl mx-auto text-center space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border bg-card text-xs font-medium text-muted-foreground shadow-sm">
              <Sparkle className="h-3.5 w-3.5 text-primary" />
              <span>Multi-Portal AI Career Navigation Engine</span>
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-foreground leading-tight">
              Unified Job Discovery &{' '}
              <span className="underline decoration-primary/40 underline-offset-8">
                Semantic Match Intelligence
              </span>
            </h1>

            <p className="text-lg sm:text-xl text-muted-foreground max-w-3xl mx-auto leading-relaxed">
              CareerPilot AI combines continuous multi-source job scraping across 9+ portals with pgvector resume vector matching and automated cover letter generation—all in one unified dashboard.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
              <Link href="/register" className="w-full sm:w-auto">
                <Button size="lg" className="w-full sm:w-auto gap-2 px-8">
                  <UserPlus className="h-5 w-5" />
                  <span>Create Free Account</span>
                </Button>
              </Link>
              <a href="#simulator" className="w-full sm:w-auto">
                <Button size="lg" variant="outline" className="w-full sm:w-auto gap-2 px-8">
                  <Play className="h-4 w-4" />
                  <span>Try Interactive Simulator</span>
                </Button>
              </a>
            </div>

            {/* Feature Badges */}
            <div className="pt-8 flex flex-wrap items-center justify-center gap-4 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                9+ Integrated Scrapers
              </span>
              <span className="flex items-center gap-1.5">
                <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                Vector Cosine Similarity
              </span>
              <span className="flex items-center gap-1.5">
                <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                LLM Cover Letter Drafting
              </span>
            </div>
          </div>
        </section>

        {/* INTERACTIVE AI MATCH & COVER LETTER SIMULATOR (Using App Card System) */}
        <section id="simulator" className="py-16 px-6 max-w-6xl mx-auto border-b">
          <div className="text-center mb-10 space-y-2">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              Interactive Match Scoring Simulator
            </h2>
            <p className="text-sm text-muted-foreground max-w-2xl mx-auto">
              Explore how our internal vector matching engine evaluates candidate roles against semantic skills.
            </p>
          </div>

          {/* Persona Tabs */}
          <div className="flex flex-wrap justify-center gap-2 mb-8">
            {PERSONAS.map((p) => {
              const isActive = activePersona.id === p.id;
              return (
                <Button
                  key={p.id}
                  variant={isActive ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setActivePersona(p)}
                  className="gap-2"
                >
                  <Sparkle className="h-4 w-4" />
                  <span>{p.title.split('@')[0].trim()}</span>
                </Button>
              );
            })}
          </div>

          {/* Card styled exactly like internal App Cards */}
          <div className="border rounded-xl bg-card text-card-foreground shadow-sm p-6 sm:p-8 transition-all duration-200 hover:shadow-md">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-6 border-b">
              <div className="space-y-1.5">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="secondary">{activePersona.source}</Badge>
                  <span className="text-xs text-muted-foreground">{activePersona.location}</span>
                  <span className="text-xs text-muted-foreground">• {activePersona.salary}</span>
                </div>
                <h3 className="text-xl sm:text-2xl font-bold text-foreground">{activePersona.title}</h3>
              </div>

              {/* Vector Score Display matching JobCard */}
              <div className="flex items-center gap-4 bg-muted/60 border px-5 py-3 rounded-lg">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground font-bold text-lg shadow-sm">
                  {activePersona.score}%
                </div>
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Match Score
                  </div>
                  <div className="text-sm font-bold text-foreground">{activePersona.verdict}</div>
                </div>
              </div>
            </div>

            {/* Sub navigation inside card */}
            <div className="flex gap-4 mt-6 mb-6 border-b">
              <button
                onClick={() => setActiveTab('match')}
                className={`pb-3 text-sm font-semibold border-b-2 transition-all ${
                  activeTab === 'match'
                    ? 'border-primary text-foreground'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
              >
                Semantic Match Breakdown
              </button>
              <button
                onClick={() => setActiveTab('cover')}
                className={`pb-3 text-sm font-semibold border-b-2 transition-all ${
                  activeTab === 'cover'
                    ? 'border-primary text-foreground'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
              >
                AI Generated Cover Letter
              </button>
            </div>

            {activeTab === 'match' ? (
              <div className="space-y-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                  Key Vector Alignment Reasons:
                </h4>
                {activePersona.reasons.map((reason, i) => (
                  <div key={i} className="flex items-start gap-3 p-3.5 rounded-lg border bg-muted/30 transition-colors hover:bg-muted/50">
                    <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400 shrink-0 mt-0.5" />
                    <span className="text-sm text-foreground">{reason}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-5 rounded-lg border bg-muted/30 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                    <Bot className="h-4 w-4 text-primary" />
                    Tailored for {activePersona.title.split('@')[1].trim()}
                  </span>
                  <span className="text-[11px] text-muted-foreground">Generated via CareerPilot LLM Engine</span>
                </div>
                <p className="text-sm text-foreground italic leading-relaxed">{activePersona.coverLetterSnippet}</p>
              </div>
            )}
          </div>
        </section>

        {/* 9 SCRAPER PORTALS MATRIX (Unified Card Grid) */}
        <section id="scrapers" className="py-16 px-6 max-w-6xl mx-auto border-b">
          <div className="text-center mb-12 space-y-2">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              9 Integrated Scraper & API Sources
            </h2>
            <p className="text-sm text-muted-foreground max-w-2xl mx-auto">
              Our automated discovery engine aggregates live API feeds and intelligent local fallback scrapers into a unified PostgreSQL schema.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {SCRAPERS.map((s) => (
              <div key={s.name} className="p-5 rounded-xl border bg-card text-card-foreground shadow-sm flex flex-col justify-between transition-all duration-200 hover:-translate-y-1 hover:shadow-md hover:border-primary/25">
                <div className="flex items-center justify-between mb-3">
                  <span className="font-bold text-foreground text-base">{s.name}</span>
                  <Badge variant={s.status.includes('Live') ? 'success' : 'secondary'}>
                    {s.status}
                  </Badge>
                </div>
                <div className="text-xs text-muted-foreground mb-1">{s.type}</div>
                <div className="text-xs font-medium text-foreground">{s.count}</div>
              </div>
            ))}
          </div>
        </section>

        {/* 3-STEP WORKFLOW */}
        <section id="workflow" className="py-16 px-6 max-w-6xl mx-auto border-b">
          <div className="text-center mb-12 space-y-2">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              Autonomous 3-Step Workflow
            </h2>
            <p className="text-sm text-muted-foreground">
              Continuous background job discovery, vector scoring, and application assistance.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-6 rounded-xl border bg-card text-card-foreground shadow-sm space-y-3 transition-all duration-200 hover:-translate-y-1 hover:shadow-md">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold">
                01
              </div>
              <h3 className="text-lg font-bold text-foreground">Multi-Portal Aggregation</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Queries Tier-1 APIs and Tier-2 scrapers in parallel, deduplicating listings by unique URL automatically.
              </p>
            </div>

            <div className="p-6 rounded-xl border bg-card text-card-foreground shadow-sm space-y-3 transition-all duration-200 hover:-translate-y-1 hover:shadow-md">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold">
                02
              </div>
              <h3 className="text-lg font-bold text-foreground">Semantic Vector Match</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Uses pgvector similarity to score each job description against your profile and resume experience.
              </p>
            </div>

            <div className="p-6 rounded-xl border bg-card text-card-foreground shadow-sm space-y-3 transition-all duration-200 hover:-translate-y-1 hover:shadow-md">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold">
                03
              </div>
              <h3 className="text-lg font-bold text-foreground">Automated Cover Letters</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Drafts highly contextual cover letters tailored to each company and role with one click.
              </p>
            </div>
          </div>
        </section>

        {/* FINAL CTA matching Internal Software */}
        <section className="py-20 px-6 max-w-4xl mx-auto text-center space-y-6">
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground">
            Get Started with CareerPilot AI
          </h2>
          <p className="text-muted-foreground text-base max-w-xl mx-auto">
            Experience the same streamlined interface from discovery to interview tracking.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/register" className="w-full sm:w-auto">
              <Button size="lg" className="w-full sm:w-auto gap-2 px-8">
                <UserPlus className="h-5 w-5" />
                <span>Create Account</span>
              </Button>
            </Link>
            <Link href="/login" className="w-full sm:w-auto">
              <Button size="lg" variant="outline" className="w-full sm:w-auto gap-2 px-8">
                <Lock className="h-4 w-4" />
                <span>Sign In</span>
              </Button>
            </Link>
          </div>
        </section>
      </main>

      {/* COHESIVE FOOTER */}
      <footer className="border-t py-8 px-6 text-center text-xs text-muted-foreground bg-muted/20">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Briefcase className="h-4 w-4 text-foreground" />
            <span className="font-semibold text-foreground">CareerPilot AI</span>
          </div>
          <p>© 2026 CareerPilot AI. Unified Autonomous Job Platform.</p>
          <div className="flex gap-6">
            <Link href="/login" className="hover:text-foreground transition-colors">
              Sign In
            </Link>
            <Link href="/register" className="hover:text-foreground transition-colors">
              Register
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
