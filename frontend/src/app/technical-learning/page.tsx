'use client';

import { useEffect, useState } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import {
  Activity,
  ArrowLeft,
  BookOpen,
  BrainCircuit,
  Clock,
  Code2,
  Layers3,
  Loader2,
  LogOut,
  Settings,
  Sparkles,
  Trash2,
} from 'lucide-react';
import axios from 'axios';
import api from '@/lib/api';
import { useAuth } from '@/context/AuthContext';

type PreferredLevelOption = 'auto' | 'beginner' | 'intermediate' | 'advanced';
type CourseLanguageOption = 'english' | 'bengali' | 'hindi';
type ContentStyleOption = 'conceptual' | 'balanced' | 'practical';

type CourseSummary = {
  id: number;
  title: string;
  description: string;
  preferred_level?: 'beginner' | 'intermediate' | 'advanced' | null;
  content_style?: ContentStyleOption;
  warnings?: string[];
  progress_percentage?: number;
  modules: { id: number }[];
};

export default function TechnicalLearningPage() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [topic, setTopic] = useState('');
  const [learningGoal, setLearningGoal] = useState('');
  const [preferredLevel, setPreferredLevel] = useState<PreferredLevelOption>('auto');
  const [courseLanguage, setCourseLanguage] = useState<CourseLanguageOption>('english');
  const [contentStyle, setContentStyle] = useState<ContentStyleOption>('balanced');
  const [deletingCourseId, setDeletingCourseId] = useState<number | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
      return;
    }
    if (user?.is_admin) {
      router.push('/admin/dashboard');
      return;
    }
    if (user) {
      let isCancelled = false;
      const loadCourses = async () => {
        try {
          const { data } = await api.get<CourseSummary[]>('/api/courses/user/courses');
          if (!isCancelled) {
            setCourses(data);
          }
        } catch (err) {
          console.error('Failed to fetch courses', err);
        }
      };
      void loadCourses();
      return () => {
        isCancelled = true;
      };
    }
  }, [loading, router, user]);

  const handleGenerateCourse = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;

    setIsGenerating(true);
    setError('');

    try {
      const payload = {
        topic: topic.trim(),
        learning_goal: learningGoal.trim() || null,
        preferred_level: preferredLevel === 'auto' ? null : preferredLevel,
        language: courseLanguage,
        content_style: contentStyle,
      };

      const { data } = await api.post<CourseSummary>('/api/courses/generate', payload);
      setCourses((prevCourses) => [data, ...prevCourses]);
      setTopic('');
      setLearningGoal('');
      setPreferredLevel('auto');
      setCourseLanguage('english');
      setContentStyle('balanced');
      router.push(`/course/${data.id}`);
    } catch (err: unknown) {
      setError(
        axios.isAxiosError(err)
          ? (err.response?.data?.detail as string) || 'Failed to generate technical course. Please try again.'
          : 'Failed to generate technical course. Please try again.'
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
      <div className="fixed top-0 left-0 h-full w-64 bg-gray-900 border-r border-gray-800 p-6 hidden md:block z-10">
        <div className="flex items-center gap-3 mb-12">
          <Image src="/logo.png" alt="AITutor" width={140} height={40} className="object-contain" />
        </div>

        <nav className="space-y-2">
          <NavItem icon={<Activity />} label="Dashboard" onClick={() => router.push('/dashboard')} />
          <NavItem icon={<BookOpen />} label="Technical Learning" active onClick={() => router.push('/technical-learning')} />
          <NavItem icon={<BrainCircuit />} label="DSA Learn" onClick={() => router.push('/dsa-learn')} />
          <NavItem icon={<Code2 />} label="DSA Solve" onClick={() => router.push('/dsa-solve')} />
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

      <div className="md:ml-64 p-8">
        <header className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6 mb-10">
          <div>
            <button
              onClick={() => router.push('/dashboard')}
              className="inline-flex items-center gap-2 text-gray-400 hover:text-white transition-colors mb-4"
            >
              <ArrowLeft className="w-4 h-4" /> Back to Learning Hub
            </button>
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.22em] text-blue-300 bg-blue-500/10 border border-blue-500/30 rounded-full px-3 py-1 mb-4">
              Technical Learning
            </div>
            <h1 className="text-4xl font-bold mb-3">Build technical skill with real work context</h1>
            <p className="text-gray-400 max-w-3xl leading-relaxed">
              Generate technical courses for programming languages, frameworks, system design, cloud, DevOps, SRE,
              networking, security, and adjacent engineering topics. The content is designed to move past shallow
              tutorial flow into deeper concepts, work-relevant examples, and realistic mistakes.
            </p>
          </div>
          <div className="text-right hidden sm:block">
            <p className="text-sm font-medium text-white">{user.email}</p>
            <p className="text-xs text-gray-500">Joined {joinDate}</p>
          </div>
        </header>

        <div className="grid grid-cols-1 xl:grid-cols-[1.1fr,0.9fr] gap-6 mb-10">
          <section className="bg-gradient-to-br from-blue-600/12 via-cyan-500/8 to-gray-900 border border-blue-500/20 rounded-3xl p-7">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-11 h-11 rounded-2xl bg-blue-500/15 border border-blue-500/20 flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-blue-300" />
              </div>
              <div>
                <h2 className="text-xl font-bold">Generate a Technical Course</h2>
                <p className="text-sm text-gray-400">Choose a topic, set your depth, and shape how the course teaches.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6 text-xs text-blue-100/90">
              <div className="rounded-2xl border border-blue-500/20 bg-blue-500/10 px-4 py-3">
                Work-relevant examples
              </div>
              <div className="rounded-2xl border border-blue-500/20 bg-blue-500/10 px-4 py-3">
                Common mistakes and pitfalls
              </div>
              <div className="rounded-2xl border border-blue-500/20 bg-blue-500/10 px-4 py-3">
                Beginner to advanced depth
              </div>
            </div>

            <form onSubmit={handleGenerateCourse} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Technical Topic</label>
                <input
                  type="text"
                  className="w-full bg-gray-950 border border-gray-700 text-white rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  placeholder="e.g. React Performance, Kubernetes for Beginners, Python Internals, Linux Networking"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  disabled={isGenerating}
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Learning Goal (optional)</label>
                <textarea
                  className="w-full bg-gray-950 border border-gray-700 text-white rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all min-h-24 resize-y"
                  placeholder="e.g. Build and operate a production-ready FastAPI service with auth, observability, and deployment."
                  value={learningGoal}
                  onChange={(e) => setLearningGoal(e.target.value)}
                  disabled={isGenerating}
                  minLength={10}
                  maxLength={300}
                />
                <p className="text-xs text-gray-500 mt-2">
                  Use this to shape practical examples, depth, and the type of work the course prepares for.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Course Language</label>
                  <select
                    className="w-full bg-gray-950 border border-gray-700 text-white rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                    value={courseLanguage}
                    onChange={(e) => setCourseLanguage(e.target.value as CourseLanguageOption)}
                    disabled={isGenerating}
                  >
                    <option value="english">English</option>
                    <option value="bengali">Bengali</option>
                    <option value="hindi">Hindi</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Preferred Level</label>
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

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Content Style</label>
                  <select
                    className="w-full bg-gray-950 border border-gray-700 text-white rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                    value={contentStyle}
                    onChange={(e) => setContentStyle(e.target.value as ContentStyleOption)}
                    disabled={isGenerating}
                  >
                    <option value="conceptual">Conceptual</option>
                    <option value="balanced">Balanced</option>
                    <option value="practical">Practical</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs text-gray-400">
                <div className="rounded-2xl border border-gray-800 bg-gray-950/70 px-4 py-3">
                  <span className="text-gray-200 font-medium">Conceptual</span>
                  <p className="mt-1">Deeper mental models, internals, and reasoning.</p>
                </div>
                <div className="rounded-2xl border border-gray-800 bg-gray-950/70 px-4 py-3">
                  <span className="text-gray-200 font-medium">Balanced</span>
                  <p className="mt-1">Strong theory plus practical examples and mistakes.</p>
                </div>
                <div className="rounded-2xl border border-gray-800 bg-gray-950/70 px-4 py-3">
                  <span className="text-gray-200 font-medium">Practical</span>
                  <p className="mt-1">Workflows, implementation detail, and job-relevant examples.</p>
                </div>
              </div>

              {error && (
                <div className="p-3 bg-red-500/10 border border-red-500/50 rounded-lg text-red-300 text-sm">
                  {error}
                </div>
              )}

              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={isGenerating || !topic.trim()}
                  className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 text-white px-6 py-3 rounded-xl font-medium transition-colors shadow-lg shadow-blue-500/20"
                >
                  {isGenerating ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Designing Technical Course...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      Generate Technical Course
                    </>
                  )}
                </button>
              </div>
            </form>
          </section>

          <section className="bg-gray-900 border border-gray-800 rounded-3xl p-7">
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.22em] text-blue-300 bg-blue-500/10 border border-blue-500/30 rounded-full px-3 py-1 mb-5">
              Technical Positioning
            </div>
            <h2 className="text-xl font-bold mb-4">What this workspace is optimizing for</h2>
            <div className="space-y-4 text-sm text-gray-400 leading-relaxed">
              <p>
                This workspace is for technical learning. It works whether you are starting your first programming
                language or going deeper into advanced topics like performance, internals, architecture, and production tradeoffs.
              </p>
              <p>
                Real-world means examples you could plausibly meet at work: service APIs, frontend state flows,
                deployment setups, observability, networking problems, reliability concerns, or realistic debugging situations.
              </p>
              <p>
                Lessons should not trap you inside traditional tutorial-only sequencing. They should build usable skill,
                expose common failure points, and help you reason like a practitioner.
              </p>
            </div>
          </section>
        </div>

        <section className="bg-gray-900 rounded-3xl border border-gray-800 p-6">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Layers3 className="w-5 h-5 text-blue-500" />
                Your Technical Courses
              </h3>
              <p className="text-sm text-gray-500 mt-1">
                Open, continue, or remove courses generated for your technical learning track.
              </p>
            </div>
          </div>

          {courses.length === 0 ? (
            <div className="text-center py-14 border-2 border-dashed border-gray-800 rounded-2xl">
              <div className="w-16 h-16 rounded-full bg-gray-800/50 flex items-center justify-center mx-auto mb-4">
                <BookOpen className="w-8 h-8 text-gray-500" />
              </div>
              <h4 className="text-gray-300 font-medium mb-2">No technical courses yet</h4>
              <p className="text-gray-500 text-sm max-w-md mx-auto">
                Start with a technical topic you want to learn or deepen. Good examples: FastAPI, React architecture,
                Docker fundamentals, SRE basics, or TCP/IP troubleshooting.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {courses.map((course) => {
                const progress = Math.min(100, Math.max(0, course.progress_percentage ?? 0));
                return (
                  <div
                    key={course.id}
                    onClick={() => router.push(`/course/${course.id}`)}
                    className="group cursor-pointer p-5 rounded-2xl bg-gray-950/60 border border-gray-800 hover:border-blue-500/40 hover:bg-gray-800/50 transition-all"
                  >
                    <div className="flex justify-between items-start mb-3 gap-3">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-2">
                          <span className="text-[11px] uppercase tracking-[0.2em] text-blue-300 bg-blue-500/10 border border-blue-500/20 rounded-full px-2.5 py-1">
                            Technical Learning
                          </span>
                          {course.preferred_level && (
                            <span className="text-[11px] uppercase tracking-[0.18em] text-gray-300 bg-gray-800 border border-gray-700 rounded-full px-2.5 py-1">
                              {course.preferred_level}
                            </span>
                          )}
                          {course.content_style && (
                            <span className="text-[11px] uppercase tracking-[0.18em] text-cyan-300 bg-cyan-500/10 border border-cyan-500/20 rounded-full px-2.5 py-1">
                              {course.content_style}
                            </span>
                          )}
                        </div>
                        <h4 className="font-medium text-lg group-hover:text-blue-400 transition-colors line-clamp-1">
                          {course.title}
                        </h4>
                      </div>
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

                    {course.warnings && course.warnings.length > 0 && (
                      <div className="mb-4 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
                        {course.warnings[0]}
                      </div>
                    )}

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
                );
              })}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function NavItem({
  icon,
  label,
  active = false,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full text-left flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${active ? 'bg-blue-600/10 text-blue-500 font-medium' : 'text-gray-400 hover:bg-gray-800 hover:text-white'}`}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}
