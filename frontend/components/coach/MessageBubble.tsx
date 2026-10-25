import { motion } from "framer-motion";

import type { CoachMessageItem } from "@/lib/types";

export function MessageBubble({ message }: { message: CoachMessageItem }) {
  const isUser = message.role === "USER";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2, ease: "easeOut" }}
        className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm ${
          isUser ? "bg-accent text-accent-foreground" : "bg-surface-hover text-foreground"
        }`}
      >
        {message.content}
      </motion.div>
    </div>
  );
}
