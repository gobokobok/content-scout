"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { api, ApiError, type RunSummaryResponse } from "@/lib/api";

function formatTokens(input: number, output: number): string {
  const total = input + output;
  if (total >= 1_000_000) return `${(total / 1_000_000).toFixed(1)}M`;
  if (total >= 1_000) return `${(total / 1_000).toFixed(0)}K`;
  return String(total);
}

function formatTokensLong(input: number, output: number): string {
  return new Intl.NumberFormat("ru-RU").format(input + output);
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("ru-RU", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function monthLabel(year: number, month: number): string {
  return new Date(year, month, 1).toLocaleDateString("ru-RU", { month: "long", year: "numeric" });
}

function monthRange(year: number, month: number): { from: Date; to: Date } {
  return {
    from: new Date(year, month, 1),
    to: new Date(year, month + 1, 1),
  };
}

// ---------------------------------------------------------------------------
// Run detail bottom sheet
// ---------------------------------------------------------------------------
function RunDetailSheet({ run, onClose }: { run: RunSummaryResponse; onClose: () => void }) {
  const t = useTranslations("Usage");

  useEffect(() => {
    document.body.style.overflow = "hidden";
    const handle = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handle);
    return () => { document.removeEventListener("keydown", handle); document.body.style.overflow = ""; };
  }, [onClose]);

  const statusLabel: Record<string, string> = {
    pending: "Ожидание",
    scraping: "Сбор публикаций",
    summarizing: "Анализ",
    done: "Готово",
    failed: "Ошибка",
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40" onClick={onClose}>
      <div
        className="relative w-full max-h-[70vh] overflow-y-auto rounded-t-2xl bg-card shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drag handle */}
        <div className="flex justify-center px-4 pt-3 pb-2">
          <div className="h-1 w-10 rounded-full bg-border" />
        </div>
        <div className="border-b border-border px-4 pb-3">
          <p className="text-sm font-semibold text-ink">{run.project_name}</p>
        </div>
        <dl className="flex flex-col gap-0 divide-y divide-border px-4" style={{ paddingBottom: "max(1.5rem, env(safe-area-inset-bottom))" }}>
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-secondary">{t("detailType")}</dt>
            <dd className="text-sm font-medium text-ink">{t("runTypeAnalysis")}</dd>
          </div>
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-secondary">{t("detailRunId")}</dt>
            <dd className="font-mono text-xs text-secondary truncate ml-4">{run.id.slice(0, 8)}…</dd>
          </div>
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-secondary">{t("detailStarted")}</dt>
            <dd className="text-sm text-ink">{formatDateTime(run.created_at)}</dd>
          </div>
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-secondary">{t("detailStatus")}</dt>
            <dd className="text-sm text-ink">{statusLabel[run.status] ?? run.status}</dd>
          </div>
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-secondary">{t("detailPublications")}</dt>
            <dd className="text-sm font-medium text-ink">{run.progress_items}</dd>
          </div>
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-secondary">{t("detailTokens")}</dt>
            <dd className="text-sm font-medium text-ink tabular-nums">
              {formatTokensLong(run.total_input_tokens, run.total_output_tokens)}
            </dd>
          </div>
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-secondary">{t("detailTokensBreakdown")}</dt>
            <dd className="text-xs text-secondary tabular-nums">
              {new Intl.NumberFormat("ru-RU").format(run.total_input_tokens)} / {new Intl.NumberFormat("ru-RU").format(run.total_output_tokens)}
            </dd>
          </div>
        </dl>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Usage page
// ---------------------------------------------------------------------------
export default function UsagePage() {
  const t = useTranslations("Usage");

  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth());
  const [runs, setRuns] = useState<RunSummaryResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<RunSummaryResponse | null>(null);

  const load = useCallback(async () => {
    setRuns(null);
    setError(null);
    try {
      const { from, to } = monthRange(year, month);
      setRuns(await api.getMyRuns(from, to));
    } catch (err) {
      setError(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }, [year, month, t]);

  useEffect(() => { void load(); }, [load]);

  function prevMonth() {
    if (month === 0) { setYear((y) => y - 1); setMonth(11); }
    else setMonth((m) => m - 1);
  }

  function nextMonth() {
    const nextY = month === 11 ? year + 1 : year;
    const nextM = month === 11 ? 0 : month + 1;
    if (nextY > now.getFullYear() || (nextY === now.getFullYear() && nextM > now.getMonth())) return;
    setYear(nextY);
    setMonth(nextM);
  }

  const isCurrentMonth = year === now.getFullYear() && month === now.getMonth();
  const totalTokens = runs?.reduce((sum, r) => sum + r.total_input_tokens + r.total_output_tokens, 0) ?? 0;

  return (
    <main className="mx-auto max-w-2xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-semibold text-ink">{t("title")}</h1>

      {/* Month navigation */}
      <div className="mb-4 flex items-center gap-3">
        <button
          onClick={prevMonth}
          className="rounded-control border border-border p-2 text-secondary hover:bg-bg transition-colors"
          aria-label="Предыдущий месяц"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="flex-1 text-center text-sm font-medium text-ink capitalize">
          {monthLabel(year, month)}
        </span>
        <button
          onClick={nextMonth}
          disabled={isCurrentMonth}
          className="rounded-control border border-border p-2 text-secondary hover:bg-bg transition-colors disabled:opacity-30"
          aria-label="Следующий месяц"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      {error && <p className="mb-4 text-sm text-danger">{error}</p>}

      {/* Month summary */}
      {runs !== null && (
        <div className="mb-4 rounded-card border border-border bg-card px-4 py-3 flex items-center justify-between gap-2">
          <span className="text-sm text-secondary">{t("monthTotalTokens")}</span>
          <span className="text-sm font-semibold tabular-nums text-ink">
            {new Intl.NumberFormat("ru-RU").format(totalTokens)}
          </span>
        </div>
      )}

      {/* Loading state */}
      {runs === null && !error && (
        <p className="text-secondary text-sm">{t("loading")}</p>
      )}

      {/* Empty state */}
      {runs !== null && runs.length === 0 && (
        <p className="text-secondary">{t("empty")}</p>
      )}

      {/* Runs table */}
      {runs !== null && runs.length > 0 && (
        <div className="overflow-hidden rounded-card border border-border">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr>
                <th scope="col" className="bg-bg px-4 py-2 text-left font-medium text-secondary whitespace-nowrap">
                  {t("colDate")}
                </th>
                <th scope="col" className="bg-bg px-4 py-2 text-left font-medium text-secondary whitespace-nowrap">
                  {t("colProject")}
                </th>
                <th scope="col" className="bg-bg px-4 py-2 text-right font-medium text-secondary whitespace-nowrap">
                  {t("colTokens")}
                </th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr
                  key={r.id}
                  className="border-t border-border cursor-pointer hover:bg-bg transition-colors"
                  onClick={() => setSelectedRun(r)}
                >
                  <td className="px-4 py-3 whitespace-nowrap text-secondary tabular-nums text-xs">
                    {formatDate(r.created_at)}
                  </td>
                  <td className="px-4 py-3 text-ink max-w-[160px] truncate">
                    {r.project_name}
                  </td>
                  <td className="px-4 py-3 text-right font-medium tabular-nums text-ink whitespace-nowrap">
                    {formatTokens(r.total_input_tokens, r.total_output_tokens)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Run detail sheet */}
      {selectedRun && (
        <RunDetailSheet run={selectedRun} onClose={() => setSelectedRun(null)} />
      )}
    </main>
  );
}
