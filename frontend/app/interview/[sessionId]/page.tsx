"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import {
  ApiError,
  endSession,
  getCurrentQuestion,
  getSession,
  repeatQuestion,
  submitAnswer,
} from "@/lib/api-client";
import type { Question } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { MicButton } from "@/components/interview/MicButton";
import { ProgressBar } from "@/components/interview/ProgressBar";
import { RoundBadge } from "@/components/interview/RoundBadge";
import { useVoiceTurn } from "@/hooks/useVoiceTurn";

export default function InterviewPage() {
  const params = useParams<{ sessionId: string }>();
  const sessionId = params.sessionId;
  const router = useRouter();

  const [question, setQuestion] = useState<Question | null>(null);
  const [transcript, setTranscript] = useState("");
  const [progress, setProgress] = useState({ asked: 0, total_estimate: 0 });
  const [difficulty, setDifficulty] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const voice = useVoiceTurn();
  const spokenQuestionIdRef = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const session = await getSession(sessionId);
        if (session.state === "COMPLETED" || session.state === "TERMINATED") {
          router.replace(`/complete/${sessionId}`);
          return;
        }
        const currentQuestion = await getCurrentQuestion(sessionId);
        if (cancelled) return;
        setQuestion(currentQuestion);
        setProgress(session.progress);
        setDifficulty(session.difficulty);
        setIsLoading(false);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 409) {
          router.replace(`/instructions/${sessionId}`);
          return;
        }
        setError("Could not load your interview session.");
        setIsLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [sessionId, router]);

  useEffect(() => {
    if (!question || spokenQuestionIdRef.current === question.question_id) return;
    spokenQuestionIdRef.current = question.question_id;
    voice.speak(question.question_text);
    // voice.speak is stable across renders (useCallback with no deps); only
    // re-run this when the question itself actually changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [question]);

  function handleVoiceResult(finalText: string) {
    setTranscript((prev) => (prev ? `${prev} ${finalText}` : finalText));
  }

  async function handleRepeat() {
    try {
      const result = await repeatQuestion(sessionId);
      voice.speak(result.question_text);
    } catch {
      // Repeating is a convenience, not critical - fail silently and let
      // the candidate re-read the question text already on screen.
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!question || !transcript.trim() || isSubmitting) return;

    setIsSubmitting(true);
    setError(null);
    try {
      const result = await submitAnswer(sessionId, {
        question_id: question.question_id,
        transcript_text: transcript.trim(),
      });
      if (result.next_question === null) {
        // Leave isSubmitting true (keeps the form disabled) - we're
        // navigating away, not resetting to an interactive state.
        router.push(`/complete/${sessionId}`);
        return;
      }
      setQuestion(result.next_question);
      setTranscript("");
      const session = await getSession(sessionId);
      setProgress(session.progress);
      setDifficulty(session.difficulty);
      setIsSubmitting(false);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Could not submit your answer. Please try again.",
      );
      setIsSubmitting(false);
    }
  }

  async function handleEnd() {
    if (!window.confirm("End the interview now? You'll still get a report for what you've completed so far.")) {
      return;
    }
    try {
      await endSession(sessionId, "candidate_ended");
    } finally {
      router.push(`/complete/${sessionId}`);
    }
  }

  if (isLoading) {
    return (
      <main className="flex flex-1 items-center justify-center px-6">
        <p className="text-neutral-500">Loading your interview...</p>
      </main>
    );
  }

  if (!question) {
    return (
      <main className="flex flex-1 flex-col items-center justify-center gap-4 px-6 text-center">
        <p className="text-red-600">{error ?? "Something went wrong."}</p>
        <Button onClick={() => router.push("/")}>Back to start</Button>
      </main>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-6 py-10">
      <ProgressBar asked={progress.asked} totalEstimate={progress.total_estimate} />

      <Card>
        <div className="mb-4 flex items-center justify-between">
          <RoundBadge round={question.round} />
          <span className="text-xs text-neutral-500">Difficulty {difficulty}/5</span>
        </div>
        <p className="text-lg leading-relaxed">{question.question_text}</p>
        <div className="mt-3 flex gap-4">
          <button
            type="button"
            onClick={handleRepeat}
            className="text-xs text-neutral-400 underline-offset-2 hover:text-neutral-600 hover:underline dark:hover:text-neutral-300"
          >
            Repeat question
          </button>
          {voice.status === "speaking" && (
            <button
              type="button"
              onClick={voice.stopSpeaking}
              className="text-xs text-neutral-400 underline-offset-2 hover:text-neutral-600 hover:underline dark:hover:text-neutral-300"
            >
              Stop speaking
            </button>
          )}
        </div>
      </Card>

      <MicButton
        status={voice.status}
        interimText={voice.interimText}
        recognitionSupported={voice.recognitionSupported}
        voiceError={voice.voiceError}
        onStart={() => voice.startListening(handleVoiceResult)}
        onStop={voice.stopListening}
      />

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <textarea
          value={transcript}
          onChange={(e) => setTranscript(e.target.value)}
          placeholder="Type your answer here, or use the microphone above..."
          rows={6}
          className="w-full resize-none rounded-xl border border-neutral-300 p-4 text-base outline-none focus:border-neutral-500 dark:border-neutral-700 dark:bg-neutral-900"
          disabled={isSubmitting}
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={handleEnd}
            className="text-sm text-neutral-400 underline-offset-2 hover:text-neutral-600 hover:underline dark:hover:text-neutral-300"
          >
            End interview
          </button>
          <Button
            type="submit"
            disabled={isSubmitting || voice.status === "listening" || !transcript.trim()}
          >
            {isSubmitting ? "Submitting..." : "Submit answer"}
          </Button>
        </div>
      </form>
    </main>
  );
}
