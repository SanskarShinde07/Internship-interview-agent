import type { CoachMessageItem } from "@/lib/types";

export function MessageBubble({ message }: { message: CoachMessageItem }) {
  const isUser = message.role === "USER";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm ${
          isUser ? "bg-accent text-accent-foreground" : "bg-surface-hover text-foreground"
        }`}
      >
        {message.content}
      </div>
    </div>
  );
}
