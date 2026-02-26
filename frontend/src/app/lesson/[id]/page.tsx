'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { ArrowLeft, BookOpen, CheckCircle, BrainCircuit, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css'; // For markdown code blocks
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';

export default function LessonPage() {
  const { id } = useParams();
  const router = useRouter();
  const { user, loading } = useAuth();

  const [lesson, setLesson] = useState<any>(null);
  const [course, setCourse] = useState<any>(null);
  const [nextLessonId, setNextLessonId] = useState<number | null>(null);
  const [isGenerating, setIsGenerating] = useState(true);
  const [isCompleting, setIsCompleting] = useState(false);

  // Quiz State
  const [quizScore, setQuizScore] = useState<number | null>(null);
  const [selectedAnswers, setSelectedAnswers] = useState<Record<number, number>>({});
  const [showResults, setShowResults] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.push('/login');
    if (user && id) fetchLessonContent();
  }, [user, id, loading]);

  const fetchLessonContent = async () => {
    try {
      setIsGenerating(true);
      // This endpoint triggers Bedrock to generate the content JIT if it doesn't exist
      const { data } = await api.get(`/api/courses/lessons/${id}`);
      setLesson(data);

      // Fetch the full course to find the next lesson
      const courseRes = await api.get(`/api/courses/${data.course_id}`);
      setCourse(courseRes.data);

      const allLessons = courseRes.data.modules.flatMap((m: any) => m.lessons);
      const currentIndex = allLessons.findIndex((l: any) => l.id === data.id);
      if (currentIndex !== -1 && currentIndex < allLessons.length - 1) {
        setNextLessonId(allLessons[currentIndex + 1].id);
      }

    } catch (err) {
      console.error("Failed to fetch/generate lesson", err);
      router.push('/dashboard');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleQuizSubmit = () => {
    if (!lesson?.quiz_data) return;

    let score = 0;
    lesson.quiz_data.forEach((q: any, i: number) => {
      if (selectedAnswers[i] === q.correct_answer_index) {
        score++;
      }
    });

    setQuizScore(score);
    setShowResults(true);
  };

  const handleCompleteLesson = async () => {
    try {
      setIsCompleting(true);
      await api.post(`/api/courses/lessons/${id}/progress`, {
        is_completed: true,
        quiz_score: quizScore
      });

      if (nextLessonId) {
        router.push(`/lesson/${nextLessonId}`);
      } else {
        router.push(`/course/${lesson.course_id}`);
      }
    } catch (err) {
      console.error("Failed to mark complete", err);
      setIsCompleting(false);
    }
  };

  if (isGenerating) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-950 text-white">
        <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-6" />
        <h2 className="text-2xl font-bold mb-2">Generating Lesson...</h2>
        <p className="text-gray-400 max-w-sm text-center">
          Our AI Tutor is currently crafting custom curriculum, examples, and a quiz just for you.
        </p>
      </div>
    );
  }

  if (!lesson) return null;

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Top Navigation */}
      <div className="sticky top-0 z-10 bg-gray-900/80 backdrop-blur-md border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Syllabus
        </button>
        <div className="flex items-center gap-2 text-blue-500 font-medium">
          <BookOpen className="w-4 h-4" /> AITutor Lesson
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-12">
        <header className="mb-12">
          <h1 className="text-4xl md:text-5xl font-extrabold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
            {lesson.title}
          </h1>
        </header>

        {/* AI Generated Markdown Content */}
        <article className="prose prose-invert prose-blue max-w-none mb-16 prose-headings:text-blue-400 prose-a:text-blue-500 hover:prose-a:text-blue-400 prose-strong:text-white prose-code:text-pink-400 prose-pre:bg-gray-900 prose-pre:border prose-pre:border-gray-800 bg-gray-900/40 p-8 md:p-12 rounded-3xl border border-gray-800/60 shadow-xl leading-relaxed text-gray-300">
          <ReactMarkdown rehypePlugins={[rehypeHighlight]}>
            {lesson.content}
          </ReactMarkdown>
        </article>

        {/* AI Generated Interactive Quiz */}
        {lesson.quiz_data && lesson.quiz_data.length > 0 && (
          <div className="bg-gray-900 rounded-2xl border border-gray-800 p-8 mb-16">
            <div className="flex items-center gap-3 mb-8">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg">
                <BrainCircuit className="w-6 h-6 text-white" />
              </div>
              <div>
                <h3 className="text-2xl font-bold text-white">Knowledge Check</h3>
                <p className="text-gray-400">Test your understanding of {lesson.title}</p>
              </div>
            </div>

            <div className="space-y-10">
              {lesson.quiz_data.map((q: any, qIndex: number) => (
                <div key={qIndex} className="bg-gray-950/50 rounded-xl p-6 border border-gray-800/50">
                  <p className="text-lg font-medium text-white mb-4">
                    <span className="text-blue-500 mr-2">{qIndex + 1}.</span> {q.question}
                  </p>

                  <div className="space-y-3">
                    {q.options.map((opt: string, optIndex: number) => {
                      const isSelected = selectedAnswers[qIndex] === optIndex;
                      const isCorrect = optIndex === q.correct_answer_index;

                      // Formatting based on submission state
                      let optionClasses = "relative flex items-center p-4 rounded-xl border-2 cursor-pointer transition-all overflow-hidden ";

                      if (!showResults) {
                        optionClasses += isSelected ? "border-blue-500 bg-blue-500/10 text-white" : "border-gray-800 hover:border-gray-600 bg-gray-900 text-gray-300";
                      } else {
                        // Show results states
                        if (isCorrect) {
                          optionClasses += "border-green-500 bg-green-500/10 text-green-400";
                        } else if (isSelected && !isCorrect) {
                          optionClasses += "border-red-500 bg-red-500/10 text-red-400 opacity-50";
                        } else {
                          optionClasses += "border-gray-800 bg-gray-900 text-gray-500 opacity-50";
                        }
                      }

                      return (
                        <div
                          key={optIndex}
                          onClick={() => !showResults && setSelectedAnswers(prev => ({ ...prev, [qIndex]: optIndex }))}
                          className={optionClasses}
                        >
                          {/* Radio button circle */}
                          <div className={`w-5 h-5 rounded-full border flex items-center justify-center mr-4 flex-shrink-0 ${showResults && isCorrect ? 'border-green-500 bg-green-500' :
                            showResults && isSelected && !isCorrect ? 'border-red-500 bg-red-500' :
                              isSelected ? 'border-blue-500 border-[6px]' : 'border-gray-600'
                            }`}>
                            {showResults && isCorrect && <CheckCircle className="w-4 h-4 text-white" />}
                          </div>

                          <span className="font-medium">{opt}</span>
                        </div>
                      );
                    })}
                  </div>

                  {/* Explanation after submission */}
                  {showResults && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      className="mt-6 p-4 bg-blue-900/20 border border-blue-500/30 rounded-xl text-blue-200"
                    >
                      <span className="font-bold text-blue-400 mr-2">Explanation:</span>
                      {q.explanation}
                    </motion.div>
                  )}
                </div>
              ))}
            </div>

            <div className="mt-8 pt-8 border-t border-gray-800 flex justify-between items-center">
              {showResults ? (
                <div className="flex items-center gap-4">
                  <div className="text-3xl font-bold text-white">
                    {quizScore} <span className="text-gray-500 text-xl">/ {lesson.quiz_data.length}</span>
                  </div>
                  <div className={`px-3 py-1 text-sm font-bold rounded-full ${quizScore === lesson.quiz_data.length ? 'bg-green-500/20 text-green-400' :
                    quizScore && quizScore > 0 ? 'bg-yellow-500/20 text-yellow-400' : 'bg-red-500/20 text-red-400'
                    }`}>
                    {quizScore === lesson.quiz_data.length ? 'Perfect Score!' : 'Keep Practicing'}
                  </div>
                </div>
              ) : (
                <p className="text-gray-400">Select an answer for each question to complete the lesson.</p>
              )}

              {!showResults ? (
                <button
                  onClick={handleQuizSubmit}
                  disabled={Object.keys(selectedAnswers).length < lesson.quiz_data.length}
                  className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 disabled:cursor-not-allowed text-white px-8 py-3 rounded-xl font-bold transition-colors"
                >
                  Submit Quiz
                </button>
              ) : (
                <button
                  onClick={handleCompleteLesson}
                  disabled={isCompleting}
                  className="bg-green-600 hover:bg-green-700 disabled:bg-green-600/50 disabled:cursor-not-allowed flex items-center gap-2 text-white px-8 py-3 rounded-xl font-bold transition-colors"
                >
                  {isCompleting ? <Loader2 className="w-5 h-5 animate-spin" /> : <CheckCircle className="w-5 h-5" />}
                  {nextLessonId ? "Complete & Continue" : "Complete Course"}
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
