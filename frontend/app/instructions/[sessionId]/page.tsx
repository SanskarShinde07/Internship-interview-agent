"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { ApiError, startSession } from "@/lib/api-client";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

const ROUNDS = [
  { name: "Introduction", detail: "A brief warm-up: tell us about yourself." },
  { name: "Python", detail: "Fundamentals, data structures, NumPy, Pandas, problem solving." },
  { name: "Machine Learning", detail: "Supervised/unsupervised learning, model evaluation, tuning." },
  { name: "NLP", detail: "Tokenization, embeddings, transformers, LLMs, RAG." },
  { name: "Project Discussion", detail: "We'll dig into a project you've worked on." },
  { name: "Scenario", detail: "Reasoning through realistic ML engineering situations." },
  { name: "Behavioral", detail: "A few questions about how you work with others." },
];

export default function InstructionsPage() {
  const params = useParams<{ sessionId: string }>();
  const router = useRouter();
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleStart() {
    setIsStarting(true);
    setError(null);
    try {
      await startSession(params.sessionId);
      router.push(`/interview/${params.sessionId}`);
    } catch (err) {
      if (err instanceof ApiError && err.errorCode === "invalid_transition") {
        // Already started (e.g. the candidate navigated back) - just resume.
        router.push(`/interview/${params.sessionId}`);
        return;
      }
      setError(
        err instanceof ApiError
          ? err.message
          : "Could not start the interview. Please try again.",
      );
      setIsStarting(false);
    }
  }

  return (
    <main className="flex flex-1 flex-col items-center justify-center px-6 py-16">
      <Card className="w-full max-w-xl">
        <h1 className="mb-2 text-2xl font-semibold">How this works</h1>
        <p className="mb-6 text-sm text-neutral-500">
          You&apos;ll go through seven short rounds. Difficulty adapts to how you answer, and
          the interviewer may ask natural follow-up questions based on what you say.
        </p>
        <ul className="mb-6 flex flex-col gap-3">
          {ROUNDS.map((round) => (
            <li key={round.name} className="flex flex-col rounded-lg bg-neutral-50 p-3 dark:bg-neutral-800">
              <span className="text-sm font-semibold">{round.name}</span>
              <span className="text-sm text-neutral-500">{round.detail}</span>
            </li>
          ))}
        </ul>
        <p className="mb-6 text-xs text-neutral-500">
          For now, answers are typed. Voice input/output will be available once the voice layer
          ships.
        </p>
        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
        <Button onClick={handleStart} disabled={isStarting} className="w-full">
          {isStarting ? "Starting..." : "I'm ready - start the interview"}
        </Button>
      </Card>
    </main>
  );
}
