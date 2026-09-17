"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

import { ApiError, getReport } from "@/lib/api-client";
import type { InterviewReport } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { CategoryScores } from "@/components/report/CategoryScores";
import { RoadmapList } from "@/components/report/RoadmapList";
import { ScoreCard } from "@/components/report/ScoreCard";

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mb-3 text-sm font-semibold tracking-wide text-neutral-500 uppercase">
      {children}
    </h2>
  );
}

function AiTag() {
  return (
    <span className="ml-2 rounded bg-neutral-100 px-1.5 py-0.5 text-[10px] font-normal tracking-normal text-neutral-500 normal-case dark:bg-neutral-800">
      AI-generated
    </span>
  );
}

export default function ReportPage() {
  const params = useParams<{ sessionId: string }>();
  const [report, setReport] = useState<InterviewReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getReport(params.sessionId)
      .then((r) => {
        if (!cancelled) setReport(r);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "Could not load your report.");
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

  if (!report) {
    return (
      <main className="flex flex-1 items-center justify-center px-6">
        <p className="text-neutral-500">Generating your report...</p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-6 py-10">
      <div>
        <h1 className="text-2xl font-semibold">Your Recruiter Report</h1>
        <p className="text-sm text-neutral-500">
          Scores below are computed deterministically from your interview. The summary and
          roadmap are AI-generated based on those scores.
        </p>
      </div>

      <Card>
        <ScoreCard overallScore={report.overall_score} readinessLevel={report.readiness_level} />
      </Card>

      <Card>
        <SectionLabel>Category Scores</SectionLabel>
        <CategoryScores scores={report.category_scores} />
      </Card>

      <Card>
        <SectionLabel>
          Recruiter Summary
          <AiTag />
        </SectionLabel>
        <p className="text-sm leading-relaxed">{report.recruiter_summary}</p>
      </Card>

      <div className="grid gap-6 sm:grid-cols-2">
        <Card>
          <SectionLabel>
            Strengths
            <AiTag />
          </SectionLabel>
          <ul className="flex flex-col gap-2 text-sm">
            {report.strengths.map((s) => (
              <li key={s}>• {s}</li>
            ))}
          </ul>
        </Card>
        <Card>
          <SectionLabel>
            Areas to Improve
            <AiTag />
          </SectionLabel>
          <ul className="flex flex-col gap-2 text-sm">
            {report.improvements.map((s) => (
              <li key={s}>• {s}</li>
            ))}
          </ul>
        </Card>
      </div>

      <Card>
        <SectionLabel>
          Learning Roadmap
          <AiTag />
        </SectionLabel>
        <RoadmapList items={report.learning_roadmap} />
      </Card>

      <div className="flex justify-center gap-4 pb-4">
        <Link href={`/analytics/${params.sessionId}`}>
          <Button variant="secondary">View Analytics</Button>
        </Link>
        <Link href={`/coach/${params.sessionId}`}>
          <Button>Ask the Coach</Button>
        </Link>
      </div>
    </main>
  );
}
