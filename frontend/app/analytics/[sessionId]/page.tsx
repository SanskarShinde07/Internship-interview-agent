"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { ApiError, getAnalytics } from "@/lib/api-client";
import type { InterviewAnalytics } from "@/lib/types";
import { Card } from "@/components/ui/Card";
import { ScoreBar } from "@/components/analytics/ScoreBar";
import { StatTile } from "@/components/analytics/StatTile";

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mb-3 text-sm font-semibold tracking-wide text-neutral-500 uppercase">
      {children}
    </h2>
  );
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "—";
  const minutes = Math.floor(seconds / 60);
  const remaining = Math.round(seconds % 60);
  return `${minutes}m ${remaining}s`;
}

export default function AnalyticsPage() {
  const params = useParams<{ sessionId: string }>();
  const [analytics, setAnalytics] = useState<InterviewAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getAnalytics(params.sessionId)
      .then((a) => {
        if (!cancelled) setAnalytics(a);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "Could not load analytics.");
      });
    return () => {
      cancelled = true;
    };
  }, [params.sessionId]);

  if (error) {
    return (
      <main className="flex flex-1 items-center justify-center px-6 text-center">
        <p className="text-red-600">{error}</p>
      </main>
    );
  }

  if (!analytics) {
    return (
      <main className="flex flex-1 items-center justify-center px-6">
        <p className="text-neutral-500">Loading analytics...</p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-6 py-10">
      <h1 className="text-2xl font-semibold">Interview Analytics</h1>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Duration" value={formatDuration(analytics.interview_duration_seconds)} />
        <StatTile label="Total Questions" value={analytics.total_questions} />
        <StatTile label="Follow-ups" value={analytics.follow_up_questions} />
        <StatTile label="Highest Difficulty" value={analytics.highest_difficulty_reached ?? "—"} />
        <StatTile label="Difficulty Changes" value={analytics.adaptive_difficulty_changes} />
        <StatTile label="Avg. Technical Score" value={analytics.average_technical_score ?? "—"} />
        <StatTile
          label="Avg. Communication Score"
          value={analytics.average_communication_score ?? "—"}
        />
        <StatTile
          label="Completion Rate"
          value={`${Math.round(analytics.interview_completion_rate * 100)}%`}
        />
      </div>

      <Card>
        <SectionLabel>Topic-wise Scores</SectionLabel>
        <div className="flex flex-col gap-3">
          {Object.entries(analytics.topic_wise_scores).map(([topic, score]) => (
            <ScoreBar key={topic} label={topic} score={score} />
          ))}
        </div>
        {analytics.strongest_topic && (
          <p className="mt-4 text-xs text-neutral-500">
            Strongest:{" "}
            <span className="font-medium">{analytics.strongest_topic.replace(/_/g, " ")}</span>
            {" · "}
            Weakest:{" "}
            <span className="font-medium">{analytics.weakest_topic?.replace(/_/g, " ")}</span>
          </p>
        )}
      </Card>

      <Card>
        <SectionLabel>Adaptive Difficulty Progression</SectionLabel>
        {analytics.difficulty_progression.length === 0 ? (
          <p className="text-sm text-neutral-500">Difficulty stayed constant throughout.</p>
        ) : (
          <ul className="flex flex-col gap-1 text-sm">
            {analytics.difficulty_progression.map((d) => (
              <li
                key={d.sequence_number}
                className="flex justify-between border-b border-neutral-100 py-1 last:border-0 dark:border-neutral-800"
              >
                <span>Q{d.sequence_number}</span>
                <span>
                  {d.previous_difficulty} → {d.new_difficulty}
                </span>
                <span className="text-neutral-500">{d.reason.replace(/_/g, " ").toLowerCase()}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card>
        <SectionLabel>Interview Timeline</SectionLabel>
        <ul className="flex flex-col gap-1 text-sm">
          {analytics.interview_timeline.map((t) => (
            <li
              key={t.sequence_number}
              className="flex justify-between border-b border-neutral-100 py-1 last:border-0 dark:border-neutral-800"
            >
              <span>#{t.sequence_number}</span>
              <span>{t.round}</span>
              <span>{t.topic.replace(/_/g, " ")}</span>
              <span className="text-neutral-500">d{t.difficulty}</span>
            </li>
          ))}
        </ul>
      </Card>
    </main>
  );
}
