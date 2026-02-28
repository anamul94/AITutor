'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { ShieldCheck, Users, UserPlus, Activity, BookOpen, GraduationCap, Coins, RefreshCw, LogOut, Loader2 } from 'lucide-react';
import axios from 'axios';
import api from '@/lib/api';
import { useAuth } from '@/context/AuthContext';

interface AdminStats {
  total_users: number;
  users_registered_today: number;
  active_users: number;
  courses_generated_today: number;
  lessons_generated_today: number;
  total_content_generated_today: number;
  total_token_usage: number;
  token_usage_today: number;
}

interface AdminUser {
  id: number;
  email: string;
  is_active: boolean;
  is_admin: boolean;
  plan_type: 'free' | 'premium';
  trial_expires_at: string | null;
  created_at: string;
}

interface DailyRegistrationStat {
  date: string;
  user_count: number;
}

interface TokenUsageByUserStat {
  user_id: number;
  email: string;
  total_tokens: number;
  token_usage_today: number;
}

interface AdminInsights {
  lookback_days: number;
  daily_registrations: DailyRegistrationStat[];
  today_registered_users: AdminUser[];
  token_usage_per_user: TokenUsageByUserStat[];
}

interface AdminTrialDaysResponse {
  premium_trial_days: number;
}

const numberFormatter = new Intl.NumberFormat('en-US');

