"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { ApiError, getMyInterviews } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { SessionHistoryItem } from "@/lib/types";
import { BackButton } from "@/components/ui/BackButton";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

const READINESS_LABELS: Record<string, string> = {
  NOT_READY: "Not Ready",
  DEVELOPING: "Developing",
  READY: "Ready",
  STRONG: "Strong",
};

const READINESS_COLORS: Record<string, string> = {
  NOT_READY: "bg-danger-bg text-danger",
  DEVELOPING: "bg-warning-bg text-warning",
  READY: "bg-info-bg text-info",
  STRONG: "bg-success-bg text-success",
};

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function HistoryPage() {
  const router = useRouter();
  const { user, isLoading: isAuthLoading } = useAuth();
  const [sessions, setSessions] = useState<SessionHistoryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthLoading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    let cancelled = false;
    getMyInterviews()
      .then((res) => {
        if (!cancelled) setSessions(res.sessions);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "Could not load your interviews.");
      });
    return () => {
      cancelled = true;
    };
  }, [user, isAuthLoading, router]);

  if (isAuthLoading || (!user && !error)) {
    return (
      <main className="flex flex-1 items-center justify-center px-6">
        <p className="text-muted">Loading...</p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-6 py-10">
      <BackButton />
      <div>
        <h1 className="text-2xl font-semibold">My Interviews</h1>
        <p className="text-sm text-muted">
          Every interview you&apos;ve started while signed in, with a link to its report.
        </p>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      {sessions && sessions.length === 0 && (
        <Card className="text-center">
          <p className="mb-4 text-sm text-muted">You haven&apos;t started an interview yet.</p>
          <Link href="/setup">
            <Button>Start Mock Interview</Button>
          </Link>
        </Card>
      )}

      {sessions && sessions.length > 0 && (
        <div className="flex flex-col gap-3">
          {sessions.map((session) => (
            <Card key={session.session_id} className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-medium">{formatDate(session.started_at)}</p>
                <p className="text-xs text-muted">{session.state.replace(/_/g, " ")}</p>
              </div>
              <div className="flex items-center gap-4">
                {session.overall_score !== null && (
                  <>
                    <span className="text-sm font-semibold">{session.overall_score}/100</span>
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${
                        READINESS_COLORS[session.readiness_level ?? ""] ?? ""
                      }`}
                    >
                      {READINESS_LABELS[session.readiness_level ?? ""] ?? session.readiness_level}
                    </span>
                  </>
                )}
                {session.state === "COMPLETED" ? (
                  <Link href={`/report/${session.session_id}`}>
                    <Button variant="secondary">View Report</Button>
                  </Link>
                ) : session.state === "TERMINATED" ? (
                  <span className="text-xs text-muted">Ended early</span>
                ) : (
                  <Link href={`/interview/${session.session_id}`}>
                    <Button variant="secondary">Resume</Button>
                  </Link>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </main>
  );
}
