'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import axios from 'axios';
import { ArrowLeft, BookOpen, ChevronRight, Clock, UserRound } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';

interface AdminUser {
  id: number;
  email: string;
  is_active: boolean;
  is_admin: boolean;
  plan_type: 'free' | 'premium';
  trial_expires_at: string | null;
  created_at: string;
}

interface LessonItem {
  id: number;
}

interface ModuleItem {
  lessons: LessonItem[];
}

interface CourseData {
  id: number;
  title: string;
  description: string;
  topic: string;
  progress_percentage: number;
  modules: ModuleItem[];
}

export default function AdminUserCoursesPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { user, loading } = useAuth();
  const [targetUser, setTargetUser] = useState<AdminUser | null>(null);
  const [courses, setCourses] = useState<CourseData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const parseApiError = useCallback((err: unknown, fallbackMessage: string): string => (
    axios.isAxiosError(err)
      ? (err.response?.data?.detail as string) || fallbackMessage
      : fallbackMessage
  ), []);

  const fetchPageData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError('');

      const [{ data: users }, { data: userCourses }] = await Promise.all([
        api.get<AdminUser[]>('/api/admin/users'),
        api.get<CourseData[]>(`/api/admin/users/${id}/courses`),
      ]);

      const matchedUser = users.find((entry) => String(entry.id) === String(id) && !entry.is_admin) ?? null;
      if (!matchedUser) {
        setError('User not found.');
        return;
      }

      setTargetUser(matchedUser);
      setCourses(userCourses);
    } catch (err: unknown) {
      setError(parseApiError(err, 'Failed to load user courses.'));
    } finally {
      setIsLoading(false);
    }
  }, [id, parseApiError]);

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
      return;
    }
    if (user && !user.is_admin) {
      router.push('/dashboard');
      return;
    }
    if (user?.is_admin && id) {
      fetchPageData();
    }
  }, [fetchPageData, id, loading, router, user]);

  const totalLessons = useMemo(
    () => courses.reduce((sum, course) => sum + course.modules.reduce((moduleSum, module) => moduleSum + module.lessons.length, 0), 0),
    [courses],
  );

  if (loading || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (!user?.is_admin) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6 md:p-10">
      <div className="max-w-6xl mx-auto">
        <button
          onClick={() => router.push('/admin/dashboard')}
          className="inline-flex items-center gap-2 text-gray-400 hover:text-white transition-colors border border-gray-800 bg-gray-900 rounded-xl px-4 py-2 mb-8"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Admin Dashboard
        </button>

        {error && (
          <div className="mb-6 p-4 rounded-xl border border-red-500/40 bg-red-500/10 text-red-300">
            {error}
          </div>
        )}

        {targetUser && (
          <header className="mb-8 rounded-3xl border border-gray-800 bg-gray-900 p-6 md:p-8">
            <div className="flex flex-wrap items-center gap-3 text-blue-300 text-sm font-medium mb-3">
              <UserRound className="w-4 h-4" />
              <span>Admin View Only</span>
            </div>
            <h1 className="text-3xl md:text-4xl font-bold break-all">{targetUser.email}</h1>
            <p className="text-gray-400 mt-3">
              Browse this user&apos;s courses and generated lessons without editing, generating, or marking progress.
            </p>
            <div className="flex flex-wrap gap-3 mt-5 text-sm">
              <span className="px-3 py-1.5 rounded-lg bg-gray-950 border border-gray-800 text-gray-300">
                {courses.length} Course{courses.length === 1 ? '' : 's'}
              </span>
              <span className="px-3 py-1.5 rounded-lg bg-gray-950 border border-gray-800 text-gray-300">
                {totalLessons} Lesson{totalLessons === 1 ? '' : 's'}
              </span>
              <span className={`px-3 py-1.5 rounded-lg ${targetUser.is_active ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300' : 'bg-red-500/10 border border-red-500/30 text-red-300'}`}>
                {targetUser.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>
          </header>
        )}

        {courses.length === 0 && !error ? (
          <div className="rounded-2xl border border-gray-800 bg-gray-900 p-8 text-gray-400">
            This user has no courses yet.
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {courses.map((course) => {
              const lessonCount = course.modules.reduce((sum, module) => sum + module.lessons.length, 0);

              return (
                <button
                  key={course.id}
                  onClick={() => router.push(`/admin/courses/${course.id}?userId=${id}`)}
                  className="text-left rounded-3xl border border-gray-800 bg-gray-900 hover:border-blue-500/40 hover:bg-gray-900/80 transition-colors p-6"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-blue-300 mb-3">
                        <BookOpen className="w-4 h-4" />
                        Course
                      </div>
                      <h2 className="text-2xl font-bold">{course.title}</h2>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-500" />
                  </div>
                  <p className="text-gray-400 mt-4 line-clamp-3">{course.description}</p>
                  <div className="flex flex-wrap gap-3 mt-5 text-sm">
                    <span className="inline-flex items-center gap-2 rounded-lg border border-gray-800 bg-gray-950 px-3 py-1.5 text-gray-300">
                      <Clock className="w-4 h-4" />
                      {course.modules.length} Module{course.modules.length === 1 ? '' : 's'}
                    </span>
                    <span className="inline-flex items-center gap-2 rounded-lg border border-gray-800 bg-gray-950 px-3 py-1.5 text-gray-300">
                      <BookOpen className="w-4 h-4" />
                      {lessonCount} Lesson{lessonCount === 1 ? '' : 's'}
                    </span>
                    <span className="inline-flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3 py-1.5 text-emerald-300">
                      {course.progress_percentage}% Complete
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
