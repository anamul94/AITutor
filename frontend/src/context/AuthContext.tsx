'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';

interface User {
  id: number;
  email: string;
  is_active: boolean;
  is_admin: boolean;
  plan_type: 'free' | 'premium';
  trial_expires_at: string | null;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (token: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const loadUser = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          const res = await api.get('/auth/me');
          setUser(res.data);
        } catch (error) {
          console.error("Failed to fetch user", error);
          localStorage.removeItem('token');
        }
      }
      setLoading(false);
    };

    loadUser();
  }, []);

  const login = async (token: string) => {
    localStorage.setItem('token', token);
    try {
      const res = await api.get('/auth/me');
      setUser(res.data);
      router.push(res.data?.is_admin ? '/admin/dashboard' : '/dashboard');
    } catch (error) {
      console.error("Failed to fetch user during login", error);
      localStorage.removeItem('token');
    }
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } catch (error) {
      // Logout should still succeed locally even if server call fails.
      console.error('Failed to notify server during logout', error);
    } finally {
      localStorage.removeItem('token');
      setUser(null);
      router.push('/login');
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
