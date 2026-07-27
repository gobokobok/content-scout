"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowUpRight,
  Calendar,
  Flame,
  HelpCircle,
  Lightbulb,
  MessageSquare,
  Quote,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";
import { api, ApiError, type DeepAnalysisResponse, type RunResponse } from "@/lib/api";
import { TabChip } from "@/components/ui";
import { SkeletonRows } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { DEEP_ANALYSIS_STATUS_DOT, DEEP_ANALYSIS_STATUS_PILL, VIRALITY_STYLE } from "@/lib/format";

type Tab = "stats" | "recommendations";

const POLL_INTERVAL_MS = 5000;

function formatDate(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function DeepAnalysisReportPage() {
  const t = useTranslations("DeepAnalysis");
  const params = useParams<{ id: string; analysisId: string }>();
  const router = useRouter();
  const { addToast } = useToast();

  const [tab, setTab] = useState<Tab>("stats");
  const [analysis, setAnalysis] = useState<DeepAnalysisResponse | null>(null);
  const [run, setRun] = useState<RunResponse | null>(null);

  const load = useCallback(async () => {
    try {
      const loaded = await api.getDeepAnalysis(params.analysisId);
      setAnalysis(loaded);
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }, [params.analysisId, t, addToast]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!analysis || analysis.status === "done" || analysis.status === "failed") return;
    const handle = setInterval(() => void load(), POLL_INTERVAL_MS);
    return () => clearInterval(handle);
  }, [analysis, load]);

  // Summary card needs the base run's account/publication counts — fetched once the analysis
  // (and thus its stable run_id) is known, not on every poll tick.
  useEffect(() => {
    if (!analysis?.run_id) return;
    api
      .getRun(analysis.run_id)
      .then(setRun)
      .catch(() => {});
  }, [analysis?.run_id]);

  const statusLabel: Record<DeepAnalysisResponse["status"], string> = {
    pending: t("statusPending"),
    extracting: t("statusExtracting"),
    synthesizing: t("statusSynthesizing"),
    done: t("statusDone"),
    failed: t("statusFailed"),
  };

  const viralityLabel: Record<"high" | "medium" | "low", string> = {
    high: t("viralityHigh"),
    medium: t("viralityMedium"),
    low: t("viralityLow"),
  };

  const stats = analysis?.report_stats ?? null;
  const recommendations = analysis?.report_recommendations ?? null;

  return (
    <div className="flex flex-col gap-4">
      <button
        onClick={() => router.push("/")}
        className="flex w-fit items-center gap-1 text-sm text-secondary hover:text-ink transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        {t("backToHistory")}
      </button>

      <div className="flex items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold text-ink">{t("reportTitle")}</h1>
        {analysis && (
          <span
            className={`inline-flex w-fit items-center gap-1.5 rounded-chip px-2.5 py-1 text-[11.5px] font-medium ${DEEP_ANALYSIS_STATUS_PILL[analysis.status]}`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${DEEP_ANALYSIS_STATUS_DOT[analysis.status]}`} />
            {statusLabel[analysis.status]}
          </span>
        )}
      </div>

      {analysis && (
        <p className="font-mono text-xs text-secondary">{formatDate(analysis.created_at)}</p>
      )}

      {!analysis && <SkeletonRows count={5} />}

      {analysis && analysis.status !== "done" && analysis.status !== "failed" && (
        <p className="text-sm text-secondary">{t("inProgress")}</p>
      )}

      {analysis && analysis.status === "failed" && (
        <p className="text-sm text-danger">{analysis.error_message || t("failedMessage")}</p>
      )}

      {analysis && analysis.status === "done" && (
        <div className="flex flex-col gap-4">
          <div className="flex gap-2">
            {(["stats", "recommendations"] as const).map((key) => (
              <TabChip key={key} active={tab === key} onClick={() => setTab(key)}>
                {key === "stats" ? t("statsTab") : t("recommendationsTab")}
              </TabChip>
            ))}
          </div>

          {stats?.comment_coverage_degraded && (
            <div className="flex items-start gap-2 rounded-card border border-warning/30 bg-accent-soft px-3.5 py-3">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
              <p className="text-sm text-accent">{t("thinDataNotice")}</p>
            </div>
          )}

          {tab === "stats" && (
            <div className="flex flex-col gap-4">
              <div className="flex flex-col divide-y divide-border rounded-card border border-border bg-card px-4">
                <div className="flex items-center justify-between gap-2 py-3">
                  <span className="text-sm text-secondary">{t("dateLabel")}</span>
                  <span className="text-sm font-medium text-ink">
                    {formatDate(analysis.created_at)}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-2 py-3">
                  <span className="text-sm text-secondary">{t("accountsAnalyzed")}</span>
                  <span className="text-sm font-medium text-ink">
                    {run?.progress_accounts ?? "—"}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-2 py-3">
                  <span className="text-sm text-secondary">{t("publicationsAnalyzed")}</span>
                  <span className="text-sm font-medium text-ink">
                    {run?.progress_items ?? "—"}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-2 py-3">
                  <span className="text-sm text-secondary">{t("tokensSpentLabel")}</span>
                  <span className="text-sm font-medium text-ink">{analysis.tokens_charged}</span>
                </div>
                <div className="flex items-center justify-between gap-2 py-3">
                  <span className="text-sm text-secondary">{t("commentsAnalyzedLabel")}</span>
                  <span className="text-sm font-medium text-ink">
                    {analysis.comments_analyzed_count ?? "—"}
                  </span>
                </div>
              </div>

              {(!stats ||
                (stats.topics.length === 0 &&
                  stats.formats.length === 0 &&
                  stats.hooks.length === 0)) && (
                <p className="text-sm text-secondary">{t("noStatsData")}</p>
              )}

              {stats && stats.topics.length > 0 && (
                <div className="rounded-card border border-border bg-card p-4">
                  <p className="mb-3 text-sm font-semibold text-ink">{t("topicsTitle")}</p>
                  <div className="flex flex-col gap-2">
                    {stats.topics.map((topic) => (
                      <div
                        key={topic.topic}
                        className="flex items-center justify-between gap-2 rounded-control border border-border p-2.5"
                      >
                        <div className="flex min-w-0 flex-col">
                          <span className="truncate text-sm font-medium text-ink">
                            {topic.topic}
                          </span>
                          <span className="font-mono text-xs text-secondary">
                            {t("topicFrequency", { count: topic.frequency })}
                          </span>
                        </div>
                        {topic.avg_virality !== "unknown" && (
                          <span
                            className={`inline-flex shrink-0 items-center gap-1 rounded-chip px-2 py-0.5 text-xs font-medium ${VIRALITY_STYLE[topic.avg_virality]}`}
                          >
                            {topic.avg_virality === "high" && <Flame className="h-3 w-3" />}
                            {viralityLabel[topic.avg_virality]}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {stats && (stats.formats.length > 0 || stats.hooks.length > 0) && (
                <div className="rounded-card border border-border bg-card p-4">
                  {stats.formats.length > 0 && (
                    <div className="mb-3">
                      <p className="mb-2 text-sm font-semibold text-ink">{t("formatsTitle")}</p>
                      <div className="flex flex-wrap gap-1.5">
                        {stats.formats.map((f) => (
                          <span
                            key={f.format}
                            className="inline-flex items-center gap-1 rounded-chip border border-border bg-bg px-2 py-0.5 text-xs text-secondary"
                          >
                            {f.format}
                            <span className="font-mono">{f.count}</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {stats.hooks.length > 0 && (
                    <div className="mb-3">
                      <p className="mb-2 text-sm font-semibold text-ink">{t("hooksTitle")}</p>
                      <div className="flex flex-wrap gap-1.5">
                        {stats.hooks.map((h) => (
                          <span
                            key={h.hook_type}
                            className="inline-flex items-center gap-1 rounded-chip border border-border bg-bg px-2 py-0.5 text-xs text-secondary"
                          >
                            {h.hook_type}
                            <span className="font-mono">{h.count}</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {stats.cta_share !== null && (
                    <div className="flex items-center justify-between gap-2 border-t border-border pt-3">
                      <span className="text-sm text-secondary">{t("ctaShareTitle")}</span>
                      <span className="font-mono text-sm font-medium text-ink">
                        {(stats.cta_share * 100).toFixed(0)}%
                      </span>
                    </div>
                  )}
                </div>
              )}

              {stats && stats.cadence_summary && (
                <div className="rounded-card border border-border bg-card p-4">
                  <p className="mb-1.5 text-sm font-semibold text-ink">{t("cadenceTitle")}</p>
                  <p className="text-sm text-secondary">{stats.cadence_summary}</p>
                </div>
              )}

              {stats && stats.sentiment_summary && (
                <div className="rounded-card border border-border bg-card p-4">
                  <p className="mb-1.5 flex items-center gap-1.5 text-sm font-semibold text-ink">
                    <MessageSquare className="h-4 w-4" />
                    {t("sentimentTitle")}
                  </p>
                  <p className="text-sm text-secondary">{stats.sentiment_summary}</p>
                  {stats.representative_quotes.length > 0 && (
                    <div className="mt-3 flex flex-col gap-2">
                      <p className="text-xs font-medium text-secondary">{t("quotesTitle")}</p>
                      {stats.representative_quotes.map((quote, idx) => (
                        <div
                          key={idx}
                          className="flex items-start gap-2 rounded-control bg-bg p-2.5 text-sm text-secondary"
                        >
                          <Quote className="mt-0.5 h-3.5 w-3.5 shrink-0 text-secondary" />
                          <span>{quote}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {tab === "recommendations" && (
            <div className="flex flex-col gap-4">
              {!recommendations && (
                <p className="text-sm text-secondary">{t("noRecommendationsData")}</p>
              )}

              {recommendations && recommendations.content_ideas.length > 0 && (
                <div className="flex flex-col gap-2">
                  <p className="text-sm font-semibold text-ink">{t("contentIdeasTitle")}</p>
                  {recommendations.content_ideas.map((idea, idx) => (
                    <div
                      key={idx}
                      className="flex flex-col gap-1.5 rounded-card border border-border bg-card p-3.5"
                    >
                      <div className="flex items-center gap-2">
                        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-soft text-accent">
                          <Lightbulb className="h-3.5 w-3.5" />
                        </span>
                        <span className="text-sm font-medium text-ink">{idea.topic}</span>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        <span className="inline-flex items-center rounded-chip border border-border bg-bg px-2 py-0.5 text-xs text-secondary">
                          {idea.format}
                        </span>
                        <span className="inline-flex items-center rounded-chip border border-border bg-bg px-2 py-0.5 text-xs text-secondary">
                          {idea.hook}
                        </span>
                      </div>
                      <p className="text-xs text-secondary">{idea.why}</p>
                    </div>
                  ))}
                </div>
              )}

              {recommendations &&
                (recommendations.do_more.length > 0 || recommendations.do_less.length > 0) && (
                  <div className="rounded-card border border-border bg-card p-4">
                    {recommendations.do_more.length > 0 && (
                      <div className="mb-3">
                        <p className="mb-1.5 flex items-center gap-1.5 text-sm font-semibold text-ink">
                          <ThumbsUp className="h-4 w-4" />
                          {t("doMoreTitle")}
                        </p>
                        <ul className="flex flex-col gap-1">
                          {recommendations.do_more.map((line, idx) => (
                            <li key={idx} className="text-sm text-secondary">
                              {line}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {recommendations.do_less.length > 0 && (
                      <div>
                        <p className="mb-1.5 flex items-center gap-1.5 text-sm font-semibold text-ink">
                          <ThumbsDown className="h-4 w-4" />
                          {t("doLessTitle")}
                        </p>
                        <ul className="flex flex-col gap-1">
                          {recommendations.do_less.map((line, idx) => (
                            <li key={idx} className="text-sm text-secondary">
                              {line}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

              {recommendations && recommendations.hook_templates.length > 0 && (
                <div className="rounded-card border border-border bg-card p-4">
                  <p className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-ink">
                    <Sparkles className="h-4 w-4" />
                    {t("hookTemplatesTitle")}
                  </p>
                  <div className="flex flex-col gap-1.5">
                    {recommendations.hook_templates.map((line, idx) => (
                      <p
                        key={idx}
                        className="rounded-control bg-bg px-2.5 py-2 text-sm text-secondary"
                      >
                        {line}
                      </p>
                    ))}
                  </div>
                </div>
              )}

              {recommendations && recommendations.faq_pack.length > 0 && (
                <div className="rounded-card border border-border bg-card p-4">
                  <p className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-ink">
                    <HelpCircle className="h-4 w-4" />
                    {t("faqPackTitle")}
                  </p>
                  <ul className="flex flex-col gap-1">
                    {recommendations.faq_pack.map((line, idx) => (
                      <li key={idx} className="text-sm text-secondary">
                        {line}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {recommendations && recommendations.posting_schedule && (
                <div className="rounded-card border border-border bg-card p-4">
                  <p className="mb-1.5 flex items-center gap-1.5 text-sm font-semibold text-ink">
                    <Calendar className="h-4 w-4" />
                    {t("postingScheduleTitle")}
                  </p>
                  <p className="text-sm text-secondary">{recommendations.posting_schedule}</p>
                </div>
              )}

              {recommendations && recommendations.steal_this.length > 0 && analysis && (
                <div className="flex flex-col gap-2">
                  <p className="text-sm font-semibold text-ink">{t("stealThisTitle")}</p>
                  {recommendations.steal_this.map((item, idx) => (
                    <Link
                      key={idx}
                      href={`/projects/${params.id}/runs/${analysis.run_id}?tab=publications`}
                      className="flex items-center gap-3 rounded-card border border-border bg-card p-3.5 transition-all active:scale-[0.98] hover:bg-bg"
                    >
                      <p className="min-w-0 flex-1 text-sm text-secondary">{item.reason}</p>
                      <ArrowUpRight className="h-4 w-4 shrink-0 text-accent" />
                    </Link>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
