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

export function ScoreCard({
  overallScore,
  readinessLevel,
}: {
  overallScore: number;
  readinessLevel: string;
}) {
  return (
    <div className="flex items-center gap-6">
      <div className="text-5xl font-bold">{overallScore}</div>
      <div>
        <div className="text-sm text-muted">out of 100 — deterministic score</div>
        <span
          className={`mt-1 inline-block rounded-full px-3 py-1 text-xs font-semibold ${
            READINESS_COLORS[readinessLevel] ?? ""
          }`}
        >
          {READINESS_LABELS[readinessLevel] ?? readinessLevel}
        </span>
      </div>
    </div>
  );
}
