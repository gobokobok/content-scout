"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { ArrowLeft, Check, Coins, Users, X } from "lucide-react";
import { api, ApiError, type AccountResponse, type EstimateResponse } from "@/lib/api";
import { useRunTracker } from "@/lib/run-tracker";
import { formatFollowers } from "@/lib/format";
import { detectLocalTimezone } from "@/lib/telegram-webapp";
import { Segmented } from "@/components/ui";

const DAY_OPTIONS = [1, 2, 3, 4, 5, 6, 7];
const ITEM_LIMIT_OPTIONS = [5, 10, 15, 20, 30, 50];
const WEEKDAYS = [0, 1, 2, 3, 4, 5, 6] as const;
type ScopeMode = "days" | "count";
type LaunchMode = "now" | "schedule";
type View = "form" | "pickCompetitors";
type RepeatMode = "once" | "recurring";

function chipClass(active: boolean): string {
  return `h-10 min-w-10 rounded-[10px] px-2 font-mono text-[13px] font-medium transition-all active:scale-[0.98] ${
    active ? "bg-ink text-lime font-semibold" : "border border-border text-ink hover:bg-bg"
  }`;
}

export function RunDialog({
  projectId,
  projectName,
  accounts,
  runType = "stat_collection",
  onClose,
}: {
  projectId: string;
  projectName: string;
  accounts: AccountResponse[];
  runType?: "stat_collection" | "deep_analysis";
  onClose: () => void;
}) {
  const t = useTranslations("RunDialog");
  const { trackedRuns, track } = useRunTracker();
  const [view, setView] = useState<View>("form");
  const [scopeMode, setScopeMode] = useState<ScopeMode>("days");
  const [duration, setDuration] = useState(3);
  const [itemLimit, setItemLimit] = useState(10);
  const [allAccounts, setAllAccounts] = useState(true);
  const [selectedAccountIds, setSelectedAccountIds] = useState<string[]>([]);
  const [launchMode, setLaunchMode] = useState<LaunchMode>("now");
  const [repeatMode, setRepeatMode] = useState<RepeatMode>("recurring");
  const [selectedDays, setSelectedDays] = useState<number[]>([]);
  const [timeOfDay, setTimeOfDay] = useState("09:00");
  const [notifyEnabled, setNotifyEnabled] = useState(false);
  const [timezone] = useState(() => detectLocalTimezone());
  const [estimate, setEstimate] = useState<EstimateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [scheduled, setScheduled] = useState(false);
  const [starting, setStarting] = useState(false);

  const tracked = runId ? trackedRuns.find((tr) => tr.run.id === runId) : undefined;
  const run = tracked?.run ?? null;
  const accountIds = allAccounts ? undefined : selectedAccountIds;

  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = ""; };
  }, []);

  useEffect(() => {
    const handle = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handle);
    return () => document.removeEventListener("keydown", handle);
  }, [onClose]);

  useEffect(() => {
    if (run || scheduled) return;
    if (!allAccounts && selectedAccountIds.length === 0) {
      setEstimate(null);
      return;
    }
    let cancelled = false;
    const handle = setTimeout(() => {
      api
        .estimateRun(projectId, {
          duration_days: scopeMode === "days" ? duration : undefined,
          item_limit: scopeMode === "count" ? itemLimit : undefined,
          account_ids: accountIds,
        })
        .then((res) => { if (!cancelled) setEstimate(res); })
        .catch(() => { if (!cancelled) setEstimate(null); });
    }, 250);
    return () => { cancelled = true; clearTimeout(handle); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, scopeMode, duration, itemLimit, allAccounts, selectedAccountIds, run, scheduled]);

  function toggleAccount(id: string) {
    setSelectedAccountIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }

  function toggleDay(d: number) {
    if (repeatMode === "once") {
      setSelectedDays([d]);
      return;
    }
    setSelectedDays((prev) => (prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d]));
  }

  function onRepeatModeChange(mode: RepeatMode) {
    setRepeatMode(mode);
    if (mode === "once" && selectedDays.length > 1) {
      setSelectedDays((prev) => prev.slice(0, 1));
    }
  }

  async function onConfirm() {
    if (!allAccounts && selectedAccountIds.length === 0) {
      setError(t("selectCompetitorsError"));
      return;
    }
    if (launchMode === "schedule" && selectedDays.length === 0) {
      setError(t("selectDayError"));
      return;
    }
    setStarting(true);
    setError(null);
    try {
      if (launchMode === "schedule") {
        await api.createScheduledRun(projectId, {
          duration_days: scopeMode === "days" ? duration : undefined,
          item_limit: scopeMode === "count" ? itemLimit : undefined,
          account_ids: accountIds,
          run_type: runType,
          mode: repeatMode,
          days_of_week: selectedDays,
          time_of_day: `${timeOfDay}:00`,
          timezone,
          active: true,
          notify_enabled: notifyEnabled,
        });
        setScheduled(true);
      } else {
        const created = await api.createRun(projectId, {
          duration_days: scopeMode === "days" ? duration : undefined,
          item_limit: scopeMode === "count" ? itemLimit : undefined,
          account_ids: accountIds,
          run_type: runType,
        });
        track(created, projectId, projectName);
        setRunId(created.id);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.messageRu : t("genericError"));
    } finally {
      setStarting(false);
    }
  }

  const statusKey = run
    ? ({ pending: "statusPending", scraping: "statusScraping", summarizing: "statusSummarizing", done: "statusDone", failed: "statusFailed" } as const)[run.status]
    : null;

  const dialogTitle = runType === "deep_analysis" ? t("deepTitle") : t("title");

  if (view === "pickCompetitors") {
    return (
      <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center bg-black/40 p-0 md:p-4">
        <div className="relative flex max-h-[85vh] w-full flex-col overflow-hidden rounded-t-[22px] bg-card shadow-2xl md:max-w-md md:rounded-[22px]">
          <div className="flex shrink-0 justify-center px-4 pt-3 pb-2 md:hidden">
            <div className="h-1 w-10 rounded-full bg-border" />
          </div>
          <div className="flex shrink-0 items-center justify-between gap-2 border-b border-border px-4 pb-3">
            <button
              onClick={() => setView("form")}
              className="flex items-center gap-1 text-sm text-secondary transition-colors hover:text-ink"
            >
              <ArrowLeft className="h-4 w-4" />
              {t("backToForm")}
            </button>
            <p className="text-sm font-semibold text-ink">{t("selectCompetitorsTitle")}</p>
            <span className="w-[52px]" />
          </div>
          <div
            className="flex flex-col gap-3 overflow-y-auto p-4"
            style={{ paddingBottom: "max(1.5rem, env(safe-area-inset-bottom))" }}
          >
            <div className="flex flex-col overflow-hidden rounded-card border border-border">
              {accounts.length === 0 && (
                <p className="p-4 text-sm text-secondary">{t("noAccounts")}</p>
              )}
              {accounts.map((a, idx) => {
                const selected = selectedAccountIds.includes(a.id);
                return (
                  <button
                    key={a.id}
                    onClick={() => toggleAccount(a.id)}
                    className={`flex items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-bg ${
                      idx < accounts.length - 1 ? "border-b border-border" : ""
                    }`}
                  >
                    <span
                      className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors ${
                        selected ? "border-ink bg-ink text-lime" : "border-border text-transparent"
                      }`}
                    >
                      <Check className="h-3.5 w-3.5" />
                    </span>
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-full border border-border bg-bg">
                      {a.avatar_url ? (
                        // eslint-disable-next-line @next/next/no-img-element -- external CDN
                        <img src={a.avatar_url} alt="" className="h-full w-full object-cover" />
                      ) : (
                        <Users className="h-4 w-4 text-secondary" />
                      )}
                    </span>
                    <span className="flex min-w-0 flex-1 flex-col">
                      <span className="truncate text-sm font-medium text-ink">
                        {a.display_name || `@${a.handle}`}
                      </span>
                      <span className="truncate text-xs text-secondary">
                        @{a.handle}
                        {a.followers_count != null &&
                          ` · ${formatFollowers(a.followers_count)} ${t("followersShort")}`}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
            <button
              onClick={() => setView("form")}
              className="rounded-chip bg-lime px-4 py-3 text-sm font-semibold text-ink shadow-[0_8px_20px_rgba(140,170,20,0.30)] transition-all active:scale-[0.98]"
            >
              {t("selectedCompetitorsCount", { count: selectedAccountIds.length })} · {t("doneButton")}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end md:items-center justify-center bg-black/40 p-0 md:p-4"
      onClick={onClose}
    >
      <div
        className="relative flex max-h-[85vh] w-full flex-col overflow-hidden rounded-t-[22px] bg-card shadow-2xl md:max-w-md md:rounded-[22px]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex shrink-0 justify-center px-4 pt-3 pb-2 md:hidden">
          <div className="h-1 w-10 rounded-full bg-border" />
        </div>
        <div className="flex shrink-0 items-center justify-between gap-2 border-b border-border px-4 pb-3">
          <p className="text-sm font-semibold text-ink">{dialogTitle}</p>
          <button
            onClick={onClose}
            aria-label={t("minimize")}
            className="rounded-control p-1 text-secondary hover:bg-bg transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div
          className="overflow-y-auto"
          style={{ paddingBottom: "max(1.5rem, env(safe-area-inset-bottom))" }}
        >
          {!run && !scheduled && (
            <div className="flex flex-col gap-5 p-4">
              {runType === "deep_analysis" && (
                <p className="rounded-[10px] bg-accent-soft px-3 py-2.5 text-xs text-accent">
                  {t("deepHint")}
                </p>
              )}

              {/* Step 1 — analysis scope */}
              <div className="flex flex-col gap-2.5">
                <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-secondary">
                  {t("scopeStepLabel")}
                </span>
                <Segmented
                  value={scopeMode}
                  onChange={setScopeMode}
                  options={[
                    { value: "days", label: t("scopeModeDays") },
                    { value: "count", label: t("scopeModeCount") },
                  ]}
                />
                {scopeMode === "days" ? (
                  <div className="grid grid-cols-7 gap-1.5">
                    {DAY_OPTIONS.map((d) => (
                      <button key={d} onClick={() => setDuration(d)} className={chipClass(duration === d)}>
                        {d}
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-1.5">
                    {ITEM_LIMIT_OPTIONS.map((n) => (
                      <button key={n} onClick={() => setItemLimit(n)} className={chipClass(itemLimit === n)}>
                        {n}
                      </button>
                    ))}
                  </div>
                )}
                <p className="text-xs text-secondary">
                  {scopeMode === "days"
                    ? t("scopeDaysExplanation", { count: duration })
                    : t("scopeCountExplanation", { count: itemLimit })}
                </p>
              </div>

              {/* Step 2 — competitors */}
              <div className="flex flex-col gap-2.5 border-t border-border pt-5">
                <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-secondary">
                  {t("competitorsStepLabel")}
                </span>
                <Segmented
                  value={allAccounts ? "all" : "select"}
                  onChange={(v) => {
                    if (v === "all") setAllAccounts(true);
                    else { setAllAccounts(false); setView("pickCompetitors"); }
                  }}
                  options={[
                    { value: "all", label: t("allAccounts") },
                    { value: "select", label: t("selectCompetitorsButton") },
                  ]}
                />
                {!allAccounts && (
                  <button
                    onClick={() => setView("pickCompetitors")}
                    className="w-fit text-sm font-medium text-accent hover:underline"
                  >
                    {t("selectedCompetitorsCount", { count: selectedAccountIds.length })}
                  </button>
                )}
              </div>

              {/* Step 3 — when to run */}
              <div className="flex flex-col gap-2.5 border-t border-border pt-5">
                <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-secondary">
                  {t("launchModeLabel")}
                </span>
                <Segmented
                  value={launchMode}
                  onChange={setLaunchMode}
                  options={[
                    { value: "now", label: t("launchModeNow") },
                    { value: "schedule", label: t("launchModeSchedule") },
                  ]}
                />
                {launchMode === "schedule" && (
                  <div className="flex flex-col gap-3 rounded-[14px] bg-bg p-3">
                    <Segmented
                      value={repeatMode}
                      onChange={onRepeatModeChange}
                      options={[
                        { value: "once", label: t("repeatModeOnce") },
                        { value: "recurring", label: t("repeatModeRecurring") },
                      ]}
                    />
                    <div className="grid grid-cols-7 gap-1.5">
                      {WEEKDAYS.map((d) => (
                        <button key={d} onClick={() => toggleDay(d)} className={chipClass(selectedDays.includes(d))}>
                          {t(`weekday${d}`)}
                        </button>
                      ))}
                    </div>
                    <input
                      type="time"
                      value={timeOfDay}
                      onChange={(e) => setTimeOfDay(e.target.value)}
                      className="w-full rounded-control border border-border bg-card px-3 py-2 text-base text-ink focus:outline-none focus:ring-2 focus:ring-accent/30"
                    />
                    <p className="text-xs text-secondary">{t("timezoneHint", { timezone })}</p>
                    <p className="text-xs text-secondary">
                      {repeatMode === "once" ? t("repeatModeOnceHint") : t("repeatModeRecurringHint")}
                    </p>
                    <div className="flex items-center justify-between gap-2 border-t border-border pt-3">
                      <span className="text-sm font-medium text-ink">{t("notifyLabel")}</span>
                      <button
                        type="button"
                        role="switch"
                        aria-checked={notifyEnabled}
                        onClick={() => setNotifyEnabled((v) => !v)}
                        className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${
                          notifyEnabled ? "bg-lime" : "bg-border"
                        }`}
                      >
                        <span
                          className={`absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${
                            notifyEnabled ? "translate-x-5" : "translate-x-0"
                          }`}
                        />
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Cost estimate */}
              <div className="flex items-center justify-between gap-2 rounded-[14px] bg-accent-soft px-3.5 py-3">
                <span className="flex items-center gap-1.5 text-sm font-medium text-accent">
                  <Coins className="h-3.5 w-3.5" />
                  {t("costEstimateLabel")}
                </span>
                <span className="font-mono text-sm font-semibold text-accent">
                  {estimate ? t("costEstimateValue", { count: estimate.apify_units }) : "…"}
                </span>
              </div>

              {error && <p className="text-sm text-danger">{error}</p>}

              <button
                onClick={() => void onConfirm()}
                disabled={starting}
                className="rounded-chip bg-lime px-4 py-3.5 text-sm font-semibold text-ink shadow-[0_8px_20px_rgba(140,170,20,0.30)] transition-all active:scale-[0.98] disabled:opacity-50"
              >
                {starting
                  ? t("starting")
                  : launchMode === "now"
                    ? t("confirmButton")
                    : t("scheduleButton")}
              </button>
            </div>
          )}

          {scheduled && (
            <div className="flex flex-col gap-4 p-4">
              <p className="text-base font-medium text-ink">{t("scheduledTitle")}</p>
              <p className="text-sm text-secondary">{t("scheduledHint")}</p>
              <div className="flex gap-2">
                <Link
                  href={`/projects/${projectId}/scheduled`}
                  className="flex-1 rounded-chip border border-border px-4 py-2.5 text-center text-sm text-ink hover:bg-bg"
                >
                  {t("goToScheduled")}
                </Link>
                <button
                  onClick={onClose}
                  className="flex-1 rounded-chip bg-lime px-4 py-2.5 text-sm font-semibold text-ink"
                >
                  {t("close")}
                </button>
              </div>
            </div>
          )}

          {run && (
            <div className="flex flex-col gap-4 p-4">
              <p className="text-base font-medium text-ink">{statusKey && t(statusKey)}</p>
              {run.status === "summarizing" ? (
                <p className="text-sm text-secondary">
                  {t("summarizeProgress", { done: run.progress_summarized, total: run.progress_items })}
                </p>
              ) : (
                <p className="text-sm text-secondary">
                  {t("progress", { done: run.progress_accounts })}
                </p>
              )}
              {run.status === "failed" && run.error_message && (
                <p className="text-sm text-danger">{run.error_message}</p>
              )}
              {run.status !== "done" && run.status !== "failed" && (
                <p className="text-xs text-secondary">{t("backgroundHint")}</p>
              )}
              {runType === "deep_analysis" && run.status === "done" && (
                <p className="text-xs text-accent">{t("deepHint")}</p>
              )}
              <div className="flex gap-2">
                <button
                  onClick={onClose}
                  className="flex-1 rounded-chip bg-lime px-4 py-2.5 text-sm font-semibold text-ink"
                >
                  {run.status === "done" || run.status === "failed" ? t("close") : t("minimize")}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
