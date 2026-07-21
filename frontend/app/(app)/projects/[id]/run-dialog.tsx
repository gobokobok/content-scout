"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useRunTracker } from "@/lib/run-tracker";

const DAY_OPTIONS = [1, 2, 3, 4, 5, 6, 7];

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
  const [duration, setDuration] = useState(3);
  const [error, setError] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
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
      const created = await api.createRun(projectId, { duration_days: duration, account_ids: accountIds });
      track(created, projectId, projectName);
      setRunId(created.id);
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
          {!run && (
            <div className="flex flex-col gap-4 p-4">
              {/* Duration picker */}
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

              <p className="text-sm text-secondary">{t("accountsLabel", { count: accountsCount })}</p>

              {/* Token info note */}
              <p className="rounded-card border border-border bg-bg px-3 py-2.5 text-sm text-secondary">
                {t("tokenInfo")}
              </p>

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
                  {starting ? t("starting") : t("confirmButton")}
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
