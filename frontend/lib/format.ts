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
// Heat scale (D31): high = inverse chip (ink bg, lime text) — the scan-anchor in a feed;
// medium = soft accent; low = neutral gray, never red (low performance isn't an error).
export const VIRALITY_STYLE: Record<Virality, string> = {
  high: "bg-ink text-lime",
  medium: "bg-accent-soft text-accent",
  low: "bg-bg text-secondary border border-border",
};
