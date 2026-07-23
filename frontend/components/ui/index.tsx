import { type ButtonHTMLAttributes, type InputHTMLAttributes, type TextareaHTMLAttributes, forwardRef } from "react";

type ButtonVariant = "primary" | "dark" | "secondary" | "ghost" | "danger";

const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary: "rounded-chip bg-lime text-ink shadow-[0_8px_20px_rgba(140,170,20,0.30)] hover:opacity-90",
  dark: "rounded-chip bg-ink text-lime hover:opacity-90",
  secondary: "rounded-chip border border-border bg-card text-ink hover:bg-bg",
  ghost: "rounded-control text-secondary hover:text-ink",
  danger: "rounded-control text-danger hover:underline",
};

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      className={`inline-flex items-center justify-center px-4 py-2.5 text-sm font-semibold transition-all active:scale-[0.98] disabled:opacity-50 disabled:active:scale-100 ${BUTTON_VARIANTS[variant]} ${className}`}
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
  success: "bg-success-soft text-success",
  warning: "bg-accent-soft text-accent",
  danger: "bg-danger-soft text-danger",
};

export function tabChipClass(active: boolean, className = ""): string {
  return `inline-block whitespace-nowrap rounded-chip px-3.5 py-1.5 text-sm font-medium transition-all active:scale-[0.98] ${
    active ? "bg-ink text-white font-semibold" : "border border-border text-secondary hover:text-ink"
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

export function Segmented<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string }[];
}) {
  return (
    <div className="inline-flex w-full gap-0.5 rounded-chip bg-[#E9EBE6] p-[3px]">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={`flex-1 rounded-chip px-3 py-2 text-sm transition-all active:scale-[0.98] ${
            value === opt.value ? "bg-ink font-semibold text-white" : "font-medium text-secondary hover:text-ink"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
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
