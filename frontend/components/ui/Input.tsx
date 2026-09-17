import type { InputHTMLAttributes } from "react";

export function Input({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`rounded-lg border border-border bg-background px-3 py-2 text-base text-foreground outline-none placeholder:text-muted focus:border-accent ${className}`}
      {...props}
    />
  );
}
