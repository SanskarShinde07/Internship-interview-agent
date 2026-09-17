import type { LearningRoadmapItem } from "@/lib/types";

const PRIORITY_COLORS: Record<string, string> = {
  HIGH: "text-danger",
  MEDIUM: "text-warning",
  LOW: "text-muted",
};

export function RoadmapList({ items }: { items: LearningRoadmapItem[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-muted">No specific gaps identified — nice work.</p>;
  }

  return (
    <ul className="flex flex-col gap-2">
      {items.map((item) => (
        <li key={item.topic} className="rounded-lg border border-border p-3">
          <div className="flex items-center justify-between">
            <span className="font-medium">{item.topic.replace(/_/g, " ")}</span>
            <span className={`text-xs font-semibold ${PRIORITY_COLORS[item.priority] ?? ""}`}>
              {item.priority}
            </span>
          </div>
          <p className="text-sm text-muted">{item.action}</p>
        </li>
      ))}
    </ul>
  );
}
