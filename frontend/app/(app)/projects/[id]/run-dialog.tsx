"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { api, ApiError, type EstimateResponse, type RunResponse } from "@/lib/api";
import { BottomSheet } from "@/components/ui/bottom-sheet";

const POLL_INTERVAL_MS = 2000;

const DAY_OPTIONS = [1, 2, 3, 4, 5, 6, 7];

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

  const runInProgress = run && run.status !== "done" && run.status !== "failed";
  const statusKey = run
    ? ({
        pending: "statusPending",
        scraping: "statusScraping",
        summarizing: "statusSummarizing",
        done: "statusDone",
        failed: "statusFailed",
      } as const)[run.status]
    : null;

  function safeClose() {
    if (!runInProgress) onClose();
  }

  return (
    <BottomSheet open onClose={safeClose} title={t("title")}>
      {!run && (
        <div className="flex flex-col gap-4 p-4">
          {/* Duration picker */}
          <div className="flex flex-col gap-2">
            <span className="text-sm font-medium text-secondary">{t("durationLabel")}</span>
            <div className="flex gap-2 flex-wrap">
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

          {/* Cost estimate */}
          {estimate ? (
            <div className="flex flex-col gap-1.5 rounded-card border border-border bg-bg p-3 text-sm">
              <span className="text-ink">{t("estimateApify", { units: estimate.apify_units })}</span>
              <span className="text-ink">
                {t("estimateTokens", {
                  input: estimate.claude_input_tokens,
                  output: estimate.claude_output_tokens,
                })}
              </span>
              <span className="font-semibold text-ink">
                {t("estimateCost", { cost: estimate.estimated_cost_usd })}
              </span>
            </div>
          ) : (
            <p className="text-sm text-secondary">{t("estimateLoading")}</p>
          )}

          {error && <p className="text-sm text-danger">{error}</p>}

          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="rounded-control border border-border px-4 py-2.5 text-sm text-ink hover:bg-bg flex-1"
            >
              {t("cancel")}
            </button>
            <button
              onClick={() => void onConfirm()}
              disabled={starting || !estimate}
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
            <button
              onClick={onClose}
              className="rounded-control bg-accent px-4 py-2.5 text-sm font-medium text-white"
            >
              {t("close")}
            </button>
          )}
        </div>
      )}
    </BottomSheet>
  );
}
