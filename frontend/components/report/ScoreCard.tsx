const READINESS_LABELS: Record<string, string> = {
  NOT_READY: "Not Ready",
  DEVELOPING: "Developing",
  READY: "Ready",
  STRONG: "Strong",
};

const READINESS_COLORS: Record<string, string> = {
  NOT_READY: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
  DEVELOPING: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300",
  READY: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  STRONG: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
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
        <div className="text-sm text-neutral-500">out of 100 — deterministic score</div>
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
