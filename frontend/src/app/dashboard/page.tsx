'use client';

import { useEffect, useState } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  Activity,
  ArrowRight,
  BookOpen,
  BrainCircuit,
  Clock,
  Code2,
  LogOut,
  Settings,
  User as UserIcon,
} from 'lucide-react';
import api from '@/lib/api';
import { useAuth } from '@/context/AuthContext';

type CourseSummary = {
  id: number;
  title: string;
  description: string;
  progress_percentage?: number;
  modules: { id: number }[];
};

export default function DashboardPage() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const [courses, setCourses] = useState<CourseSummary[]>([]);

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

  if (loading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  const joinDate = new Date(user.created_at).toLocaleDateString();
  const recentCourses = courses.slice(0, 4);

  return (
    <div className="min-h-screen bg-gray-950 text-white relative">
      <div className="fixed top-0 left-0 h-full w-64 bg-gray-900 border-r border-gray-800 p-6 hidden md:block z-10">
        <div className="flex items-center gap-3 mb-12">
          <Image src="/logo.png" alt="AITutor" width={140} height={40} className="object-contain" />
        </div>

        <nav className="space-y-2">
          <NavItem icon={<Activity />} label="Dashboard" active onClick={() => router.push('/dashboard')} />
          <NavItem icon={<BookOpen />} label="Technical Learning" onClick={() => router.push('/technical-learning')} />
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
        <header className="flex justify-between items-center mb-10">
          <div>
            <h1 className="text-3xl font-bold mb-2">Learning Hub</h1>
            <p className="text-gray-400">
              Choose the domain you want to learn in. Technical learning is active now.
            </p>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push('/technical-learning')}
              className="hidden sm:flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl font-medium transition-colors shadow-lg shadow-blue-500/20"
            >
              <BookOpen className="w-4 h-4" />
              Open Technical Learning
            </button>
            <div className="text-right hidden sm:block">
              <p className="text-sm font-medium text-white">{user.email}</p>
              <p className="text-xs text-gray-500">Joined {joinDate}</p>
            </div>
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg">
              <UserIcon className="w-6 h-6 text-white" />
            </div>
          </div>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          <StatCard title="Technical Courses" value={courses.length.toString()} icon={<BookOpen className="w-6 h-6 text-blue-400" />} />
          <StatCard title="Hours Learned" value="0.0" icon={<Clock className="w-6 h-6 text-cyan-400" />} />
          <StatCard title="Current Streak" value="1 Day" icon={<Activity className="w-6 h-6 text-emerald-400" />} />
        </div>

        <section className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-10">
          <motion.button
            whileHover={{ y: -4 }}
            onClick={() => router.push('/technical-learning')}
            className="text-left bg-gradient-to-br from-blue-600/15 via-cyan-500/10 to-gray-900 border border-blue-500/30 rounded-3xl p-7 shadow-xl shadow-blue-950/30"
          >
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.22em] text-blue-300 bg-blue-500/10 border border-blue-500/30 rounded-full px-3 py-1 mb-5">
              Active Domain
            </div>
            <h2 className="text-2xl font-bold mb-3">Technical Learning</h2>
            <p className="text-gray-300 leading-relaxed mb-6">
              Generate deep technical courses for programming languages, frontend/backend stacks, cloud,
              DevOps, SRE, networking, security, and adjacent engineering topics. Lessons emphasize work-relevant
              examples, deeper concepts, and realistic mistakes.
            </p>
            <div className="flex flex-wrap gap-2 mb-6 text-xs text-blue-100/90">
              <span className="rounded-full border border-blue-500/30 bg-blue-500/10 px-3 py-1">Beginner to advanced</span>
              <span className="rounded-full border border-blue-500/30 bg-blue-500/10 px-3 py-1">Production-flavored examples</span>
              <span className="rounded-full border border-blue-500/30 bg-blue-500/10 px-3 py-1">Common mistakes included</span>
            </div>
            <div className="inline-flex items-center gap-2 text-sm font-medium text-blue-300">
              Enter Technical Learning <ArrowRight className="w-4 h-4" />
            </div>
          </motion.button>

          <div className="bg-gray-900 border border-gray-800 rounded-3xl p-7 opacity-90">
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.22em] text-amber-200 bg-amber-500/10 border border-amber-500/30 rounded-full px-3 py-1 mb-5">
              Coming Soon
            </div>
            <h2 className="text-2xl font-bold mb-3">Non-Technical Learning</h2>
            <p className="text-gray-400 leading-relaxed mb-6">
              A dedicated non-technical learning experience will come later with its own agent and content model.
              It is intentionally separated so technical learners are not pushed into a generalized learning flow.
            </p>
            <div className="space-y-3 text-sm text-gray-500">
              <p>Separate agent and prompts</p>
              <p>Separate UI and examples</p>
              <p>Not part of the current release</p>
            </div>
          </div>
        </section>

        <section className="bg-gray-900 rounded-3xl border border-gray-800 p-6">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-blue-500" />
                Recent Technical Courses
              </h3>
              <p className="text-sm text-gray-500 mt-1">
                Continue your latest technical learning tracks or open the full workspace.
              </p>
            </div>
            <button
              onClick={() => router.push('/technical-learning')}
              className="text-sm font-medium text-blue-400 hover:text-blue-300"
            >
              Open Workspace
            </button>
          </div>

          {recentCourses.length === 0 ? (
            <div className="text-center py-12 border-2 border-dashed border-gray-800 rounded-2xl">
              <div className="w-16 h-16 rounded-full bg-gray-800/50 flex items-center justify-center mx-auto mb-4">
                <BookOpen className="w-8 h-8 text-gray-500" />
              </div>
              <h4 className="text-gray-300 font-medium mb-2">No technical courses yet</h4>
              <p className="text-gray-500 text-sm mb-6 max-w-sm mx-auto">
                Start with a technical topic like React, Kubernetes, Python internals, Linux networking, or system design.
              </p>
              <button
                onClick={() => router.push('/technical-learning')}
                className="bg-gray-800 hover:bg-gray-700 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition-colors"
              >
                Open Technical Learning
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {recentCourses.map((course) => {
                const progress = Math.min(100, Math.max(0, course.progress_percentage ?? 0));
                return (
                  <div
                    key={course.id}
                    onClick={() => router.push(`/course/${course.id}`)}
                    className="group cursor-pointer p-5 rounded-2xl bg-gray-950/60 border border-gray-800 hover:border-blue-500/40 hover:bg-gray-800/50 transition-all"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <h4 className="font-medium text-lg group-hover:text-blue-400 transition-colors line-clamp-1">
                        {course.title}
                      </h4>
                      <span className="text-[11px] uppercase tracking-[0.2em] text-blue-300 bg-blue-500/10 border border-blue-500/20 rounded-full px-2.5 py-1">
                        Tech
                      </span>
                    </div>
                    <p className="text-sm text-gray-500 line-clamp-2 mb-4">{course.description}</p>
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
