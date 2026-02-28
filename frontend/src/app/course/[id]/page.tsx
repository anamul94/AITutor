'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { ChevronRight, PlayCircle, CheckCircle2, ArrowLeft, BookOpen, Clock } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';

export default function CoursePage() {
  const { id } = useParams();
  const router = useRouter();
  const { user, loading } = useAuth();
  const [course, setCourse] = useState<any>(null);
  const [progress, setProgress] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!loading && !user) router.push('/login');
    if (user && id) {
      fetchCourse();
      fetchProgress();
    }
  }, [user, id, loading]);

  const fetchCourse = async () => {
    try {
      const { data } = await api.get(`/api/courses/${id}`);
      setCourse(data);
    } catch (err) {
      console.error("Failed to fetch course", err);
      router.push('/dashboard');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchProgress = async () => {
    try {
      const { data } = await api.get(`/api/courses/${id}/progress`);
      setProgress(data);
    } catch (err) {
      console.error("Failed to fetch progress", err);
    }
  };

  if (isLoading || !course) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6 md:p-12">
      <div className="max-w-4xl mx-auto">
        <button
          onClick={() => router.push('/dashboard')}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors border border-gray-800 bg-gray-900 rounded-xl px-4 py-2 mb-8"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </button>

        <header className="mb-12">
          <div className="flex items-center gap-3 text-blue-500 mb-4 font-medium text-sm">
            <BookOpen className="w-5 h-5" />
            <span>AI Generated Course</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
            {course.title}
          </h1>
          <p className="text-xl text-gray-400 leading-relaxed mb-6">
            {course.description}
          </p>
          <div className="flex items-center gap-4 text-sm text-gray-500">
            <span className="flex items-center gap-2 bg-gray-900 px-3 py-1.5 rounded-lg border border-gray-800">
              <Clock className="w-4 h-4" /> {course.modules.length} Modules
            </span>
          </div>
        </header>

        <div className="space-y-8">
          {course.modules.map((module: any) => (
            <div key={module.id} className="bg-gray-900 rounded-2xl border border-gray-800 overflow-hidden">
              <div className="p-6 border-b border-gray-800 bg-gray-900/50 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-blue-500 mb-1">Module {module.order_index}</p>
                  <h3 className="text-xl font-bold">{module.title}</h3>
                </div>
              </div>

              <div className="divide-y divide-gray-800">
                {module.lessons.map((lesson: any) => {
                  const lessonProgress = progress.find(p => p.lesson_id === lesson.id);
                  const isCompleted = lessonProgress?.is_completed;

                  return (
                    <div
                      key={lesson.id}
                      onClick={() => router.push(`/lesson/${lesson.id}`)}
                      className="p-5 flex items-center justify-between hover:bg-gray-800/50 cursor-pointer transition-colors group"
                    >
                      <div className="flex items-center gap-4">

                        {/* Completed Checkmark vs Uncompleted Play */}
                        {isCompleted ? (
                          <div className="w-8 h-8 rounded-full flex items-center justify-center bg-green-500/20 text-green-500">
                            <CheckCircle2 className="w-5 h-5" />
                          </div>
                        ) : (
                          <div className="w-8 h-8 rounded-full border-2 border-gray-700 flex items-center justify-center group-hover:border-blue-500 transition-colors">
                            <PlayCircle className="w-4 h-4 text-gray-400 group-hover:text-blue-500 transition-colors" />
                          </div>
                        )}

                        <div>
                          <p className="text-sm text-gray-400 mb-1">Lesson {module.order_index}.{lesson.order_index}</p>
                          <h4 className={`font-medium transition-colors ${isCompleted ? 'text-gray-300' : 'group-hover:text-white'}`}>
                            {lesson.title}
                          </h4>
                          {lesson.description && (
                            <p className="text-sm text-gray-500 mt-1 line-clamp-2 max-w-2xl">
                              {lesson.description}
                            </p>
                          )}
                        </div>
                      </div>

                      <ChevronRight className="w-5 h-5 text-gray-600 group-hover:text-blue-500 transition-colors" />
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
