import type { DeepAnalysisResponse, RunResponse } from "@/lib/api";

type RunStatus = RunResponse["status"];
type DeepAnalysisStatus = DeepAnalysisResponse["status"];

// Shared "dot + soft chip" treatment for run status, used on Details' last-run
// card, the Результаты run list, and anywhere else a run status is shown.
export const RUN_STATUS_PILL: Record<RunStatus, string> = {
  done: "bg-success-soft text-success",
  failed: "bg-danger-soft text-danger",
  pending: "bg-accent-soft text-accent",
  scraping: "bg-accent-soft text-accent",
  summarizing: "bg-accent-soft text-accent",
};

export const RUN_STATUS_DOT: Record<RunStatus, string> = {
  done: "bg-success",
  failed: "bg-danger",
  pending: "bg-accent",
  scraping: "bg-accent",
  summarizing: "bg-accent",
};

// Same "dot + soft chip" treatment as RUN_STATUS_PILL/DOT, for E17's deep-analysis status
// (pending/extracting/synthesizing map to the same in-progress accent chip as a run's
// pending/scraping/summarizing — the report page cares about done/failed, not which sub-step).
export const DEEP_ANALYSIS_STATUS_PILL: Record<DeepAnalysisStatus, string> = {
  done: "bg-success-soft text-success",
  failed: "bg-danger-soft text-danger",
  pending: "bg-accent-soft text-accent",
  extracting: "bg-accent-soft text-accent",
  synthesizing: "bg-accent-soft text-accent",
};

export const DEEP_ANALYSIS_STATUS_DOT: Record<DeepAnalysisStatus, string> = {
  done: "bg-success",
  failed: "bg-danger",
  pending: "bg-accent",
  extracting: "bg-accent",
  synthesizing: "bg-accent",
};

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
