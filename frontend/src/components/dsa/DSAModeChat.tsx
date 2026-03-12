'use client';

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import axios from 'axios';
import {
  ArrowLeft, BookOpen, BrainCircuit, ChevronLeft, ChevronRight,
  Loader2, MessageSquare, Plus, Send, Target, TrendingUp, X, Zap,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';

import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';
import MermaidDiagram from './MermaidDiagram';

// ─── Types ───────────────────────────────────────────────────────────────────

export type DSATopic =
  | 'arrays'
  | 'linked_lists'
  | 'stacks_and_queues'
  | 'sliding_window'
  | 'two_pointers'
  | 'binary_search'
  | 'sorting'
  | 'hashing'
  | 'trees'
  | 'binary_search_tree'
  | 'heaps'
  | 'graphs'
  | 'recursion'
  | 'backtracking'
  | 'dynamic_programming'
  | 'greedy'
  | 'tries'
  | 'bit_manipulation'
  | 'string_manipulation'
  | 'intervals'
  | 'matrix'
  | 'general_problem_solving';

export type DSACoachingMode = 'learn_topic' | 'solve_problem';

interface CoachTurn {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
}

interface CoachSession {
  id: number;
  topic: DSATopic;
  coaching_mode: DSACoachingMode;
  problem_statement: string;
  prior_knowledge?: string | null;
  learner_attempt?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  turns: CoachTurn[];
}

interface CoachSessionSummary {
  id: number;
  topic: DSATopic;
  coaching_mode: DSACoachingMode;
  status: string;
  created_at: string;
  updated_at: string;
  turns_count: number;
  latest_assistant_preview?: string | null;
  concept_focus?: string | null;
}

interface WeakArea {
  id: number;
  topic: DSATopic;
  area: string;
  evidence?: string | null;
  severity_score: number;
  occurrence_count: number;
  first_seen_at: string;
  last_seen_at: string;
}

interface TurnResult {
  session_id: number;
  coaching_stage?: string | null;
  hint_level?: string | null;
  concept_focus?: string | null;
  next_action?: string | null;
  assistant_turn: CoachTurn;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const TOPIC_OPTIONS: Array<{ value: DSATopic; label: string; group: string }> = [
  // Fundamentals
  { value: 'arrays',             label: 'Arrays',                group: 'Fundamentals' },
  { value: 'linked_lists',       label: 'Linked Lists',          group: 'Fundamentals' },
  { value: 'stacks_and_queues',  label: 'Stacks & Queues',       group: 'Fundamentals' },
  { value: 'hashing',            label: 'Hashing / Hash Maps',   group: 'Fundamentals' },
  { value: 'string_manipulation',label: 'String Manipulation',   group: 'Fundamentals' },
  { value: 'sorting',            label: 'Sorting',               group: 'Fundamentals' },
  // Patterns
  { value: 'two_pointers',       label: 'Two Pointers',          group: 'Patterns' },
  { value: 'sliding_window',     label: 'Sliding Window',        group: 'Patterns' },
  { value: 'binary_search',      label: 'Binary Search',         group: 'Patterns' },
  { value: 'intervals',          label: 'Intervals',             group: 'Patterns' },
  { value: 'matrix',             label: 'Matrix / 2D Grid',      group: 'Patterns' },
  { value: 'bit_manipulation',   label: 'Bit Manipulation',      group: 'Patterns' },
  // Trees & Graphs
  { value: 'trees',              label: 'Trees',                 group: 'Trees & Graphs' },
  { value: 'binary_search_tree', label: 'Binary Search Tree',    group: 'Trees & Graphs' },
  { value: 'heaps',              label: 'Heaps / Priority Queue',group: 'Trees & Graphs' },
  { value: 'tries',              label: 'Tries',                 group: 'Trees & Graphs' },
  { value: 'graphs',             label: 'Graphs',                group: 'Trees & Graphs' },
  // Advanced
  { value: 'recursion',          label: 'Recursion',             group: 'Advanced' },
  { value: 'backtracking',       label: 'Backtracking',          group: 'Advanced' },
  { value: 'dynamic_programming',label: 'Dynamic Programming',   group: 'Advanced' },
  { value: 'greedy',             label: 'Greedy',                group: 'Advanced' },
  // General
  { value: 'general_problem_solving', label: 'General Problem Solving', group: 'General' },
];

const TOPIC_LABELS: Record<DSATopic, string> = TOPIC_OPTIONS.reduce(
  (acc, o) => ({ ...acc, [o.value]: o.label }),
  {} as Record<DSATopic, string>,
);

// Group topics for the select dropdown
const TOPIC_GROUPS = TOPIC_OPTIONS.reduce<Record<string, typeof TOPIC_OPTIONS>>((acc, o) => {
  if (!acc[o.group]) acc[o.group] = [];
  acc[o.group].push(o);
  return acc;
}, {});

const STAGE_CONFIG: Record<string, { label: string; cls: string }> = {
  understanding: { label: 'Understanding', cls: 'text-blue-400 bg-blue-500/10 border-blue-500/30' },
  application:   { label: 'Applying',      cls: 'text-green-400 bg-green-500/10 border-green-500/30' },
  debugging:     { label: 'Debugging',     cls: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30' },
  complexity:    { label: 'Complexity',    cls: 'text-purple-400 bg-purple-500/10 border-purple-500/30' },
  reflection:    { label: 'Reflecting',    cls: 'text-teal-400 bg-teal-500/10 border-teal-500/30' },
};

const QUICK_REPLIES: Record<string, string[]> = {
  assess_baseline:      ["I'm completely new to this", 'I know the basics', "I'm fairly comfortable"],
  explain_concept:      ['Got it! Give me a practice problem', 'Still confused — try a simpler example', "What's the time complexity?"],
  worked_example:       ['I follow the example, give me practice!', "Still confused — what's the tricky part?", 'Walk me through step 3 again'],
  correct_misconception:['I see my mistake now', 'Can you clarify further?'],
  bridge_prerequisite:  ['I know this already, please continue', 'Please explain this prerequisite first'],
  give_practice:        ["I'll try it!", 'Give me a small hint first', "I don't know where to start"],
  verify_understanding: ['Yes, I understand', 'Not quite — can you re-explain?', 'Can you give another example?'],
  ask_initial_thought:  ['My initial thought is…', "I don't understand the problem yet"],
  guided_hint:          ['Give me another hint', 'I think I see it now', 'Show me the full approach'],
  default:              ["I understand", "I'm confused", 'Show me an example', 'Give me a practice problem'],
};
const ALWAYS_REPLIES = ['Reflect on this session'];

// ─── Helpers ─────────────────────────────────────────────────────────────────

function relativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days === 1) return 'yesterday';
  return `${days}d ago`;
}

function buildSessionLabels(sessions: CoachSessionSummary[]): Record<number, string> {
  const topicCount: Record<string, number> = {};
  const topicIndex: Record<number, number> = {};
  const sorted = [...sessions].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  );
  for (const s of sorted) {
    topicCount[s.topic] = (topicCount[s.topic] || 0) + 1;
    topicIndex[s.id] = topicCount[s.topic];
  }
  const labels: Record<number, string> = {};
  for (const s of sessions) {
    const hasDuplicate = sessions.filter((x) => x.topic === s.topic).length > 1;
    labels[s.id] = hasDuplicate
      ? `${TOPIC_LABELS[s.topic]} #${topicIndex[s.id]}`
      : TOPIC_LABELS[s.topic];
  }
  return labels;
}

