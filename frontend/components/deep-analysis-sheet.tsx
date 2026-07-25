"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Check, Coins, FileText, X } from "lucide-react";
import {
  api,
  ApiError,
  type DeepAnalysisResponse,
  type RunResponse,
} from "@/lib/api";

function formatRunDate(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`;
}

export function DeepAnalysisSheet({
  projectId,
  doneRuns,
  onClose,
  onCreated,
}: {
  projectId: string;
  doneRuns: RunResponse[];
  onClose: () => void;
  onCreated: (analysis: DeepAnalysisResponse) => void;
}) {
  const t = useTranslations("DeepAnalysis");
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [estimateTokens, setEstimateTokens] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, []);

  useEffect(() => {
    const handle = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handle);
    return () => document.removeEventListener("keydown", handle);
  }, [onClose]);

  useEffect(() => {
    if (!selectedRunId) {
      setEstimateTokens(null);
      return;
    }
    let cancelled = false;
    setEstimateTokens(null);
    api
      .estimateDeepAnalysis(projectId, selectedRunId)
      .then((res) => {
        if (!cancelled) setEstimateTokens(res.tokens);
      })
      .catch(() => {
        if (!cancelled) setEstimateTokens(null);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, selectedRunId]);

  async function onConfirm() {
    if (!selectedRunId) return;
    setStarting(true);
    setError(null);
    try {
      const analysis = await api.createDeepAnalysis(projectId, selectedRunId);
      onCreated(analysis);
    } catch (err) {
      setError(err instanceof ApiError ? err.messageRu : t("genericError"));
    } finally {
      setStarting(false);
    }
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
          <p className="text-sm font-semibold text-ink">{t("sheetTitle")}</p>
          <button
            onClick={onClose}
            aria-label={t("close")}
            className="rounded-control p-1 text-secondary hover:bg-bg transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div
          className="flex flex-col gap-4 overflow-y-auto p-4"
          style={{ paddingBottom: "max(1.5rem, env(safe-area-inset-bottom))" }}
        >
          <div className="flex flex-col gap-2.5">
            <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-secondary">
              {t("pickRunLabel")}
            </span>
            {doneRuns.length === 0 && (
              <p className="text-sm text-secondary">{t("noDoneRuns")}</p>
            )}
            <div className="flex flex-col overflow-hidden rounded-card border border-border">
              {doneRuns.map((run, idx) => {
                const selected = selectedRunId === run.id;
                return (
                  <button
                    key={run.id}
                    onClick={() => setSelectedRunId(run.id)}
                    className={`flex items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-bg ${
                      idx < doneRuns.length - 1 ? "border-b border-border" : ""
                    }`}
                  >
                    <span
                      className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors ${
                        selected ? "border-ink bg-ink text-lime" : "border-border text-transparent"
                      }`}
                    >
                      <Check className="h-3.5 w-3.5" />
                    </span>
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-border bg-bg text-secondary">
                      <FileText className="h-4 w-4" />
                    </span>
                    <span className="flex min-w-0 flex-1 flex-col">
                      <span className="truncate text-sm font-medium text-ink">
                        {formatRunDate(run.created_at)}
                      </span>
                      <span className="truncate text-xs text-secondary">
                        {t("runItemsCount", { count: run.progress_items })}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {selectedRunId && (
            <div className="flex items-center justify-between gap-2 rounded-[14px] bg-accent-soft px-3.5 py-3">
              <span className="flex items-center gap-1.5 text-sm font-medium text-accent">
                <Coins className="h-3.5 w-3.5" />
                {t("costEstimateLabel")}
              </span>
              <span className="font-mono text-sm font-semibold text-accent">
                {estimateTokens !== null ? t("costEstimateValue", { count: estimateTokens }) : "…"}
              </span>
            </div>
          )}

          {error && <p className="text-sm text-danger">{error}</p>}

          <button
            onClick={() => void onConfirm()}
            disabled={!selectedRunId || starting}
            className="rounded-chip bg-lime px-4 py-3.5 text-sm font-semibold text-ink shadow-[0_8px_20px_rgba(140,170,20,0.30)] transition-all active:scale-[0.98] disabled:opacity-50"
          >
            {starting ? t("starting") : t("confirmButton")}
          </button>
        </div>
      </div>
    </div>
  );
}
