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
    <span className="inline-block rounded-full bg-neutral-100 px-3 py-1 text-xs font-medium tracking-wide text-neutral-600 uppercase dark:bg-neutral-800 dark:text-neutral-300">
      {ROUND_LABELS[round] ?? round}
    </span>
  );
}
