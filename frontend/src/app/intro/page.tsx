'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Sparkles,
  Briefcase,
  Search,
  Bot,
  CheckCircle2,
  ArrowRight,
  ShieldCheck,
  Zap,
  Globe,
  FileText,
  Layers,
  TrendingUp,
  UserPlus,
  Lock,
  Play,
  Star,
  Award,
  Cpu,
  Check,
} from 'lucide-react';

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
    <div className="min-h-screen bg-slate-950 text-slate-100 selection:bg-indigo-500 selection:text-white overflow-x-hidden">
      {/* Background Ambient Glows */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-indigo-600/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute top-1/3 -right-40 w-96 h-96 bg-emerald-500/15 rounded-full blur-3xl" />
        <div className="absolute bottom-10 left-1/4 w-96 h-96 bg-purple-600/15 rounded-full blur-3xl" />
      </div>

      {/* Sticky Header */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-slate-950/80 border-b border-slate-800/80">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/30 group-hover:scale-105 transition-transform">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
              CareerPilot AI
            </span>
            <span className="text-[10px] uppercase font-semibold tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              Pro Max 2.6
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-400">
            <a href="#simulator" className="hover:text-white transition-colors">
              Interactive Demo
            </a>
            <a href="#scrapers" className="hover:text-white transition-colors">
              9 Scraper Sources
            </a>
            <a href="#workflow" className="hover:text-white transition-colors">
              How it Works
            </a>
            <a href="#features" className="hover:text-white transition-colors">
              AI Intelligence
            </a>
          </nav>

          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="px-4 py-2 rounded-lg text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-900 transition-colors"
            >
              Sign In
            </Link>
            <Link
              href="/register"
              className="px-5 py-2 rounded-lg text-sm font-semibold bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40 transition-all flex items-center gap-2"
            >
              <span>Get Started Free</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative z-10 pt-16 pb-20 px-6">
        <div className="max-w-5xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-medium mb-8">
            <Cpu className="w-3.5 h-3.5" />
            <span>Autonomous AI Career Intelligence Engine</span>
          </div>

          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-white mb-6 leading-[1.1]">
            Your AI Agent for{' '}
            <span className="bg-gradient-to-r from-indigo-400 via-purple-400 to-emerald-400 bg-clip-text text-transparent">
              Multi-Source Job Hunting
            </span>
          </h1>

          <p className="text-lg sm:text-xl text-slate-400 max-w-3xl mx-auto mb-10 leading-relaxed">
            Stop searching manually. CareerPilot AI aggregates jobs across{' '}
            <span className="text-slate-200 font-semibold">BrightData, Remotive, The Muse, LinkedIn, Naukri</span>{' '}
            and more — automatically scoring each role against your resume and generating bespoke AI cover letters.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            <Link
              href="/register"
              className="w-full sm:w-auto px-8 py-4 rounded-xl font-semibold text-base bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white shadow-xl shadow-indigo-500/30 hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center justify-center gap-3"
            >
              <UserPlus className="w-5 h-5" />
              <span>Launch Your Autonomous Search</span>
            </Link>
            <a
              href="#simulator"
              className="w-full sm:w-auto px-8 py-4 rounded-xl font-semibold text-base bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 transition-all flex items-center justify-center gap-2"
            >
              <Play className="w-4 h-4 text-indigo-400 fill-indigo-400" />
              <span>Try Live AI Simulator</span>
            </a>
          </div>

          {/* Quick Trust Badges */}
          <div className="flex flex-wrap items-center justify-center gap-6 text-xs font-medium text-slate-500">
            <span className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              9+ Job Portal Integrations
            </span>
            <span className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-indigo-500" />
              pgvector Semantic Embeddings
            </span>
            <span className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-purple-500" />
              Instant Cover Letter Generation
            </span>
          </div>
        </div>
      </section>

      {/* INTERACTIVE SIMULATOR (UI/UX Pro Max Showcase) */}
      <section id="simulator" className="relative z-10 py-16 px-6 max-w-6xl mx-auto">
        <div className="text-center mb-10">
          <h2 className="text-2xl sm:text-3xl font-bold text-white mb-2">
            Interactive AI Match & Cover Letter Simulator
          </h2>
          <p className="text-slate-400 text-sm">
            Select a target role below to see how CareerPilot AI evaluates semantic alignment and composes cover letters.
          </p>
        </div>

        {/* Persona Selector Tabs */}
        <div className="flex flex-wrap justify-center gap-3 mb-8">
          {PERSONAS.map((p) => {
            const isActive = activePersona.id === p.id;
            return (
              <button
                key={p.id}
                onClick={() => setActivePersona(p)}
                className={`px-5 py-3 rounded-xl text-sm font-medium transition-all flex items-center gap-2.5 border ${
                  isActive
                    ? 'bg-indigo-600/20 border-indigo-500 text-white shadow-lg shadow-indigo-500/20'
                    : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                <Sparkles className={`w-4 h-4 ${isActive ? 'text-indigo-400' : 'text-slate-500'}`} />
                <span>{p.title.split('@')[0].trim()}</span>
              </button>
            );
          })}
        </div>

        {/* Interactive Match Card Preview */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-2xl backdrop-blur-xl">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-6 border-b border-slate-800">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <span className="px-2.5 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold">
                  {activePersona.source}
                </span>
                <span className="text-xs text-slate-400">{activePersona.location}</span>
                <span className="text-xs text-slate-400">• {activePersona.salary}</span>
              </div>
              <h3 className="text-xl sm:text-2xl font-bold text-white">{activePersona.title}</h3>
            </div>

            {/* AI Vector Score Pill */}
            <div className="flex items-center gap-4 bg-slate-950/80 border border-slate-800 px-5 py-3 rounded-xl">
              <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-emerald-500 to-indigo-500 flex items-center justify-center text-white font-extrabold text-lg shadow-md">
                {activePersona.score}%
              </div>
              <div>
                <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold">
                  Vector Match Score
                </div>
                <div className="text-sm font-bold text-emerald-400">{activePersona.verdict}</div>
              </div>
            </div>
          </div>

          {/* Sub Tabs inside Preview Card */}
          <div className="flex gap-4 mt-6 mb-6 border-b border-slate-800/80">
            <button
              onClick={() => setActiveTab('match')}
              className={`pb-3 text-sm font-semibold border-b-2 transition-all ${
                activeTab === 'match'
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              AI Semantic Fit Breakdown
            </button>
            <button
              onClick={() => setActiveTab('cover')}
              className={`pb-3 text-sm font-semibold border-b-2 transition-all ${
                activeTab === 'cover'
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              Auto-Generated Cover Letter
            </button>
          </div>

          {activeTab === 'match' ? (
            <div className="space-y-3">
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                Why CareerPilot AI Recommends This Role:
              </h4>
              {activePersona.reasons.map((reason, i) => (
                <div key={i} className="flex items-start gap-3 p-3.5 rounded-xl bg-slate-950/50 border border-slate-800/80">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                  <span className="text-sm text-slate-300">{reason}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-5 rounded-xl bg-slate-950/80 border border-slate-800/80">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs text-indigo-400 font-semibold flex items-center gap-1.5">
                  <Bot className="w-4 h-4" />
                  Customized for {activePersona.title.split('@')[1].trim()}
                </span>
                <span className="text-[11px] text-slate-500">Generated in 1.4s via LLM Engine</span>
              </div>
              <p className="text-sm text-slate-300 italic leading-relaxed">{activePersona.coverLetterSnippet}</p>
            </div>
          )}
        </div>
      </section>

      {/* 9 SCRAPER SOURCES MATRIX */}
      <section id="scrapers" className="relative z-10 py-16 px-6 max-w-6xl mx-auto border-t border-slate-900">
        <div className="text-center mb-12">
          <h2 className="text-2xl sm:text-3xl font-bold text-white mb-3">
            Multi-Tier Scraper Architecture
          </h2>
          <p className="text-slate-400 text-sm max-w-2xl mx-auto">
            Our pipeline continuously sweeps 7 primary API portals and intelligently executes Tier-2 local scrapers as a resilient fallback.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {SCRAPERS.map((s) => (
            <div
              key={s.name}
              className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-slate-700 transition-all flex flex-col justify-between"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="font-bold text-white text-base">{s.name}</span>
                <span
                  className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full ${
                    s.status.includes('Live')
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                  }`}
                >
                  {s.status}
                </span>
              </div>
              <div className="text-xs text-slate-400 mb-1">{s.type}</div>
              <div className="text-xs font-medium text-slate-500">{s.count}</div>
            </div>
          ))}
        </div>
      </section>

      {/* 3-STEP WORKFLOW */}
      <section id="workflow" className="relative z-10 py-20 px-6 max-w-6xl mx-auto border-t border-slate-900">
        <div className="text-center mb-16">
          <h2 className="text-2xl sm:text-4xl font-bold text-white mb-3">
            How Autonomous Job Hunting Works
          </h2>
          <p className="text-slate-400 text-sm">Three automated phases running 24/7 on your behalf.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 relative">
            <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 font-bold mb-5">
              01
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Aggregated Scraping</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Sweeps tech job boards and enterprise portals simultaneously, deduplicating listings by unique URL in PostgreSQL.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 relative">
            <div className="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 font-bold mb-5">
              02
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Vector Matching Engine</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Uses pgvector cosine similarity to rank job descriptions against your resume and profile skills automatically.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 relative">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 font-bold mb-5">
              03
            </div>
            <h3 className="text-lg font-bold text-white mb-2">1-Click Application Workflow</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Generates role-specific cover letters and tracks every application status from Submission to Interview.
            </p>
          </div>
        </div>
      </section>

      {/* FINAL CTA BANNER */}
      <section className="relative z-10 py-20 px-6 max-w-5xl mx-auto">
        <div className="rounded-3xl bg-gradient-to-r from-indigo-900/50 via-purple-900/40 to-slate-900 border border-indigo-500/30 p-8 sm:p-14 text-center relative overflow-hidden shadow-2xl">
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white mb-4">
            Ready to Upgrade Your Career Pipeline?
          </h2>
          <p className="text-slate-300 text-base max-w-2xl mx-auto mb-8">
            Create your free account today and let CareerPilot AI discover, score, and draft applications for you.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/register"
              className="w-full sm:w-auto px-8 py-4 rounded-xl font-semibold text-base bg-white hover:bg-slate-100 text-slate-950 shadow-xl transition-all"
            >
              Get Started Now
            </Link>
            <Link
              href="/login"
              className="w-full sm:w-auto px-8 py-4 rounded-xl font-semibold text-base bg-slate-900/80 hover:bg-slate-900 text-white border border-slate-700 transition-all"
            >
              Existing Member Sign In
            </Link>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-slate-900 py-10 px-6 text-center text-xs text-slate-500">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            <span className="font-semibold text-slate-400">CareerPilot AI Pro Max</span>
          </div>
          <p>© 2026 CareerPilot AI. Autonomous Agentic Career System.</p>
          <div className="flex gap-6">
            <Link href="/login" className="hover:text-slate-300">
              Sign In
            </Link>
            <Link href="/register" className="hover:text-slate-300">
              Register
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
