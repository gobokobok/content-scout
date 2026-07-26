"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { ArrowLeft, CalendarRange, Copy, Check } from "lucide-react";
import { api, ApiError, type RunSummaryResponse, type UserResponse } from "@/lib/api";
import { BottomSheet } from "@/components/ui/bottom-sheet";

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("ru-RU", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function dayLabel(iso: string): string {
  const d = new Date(iso);
  const today = new Date();
  const sameYear = d.getFullYear() === today.getFullYear();
  return d
    .toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: sameYear ? undefined : "numeric" })
    .replace(/^./, (c) => c.toUpperCase());
}

function dayKey(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}

function monthLabel(year: number, month: number): string {
  return new Date(year, month, 1)
    .toLocaleDateString("ru-RU", { month: "long", year: "numeric" })
    .replace(/^./, (c) => c.toUpperCase());
}

function shortMonthLabel(year: number, month: number): string {
  return new Date(year, month, 1)
    .toLocaleDateString("ru-RU", { month: "long" })
    .replace(/^./, (c) => c.toUpperCase());
}

function monthRange(year: number, month: number): { from: Date; to: Date } {
  return { from: new Date(year, month, 1), to: new Date(year, month + 1, 1) };
}

function toMonthInputValue(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function monthNames(): string[] {
  return Array.from({ length: 12 }, (_, i) =>
    new Date(2000, i, 1).toLocaleDateString("ru-RU", { month: "long" }).replace(/^./, (c) => c.toUpperCase()),
  );
}

// ---------------------------------------------------------------------------
// Copy button for Run ID
// ---------------------------------------------------------------------------
function CopyButton({ value }: { value: string }) {
  const t = useTranslations("Usage");
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard unavailable
    }
  }

  return (
    <button
      onClick={() => void handleCopy()}
      className="ml-1 inline-flex shrink-0 items-center text-secondary hover:text-accent transition-colors"
      aria-label={t("copied")}
    >
      {copied ? <Check className="h-3.5 w-3.5 text-accent" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
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
    extracting: "Сбор данных",
    synthesizing: "Формирование отчёта",
    done: "Готово",
    failed: "Ошибка",
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40" onClick={onClose}>
      <div
        className="relative w-full max-h-[70vh] overflow-y-auto rounded-t-[22px] bg-card shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-center px-4 pt-3 pb-2">
          <div className="h-1 w-10 rounded-full bg-border" />
        </div>
        <div className="border-b border-border px-4 pb-3">
          <p className="text-sm font-semibold text-ink">{run.project_name}</p>
        </div>
        <dl className="flex flex-col gap-0 divide-y divide-border px-4" style={{ paddingBottom: "max(1.5rem, env(safe-area-inset-bottom))" }}>
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-secondary">{t("detailType")}</dt>
            <dd className="text-sm font-medium text-ink">
              {run.kind === "deep_analysis" ? t("runTypeDeepAnalysis") : t("runTypeAnalysis")}
            </dd>
          </div>
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-secondary">{t("detailRunId")}</dt>
            <dd className="flex items-center font-mono text-xs text-secondary ml-4">
              <span className="truncate max-w-[120px]">{run.id.slice(0, 8)}…</span>
              <CopyButton value={run.id} />
            </dd>
          </div>
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-secondary">{t("detailStarted")}</dt>
            <dd className="font-mono text-sm text-ink">{formatDateTime(run.created_at)}</dd>
          </div>
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-secondary">{t("detailStatus")}</dt>
            <dd className="text-sm text-ink">{statusLabel[run.status] ?? run.status}</dd>
          </div>
          {run.kind === "run" && (
            <div className="flex items-center justify-between py-3">
              <dt className="text-sm text-secondary">{t("detailPublications")}</dt>
              <dd className="font-mono text-sm font-medium text-ink">{run.progress_items}</dd>
            </div>
          )}
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-secondary">{t("detailTokens")}</dt>
            <dd className="font-mono text-sm font-medium text-ink tabular-nums">
              {new Intl.NumberFormat("ru-RU").format(run.tokens_charged)}
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

type PeriodSelection =
  | { kind: "quick"; monthsBack: 0 | 1 | 2 }
  | { kind: "custom"; from: string; to: string }; // "YYYY-MM"

export default function UsagePage() {
  const t = useTranslations("Usage");
  const router = useRouter();
  const now = new Date();

  const [selection, setSelection] = useState<PeriodSelection>({ kind: "quick", monthsBack: 0 });
  const [customSheetOpen, setCustomSheetOpen] = useState(false);
  const [draftFrom, setDraftFrom] = useState(toMonthInputValue(now));
  const [draftTo, setDraftTo] = useState(toMonthInputValue(now));
  const [runs, setRuns] = useState<RunSummaryResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<RunSummaryResponse | null>(null);
  const [me, setMe] = useState<UserResponse | null>(null);

  useEffect(() => {
    api.me().then(setMe).catch(() => null);
  }, []);

  const { from, to, label } = (() => {
    if (selection.kind === "quick") {
      const target = new Date(now.getFullYear(), now.getMonth() - selection.monthsBack, 1);
      const range = monthRange(target.getFullYear(), target.getMonth());
      return { ...range, label: monthLabel(target.getFullYear(), target.getMonth()) };
    }
    const [fy, fm] = selection.from.split("-").map(Number);
    const [ty, tm] = selection.to.split("-").map(Number);
    const range = { from: monthRange(fy, fm - 1).from, to: monthRange(ty, tm - 1).to };
    const label =
      fy === ty && fm === tm
        ? monthLabel(fy, fm - 1)
        : `${shortMonthLabel(fy, fm - 1)} ${fy} — ${monthLabel(ty, tm - 1)}`;
    return { ...range, label };
  })();

  const load = useCallback(async () => {
    setRuns(null);
    setError(null);
    try {
      setRuns(await api.getMyRuns(from, to));
    } catch (err) {
      setError(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [from.getTime(), to.getTime(), t]);

  useEffect(() => { void load(); }, [load]);

  const totalTokens = runs?.reduce((sum, r) => sum + r.tokens_charged, 0) ?? 0;

  const groups = (() => {
    if (!runs) return [];
    const sorted = [...runs].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    const map = new Map<string, { label: string; items: RunSummaryResponse[] }>();
    for (const r of sorted) {
      const key = dayKey(r.created_at);
      if (!map.has(key)) map.set(key, { label: dayLabel(r.created_at), items: [] });
      map.get(key)!.items.push(r);
    }
    return [...map.values()];
  })();

  const quickMonths: { monthsBack: 0 | 1 | 2 }[] = [{ monthsBack: 0 }, { monthsBack: 1 }, { monthsBack: 2 }];

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-4 p-4">
      <button
        onClick={() => router.push("/")}
        className="flex w-fit items-center gap-1 text-sm text-secondary transition-colors hover:text-ink"
      >
        <ArrowLeft className="h-4 w-4" />
        {t("back")}
      </button>

      <h1 className="text-2xl font-semibold tracking-tight text-ink">{t("title")}</h1>

      {/* Balance — hero card */}
      {me !== null && (
        <div className="flex flex-col gap-3.5 rounded-card bg-ink px-5 py-4 text-white">
          <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#9BA1AB]">
            {t("balanceLabel")}
          </span>
          <span className="font-mono text-[40px] font-semibold leading-none tracking-tight text-lime">
            {new Intl.NumberFormat("ru-RU").format(me.token_balance)}
          </span>
          <div className="flex items-center justify-between border-t border-[#2A2E36] pt-3">
            <span className="text-sm text-[#9BA1AB]">{t("spentThisPeriod")}</span>
            <span className="font-mono text-sm font-semibold text-white">
              {new Intl.NumberFormat("ru-RU").format(totalTokens)}
            </span>
          </div>
        </div>
      )}

      {/* Period selector */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5">
        {quickMonths.map(({ monthsBack }) => {
          const target = new Date(now.getFullYear(), now.getMonth() - monthsBack, 1);
          const active = selection.kind === "quick" && selection.monthsBack === monthsBack;
          return (
            <button
              key={monthsBack}
              onClick={() => setSelection({ kind: "quick", monthsBack })}
              className={`shrink-0 rounded-chip px-3.5 py-2 text-sm transition-all active:scale-[0.98] ${
                active ? "bg-ink font-semibold text-lime" : "border border-border bg-card font-medium text-secondary hover:text-ink"
              }`}
            >
              {shortMonthLabel(target.getFullYear(), target.getMonth())}
            </button>
          );
        })}
        <button
          onClick={() => {
            setDraftFrom(selection.kind === "custom" ? selection.from : toMonthInputValue(now));
            setDraftTo(selection.kind === "custom" ? selection.to : toMonthInputValue(now));
            setCustomSheetOpen(true);
          }}
          className={`shrink-0 inline-flex items-center gap-1.5 rounded-chip px-3.5 py-2 text-sm transition-all active:scale-[0.98] ${
            selection.kind === "custom" ? "bg-ink font-semibold text-lime" : "border border-border bg-card font-medium text-secondary hover:text-ink"
          }`}
        >
          <CalendarRange className="h-3.5 w-3.5" />
          {selection.kind === "custom" ? label : t("customPeriod")}
        </button>
      </div>

      <BottomSheet open={customSheetOpen} onClose={() => setCustomSheetOpen(false)} title={t("customPeriodTitle")}>
        <div className="flex flex-col gap-3 px-4 pb-4">
          {[
            { label: t("fromLabel"), value: draftFrom, onChange: setDraftFrom },
            { label: t("toLabel"), value: draftTo, onChange: setDraftTo },
          ].map(({ label, value, onChange }) => {
            const [y, m] = value.split("-").map(Number);
            return (
              <div key={label} className="flex flex-col gap-1.5">
                <span className="text-sm font-medium text-secondary">{label}</span>
                <div className="flex gap-2">
                  <select
                    value={m}
                    onChange={(e) => onChange(`${y}-${String(Number(e.target.value)).padStart(2, "0")}`)}
                    className="w-0 flex-[2] rounded-control border border-border bg-card px-3 py-2.5 text-base text-ink focus:outline-none focus:ring-2 focus:ring-accent/30"
                  >
                    {monthNames().map((name, idx) => (
                      <option key={name} value={idx + 1}>{name}</option>
                    ))}
                  </select>
                  <select
                    value={y}
                    onChange={(e) => onChange(`${e.target.value}-${String(m).padStart(2, "0")}`)}
                    className="w-0 flex-1 rounded-control border border-border bg-card px-3 py-2.5 text-base text-ink focus:outline-none focus:ring-2 focus:ring-accent/30"
                  >
                    {Array.from({ length: 5 }, (_, i) => now.getFullYear() - i).map((yr) => (
                      <option key={yr} value={yr}>{yr}</option>
                    ))}
                  </select>
                </div>
              </div>
            );
          })}
          <button
            onClick={() => {
              const orderedFrom = draftFrom <= draftTo ? draftFrom : draftTo;
              const orderedTo = draftFrom <= draftTo ? draftTo : draftFrom;
              setSelection({ kind: "custom", from: orderedFrom, to: orderedTo });
              setCustomSheetOpen(false);
            }}
            className="rounded-chip bg-lime px-4 py-3 text-sm font-semibold text-ink shadow-[0_8px_20px_rgba(140,170,20,0.30)] transition-all active:scale-[0.98]"
          >
            {t("apply")}
          </button>
        </div>
      </BottomSheet>

      {error && <p className="text-sm text-danger">{error}</p>}

      {/* Loading */}
      {runs === null && !error && (
        <div className="flex flex-col gap-2">
          <div className="h-[72px] animate-pulse rounded-card bg-border/60" />
          <div className="h-[72px] animate-pulse rounded-card bg-border/60" />
        </div>
      )}

      {/* Empty */}
      {runs !== null && runs.length === 0 && (
        <p className="rounded-card border border-border bg-card px-4 py-6 text-center text-sm text-secondary">
          {t("empty")}
        </p>
      )}

      {/* Grouped run list */}
      {runs !== null && runs.length > 0 && (
        <div className="flex flex-col gap-4">
          {groups.map((g) => (
            <div key={g.label} className="flex flex-col gap-1.5">
              <span className="px-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-secondary">
                {g.label}
              </span>
              <div className="flex flex-col overflow-hidden rounded-card border border-border bg-card">
                {g.items.map((r, idx) => (
                  <button
                    key={r.id}
                    onClick={() => setSelectedRun(r)}
                    className={`flex items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-bg ${
                      idx < g.items.length - 1 ? "border-b border-border" : ""
                    }`}
                  >
                    <span className="w-11 shrink-0 font-mono text-xs text-secondary">
                      {formatTime(r.created_at)}
                    </span>
                    <span className="min-w-0 flex-1 truncate text-sm font-medium text-ink">
                      {r.project_name}
                      {r.kind === "deep_analysis" && (
                        <span className="ml-1.5 text-xs font-normal text-secondary">
                          · {t("runTypeDeepAnalysis")}
                        </span>
                      )}
                    </span>
                    <span className="shrink-0 font-mono text-sm font-semibold text-ink">
                      −{new Intl.NumberFormat("ru-RU").format(r.tokens_charged)}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedRun && <RunDetailSheet run={selectedRun} onClose={() => setSelectedRun(null)} />}
    </main>
  );
}