export default function AdminDashboardPage() {
  const router = useRouter();
  const { user, loading, logout } = useAuth();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [insights, setInsights] = useState<AdminInsights | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [premiumTrialDays, setPremiumTrialDays] = useState<number>(1);
  const [premiumTrialDaysDraft, setPremiumTrialDaysDraft] = useState<string>('1');
  const [isLoadingStats, setIsLoadingStats] = useState(false);
  const [isLoadingInsights, setIsLoadingInsights] = useState(false);
  const [isLoadingUsers, setIsLoadingUsers] = useState(false);
  const [isLoadingTrialDays, setIsLoadingTrialDays] = useState(false);
  const [isSavingTrialDays, setIsSavingTrialDays] = useState(false);
  const [updatingUserId, setUpdatingUserId] = useState<number | null>(null);
  const [error, setError] = useState('');

  const parseApiError = useCallback((err: unknown, fallbackMessage: string): string => (
    axios.isAxiosError(err)
      ? (err.response?.data?.detail as string) || fallbackMessage
      : fallbackMessage
  ), []);

  const fetchStats = useCallback(async () => {
    setIsLoadingStats(true);
    setError('');
    try {
      const { data } = await api.get<AdminStats>('/api/admin/stats');
      setStats(data);
    } catch (err: unknown) {
      setError(parseApiError(err, 'Failed to load admin statistics.'));
    } finally {
      setIsLoadingStats(false);
    }
  }, [parseApiError]);

  const fetchInsights = useCallback(async () => {
    setIsLoadingInsights(true);
    setError('');
    try {
      const { data } = await api.get<AdminInsights>('/api/admin/insights?days=14');
      setInsights(data);
    } catch (err: unknown) {
      setError(parseApiError(err, 'Failed to load dashboard insights.'));
    } finally {
      setIsLoadingInsights(false);
    }
  }, [parseApiError]);

  const fetchUsers = useCallback(async () => {
    setIsLoadingUsers(true);
    setError('');
    try {
      const { data } = await api.get<AdminUser[]>('/api/admin/users');
      setUsers(data);
    } catch (err: unknown) {
      setError(parseApiError(err, 'Failed to load users.'));
    } finally {
      setIsLoadingUsers(false);
    }
  }, [parseApiError]);

  const fetchTrialDays = useCallback(async () => {
    setIsLoadingTrialDays(true);
    setError('');
    try {
      const { data } = await api.get<AdminTrialDaysResponse>('/api/admin/settings/trial-days');
      setPremiumTrialDays(data.premium_trial_days);
      setPremiumTrialDaysDraft(String(data.premium_trial_days));
    } catch (err: unknown) {
      setError(parseApiError(err, 'Failed to load trial days setting.'));
    } finally {
      setIsLoadingTrialDays(false);
    }
  }, [parseApiError]);

  const handleSaveTrialDays = useCallback(async () => {
    const parsed = Number.parseInt(premiumTrialDaysDraft, 10);
    if (!Number.isFinite(parsed) || parsed < 0 || parsed > 365) {
      setError('Trial days must be between 0 and 365.');
      return;
    }

    setIsSavingTrialDays(true);
    setError('');
    try {
      const { data } = await api.put<AdminTrialDaysResponse>('/api/admin/settings/trial-days', {
        premium_trial_days: parsed,
      });
      setPremiumTrialDays(data.premium_trial_days);
      setPremiumTrialDaysDraft(String(data.premium_trial_days));
    } catch (err: unknown) {
      setError(parseApiError(err, 'Failed to update trial days setting.'));
    } finally {
      setIsSavingTrialDays(false);
    }
  }, [premiumTrialDaysDraft, parseApiError]);

  const handleUserPlanChange = useCallback(async (targetUser: AdminUser, planType: 'free' | 'premium') => {
    if (targetUser.is_admin || targetUser.plan_type === planType) {
      return;
    }

    setUpdatingUserId(targetUser.id);
    setError('');
    try {
      const { data } = await api.patch<AdminUser>(`/api/admin/users/${targetUser.id}/plan`, { plan_type: planType });
      setUsers((prevUsers) => prevUsers.map((prevUser) => (prevUser.id === data.id ? data : prevUser)));
    } catch (err: unknown) {
      setError(parseApiError(err, 'Failed to update user plan.'));
    } finally {
      setUpdatingUserId(null);
    }
  }, [parseApiError]);

  const handleUserStatusChange = useCallback(async (targetUser: AdminUser, isActive: boolean) => {
    if (targetUser.is_admin || targetUser.is_active === isActive) {
      return;
    }

    setUpdatingUserId(targetUser.id);
    setError('');
    try {
      const { data } = await api.patch<AdminUser>(`/api/admin/users/${targetUser.id}/status`, { is_active: isActive });
      setUsers((prevUsers) => prevUsers.map((prevUser) => (prevUser.id === data.id ? data : prevUser)));
    } catch (err: unknown) {
      setError(parseApiError(err, 'Failed to update user status.'));
    } finally {
      setUpdatingUserId(null);
    }
  }, [parseApiError]);

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
      return;
    }
    if (user && !user.is_admin) {
      router.push('/dashboard');
      return;
    }
    if (user?.is_admin) {
      fetchStats();
      fetchInsights();
      fetchUsers();
      fetchTrialDays();
    }
  }, [loading, user, router, fetchStats, fetchInsights, fetchUsers, fetchTrialDays]);

  if (loading || !user || (user.is_admin && !stats && isLoadingStats)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="w-8 h-8 border-4 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (!user.is_admin) {
    return null;
  }

  const cardData = [
    { label: 'Total Users', value: numberFormatter.format(stats?.total_users ?? 0), icon: <Users className="w-5 h-5 text-cyan-300" /> },
    { label: 'Registered Today', value: numberFormatter.format(stats?.users_registered_today ?? 0), icon: <UserPlus className="w-5 h-5 text-emerald-300" /> },
    { label: 'Active Users Today', value: numberFormatter.format(stats?.active_users ?? 0), icon: <Activity className="w-5 h-5 text-lime-300" /> },
    { label: 'Courses Today', value: numberFormatter.format(stats?.courses_generated_today ?? 0), icon: <BookOpen className="w-5 h-5 text-indigo-300" /> },
    { label: 'Lessons Today', value: numberFormatter.format(stats?.lessons_generated_today ?? 0), icon: <GraduationCap className="w-5 h-5 text-fuchsia-300" /> },
    { label: 'Content Today', value: numberFormatter.format(stats?.total_content_generated_today ?? 0), icon: <ShieldCheck className="w-5 h-5 text-amber-300" /> },
    { label: 'Token Usage (Today)', value: numberFormatter.format(stats?.token_usage_today ?? 0), icon: <Coins className="w-5 h-5 text-orange-300" /> },
    { label: 'Token Usage (Total)', value: numberFormatter.format(stats?.total_token_usage ?? 0), icon: <Coins className="w-5 h-5 text-rose-300" /> },
  ];

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6 md:p-10">
      <div className="max-w-6xl mx-auto">
        <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <p className="inline-flex items-center gap-2 text-emerald-300 text-sm font-medium mb-2">
              <ShieldCheck className="w-4 h-4" />
              Admin Control Panel
            </p>
            <h1 className="text-3xl font-bold">Platform Statistics</h1>
            <p className="text-gray-400 mt-2">{user.email}</p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                fetchStats();
                fetchInsights();
                fetchUsers();
                fetchTrialDays();
              }}
              disabled={isLoadingStats || isLoadingInsights || isLoadingUsers || isLoadingTrialDays}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-gray-700 bg-gray-900 hover:bg-gray-800 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw className={`w-4 h-4 ${(isLoadingStats || isLoadingInsights || isLoadingUsers || isLoadingTrialDays) ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              onClick={logout}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-red-500/30 bg-red-500/10 hover:bg-red-500/20 text-red-200 text-sm"
            >
              <LogOut className="w-4 h-4" />
              Sign Out
            </button>
          </div>
        </header>

        {error && (
          <div className="mb-6 p-3 rounded-lg border border-red-500/40 bg-red-500/10 text-red-300 text-sm">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {cardData.map((item, idx) => (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, delay: idx * 0.03 }}
              className="rounded-2xl border border-gray-800 bg-gray-900 p-5"
            >
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm text-gray-400">{item.label}</p>
                <div className="w-9 h-9 rounded-lg bg-gray-800 border border-gray-700 flex items-center justify-center">
                  {item.icon}
                </div>
              </div>
              <p className="text-2xl font-bold">{item.value}</p>
            </motion.div>
          ))}
        </div>

        <section className="mt-8 grid grid-cols-1 xl:grid-cols-2 gap-6">
          <div className="rounded-2xl border border-gray-800 bg-gray-900 p-6">
            <h2 className="text-xl font-semibold mb-4">Premium Trial Days</h2>
            <p className="text-sm text-gray-400 mb-4">
              Controls how many premium trial days new users receive at registration.
            </p>
            <div className="flex items-end gap-3">
              <div className="flex-1">
                <label className="block text-xs text-gray-400 mb-2">Days (0-365)</label>
                <input
                  type="number"
                  min={0}
                  max={365}
                  value={premiumTrialDaysDraft}
                  onChange={(e) => setPremiumTrialDaysDraft(e.target.value)}
                  disabled={isLoadingTrialDays || isSavingTrialDays}
                  className="w-full bg-gray-950 border border-gray-700 text-white rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                />
              </div>
              <button
                onClick={handleSaveTrialDays}
                disabled={isLoadingTrialDays || isSavingTrialDays}
                className="px-4 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-2"
              >
                {isSavingTrialDays && <Loader2 className="w-4 h-4 animate-spin" />}
                Save
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-3">
              Current value: {premiumTrialDays} day(s)
            </p>
          </div>

          <div className="rounded-2xl border border-gray-800 bg-gray-900 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Date-wise Registrations (14 days)</h2>
              {isLoadingInsights && <Loader2 className="w-4 h-4 animate-spin text-gray-400" />}
            </div>
            <div className="space-y-2">
              {(insights?.daily_registrations ?? []).map((item) => (
                <div key={item.date} className="grid grid-cols-[120px_1fr_60px] items-center gap-3 text-sm">
                  <span className="text-gray-400">{item.date}</span>
                  <div className="h-2 rounded bg-gray-800 overflow-hidden">
                    <div
                      className="h-full bg-emerald-500"
                      style={{
                        width: `${Math.min(
                          100,
                          ((item.user_count / Math.max(...(insights?.daily_registrations.map((r) => r.user_count) ?? [1]), 1)) * 100)
                        )}%`,
                      }}
                    />
                  </div>
                  <span className="text-right text-gray-200">{item.user_count}</span>
                </div>
              ))}
              {(!insights || insights.daily_registrations.length === 0) && (
                <p className="text-sm text-gray-400">No registration data available.</p>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-gray-800 bg-gray-900 p-6">
            <h2 className="text-xl font-semibold mb-4">Today Registered Users</h2>
            {insights?.today_registered_users?.length ? (
              <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                {insights.today_registered_users.map((u) => (
                  <div key={u.id} className="flex items-center justify-between rounded-lg bg-gray-800/60 px-3 py-2">
                    <span className="text-sm text-white">{u.email}</span>
                    <span className="text-xs text-gray-400">{new Date(u.created_at).toLocaleTimeString()}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400">No users registered today.</p>
            )}
          </div>
        </section>

        <section className="mt-8 rounded-2xl border border-gray-800 bg-gray-900 p-6">
          <h2 className="text-xl font-semibold mb-4">Token Usage Per User</h2>
          {insights?.token_usage_per_user?.length ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-gray-800">
                    <th className="py-3 pr-4 font-medium">Email</th>
                    <th className="py-3 pr-4 font-medium">Today</th>
                    <th className="py-3 font-medium">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {insights.token_usage_per_user.map((entry) => (
                    <tr key={entry.user_id} className="border-b border-gray-800/70 last:border-b-0">
                      <td className="py-3 pr-4 text-white">{entry.email}</td>
                      <td className="py-3 pr-4 text-gray-300">{numberFormatter.format(entry.token_usage_today)}</td>
                      <td className="py-3 text-gray-100 font-medium">{numberFormatter.format(entry.total_tokens)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-gray-400">No token usage data yet.</p>
          )}
        </section>

        <section className="mt-8 rounded-2xl border border-gray-800 bg-gray-900 p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-xl font-semibold">User Plan & Status Management</h2>
            {isLoadingUsers && (
              <div className="text-xs text-gray-400 inline-flex items-center gap-2">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Loading users
              </div>
            )}
          </div>

          {users.length === 0 && !isLoadingUsers ? (
            <p className="text-sm text-gray-400">No users found.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-gray-800">
                    <th className="py-3 pr-4 font-medium">Email</th>
                    <th className="py-3 pr-4 font-medium">Role</th>
                    <th className="py-3 pr-4 font-medium">Status</th>
                    <th className="py-3 pr-4 font-medium">Current Plan</th>
                    <th className="py-3 pr-4 font-medium">Joined</th>
                    <th className="py-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((accountUser) => {
                    const isUpdatingRow = updatingUserId === accountUser.id;
                    const joinedDate = new Date(accountUser.created_at).toLocaleDateString();

                    return (
                      <tr key={accountUser.id} className="border-b border-gray-800/70 last:border-b-0">
                        <td className="py-3 pr-4">
                          <div className="font-medium text-white">{accountUser.email}</div>
                        </td>
                        <td className="py-3 pr-4">
                          {accountUser.is_admin ? (
                            <span className="px-2 py-1 rounded-md bg-emerald-500/20 text-emerald-300 text-xs font-semibold">Admin</span>
                          ) : (
                            <span className="px-2 py-1 rounded-md bg-gray-800 text-gray-300 text-xs font-semibold">User</span>
                          )}
                        </td>
                        <td className="py-3 pr-4">
                          {accountUser.is_active ? (
                            <span className="px-2 py-1 rounded-md bg-emerald-500/20 text-emerald-300 text-xs font-semibold">Active</span>
                          ) : (
                            <span className="px-2 py-1 rounded-md bg-red-500/20 text-red-300 text-xs font-semibold">Inactive</span>
                          )}
                        </td>
                        <td className="py-3 pr-4">
                          {accountUser.plan_type === 'premium' ? (
                            <span className="px-2 py-1 rounded-md bg-blue-500/20 text-blue-300 text-xs font-semibold">Premium</span>
                          ) : (
                            <span className="px-2 py-1 rounded-md bg-amber-500/20 text-amber-300 text-xs font-semibold">Free</span>
                          )}
                        </td>
                        <td className="py-3 pr-4 text-gray-300">{joinedDate}</td>
                        <td className="py-3">
                          <div className="flex flex-wrap gap-2">
                            <button
                              onClick={() => handleUserPlanChange(accountUser, 'premium')}
                              disabled={accountUser.is_admin || isUpdatingRow || accountUser.plan_type === 'premium'}
                              className="px-3 py-1.5 rounded-lg text-xs font-medium border border-blue-500/40 text-blue-200 bg-blue-500/10 hover:bg-blue-500/20 disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                              Premium
                            </button>
                            <button
                              onClick={() => handleUserPlanChange(accountUser, 'free')}
                              disabled={accountUser.is_admin || isUpdatingRow || accountUser.plan_type === 'free'}
                              className="px-3 py-1.5 rounded-lg text-xs font-medium border border-amber-500/40 text-amber-200 bg-amber-500/10 hover:bg-amber-500/20 disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                              Free
                            </button>
                            <button
                              onClick={() => handleUserStatusChange(accountUser, true)}
                              disabled={accountUser.is_admin || isUpdatingRow || accountUser.is_active}
                              className="px-3 py-1.5 rounded-lg text-xs font-medium border border-emerald-500/40 text-emerald-200 bg-emerald-500/10 hover:bg-emerald-500/20 disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                              Activate
                            </button>
                            <button
                              onClick={() => handleUserStatusChange(accountUser, false)}
                              disabled={accountUser.is_admin || isUpdatingRow || !accountUser.is_active}
                              className="px-3 py-1.5 rounded-lg text-xs font-medium border border-red-500/40 text-red-200 bg-red-500/10 hover:bg-red-500/20 disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                              Deactivate
                            </button>
                            {isUpdatingRow && <Loader2 className="w-4 h-4 animate-spin text-gray-300 self-center" />}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
