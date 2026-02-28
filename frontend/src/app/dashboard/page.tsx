'use client';

import { useCallback, useEffect, useState } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { LogOut, BookOpen, Clock, Activity, Settings, User as UserIcon, Plus, X, Sparkles, Loader2, Trash2 } from 'lucide-react';
import axios from 'axios';
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';

export default function DashboardPage() {
  type PreferredLevelOption = 'auto' | 'beginner' | 'intermediate' | 'advanced';
  interface CourseSummary {
    id: number;
    title: string;
    description: string;
    progress_percentage?: number;
    modules: { id: number }[];
  }

  const { user, loading, logout } = useAuth();
  const router = useRouter();

  // State for Course Generation
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [showNewCourseModal, setShowNewCourseModal] = useState(false);
  const [topic, setTopic] = useState('');
  const [learningGoal, setLearningGoal] = useState('');
  const [preferredLevel, setPreferredLevel] = useState<PreferredLevelOption>('auto');
  const [deletingCourseId, setDeletingCourseId] = useState<number | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
    if (user?.is_admin) {
      router.push('/admin/dashboard');
    }
  }, [user, loading, router]);

  const fetchCourses = useCallback(async () => {
    try {
      const { data } = await api.get<CourseSummary[]>('/api/courses/user/courses');
      setCourses(data);
    } catch (err) {
      console.error("Failed to fetch courses", err);
    }
  }, []);

  useEffect(() => {
    if (user && !user.is_admin) {
      fetchCourses();
    }
  }, [user, fetchCourses]);

  const handleGenerateCourse = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;

    setIsGenerating(true);
    setError('');

    try {
      const normalizedLearningGoal = learningGoal.trim();
      const payload = {
        topic: topic.trim(),
        learning_goal: normalizedLearningGoal || null,
        preferred_level: preferredLevel === 'auto' ? null : preferredLevel,
      };

      const { data } = await api.post<CourseSummary>('/api/courses/generate', payload);
      setCourses((prevCourses) => [data, ...prevCourses]);
      setShowNewCourseModal(false);
      setTopic('');
      setLearningGoal('');
      setPreferredLevel('auto');
      if (data?.id) {
        router.push(`/course/${data.id}`);
      }
    } catch (err: unknown) {
      setError(
        axios.isAxiosError(err)
          ? (err.response?.data?.detail as string) || 'Failed to generate course. Please try again.'
          : 'Failed to generate course. Please try again.'
      );
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDeleteCourse = async (courseId: number, courseTitle: string) => {
    const confirmed = window.confirm(`Delete "${courseTitle}"? This action cannot be undone.`);
    if (!confirmed) return;

    setDeletingCourseId(courseId);
    setError('');
    try {
      await api.delete(`/api/courses/${courseId}`);
      setCourses((prevCourses) => prevCourses.filter((course) => course.id !== courseId));
    } catch (err: unknown) {
      setError(
        axios.isAxiosError(err)
          ? (err.response?.data?.detail as string) || 'Failed to delete course. Please try again.'
          : 'Failed to delete course. Please try again.'
      );
    } finally {
      setDeletingCourseId(null);
    }
  };

  if (loading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  const joinDate = new Date(user.created_at).toLocaleDateString();

  return (
    <div className="min-h-screen bg-gray-950 text-white relative">
      {/* Sidebar / Navigation */}
      <div className="fixed top-0 left-0 h-full w-64 bg-gray-900 border-r border-gray-800 p-6 hidden md:block z-10">
        <div className="flex items-center gap-3 mb-12">
          <Image src="/logo.png" alt="AITutor" width={140} height={40} className="object-contain" />
        </div>

        <nav className="space-y-2">
          <NavItem icon={<Activity />} label="Dashboard" active />
          <NavItem icon={<BookOpen />} label="Courses" />
          <NavItem icon={<Clock />} label="History" />
          <NavItem icon={<Settings />} label="Settings" />
        </nav>

        <div className="absolute bottom-6 left-6 right-6">
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium text-gray-400 hover:text-white rounded-xl hover:bg-gray-800 transition-colors"
          >
            <LogOut className="w-5 h-5" />
            Sign Out
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="md:ml-64 p-8 relative z-0">
        <header className="flex justify-between items-center mb-10">
          <div>
            <h1 className="text-3xl font-bold mb-2">Welcome back!</h1>
            <p className="text-gray-400">Here is your learning overview for today.</p>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => setShowNewCourseModal(true)}
              className="hidden sm:flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl font-medium transition-colors shadow-lg shadow-blue-500/20"
            >
              <Sparkles className="w-4 h-4" />
              Generate Course
            </button>
            <div className="text-right hidden sm:block">
              <p className="text-sm font-medium text-white">{user.email}</p>
              <p className="text-xs text-gray-500">Joined {joinDate}</p>
            </div>
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg">
              <UserIcon className="w-6 h-6 text-white" />
            </div>
          </div>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-10">
          {/* Stat Cards */}
          <StatCard title="Active Courses" value={courses.length.toString()} icon={<BookOpen className="w-6 h-6 text-blue-400" />} />
          <StatCard title="Hours Learned" value="0.0" icon={<Clock className="w-6 h-6 text-purple-400" />} />
          <StatCard title="Current Streak" value="1 Day" icon={<Activity className="w-6 h-6 text-green-400" />} />
        </div>

        <div className="bg-gray-900 rounded-2xl border border-gray-800 p-6 mb-8">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-blue-500" />
              Your Courses
            </h3>
            <button
              onClick={() => setShowNewCourseModal(true)}
              className="sm:hidden flex items-center gap-2 text-blue-400 hover:text-blue-300 text-sm font-medium"
            >
              <Plus className="w-4 h-4" /> New
            </button>
          </div>

          {courses.length === 0 ? (
            <div className="text-center py-12 border-2 border-dashed border-gray-800 rounded-xl">
              <div className="w-16 h-16 rounded-full bg-gray-800/50 flex items-center justify-center mx-auto mb-4">
                <Sparkles className="w-8 h-8 text-gray-500" />
              </div>
              <h4 className="text-gray-300 font-medium mb-2">No courses yet</h4>
              <p className="text-gray-500 text-sm mb-6 max-w-sm mx-auto">
                Generate your first personalized AI course by entering any topic you want to learn about!
              </p>
              <button
                onClick={() => setShowNewCourseModal(true)}
                className="bg-gray-800 hover:bg-gray-700 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition-colors"
              >
                Create a Course
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {courses.map((course) => {
                const rawProgress = typeof course.progress_percentage === 'number' ? course.progress_percentage : 0;
                const progress = Math.min(100, Math.max(0, rawProgress));

                return (
                  <div key={course.id} onClick={() => router.push(`/course/${course.id}`)} className="group cursor-pointer p-5 rounded-xl bg-gray-950/50 border border-gray-800 hover:border-blue-500/50 hover:bg-gray-800/50 transition-all">
                    <div className="flex justify-between items-start mb-3">
                      <h4 className="font-medium text-lg group-hover:text-blue-400 transition-colors line-clamp-1">{course.title}</h4>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteCourse(course.id, course.title);
                        }}
                        disabled={deletingCourseId === course.id}
                        className="inline-flex items-center gap-1 text-xs text-red-400 hover:text-red-300 disabled:text-gray-500 disabled:cursor-not-allowed px-2 py-1 rounded-md hover:bg-red-500/10 transition-colors"
                        aria-label={`Delete ${course.title}`}
                      >
                        {deletingCourseId === course.id ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <Trash2 className="w-3 h-3" />
                        )}
                        {deletingCourseId === course.id ? 'Deleting' : 'Delete'}
                      </button>
                    </div>
                    <p className="text-sm text-gray-500 line-clamp-2 mb-4">{course.description}</p>
                    <div className="mb-4">
                      <div className="flex items-center justify-between text-xs text-gray-400 mb-2">
                        <span>{progress.toFixed(1)}% complete</span>
                        <span>{course.modules.length} Modules</span>
                      </div>
                      <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 transition-all duration-500"
                          style={{ width: `${progress}%` }}
                        />
                      </div>
                    </div>
                    <div className="flex items-center justify-end text-xs text-gray-400">
                      <span className="text-blue-500 group-hover:underline">Start Learning →</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Floating Generate Course Modal */}
      <AnimatePresence>
        {showNewCourseModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => !isGenerating && setShowNewCourseModal(false)}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            />

            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 20 }}
              className="relative w-full max-w-lg bg-gray-900 rounded-2xl border border-gray-800 shadow-2xl overflow-hidden"
            >
              <div className="p-6">
                <div className="flex justify-between items-center mb-6">
                  <h3 className="text-xl font-bold flex items-center gap-2 text-white">
                    <Sparkles className="w-5 h-5 text-blue-500" />
                    Generate Syllabus
                  </h3>
                  <button
                    onClick={() => setShowNewCourseModal(false)}
                    disabled={isGenerating}
                    className="text-gray-400 hover:text-white transition-colors disabled:opacity-50"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <form onSubmit={handleGenerateCourse}>
                  <p className="text-gray-400 text-sm mb-4">
                    What do you want to learn? Our AI will instantly craft a structured syllabus and interactive lessons customized for you.
                  </p>

                  <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Course Topic
                    </label>
                    <input
                      type="text"
                      className="w-full bg-gray-950 border border-gray-700 text-white rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                      placeholder="e.g. Introduction to Quantum Computing, Complete History of Rome..."
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      disabled={isGenerating}
                      required
                    />
                  </div>

                  <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Learning Goal (optional)
                    </label>
                    <textarea
                      className="w-full bg-gray-950 border border-gray-700 text-white rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all min-h-24 resize-y"
                      placeholder="e.g. Build and deploy a production-ready FastAPI backend in 6 weeks."
                      value={learningGoal}
                      onChange={(e) => setLearningGoal(e.target.value)}
                      disabled={isGenerating}
                      minLength={10}
                      maxLength={300}
                    />
                    <p className="text-xs text-gray-500 mt-2">
                      If provided, this should be 10-300 characters and will shape lesson examples.
                    </p>
                  </div>

                  <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Preferred Level
                    </label>
                    <select
                      className="w-full bg-gray-950 border border-gray-700 text-white rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                      value={preferredLevel}
                      onChange={(e) => setPreferredLevel(e.target.value as PreferredLevelOption)}
                      disabled={isGenerating}
                    >
                      <option value="auto">Auto (Infer from topic)</option>
                      <option value="beginner">Beginner</option>
                      <option value="intermediate">Intermediate</option>
                      <option value="advanced">Advanced</option>
                    </select>
                  </div>

                  {error && (
                    <div className="mb-6 p-3 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm">
                      {error}
                    </div>
                  )}

                  <div className="flex justify-end gap-3">
                    <button
                      type="button"
                      onClick={() => setShowNewCourseModal(false)}
                      disabled={isGenerating}
                      className="px-5 py-2.5 rounded-xl font-medium text-gray-300 hover:bg-gray-800 transition-colors disabled:opacity-50"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isGenerating || !topic.trim()}
                      className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 text-white px-5 py-2.5 rounded-xl font-medium transition-colors shadow-lg shadow-blue-500/20"
                    >
                      {isGenerating ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Designing Course...
                        </>
                      ) : (
                        'Generate'
                      )}
                    </button>
                  </div>
                </form>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

function NavItem({ icon, label, active = false }: { icon: React.ReactNode; label: string; active?: boolean }) {
  return (
    <a href="#" className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${active ? 'bg-blue-600/10 text-blue-500 font-medium' : 'text-gray-400 hover:bg-gray-800 hover:text-white'}`}>
      {icon}
      <span>{label}</span>
    </a>
  );
}

function StatCard({ title, value, icon }: { title: string; value: string; icon: React.ReactNode }) {
  return (
    <motion.div
      whileHover={{ y: -4 }}
      className="bg-gray-900 p-6 rounded-2xl border border-gray-800 flex items-center gap-5"
    >
      <div className="w-14 h-14 rounded-2xl bg-gray-800 flex items-center justify-center border border-gray-700">
        {icon}
      </div>
      <div>
        <p className="text-sm font-medium text-gray-400 mb-1">{title}</p>
        <p className="text-2xl font-bold">{value}</p>
      </div>
    </motion.div>
  );
}
