'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import axios from 'axios';
import { ArrowLeft, BookOpen, ChevronRight, Eye, FileText } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';

interface LessonItem {
  id: number;
  title: string;
  description?: string | null;
  order_index: number;
  content_generated_at?: string | null;
}

interface ModuleItem {
  id: number;
  title: string;
  order_index: number;
  lessons: LessonItem[];
}

interface CourseData {
  id: number;
  title: string;
  description: string;
  preferred_level?: 'beginner' | 'intermediate' | 'advanced' | null;
  content_style?: 'conceptual' | 'balanced' | 'practical';
  warnings?: string[];
  progress_percentage: number;
  modules: ModuleItem[];
}

export default function AdminCoursePage() {
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { user, loading } = useAuth();
  const [course, setCourse] = useState<CourseData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const userId = searchParams.get('userId');

  const parseApiError = useCallback((err: unknown, fallbackMessage: string): string => (
    axios.isAxiosError(err)
      ? (err.response?.data?.detail as string) || fallbackMessage
      : fallbackMessage
  ), []);

  const fetchCourse = useCallback(async () => {
    try {
      setIsLoading(true);
      setError('');
      const { data } = await api.get<CourseData>(`/api/admin/courses/${id}`);
      setCourse(data);
    } catch (err: unknown) {
      setError(parseApiError(err, 'Failed to load course.'));
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
      fetchCourse();
    }
  }, [fetchCourse, id, loading, router, user]);

  const sortedModules = useMemo(() => {
    if (!course) {
      return [];
    }
    return course.modules
      .slice()
      .sort((a, b) => a.order_index - b.order_index)
      .map((module) => ({
        ...module,
        lessons: module.lessons.slice().sort((a, b) => a.order_index - b.order_index),
      }));
  }, [course]);

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
    <div className="min-h-screen bg-gray-950 text-white p-6 md:p-12">
      <div className="max-w-5xl mx-auto">
        <button
          onClick={() => router.push(userId ? `/admin/users/${userId}` : '/admin/dashboard')}
          className="inline-flex items-center gap-2 text-gray-400 hover:text-white transition-colors border border-gray-800 bg-gray-900 rounded-xl px-4 py-2 mb-8"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>

        {error && (
          <div className="mb-6 p-4 rounded-xl border border-red-500/40 bg-red-500/10 text-red-300">
            {error}
          </div>
        )}

        {course && (
          <>
            <header className="mb-10 rounded-3xl border border-gray-800 bg-gray-900 p-6 md:p-8">
              <div className="flex flex-wrap items-center gap-3 text-blue-300 mb-4 font-medium text-sm">
                <Eye className="w-4 h-4" />
                <span>Admin Read-Only Course View</span>
                {course.preferred_level && (
                  <span className="text-[11px] uppercase tracking-[0.18em] text-gray-300 bg-gray-950 px-3 py-1 rounded-full border border-gray-800">
                    {course.preferred_level}
                  </span>
                )}
                {course.content_style && (
                  <span className="text-[11px] uppercase tracking-[0.18em] text-cyan-300 bg-cyan-500/10 px-3 py-1 rounded-full border border-cyan-500/20">
                    {course.content_style}
                  </span>
                )}
              </div>
              <h1 className="text-4xl md:text-5xl font-extrabold">{course.title}</h1>
              <p className="text-lg text-gray-400 leading-relaxed mt-4">{course.description}</p>
              {course.warnings && course.warnings.length > 0 && (
                <div className="mt-5 rounded-2xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
                  {course.warnings[0]}
                </div>
              )}
            </header>

            <div className="space-y-8">
              {sortedModules.map((module) => (
                <div key={module.id} className="bg-gray-900 rounded-2xl border border-gray-800 overflow-hidden">
                  <div className="p-6 border-b border-gray-800 bg-gray-900/50">
                    <p className="text-sm font-medium text-blue-500 mb-1">Module {module.order_index}</p>
                    <h2 className="text-xl font-bold">{module.title}</h2>
                  </div>

                  <div className="divide-y divide-gray-800">
                    {module.lessons.map((lesson) => {
                      const isGenerated = Boolean(lesson.content_generated_at);

                      return (
                        <button
                          key={lesson.id}
                          onClick={() => router.push(`/admin/lessons/${lesson.id}?courseId=${course.id}${userId ? `&userId=${userId}` : ''}`)}
                          className="w-full text-left p-5 flex items-center justify-between hover:bg-gray-800/50 transition-colors group"
                        >
                          <div className="flex items-center gap-4">
                            <div className={`w-10 h-10 rounded-full flex items-center justify-center border ${isGenerated ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300' : 'border-gray-700 bg-gray-950 text-gray-500'}`}>
                              {isGenerated ? <BookOpen className="w-4 h-4" /> : <FileText className="w-4 h-4" />}
                            </div>
                            <div>
                              <p className="text-sm text-gray-400 mb-1">Lesson {module.order_index}.{lesson.order_index}</p>
                              <h3 className="font-medium group-hover:text-white">{lesson.title}</h3>
                              {lesson.description && (
                                <p className="text-sm text-gray-500 mt-1 line-clamp-2 max-w-2xl">
                                  {lesson.description}
                                </p>
                              )}
                              <p className={`text-xs mt-2 ${isGenerated ? 'text-emerald-300' : 'text-amber-300'}`}>
                                {isGenerated ? 'Generated content available' : 'Not generated yet, admin can only preview metadata'}
                              </p>
                            </div>
                          </div>
                          <ChevronRight className="w-5 h-5 text-gray-600 group-hover:text-blue-500 transition-colors" />
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
