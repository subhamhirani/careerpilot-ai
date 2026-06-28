'use client';

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { setAuthToken, clearAuthToken } from '@/lib/api';

interface User {
  user_id: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
  forgotPassword: (email: string) => Promise<{message: string; token: string | null}>;
  resetPassword: (token: string, newPassword: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

const API = typeof window !== 'undefined' ? window.location.origin : '';

async function apiPost(path: string, body: unknown): Promise<Record<string, unknown>> {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    let message = `HTTP ${res.status}`;
    if (typeof err.detail === 'string') {
      message = err.detail;
    } else if (Array.isArray(err.detail)) {
      message = err.detail[0]?.msg || `Validation error (HTTP ${res.status})`;
    } else if (err.message) {
      message = err.message;
    }
    throw new Error(message);
  }
  return res.json();
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [initialized, setInitialized] = useState(false);

  // Restore token from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem('careerpilot_token');
    if (stored) {
      setToken(stored);
      // Try to decode user info from JWT payload
      try {
        const payload = JSON.parse(atob(stored.split('.')[1]));
        if (payload.sub) {
          setUser({ user_id: payload.sub, email: payload.email || '' });
        }
      } catch {
        // Token exists but can't decode user — still set it
      }
    }
    setInitialized(true);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await apiPost('/api/auth/login', { email, password });
    const accessToken = data.access_token as string;
    localStorage.setItem('careerpilot_token', accessToken);
    setToken(accessToken);
    // Decode user from token
    try {
      const payload = JSON.parse(atob(accessToken.split('.')[1]));
      setUser({ user_id: payload.sub as string, email: payload.email as string || email });
    } catch {
      setUser({ user_id: '', email });
    }
    // Redirect new users to onboarding
    if (data.is_new_user) {
      if (typeof window !== 'undefined') {
        window.location.href = '/onboarding';
      }
    }
  }, []);

  const register = useCallback(async (email: string, password: string, fullName?: string) => {
    const data = await apiPost('/api/auth/register', { email, password, full_name: fullName });
    const accessToken = data.access_token as string;
    localStorage.setItem('careerpilot_token', accessToken);
    setToken(accessToken);
    setUser({
      user_id: data.user_id as string,
      email: data.email as string || email,
    });
    // New users go to onboarding
    if (typeof window !== 'undefined') {
      window.location.href = '/onboarding';
    }
  }, []);

  const forgotPassword = useCallback(async (email: string) => {
    return apiPost('/api/auth/forgot-password', { email }) as Promise<{message: string; token: string | null}>;
  }, []);

  const resetPassword = useCallback(async (token: string, newPassword: string) => {
    await apiPost('/api/auth/reset-password', { token, new_password: newPassword });
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('careerpilot_token');
    clearAuthToken();
    setUser(null);
    setToken(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated: !!token, login, register, logout, forgotPassword, resetPassword }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
