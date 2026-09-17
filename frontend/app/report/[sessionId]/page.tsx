"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";

import { ApiError, getReport } from "@/lib/api-client";
import { exportElementToPdf } from "@/lib/export-pdf";
import type { InterviewReport } from "@/lib/types";
import { BackButton } from "@/components/ui/BackButton";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { CategoryScores } from "@/components/report/CategoryScores";
import { RoadmapList } from "@/components/report/RoadmapList";
import { ScoreCard } from "@/components/report/ScoreCard";

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mb-3 text-sm font-semibold tracking-wide text-muted uppercase">{children}</h2>
  );
}

function AiTag() {
  return (
    <span className="ml-2 rounded bg-accent/10 px-1.5 py-0.5 text-[10px] font-normal tracking-normal text-accent normal-case">
      AI-generated
    </span>
  );
}

export default function ReportPage() {
  const params = useParams<{ sessionId: string }>();
  const [report, setReport] = useState<InterviewReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const printableRef = useRef<HTMLDivElement>(null);

  async function handleDownloadPdf() {
    if (!printableRef.current) return;
    setIsExportingPdf(true);
    setExportError(null);
    try {
      await exportElementToPdf(printableRef.current, `intervue-ai-report-${params.sessionId}.pdf`);
    } catch {
      setExportError("Could not generate the PDF. Please try again.");
    } finally {
      setIsExportingPdf(false);
    }
  }

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
      <main className="relative flex flex-1 items-center justify-center px-6 text-center">
        <div className="absolute top-6 left-6">
          <BackButton />
        </div>
        <p className="text-danger">{error}</p>
      </main>
    );
  }

  if (!report) {
    return (
      <main className="relative flex flex-1 items-center justify-center px-6">
        <div className="absolute top-6 left-6">
          <BackButton />
        </div>
        <p className="text-muted">Generating your report...</p>
      </main>
    );
  }

  const sections = [
    <Card key="score">
      <ScoreCard overallScore={report.overall_score} readinessLevel={report.readiness_level} />
    </Card>,
    <Card key="categories">
      <SectionLabel>Category Scores</SectionLabel>
      <CategoryScores scores={report.category_scores} />
    </Card>,
    <Card key="summary">
      <SectionLabel>
        Recruiter Summary
        <AiTag />
      </SectionLabel>
      <p className="text-sm leading-relaxed">{report.recruiter_summary}</p>
    </Card>,
    <div key="strengths-improvements" className="grid gap-6 sm:grid-cols-2">
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
    </div>,
    <Card key="roadmap">
      <SectionLabel>
        Learning Roadmap
        <AiTag />
      </SectionLabel>
      <RoadmapList items={report.learning_roadmap} />
    </Card>,
  ];

  return (
    <main className="relative mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-6 py-10">
      <BackButton />
      <div ref={printableRef} className="flex flex-col gap-6 bg-background">
        <div>
          <h1 className="text-2xl font-semibold">Your Recruiter Report</h1>
          <p className="text-sm text-muted">
            Scores below are computed deterministically from your interview. The summary and
            roadmap are AI-generated based on those scores.
          </p>
        </div>

        {sections.map((section, index) => (
          <motion.div
            key={section.key}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: "easeOut", delay: index * 0.06 }}
          >
            {section}
          </motion.div>
        ))}
      </div>

      {exportError && <p className="text-center text-sm text-danger">{exportError}</p>}

      <div className="flex flex-wrap justify-center gap-4 pb-4">
        <Button variant="secondary" onClick={handleDownloadPdf} disabled={isExportingPdf}>
          {isExportingPdf ? "Preparing PDF..." : "Download PDF"}
        </Button>
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