// ─── Chat markdown renderer ───────────────────────────────────────────────────

function ChatMarkdown({ content }: { content: string }) {
  return (
    <article className="prose prose-invert prose-sm max-w-none prose-headings:text-sky-300 prose-headings:font-semibold prose-p:text-gray-200 prose-code:text-pink-300 prose-pre:bg-[#0d1117] prose-pre:border prose-pre:border-[#30363d] prose-li:text-gray-200 prose-strong:text-white">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          code({ className, children, ...props }) {
            const lang = /language-(\w+)/.exec(className || '')?.[1];
            if (lang === 'mermaid') {
              return <MermaidDiagram code={String(children)} />;
            }
            return (
              <code className={className} {...props}>
                {children}
              </code>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </article>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

interface DSAModeChatProps {
  mode: DSACoachingMode;
}

export default function DSAModeChat({ mode }: DSAModeChatProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionIdFromUrl = searchParams.get('s') ? parseInt(searchParams.get('s')!) : null;
  const { user, loading } = useAuth();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [sessions, setSessions] = useState<CoachSessionSummary[]>([]);
  const [activeSession, setActiveSession] = useState<CoachSession | null>(null);
  const [weakAreas, setWeakAreas] = useState<WeakArea[]>([]);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isLoadingSession, setIsLoadingSession] = useState(false);
  const [error, setError] = useState('');

  // Sidebar & modal
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showNewSessionModal, setShowNewSessionModal] = useState(false);

  // New session form
  const [topic, setTopic] = useState<DSATopic>('arrays');
  const [problemStatement, setProblemStatement] = useState('');
  const [priorKnowledge, setPriorKnowledge] = useState('');
  const [attemptDraft, setAttemptDraft] = useState('');
  const [openingMessage, setOpeningMessage] = useState(
    mode === 'learn_topic'
      ? 'Teach me from basics, check what I know, then give me guided practice.'
      : 'Please coach me step by step without giving the full answer early.',
  );
  const [chatMessage, setChatMessage] = useState('');

  // Active session teaching context
  const [currentStage, setCurrentStage] = useState<string>('');
  const [currentConceptFocus, setCurrentConceptFocus] = useState<string>('');
  const [currentNextAction, setCurrentNextAction] = useState<string>('');

  const parseApiError = useCallback(
    (err: unknown, fallback: string) =>
      axios.isAxiosError(err) ? (err.response?.data?.detail as string) || fallback : fallback,
    [],
  );

  const refreshWeakAreas = useCallback(async () => {
    const { data } = await api.get<WeakArea[]>('/api/dsa-coach/weak-areas');
    setWeakAreas(data);
  }, []);

  const refreshSessionSummaries = useCallback(async () => {
    const { data } = await api.get<CoachSessionSummary[]>('/api/dsa-coach/sessions', {
      params: { coaching_mode: mode },
    });
    setSessions(data);
    return data;
  }, [mode]);

  const loadSessionById = useCallback(
    async (sessionId: number) => {
      setIsLoadingSession(true);
      setError('');
      try {
        const { data } = await api.get<CoachSession>(`/api/dsa-coach/sessions/${sessionId}`);
        if (data.coaching_mode !== mode) return;
        setActiveSession(data);
        setPriorKnowledge(data.prior_knowledge || '');
        setAttemptDraft(mode === 'solve_problem' ? data.learner_attempt || '' : '');
        setChatMessage('');
        setCurrentStage('');
        setCurrentConceptFocus('');
        setCurrentNextAction('');
      } catch (err) {
        setError(parseApiError(err, 'Failed to load session.'));
      } finally {
        setIsLoadingSession(false);
      }
    },
    [mode, parseApiError],
  );

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeSession?.turns]);

  useEffect(() => {
    if (!loading && !user) { router.push('/login'); return; }
    if (user?.is_admin) { router.push('/admin/dashboard'); return; }
    if (!user) return;

    const bootstrap = async () => {
      setIsBootstrapping(true);
      setError('');
      setActiveSession(null);
      try {
        const [sessionData] = await Promise.all([refreshSessionSummaries(), refreshWeakAreas()]);
        if (sessionIdFromUrl) {
          await loadSessionById(sessionIdFromUrl);
        } else if (sessionData.length > 0) {
          await loadSessionById(sessionData[0].id);
        } else {
          setShowNewSessionModal(true);
        }
      } catch (err) {
        setError(parseApiError(err, 'Failed to initialise DSA mode.'));
      } finally {
        setIsBootstrapping(false);
      }
    };
    bootstrap();
  }, [loading, user, router, parseApiError, refreshSessionSummaries, refreshWeakAreas, loadSessionById, sessionIdFromUrl]);

  const sessionLabels = useMemo(() => buildSessionLabels(sessions), [sessions]);

  const pageTitle = mode === 'learn_topic' ? 'DSA Learn' : 'DSA Solve';
  const stageConfig = STAGE_CONFIG[currentStage] ?? null;
  const quickReplies = [
    ...(QUICK_REPLIES[currentNextAction] ?? QUICK_REPLIES.default),
    ...ALWAYS_REPLIES,
  ];

  const handleCreateSession = async (e: FormEvent) => {
    e.preventDefault();
    if (mode === 'solve_problem' && !problemStatement.trim()) return;
    setIsCreating(true);
    setError('');
    try {
      const payload = {
        coaching_mode: mode,
        topic,
        problem_statement: mode === 'solve_problem' ? problemStatement.trim() || null : null,
        prior_knowledge: mode === 'learn_topic' ? priorKnowledge.trim() || null : null,
        learner_attempt: mode === 'solve_problem' ? attemptDraft.trim() || null : null,
        message: openingMessage.trim() || null,
      };
      const { data } = await api.post<CoachSession>('/api/dsa-coach/sessions', payload);
      setShowNewSessionModal(false);
      setProblemStatement('');
      const targetPage = mode === 'learn_topic' ? '/dsa-learn' : '/dsa-solve';
      router.push(`${targetPage}?s=${data.id}`);
    } catch (err) {
      setError(parseApiError(err, 'Failed to create session.'));
    } finally {
      setIsCreating(false);
    }
  };

  const handleSendMessage = async (e: FormEvent) => {
    e.preventDefault();
    if (!activeSession || !chatMessage.trim()) return;

    const outgoing = chatMessage.trim();
    const localTurn: CoachTurn = {
      id: -Date.now(),
      role: 'user',
      content: outgoing,
      created_at: new Date().toISOString(),
    };

    setIsSending(true);
    setError('');
    setChatMessage('');
    setActiveSession((prev) => prev ? { ...prev, turns: [...prev.turns, localTurn] } : prev);

    try {
      const payload = {
        message: outgoing,
        learner_attempt: mode === 'solve_problem' ? attemptDraft.trim() || null : null,
      };
      const { data } = await api.post<TurnResult>(
        `/api/dsa-coach/sessions/${activeSession.id}/messages`,
        payload,
      );

      setActiveSession((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          learner_attempt: mode === 'solve_problem' ? attemptDraft.trim() || null : prev.learner_attempt,
          updated_at: new Date().toISOString(),
          turns: [...prev.turns.filter((t) => t.id !== localTurn.id), localTurn, data.assistant_turn],
        };
      });

      if (data.coaching_stage) setCurrentStage(data.coaching_stage);
      if (data.concept_focus)  setCurrentConceptFocus(data.concept_focus);
      if (data.next_action)    setCurrentNextAction(data.next_action);

      await Promise.all([refreshSessionSummaries(), refreshWeakAreas()]);
    } catch (err) {
      setError(parseApiError(err, 'Failed to send message.'));
      setChatMessage(outgoing);
      setActiveSession((prev) =>
        prev ? { ...prev, turns: prev.turns.filter((t) => t.id !== localTurn.id) } : prev,
      );
    } finally {
      setIsSending(false);
    }
  };

  if (loading || isBootstrapping) {
    return (
      <div className="min-h-screen bg-[#0b0d10] text-white flex items-center justify-center">
        <div className="flex items-center gap-3">
          <Loader2 className="w-5 h-5 animate-spin text-sky-400" />
          <p className="text-sm text-gray-300">Loading {pageTitle}…</p>
        </div>
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="min-h-screen bg-[#0b0d10] text-white">
      <div className="flex h-screen overflow-hidden">

        {/* ── Sidebar (full) ─────────────────────────────────────────────── */}
        {sidebarOpen && (
          <aside className="w-[280px] shrink-0 border-r border-[#1f232b] bg-[#0e1117] flex flex-col">

            {/* Header */}
            <div className="px-4 py-3 border-b border-[#1f232b] flex items-start justify-between gap-2">
              <div className="min-w-0">
                <button
                  onClick={() => router.push('/dashboard')}
                  className="inline-flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  Dashboard
                </button>
                <h1 className="mt-2 text-sm font-semibold text-white">{pageTitle}</h1>
                <p className="text-[11px] text-gray-600 mt-0.5">
                  {mode === 'learn_topic' ? 'Concept-first guided learning' : 'Pattern-first problem coaching'}
                </p>
              </div>
              <button
                onClick={() => setSidebarOpen(false)}
                title="Collapse sidebar"
                className="mt-1 shrink-0 p-1.5 rounded-lg text-gray-600 hover:text-gray-300 hover:bg-white/5 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
            </div>

            {/* New session button */}
            <div className="px-3 py-3 border-b border-[#1f232b]">
              <button
                type="button"
                onClick={() => setShowNewSessionModal(true)}
                className="w-full flex items-center justify-center gap-2 rounded-lg bg-sky-600 hover:bg-sky-500 px-3 py-2 text-sm font-medium text-white transition-colors"
              >
                <Plus className="w-4 h-4" />
                New session
              </button>
            </div>

            {/* Session list */}
            <div className="flex-1 overflow-y-auto py-2 px-2 space-y-1">
              {sessions.length === 0 && (
                <p className="text-xs text-gray-600 text-center mt-6 px-3">No sessions yet.</p>
              )}
              {sessions.map((session) => {
                const isActive = activeSession?.id === session.id;
                const label = sessionLabels[session.id] ?? TOPIC_LABELS[session.topic];
                return (
                  <button
                    key={session.id}
                    type="button"
                    onClick={() => loadSessionById(session.id)}
                    disabled={isLoadingSession}
                    className={`w-full text-left rounded-xl px-3 py-2.5 border transition-all ${
                      isActive
                        ? 'border-sky-500/40 bg-sky-500/8'
                        : 'border-transparent hover:border-[#252b36] hover:bg-white/[0.03]'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className={`text-sm font-medium truncate leading-tight ${isActive ? 'text-sky-300' : 'text-gray-200'}`}>
                        {label}
                      </span>
                      <span className="shrink-0 text-[10px] text-gray-600 tabular-nums">
                        {session.turns_count} turns
                      </span>
                    </div>
                    {session.concept_focus && (
                      <p className="mt-0.5 text-[11px] text-sky-500/70 truncate">
                        {session.concept_focus}
                      </p>
                    )}
                    {session.latest_assistant_preview && !session.concept_focus && (
                      <p className="mt-0.5 text-[11px] text-gray-600 truncate">
                        {session.latest_assistant_preview}
                      </p>
                    )}
                    <p className="mt-1 text-[10px] text-gray-700">
                      {relativeTime(session.updated_at)}
                    </p>
                  </button>
                );
              })}
            </div>

            {/* Weak areas */}
            {weakAreas.length > 0 && (
              <div className="border-t border-[#1f232b] px-3 py-3">
                <p className="text-[11px] text-gray-600 flex items-center gap-1.5 mb-2">
                  <TrendingUp className="w-3 h-3" />
                  Weak areas
                </p>
                <div className="space-y-1.5 max-h-28 overflow-y-auto">
                  {weakAreas.slice(0, 6).map((area) => (
                    <div key={area.id} className="flex items-center gap-2 text-[11px]">
                      <span
                        className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                          area.severity_score === 3 ? 'bg-red-400' :
                          area.severity_score === 2 ? 'bg-yellow-400' : 'bg-blue-400'
                        }`}
                      />
                      <span className="text-gray-500 truncate">{area.area}</span>
                      <span className="shrink-0 text-gray-700">×{area.occurrence_count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </aside>
        )}

        {/* ── Sidebar collapsed strip ─────────────────────────────────────── */}
        {!sidebarOpen && (
          <div className="w-12 shrink-0 border-r border-[#1f232b] bg-[#0e1117] flex flex-col items-center pt-3 gap-1">
            <button
              onClick={() => setSidebarOpen(true)}
              title="Expand sidebar"
              className="p-2 rounded-lg text-gray-600 hover:text-gray-300 hover:bg-white/5 transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => setShowNewSessionModal(true)}
              title="New session"
              className="p-2 rounded-lg text-gray-600 hover:text-sky-400 hover:bg-sky-500/10 transition-colors"
            >
              <Plus className="w-4 h-4" />
            </button>
            {sessions.length > 0 && (
              <div className="mt-2 flex flex-col items-center gap-1.5 w-full px-2">
                {sessions.slice(0, 6).map((s) => (
                  <button
                    key={s.id}
                    onClick={() => { setSidebarOpen(true); loadSessionById(s.id); }}
                    title={sessionLabels[s.id] ?? TOPIC_LABELS[s.topic]}
                    className={`w-8 h-8 rounded-lg border text-[10px] font-bold transition-colors ${
                      activeSession?.id === s.id
                        ? 'border-sky-500/50 bg-sky-500/15 text-sky-400'
                        : 'border-[#1f232b] bg-transparent text-gray-600 hover:border-[#2d3a4e] hover:text-gray-400'
                    }`}
                  >
                    {(sessionLabels[s.id] ?? TOPIC_LABELS[s.topic]).slice(0, 2).toUpperCase()}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Main chat area ─────────────────────────────────────────────── */}
        <main className="flex-1 flex flex-col min-w-0">

          {/* Chat header */}
          <div className="shrink-0 border-b border-[#1f232b] px-5 py-3 bg-[#0e1117] flex items-center justify-between gap-4">
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">
                  {activeSession ? (sessionLabels[activeSession.id] ?? TOPIC_LABELS[activeSession.topic]) : pageTitle}
                </p>
                {stageConfig && (
                  <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${stageConfig.cls}`}>
                    {stageConfig.label}
                  </span>
                )}
              </div>
              {currentConceptFocus && (
                <p className="text-sm text-sky-300 font-medium truncate mt-0.5">
                  {currentConceptFocus}
                </p>
              )}
            </div>
            <div className="hidden md:flex items-center gap-1.5 text-xs text-gray-600 shrink-0">
              <BrainCircuit className="w-3.5 h-3.5" />
              {mode === 'learn_topic' ? 'Learn mode' : 'Solve mode'}
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6">
            {!activeSession ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-center text-gray-600 max-w-xs">
                  <BookOpen className="w-8 h-8 mx-auto mb-3 opacity-30" />
                  <p className="text-sm">
                    {sessions.length === 0
                      ? 'Click "New session" to start learning.'
                      : 'Select a session from the sidebar.'}
                  </p>
                </div>
              </div>
            ) : (
              <div className="max-w-2xl mx-auto space-y-4">

                {/* Session context card */}
                <div className="rounded-xl border border-[#1f232b] bg-[#0d1117] p-4">
                  <p className="text-[11px] text-gray-600 flex items-center gap-1.5 mb-2">
                    <Target className="w-3 h-3" />
                    {mode === 'learn_topic' ? 'Learning context' : 'Problem'}
                  </p>
                  <p className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">
                    {activeSession.problem_statement}
                  </p>
                  {mode === 'learn_topic' && activeSession.prior_knowledge && (
                    <p className="mt-2 text-xs text-gray-600 border-t border-[#1f232b] pt-2">
                      Prior knowledge: {activeSession.prior_knowledge}
                    </p>
                  )}
                </div>

                {/* Turns */}
                {activeSession.turns.map((turn) =>
                  turn.role === 'assistant' ? (
                    /* Coach message — left, blue tinted */
                    <div key={turn.id} className="flex gap-3">
                      <div className="shrink-0 w-7 h-7 rounded-full bg-sky-500/15 border border-sky-500/25 flex items-center justify-center mt-0.5">
                        <BrainCircuit className="w-3.5 h-3.5 text-sky-400" />
                      </div>
                      <div className="flex-1 min-w-0 rounded-2xl rounded-tl-sm px-4 py-3 border border-[#1e2d3d] bg-[#0a1628]">
                        <p className="text-[10px] uppercase tracking-widest text-sky-500/60 mb-2">Coach</p>
                        <ChatMarkdown content={turn.content} />
                      </div>
                    </div>
                  ) : (
                    /* User message — right, warm tinted */
                    <div key={turn.id} className="flex gap-3 justify-end">
                      <div className="max-w-[80%] rounded-2xl rounded-tr-sm px-4 py-3 border border-[#2a2010] bg-[#1a1508]">
                        <p className="text-[10px] uppercase tracking-widest text-amber-500/50 mb-2 text-right">You</p>
                        <p className="text-sm text-gray-100 whitespace-pre-wrap leading-relaxed">
                          {turn.content}
                        </p>
                      </div>
                      <div className="shrink-0 w-7 h-7 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mt-0.5 text-[11px] font-semibold text-amber-400">
                        Y
                      </div>
                    </div>
                  )
                )}

                {isSending && (
                  <div className="flex gap-3">
                    <div className="shrink-0 w-7 h-7 rounded-full bg-sky-500/15 border border-sky-500/25 flex items-center justify-center">
                      <BrainCircuit className="w-3.5 h-3.5 text-sky-400" />
                    </div>
                    <div className="rounded-2xl rounded-tl-sm px-4 py-3 border border-[#1e2d3d] bg-[#0a1628]">
                      <div className="flex items-center gap-2 text-sky-400 text-sm">
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        Thinking…
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/* Input area */}
          <div className="shrink-0 border-t border-[#1f232b] bg-[#0e1117] px-4 md:px-8 py-3">

            {mode === 'solve_problem' && activeSession && (
              <div className="max-w-2xl mx-auto mb-2">
                <textarea
                  value={attemptDraft}
                  onChange={(e) => setAttemptDraft(e.target.value)}
                  className="w-full bg-[#0b0f14] border border-[#1f232b] rounded-lg px-3 py-2 text-xs min-h-14 resize-y font-mono text-gray-300 focus:outline-none focus:border-sky-500/40"
                  placeholder="Update your approach / code (optional)"
                  disabled={isSending}
                />
              </div>
            )}

            {activeSession && (
              <div className="max-w-2xl mx-auto mb-2 flex flex-wrap gap-1.5">
                {quickReplies.map((reply) => (
                  <button
                    key={reply}
                    type="button"
                    onClick={() => setChatMessage(reply)}
                    disabled={isSending}
                    className="inline-flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-full border border-[#252b36] bg-transparent text-gray-500 hover:border-sky-500/40 hover:text-sky-300 hover:bg-sky-500/5 transition-colors disabled:opacity-40"
                  >
                    <Zap className="w-2.5 h-2.5" />
                    {reply}
                  </button>
                ))}
              </div>
            )}

            <form onSubmit={handleSendMessage} className="max-w-2xl mx-auto flex gap-2">
              <input
                type="text"
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                className="flex-1 min-w-0 bg-[#0b0f14] border border-[#1f232b] rounded-xl px-4 py-2.5 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-sky-500/40 transition-colors"
                placeholder={
                  mode === 'learn_topic'
                    ? 'Ask a question, answer the checkpoint, or pick a quick reply…'
                    : "Share your thought, ask for a hint, or describe where you're stuck…"
                }
                disabled={isSending || !activeSession}
              />
              <button
                type="submit"
                disabled={isSending || !chatMessage.trim() || !activeSession}
                className="shrink-0 rounded-xl bg-sky-600 hover:bg-sky-500 disabled:bg-[#1a2535] disabled:text-gray-600 px-4 py-2.5 text-sm font-medium inline-flex items-center gap-2 transition-colors"
              >
                {isSending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                Send
              </button>
            </form>
          </div>
        </main>
      </div>

      {/* ── New Session Modal ───────────────────────────────────────────────── */}
      {showNewSessionModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
          onClick={(e) => { if (e.target === e.currentTarget) setShowNewSessionModal(false); }}
        >
          <div className="bg-[#0e1117] border border-[#252b36] rounded-2xl w-full max-w-lg shadow-2xl max-h-[90vh] flex flex-col">

            {/* Modal header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#1f232b]">
              <div>
                <h2 className="text-base font-semibold text-white">New {pageTitle} session</h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  {mode === 'learn_topic' ? 'Choose a topic to learn' : 'Paste a problem to solve with coaching'}
                </p>
              </div>
              <button
                onClick={() => setShowNewSessionModal(false)}
                className="p-1.5 rounded-lg text-gray-600 hover:text-gray-300 hover:bg-white/5 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal body */}
            <form onSubmit={handleCreateSession} className="overflow-y-auto px-6 py-5 space-y-4 flex-1">

              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1.5">Topic</label>
                <select
                  value={topic}
                  onChange={(e) => setTopic(e.target.value as DSATopic)}
                  className="w-full bg-[#0b0f14] border border-[#252b36] rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-sky-500/50"
                  disabled={isCreating}
                >
                  {Object.entries(TOPIC_GROUPS).map(([group, options]) => (
                    <optgroup key={group} label={group}>
                      {options.map((o) => (
                        <option key={o.value} value={o.value}>{o.label}</option>
                      ))}
                    </optgroup>
                  ))}
                </select>
              </div>

              {mode === 'learn_topic' && (
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">
                    Prior knowledge <span className="text-gray-600 font-normal">(optional)</span>
                  </label>
                  <textarea
                    value={priorKnowledge}
                    onChange={(e) => setPriorKnowledge(e.target.value)}
                    className="w-full bg-[#0b0f14] border border-[#252b36] rounded-lg px-3 py-2 text-sm text-gray-100 min-h-20 resize-y focus:outline-none focus:border-sky-500/50"
                    placeholder="e.g. I know loops and arrays but haven't used two pointers"
                    disabled={isCreating}
                  />
                </div>
              )}

              {mode === 'solve_problem' && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1.5">
                      Problem statement <span className="text-red-400">*</span>
                    </label>
                    <textarea
                      value={problemStatement}
                      onChange={(e) => setProblemStatement(e.target.value)}
                      className="w-full bg-[#0b0f14] border border-[#252b36] rounded-lg px-3 py-2 text-sm text-gray-100 min-h-28 resize-y focus:outline-none focus:border-sky-500/50"
                      placeholder="Paste the full problem statement here…"
                      disabled={isCreating}
                      required
                      minLength={20}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1.5">
                      Your current approach <span className="text-gray-600 font-normal">(optional)</span>
                    </label>
                    <textarea
                      value={attemptDraft}
                      onChange={(e) => setAttemptDraft(e.target.value)}
                      className="w-full bg-[#0b0f14] border border-[#252b36] rounded-lg px-3 py-2 text-xs text-gray-300 min-h-20 resize-y font-mono focus:outline-none focus:border-sky-500/50"
                      placeholder="Pseudocode or code attempt…"
                      disabled={isCreating}
                    />
                  </div>
                </>
              )}

              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1.5">Opening message</label>
                <input
                  type="text"
                  value={openingMessage}
                  onChange={(e) => setOpeningMessage(e.target.value)}
                  className="w-full bg-[#0b0f14] border border-[#252b36] rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-sky-500/50"
                  disabled={isCreating}
                />
              </div>

              {error && (
                <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                  {error}
                </p>
              )}

              <div className="flex gap-3 pt-1">
                <button
                  type="button"
                  onClick={() => setShowNewSessionModal(false)}
                  className="flex-1 rounded-lg border border-[#252b36] bg-transparent hover:bg-white/5 px-4 py-2.5 text-sm text-gray-400 transition-colors"
                  disabled={isCreating}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreating || (mode === 'solve_problem' && !problemStatement.trim())}
                  className="flex-1 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:bg-sky-900/50 disabled:text-gray-600 px-4 py-2.5 text-sm font-medium transition-colors inline-flex items-center justify-center gap-2"
                >
                  {isCreating ? (
                    <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Starting…</>
                  ) : 'Start session'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Error toast */}
      {error && !showNewSessionModal && (
        <div className="fixed bottom-4 right-4 max-w-sm bg-red-500/10 border border-red-500/30 text-red-300 px-4 py-3 rounded-xl text-sm shadow-xl">
          <p className="flex items-center gap-2">
            <MessageSquare className="w-4 h-4 shrink-0" />
            {error}
          </p>
        </div>
      )}
    </div>
  );
}
