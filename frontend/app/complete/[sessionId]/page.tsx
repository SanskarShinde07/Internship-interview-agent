"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

import { Card } from "@/components/ui/Card";

export default function CompletePage() {
  const params = useParams<{ sessionId: string }>();
  const router = useRouter();

  useEffect(() => {
    const timer = setTimeout(() => {
      router.push(`/report/${params.sessionId}`);
    }, 1800);
    return () => clearTimeout(timer);
  }, [params.sessionId, router]);

  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 px-6 text-center">
      <Card className="max-w-md">
        <h1 className="mb-2 text-xl font-semibold">Interview complete</h1>
        <p className="text-sm text-muted">Generating your recruiter report and analytics...</p>
      </Card>
    </main>
  );
}
