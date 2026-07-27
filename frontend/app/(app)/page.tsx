"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { ArrowLeft, CalendarClock, Plus } from "lucide-react";
import {
  api,
  ApiError,
  type AccountResponse,
  type ProjectResponse,
  type RunFeedItem,
  type ScheduledFeedItem,
} from "@/lib/api";
import { RUN_STATUS_DOT, RUN_STATUS_PILL } from "@/lib/format";
import { SkeletonList } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { RunDialog } from "@/components/run-dialog";
import { RunTypePickerSheet } from "@/components/run-type-picker-sheet";

type View = "feed" | "schedule";
type RunTypeFilter = "all" | "stat_collection" | "deep_analysis";
type RunType = "stat_collection" | "deep_analysis";

const IN_PROGRESS_STATUSES = new Set(["pending", "scraping", "summarizing"]);
const POLL_MS = 5000;

const WEEKDAY_KEYS = [
  "weekday0Short",
  "weekday1Short",
  "weekday2Short",
  "weekday3Short",
  "weekday4Short",
  "weekday5Short",
  "weekday6Short",
] as const;

function formatDate(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function RunFeedPage() {
  const t = useTranslations("RunFeed");
  const router = useRouter();
  const { addToast } = useToast();

  const [view, setView] = useState<View>("feed");
  const [filter, setFilter] = useState<RunTypeFilter>("all");
  const [runs, setRuns] = useState<RunFeedItem[] | null>(null);
  const [scheduled, setScheduled] = useState<ScheduledFeedItem[] | null>(null);

  // Default project + accounts — needed to open RunDialog
  const [defaultProject, setDefaultProject] = useState<ProjectResponse | null>(null);
  const [accounts, setAccounts] = useState<AccountResponse[]>([]);

  const [pickerOpen, setPickerOpen] = useState(false);
  const [dialogRunType, setDialogRunType] = useState<RunType | null>(null);

  const loadFeed = useCallback(async () => {
    try {
      const [runsData, scheduledData] = await Promise.all([
        api.getRunFeed(),
        api.getScheduledRunFeed(),
      ]);
      setRuns(runsData);
      setScheduled(scheduledData);
    } catch (err) {
      addToast(err instanceof ApiError ? err.messageRu : t("genericError"));
    }
  }, [t, addToast]);

  // Load default project + accounts on mount
  useEffect(() => {
    api
      .listProjects()
      .then((projects) => {
        const active = projects.filter((p) => p.archived_at === null);
        const proj = active[0] ?? projects[0] ?? null;
        setDefaultProject(proj);
        if (proj) {
          return api.listAccounts(proj.id).then(setAccounts);
        }
      })
      .catch(() => {});
  }, []);

  // Load feed on mount
  useEffect(() => {
    void loadFeed();
  }, [loadFeed]);

  // Poll while any run is in progress
  useEffect(() => {
    if (!runs) return;
    const hasInProgress = runs.some((r) => IN_PROGRESS_STATUSES.has(r.status));
    if (!hasInProgress) return;
    const handle = setInterval(() => void loadFeed(), POLL_MS);
    return () => clearInterval(handle);
  }, [runs, loadFeed]);

  function onPickRunType(runType: RunType) {
    setPickerOpen(false);
    setDialogRunType(runType);
  }

  const filteredRuns =
    filter === "all" ? (runs ?? []) : (runs ?? []).filter((r) => r.run_type === filter);

  const hasStatRuns = (runs ?? []).some((r) => r.run_type === "stat_collection");
  const hasDeepRuns = (runs ?? []).some((r) => r.run_type === "deep_analysis");

  const statusLabel: Record<RunFeedItem["status"], string> = {
    pending: t("statusPending"),
    scraping: t("statusScraping"),
    summarizing: t("statusSummarizing"),
    done: t("statusDone"),
    failed: t("statusFailed"),
  };

  return (
    <main
      className="relative mx-auto flex w-full max-w-2xl flex-col gap-4 p-4"
      style={{ paddingBottom: "max(5.5rem, calc(env(safe-area-inset-bottom) + 5.5rem))" }}
    >
      {view === "feed" && (
        <>
          {/* Filter chips + schedule icon */}
          <div className="flex items-center justify-between gap-2">
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setFilter("all")}
                className={`rounded-chip px-3.5 py-1.5 text-sm font-medium transition-all active:scale-[0.98] ${
                  filter === "all"
                    ? "bg-ink text-white"
                    : "border border-border text-secondary hover:text-ink"
                }`}
              >
                {t("filterAll")}
              </button>
              {hasStatRuns && (
                <button
                  onClick={() => setFilter("stat_collection")}
                  className={`rounded-chip px-3.5 py-1.5 text-sm font-medium transition-all active:scale-[0.98] ${
                    filter === "stat_collection"
                      ? "bg-ink text-white"
                      : "border border-border text-secondary hover:text-ink"
                  }`}
                >
                  {t("filterStat")}
                </button>
              )}
              {hasDeepRuns && (
                <button
                  onClick={() => setFilter("deep_analysis")}
                  className={`rounded-chip px-3.5 py-1.5 text-sm font-medium transition-all active:scale-[0.98] ${
                    filter === "deep_analysis"
                      ? "bg-ink text-white"
                      : "border border-border text-secondary hover:text-ink"
                  }`}
                >
                  {t("filterDeep")}
                </button>
              )}
            </div>
            <button
              onClick={() => setView("schedule")}
              aria-label={t("scheduleIconLabel")}
              className="inline-flex shrink-0 items-center justify-center rounded-control border border-border p-2.5 text-secondary transition-colors active:scale-[0.98] hover:bg-bg"
            >
              <CalendarClock className="h-4 w-4" />
            </button>
          </div>

          {/* Runs list */}
          {runs === null && <SkeletonList count={4} />}
          {runs !== null && filteredRuns.length === 0 && (
            <p className="py-8 text-center text-sm text-secondary">{t("emptyRuns")}</p>
          )}
          {filteredRuns.length > 0 && (
            <div className="flex flex-col gap-2">
              {filteredRuns.map((run) => (
                <button
                  key={run.id}
                  onClick={() => router.push(`/projects/${run.project_id}/runs/${run.id}`)}
                  className="flex items-center gap-3 rounded-card border border-border bg-card px-4 py-3.5 text-left transition-all active:scale-[0.99] hover:bg-bg"
                >
                  <div className="min-w-0 flex-1">
                    <div className="mb-1.5 flex items-center gap-2">
                      <span className="rounded-chip bg-bg px-2 py-0.5 text-[11px] font-medium text-secondary border border-border">
                        {run.run_type === "deep_analysis" ? t("runTypeDeep") : t("runTypeStat")}
                      </span>
                    </div>
                    <p className="font-mono text-sm font-medium text-ink">{formatDate(run.created_at)}</p>
                    <p className="mt-0.5 truncate text-xs text-secondary">{run.project_name}</p>
                  </div>
                  <div className="shrink-0">
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-chip px-2.5 py-1 text-[11.5px] font-medium ${
                        RUN_STATUS_PILL[run.status]
                      }`}
                    >
                      <span className={`h-1.5 w-1.5 rounded-full ${RUN_STATUS_DOT[run.status]}`} />
                      {statusLabel[run.status]}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </>
      )}

      {view === "schedule" && (
        <>
          <button
            onClick={() => setView("feed")}
            className="flex w-fit items-center gap-1 text-sm text-secondary transition-colors hover:text-ink"
          >
            <ArrowLeft className="h-4 w-4" />
            {t("back")}
          </button>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">{t("tabScheduled")}</h1>

          {scheduled === null && <SkeletonList count={3} />}
          {scheduled !== null && scheduled.length === 0 && (
            <p className="py-8 text-center text-sm text-secondary">{t("emptyScheduled")}</p>
          )}
          {scheduled !== null && scheduled.length > 0 && (
            <div className="flex flex-col gap-2">
              {scheduled.map((sr) => (
                <button
                  key={sr.id}
                  onClick={() => router.push(`/projects/${sr.project_id}/scheduled`)}
                  className="flex items-center gap-3 rounded-card border border-border bg-card px-4 py-3.5 text-left transition-all active:scale-[0.99] hover:bg-bg"
                >
                  <div className="min-w-0 flex-1">
                    <div className="mb-1.5 flex items-center gap-2">
                      <span className="rounded-chip bg-bg px-2 py-0.5 text-[11px] font-medium text-secondary border border-border">
                        {sr.run_type === "deep_analysis" ? t("runTypeDeep") : t("runTypeStat")}
                      </span>
                      {!sr.active && (
                        <span className="rounded-chip bg-danger-soft px-2 py-0.5 text-[11px] font-medium text-danger">
                          {t("scheduledInactive")}
                        </span>
                      )}
                    </div>
                    <p className="text-sm font-medium text-ink">
                      {sr.mode === "once" ? t("scheduledModeOnce") : t("scheduledModeRecurring")}
                      {" · "}
                      {sr.days_of_week.map((d) => t(WEEKDAY_KEYS[d])).join(", ")}
                    </p>
                    <p className="mt-0.5 truncate text-xs text-secondary">{sr.project_name}</p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </>
      )}

      {/* FAB — available on both the feed and schedule views */}
      <button
        onClick={() => setPickerOpen(true)}
        className="fixed bottom-6 right-6 z-40 flex h-16 w-16 items-center justify-center rounded-card bg-lime shadow-[0_8px_24px_rgba(140,170,20,0.40)] transition-all active:scale-[0.96] hover:opacity-90"
        style={{ bottom: "max(1.5rem, calc(env(safe-area-inset-bottom) + 1.5rem))" }}
        aria-label="Новый запуск"
      >
        <Plus className="h-7 w-7 text-ink" />
      </button>

      {/* Run type picker */}
      {pickerOpen && (
        <RunTypePickerSheet
          onPick={onPickRunType}
          onClose={() => setPickerOpen(false)}
        />
      )}

      {/* Run dialog */}
      {dialogRunType !== null && defaultProject && (
        <RunDialog
          projectId={defaultProject.id}
          projectName={defaultProject.name}
          accounts={accounts}
          runType={dialogRunType}
          onClose={() => {
            setDialogRunType(null);
            void loadFeed();
          }}
        />
      )}
    </main>
  );
}
