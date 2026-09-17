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
      <div className="mb-1 flex justify-between text-xs text-neutral-500">
        <span>Question {asked}</span>
        <span>~{totalEstimate} total (estimate)</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-neutral-200 dark:bg-neutral-800">
        <div
          className="h-full rounded-full bg-neutral-900 transition-all dark:bg-white"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
