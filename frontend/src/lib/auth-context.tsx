'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface AuthContextType {
  isAuthenticated: boolean;
  isLoadingAuth: boolean;
  user: any | null;
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>;
  register: (fullName: string, email: string, password: string) => Promise<void>;
  forgotPassword: (email: string) => Promise<string | null>;
  resetPassword: (token: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  isLoadingAuth: true,
  user: null,
  login: async () => {},
  register: async () => {},
  forgotPassword: async () => null,
  resetPassword: async () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoadingAuth, setIsLoadingAuth] = useState(true);
  const [user, setUser] = useState(null);

  const clearTokens = () => {
    if (typeof window === 'undefined') return;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('careerpilot_token');
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('refresh_token');
    sessionStorage.removeItem('careerpilot_token');
  };

  useEffect(() => {
    let isMounted = true;

    const verifySession = async () => {
      const token =
        sessionStorage.getItem('access_token') ||
        localStorage.getItem('access_token') ||
        sessionStorage.getItem('careerpilot_token') ||
        localStorage.getItem('careerpilot_token');

      if (!token) {
        if (isMounted) {
          setIsAuthenticated(false);
          setUser(null);
          setIsLoadingAuth(false);
        }
        return;
      }

      try {
        const res = await fetch('/api/auth/me', {
          method: 'GET',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (res.ok) {
          const data = await res.json();
          if (isMounted) {
            setUser(data);
            setIsAuthenticated(true);
            setIsLoadingAuth(false);
          }
        } else {
          clearTokens();
          if (isMounted) {
            setIsAuthenticated(false);
            setUser(null);
            setIsLoadingAuth(false);
          }
        }
      } catch (e) {
        clearTokens();
        if (isMounted) {
          setIsAuthenticated(false);
          setUser(null);
          setIsLoadingAuth(false);
        }
      }
    };

    verifySession();

    const handleUnauthorized = () => {
      clearTokens();
      if (isMounted) {
        setIsAuthenticated(false);
        setUser(null);
        setIsLoadingAuth(false);
      }
    };

    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => {
      isMounted = false;
      window.removeEventListener('auth:unauthorized', handleUnauthorized);
    };
  }, []);

  const login = async (email: string, password: string, rememberMe = false) => {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const error = await res.text();
      throw new Error(error || 'Login failed');
    }

    const data = await res.json();
    clearTokens();

    if (rememberMe) {
      localStorage.setItem('access_token', data.access_token);
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token);
      }
    } else {
      sessionStorage.setItem('access_token', data.access_token);
      if (data.refresh_token) {
        sessionStorage.setItem('refresh_token', data.refresh_token);
      }
    }
    setIsAuthenticated(true);
    setUser(data.user || { email });
  };

  const register = async (fullName: string, email: string, password: string) => {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ full_name: fullName, email, password }),
    });

    if (!res.ok) {
      const error = await res.text();
      throw new Error(error || 'Registration failed');
    }

    const data = await res.json();
    clearTokens();
    sessionStorage.setItem('access_token', data.access_token);
    if (data.refresh_token) {
      sessionStorage.setItem('refresh_token', data.refresh_token);
    }
    setIsAuthenticated(true);
    setUser(data.user || { email });
  };

  const forgotPassword = async (email: string): Promise<string | null> => {
    const res = await fetch('/api/auth/forgot-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });

    if (!res.ok) {
      const error = await res.text();
      throw new Error(error || 'Failed to send reset email');
    }

    const data = await res.json();
    return data.token || null;
  };

  const resetPassword = async (token: string, password: string) => {
    const res = await fetch('/api/auth/reset-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, new_password: password }),
    });

    if (!res.ok) {
      const error = await res.text();
      throw new Error(error || 'Failed to reset password');
    }
  };

  const logout = () => {
    clearTokens();
    setIsAuthenticated(false);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoadingAuth, user, login, register, forgotPassword, resetPassword, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
