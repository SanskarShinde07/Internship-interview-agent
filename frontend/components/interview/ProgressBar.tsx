export function ProgressBar({
  asked,
  totalEstimate,
}: {
  asked: number;
  totalEstimate: number;
}) {
  const percent = Math.min(100, Math.round((asked / Math.max(totalEstimate, 1)) * 100));
  return (
    <div className="w-full">
      <div className="mb-1 flex justify-between text-xs text-muted">
        <span>Question {asked}</span>
        <span>~{totalEstimate} total (estimate)</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-hover">
        <div
          className="h-full rounded-full bg-accent transition-all"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
