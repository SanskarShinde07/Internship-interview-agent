"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { ApiError, startSession } from "@/lib/api-client";
import { isSpeechRecognitionSupported } from "@/lib/voice/speech-recognition";
import { isSpeechSynthesisSupported } from "@/lib/voice/speech-synthesis";
import { BackButton } from "@/components/ui/BackButton";
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

type MicCheckStatus = "unchecked" | "checking" | "granted" | "denied" | "unavailable";

export default function InstructionsPage() {
  const params = useParams<{ sessionId: string }>();
  const router = useRouter();
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [voiceSupported, setVoiceSupported] = useState(true);
  const [micStatus, setMicStatus] = useState<MicCheckStatus>("unchecked");

  useEffect(() => {
    // See the matching comment in useVoiceTurn.ts: this must run after
    // mount, not as a useState initializer, to avoid a hydration mismatch
    // against the window-less server render.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setVoiceSupported(isSpeechRecognitionSupported() && isSpeechSynthesisSupported());
  }, []);

  async function handleTestMicrophone() {
    setMicStatus("checking");
    if (!navigator.mediaDevices?.getUserMedia) {
      setMicStatus("unavailable");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((track) => track.stop());
      setMicStatus("granted");
    } catch {
      setMicStatus("denied");
    }
  }

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
    <main className="relative flex flex-1 flex-col items-center justify-center px-6 py-16">
      <div className="absolute top-6 left-6">
        <BackButton />
      </div>
      <Card className="w-full max-w-xl">
        <h1 className="mb-2 text-2xl font-semibold">How this works</h1>
        <p className="mb-6 text-sm text-muted">
          You&apos;ll go through seven short rounds. Difficulty adapts to how you answer, and
          the interviewer may ask natural follow-up questions based on what you say.
        </p>
        <ul className="mb-6 flex flex-col gap-3">
          {ROUNDS.map((round) => (
            <li
              key={round.name}
              className="flex flex-col rounded-lg border border-border bg-background p-3"
            >
              <span className="text-sm font-semibold">{round.name}</span>
              <span className="text-sm text-muted">{round.detail}</span>
            </li>
          ))}
        </ul>

        {voiceSupported ? (
          <div className="mb-6 rounded-lg border border-border p-4">
            <p className="mb-3 text-sm">
              You can answer by voice or by typing. Let&apos;s check your microphone works.
            </p>
            <div className="flex items-center gap-3">
              <Button
                type="button"
                variant="secondary"
                onClick={handleTestMicrophone}
                disabled={micStatus === "checking"}
              >
                {micStatus === "checking" ? "Checking..." : "Test microphone"}
              </Button>
              {micStatus === "granted" && (
                <span className="text-sm text-success">Microphone works.</span>
              )}
              {micStatus === "denied" && (
                <span className="text-sm text-danger">
                  Access denied — you can still type your answers.
                </span>
              )}
              {micStatus === "unavailable" && (
                <span className="text-sm text-danger">
                  No microphone detected — you can still type your answers.
                </span>
              )}
            </div>
          </div>
        ) : (
          <p className="mb-6 rounded-lg border border-warning/30 bg-warning-bg p-3 text-xs text-warning">
            Voice isn&apos;t supported in this browser. Chrome or Edge are recommended for voice
            — you can still complete the interview by typing your answers.
          </p>
        )}

        {error && <p className="mb-4 text-sm text-danger">{error}</p>}
        <Button onClick={handleStart} disabled={isStarting} className="w-full">
          {isStarting ? "Starting..." : "I'm ready - start the interview"}
        </Button>
      </Card>
    </main>
  );
}
