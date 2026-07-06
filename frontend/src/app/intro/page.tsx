'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Briefcase, ArrowRight, UserPlus, Lock } from '@phosphor-icons/react';

export default function IntroPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      <div className="max-w-3xl mx-auto px-6 py-20 text-center">
        {/* Logo/Icon */}
        <div className="mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-primary/10 text-primary mb-6">
            <Briefcase className="h-10 w-10" />
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 dark:text-white mb-4">
            CareerPilot AI
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
            Your AI-powered career navigation platform. Find, match, and apply to jobs intelligently with automated workflows.
          </p>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-6 mb-12 max-w-4xl mx-auto">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
            <div className="w-12 h-12 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center mb-4 mx-auto">
              <Briefcase className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Smart Job Discovery</h3>
            <p className="text-gray-600 dark:text-gray-400">AI-powered scraping from multiple job boards with location and role filtering.</p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
            <div className="w-12 h-12 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center mb-4 mx-auto">
              <ArrowRight className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Intelligent Matching</h3>
            <p className="text-gray-600 dark:text-gray-400">Vector-based semantic matching scores jobs against your profile and resume.</p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
            <div className="w-12 h-12 rounded-lg bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center mb-4 mx-auto">
              <UserPlus className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Automated Applications</h3>
            <p className="text-gray-600 dark:text-gray-400">Generate tailored cover letters and apply with one click. Track all applications in one place.</p>
          </div>
        </div>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
          <Link href="/register" passHref>
            <Button size="lg" className="w-full sm:w-auto px-8 py-3 text-lg gap-2">
              <UserPlus className="h-5 w-5" />
              <span>Get Started Free</span>
            </Button>
          </Link>
          <Link href="/login" passHref>
            <Button size="lg" variant="outline" className="w-full sm:w-auto px-8 py-3 text-lg gap-2">
              <Lock className="h-5 w-5" />
              <span>Sign In</span>
            </Button>
          </Link>
        </div>

        {/* Trust indicators */}
        <div className="border-t border-gray-200 dark:border-gray-700 pt-8">
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">Trusted by job seekers worldwide</p>
          <div className="flex flex-wrap items-center justify-center gap-6 text-gray-400 dark:text-gray-500 text-sm">
            <span>✓ AI-Powered Matching</span>
            <span>✓ Data Privacy First</span>
            <span>✓ No Spam Pavilion.</span>
            <span>✓ Open Source Core</span>
          </div>
        </div>
      </div>
    </div>
  );
}
