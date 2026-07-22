"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useRunTracker } from "@/lib/run-tracker";

const DAY_OPTIONS = [1, 2, 3, 4, 5, 6, 7];
const ITEM_LIMIT_OPTIONS = [5, 10, 15, 20, 30, 50];
const WEEKDAYS = [0, 1, 2, 3, 4, 5, 6] as const;
const DEFAULT_TIMEZONE = "Europe/Moscow";
type ScopeMode = "days" | "count";
type LaunchMode = "now" | "schedule";

export function RunDialog({
  projectId,
  projectName,
  accountIds,
  accountsCount,
  onClose,
}: {
  projectId: string;
  projectName: string;
  accountIds: string[] | undefined;
  accountsCount: number;
  onClose: () => void;
}) {
  const t = useTranslations("RunDialog");
  const { trackedRuns, track } = useRunTracker();
  const [scopeMode, setScopeMode] = useState<ScopeMode>("days");
  const [duration, setDuration] = useState(3);
  const [itemLimit, setItemLimit] = useState(10);
  const [launchMode, setLaunchMode] = useState<LaunchMode>("now");
  const [dayOfWeek, setDayOfWeek] = useState(0);
  const [timeOfDay, setTimeOfDay] = useState("09:00");
  const [error, setError] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [scheduled, setScheduled] = useState(false);
  const [starting, setStarting] = useState(false);

  const tracked = runId ? trackedRuns.find((tr) => tr.run.id === runId) : undefined;
  const run = tracked?.run ?? null;

  /* Body scroll lock */
  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = ""; };
  }, []);

  /* Escape to close — the run (if any) keeps going in the background regardless */
  useEffect(() => {
    const handle = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handle);
    return () => document.removeEventListener("keydown", handle);
  }, [onClose]);

  async function onConfirm() {
    setStarting(true);
    setError(null);
    try {
      if (launchMode === "schedule") {
        await api.createScheduledRun(projectId, {
          duration_days: scopeMode === "days" ? duration : undefined,
          item_limit: scopeMode === "count" ? itemLimit : undefined,
          account_ids: accountIds,
          day_of_week: dayOfWeek,
          time_of_day: `${timeOfDay}:00`,
          timezone: DEFAULT_TIMEZONE,
          active: true,
        });
        setScheduled(true);
      } else {
        const created = await api.createRun(projectId, {
          duration_days: scopeMode === "days" ? duration : undefined,
          item_limit: scopeMode === "count" ? itemLimit : undefined,
          account_ids: accountIds,
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

  return (
    /* Responsive: bottom of screen on mobile, centered on desktop */
    <div
      className="fixed inset-0 z-50 flex items-end md:items-center justify-center bg-black/40 p-0 md:p-4"
      onClick={onClose}
    >
      <div
        className="relative flex max-h-[80vh] w-full flex-col overflow-hidden rounded-t-2xl bg-card shadow-2xl md:max-w-md md:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drag handle — mobile only */}
        <div className="flex shrink-0 justify-center px-4 pt-3 pb-2 md:hidden">
          <div className="h-1 w-10 rounded-full bg-border" />
        </div>
        {/* Title */}
        <div className="flex shrink-0 items-center justify-between gap-2 border-b border-border px-4 pb-3">
          <p className="text-sm font-semibold text-ink">{t("title")}</p>
          <button
            onClick={onClose}
            aria-label={t("minimize")}
            className="rounded-control p-1 text-secondary hover:bg-bg transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        {/* Scrollable content */}
        <div
          className="overflow-y-auto"
          style={{ paddingBottom: "max(1.5rem, env(safe-area-inset-bottom))" }}
        >
          {!run && !scheduled && (
            <div className="flex flex-col gap-4 p-4">
              {/* Scope mode toggle: day window vs. last-N publications */}
              <div className="inline-flex self-start rounded-control border border-border p-0.5">
                {(["days", "count"] as ScopeMode[]).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setScopeMode(mode)}
                    className={`rounded-control px-3 py-1.5 text-sm font-medium transition-colors ${
                      scopeMode === mode
                        ? "bg-accent text-white"
                        : "text-secondary hover:text-ink"
                    }`}
                  >
                    {mode === "days" ? t("scopeModeDays") : t("scopeModeCount")}
                  </button>
                ))}
              </div>

              {/* Duration / item-count picker */}
              {scopeMode === "days" ? (
                <div className="flex flex-col gap-2">
                  <span className="text-sm font-medium text-secondary">{t("durationLabel")}</span>
                  <div className="flex flex-wrap gap-2">
                    {DAY_OPTIONS.map((d) => (
                      <button
                        key={d}
                        onClick={() => setDuration(d)}
                        className={`h-10 w-10 rounded-control text-sm font-medium transition-colors ${
                          duration === d
                            ? "bg-accent text-white"
                            : "border border-border text-ink hover:bg-bg"
                        }`}
                      >
                        {d}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="flex flex-col gap-2">
                  <span className="text-sm font-medium text-secondary">{t("itemLimitLabel")}</span>
                  <div className="flex flex-wrap gap-2">
                    {ITEM_LIMIT_OPTIONS.map((n) => (
                      <button
                        key={n}
                        onClick={() => setItemLimit(n)}
                        className={`h-10 min-w-10 rounded-control px-2 text-sm font-medium transition-colors ${
                          itemLimit === n
                            ? "bg-accent text-white"
                            : "border border-border text-ink hover:bg-bg"
                        }`}
                      >
                        {n}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <p className="text-sm text-secondary">{t("accountsLabel", { count: accountsCount })}</p>

              {/* Run-now / Schedule choice (E14-S4) */}
              <div className="flex flex-col gap-2">
                <span className="text-sm font-medium text-secondary">{t("launchModeLabel")}</span>
                <div className="inline-flex self-start rounded-control border border-border p-0.5">
                  {(["now", "schedule"] as LaunchMode[]).map((mode) => (
                    <button
                      key={mode}
                      onClick={() => setLaunchMode(mode)}
                      className={`rounded-control px-3 py-1.5 text-sm font-medium transition-colors ${
                        launchMode === mode
                          ? "bg-accent text-white"
                          : "text-secondary hover:text-ink"
                      }`}
                    >
                      {mode === "now" ? t("launchModeNow") : t("launchModeSchedule")}
                    </button>
                  ))}
                </div>
              </div>

              {launchMode === "schedule" && (
                <>
                  <div className="flex flex-col gap-2">
                    <span className="text-sm font-medium text-secondary">{t("dayOfWeekLabel")}</span>
                    <div className="flex flex-wrap gap-2">
                      {WEEKDAYS.map((d) => (
                        <button
                          key={d}
                          onClick={() => setDayOfWeek(d)}
                          className={`h-10 min-w-10 rounded-control px-2 text-sm font-medium transition-colors ${
                            dayOfWeek === d
                              ? "bg-accent text-white"
                              : "border border-border text-ink hover:bg-bg"
                          }`}
                        >
                          {t(`weekday${d}`)}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="flex flex-col gap-2">
                    <span className="text-sm font-medium text-secondary">{t("timeOfDayLabel")}</span>
                    <input
                      type="time"
                      value={timeOfDay}
                      onChange={(e) => setTimeOfDay(e.target.value)}
                      className="w-full rounded-control border border-border bg-card px-3 py-2 text-base text-ink focus:outline-none focus:ring-2 focus:ring-accent/30"
                    />
                  </div>
                </>
              )}

              {/* Token info note — only relevant for an immediate run */}
              {launchMode === "now" && (
                <p className="rounded-card border border-border bg-bg px-3 py-2.5 text-sm text-secondary">
                  {t("tokenInfo")}
                </p>
              )}

              {error && <p className="text-sm text-danger">{error}</p>}

              <div className="flex gap-2">
                <button
                  onClick={onClose}
                  className="flex-1 rounded-control border border-border px-4 py-2.5 text-sm text-ink hover:bg-bg"
                >
                  {t("cancel")}
                </button>
                <button
                  onClick={() => void onConfirm()}
                  disabled={starting}
                  className="flex-1 rounded-control bg-accent px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50"
                >
                  {starting
                    ? t("starting")
                    : launchMode === "now"
                      ? t("confirmButton")
                      : t("scheduleButton")}
                </button>
              </div>
            </div>
          )}

          {scheduled && (
            <div className="flex flex-col gap-4 p-4">
              <p className="text-base font-medium text-ink">{t("scheduledTitle")}</p>
              <p className="text-sm text-secondary">{t("scheduledHint")}</p>
              <div className="flex gap-2">
                <Link
                  href={`/projects/${projectId}/scheduled`}
                  className="flex-1 rounded-control border border-border px-4 py-2.5 text-center text-sm text-ink hover:bg-bg"
                >
                  {t("goToScheduled")}
                </Link>
                <button
                  onClick={onClose}
                  className="flex-1 rounded-control bg-accent px-4 py-2.5 text-sm font-medium text-white"
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
              <div className="flex gap-2">
                <button
                  onClick={onClose}
                  className="flex-1 rounded-control bg-accent px-4 py-2.5 text-sm font-medium text-white"
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
