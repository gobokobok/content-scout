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
      <div className="w-full max-w-md rounded-lg bg-white p-6 dark:bg-gray-950">
        <h2 className="mb-4 text-lg font-semibold">{t("title")}</h2>

        {!run && (
          <div className="flex flex-col gap-4">
            <label className="flex flex-col gap-1">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {t("durationLabel")}
              </span>
              <input
                type="number"
                min={1}
                max={7}
                value={duration}
                onChange={(e) =>
                  setDuration(Math.min(7, Math.max(1, Number(e.target.value) || 1)))
                }
                className="rounded-md border border-gray-300 px-3 py-2 dark:border-gray-700 dark:bg-gray-900"
              />
            </label>

            <p className="text-sm text-gray-600 dark:text-gray-400">
              {t("accountsLabel", { count: accountsCount })}
            </p>

            {estimate ? (
              <div className="flex flex-col gap-1 rounded-md border border-gray-200 p-3 text-sm dark:border-gray-800">
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
              <p className="text-sm text-gray-600 dark:text-gray-400">{t("estimateLoading")}</p>
            )}

            {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

            <div className="flex justify-end gap-2">
              <button
                onClick={onClose}
                className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-700"
              >
                {t("cancel")}
              </button>
              <button
                onClick={onConfirm}
                disabled={starting || !estimate}
                className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-gray-900"
              >
                {starting ? t("starting") : t("confirmButton")}
              </button>
            </div>
          </div>
        )}

        {run && (
          <div className="flex flex-col gap-3">
            <p className="text-base font-medium">{statusKey && t(statusKey)}</p>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {t("progress", { done: run.progress_accounts })}
            </p>
            {run.status === "failed" && run.error_message && (
              <p className="text-sm text-red-600 dark:text-red-400">{run.error_message}</p>
            )}
            {(run.status === "done" || run.status === "failed") && (
              <div className="flex justify-end">
                <button
                  onClick={onClose}
                  className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white dark:bg-white dark:text-gray-900"
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
