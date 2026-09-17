export function ScoreBar({ label, score }: { label: string; score: number }) {
  const percent = Math.max(0, Math.min(100, score));
  const color = score >= 80 ? "bg-green-500" : score >= 50 ? "bg-yellow-500" : "bg-red-500";

  return (
    <div>
      <div className="mb-1 flex justify-between text-xs">
        <span>{label.replace(/_/g, " ")}</span>
        <span className="text-neutral-500">{Math.round(score)}</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-neutral-200 dark:bg-neutral-800">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}
