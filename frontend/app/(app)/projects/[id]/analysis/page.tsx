"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { ArrowLeft, Sparkles, Users, TrendingUp, FileText, Plus } from "lucide-react";
import { api, ApiError, type DeepAnalysisResponse, type RunResponse } from "@/lib/api";
import { Card, Badge } from "@/components/ui";
import { SkeletonList } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { DEEP_ANALYSIS_STATUS_DOT, DEEP_ANALYSIS_STATUS_PILL } from "@/lib/format";
import { DeepAnalysisSheet } from "@/components/deep-analysis-sheet";

const TEASER_CARDS = [
  { icon: Users, key: "competitor" },
  { icon: TrendingUp, key: "run" },
  { icon: FileText, key: "publication" },
] as const;

const POLL_INTERVAL_MS = 5000;

function formatDate(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function AnalysisPage() {
  const t = useTranslations("Analysis");
  const tDeep = useTranslations("DeepAnalysis");
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { addToast } = useToast();

  const [view, setView] = useState<"teaser" | "history">("teaser");
  const [analyses, setAnalyses] = useState<DeepAnalysisResponse[] | null>(null);
  const [runs, setRuns] = useState<RunResponse[] | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      const [loadedAnalyses, loadedRuns] = await Promise.all([
        api.listDeepAnalyses(params.id),
        api.listRuns(params.id),
      ]);
      setAnalyses(loadedAnalyses);
      setRuns(loadedRuns);
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }, [params.id, t, addToast]);

  useEffect(() => {
    if (view === "history") void load();
  }, [view, load]);

  // Poll while any analysis is still extracting/synthesizing (E17-S6's "in-progress state").
  useEffect(() => {
    if (view !== "history" || !analyses) return;
    const hasInProgress = analyses.some(
      (a) => a.status !== "done" && a.status !== "failed",
    );
    if (!hasInProgress) return;
    const handle = setInterval(() => void load(), POLL_INTERVAL_MS);
    return () => clearInterval(handle);
  }, [view, analyses, load]);

  const doneRuns = (runs ?? []).filter((r) => r.status === "done");

  const statusLabel: Record<DeepAnalysisResponse["status"], string> = {
    pending: tDeep("statusPending"),
    extracting: tDeep("statusExtracting"),
    synthesizing: tDeep("statusSynthesizing"),
    done: tDeep("statusDone"),
    failed: tDeep("statusFailed"),
  };

  if (view === "history") {
    return (
      <div className="flex flex-col gap-4">
        <button
          onClick={() => setView("teaser")}
          className="flex w-fit items-center gap-1 text-sm text-secondary hover:text-ink transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          {tDeep("backToAnalysis")}
        </button>

        <div className="flex items-center justify-between gap-2">
          <h1 className="text-2xl font-semibold text-ink">{tDeep("historyTitle")}</h1>
          <button
            onClick={() => setSheetOpen(true)}
            className="flex items-center gap-1.5 rounded-chip bg-lime px-3.5 py-2 text-sm font-semibold text-ink shadow-[0_6px_16px_rgba(140,170,20,0.28)] transition-all active:scale-[0.98]"
          >
            <Plus className="h-4 w-4" />
            {tDeep("newAnalysisButton")}
          </button>
        </div>

        {analyses === null && <SkeletonList count={3} />}

        {analyses !== null && analyses.length === 0 && (
          <p className="text-sm text-secondary">{tDeep("noAnalyses")}</p>
        )}

        {analyses !== null && analyses.length > 0 && (
          <div className="flex flex-col gap-2">
            {analyses.map((analysis) => {
              const openable = analysis.status === "done";
              return (
                <div
                  key={analysis.id}
                  onClick={
                    openable
                      ? () => router.push(`/projects/${params.id}/deep-analyses/${analysis.id}`)
                      : undefined
                  }
                  className={`flex items-center justify-between gap-2 rounded-card border border-border bg-card px-4 py-3.5 transition-all active:scale-[0.99] ${
                    openable ? "cursor-pointer hover:bg-bg" : ""
                  }`}
                >
                  <div className="flex flex-col gap-1">
                    <span className="font-mono text-sm font-medium text-ink">
                      {formatDate(analysis.created_at)}
                    </span>
                    <span
                      className={`inline-flex w-fit items-center gap-1.5 rounded-chip px-2.5 py-1 text-[11.5px] font-medium ${DEEP_ANALYSIS_STATUS_PILL[analysis.status]}`}
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${DEEP_ANALYSIS_STATUS_DOT[analysis.status]}`}
                      />
                      {statusLabel[analysis.status]}
                    </span>
                  </div>
                  {openable && (
                    <span className="text-sm font-medium text-accent">{tDeep("openButton")}</span>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {sheetOpen && (
          <DeepAnalysisSheet
            projectId={params.id}
            doneRuns={doneRuns}
            onClose={() => setSheetOpen(false)}
            onCreated={(analysis) => {
              setSheetOpen(false);
              setAnalyses((prev) => (prev ? [analysis, ...prev] : [analysis]));
            }}
          />
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-8 px-4 py-16 text-center">
      <div className="flex flex-col items-center gap-6">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-accent-soft text-accent">
          <Sparkles className="h-8 w-8" />
        </div>
        <div className="max-w-sm">
          <h2 className="mb-2 text-lg font-semibold text-ink">{t("title")}</h2>
          <p className="text-sm leading-relaxed text-secondary">{t("comingSoon")}</p>
        </div>
      </div>

      <div className="grid w-full max-w-2xl gap-4 sm:grid-cols-3">
        {TEASER_CARDS.map(({ icon: Icon, key }) => {
          const enabled = key === "run";
          return (
            <Card
              key={key}
              onClick={enabled ? () => setView("history") : undefined}
              className={`flex flex-col items-center gap-3 p-5 text-center transition-all ${
                enabled
                  ? "cursor-pointer active:scale-[0.98] hover:bg-bg"
                  : "cursor-not-allowed opacity-60"
              }`}
              aria-disabled={!enabled}
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent-soft text-accent">
                <Icon className="h-5 w-5" />
              </div>
              <h3 className="text-sm font-semibold text-ink">{t(`cards.${key}.title`)}</h3>
              <p className="text-xs leading-relaxed text-secondary">
                {t(`cards.${key}.description`)}
              </p>
              {!enabled && <Badge>{t("cards.badge")}</Badge>}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
