"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { ArrowLeft, CalendarRange, ChevronLeft, ChevronRight, Copy, Check, Funnel, Plus } from "lucide-react";
import { api, ApiError, type RunSummaryResponse, type UserResponse } from "@/lib/api";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { useToast } from "@/components/ui/toast";
import { isTelegramContext, openTelegramInvoice } from "@/lib/telegram-webapp";

const QUICK_PURCHASE_AMOUNTS = [1000, 2000, 5000];
const MIN_PURCHASE_TOKENS = 300;

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

function monthShortNames(): string[] {
  return monthNames().map((name) => name.slice(0, 3).toUpperCase());
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
          <p className="text-sm font-semibold text-ink">{t("detailsHeader")}</p>
        </div>
        <dl className="flex flex-col gap-0 divide-y divide-border px-4" style={{ paddingBottom: "max(1.5rem, env(safe-area-inset-bottom))" }}>
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-secondary">{t("detailType")}</dt>
            <dd className="text-sm font-medium text-ink">
              {run.kind === "deep_analysis" ? t("taskTypeAnalysis") : t("taskTypeReview")}
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
          <div className="flex items-center justify-between py-3">
            <dt className="text-sm text-secondary">{t("detailPublications")}</dt>
            <dd className="font-mono text-sm font-medium text-ink">{run.progress_items}</dd>
          </div>
          {run.kind === "deep_analysis" && (
            <div className="flex items-center justify-between py-3">
              <dt className="text-sm text-secondary">{t("detailCommentsAnalyzed")}</dt>
              <dd className="font-mono text-sm font-medium text-ink">
                {run.comments_analyzed_count ?? 0}
              </dd>
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

type LineFilter = "all" | "usage" | "topup";

export default function UsagePage() {
  const t = useTranslations("Usage");
  const router = useRouter();
  const { addToast } = useToast();
  const now = new Date();

  const [selection, setSelection] = useState<PeriodSelection>({ kind: "quick", monthsBack: 0 });
  const [customSheetOpen, setCustomSheetOpen] = useState(false);
  const [draftFrom, setDraftFrom] = useState(toMonthInputValue(now));
  const [draftTo, setDraftTo] = useState(toMonthInputValue(now));
  const [runs, setRuns] = useState<RunSummaryResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<RunSummaryResponse | null>(null);
  const [me, setMe] = useState<UserResponse | null>(null);
  const [lineFilter, setLineFilter] = useState<LineFilter>("all");
  const [filterSheetOpen, setFilterSheetOpen] = useState(false);
  const [pickerYear, setPickerYear] = useState(now.getFullYear());
  const [pickerPhase, setPickerPhase] = useState<"start" | "end">("start");
  const [purchaseSheetOpen, setPurchaseSheetOpen] = useState(false);
  const [purchaseAmount, setPurchaseAmount] = useState<number | null>(QUICK_PURCHASE_AMOUNTS[0]);
  const [purchaseCustomText, setPurchaseCustomText] = useState("");
  const [purchasing, setPurchasing] = useState(false);

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

  const draftLabel = (() => {
    const [fy, fm] = draftFrom.split("-").map(Number);
    const [ty, tm] = draftTo.split("-").map(Number);
    return fy === ty && fm === tm
      ? monthLabel(fy, fm - 1)
      : `${shortMonthLabel(fy, fm - 1)} ${fy} — ${monthLabel(ty, tm - 1)}`;
  })();

  function openPurchaseSheet() {
    setPurchaseAmount(QUICK_PURCHASE_AMOUNTS[0]);
    setPurchaseCustomText("");
    setPurchaseSheetOpen(true);
  }

  function pickQuickPurchaseAmount(value: number) {
    setPurchaseAmount(value);
    setPurchaseCustomText("");
  }

  function onPurchaseCustomTextChange(value: string) {
    setPurchaseCustomText(value);
    const n = Number(value);
    setPurchaseAmount(value !== "" && Number.isFinite(n) ? Math.floor(n) : null);
  }

  const purchaseValid = purchaseAmount !== null && purchaseAmount >= MIN_PURCHASE_TOKENS;

  async function handlePurchase() {
    if (!purchaseValid || purchaseAmount === null) return;
    if (!isTelegramContext()) {
      addToast(t("purchaseRequiresTelegram"));
      return;
    }
    setPurchasing(true);
    try {
      const invoice = await api.createPurchaseInvoice(purchaseAmount);
      const outcome = await openTelegramInvoice(invoice.invoice_url);
      if (outcome === "paid") {
        addToast(t("purchaseSuccess"), "success");
        setPurchaseSheetOpen(false);
        const freshMe = await api.me().catch(() => null);
        if (freshMe) setMe(freshMe);
        void load();
      } else if (outcome === "failed") {
        addToast(t("purchaseFailed"));
      }
      // "cancelled"/"pending": user backed out of the sheet, or Telegram is still processing —
      // neither is an error worth a toast.
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    } finally {
      setPurchasing(false);
    }
  }

  function openCustomSheet() {
    const initFrom = selection.kind === "custom" ? selection.from : toMonthInputValue(now);
    const initTo = selection.kind === "custom" ? selection.to : toMonthInputValue(now);
    setDraftFrom(initFrom);
    setDraftTo(initTo);
    setPickerYear(Number(initFrom.split("-")[0]));
    setPickerPhase("start");
    setCustomSheetOpen(true);
  }

  function pickMonth(month: number) {
    const value = `${pickerYear}-${String(month).padStart(2, "0")}`;
    if (pickerPhase === "start") {
      setDraftFrom(value);
      setDraftTo(value);
      setPickerPhase("end");
    } else {
      if (value < draftFrom) {
        setDraftTo(draftFrom);
        setDraftFrom(value);
      } else {
        setDraftTo(value);
      }
      setPickerPhase("start");
    }
  }

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

  // Every existing ledger line is a spend ("usage") — top-ups are not tracked yet, so that
  // filter option always yields an empty list until a real top-up flow lands.
  const filteredRuns = runs === null ? null : lineFilter === "topup" ? [] : runs;

  const groups = (() => {
    if (!filteredRuns) return [];
    const sorted = [...filteredRuns].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    const map = new Map<string, { label: string; items: RunSummaryResponse[] }>();
    for (const r of sorted) {
      const key = dayKey(r.created_at);
      if (!map.has(key)) map.set(key, { label: dayLabel(r.created_at), items: [] });
      map.get(key)!.items.push(r);
    }
    return [...map.values()];
  })();

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-4 p-4">
      <button
        onClick={() => router.push("/")}
        className="flex w-fit items-center gap-1 text-sm text-secondary transition-colors hover:text-ink"
      >
        <ArrowLeft className="h-4 w-4" />
        {t("back")}
      </button>

      {/* Balance — hero card */}
      {me !== null && (
        <div className="flex flex-col gap-3.5 rounded-card bg-ink px-5 py-4 text-white">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-semibold uppercase tracking-[0.06em] text-[#9BA1AB]">
              {t("title")}
            </span>
            <button
              onClick={openPurchaseSheet}
              aria-label={t("buyTokensLabel")}
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-lime text-ink transition-all active:scale-[0.95]"
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-[40px] font-semibold leading-none tracking-tight text-lime">
              {new Intl.NumberFormat("ru-RU").format(me.token_balance)}
            </span>
            <span className="text-sm font-medium text-[#9BA1AB]">{t("balanceLabel")}</span>
          </div>
          <div className="flex items-center justify-between border-t border-[#2A2E36] pt-3">
            <span className="text-sm text-[#9BA1AB]">{t("spentThisPeriod")}</span>
            <span className="font-mono text-sm font-semibold text-white">
              {new Intl.NumberFormat("ru-RU").format(totalTokens)}
            </span>
          </div>
        </div>
      )}

      <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink">{t("usageHeader")}</h2>

      {/* Period + filter selector */}
      <div className="flex items-center justify-between gap-1.5">
        <button
          onClick={openCustomSheet}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-chip bg-ink px-3.5 py-2 text-sm font-semibold text-lime transition-all active:scale-[0.98]"
        >
          <CalendarRange className="h-3.5 w-3.5" />
          {label}
        </button>
        <button
          onClick={() => setFilterSheetOpen(true)}
          aria-label={t("filterLabel")}
          className={`inline-flex items-center justify-center rounded-control border p-2 transition-colors ${
            lineFilter !== "all" ? "border-accent/30 bg-accent-soft text-accent" : "border-border text-secondary hover:bg-bg"
          }`}
        >
          <Funnel className="h-4 w-4" />
        </button>
      </div>

      <BottomSheet open={filterSheetOpen} onClose={() => setFilterSheetOpen(false)} title={t("filterSheetTitle")}>
        <div className="flex flex-col gap-1 px-4 pb-4">
          {([
            { value: "all", label: t("filterAll") },
            { value: "usage", label: t("filterUsage") },
            { value: "topup", label: t("filterTopup") },
          ] as { value: LineFilter; label: string }[]).map((opt) => (
            <button
              key={opt.value}
              onClick={() => {
                setLineFilter(opt.value);
                setFilterSheetOpen(false);
              }}
              className={`flex items-center justify-between rounded-control px-3.5 py-3 text-left text-sm transition-colors ${
                lineFilter === opt.value ? "bg-bg font-semibold text-ink" : "font-medium text-secondary hover:text-ink"
              }`}
            >
              {opt.label}
              {lineFilter === opt.value && <Check className="h-4 w-4 text-accent" />}
            </button>
          ))}
        </div>
      </BottomSheet>

      <BottomSheet open={customSheetOpen} onClose={() => setCustomSheetOpen(false)}>
        <div className="-mt-3 flex flex-col items-center gap-1.5 bg-ink px-4 py-5 text-white">
          <span className="text-xs font-semibold uppercase tracking-[0.08em] text-[#9BA1AB]">
            {t("customPeriodTitle")}
          </span>
          <span className="text-xl font-semibold tracking-tight">{draftLabel}</span>
          <div className="flex items-center gap-4 pt-1">
            <button
              onClick={() => setPickerYear((y) => y - 1)}
              aria-label={t("prevYear")}
              className="text-[#9BA1AB] transition-colors hover:text-white"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
            <span className="font-mono text-lg font-semibold text-lime">{pickerYear}</span>
            <button
              onClick={() => setPickerYear((y) => y + 1)}
              aria-label={t("nextYear")}
              className="text-[#9BA1AB] transition-colors hover:text-white"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2 px-4 py-4">
          {monthShortNames().map((name, idx) => {
            const monthNum = idx + 1;
            const key = `${pickerYear}-${String(monthNum).padStart(2, "0")}`;
            const selected = key >= draftFrom && key <= draftTo;
            return (
              <button
                key={name}
                onClick={() => pickMonth(monthNum)}
                className={`flex items-center justify-center rounded-chip py-3 text-sm font-semibold transition-all active:scale-[0.98] ${
                  selected ? "bg-ink text-lime" : "text-ink hover:bg-bg"
                }`}
              >
                {name}
              </button>
            );
          })}
        </div>

        <div className="flex items-center justify-end gap-2 px-4 pb-4 pt-1">
          <button
            onClick={() => setCustomSheetOpen(false)}
            className="rounded-chip px-4 py-2.5 text-sm font-semibold text-secondary transition-colors hover:text-ink"
          >
            {t("cancel")}
          </button>
          <button
            onClick={() => {
              const orderedFrom = draftFrom <= draftTo ? draftFrom : draftTo;
              const orderedTo = draftFrom <= draftTo ? draftTo : draftFrom;
              setSelection({ kind: "custom", from: orderedFrom, to: orderedTo });
              setCustomSheetOpen(false);
            }}
            className="rounded-chip bg-lime px-4 py-2.5 text-sm font-semibold text-ink shadow-[0_8px_20px_rgba(140,170,20,0.30)] transition-all active:scale-[0.98]"
          >
            {t("apply")}
          </button>
        </div>
      </BottomSheet>

      <BottomSheet
        open={purchaseSheetOpen}
        onClose={() => setPurchaseSheetOpen(false)}
        title={t("buyTokensLabel")}
      >
        <div className="flex flex-col gap-4 px-4 pb-4">
          <div className="flex gap-2">
            {QUICK_PURCHASE_AMOUNTS.map((amount) => (
              <button
                key={amount}
                onClick={() => pickQuickPurchaseAmount(amount)}
                className={`flex-1 rounded-chip border px-3 py-2.5 text-center font-mono text-sm font-semibold transition-colors ${
                  purchaseCustomText === "" && purchaseAmount === amount
                    ? "border-ink bg-ink text-lime"
                    : "border-border text-ink hover:bg-bg"
                }`}
              >
                {new Intl.NumberFormat("ru-RU").format(amount)}
              </button>
            ))}
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="purchase-custom-amount" className="text-sm text-secondary">
              {t("purchaseCustomLabel")}
            </label>
            <input
              id="purchase-custom-amount"
              type="number"
              inputMode="numeric"
              min={MIN_PURCHASE_TOKENS}
              step={1}
              placeholder={String(MIN_PURCHASE_TOKENS)}
              value={purchaseCustomText}
              onChange={(e) => onPurchaseCustomTextChange(e.target.value)}
              className="rounded-control border border-border bg-card px-3.5 py-2.5 font-mono text-sm text-ink outline-none focus:border-ink"
            />
            {purchaseCustomText !== "" && !purchaseValid && (
              <p className="text-xs text-danger">
                {t("purchaseBelowMinimum", { min: MIN_PURCHASE_TOKENS })}
              </p>
            )}
          </div>

          {purchaseValid && purchaseAmount !== null && (
            <p className="text-sm text-secondary">
              {t("purchasePrice", { amount: new Intl.NumberFormat("ru-RU").format(purchaseAmount) })}
            </p>
          )}

          <button
            onClick={() => void handlePurchase()}
            disabled={!purchaseValid || purchasing}
            className="rounded-chip bg-lime px-4 py-3 text-center text-sm font-semibold text-ink shadow-[0_8px_20px_rgba(140,170,20,0.30)] transition-all active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {purchasing ? t("loading") : t("purchaseConfirm")}
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
      {filteredRuns !== null && filteredRuns.length === 0 && (
        <p className="rounded-card border border-border bg-card px-4 py-6 text-center text-sm text-secondary">
          {lineFilter === "topup" ? t("emptyTopup") : t("empty")}
        </p>
      )}

      {/* Grouped run list */}
      {filteredRuns !== null && filteredRuns.length > 0 && (
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
                      {r.kind === "deep_analysis" ? t("taskTypeAnalysis") : t("taskTypeReview")}
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
