"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { api, ApiError, type EstimateResponse, type RunResponse } from "@/lib/api";

const POLL_INTERVAL_MS = 2000;

export function RunDialog({
  projectId,
  accountIds,
  accountsCount,
  onClose,
}: {
  projectId: string;
  accountIds: string[] | undefined;
  accountsCount: number;
  onClose: () => void;
}) {
  const t = useTranslations("RunDialog");
  const [duration, setDuration] = useState(3);
  const [estimate, setEstimate] = useState<EstimateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [run, setRun] = useState<RunResponse | null>(null);
  const [starting, setStarting] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let cancelled = false;
    setEstimate(null);
    api
      .estimateRun(projectId, { duration_days: duration, account_ids: accountIds })
      .then((e) => {
        if (!cancelled) setEstimate(e);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.messageRu : t("genericError"));
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, duration, accountIds, t]);

  useEffect(() => {
    if (!run || run.status === "done" || run.status === "failed") {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }
    pollRef.current = setInterval(async () => {
      try {
        const updated = await api.getRun(run.id);
        setRun(updated);
      } catch {
        // transient poll failure — try again next tick
      }
    }, POLL_INTERVAL_MS);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [run]);

  async function onConfirm() {
    setStarting(true);
    setError(null);
    try {
      const created = await api.createRun(projectId, {
        duration_days: duration,
        account_ids: accountIds,
      });
      setRun(created);
    } catch (err) {
      setError(err instanceof ApiError ? err.messageRu : t("genericError"));
    } finally {
      setStarting(false);
    }
  }

  const statusKey = run
    ? ({
        pending: "statusPending",
        scraping: "statusScraping",
        summarizing: "statusSummarizing",
        done: "statusDone",
        failed: "statusFailed",
      } as const)[run.status]
    : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-card bg-card p-6 shadow-lg">
        <h2 className="mb-4 text-lg font-semibold text-ink">{t("title")}</h2>

        {!run && (
          <div className="flex flex-col gap-4">
            <label className="flex flex-col gap-1">
              <span className="text-sm text-secondary">{t("durationLabel")}</span>
              <input
                type="number"
                min={1}
                max={7}
                value={duration}
                onChange={(e) =>
                  setDuration(Math.min(7, Math.max(1, Number(e.target.value) || 1)))
                }
                className="rounded-control border border-border bg-bg px-3 py-2 text-ink focus:outline-none focus:ring-2 focus:ring-accent/30"
              />
            </label>

            <p className="text-sm text-secondary">{t("accountsLabel", { count: accountsCount })}</p>

            {estimate ? (
              <div className="flex flex-col gap-1 rounded-card border border-border bg-bg p-3 text-sm text-ink">
                <span>{t("estimateApify", { units: estimate.apify_units })}</span>
                <span>
                  {t("estimateTokens", {
                    input: estimate.claude_input_tokens,
                    output: estimate.claude_output_tokens,
                  })}
                </span>
                <span className="font-medium">
                  {t("estimateCost", { cost: estimate.estimated_cost_usd })}
                </span>
              </div>
            ) : (
              <p className="text-sm text-secondary">{t("estimateLoading")}</p>
            )}

            {error && <p className="text-sm text-danger">{error}</p>}

            <div className="flex justify-end gap-2">
              <button
                onClick={onClose}
                className="rounded-control border border-border px-4 py-2 text-sm text-ink hover:bg-bg"
              >
                {t("cancel")}
              </button>
              <button
                onClick={onConfirm}
                disabled={starting || !estimate}
                className="rounded-control bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                {starting ? t("starting") : t("confirmButton")}
              </button>
            </div>
          </div>
        )}

        {run && (
          <div className="flex flex-col gap-3">
            <p className="text-base font-medium text-ink">{statusKey && t(statusKey)}</p>
            {run.status === "summarizing" ? (
              <p className="text-sm text-secondary">
                {t("summarizeProgress", {
                  done: run.progress_summarized,
                  total: run.progress_items,
                })}
              </p>
            ) : (
              <p className="text-sm text-secondary">
                {t("progress", { done: run.progress_accounts })}
              </p>
            )}
            {run.status === "done" && (
              <p className="text-sm text-secondary">
                {t("tokenTotals", {
                  input: run.total_input_tokens,
                  output: run.total_output_tokens,
                })}
              </p>
            )}
            {run.status === "failed" && run.error_message && (
              <p className="text-sm text-danger">{run.error_message}</p>
            )}
            {(run.status === "done" || run.status === "failed") && (
              <div className="flex justify-end">
                <button
                  onClick={onClose}
                  className="rounded-control bg-accent px-4 py-2 text-sm font-medium text-white"
                >
                  {t("close")}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
