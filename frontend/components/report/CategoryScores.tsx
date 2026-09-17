const CATEGORY_LABELS: Record<string, string> = {
  python: "Python",
  machine_learning: "Machine Learning",
  nlp: "NLP",
  problem_solving: "Problem Solving",
  communication: "Communication",
  project_understanding: "Project Understanding",
};

export function CategoryScores({ scores }: { scores: Record<string, number | null> }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {Object.entries(scores).map(([key, value]) => (
        <div key={key} className="rounded-lg bg-neutral-50 p-3 dark:bg-neutral-800">
          <div className="text-xs text-neutral-500">{CATEGORY_LABELS[key] ?? key}</div>
          <div className="text-lg font-semibold">{value !== null ? Math.round(value) : "—"}</div>
        </div>
      ))}
    </div>
  );
}
