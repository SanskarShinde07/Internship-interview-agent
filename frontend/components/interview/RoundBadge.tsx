const ROUND_LABELS: Record<string, string> = {
  INTRODUCTION: "Introduction",
  PYTHON: "Python",
  MACHINE_LEARNING: "Machine Learning",
  NLP: "NLP",
  PROJECT_DISCUSSION: "Project Discussion",
  SCENARIO: "Scenario",
  HR: "Behavioral",
};

export function RoundBadge({ round }: { round: string }) {
  return (
    <span className="inline-block rounded-full bg-accent/10 px-3 py-1 text-xs font-medium tracking-wide text-accent uppercase">
      {ROUND_LABELS[round] ?? round}
    </span>
  );
}
