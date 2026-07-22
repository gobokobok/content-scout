import { type ButtonHTMLAttributes, type InputHTMLAttributes, type TextareaHTMLAttributes, forwardRef } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-accent text-white hover:opacity-90",
  secondary: "border border-border text-ink hover:bg-bg",
  ghost: "text-secondary hover:text-ink",
  danger: "text-danger hover:underline",
};

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      className={`inline-flex items-center justify-center rounded-control px-4 py-2 text-sm font-medium transition-opacity disabled:opacity-50 ${BUTTON_VARIANTS[variant]} ${className}`}
      {...props}
    />
  );
}

export function Card({
  className = "",
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`rounded-card border border-border bg-card ${className}`} {...props}>
      {children}
    </div>
  );
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className = "", ...props }, ref) => (
    <input
      ref={ref}
      className={`w-full rounded-control border border-border bg-card px-3 py-2 text-base text-ink placeholder:text-secondary focus:outline-none focus:ring-2 focus:ring-accent/30 ${className}`}
      {...props}
    />
  ),
);
Input.displayName = "Input";

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className = "", ...props }, ref) => (
  <textarea
    ref={ref}
    className={`w-full rounded-control border border-border bg-card px-3 py-2 text-base text-ink placeholder:text-secondary focus:outline-none focus:ring-2 focus:ring-accent/30 ${className}`}
    {...props}
  />
));
Textarea.displayName = "Textarea";

type BadgeVariant = "default" | "success" | "warning" | "danger";

const BADGE_VARIANTS: Record<BadgeVariant, string> = {
  default: "bg-accent-soft text-accent",
  success: "bg-success/10 text-success",
  warning: "bg-warning/10 text-warning",
  danger: "bg-danger/10 text-danger",
};

export function tabChipClass(active: boolean, className = ""): string {
  return `inline-block whitespace-nowrap rounded-chip px-3.5 py-1.5 text-sm font-medium transition-colors ${
    active ? "bg-accent text-white" : "border border-border text-secondary hover:text-ink"
  } ${className}`;
}

export function TabChip({
  active,
  className = "",
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { active: boolean }) {
  return (
    <button className={tabChipClass(active, className)} {...props}>
      {children}
    </button>
  );
}

export function Badge({
  variant = "default",
  className = "",
  children,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { variant?: BadgeVariant }) {
  return (
    <span
      className={`inline-flex items-center rounded-chip px-2 py-0.5 text-xs font-medium ${BADGE_VARIANTS[variant]} ${className}`}
      {...props}
    >
      {children}
    </span>
  );
}
