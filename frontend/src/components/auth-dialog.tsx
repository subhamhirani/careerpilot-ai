'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { toast } from 'sonner';

type AuthView = 'login' | 'register' | 'forgot' | 'reset';

interface AuthDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AuthDialog({ open, onOpenChange }: AuthDialogProps) {
  const { login, register, forgotPassword, resetPassword } = useAuth();
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState<AuthView>('login');
  const [resetToken, setResetToken] = useState<string | null>(null);

  // Login form
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  // Register form
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirm, setRegConfirm] = useState('');
  const [regFullName, setRegFullName] = useState('');

  // Forgot password form
  const [forgotEmail, setForgotEmail] = useState('');

  // Reset password form
  const [resetNewPassword, setResetNewPassword] = useState('');
  const [resetConfirmPassword, setResetConfirmPassword] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginEmail || !loginPassword) {
      toast.error('Please fill in all fields');
      return;
    }
    setLoading(true);
    try {
      await login(loginEmail, loginPassword);
      toast.success('Logged in successfully');
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!regEmail || !regPassword) {
      toast.error('Please fill in all fields');
      return;
    }
    if (regPassword !== regConfirm) {
      toast.error('Passwords do not match');
      return;
    }
    if (regPassword.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }
    setLoading(true);
    try {
      await register(regEmail, regPassword, regFullName || undefined);
      toast.success('Account created successfully');
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!forgotEmail) {
      toast.error('Please enter your email');
      return;
    }
    setLoading(true);
    try {
      const result = await forgotPassword(forgotEmail);
      if (result.token) {
        setResetToken(result.token);
        toast.success('Reset token generated! Set your new password below.');
        setView('reset');
      } else {
        toast.success('If an account exists, a reset token has been generated. Check your email.');
        setForgotEmail('');
        setView('login');
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Request failed');
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetToken || !resetNewPassword) {
      toast.error('Please fill in all fields');
      return;
    }
    if (resetNewPassword.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }
    if (resetNewPassword !== resetConfirmPassword) {
      toast.error('Passwords do not match');
      return;
    }
    setLoading(true);
    try {
      await resetPassword(resetToken, resetNewPassword);
      toast.success('Password reset successfully! Please sign in.');
      setResetToken(null);
      setResetNewPassword('');
      setResetConfirmPassword('');
      setLoginEmail(forgotEmail);
      setView('login');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Password reset failed');
    } finally {
      setLoading(false);
    }
  };

  const switchView = (newView: AuthView) => {
    setView(newView);
    setResetToken(null);
  };

  const title = view === 'login' ? 'Sign In'
    : view === 'register' ? 'Create Account'
    : view === 'forgot' ? 'Reset Password'
    : 'Set New Password';

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>

        {view === 'login' && (
          <form onSubmit={handleLogin} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="login-email">Email</Label>
              <Input
                id="login-email"
                type="email"
                placeholder="you@example.com"
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="login-password">Password</Label>
              <Input
                id="login-password"
                type="password"
                placeholder="••••••••"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                required
              />
            </div>
            <div className="flex items-center justify-between gap-2">
              <Button type="submit" className="flex-1" disabled={loading}>
                {loading ? 'Signing in...' : 'Sign In'}
              </Button>
            </div>
            <div className="flex items-center justify-between text-sm">
              <button
                type="button"
                onClick={() => switchView('register')}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                No account? Register
              </button>
              <button
                type="button"
                onClick={() => {
                  setForgotEmail(loginEmail);
                  switchView('forgot');
                }}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                Forgot password?
              </button>
            </div>
          </form>
        )}

        {view === 'register' && (
          <form onSubmit={handleRegister} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="reg-name">Full Name</Label>
              <Input
                id="reg-name"
                type="text"
                placeholder="John Doe"
                value={regFullName}
                onChange={(e) => setRegFullName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="reg-email">Email</Label>
              <Input
                id="reg-email"
                type="email"
                placeholder="you@example.com"
                value={regEmail}
                onChange={(e) => setRegEmail(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="reg-password">Password</Label>
              <Input
                id="reg-password"
                type="password"
                placeholder="••••••••"
                value={regPassword}
                onChange={(e) => setRegPassword(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="reg-confirm">Confirm Password</Label>
              <Input
                id="reg-confirm"
                type="password"
                placeholder="••••••••"
                value={regConfirm}
                onChange={(e) => setRegConfirm(e.target.value)}
                required
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Creating account...' : 'Create Account'}
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => switchView('login')}
                className="underline hover:text-foreground transition-colors"
              >
                Sign in
              </button>
            </p>
          </form>
        )}

        {view === 'forgot' && (
          <form onSubmit={handleForgotPassword} className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Enter your email address and we&apos;ll generate a reset token for you.
            </p>
            <div className="space-y-2">
              <Label htmlFor="forgot-email">Email</Label>
              <Input
                id="forgot-email"
                type="email"
                placeholder="you@example.com"
                value={forgotEmail}
                onChange={(e) => setForgotEmail(e.target.value)}
                required
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Generating token...' : 'Send Reset Token'}
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              <button
                type="button"
                onClick={() => switchView('login')}
                className="underline hover:text-foreground transition-colors"
              >
                Back to sign in
              </button>
            </p>
          </form>
        )}

        {view === 'reset' && (
          <form onSubmit={handleResetPassword} className="space-y-4">
            <div className="rounded-md bg-muted p-3 text-sm">
              <p className="font-medium mb-1">Your reset token</p>
              <code className="block break-all text-xs bg-background rounded p-2 border">
                {resetToken}
              </code>
              <p className="text-xs text-muted-foreground mt-1">
                This token expires in 1 hour. Save it now — you won&apos;t see it again.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="reset-password">New Password</Label>
              <Input
                id="reset-password"
                type="password"
                placeholder="Min. 8 characters"
                value={resetNewPassword}
                onChange={(e) => setResetNewPassword(e.target.value)}
                required
                minLength={8}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="reset-confirm">Confirm New Password</Label>
              <Input
                id="reset-confirm"
                type="password"
                placeholder="••••••••"
                value={resetConfirmPassword}
                onChange={(e) => setResetConfirmPassword(e.target.value)}
                required
                minLength={8}
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Resetting...' : 'Reset Password'}
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              <button
                type="button"
                onClick={() => switchView('login')}
                className="underline hover:text-foreground transition-colors"
              >
                Back to sign in
              </button>
            </p>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
