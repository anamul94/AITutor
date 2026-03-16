'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import axios from 'axios';
import { ArrowLeft, BookOpen, Eye, FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';

interface LessonQuizQuestion {
  question: string;
  options: string[];
  correct_answer_index: number;
  explanation: string;
}

interface LessonContent {
  id: number;
  course_id: number;
  title: string;
  description?: string | null;
  content: string | null;
  quiz_data?: LessonQuizQuestion[];
}

interface CourseModule {
  order_index: number;
  lessons: Array<{ id: number; order_index: number }>;
}

interface CourseData {
  title?: string;
  preferred_level?: 'beginner' | 'intermediate' | 'advanced' | null;
  content_style?: 'conceptual' | 'balanced' | 'practical';
  warnings?: string[];
  modules: CourseModule[];
}

export default function AdminLessonPage() {
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { user, loading } = useAuth();
  const [lesson, setLesson] = useState<LessonContent | null>(null);
  const [courseMeta, setCourseMeta] = useState<CourseData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const courseId = searchParams.get('courseId');
  const userId = searchParams.get('userId');

  const parseApiError = useCallback((err: unknown, fallbackMessage: string): string => (
    axios.isAxiosError(err)
      ? (err.response?.data?.detail as string) || fallbackMessage
      : fallbackMessage
  ), []);

  const fetchLessonData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError('');

      const { data } = await api.get<LessonContent>(`/api/admin/lessons/${id}`);
      setLesson(data);

      const resolvedCourseId = courseId ?? String(data.course_id);
      const courseRes = await api.get<CourseData>(`/api/admin/courses/${resolvedCourseId}`);
      setCourseMeta(courseRes.data);
    } catch (err: unknown) {
      setError(parseApiError(err, 'Failed to load lesson.'));
    } finally {
      setIsLoading(false);
    }
  }, [courseId, id, parseApiError]);

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
      fetchLessonData();
    }
  }, [fetchLessonData, id, loading, router, user]);

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
    <div className="min-h-screen bg-gray-950 text-white">
      <div className="sticky top-0 z-10 bg-gray-900/80 backdrop-blur-md border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <button
          onClick={() => router.push(courseId ? `/admin/courses/${courseId}${userId ? `?userId=${userId}` : ''}` : '/admin/dashboard')}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Course
        </button>
        <div className="flex items-center gap-2 text-blue-400 font-medium">
          <Eye className="w-4 h-4" />
          Admin Lesson View
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-12">
        {error && (
          <div className="mb-6 p-4 rounded-xl border border-red-500/50 bg-red-500/10 text-red-300">
            {error}
          </div>
        )}

        {courseMeta?.warnings && courseMeta.warnings.length > 0 && (
          <div className="mb-6 p-4 rounded-xl border border-amber-500/40 bg-amber-500/10 text-amber-200">
            {courseMeta.warnings[0]}
          </div>
        )}

        {lesson && (
          <>
            <header className="mb-10">
              <div className="flex flex-wrap items-center gap-2 mb-4">
                <span className="text-[11px] uppercase tracking-[0.2em] text-blue-300 bg-blue-500/10 border border-blue-500/20 rounded-full px-2.5 py-1">
                  Read Only
                </span>
                {courseMeta?.preferred_level && (
                  <span className="text-[11px] uppercase tracking-[0.18em] text-gray-300 bg-gray-900 border border-gray-800 rounded-full px-2.5 py-1">
                    {courseMeta.preferred_level}
                  </span>
                )}
                {courseMeta?.content_style && (
                  <span className="text-[11px] uppercase tracking-[0.18em] text-cyan-300 bg-cyan-500/10 border border-cyan-500/20 rounded-full px-2.5 py-1">
                    {courseMeta.content_style}
                  </span>
                )}
              </div>
              <h1 className="text-4xl md:text-5xl font-extrabold">{lesson.title}</h1>
              {lesson.description && (
                <p className="text-lg text-gray-400 mt-4">{lesson.description}</p>
              )}
              <p className="text-sm text-gray-500 mt-4">
                Admin can view existing lesson content and quiz only. Missing content stays missing.
              </p>
            </header>

            {lesson.content ? (
              <article className="prose prose-invert prose-blue max-w-none mb-16 prose-headings:text-blue-400 prose-a:text-blue-500 hover:prose-a:text-blue-400 prose-strong:text-white prose-code:text-pink-400 prose-pre:bg-gray-900 prose-pre:border prose-pre:border-gray-800 bg-gray-900/40 p-8 md:p-12 rounded-3xl border border-gray-800/60 shadow-xl leading-relaxed text-gray-300">
                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                  {lesson.content}
                </ReactMarkdown>
              </article>
            ) : (
              <div className="mb-16 rounded-3xl border border-amber-500/30 bg-amber-500/10 p-8 text-amber-100">
                <div className="flex items-center gap-3 mb-3">
                  <FileText className="w-5 h-5" />
                  <h2 className="text-xl font-semibold">Lesson Not Generated</h2>
                </div>
                <p>
                  This lesson does not have generated content yet. Admin view does not trigger lesson generation.
                </p>
              </div>
            )}

            <section className="bg-gray-900 rounded-2xl border border-gray-800 p-8">
              <div className="flex items-center gap-3 mb-4">
                <BookOpen className="w-5 h-5 text-blue-400" />
                <h2 className="text-2xl font-bold">Quiz</h2>
              </div>

              {lesson.quiz_data && lesson.quiz_data.length > 0 ? (
                <div className="space-y-6">
                  {lesson.quiz_data.map((question, index) => (
                    <div key={index} className="rounded-xl border border-gray-800 bg-gray-950/40 p-5">
                      <p className="text-white font-medium mb-4">
                        {index + 1}. {question.question}
                      </p>
                      <div className="space-y-2 mb-4">
                        {question.options.map((option, optionIndex) => (
                          <div
                            key={optionIndex}
                            className={`rounded-lg border px-4 py-3 text-sm ${optionIndex === question.correct_answer_index ? 'border-green-500/40 bg-green-500/10 text-green-300' : 'border-gray-800 bg-gray-900 text-gray-300'}`}
                          >
                            {option}
                          </div>
                        ))}
                      </div>
                      <p className="text-sm text-blue-200">
                        <span className="font-semibold text-blue-400">Explanation:</span> {question.explanation}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-xl border border-gray-800 bg-gray-950/40 p-5 text-gray-400">
                  No quiz has been generated for this lesson. Admin view does not generate a new quiz.
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}
