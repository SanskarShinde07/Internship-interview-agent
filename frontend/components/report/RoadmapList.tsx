import type { LearningRoadmapItem } from "@/lib/types";

const PRIORITY_COLORS: Record<string, string> = {
  HIGH: "text-red-600 dark:text-red-400",
  MEDIUM: "text-yellow-600 dark:text-yellow-400",
  LOW: "text-neutral-500",
};

export function RoadmapList({ items }: { items: LearningRoadmapItem[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-neutral-500">No specific gaps identified — nice work.</p>;
  }

  return (
    <ul className="flex flex-col gap-2">
      {items.map((item) => (
        <li
          key={item.topic}
          className="rounded-lg border border-neutral-200 p-3 dark:border-neutral-800"
        >
          <div className="flex items-center justify-between">
            <span className="font-medium">{item.topic.replace(/_/g, " ")}</span>
            <span className={`text-xs font-semibold ${PRIORITY_COLORS[item.priority] ?? ""}`}>
              {item.priority}
            </span>
          </div>
          <p className="text-sm text-neutral-500">{item.action}</p>
        </li>
      ))}
    </ul>
  );
}
