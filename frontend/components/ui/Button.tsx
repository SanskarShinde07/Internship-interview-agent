import type { ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary";
}

export function Button({ variant = "primary", className = "", ...props }: ButtonProps) {
  const base =
    "rounded-full px-6 py-3 font-medium transition disabled:cursor-not-allowed disabled:opacity-40";
  const styles =
    variant === "primary"
      ? "bg-accent text-accent-foreground hover:bg-accent-hover"
      : "border border-border text-foreground hover:bg-surface-hover";

  return <button className={`${base} ${styles} ${className}`} {...props} />;
}
