export function ScoreBar({ label, score }: { label: string; score: number }) {
  const percent = Math.max(0, Math.min(100, score));
  const color = score >= 80 ? "bg-success" : score >= 50 ? "bg-warning" : "bg-danger";

  return (
    <div>
      <div className="mb-1 flex justify-between text-xs">
        <span>{label.replace(/_/g, " ")}</span>
        <span className="text-muted">{Math.round(score)}</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-hover">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}
