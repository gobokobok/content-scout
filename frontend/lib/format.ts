export function formatNumber(n: number | null): string {
  if (n === null) return "—";
  return new Intl.NumberFormat("ru-RU").format(Math.round(n));
}

export function formatFollowers(n: number | null): string | null {
  if (n === null) return null;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(".", ",")} млн`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1).replace(".", ",")} тыс.`;
  return new Intl.NumberFormat("ru-RU").format(n);
}

export function formatPercent(n: number | null): string {
  if (n === null) return "—";
  return `${(n * 100).toFixed(1).replace(".", ",")}%`;
}

export type Virality = "high" | "medium" | "low";

// E5-S5: relative to that account's own median in the run, never an absolute/industry benchmark.
export const VIRALITY_STYLE: Record<Virality, string> = {
  high: "bg-success/10 text-success",
  medium: "border border-border bg-bg text-secondary",
  low: "text-secondary opacity-70",
};
